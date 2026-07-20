"""
训练相关 API 路由

接口列表：
  - POST   /api/training/start              启动训练任务
  - GET    /api/training/tasks               获取训练任务列表
  - GET    /api/training/status/{task_id}    获取训练状态（含最新指标）
  - GET    /api/training/metrics/{task_id}   获取训练指标历史（所有 epoch）
  - POST   /api/training/stop/{task_id}      停止训练任务
  - GET    /api/training/results/{task_uuid}  获取 results.csv 原始数据
  - POST   /api/training/validate/{task_id}  模型评估
  - POST   /api/training/export/{task_id}    模型导出
  - GET    /api/training/download/{task_id}  下载模型权重
  - POST   /api/training/predict            测试图验证
"""

import base64
import hashlib
import io
import math
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import cv2
import yaml
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import get_db
from app.entity.db_models import TrainingDataset, TrainingTask, User
from app.entity.schemas import (
    ModelExportRequest,
    ModelValidateRequest,
    TrainingMetricResponse,
    TrainingDatasetMetadataUpdate,
    TrainingTaskCreate,
    TrainingTaskResponse,
)
from app.training.training_service import training_service

logger = get_logger(__name__)

BUILTIN_DATASET_PATH = "NEU-DET.v9i.yolov11"
MAX_DATASET_ARCHIVE_BYTES = 500 * 1024 * 1024
MAX_DATASET_EXTRACTED_BYTES = 2 * 1024 * 1024 * 1024
ALLOWED_DATASET_SUFFIXES = {
    ".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff",
    ".txt", ".yaml", ".yml",
}


def _is_builtin_dataset(record: TrainingDataset | None) -> bool:
    return bool(record and record.is_builtin)


def _is_builtin_dataset_path(dataset_path: str, record: TrainingDataset | None = None) -> bool:
    # The dataset list exposes the root dataset as ``.``.  Treat that stable
    # relative alias exactly like the shipped dataset name so starting a task
    # does not fail the ownership lookup with RESOURCE_NOT_FOUND.
    return dataset_path in {".", BUILTIN_DATASET_PATH} or _is_builtin_dataset(record)

router = APIRouter(prefix="/api/training", tags=["模型训练"])


def _dataset_root() -> Path:
    project_root = Path(__file__).resolve().parents[3]
    return (project_root / settings.DATASET_BASE_DIR).resolve()


def _safe_dataset_path(dataset_path: str | None) -> Path:
    root = _dataset_root()
    candidate = (root / dataset_path).resolve() if dataset_path else root
    if candidate != root and root not in candidate.parents:
        raise HTTPException(status_code=400, detail="数据集路径无效")
    return candidate


def _dataset_image_count(dataset_path: Path) -> int:
    image_suffixes = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
    return sum(
        1 for item in dataset_path.rglob("*")
        if item.is_file() and item.suffix.lower() in image_suffixes
    )


def _validate_dataset_archive(archive_file: zipfile.ZipFile) -> None:
    """Reject unsafe, oversized, unsupported or duplicate YOLO dataset archives before extraction."""
    total_uncompressed = 0
    seen_paths: set[str] = set()
    image_hashes: set[str] = set()
    image_count = 0
    for member in archive_file.infolist():
        if member.is_dir():
            continue
        normalized = member.filename.replace("\\", "/").strip("/")
        if not normalized or normalized.casefold() in seen_paths:
            raise HTTPException(status_code=400, detail={"code": "DUPLICATE_CONTENT", "message": "数据集压缩包包含重复文件"})
        seen_paths.add(normalized.casefold())
        suffix = Path(normalized).suffix.lower()
        if suffix not in ALLOWED_DATASET_SUFFIXES:
            raise HTTPException(status_code=400, detail={"code": "INVALID_FORMAT", "message": f"数据集包含不支持的文件类型: {suffix or '无扩展名'}"})
        total_uncompressed += member.file_size
        if total_uncompressed > MAX_DATASET_EXTRACTED_BYTES:
            raise HTTPException(status_code=413, detail={"code": "DATASET_TOO_LARGE", "message": "数据集解压后不能超过 2 GB"})
        if suffix in {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}:
            image_count += 1
            digest = hashlib.sha256()
            with archive_file.open(member) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() in image_hashes:
                raise HTTPException(status_code=400, detail={"code": "DUPLICATE_CONTENT", "message": "数据集包含内容重复的图片"})
            image_hashes.add(digest.hexdigest())
    if image_count == 0:
        raise HTTPException(status_code=400, detail={"code": "INVALID_DATASET", "message": "数据集至少需要一张图片"})


def _validate_dataset_classes(dataset_path: Path) -> None:
    """Validate data.yaml classes and labels under labels/ without changing uploaded files."""
    try:
        config = yaml.safe_load((dataset_path / "data.yaml").read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_DATASET", "message": "data.yaml 无法解析"}) from exc
    names = config.get("names") if isinstance(config, dict) else None
    if isinstance(names, dict):
        classes = list(names.values())
    elif isinstance(names, list):
        classes = names
    else:
        classes = []
    if not classes or any(not isinstance(name, str) or not name.strip() for name in classes):
        raise HTTPException(status_code=400, detail={"code": "INVALID_DATASET", "message": "data.yaml 必须定义非空 names 类别列表"})
    if config.get("nc") is not None and config["nc"] != len(classes):
        raise HTTPException(status_code=400, detail={"code": "INVALID_DATASET", "message": "data.yaml 的 nc 与 names 类别数量不一致"})
    for label_file in dataset_path.rglob("*.txt"):
        if "labels" not in {part.lower() for part in label_file.parts}:
            continue
        for line_number, line in enumerate(label_file.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            fields = line.split()
            try:
                class_id = int(fields[0])
                coordinates = [float(value) for value in fields[1:]]
            except (ValueError, IndexError) as exc:
                raise HTTPException(status_code=400, detail={"code": "INVALID_DATASET", "message": f"标签格式无效: {label_file.name}:{line_number}"}) from exc
            if len(fields) != 5 or not 0 <= class_id < len(classes):
                raise HTTPException(status_code=400, detail={"code": "INVALID_DATASET", "message": f"标签类别超出 data.yaml 范围: {label_file.name}:{line_number}"})
            if not all(math.isfinite(value) and 0 <= value <= 1 for value in coordinates) or coordinates[2] <= 0 or coordinates[3] <= 0:
                raise HTTPException(status_code=400, detail={"code": "INVALID_DATASET", "message": f"标签坐标必须是 0-1 范围内的有限值: {label_file.name}:{line_number}"})


def _get_dataset_record(db: Session, dataset_path: str, current_user: User) -> TrainingDataset | None:
    record = db.query(TrainingDataset).filter(TrainingDataset.path == dataset_path).first()
    if record is None and not _is_builtin_dataset_path(dataset_path):
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "数据集不存在或尚未登记"})
    if record and not (_is_builtin_dataset_path(dataset_path, record) or record.owner_id == current_user.id or current_user.is_superuser):
        raise HTTPException(status_code=403, detail="无权访问该数据集")
    return record


@router.get("/datasets")
async def list_datasets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    root = _dataset_root()
    root.mkdir(parents=True, exist_ok=True)
    datasets = []
    records = {record.path: record for record in db.query(TrainingDataset).all()}
    for directory in sorted(item for item in root.iterdir() if item.is_dir()):
        record = records.get(directory.name)
        is_builtin = _is_builtin_dataset_path(directory.name, record)
        if record is None and not is_builtin:
            continue
        if record and not (is_builtin or record.owner_id == current_user.id or current_user.is_superuser):
            continue
        datasets.append({
            "name": record.display_name or directory.name if record else directory.name,
            "path": directory.name,
            "ready": (directory / "data.yaml").is_file(),
            "owner_id": record.owner_id if record else None,
            "is_builtin": is_builtin,
            "display_name": record.display_name if record else None,
            "description": record.description if record else None,
        })
    if (root / "data.yaml").is_file():
        datasets.insert(0, {"name": root.name, "path": ".", "ready": True, "owner_id": None, "is_builtin": True})
    return {"items": datasets}


@router.patch("/datasets/{dataset_path}")
async def update_dataset_metadata(
    dataset_path: str,
    payload: TrainingDatasetMetadataUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update metadata only; dataset files and their stable path are not renamed."""
    record = _get_dataset_record(db, dataset_path, current_user)
    if _is_builtin_dataset_path(dataset_path, record):
        raise HTTPException(status_code=403, detail={"code": "BUILTIN_RESOURCE", "message": "内置数据集只读"})
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "数据集不存在"})
    if record.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "无权编辑该数据集"})
    record.display_name = payload.display_name.strip() if payload.display_name else None
    record.description = payload.description.strip() if payload.description else None
    db.commit()
    db.refresh(record)
    return {
        "name": record.display_name or record.path,
        "path": record.path,
        "display_name": record.display_name,
        "description": record.description,
        "owner_id": record.owner_id,
        "is_builtin": record.is_builtin,
    }


@router.get("/datasets/{dataset_path}/download")
async def download_dataset(
    dataset_path: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a temporary ZIP download for one dataset directory."""
    root = _dataset_root()
    dataset = _safe_dataset_path(dataset_path)
    if not dataset.is_dir():
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "数据集不存在"})
    _get_dataset_record(db, dataset_path, current_user)

    archive_dir = Path(tempfile.mkdtemp(prefix="dataset-download-"))
    archive_path = Path(shutil.make_archive(str(archive_dir / dataset.name), "zip", dataset))
    background_tasks.add_task(shutil.rmtree, archive_dir, ignore_errors=True)
    return FileResponse(path=archive_path, media_type="application/zip", filename=f"{dataset.name}.zip", background=background_tasks)


@router.delete("/datasets/{dataset_path}")
async def delete_dataset(
    dataset_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an unused dataset directory without allowing root deletion."""
    root = _dataset_root()
    dataset = _safe_dataset_path(dataset_path)
    if dataset == root:
        raise HTTPException(status_code=400, detail="不能删除数据集根目录")
    if not dataset.is_dir():
        raise HTTPException(status_code=404, detail="数据集不存在")
    record = _get_dataset_record(db, dataset_path, current_user)
    if record is None or _is_builtin_dataset_path(dataset_path, record):
        raise HTTPException(status_code=403, detail={"code": "BUILTIN_RESOURCE", "message": "内置数据集只读"})
    if record.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权删除该数据集")

    active_paths = {
        Path(task.dataset_path).resolve()
        for task in db.query(TrainingTask).filter(TrainingTask.status.in_(("pending", "running"))).all()
        if task.dataset_path
    }
    if dataset in active_paths:
        raise HTTPException(status_code=409, detail={"code": "RESOURCE_IN_USE", "message": "该数据集正在被训练任务使用，暂不能删除"})

    shutil.rmtree(dataset)
    db.delete(record)
    db.commit()
    return {"path": dataset_path, "deleted": True}


@router.post("/datasets/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="数据集必须是 ZIP 文件")
    dataset_name = Path(file.filename).stem.replace(" ", "_")
    target = _safe_dataset_path(dataset_name)
    existing = db.query(TrainingDataset).filter(TrainingDataset.path == dataset_name).first()
    if existing or target.exists():
        raise HTTPException(status_code=409, detail="同名数据集已存在")
    archive = await file.read()
    if len(archive) > MAX_DATASET_ARCHIVE_BYTES:
        raise HTTPException(status_code=413, detail={"code": "DATASET_TOO_LARGE", "message": "数据集压缩包不能超过 500 MB"})
    try:
        target.mkdir(parents=True, exist_ok=False)
        with zipfile.ZipFile(io.BytesIO(archive)) as archive_file:
            for member in archive_file.infolist():
                member_path = (target / member.filename).resolve()
                if target not in member_path.parents and member_path != target:
                    raise HTTPException(status_code=400, detail={"code": "INVALID_FORMAT", "message": "数据集压缩包包含非法路径"})
            _validate_dataset_archive(archive_file)
            archive_file.extractall(target)
        if not (target / "data.yaml").is_file():
            raise HTTPException(status_code=400, detail={"code": "INVALID_DATASET", "message": "数据集压缩包根目录必须包含 data.yaml"})
        _validate_dataset_classes(target)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail={"code": "INVALID_FORMAT", "message": "数据集压缩包无法解析"})
    except HTTPException:
        shutil.rmtree(target, ignore_errors=True)
        raise
    record = TrainingDataset(path=dataset_name, owner_id=current_user.id, is_builtin=False)
    db.add(record)
    db.commit()
    return {"name": target.name, "path": target.name, "ready": True, "owner_id": current_user.id, "is_builtin": False}


def _resolve_training_task(db: Session, identifier: str | int):
    value = str(identifier).strip()
    task = db.query(TrainingTask).filter(TrainingTask.id == int(value)).first() if value.isdigit() else None
    return task or db.query(TrainingTask).filter(TrainingTask.task_uuid == value).first()


def _check_task_access(db: Session, task_id: str | int, current_user):
    task = _resolve_training_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    if task.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权访问该训练任务")
    return task


@router.post("/start")
async def start_training(
    request: TrainingTaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    启动模型训练任务

    - **scene_id**: 关联的检测场景 ID
    - **model_name**: 基础模型（yolov11n/s/m/l/x）
    - **epochs**: 训练轮数（10~500）
    - **batch_size**: 批次大小（1~64）
    - **device**: 训练设备（cpu / 0 / 1）
    - **optimizer**: 优化器（SGD / Adam / AdamW）
    - **lr0**: 初始学习率
    - **augment_config**: 数据增强配置（JSON）
    """
    # ── 构造训练配置 ──
    config = {
        "model_name": request.model_name,
        "epochs": request.epochs,
        "img_size": request.img_size,
        "batch_size": request.batch_size,
        "device": request.device,
        "optimizer": request.optimizer,
        "lr0": request.lr0,
        "augment_config": request.augment_config,
    }

    # ── 从场景获取数据集路径 ──
    from app.entity.db_models import DetectionScene
    scene = db.query(DetectionScene).filter(DetectionScene.id == request.scene_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail="检测场景不存在")

    # 数据集路径：project_root/datasets/ssdd/
    api_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(api_dir)
    backend_dir = os.path.dirname(app_dir)
    project_root = os.path.dirname(backend_dir)
    requested_dataset = request.dataset_path
    dataset_path = os.path.join(project_root, settings.DATASET_BASE_DIR)
    if requested_dataset:
        _get_dataset_record(db, requested_dataset, current_user)
        dataset_path = str(_safe_dataset_path(requested_dataset))
    config["dataset_path"] = dataset_path
    config["dataset_size"] = _dataset_image_count(Path(dataset_path))

    # 检查 data.yaml 是否存在
    data_yaml = os.path.join(dataset_path, "data.yaml")
    if not os.path.exists(data_yaml):
        raise HTTPException(
            status_code=400,
            detail=f"data.yaml 不存在：{data_yaml}，请先完成数据集准备",
        )
    config["data_yaml"] = data_yaml

    # ── 启动训练 ──
    try:
        task = training_service.start_training(
            db=db,
            user_id=current_user.id,
            scene_id=request.scene_id,
            config=config,
        )
    except Exception as e:
        logger.error("启动训练失败：%s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"启动训练失败：{str(e)}")

    logger.info(
        "用户 %s 启动训练任务：scene=%s, model=%s, epochs=%d",
        current_user.username, scene.name, request.model_name, request.epochs,
    )

    return {
        "id": task.id,
        "task_uuid": task.task_uuid,
        "status": task.status,
        "model_name": task.model_name,
        "epochs": task.epochs,
        "message": "训练任务已创建，正在后台启动",
    }


@router.get("/tasks")
async def list_training_tasks(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取当前用户的训练任务列表"""
    tasks = training_service.get_task_list(
        db, user_id=current_user.id, is_superuser=current_user.is_superuser,
    )
    return {"total": len(tasks), "items": tasks}


@router.delete("/tasks/{task_id}")
async def delete_training_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """删除已结束的训练历史及其指标，保留已发布的模型版本。"""
    task = _check_task_access(db, task_id, current_user)
    result = training_service.delete_training_task(db, task.id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/status/{task_id}")
async def get_training_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    获取训练任务状态

    返回任务基本信息、当前进度和最新 epoch 指标
    前端可轮询此接口实现实时监控
    """
    _check_task_access(db, task_id, current_user)
    status = training_service.get_training_status(db, task_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    return status


@router.get("/metrics/{task_id}")
async def get_training_metrics(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    获取训练任务的所有 epoch 指标

    用于绘制完整的训练曲线（loss、mAP、precision、recall）
    """
    _check_task_access(db, task_id, current_user)
    metrics = training_service.get_training_metrics(db, task_id)
    return {"task_id": task_id, "total": len(metrics), "metrics": metrics}


@router.post("/stop/{task_id}")
async def stop_training(
    task_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """停止正在运行的训练任务"""
    task = _check_task_access(db, task_id, current_user)
    result = training_service.stop_training(db, task.id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/results/{task_uuid}")
async def get_results_csv(
    task_uuid: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    获取 Ultralytics 生成的原始 results.csv 文件

    可用于离线分析或导出到其他工具
    """
    task = db.query(TrainingTask).filter(TrainingTask.task_uuid == task_uuid).first()
    if not task:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    _check_task_access(db, task.id, current_user)
    results_path = os.path.join(
        settings.TRAIN_OUTPUT_DIR,
        f"task_{task_uuid}",
        "results.csv",
    )
    if not os.path.exists(results_path):
        raise HTTPException(status_code=404, detail="results.csv 文件不存在")

    return FileResponse(
        path=results_path,
        media_type="text/csv",
        filename=f"training_results_{task_uuid}.csv",
    )


@router.post("/validate/{task_id}")
async def validate_training_model(
    task_id: int,
    request: ModelValidateRequest = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    对已完成训练的模型执行评估

    - 在验证集或测试集上运行 model.val()
    - 返回 mAP、Precision、Recall 等指标
    - 返回每类 AP 分析
    - 自动创建/更新 ModelVersion 记录
    """
    _check_task_access(db, task_id, current_user)
    if request is None:
        request = ModelValidateRequest()

    result = training_service.validate_model(
        db=db, task_id=task_id,
        split=request.split, conf=request.conf, iou=request.iou,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    logger.info(
        "用户 %s 评估模型: task_id=%d, mAP50=%.4f",
        current_user.username, task_id,
        result.get("overall", {}).get("map50", 0),
    )
    return result


@router.post("/export/{task_id}")
async def export_training_model(
    task_id: int,
    request: ModelExportRequest = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    导出训练好的模型为正式版本

    - 复制 best.pt 到 models/ 目录
    - 运行评估获取最终指标
    - 保存评估报告 JSON
    - 创建 ModelVersion 记录
    - 可选上传到 MinIO
    """
    _check_task_access(db, task_id, current_user)
    if request is None:
        request = ModelExportRequest()

    result = training_service.export_model(
        db=db, task_id=task_id,
        version=request.version, description=request.description,
        set_default=request.set_default, upload_minio=request.upload_minio,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    logger.info(
        "用户 %s 导出模型: task_id=%d, version=%s",
        current_user.username, task_id, result.get("version"),
    )
    return result


@router.get("/download/{task_id}")
async def download_training_model(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """下载训练好的模型权重文件（best.pt）"""
    _check_task_access(db, task_id, current_user)
    result = training_service.get_model_download_path(db, task_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    logger.info(
        "用户 %s 下载模型: task_id=%d, file=%s",
        current_user.username, task_id, result["filename"],
    )
    return FileResponse(
        path=result["file_path"],
        media_type="application/octet-stream",
        filename=result["filename"],
    )


@router.post("/predict")
async def predict_training_image(
    file: UploadFile = File(..., description="测试图片"),
    task_id: int = Form(..., description="训练任务 ID"),
    conf: float = Form(0.25, description="置信度阈值"),
    iou: float = Form(0.45, description="NMS IoU 阈值"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    上传测试图片，使用训练好的模型进行预测

    - 使用 best.pt 进行推理
    - 返回标注图 (base64) + 检测结果列表
    """
    from ultralytics import YOLO

    allowed_types = {"image/jpeg", "image/png", "image/bmp", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file.content_type}",
        )

    _check_task_access(db, task_id, current_user)
    task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="训练任务未完成")

    weights_path = os.path.join(
        os.getcwd(), settings.TRAIN_OUTPUT_DIR,
        f"task_{task.task_uuid}", "weights", "best.pt",
    )
    if not os.path.exists(weights_path):
        raise HTTPException(status_code=404, detail="模型权重不存在")

    with tempfile.NamedTemporaryFile(
        suffix=os.path.splitext(file.filename)[1] or ".jpg", delete=False,
    ) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        model = YOLO(weights_path)
        results = model.predict(
            source=tmp_path, conf=conf, iou=iou,
            imgsz=task.img_size, device="cpu", save=False, verbose=False,
        )

        r = results[0]
        detections = []
        if r.boxes is not None and len(r.boxes) > 0:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names.get(cls_id, f"class_{cls_id}")
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append({
                    "class_name": cls_name,
                    "class_id": cls_id,
                    "confidence": round(float(box.conf[0]), 4),
                    "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                })

        annotated_img = r.plot()
        _, buf = cv2.imencode(".jpg", annotated_img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        annotated_b64 = base64.b64encode(buf).decode("utf-8")

        class_counts = {}
        for d in detections:
            class_counts[d["class_name"]] = class_counts.get(d["class_name"], 0) + 1

        return {
            "task_id": task_id,
            "task_uuid": task.task_uuid,
            "filename": file.filename,
            "total_objects": len(detections),
            "detections": detections,
            "class_counts": class_counts,
            "annotated_image": annotated_b64,
            "inference_time": round(float(r.speed.get("inference", 0)), 2),
        }
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
