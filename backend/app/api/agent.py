"""Agent chat API — streaming chat and model listing."""

import time
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.api.auth import get_current_user
from app.config.settings import settings
from app.core.logger import get_logger

router = APIRouter(prefix="/api/agent", tags=["智能体"])
MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}

logger = get_logger(__name__)

# ── in-process cache for model list ──
_model_cache: dict[str, Any] | None = None
_model_cache_ts: float = 0.0
_MODEL_CACHE_TTL: float = 300  # seconds


@router.get("/models")
async def list_models():
    """Fetch available models from the configured LLM provider.

    Calls ``{OPENAI_BASE_URL}/models`` with the configured API key and returns a
    deduplicated, sorted list.  Results are cached for 5 minutes.
    """
    global _model_cache, _model_cache_ts

    now = time.time()
    if _model_cache is not None and (now - _model_cache_ts) < _MODEL_CACHE_TTL:
        return _model_cache

    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="未配置 OPENAI_API_KEY，请在 backend/.env 中设置",
        )

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
        logger.warning("Model list fetch failed — status=%s body=%s", exc.response.status_code, exc.response.text[:500])
        raise HTTPException(
            status_code=502,
            detail=f"获取模型列表失败 (HTTP {exc.response.status_code}): {exc.response.text[:200]}",
        )
    except httpx.HTTPError as exc:
        logger.warning("Model list fetch failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"获取模型列表失败: {exc}",
        )

    raw_models: list[dict] = data.get("data", [])
    seen: set[str] = set()
    models: list[dict] = []
    for m in raw_models:
        model_id: str = m.get("id", "")
        owned_by: str = m.get("owned_by", "unknown")
        if not model_id or model_id in seen:
            continue
        seen.add(model_id)
        models.append({"id": model_id, "owned_by": owned_by})

    # Sort: preferred models first, then alphabetical
    preferred = {"gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-4.1"}
    models.sort(
        key=lambda m: (m["id"] not in preferred, m["id"] not in preferred and m["id"] or m["id"])
    )

    _model_cache = {"models": models, "provider": url}
    _model_cache_ts = now
    return _model_cache


@router.get("/models/cached")
async def cached_models():
    """Return the cached model list without refreshing."""
    if _model_cache is None:
        return {"models": [], "provider": None}
    return _model_cache


@router.post("/chat/stream", status_code=501)
async def stream_agent_chat(
    message: str = Form(""),
    session_id: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    _current_user=Depends(get_current_user),
):
    """Reserve the streaming contract until agent orchestration is implemented."""
    if not message.strip() and image is None:
        raise HTTPException(status_code=422, detail="消息和图片不能同时为空")
    if image is not None:
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=415, detail="仅支持 JPG、JPEG 和 PNG 图片")
        content = await image.read(MAX_IMAGE_BYTES + 1)
        if len(content) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="图片大小不能超过 10MB")
    raise HTTPException(status_code=501, detail="智能体服务尚未接入，当前仅提供接口骨架")
