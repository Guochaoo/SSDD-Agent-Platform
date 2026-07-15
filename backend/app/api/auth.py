"""
认证相关 API 路由
- POST /api/auth/register  用户注册
- POST /api/auth/login     用户登录
- GET  /api/auth/me        获取当前用户信息
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database.session import get_db
from app.entity.schemas import (
    TokenResponse, UserLogin, UserRegister, UserResponse, UserUpdate,
    ChangePassword, PasswordResetRequest, PasswordResetConfirm,
)
from app.services.user_service import user_service

router = APIRouter(prefix="/api/auth", tags=["认证"])

# OAuth2 密码模式，用于从请求 Header 中提取 Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    从 JWT Token 中解析当前用户
    在需要认证的路由中通过 Depends(get_current_user) 使用
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = user_service.get_user_by_id(db, user_id)
    return user


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(request: UserRegister, db: Session = Depends(get_db)):
    """
    用户注册

    - **username**: 用户名（3-50 字符）
    - **email**: 邮箱
    - **password**: 密码（至少 6 位）
    """
    user = user_service.register(
        db=db,
        username=request.username,
        email=request.email,
        password=request.password,
    )
    return user


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录

    - 返回 JWT access_token
    - 后续请求在 Header 中携带：Authorization: Bearer <token>
    """
    user = user_service.login(
        db=db,
        username=request.username,
        password=request.password,
    )

    access_token = user_service.create_access_token_for_user(user)
    roles = user_service.get_user_roles(db, user)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "roles": roles,
        },
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前登录用户信息（需要 Token 认证）"""
    roles = user_service.get_user_roles(db, current_user)
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "phone": current_user.phone,
        "avatar": current_user.avatar,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "roles": roles,
        "last_login_at": current_user.last_login_at,
        "created_at": current_user.created_at,
    }


@router.put("/me", response_model=UserResponse)
async def update_profile(
    payload: UserUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新当前用户资料（username/phone/avatar/email，均可选）"""
    user = user_service.update_profile(
        db,
        current_user,
        payload.phone,
        payload.avatar,
        payload.email,
        payload.username,
    )
    roles = user_service.get_user_roles(db, user)
    return {
        "id": user.id, "username": user.username, "email": user.email, "phone": user.phone,
        "avatar": user.avatar, "is_active": user.is_active, "is_superuser": user.is_superuser,
        "roles": roles, "last_login_at": user.last_login_at, "created_at": user.created_at,
    }


@router.post("/change-password")
async def change_password(
    payload: ChangePassword,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """已登录状态下修改密码，需提供旧密码校验"""
    user_service.change_password(db, current_user, payload.old_password, payload.new_password)
    return {"message": "密码修改成功"}


@router.post("/password-reset/request")
async def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    """
    忘记密码：申请重置令牌。
    出于安全考虑，无论邮箱是否存在都返回相同提示；实际发送重置邮件的逻辑（含 raw_token）
    由负责邮件发送的同学接入，这里只负责生成并落库令牌。
    """
    user_service.request_password_reset(db, payload.email)
    return {"message": "如果该邮箱已注册，重置链接将发送到您的邮箱"}


@router.post("/password-reset/confirm")
async def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    """忘记密码：使用邮件中的令牌设置新密码"""
    user_service.confirm_password_reset(db, payload.token, payload.new_password)
    return {"message": "密码重置成功，请使用新密码登录"}


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """管理员禁用某个用户账号"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    user_service.set_active(db, user_id, is_active=False)
    return {"message": "用户已禁用"}


@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """管理员重新启用某个用户账号"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    user_service.set_active(db, user_id, is_active=True)
    return {"message": "用户已启用"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """管理员删除用户，事务化级联清理其全部关联数据（对应任务文档步骤 13）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    user_service.delete_user_cascade(db, user_id)
    return {"message": "用户及其关联数据已删除"}
