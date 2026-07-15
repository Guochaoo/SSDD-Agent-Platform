"""YOLO 图片、视频和摄像头检测 API。"""

import base64
import os
import tempfile
import threading
import time

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.concurrency import run_in_threadpool
from jose import JWTError
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config.detection import (
    ALLOWED_VIDEO_SUFFIXES,
    DEFAULT_CONF_THRESHOLD,
    DEFAULT_IOU_THRESHOLD,
    DEFAULT_VIDEO_FRAME_SAMPLE_RATE,
    DEFAULT_VIDEO_MAX_FRAMES,
    MAX_VIDEO_SIZE,
    MAX_ZIP_SIZE,
    VIDEO_PROGRESS_TTL,
)
from app.core.logger import get_logger
from app.core.redis_client import redis_client
from app.core.security import decode_access_token
from app.database.session import SessionLocal, get_db
from app.entity.schemas import BatchDetectionResponse, DetectionResponse
from app.services.detection_service import detection_service
from app.services.history_service import history_service
from app.services.user_service import user_service

router = APIRouter(prefix="/api/detection", tags=["detection"])
logger = get_logger(__name__)


@router.get("/models/status")
async def detection_model_status():
    return detection_service.warmup_status()

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


@router.post("/zip", response_model=BatchDetectionResponse, summary="ZIP 图片检测")
async def detect_zip(
    file: UploadFile = File(...),
    model_id: int = Form(...),
    conf_threshold: float = Form(DEFAULT_CONF_THRESHOLD, ge=0, le=1),
    iou_threshold: float = Form(DEFAULT_IOU_THRESHOLD, ge=0, le=1),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 ZIP 压缩包")
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = tmp.name
            total_size = 0
            while chunk := await file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > MAX_ZIP_SIZE:
                    raise HTTPException(status_code=400, detail="ZIP 文件不能超过 50 MB")
                tmp.write(chunk)
        if total_size == 0:
            raise HTTPException(status_code=400, detail="上传 ZIP 为空")
        return await detection_service.detect_zip(
            db,
            current_user.id,
            tmp_path,
            model_id,
            conf_threshold,
            iou_threshold,
            file.filename,
        )
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass


@router.post("/video", summary="视频检测")
async def detect_video(
    file: UploadFile = File(...),
    model_id: int = Form(...),
    conf_threshold: float = Form(DEFAULT_CONF_THRESHOLD, ge=0, le=1),
    iou_threshold: float = Form(DEFAULT_IOU_THRESHOLD, ge=0, le=1),
    frame_sample_rate: int = Form(DEFAULT_VIDEO_FRAME_SAMPLE_RATE, ge=1, le=60),
    max_frames: int = Form(DEFAULT_VIDEO_MAX_FRAMES, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in ALLOWED_VIDEO_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的视频格式: {suffix or '无扩展名'}",
        )
    model_version = detection_service._resolve_model(db, model_id)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            total_size = 0
            while chunk := await file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > MAX_VIDEO_SIZE:
                    raise HTTPException(status_code=400, detail="视频文件不能超过 50 MB")
                tmp.write(chunk)
        if total_size == 0:
            raise HTTPException(status_code=400, detail="上传视频为空")
    except Exception:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
        raise

    task = history_service.create_task(
        db,
        user_id=current_user.id,
        scene_id=model_version.scene_id,
        task_type="video",
        model_version_id=model_version.id,
        conf_threshold=conf_threshold,
        iou_threshold=iou_threshold,
    )
    history_service.mark_processing(db, task.id)
    task_id = task.id
    model_version_id = model_version.id
    redis_client.set_video_task(
        task_id,
        {"status": "processing", "progress": 0, "message": "视频处理中..."},
        ttl=VIDEO_PROGRESS_TTL,
    )

    def update_progress(current_frame, total_frames):
        redis_client.set_video_task(
            task_id,
            {
                "status": "processing",
                "progress": round(current_frame / total_frames * 100, 2),
                "current_frame": current_frame,
                "total_frames": total_frames,
                "message": "视频处理中...",
            },
            ttl=VIDEO_PROGRESS_TTL,
        )

    def run_video_detection():
        try:
            result = detection_service.detect_video(
                video_path=tmp_path,
                model_id=model_version_id,
                task_id=task_id,
                conf=conf_threshold,
                iou=iou_threshold,
                frame_sample_rate=frame_sample_rate,
                max_frames=max_frames,
                progress_callback=update_progress,
            )
            redis_client.set_video_task(
                task_id,
                {
                    "status": "completed",
                    "progress": 100,
                    "message": f"检测完成，共处理 {result['processed_frames']} 个关键帧",
                    "result": result,
                },
                ttl=VIDEO_PROGRESS_TTL,
            )
        except Exception as exc:
            redis_client.set_video_task(
                task_id,
                {"status": "failed", "progress": 0, "message": f"视频检测失败: {exc}"},
                ttl=VIDEO_PROGRESS_TTL,
            )
        finally:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass

    threading.Thread(target=run_video_detection, daemon=True).start()
    logger.info(
        "视频任务已创建 task_id=%s user_id=%s filename=%s size=%s",
        task_id, current_user.id, file.filename, total_size,
    )
    return {
        "task_id": task_id,
        "status": "processing",
        "message": "视频已上传，正在后台处理中",
        "filename": file.filename,
    }


@router.get("/video/status/{task_id}", summary="查询视频检测进度")
async def get_video_status(
    task_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = history_service.get_task_detail(
        db, task_id, current_user.id, current_user.is_superuser
    )
    if task.task_type != "video":
        raise HTTPException(status_code=400, detail="该任务不是视频检测任务")
    progress = redis_client.get_video_task(task_id)
    if progress:
        return {"task_id": task_id, **progress}
    return {
        "task_id": task.id,
        "status": task.status,
        "progress": 100 if task.status == "completed" else 0,
        "message": task.error_message or task.status,
        "task_type": task.task_type,
        "total_images": task.total_images,
        "total_objects": task.total_objects,
        "total_inference_time": task.total_inference_time,
    }


def _get_websocket_user(token: str | None, db: Session):
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        return None
    try:
        return user_service.get_user_by_id(db, user_id)
    except HTTPException:
        return None


@router.websocket("/camera")
async def camera_detection(websocket: WebSocket):
    db = SessionLocal()
    user = _get_websocket_user(websocket.query_params.get("token"), db)
    if not user:
        await websocket.close(code=1008, reason="无效的认证凭据")
        db.close()
        return
    await websocket.accept()
    connection_id = id(websocket)
    mode = "cpu"
    conf = DEFAULT_CONF_THRESHOLD
    iou = DEFAULT_IOU_THRESHOLD
    model_version = None
    model = None
    frame_count = 0
    fps_window_started = time.perf_counter()
    fps_window_count = 0
    current_fps = 0.0
    last_frame_time = 0.0
    logger.info("摄像头连接建立 connection_id=%s user_id=%s", connection_id, user.id)
    try:
        while True:
            message = await websocket.receive_json()
            message_type = message.get("type")
            if message_type == "config":
                mode = message.get("mode", "cpu")
                if mode not in {"cpu", "gpu"}:
                    await websocket.send_json({"type": "error", "message": "mode 必须是 cpu 或 gpu"})
                    continue
                conf = float(message.get("conf", DEFAULT_CONF_THRESHOLD))
                iou = float(message.get("iou", DEFAULT_IOU_THRESHOLD))
                if not 0 <= conf <= 1 or not 0 <= iou <= 1:
                    await websocket.send_json({"type": "error", "message": "conf 和 iou 必须在 0-1 之间"})
                    continue
                try:
                    model_id = int(message.get("model_id"))
                    model_version, model = await run_in_threadpool(
                        detection_service.warmup_camera, db, model_id, mode, conf, iou
                    )
                except Exception as exc:
                    logger.exception("摄像头模型初始化失败 connection_id=%s", connection_id)
                    await websocket.send_json({"type": "error", "message": f"模型加载失败: {exc}"})
                    continue
                await websocket.send_json(
                    {
                        "type": "config_ok",
                        "mode": mode,
                        "model_id": model_version.id,
                        "model_name": model_version.model_name,
                        "model_path": model_version.model_path,
                        "message": f"配置成功，模式: {mode}，模型: {model_version.model_name}",
                    }
                )
            elif message_type == "frame":
                if model is None:
                    await websocket.send_json({"type": "error", "message": "请先发送 config 消息"})
                    continue
                now = time.perf_counter()
                if mode == "cpu" and now - last_frame_time < 0.3:
                    await websocket.send_json({"type": "frame_skipped", "retry_after_ms": 300})
                    continue
                last_frame_time = now
                try:
                    import cv2
                    import numpy as np

                    frame_bytes = base64.b64decode(message.get("data", ""), validate=True)
                    frame = cv2.imdecode(np.frombuffer(frame_bytes, np.uint8), cv2.IMREAD_COLOR)
                    if frame is None:
                        raise ValueError("无法解码摄像头帧")
                    result = await run_in_threadpool(
                        detection_service.detect_camera_frame,
                        model_version, model, frame, mode, conf, iou,
                    )
                    frame_count += 1
                    fps_window_count += 1
                    elapsed = now - fps_window_started
                    if elapsed >= 1:
                        current_fps = fps_window_count / elapsed
                        fps_window_count = 0
                        fps_window_started = now
                    await websocket.send_json(
                        {
                            "type": "result",
                            **result,
                            "fps": round(current_fps, 1),
                            "frame_count": frame_count,
                        }
                    )
                except Exception as exc:
                    logger.warning("摄像头帧处理失败 connection_id=%s error=%s", connection_id, exc)
                    await websocket.send_json({"type": "error", "message": f"帧处理失败: {exc}"})
            elif message_type == "close":
                await websocket.close(code=1000, reason="Client requested close")
                break
            else:
                await websocket.send_json({"type": "error", "message": "未知消息类型"})
    except WebSocketDisconnect as exc:
        logger.info(
            "摄像头 WebSocket 断开 connection_id=%s code=%s reason=%s",
            connection_id,
            exc.code,
            exc.reason,
        )
    finally:
        db.close()
        logger.info("摄像头连接关闭 connection_id=%s frames=%s", connection_id, frame_count)
