"""
初始化种子数据
- 创建系统内置角色（admin/operator/viewer）与基础权限
- 创建默认管理员账号
- 创建本项目的检测场景（钢铁表面缺陷检测 / NEU-CLS）

执行方式（backend 目录下）：
    python -m app.database.seed
可重复执行：已存在的数据不会重复插入。
"""
from pathlib import Path

from app.database.session import SessionLocal
from app.entity.db_models import (
    DetectionScene,
    ModelVersion,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.core.security import hash_password

DEFAULT_PERMISSIONS = [
    ("detection:task:create", "创建检测任务", "detection"),
    ("detection:task:read", "查看检测任务", "detection"),
    ("detection:task:delete", "删除检测任务", "detection"),
    ("training:task:create", "创建训练任务", "training"),
    ("training:task:read", "查看训练任务", "training"),
    ("model:manage", "管理模型版本", "training"),
    ("agent:chat", "使用智能体对话", "agent"),
    ("system:manage", "系统管理", "system"),
]

DEFAULT_ROLES = {
    "admin": ("管理员", [code for code, _, _ in DEFAULT_PERMISSIONS]),
    "operator": (
        "操作员",
        ["detection:task:create", "detection:task:read", "training:task:create", "training:task:read", "agent:chat"],
    ),
    "viewer": ("访客", ["detection:task:read", "training:task:read"]),
}

# NEU-CLS 六类钢铁表面缺陷
NEU_CLS_CLASSES = ["crazing", "inclusion", "patches", "pitted", "rolled", "scratches"]
NEU_CLS_CLASSES_CN = {
    "crazing": "裂纹",
    "inclusion": "夹杂",
    "patches": "斑块",
    "pitted": "点蚀",
    "rolled": "氧化皮压入",
    "scratches": "划痕",
}


def seed_permissions(db) -> dict[str, Permission]:
    existing_codes = {p.code for p in db.query(Permission).all()}
    for code, name, module in DEFAULT_PERMISSIONS:
        if code not in existing_codes:
            db.add(Permission(code=code, name=name, module=module))
    db.commit()
    return {p.code: p for p in db.query(Permission).all()}


def seed_roles(db, permissions: dict[str, Permission]) -> dict[str, Role]:
    existing = {r.name: r for r in db.query(Role).all()}
    for name, (display_name, perm_codes) in DEFAULT_ROLES.items():
        role = existing.get(name)
        if not role:
            role = Role(name=name, display_name=display_name, is_system=True)
            db.add(role)
            db.flush()
            existing[name] = role

        current_codes = {rp.permission.code for rp in role.role_permissions}
        for code in perm_codes:
            if code not in current_codes and code in permissions:
                db.add(RolePermission(role_id=role.id, permission_id=permissions[code].id))
    db.commit()
    return {r.name: r for r in db.query(Role).all()}


def seed_admin_user(db, roles: dict[str, Role]) -> User:
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=hash_password("Admin@123456"),
            is_superuser=True,
        )
        db.add(admin)
        db.flush()
        print("[seed] 创建默认管理员：用户名 admin / 密码 Admin@123456 —— 首次登录后请立即修改密码")

    if "admin" in roles:
        has_role = (
            db.query(UserRole)
            .filter(UserRole.user_id == admin.id, UserRole.role_id == roles["admin"].id)
            .first()
        )
        if not has_role:
            db.add(UserRole(user_id=admin.id, role_id=roles["admin"].id))

    db.commit()
    return admin


def seed_detection_scenes(db, admin_user_id: int | None) -> None:
    existing = db.query(DetectionScene).filter(DetectionScene.name == "steel_surface_defect").first()
    if not existing:
        scene = DetectionScene(
            name="steel_surface_defect",
            display_name="钢铁表面缺陷检测",
            description="基于 NEU-CLS 数据集的钢铁表面缺陷检测场景",
            category="industry",
            class_names=NEU_CLS_CLASSES,
            class_names_cn=NEU_CLS_CLASSES_CN,
            created_by=admin_user_id,
        )
        db.add(scene)
        db.commit()
        print("[seed] 创建默认检测场景：steel_surface_defect（NEU-CLS 六类缺陷）")

    scene = existing or scene
    if scene.class_names != NEU_CLS_CLASSES or scene.class_names_cn != NEU_CLS_CLASSES_CN:
        scene.class_names = NEU_CLS_CLASSES
        scene.class_names_cn = NEU_CLS_CLASSES_CN
        db.commit()
        print("[seed] 同步检测场景类别字典到部署模型")
    model_path = "models/steel_surface_defect_v1.0.0/ssdd_yolo11n_v1.pt"
    absolute_model_path = Path(__file__).resolve().parents[3] / model_path
    model = (
        db.query(ModelVersion)
        .filter(ModelVersion.scene_id == scene.id, ModelVersion.version == "v1.0.0")
        .first()
    )
    if not model:
        model = ModelVersion(
            scene_id=scene.id,
            version="v1.0.0",
            model_name="ssdd_yolo11n_v1",
            model_type="yolo11n",
            model_path=model_path,
            file_size=absolute_model_path.stat().st_size if absolute_model_path.is_file() else None,
            is_default=True,
            is_builtin=True,
            description="钢铁表面缺陷检测首个部署权重",
        )
        db.add(model)
        db.commit()
        print("[seed] 注册默认模型：ssdd_yolo11n_v1（v1.0.0）")
    elif not model.is_builtin:
        model.is_builtin = True
        model.owner_id = None
        db.commit()


def run_seed() -> None:
    db = SessionLocal()
    try:
        permissions = seed_permissions(db)
        roles = seed_roles(db, permissions)
        admin = seed_admin_user(db, roles)
        seed_detection_scenes(db, admin.id)
        print("[seed] 种子数据初始化完成")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
