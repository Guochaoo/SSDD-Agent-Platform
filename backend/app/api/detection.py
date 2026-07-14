"""YOLO 单图与批量检测 API。"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config.detection import DEFAULT_CONF_THRESHOLD, DEFAULT_IOU_THRESHOLD
from app.database.session import get_db
from app.entity.schemas import BatchDetectionResponse, DetectionResponse
from app.services.detection_service import detection_service


router = APIRouter(prefix="/api/detection", tags=["detection"])


@router.post("/single", response_model=DetectionResponse)
async def detect_single(
    file: UploadFile = File(...),
    model_id: int = Form(...),
    conf_threshold: float = Form(DEFAULT_CONF_THRESHOLD, ge=0, le=1),
    iou_threshold: float = Form(DEFAULT_IOU_THRESHOLD, ge=0, le=1),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await detection_service.detect_single(
        db, current_user.id, file, model_id, conf_threshold, iou_threshold
    )


@router.post("/batch", response_model=BatchDetectionResponse)
async def detect_batch(
    files: list[UploadFile] = File(...),
    model_id: int = Form(...),
    conf_threshold: float = Form(DEFAULT_CONF_THRESHOLD, ge=0, le=1),
    iou_threshold: float = Form(DEFAULT_IOU_THRESHOLD, ge=0, le=1),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await detection_service.detect_batch(
        db, current_user.id, files, model_id, conf_threshold, iou_threshold
    )
