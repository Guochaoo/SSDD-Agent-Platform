"""
检测场景 API 路由
- GET  /api/scenes            场景列表
- GET  /api/scenes/{scene_id} 场景详情
- POST /api/scenes            创建场景（管理员）
- POST /api/scenes/{scene_id}/default-model  切换该场景的默认模型（已登录用户）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.entity.db_models import User
from app.entity.schemas import SceneCreate, SceneResponse, ModelVersionBrief, ModelVersionResponse
from app.services.scene_service import scene_service

router = APIRouter(prefix="/api/scenes", tags=["检测场景"])


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
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List every non-deleted model version that can be inspected or selected."""
    return scene_service.list_model_versions(db, scene_id)


@router.post("", response_model=SceneResponse, status_code=201)
def create_scene(
    payload: SceneCreate,
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
    return _scene_to_response(db, scene)


@router.post("/{scene_id}/default-model")
def set_default_model(
    scene_id: int,
    model_version_id: int,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """切换某场景的默认模型版本，所有已登录用户均可操作。"""
    model = scene_service.set_default_model(db, scene_id, model_version_id)
    return ModelVersionBrief.model_validate(model)
