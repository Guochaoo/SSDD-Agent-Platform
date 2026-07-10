"""
检测场景服务层
处理检测场景（如"钢铁表面缺陷检测"）的创建、查询、更新与删除
对应任务文档步骤 11 的场景部分。
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.entity.db_models import DetectionScene, ModelVersion


class SceneService:
    """检测场景服务"""

    @staticmethod
    def create_scene(
        db: Session,
        name: str,
        display_name: str,
        category: str,
        class_names: list[str],
        description: str | None = None,
        class_names_cn: dict | None = None,
        created_by: int | None = None,
    ) -> DetectionScene:
        if db.query(DetectionScene).filter(DetectionScene.name == name).first():
            raise HTTPException(status_code=400, detail="场景标识已存在")

        scene = DetectionScene(
            name=name,
            display_name=display_name,
            description=description,
            category=category,
            class_names=class_names,
            class_names_cn=class_names_cn,
            created_by=created_by,
        )
        db.add(scene)
        db.commit()
        db.refresh(scene)
        return scene

    @staticmethod
    def get_scene(db: Session, scene_id: int) -> DetectionScene:
        scene = db.query(DetectionScene).filter(DetectionScene.id == scene_id).first()
        if not scene:
            raise HTTPException(status_code=404, detail="检测场景不存在")
        return scene

    @staticmethod
    def list_scenes(db: Session, category: str | None = None, active_only: bool = True) -> list[DetectionScene]:
        query = db.query(DetectionScene)
        if active_only:
            query = query.filter(DetectionScene.is_active.is_(True))
        if category:
            query = query.filter(DetectionScene.category == category)
        return query.order_by(DetectionScene.created_at.desc()).all()

    @staticmethod
    def get_default_model(db: Session, scene_id: int) -> ModelVersion | None:
        """获取某场景当前的默认模型版本，切换检测模型时用"""
        return (
            db.query(ModelVersion)
            .filter(ModelVersion.scene_id == scene_id, ModelVersion.is_default.is_(True), ModelVersion.status == "active")
            .first()
        )

    @staticmethod
    def set_default_model(db: Session, scene_id: int, model_version_id: int) -> ModelVersion:
        """切换某场景的默认模型：先把旧默认取消，再把新的设为默认（同一事务）"""
        model = (
            db.query(ModelVersion)
            .filter(ModelVersion.id == model_version_id, ModelVersion.scene_id == scene_id)
            .first()
        )
        if not model:
            raise HTTPException(status_code=404, detail="模型版本不存在或不属于该场景")

        try:
            db.query(ModelVersion).filter(
                ModelVersion.scene_id == scene_id, ModelVersion.is_default.is_(True)
            ).update({ModelVersion.is_default: False}, synchronize_session=False)
            model.is_default = True
            db.commit()
            db.refresh(model)
            return model
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def deactivate_scene(db: Session, scene_id: int) -> DetectionScene:
        """停用场景（不物理删除，避免破坏历史检测记录的外键引用）"""
        scene = SceneService.get_scene(db, scene_id)
        scene.is_active = False
        db.commit()
        db.refresh(scene)
        return scene


# 全局单例
scene_service = SceneService()
