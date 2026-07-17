"""
对话历史 API 路由
- POST   /api/chat/sessions                       新建会话
- GET    /api/chat/sessions                       会话列表（分页）
- GET    /api/chat/sessions/{session_uuid}        单个会话信息
- PATCH  /api/chat/sessions/{session_uuid}/title  重命名会话
- POST   /api/chat/sessions/{session_uuid}/archive 归档会话
- DELETE /api/chat/sessions/{session_uuid}        硬删除会话（含消息）
- GET    /api/chat/sessions/{session_uuid}/messages  会话消息列表
- GET    /api/chat/sessions/{session_uuid}/history   会话+消息一次性拿

Agent 编排（api/agent.py 里的流式端点）是另一个模块的责任；这里只负责
数据库这一层的会话/消息 CRUD，前端 A/组长在实现 Agent 时调这些接口落库即可。
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.entity.db_models import User
from app.entity.schemas import (
    ChatHistoryResponse, ChatMessageResponse, ChatSessionCreate,
    ChatSessionResponse, PageResponse,
)
from app.services.chat_service import chat_service

router = APIRouter(prefix="/api/chat", tags=["对话历史"])


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
def create_session(
    payload: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """新建会话；title 可以留空，第一条消息发来时会自动填充"""
    session = chat_service.create_session(db, current_user.id, title=payload.title)
    return session


@router.get("/sessions", response_model=PageResponse)
def list_sessions(
    status: Optional[str] = Query(default=None, description="active/archived，默认返回全部"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """会话列表，普通用户只能看自己的，管理员可看全部"""
    items, total = chat_service.list_sessions(
        db, user_id=current_user.id, is_superuser=current_user.is_superuser,
        status=status, page=page, page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size else 0,
        "items": [ChatSessionResponse.model_validate(s) for s in items],
    }


@router.get("/sessions/{session_uuid}", response_model=ChatSessionResponse)
def get_session(
    session_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return chat_service.get_session(db, session_uuid, current_user.id, current_user.is_superuser)


@router.patch("/sessions/{session_uuid}/title", response_model=ChatSessionResponse)
def rename_session(
    session_uuid: str,
    title: str = Query(..., min_length=1, max_length=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return chat_service.rename_session(
        db, session_uuid, current_user.id, title, current_user.is_superuser
    )


@router.post("/sessions/{session_uuid}/archive", response_model=ChatSessionResponse)
def archive_session(
    session_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """归档会话（软删除，仍保留在数据库中）"""
    return chat_service.archive_session(
        db, session_uuid, current_user.id, current_user.is_superuser
    )


@router.delete("/sessions/{session_uuid}")
def delete_session(
    session_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """硬删除会话，同时级联删除所有消息"""
    chat_service.delete_session(
        db, session_uuid, current_user.id, current_user.is_superuser
    )
    return {"message": "会话已删除"}


@router.get("/sessions/{session_uuid}/messages", response_model=list[ChatMessageResponse])
def list_messages(
    session_uuid: str,
    limit: Optional[int] = Query(default=None, ge=1, le=500,
                                    description="只取最近 N 条，Agent 拼上下文时用"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return chat_service.list_messages(
        db, session_uuid, current_user.id, current_user.is_superuser, limit=limit
    )


@router.get("/sessions/{session_uuid}/history", response_model=ChatHistoryResponse)
def get_history(
    session_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """一次性拿到会话 + 全部消息，供前端进入某个历史会话时使用"""
    session, messages = chat_service.get_history(
        db, session_uuid, current_user.id, current_user.is_superuser
    )
    return {"session": session, "messages": messages}
