"""YOLO 单图、批量与 ZIP 检测 API。"""

import json
import os
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config.detection import DEFAULT_CONF_THRESHOLD, DEFAULT_IOU_THRESHOLD
from app.database.session import get_db
from app.entity.schemas import BatchDetectionResponse, DetectionResponse
from app.services.detection_service import detection_service

router = APIRouter(prefix="/api/detection", tags=["detection"])

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}


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


@router.post("/zip")
async def detect_zip(
    file: UploadFile = File(...),
    model_id: int = Form(...),
    conf_threshold: float = Form(DEFAULT_CONF_THRESHOLD, ge=0, le=1),
    iou_threshold: float = Form(DEFAULT_IOU_THRESHOLD, ge=0, le=1),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ZIP 解压 + 批量检测。单张图片的检测复用 /single 逻辑。"""
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 .zip 文件")

    temp_dir = tempfile.mkdtemp(prefix="rsod_zip_detect_")
    try:
        content = await file.read(100 * 1024 * 1024)  # 100 MB limit
        zip_path = os.path.join(temp_dir, file.filename)
        with open(zip_path, "wb") as f:
            f.write(content)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(temp_dir)

        image_files = []
        for root, _, filenames in os.walk(temp_dir):
            for fname in filenames:
                if Path(fname).suffix.lower() in IMAGE_EXTENSIONS:
                    image_files.append(os.path.join(root, fname))

        if not image_files:
            raise HTTPException(status_code=400, detail="ZIP 文件中未找到图片")

        from concurrent.futures import ThreadPoolExecutor

        results = []
        total_objects = 0

        def _detect_one(img_path):
            with open(img_path, "rb") as fh:
                from io import BytesIO
                fake_file = UploadFile(filename=Path(img_path).name, file=BytesIO(fh.read()))
                import asyncio as _asyncio
                loop = _asyncio.new_event_loop()
                _asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        detection_service.detect_single(db, current_user.id, fake_file, model_id, conf_threshold, iou_threshold)
                    )
                finally:
                    loop.close()

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(_detect_one, image_files))

        total_objects = sum(
            (r.total_objects if hasattr(r, "total_objects") else r.get("total_objects", 0))
            for r in results
        )

        return {
            "status": "completed",
            "total_images": len(image_files),
            "total_objects": total_objects,
            "items": [
                {"file_name": Path(img).name, "result": r}
                for img, r in zip(image_files, results)
            ],
        }
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="无效的 ZIP 文件")
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
