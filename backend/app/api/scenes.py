"""
检测场景 API 路由
- GET  /api/scenes            场景列表
- GET  /api/scenes/{scene_id} 场景详情
- POST /api/scenes            创建场景（管理员）
- POST /api/scenes/{scene_id}/default-model  切换该场景的默认模型（已登录用户）
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.entity.db_models import ModelVersion, User
from app.entity.schemas import SceneCreate, SceneResponse, ModelVersionBrief, ModelVersionResponse
from app.services.operation_log_service import operation_log_service
from app.services.scene_service import scene_service
from app.services.authorization_service import authorization_service
from app.services.resource_lifecycle_service import resource_lifecycle_service

router = APIRouter(prefix="/api/scenes", tags=["检测场景"])


def _require_permission(db: Session, current_user: User, code: str):
    authorization_service.require_permission(db, current_user, code)


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
    can_read_all = authorization_service.has_permission(db, current_user, "model:read_all")
    return scene_service.list_model_versions(
        db, scene_id, user_id=current_user.id, is_superuser=can_read_all
    )


@router.delete("/{scene_id}/models/{model_version_id}", response_model=ModelVersionResponse)
def delete_scene_model(
    scene_id: int,
    model_version_id: int,
    http_request: Request,
    expected_version: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    can_manage_all = authorization_service.has_permission(db, current_user, "model:manage_all")
    model = scene_service.delete_model_version(
        db, scene_id, model_version_id, current_user.id, can_manage_all, expected_version
    )
    operation_log_service.record(
        db, user=current_user, module="training", action="trash_model",
        target_type="model", target_id=str(model_version_id),
        description=f"模型 {model_version_id} 移入回收站",
        request=http_request,
    )
    return model


@router.post("/{scene_id}/models/{model_version_id}/restore", response_model=ModelVersionResponse)
def restore_scene_model(
    scene_id: int,
    model_version_id: int,
    http_request: Request,
    expected_version: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    can_manage_all = authorization_service.has_permission(db, current_user, "model:manage_all")
    model = scene_service.restore_model_version(
        db, scene_id, model_version_id, current_user.id, can_manage_all, expected_version
    )
    operation_log_service.record(
        db, user=current_user, module="training", action="restore_model",
        target_type="model", target_id=str(model_version_id),
        description=f"模型 {model_version_id} 从回收站恢复",
        request=http_request,
    )
    return model


@router.delete("/{scene_id}/models/{model_version_id}/purge")
def purge_scene_model(
    scene_id: int,
    model_version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    model = db.query(ModelVersion).filter(
        ModelVersion.id == model_version_id,
        ModelVersion.scene_id == scene_id,
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail="模型版本不存在")
    can_manage_all = authorization_service.has_permission(db, current_user, "model:manage_all")
    if model.owner_id != current_user.id and not can_manage_all:
        raise HTTPException(status_code=403, detail="无权彻底删除该模型")
    job = resource_lifecycle_service.purge_model_version(db, model)
    return {"message": "模型已彻底删除", "cleanup_job_id": job.id, "status": job.status}


@router.post("", response_model=SceneResponse, status_code=201)
def create_scene(
    payload: SceneCreate,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建检测场景，需要管理员权限"""
    _require_permission(db, current_user, "scene:manage")
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
    expected_version: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """切换默认模型；需要明确的 RBAC 权限并使用可选乐观锁版本。"""
    _require_permission(db, current_user, "model:set_default")
    can_manage_all = authorization_service.has_permission(db, current_user, "model:manage_all")
    model = scene_service.set_default_model(
        db,
        scene_id,
        model_version_id,
        user_id=current_user.id,
        is_superuser=can_manage_all,
        expected_version=expected_version,
    )
    operation_log_service.record(
        db, user=current_user, module="training", action="set_default_model",
        target_type="model", target_id=str(model_version_id),
        description=f"场景 {scene_id} 默认模型切换为版本 {model_version_id}",
        request=http_request,
    )
    return ModelVersionBrief.model_validate(model)
