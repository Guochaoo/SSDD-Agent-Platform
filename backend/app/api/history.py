"""
检测记录与统计 API 路由
- GET    /api/history                    检测任务分页历史（支持筛选）
- GET    /api/history/statistics/summary 检测统计
- GET    /api/history/{task_id}          检测任务详情（含结果列表）
- DELETE /api/history/{task_id}          删除检测任务
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.entity.db_models import User
from app.entity.schemas import (
    DetectionTaskResponse, DetectionTaskDetail, DetectionResultResponse,
    DetectionStatistics, PageResponse,
)
from app.services.history_service import history_service

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
    items, total = history_service.list_tasks(
        db, user_id=current_user.id, is_superuser=current_user.is_superuser,
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
    return history_service.get_statistics(
        db, user_id=current_user.id, is_superuser=current_user.is_superuser, days=days
    )


@router.get("/{task_id}", response_model=DetectionTaskDetail)
def get_history_detail(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """检测任务详情，含所有检测结果"""
    task = history_service.get_task_detail(db, task_id, current_user.id, current_user.is_superuser)
    return {
        "task": _task_to_response(task),
        "results": [DetectionResultResponse.model_validate(r) for r in task.results],
    }


@router.delete("/{task_id}")
def delete_history(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除检测任务：先清理 MinIO 标注图文件，再删数据库记录"""
    history_service.delete_task(db, task_id, current_user.id, current_user.is_superuser)
    return {"message": "删除成功"}
