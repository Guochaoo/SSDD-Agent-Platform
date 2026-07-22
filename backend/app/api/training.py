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
import io
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import get_db
from app.entity.db_models import TrainingDataset, TrainingTask, User, default_purge_after
from app.entity.schemas import (
    ModelExportRequest,
    ModelValidateRequest,
    TrainingMetricResponse,
    TrainingTaskCreate,
    TrainingTaskResponse,
)
from app.training.training_service import training_service
from app.services.authorization_service import authorization_service
from app.services.resource_lifecycle_service import resource_lifecycle_service

logger = get_logger(__name__)

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


def _get_dataset_record(db: Session, dataset_path: str, current_user: User) -> TrainingDataset | None:
    record = db.query(TrainingDataset).filter(
        (TrainingDataset.storage_key == dataset_path) | (TrainingDataset.path == dataset_path)
    ).first()
    if record and record.deletion_status != "active":
        raise HTTPException(status_code=404, detail="数据集不存在")
    if record and not authorization_service.can_access_owner(
        db,
        current_user,
        record.owner_id,
        is_builtin=record.is_builtin,
        cross_user_permission="training:dataset:read_all",
    ):
        raise HTTPException(status_code=403, detail="无权访问该数据集")
    return record


@router.get("/datasets")
async def list_datasets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    root = _dataset_root()
    root.mkdir(parents=True, exist_ok=True)
    datasets = []
    records = {
        record.storage_key: record
        for record in db.query(TrainingDataset).filter(TrainingDataset.deletion_status == "active").all()
    }
    for directory in sorted(item for item in root.iterdir() if item.is_dir() and item.name != ".trash"):
        record = records.get(directory.name)
        if record and not authorization_service.can_access_owner(
            db,
            current_user,
            record.owner_id,
            is_builtin=record.is_builtin,
            cross_user_permission="training:dataset:read_all",
        ):
            continue
        datasets.append({
            "name": record.display_name if record else directory.name,
            "display_name": record.display_name if record else directory.name,
            "path": record.storage_key if record else directory.name,
            "storage_key": record.storage_key if record else directory.name,
            "ready": (directory / "data.yaml").is_file(),
            "owner_id": record.owner_id if record else None,
            "is_builtin": record.is_builtin if record else True,
        })
    if (root / "data.yaml").is_file():
        datasets.insert(0, {"name": root.name, "path": ".", "ready": True, "owner_id": None, "is_builtin": True})
    return {"items": datasets}


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
        raise HTTPException(status_code=404, detail="数据集不存在")
    _get_dataset_record(db, dataset_path, current_user)

    archive_dir = Path(tempfile.mkdtemp(prefix="dataset-download-"))
    archive_path = Path(shutil.make_archive(str(archive_dir / dataset.name), "zip", dataset))
    background_tasks.add_task(shutil.rmtree, archive_dir, ignore_errors=True)
    return FileResponse(path=archive_path, media_type="application/zip", filename=f"{dataset.name}.zip", background=background_tasks)


@router.delete("/datasets/{dataset_path}")
async def delete_dataset(
    dataset_path: str,
    expected_version: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move an unused dataset to the recoverable trash."""
    root = _dataset_root()
    dataset = _safe_dataset_path(dataset_path)
    if dataset == root:
        raise HTTPException(status_code=400, detail="不能删除数据集根目录")
    if not dataset.is_dir():
        raise HTTPException(status_code=404, detail="数据集不存在")
    record = _get_dataset_record(db, dataset_path, current_user)
    if record is None or record.is_builtin:
        raise HTTPException(status_code=403, detail="内置数据集不可删除")
    if record.owner_id != current_user.id and not authorization_service.has_permission(
        db, current_user, "training:dataset:delete_all"
    ):
        raise HTTPException(status_code=403, detail="无权删除该数据集")

    active_paths = {
        Path(task.dataset_path).resolve()
        for task in db.query(TrainingTask).filter(TrainingTask.status.in_(("pending", "running"))).all()
        if task.dataset_path
    }
    if dataset in active_paths:
        raise HTTPException(status_code=400, detail="该数据集正在被训练任务使用，暂不能删除")

    if expected_version is not None and record.resource_version != expected_version:
        raise HTTPException(status_code=409, detail={
            "code": "resource_changed",
            "current_version": record.resource_version,
        })
    trash_root = root / ".trash"
    trash_root.mkdir(parents=True, exist_ok=True)
    trash_target = trash_root / record.storage_key
    if trash_target.exists():
        raise HTTPException(status_code=409, detail="回收站中已存在同一资源")
    try:
        shutil.move(str(dataset), str(trash_target))
        record.deletion_status = "trashed"
        record.deleted_at = datetime.now()
        record.deleted_by_id = current_user.id
        record.purge_after = default_purge_after()
        record.resource_version += 1
        db.commit()
    except Exception:
        db.rollback()
        if trash_target.is_dir() and not dataset.exists():
            shutil.move(str(trash_target), str(dataset))
        raise
    return {
        "path": record.storage_key,
        "display_name": record.display_name,
        "deleted": True,
        "resource_version": record.resource_version,
        "purge_after": record.purge_after,
    }


@router.post("/datasets/{dataset_path}/restore")
async def restore_dataset(
    dataset_path: str,
    expected_version: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(TrainingDataset).filter(
        (TrainingDataset.storage_key == dataset_path) | (TrainingDataset.path == dataset_path)
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="数据集不存在")
    if record.owner_id != current_user.id and not authorization_service.has_permission(
        db, current_user, "training:dataset:delete_all"
    ):
        raise HTTPException(status_code=403, detail="无权恢复该数据集")
    if record.deletion_status != "trashed":
        raise HTTPException(status_code=409, detail="该数据集不在可恢复状态")
    if expected_version is not None and record.resource_version != expected_version:
        raise HTTPException(status_code=409, detail={
            "code": "resource_changed",
            "current_version": record.resource_version,
        })
    root = _dataset_root()
    source = root / ".trash" / record.storage_key
    target = root / record.storage_key
    if not source.is_dir():
        raise HTTPException(status_code=409, detail="回收站文件缺失，无法恢复")
    if target.exists():
        raise HTTPException(status_code=409, detail="目标存储位置已被占用")
    try:
        shutil.move(str(source), str(target))
        record.deletion_status = "active"
        record.deleted_at = None
        record.deleted_by_id = None
        record.purge_after = None
        record.cleanup_error = None
        record.resource_version += 1
        db.commit()
    except Exception:
        db.rollback()
        if target.is_dir() and not source.exists():
            shutil.move(str(target), str(source))
        raise
    return {
        "path": record.storage_key,
        "display_name": record.display_name,
        "resource_version": record.resource_version,
        "restored": True,
    }


@router.delete("/datasets/{dataset_path}/purge")
async def purge_dataset(
    dataset_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(TrainingDataset).filter(
        (TrainingDataset.storage_key == dataset_path) | (TrainingDataset.path == dataset_path)
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="数据集不存在")
    if record.owner_id != current_user.id and not authorization_service.has_permission(
        db, current_user, "training:dataset:delete_all"
    ):
        raise HTTPException(status_code=403, detail="无权彻底删除该数据集")
    job = resource_lifecycle_service.purge_dataset(db, record, _dataset_root())
    return {"message": "数据集已彻底删除", "cleanup_job_id": job.id, "status": job.status}


@router.post("/datasets/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=128),
):
    if not isinstance(idempotency_key, str):
        idempotency_key = None
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="数据集必须是 ZIP 文件")
    if idempotency_key:
        existing = db.query(TrainingDataset).filter(
            TrainingDataset.owner_id == current_user.id,
            TrainingDataset.idempotency_key == idempotency_key,
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail={
                "code": "duplicate_request",
                "storage_key": existing.storage_key,
                "deletion_status": existing.deletion_status,
            })
    dataset_name = Path(file.filename).stem.replace(" ", "_")
    storage_key = f"u{current_user.id}_{uuid4().hex}"
    target = _safe_dataset_path(storage_key)
    archive = await file.read()
    if len(archive) > 500 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="数据集压缩包不能超过 500 MB")
    target.mkdir(parents=True, exist_ok=False)
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as archive_file:
            for member in archive_file.infolist():
                member_path = (target / member.filename).resolve()
                if target not in member_path.parents and member_path != target:
                    raise HTTPException(status_code=400, detail="数据集压缩包包含非法路径")
            archive_file.extractall(target)
        if not (target / "data.yaml").is_file():
            raise HTTPException(status_code=400, detail="数据集压缩包根目录必须包含 data.yaml")
        record = TrainingDataset(
            path=storage_key,
            storage_key=storage_key,
            display_name=dataset_name,
            owner_id=current_user.id,
            is_builtin=False,
            idempotency_key=idempotency_key,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
    except zipfile.BadZipFile as exc:
        db.rollback()
        shutil.rmtree(target, ignore_errors=True)
        raise HTTPException(status_code=400, detail="数据集压缩包无法解析") from exc
    except IntegrityError as exc:
        db.rollback()
        shutil.rmtree(target, ignore_errors=True)
        existing = db.query(TrainingDataset).filter(
            TrainingDataset.owner_id == current_user.id,
            TrainingDataset.idempotency_key == idempotency_key,
        ).first() if idempotency_key else None
        if existing:
            raise HTTPException(status_code=409, detail={
                "code": "duplicate_request",
                "storage_key": existing.storage_key,
                "deletion_status": existing.deletion_status,
            }) from exc
        raise
    except Exception:
        db.rollback()
        shutil.rmtree(target, ignore_errors=True)
        raise
    return {
        "name": dataset_name,
        "display_name": dataset_name,
        "path": storage_key,
        "storage_key": storage_key,
        "ready": True,
        "owner_id": current_user.id,
        "is_builtin": False,
        "resource_version": record.resource_version,
    }


def _check_task_access(db: Session, task_id: int, current_user):
    task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    if task.user_id != current_user.id and not authorization_service.has_permission(
        db, current_user, "training:task:read_all"
    ):
        raise HTTPException(status_code=403, detail="无权访问该训练任务")
    if task.deletion_status != "active":
        raise HTTPException(status_code=404, detail="训练任务不存在")
    return task


@router.post("/start")
async def start_training(
    request: TrainingTaskCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=128),
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
    if not isinstance(idempotency_key, str):
        idempotency_key = None

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
        "idempotency_key": idempotency_key,
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error("启动训练失败：%s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"启动训练失败：{str(e)}")

    logger.info(
        "用户 %s 启动训练任务：scene=%s, model=%s, epochs=%d",
        current_user.username, scene.name, request.model_name, request.epochs,
    )

    return {
        "id": task.id,
        "public_task_id": task.public_task_id,
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
    can_read_all = authorization_service.has_permission(db, current_user, "training:task:read_all")
    tasks = training_service.get_task_list(db, user_id=None if can_read_all else current_user.id)
    return {"total": len(tasks), "items": tasks}


@router.delete("/tasks/{task_id}")
async def delete_training_task(
    task_id: int,
    expected_version: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """删除已结束的训练历史及其指标，保留已发布的模型版本。"""
    _check_task_access(db, task_id, current_user)
    result = training_service.delete_training_task(
        db, task_id, deleted_by_id=current_user.id, expected_version=expected_version
    )
    if "error" in result:
        status_code = 409 if result.get("code") == "resource_changed" else 400
        raise HTTPException(status_code=status_code, detail=result)
    return result


@router.post("/tasks/{task_id}/restore")
async def restore_training_task(
    task_id: int,
    expected_version: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    if task.user_id != current_user.id and not authorization_service.has_permission(
        db, current_user, "training:task:delete_all"
    ):
        raise HTTPException(status_code=403, detail="无权恢复该训练任务")
    result = training_service.restore_training_task(db, task_id, expected_version)
    if "error" in result:
        status_code = 409 if result.get("code") == "resource_changed" else 400
        raise HTTPException(status_code=status_code, detail=result)
    return result


@router.delete("/tasks/{task_id}/purge")
async def purge_training_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    task = db.query(TrainingTask).filter(TrainingTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    if task.user_id != current_user.id and not authorization_service.has_permission(
        db, current_user, "training:task:delete_all"
    ):
        raise HTTPException(status_code=403, detail="无权彻底删除该训练任务")
    job = resource_lifecycle_service.purge_training_task(db, task)
    return {"message": "训练任务已彻底删除", "cleanup_job_id": job.id, "status": job.status}


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
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """停止正在运行的训练任务"""
    _check_task_access(db, task_id, current_user)
    result = training_service.stop_training(db, task_id)
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
        import cv2

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
