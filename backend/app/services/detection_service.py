"""YOLO 单图与批量推理服务。"""

import io
import threading
import time
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.config.detection import (
    ALLOWED_IMAGE_TYPES,
    DEFAULT_IMAGE_SIZE,
    MAX_BATCH_SIZE,
    MAX_IMAGE_SIZE,
)
from app.core.logger import get_logger
from app.entity.db_models import ModelVersion
from app.services.history_service import history_service
from app.storage.minio_client import MinIOClient


logger = get_logger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class DetectionService:
    """编排模型加载、推理、对象存储和历史落库。"""

    def __init__(self):
        self._models = {}
        self._inference_locks = {}
        self._model_lock = threading.Lock()
        self._warmup_status = "idle"
        self._warmup_error = ""

    def warmup_models(self):
        from app.database.session import SessionLocal

        db = SessionLocal()
        self._warmup_status = "loading"
        try:
            versions = db.query(ModelVersion).filter(ModelVersion.status == "active").all()
            for version in versions:
                self._get_model(version)
            self._warmup_status = "ready"
        except Exception as exc:
            self._warmup_status = "error"
            self._warmup_error = str(exc)
            logger.warning("检测模型预热失败: %s", exc)
        finally:
            db.close()

    def warmup_status(self):
        return {"status": self._warmup_status, "error": self._warmup_error, "loaded": len(self._models)}

    @staticmethod
    def _resolve_model(db: Session, model_id: int) -> ModelVersion:
        model_version = (
            db.query(ModelVersion)
            .filter(ModelVersion.id == model_id, ModelVersion.status == "active")
            .first()
        )
        if not model_version:
            raise HTTPException(status_code=404, detail="模型版本不存在或不可用")
        return model_version

    @staticmethod
    def _resolve_model_path(model_path: str) -> Path:
        path = Path(model_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path = path.resolve()
        if not path.is_file():
            raise HTTPException(status_code=500, detail=f"模型权重不存在: {path}")
        return path

    def _get_model(self, model_version: ModelVersion):
        model_path = self._resolve_model_path(model_version.model_path)
        cache_key = (model_version.id, str(model_path))
        cached = self._models.get(cache_key)
        if cached is not None:
            return cached

        with self._model_lock:
            cached = self._models.get(cache_key)
            if cached is None:
                try:
                    from ultralytics import YOLO

                    cached = YOLO(str(model_path))
                except ImportError as exc:
                    raise HTTPException(status_code=500, detail="未安装 Ultralytics 推理依赖") from exc
                except Exception as exc:
                    logger.exception("模型加载失败 model_id=%s path=%s", model_version.id, model_path)
                    raise HTTPException(status_code=500, detail="模型权重加载失败") from exc
                self._models[cache_key] = cached
                self._inference_locks[cache_key] = threading.Lock()
        return cached

    def _predict(self, model_version, model, image, task):
        model_path = self._resolve_model_path(model_version.model_path)
        cache_key = (model_version.id, str(model_path))
        inference_lock = self._inference_locks.setdefault(cache_key, threading.Lock())
        with inference_lock:
            return model.predict(
                source=image,
                conf=task.conf_threshold,
                iou=task.iou_threshold,
                imgsz=task.image_size,
                verbose=False,
            )

    @staticmethod
    async def _read_image(file: UploadFile) -> tuple[bytes, Image.Image]:
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=400, detail=f"不支持的图片类型: {file.content_type}")
        data = await file.read(MAX_IMAGE_SIZE + 1)
        if not data:
            raise HTTPException(status_code=400, detail="上传图片为空")
        if len(data) > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail="图片大小不能超过 10 MB")
        try:
            image = Image.open(io.BytesIO(data))
            image.verify()
            image = Image.open(io.BytesIO(data)).convert("RGB")
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(status_code=400, detail="图片内容无法解析") from exc
        return data, image

    @staticmethod
    def _parse_result(result, scene) -> list[dict]:
        names = result.names
        class_names_cn = scene.class_names_cn or {}
        parsed = []
        if result.boxes is None:
            return parsed
        for box in result.boxes:
            class_id = int(box.cls.item())
            class_name = names[class_id] if isinstance(names, dict) else names[class_id]
            parsed.append(
                {
                    "class_id": class_id,
                    "class_name": class_name,
                    "class_name_cn": class_names_cn.get(class_name, class_name),
                    "confidence": round(float(box.conf.item()), 6),
                    "bbox": [round(float(value), 2) for value in box.xyxy[0].tolist()],
                }
            )
        return parsed

    @staticmethod
    def _encode_annotated_image(result) -> bytes:
        annotated_bgr = result.plot()
        annotated_rgb = annotated_bgr[:, :, ::-1]
        output = io.BytesIO()
        Image.fromarray(annotated_rgb).save(output, format="JPEG", quality=90)
        return output.getvalue()

    async def _detect_file(self, file, task, model_version, model, minio_client):
        filename = Path(file.filename or "image.jpg").name
        source_bytes, image = await self._read_image(file)
        started_at = time.perf_counter()
        try:
            results = await run_in_threadpool(self._predict, model_version, model, image, task)
        except Exception as exc:
            logger.exception("YOLO 推理失败 task_id=%s file=%s", task.id, filename)
            raise HTTPException(status_code=500, detail="YOLO 模型推理失败") from exc
        inference_time = round((time.perf_counter() - started_at) * 1000, 2)
        if not results:
            raise HTTPException(status_code=500, detail="YOLO 模型未返回推理结果")

        result = results[0]
        detections = self._parse_result(result, task.scene)
        object_id = uuid4().hex
        suffix = Path(filename).suffix.lower() or ".jpg"
        base_path = f"detections/{task.user_id}/{task.id}"
        image_url = minio_client.upload_bytes(
            f"{base_path}/original/{object_id}{suffix}",
            source_bytes,
            file.content_type,
        )
        try:
            annotated_url = minio_client.upload_bytes(
                f"{base_path}/annotated/{object_id}.jpg",
                self._encode_annotated_image(result),
                "image/jpeg",
            )
        except Exception:
            minio_client.delete_by_url(image_url)
            raise

        db_results = [
            {
                "image_path": image_url,
                "annotated_image_url": annotated_url,
                **item,
                "inference_time": inference_time,
                "image_width": image.width,
                "image_height": image.height,
            }
            for item in detections
        ]
        return {
            "filename": filename,
            "image_url": image_url,
            "annotated_image_url": annotated_url,
            "image_width": image.width,
            "image_height": image.height,
            "total_objects": len(detections),
            "inference_time_ms": inference_time,
            "objects": detections,
            "db_results": db_results,
        }

    async def detect_single(self, db, user_id, file, model_id, conf_threshold, iou_threshold):
        model_version = self._resolve_model(db, model_id)
        task = history_service.create_task(
            db,
            user_id=user_id,
            scene_id=model_version.scene_id,
            task_type="single",
            model_version_id=model_version.id,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            image_size=DEFAULT_IMAGE_SIZE,
        )
        history_service.mark_processing(db, task.id)
        try:
            result = await self._detect_file(
                file, task, model_version, self._get_model(model_version), MinIOClient()
            )
            if result["db_results"]:
                history_service.add_results(db, task.id, result["db_results"])
            history_service.mark_completed(
                db, task.id, total_images=1, total_objects=result["total_objects"],
                total_inference_time=result["inference_time_ms"],
            )
        except Exception as exc:
            detail = exc.detail if isinstance(exc, HTTPException) else "检测处理失败"
            history_service.mark_failed(db, task.id, str(detail))
            raise
        result.pop("db_results")
        return {"task_id": task.id, "status": "completed", **result}

    async def detect_batch(self, db, user_id, files, model_id, conf_threshold, iou_threshold):
        if not files or len(files) > MAX_BATCH_SIZE:
            raise HTTPException(status_code=400, detail=f"批量检测需上传 1-{MAX_BATCH_SIZE} 张图片")
        model_version = self._resolve_model(db, model_id)
        task = history_service.create_task(
            db,
            user_id=user_id,
            scene_id=model_version.scene_id,
            task_type="batch",
            model_version_id=model_version.id,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            image_size=DEFAULT_IMAGE_SIZE,
        )
        history_service.mark_processing(db, task.id)
        try:
            model = self._get_model(model_version)
            minio_client = MinIOClient()
        except Exception as exc:
            detail = exc.detail if isinstance(exc, HTTPException) else "检测服务初始化失败"
            history_service.mark_failed(db, task.id, str(detail))
            raise

        items = []
        db_results = []
        total_objects = 0
        total_inference_time = 0.0
        for file in files:
            try:
                result = await self._detect_file(file, task, model_version, model, minio_client)
                db_results.extend(result.pop("db_results"))
                total_objects += result["total_objects"]
                total_inference_time += result["inference_time_ms"]
                items.append({"file_name": result.pop("filename"), "status": "completed", **result})
            except Exception as exc:
                detail = exc.detail if isinstance(exc, HTTPException) else "检测处理失败"
                items.append({"file_name": Path(file.filename or "unknown").name, "status": "failed", "error": str(detail)})

        try:
            if db_results:
                history_service.add_results(db, task.id, db_results)
            history_service.mark_completed(
                db, task.id, total_images=len(files), total_objects=total_objects,
                total_inference_time=round(total_inference_time, 2),
            )
        except Exception:
            history_service.mark_failed(db, task.id, "检测结果保存失败")
            raise
        success_count = sum(item["status"] == "completed" for item in items)
        return {
            "task_id": task.id,
            "status": "completed",
            "success_count": success_count,
            "failed_count": len(items) - success_count,
            "items": items,
        }


    def _get_default_model(self):
        """获取默认模型实例（供 Agent Tool 使用）"""
        from app.database.session import SessionLocal

        db = SessionLocal()
        try:
            model_version = (
                db.query(ModelVersion)
                .filter(ModelVersion.status == "active", ModelVersion.is_default == True)
                .first()
            )
            if not model_version:
                model_version = db.query(ModelVersion).filter(ModelVersion.status == "active").first()
            if not model_version:
                raise RuntimeError("数据库中没有可用的模型版本，请先注册模型")
            return self._get_model(model_version), model_version
        finally:
            db.close()

    def _detect_file_sync(
        self, image_path: str, *, conf: float = 0.25, iou: float = 0.45
    ) -> dict:
        """同步检测本地图片文件（供 Agent Tool 调用，不写数据库）"""
        model, _ = self._get_default_model()

        results = model.predict(
            source=image_path, conf=conf, iou=iou, imgsz=640, device="cpu",
            save=False, verbose=False,
        )
        result = results[0]

        detections = []
        class_counts = {}
        total_objects = 0

        if result.boxes is not None and len(result.boxes) > 0:
            for box in result.boxes:
                cls_id = int(box.cls.item())
                cls_name = model.names.get(cls_id, f"class_{cls_id}")
                confidence = float(box.conf.item())
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                detections.append({
                    "class_name": cls_name,
                    "class_id": cls_id,
                    "confidence": round(confidence, 4),
                    "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                })
                total_objects += 1
                class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

        inference_time = round(float(result.speed.get("inference", 0)), 2)
        logger.info("同步检测 %s: %d 个目标, 耗时 %s ms", image_path, total_objects, inference_time)

        return {
            "total_objects": total_objects,
            "class_counts": class_counts,
            "detections": detections,
            "inference_time": inference_time,
        }


detection_service = DetectionService()
