"""Detection API contract placeholders.

The frontend can use these stable routes while inference-service integration is
developed.  They deliberately return 501 instead of a misleading 404.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.auth import get_current_user


router = APIRouter(prefix="/api/detection", tags=["detection"])


def _not_implemented() -> None:
    raise HTTPException(
        status_code=501,
        detail="Detection inference service has not been integrated yet.",
    )


@router.post("/single")
async def detect_single(
    file: UploadFile = File(...),
    model_id: int = Form(...),
    conf_threshold: float = Form(0.25),
    iou_threshold: float = Form(0.45),
    _current_user=Depends(get_current_user),
):
    _not_implemented()


@router.post("/batch")
async def detect_batch(
    files: list[UploadFile] = File(...),
    model_id: int = Form(...),
    conf_threshold: float = Form(0.25),
    iou_threshold: float = Form(0.45),
    _current_user=Depends(get_current_user),
):
    _not_implemented()
