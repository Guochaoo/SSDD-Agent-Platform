"""Agent chat API — streaming chat, model listing, and image upload."""

import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.agent.supervisor import supervisor_agent
from app.api.auth import get_current_user
from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import SessionLocal, get_db
from app.entity.db_models import ChatMessage, ChatSession

router = APIRouter(prefix="/api/agent", tags=["智能体"])
MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/bmp", "image/tiff", "image/webp"}

logger = get_logger(__name__)
MAX_HISTORY_MESSAGES = 20

# ── in-process cache for model list ──
_model_cache: dict[str, Any] | None = None
_model_cache_ts: float = 0.0
_MODEL_CACHE_TTL: float = 300

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "rsod_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════
# Model listing
# ══════════════════════════════════════════════════════════════

@router.get("/models")
async def list_models():
    global _model_cache, _model_cache_ts
    now = time.time()
    if _model_cache is not None and (now - _model_cache_ts) < _MODEL_CACHE_TTL:
        return _model_cache

    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="未配置 OPENAI_API_KEY")

    url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="获取模型列表超时")
    except httpx.HTTPStatusError as exc:
        logger.warning("Model list fetch failed — status=%s", exc.response.status_code)
        raise HTTPException(status_code=502, detail=f"获取模型列表失败 (HTTP {exc.response.status_code})")
    except httpx.HTTPError as exc:
        logger.warning("Model list fetch failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"获取模型列表失败: {exc}")

    raw_models: list[dict] = data.get("data", [])
    seen: set[str] = set()
    models: list[dict] = []
    for m in raw_models:
        mid = m.get("id", "")
        if not mid or mid in seen:
            continue
        seen.add(mid)
        models.append({"id": mid, "owned_by": m.get("owned_by", "unknown")})

    preferred = {"qwen3.7-plus", "qwen-plus", "qwen-max", "deepseek-v4-pro"}
    models.sort(key=lambda m: (m["id"] not in preferred, m["id"]))

    _model_cache = {"models": models, "provider": url}
    _model_cache_ts = now
    return _model_cache


@router.get("/models/cached")
async def cached_models():
    if _model_cache is None:
        return {"models": [], "provider": None}
    return _model_cache


@router.get("/sessions")
def list_chat_sessions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return only the authenticated user's chat sessions."""
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.last_message_at.desc(), ChatSession.created_at.desc())
        .all()
    )
    return [
        {
            "id": session.session_uuid,
            "title": session.title or "新对话",
            "message_count": session.message_count or 0,
            "created_at": session.created_at,
            "updated_at": session.last_message_at or session.created_at,
        }
        for session in sessions
    ]


@router.get("/sessions/{session_id}")
def get_chat_session(
    session_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return a session and messages only when it belongs to the current user."""
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.session_uuid == session_id,
            ChatSession.user_id == current_user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )
    return {
        "id": session.session_uuid,
        "title": session.title or "新对话",
        "message_count": session.message_count or 0,
        "created_at": session.created_at,
        "updated_at": session.last_message_at or session.created_at,
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "has_image": bool(message.image_path),
                "image_url": f"/api/agent/sessions/{session_id}/messages/{message.id}/image" if message.image_path else None,
                "tool_calls": message.tool_calls or [],
                "created_at": message.created_at,
            }
            for message in messages
        ],
    }


@router.get("/sessions/{session_id}/messages/{message_id}/image")
def get_chat_message_image(
    session_id: str,
    message_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Serve a persisted chat attachment only to the session owner."""
    message = (
        db.query(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .filter(
            ChatSession.session_uuid == session_id,
            ChatSession.user_id == current_user.id,
            ChatMessage.id == message_id,
        )
        .first()
    )
    if not message or not message.image_path:
        raise HTTPException(status_code=404, detail="图片不存在")
    image_path = _validate_uploaded_image_path(message.image_path)
    return FileResponse(image_path)


@router.delete("/sessions/{session_id}")
def delete_chat_session(
    session_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete one of the current user's persisted chat sessions and messages."""
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.session_uuid == session_id,
            ChatSession.user_id == current_user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    image_paths = [path for (path,) in db.query(ChatMessage.image_path).filter(
        ChatMessage.session_id == session.id,
        ChatMessage.image_path.isnot(None),
    ).all()]
    db.query(ChatMessage).filter(ChatMessage.session_id == session.id).delete(
        synchronize_session=False
    )
    db.delete(session)
    db.commit()

    for image_path in image_paths:
        try:
            os.unlink(_validate_uploaded_image_path(image_path))
        except (FileNotFoundError, HTTPException, OSError):
            pass
    return {"id": session_id, "message": "会话已删除"}


# ══════════════════════════════════════════════════════════════
# Image upload
# ══════════════════════════════════════════════════════════════

@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    _current_user=Depends(get_current_user),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="仅支持图片文件")
    suffix = Path(file.filename).suffix.lower() or ".jpg"
    filename = f"{os.getpid()}_{uuid4().hex}{suffix}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="图片不能为空")
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="图片大小不能超过 10MB")
    with open(filepath, "wb") as f:
        f.write(content)
    logger.info("图片上传成功: %s → %s", file.filename, filepath)
    return {"image_path": filepath}


# ══════════════════════════════════════════════════════════════
# SSE streaming chat
# ══════════════════════════════════════════════════════════════

@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    _current_user=Depends(get_current_user),
):
    """SSE 流式对话 — Agent 智能回复。

    支持两种请求格式：
    - FormData: message, session_id, model (前端 uses FormData)
    - JSON: {"message": "...", "image_path": "..."}
    """
    content_type = request.headers.get("content-type", "")

    message = ""
    image_paths = []
    image_path = None
    model = None
    session_id = None

    if "multipart/form-data" in content_type:
        form = await request.form()
        message = form.get("message", "")
        if isinstance(message, str):
            message = message.strip()
        raw_model = form.get("model")
        if raw_model and isinstance(raw_model, str) and raw_model.strip():
            model = raw_model.strip()
        raw_session = form.get("session_id")
        if raw_session and isinstance(raw_session, str) and raw_session.strip():
            session_id = raw_session.strip()
        image_paths = []
        image_files = form.getlist("image")
        for image_file in image_files:
            if image_file is not None and hasattr(image_file, "filename") and image_file.filename:
                if image_file.content_type not in ALLOWED_IMAGE_TYPES and image_file.content_type:
                    raise HTTPException(status_code=415, detail="仅支持 JPG、PNG、BMP、TIFF、WebP 图片")
                content = await image_file.read(MAX_IMAGE_BYTES + 1)
                if len(content) > MAX_IMAGE_BYTES:
                    raise HTTPException(status_code=413, detail="图片大小不能超过 10MB")
                suffix = Path(image_file.filename).suffix.lower() or ".jpg"
                filename = f"{os.getpid()}_{uuid4().hex}{suffix}"
                filepath = os.path.join(UPLOAD_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(content)
                image_paths.append(filepath)
        if image_paths:
            image_path = image_paths[0]
    else:
        body = await request.json()
        message = (body.get("message") or "").strip()
        raw_session = body.get("session_id")
        if raw_session and isinstance(raw_session, str) and raw_session.strip():
            session_id = raw_session.strip()
        raw_image_path = body.get("image_path")
        if raw_image_path:
            image_paths = [_validate_uploaded_image_path(raw_image_path)]

    if not message and not image_paths:
        raise HTTPException(status_code=422, detail="消息不能为空")

    logger.info("Agent chat: message=%s images=%d model=%s session=%s", message[:80], len(image_paths), model or "default", session_id or "new")

    user_id = _current_user.id

    # ── load chat history ──
    history = _load_history(session_id, user_id) if session_id else []

    async def event_generator():
        full_reply = ""
        tool_calls = []
        try:
            async for event in supervisor_agent.chat_stream(
                message=message, image_paths=image_paths or None, model=model, chat_history=history, user_id=user_id
            ):
                if event.get("type") == "text_chunk":
                    full_reply += event.get("content", "")
                event_type = event.get("type", "")
                if event_type == "text_chunk":
                    yield f"data: {json.dumps({'type': 'text_delta', 'content': event['content']}, ensure_ascii=False)}\n\n"
                elif event_type == "agent_switch":
                    yield f"data: {json.dumps({'type': 'agent_switch', 'agent': event['agent'], 'label': event['label']}, ensure_ascii=False)}\n\n"
                elif event_type == "tool_call":
                    tool_calls.append({"name": event["tool"], "status": "running", "input": event.get("input", {})})
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool_name': event['tool'], 'input': event.get('input', {}), 'agent': event.get('agent', '')}, ensure_ascii=False)}\n\n"
                elif event_type == "tool_result":
                    for tool_call in reversed(tool_calls):
                        if tool_call["name"] == event["tool"]:
                            tool_call.update({"status": "success", "result": event["result"]})
                            break
                    yield f"data: {json.dumps({'type': 'tool_result', 'tool_name': event['tool'], 'result': event['result'], 'agent': event.get('agent', '')}, ensure_ascii=False)}\n\n"
                elif event_type == "error":
                    yield f"data: {json.dumps({'type': 'error', 'message': event['content']}, ensure_ascii=False)}\n\n"

            # ── save to history ──
            if session_id and (message or full_reply):
                _save_message(session_id, user_id, "user", message, image_path=image_path)
                _save_message(session_id, user_id, "assistant", full_reply, tool_calls=tool_calls)

            yield f"data: {json.dumps({'type': 'message_end'})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as exc:
            logger.exception("SSE 流异常")
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ══════════════════════════════════════════════════════════════
# Session history helpers
# ══════════════════════════════════════════════════════════════

def _ensure_session(session_id: str, user_id: int):
    db = SessionLocal()
    try:
        s = db.query(ChatSession).filter(ChatSession.session_uuid == session_id).first()
        if not s:
            s = ChatSession(session_uuid=session_id, user_id=user_id, title="")
            db.add(s)
            db.commit()
            db.refresh(s)
        return s
    finally:
        db.close()


def _validate_uploaded_image_path(image_path: str) -> str:
    if not isinstance(image_path, str) or not image_path.strip():
        raise HTTPException(status_code=400, detail="图片路径无效")
    candidate = Path(image_path).resolve()
    upload_root = Path(UPLOAD_DIR).resolve()
    try:
        candidate.relative_to(upload_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="图片路径无效") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=400, detail="图片文件不存在")
    return str(candidate)


def _load_history(session_id: str, user_id: int | None = None) -> list[dict]:
    """加载最近的对话历史，转为 LangChain 消息格式"""
    db = SessionLocal()
    try:
        query = db.query(ChatSession).filter(ChatSession.session_uuid == session_id)
        if user_id is not None:
            query = query.filter(ChatSession.user_id == user_id)
        s = query.first()
        if not s:
            return []
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == s.id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(MAX_HISTORY_MESSAGES)
            .all()
        )
        messages.reverse()
        history = []
        for m in messages:
            if m.role in ("user", "assistant"):
                content = m.content or ""
                if m.role == "user" and m.image_path:
                    try:
                        image_path = _validate_uploaded_image_path(m.image_path)
                    except HTTPException:
                        image_path = None
                    if image_path:
                        content = f"{content}\n[附件图片路径: {image_path}]"
                history.append({"role": m.role, "content": content})
        return history
    finally:
        db.close()


def _save_message(
    session_id: str,
    user_id: int,
    role: str,
    content: str,
    image_path: str | None = None,
    tool_calls: list[dict] | None = None,
):
    if not content and not image_path:
        return
    db = SessionLocal()
    try:
        s = db.query(ChatSession).filter(
            ChatSession.session_uuid == session_id,
            ChatSession.user_id == user_id,
        ).first()
        if not s:
            s = ChatSession(session_uuid=session_id, user_id=user_id, title="")
            db.add(s)
            db.flush()
        db.add(ChatMessage(session_id=s.id, role=role, content=content, image_path=image_path, tool_calls=tool_calls))
        s.message_count = (s.message_count or 0) + 1
        s.last_message_at = datetime.now()
        if role == "user" and (not s.title or s.title == ""):
            s.title = (content or "图片消息")[:50]
        db.commit()
    finally:
        db.close()
