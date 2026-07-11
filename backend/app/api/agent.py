"""Agent chat API contract.

The orchestration, detection tool and RAG integration are intentionally left for
the next implementation phase. This endpoint validates the request boundary so
the frontend can be integrated without pretending that a backend agent exists.
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.auth import get_current_user

router = APIRouter(prefix="/api/agent", tags=["智能体"])
MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}


@router.post("/chat/stream", status_code=501)
async def stream_agent_chat(
    message: str = Form(""),
    session_id: str | None = Form(None),
    image: UploadFile | None = File(None),
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
