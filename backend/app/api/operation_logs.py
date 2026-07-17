"""
操作审计日志 API（管理员）
- GET /api/operation-logs 分页查询操作日志，支持按用户/模块/动作/状态筛选

写日志的动作分散在各个业务路由里（登录、密码修改、用户删除、模型默认切换等），
本模块只提供读取入口，给管理端的审计页面用。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.entity.db_models import User
from app.entity.schemas import OperationLogResponse, PageResponse
from app.services.operation_log_service import operation_log_service

router = APIRouter(prefix="/api/operation-logs", tags=["操作审计"])


@router.get("", response_model=PageResponse)
def list_operation_logs(
    user_id: Optional[int] = Query(default=None, description="按操作用户过滤"),
    module: Optional[str] = Query(default=None, description="按模块过滤"),
    action: Optional[str] = Query(default=None, description="按动作类型过滤"),
    status: Optional[str] = Query(default=None, description="success/failure"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """分页查询操作日志，仅管理员可访问"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="需要管理员权限")

    items, total = operation_log_service.list_logs(
        db, user_id=user_id, module=module, action=action, status=status,
        page=page, page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size else 0,
        "items": [OperationLogResponse.model_validate(item) for item in items],
    }
