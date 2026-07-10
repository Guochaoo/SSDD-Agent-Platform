"""
检测记录与统计服务层
处理检测任务的创建、状态更新、详情查询、分页历史、筛选、删除和统计
对应任务文档步骤 9。检测本身（跑 YOLO 推理）由后端 B 负责，这里只负责数据落库和查询。
"""
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.entity.db_models import DetectionTask, DetectionResult, DetectionScene
from app.storage.minio_client import MinIOClient


class HistoryService:
    """检测记录与统计服务"""

    # ── 创建 / 状态更新 ──────────────────────────────────

    @staticmethod
    def create_task(
        db: Session,
        user_id: int,
        scene_id: int,
        task_type: str,
        model_version_id: int | None = None,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
    ) -> DetectionTask:
        """创建检测任务，初始状态为 pending"""
        scene = db.query(DetectionScene).filter(DetectionScene.id == scene_id).first()
        if not scene:
            raise HTTPException(status_code=404, detail="检测场景不存在")

        task = DetectionTask(
            user_id=user_id,
            scene_id=scene_id,
            model_version_id=model_version_id,
            task_type=task_type,
            status="pending",
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            image_size=image_size,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def mark_processing(db: Session, task_id: int) -> DetectionTask:
        task = HistoryService._get_task_or_404(db, task_id)
        task.status = "processing"
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def mark_completed(
        db: Session,
        task_id: int,
        total_images: int,
        total_objects: int,
        total_inference_time: float,
    ) -> DetectionTask:
        task = HistoryService._get_task_or_404(db, task_id)
        task.status = "completed"
        task.total_images = total_images
        task.total_objects = total_objects
        task.total_inference_time = total_inference_time
        task.completed_at = datetime.now()
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def mark_failed(db: Session, task_id: int, error_message: str) -> DetectionTask:
        task = HistoryService._get_task_or_404(db, task_id)
        task.status = "failed"
        task.error_message = error_message
        task.completed_at = datetime.now()
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def add_results(db: Session, task_id: int, results: list[dict]) -> list[DetectionResult]:
        """
        批量写入某个检测任务下的单目标检测结果。
        results 形如 [{"image_path": ..., "annotated_image_url": ..., "class_name": ...,
                        "class_id": 0, "confidence": 0.9, "bbox": [x1,y1,x2,y2], ...}, ...]
        """
        HistoryService._get_task_or_404(db, task_id)
        objs = [DetectionResult(task_id=task_id, **r) for r in results]
        db.add_all(objs)
        db.commit()
        for o in objs:
            db.refresh(o)
        return objs

    # ── 查询 ─────────────────────────────────────────────

    @staticmethod
    def _get_task_or_404(db: Session, task_id: int) -> DetectionTask:
        task = db.query(DetectionTask).filter(DetectionTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="检测任务不存在")
        return task

    @staticmethod
    def get_task_detail(db: Session, task_id: int, user_id: int, is_superuser: bool = False) -> DetectionTask:
        """获取任务详情，非管理员只能查看自己的记录"""
        task = HistoryService._get_task_or_404(db, task_id)
        if task.user_id != user_id and not is_superuser:
            raise HTTPException(status_code=403, detail="无权访问该记录")
        return task

    @staticmethod
    def list_tasks(
        db: Session,
        user_id: int,
        is_superuser: bool = False,
        scene_id: int | None = None,
        task_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DetectionTask], int]:
        """分页历史查询，支持按场景/类型/状态筛选；非管理员只能看到自己的记录"""
        query = db.query(DetectionTask)
        if not is_superuser:
            query = query.filter(DetectionTask.user_id == user_id)
        if scene_id:
            query = query.filter(DetectionTask.scene_id == scene_id)
        if task_type:
            query = query.filter(DetectionTask.task_type == task_type)
        if status:
            query = query.filter(DetectionTask.status == status)

        total = query.count()
        items = (
            query.order_by(DetectionTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    # ── 删除 ─────────────────────────────────────────────

    @staticmethod
    def delete_task(db: Session, task_id: int, user_id: int, is_superuser: bool = False) -> None:
        """删除检测任务：先清理 MinIO 上的标注图，再删数据库记录（级联删 detection_results）"""
        task = HistoryService._get_task_or_404(db, task_id)
        if task.user_id != user_id and not is_superuser:
            raise HTTPException(status_code=403, detail="无权删除该记录")

        try:
            minio = MinIOClient()
            for result in task.results:
                minio.delete_by_url(result.annotated_image_url)
            db.delete(task)
            db.commit()
        except Exception:
            db.rollback()
            raise

    # ── 统计 ─────────────────────────────────────────────

    @staticmethod
    def get_statistics(db: Session, user_id: int, is_superuser: bool = False, days: int = 30) -> dict:
        """检测统计：总任务数/图像数/目标数、平均耗时、类别分布、每日趋势、场景分布"""
        query = db.query(DetectionTask).filter(DetectionTask.status == "completed")
        if not is_superuser:
            query = query.filter(DetectionTask.user_id == user_id)

        total_tasks = query.count()
        total_images = query.with_entities(func.coalesce(func.sum(DetectionTask.total_images), 0)).scalar()
        total_objects = query.with_entities(func.coalesce(func.sum(DetectionTask.total_objects), 0)).scalar()
        avg_time = query.with_entities(func.coalesce(func.avg(DetectionTask.total_inference_time), 0)).scalar()

        # 类别分布：基于 detection_results 按 class_name 聚合
        result_query = db.query(DetectionResult.class_name, func.count(DetectionResult.id)).join(
            DetectionTask, DetectionResult.task_id == DetectionTask.id
        )
        if not is_superuser:
            result_query = result_query.filter(DetectionTask.user_id == user_id)
        class_distribution = dict(result_query.group_by(DetectionResult.class_name).all())

        # 每日趋势：最近 N 天，每天完成的任务数
        since = datetime.now() - timedelta(days=days)
        daily_query = (
            db.query(func.date(DetectionTask.created_at), func.count(DetectionTask.id))
            .filter(DetectionTask.created_at >= since)
        )
        if not is_superuser:
            daily_query = daily_query.filter(DetectionTask.user_id == user_id)
        daily_rows = daily_query.group_by(func.date(DetectionTask.created_at)).order_by(func.date(DetectionTask.created_at)).all()
        daily_trend = [{"date": str(d), "count": c} for d, c in daily_rows]

        # 场景分布
        scene_query = query.join(DetectionScene, DetectionTask.scene_id == DetectionScene.id).with_entities(
            DetectionScene.display_name, func.count(DetectionTask.id)
        )
        scene_distribution = dict(scene_query.group_by(DetectionScene.display_name).all())

        return {
            "total_tasks": total_tasks,
            "total_images": int(total_images),
            "total_objects": int(total_objects),
            "avg_inference_time": float(avg_time),
            "class_distribution": class_distribution,
            "daily_trend": daily_trend,
            "scene_distribution": scene_distribution,
        }


# 全局单例
history_service = HistoryService()
