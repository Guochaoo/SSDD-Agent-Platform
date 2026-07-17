"""
检测场景 API 路由
- GET  /api/scenes            场景列表
- GET  /api/scenes/{scene_id} 场景详情
- POST /api/scenes            创建场景（管理员）
- POST /api/scenes/{scene_id}/default-model  切换该场景的默认模型（已登录用户）
"""
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.entity.db_models import User
from app.entity.schemas import SceneCreate, SceneResponse, ModelVersionBrief, ModelVersionResponse
from app.services.operation_log_service import operation_log_service
from app.services.scene_service import scene_service
from app.storage.minio_client import MinIOClient

router = APIRouter(prefix="/api/scenes", tags=["检测场景"])
MAX_MODEL_UPLOAD_BYTES = 1024 * 1024 * 1024


def _require_admin(current_user: User):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="需要管理员权限")


def _scene_to_response(db: Session, scene) -> SceneResponse:
    default_model = scene_service.get_default_model(db, scene.id)
    data = SceneResponse.model_validate(scene)
    data.default_model = ModelVersionBrief.model_validate(default_model) if default_model else None
    return data


@router.get("", response_model=list[SceneResponse])
def list_scenes(
    category: str | None = None,
    db: Session = Depends(get_db),
):
    """场景列表（登录与未登录都可查看，前端选择检测场景时用）"""
    scenes = scene_service.list_scenes(db, category=category)
    return [_scene_to_response(db, s) for s in scenes]


@router.get("/{scene_id}", response_model=SceneResponse)
def get_scene(scene_id: int, db: Session = Depends(get_db)):
    scene = scene_service.get_scene(db, scene_id)
    return _scene_to_response(db, scene)


@router.get("/{scene_id}/models", response_model=list[ModelVersionResponse])
def list_scene_models(
    scene_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List every non-deleted model version that can be inspected or selected."""
    return scene_service.list_model_versions(db, scene_id, current_user.id, current_user.is_superuser)


@router.post("/{scene_id}/models/upload", response_model=ModelVersionResponse, status_code=201)
async def upload_model_version(
    scene_id: int,
    file: UploadFile = File(...),
    version: str = Form(...),
    model_name: str = Form(...),
    model_type: str = Form("yolo11n"),
    description: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix != ".pt":
        raise HTTPException(status_code=400, detail="仅支持上传 .pt 模型文件")
    project_root = Path(__file__).resolve().parents[3]
    target_dir = project_root / "models" / "users" / str(current_user.id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{uuid4().hex}{suffix}"
    object_key = f"models/users/{current_user.id}/{uuid4().hex}.pt"
    try:
        size = 0
        with target.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_MODEL_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="model file exceeds 1 GB")
                output.write(chunk)
        minio_url = MinIOClient().upload_file(object_key, str(target))
        return scene_service.create_uploaded_model(
            db, scene_id, current_user.id, version.strip(), model_name.strip(), model_type.strip(),
            str(target.relative_to(project_root)), size, description, object_key, minio_url,
        )
    except HTTPException:
        target.unlink(missing_ok=True)
        raise
    except Exception:
        target.unlink(missing_ok=True)
        try:
            MinIOClient().delete_file(object_key)
        except Exception:
            pass
        raise


@router.patch("/{scene_id}/models/{model_version_id}", response_model=ModelVersionResponse)
def update_model_version(
    scene_id: int,
    model_version_id: int,
    version: str | None = Form(None),
    model_name: str | None = Form(None),
    description: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return scene_service.update_model_version(
        db, scene_id, model_version_id, current_user.id, current_user.is_superuser,
        description, version, model_name,
    )


@router.get("/{scene_id}/models/{model_version_id}/download")
def download_model_version(
    scene_id: int,
    model_version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    model = scene_service.get_model_version(
        db, scene_id, model_version_id, current_user.id, current_user.is_superuser
    )
    model_path = Path(model.model_path)
    if not model_path.is_absolute():
        model_path = Path(__file__).resolve().parents[3] / model_path
    if model_path.is_file():
        return FileResponse(path=model_path, media_type="application/octet-stream", filename=model_path.name)
    if model.minio_url:
        return RedirectResponse(url=model.minio_url)
    raise HTTPException(status_code=404, detail="模型文件不存在")


@router.post("", response_model=SceneResponse, status_code=201)
def create_scene(
    payload: SceneCreate,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建检测场景，需要管理员权限"""
    _require_admin(current_user)
    scene = scene_service.create_scene(
        db,
        name=payload.name,
        display_name=payload.display_name,
        category=payload.category,
        class_names=payload.class_names,
        description=payload.description,
        class_names_cn=payload.class_names_cn,
        created_by=current_user.id,
    )
    operation_log_service.record(
        db, user=current_user, module="detection", action="create_scene",
        target_type="scene", target_id=str(scene.id),
        description=f"创建检测场景：{scene.name}", request=http_request,
    )
    return _scene_to_response(db, scene)


@router.post("/{scene_id}/default-model")
def set_default_model(
    scene_id: int,
    model_version_id: int,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """切换某场景的默认模型版本，所有已登录用户均可操作。"""
    model = scene_service.set_default_model(db, scene_id, model_version_id)
    operation_log_service.record(
        db, user=current_user, module="training", action="set_default_model",
        target_type="model", target_id=str(model_version_id),
        description=f"场景 {scene_id} 默认模型切换为版本 {model_version_id}",
        request=http_request,
    )
    return ModelVersionBrief.model_validate(model)


@router.delete("/{scene_id}/models/{model_version_id}")
def delete_model_version(
    scene_id: int,
    model_version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    model = scene_service.delete_model_version(
        db, scene_id, model_version_id, current_user.id, current_user.is_superuser
    )
    return {"id": model.id, "status": model.status}
