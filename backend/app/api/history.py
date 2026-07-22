"""
检测记录与统计 API 路由
- GET    /api/history                    检测任务分页历史（支持筛选）
- GET    /api/history/statistics/summary 检测统计
- GET    /api/history/{task_id}          检测任务详情（含结果列表）
- DELETE /api/history/{task_id}          删除检测任务
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.entity.db_models import User
from app.entity.schemas import (
    DetectionTaskResponse, DetectionTaskDetail, DetectionResultResponse,
    DetectionStatistics, PageResponse,
)
from app.services.history_service import history_service
from app.services.operation_log_service import operation_log_service
from app.services.authorization_service import authorization_service

router = APIRouter(prefix="/api/history", tags=["检测历史"])


def _task_to_response(task) -> DetectionTaskResponse:
    data = DetectionTaskResponse.model_validate(task)
    data.scene_name = task.scene.display_name if task.scene else None
    return data


@router.get("", response_model=PageResponse)
def list_history(
    scene_id: int | None = None,
    task_type: str | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """分页查询检测历史；管理员可查看所有用户的记录，普通用户只能查看自己的"""
    can_read_all = authorization_service.has_permission(db, current_user, "detection:task:read_all")
    items, total = history_service.list_tasks(
        db, user_id=current_user.id, is_superuser=can_read_all,
        scene_id=scene_id, task_type=task_type, status=status,
        page=page, page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size else 0,
        "items": [_task_to_response(i) for i in items],
    }


@router.get("/statistics/summary", response_model=DetectionStatistics)
def get_statistics(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """检测统计数据：总量、平均耗时、类别分布、每日趋势、场景分布"""
    can_read_all = authorization_service.has_permission(db, current_user, "detection:task:read_all")
    return history_service.get_statistics(db, user_id=current_user.id, is_superuser=can_read_all, days=days)


@router.get("/{task_id}", response_model=DetectionTaskDetail)
def get_history_detail(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """检测任务详情，含所有检测结果"""
    can_read_all = authorization_service.has_permission(db, current_user, "detection:task:read_all")
    task = history_service.get_task_detail(db, task_id, current_user.id, can_read_all)
    return {
        "task": _task_to_response(task),
        "results": [DetectionResultResponse.model_validate(r) for r in task.results],
    }


@router.delete("/{task_id}")
def delete_history(
    task_id: int,
    http_request: Request,
    expected_version: int | None = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """将检测任务移入 30 天回收站；不会立即删除对象存储文件。"""
    can_delete_all = authorization_service.has_permission(db, current_user, "detection:task:delete_all")
    task = history_service.delete_task(
        db, task_id, current_user.id, can_delete_all, expected_version=expected_version
    )
    operation_log_service.record(
        db, user=current_user, module="detection", action="delete_task",
        target_type="detection_task", target_id=str(task_id),
        description=f"检测任务进入回收站 public_task_id={task.public_task_id}", request=http_request,
    )
    return {
        "message": "已移入回收站",
        "public_task_id": task.public_task_id,
        "resource_version": task.resource_version,
        "purge_after": task.purge_after,
    }


@router.post("/{task_id}/restore", response_model=DetectionTaskResponse)
def restore_history(
    task_id: int,
    expected_version: int | None = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    can_delete_all = authorization_service.has_permission(db, current_user, "detection:task:delete_all")
    task = history_service.restore_task(
        db, task_id, current_user.id, can_delete_all, expected_version=expected_version
    )
    return _task_to_response(task)


@router.delete("/{task_id}/purge")
def purge_history(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    can_delete_all = authorization_service.has_permission(db, current_user, "detection:task:delete_all")
    job = history_service.purge_task(db, task_id, current_user.id, can_delete_all)
    return {"message": "已彻底删除", "cleanup_job_id": job.id, "status": job.status}
