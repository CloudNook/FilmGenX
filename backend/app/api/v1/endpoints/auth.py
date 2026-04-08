"""
认证 API 端点。

路由前缀：/api/v1/auth
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.core.config import settings
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateUserRequest,
    UserResponse,
)
from app.utils.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, summary="注册")
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """注册新用户，返回 JWT token。"""
    repo = UserRepository(db)

    # 检查邮箱是否已注册
    if await repo.get_by_email(body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该邮箱已被注册",
        )

    # 检查用户名是否已存在
    if await repo.get_by_username(body.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该用户名已被使用",
        )

    # 创建用户
    user = await repo.create(
        email=body.email,
        username=body.username,
        hashed_password=hash_password(body.password),
    )
    await db.commit()

    # 生成 token
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse, summary="登录")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """邮箱密码登录，返回 JWT token。"""
    repo = UserRepository(db)

    # 邀请码校验（配置了才校验）
    if settings.INVITE_CODE and body.invite_code != settings.INVITE_CODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="邀请码错误",
        )

    user = await repo.get_by_email(body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用",
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_me(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取当前登录用户的信息。"""
    user = await UserRepository(db).get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    return user


@router.patch("/me", response_model=UserResponse, summary="更新当前用户信息")
async def update_me(
    body: UpdateUserRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """更新当前用户的用户名或头像。"""
    repo = UserRepository(db)

    # 检查用户名是否被占用
    if body.username:
        existing = await repo.get_by_username(body.username)
        if existing and existing.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该用户名已被使用",
            )

    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有需要更新的字段",
        )

    user = await repo.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    user = await repo.update(user, data)
    await db.commit()
    return user


@router.post("/me/avatar", response_model=UserResponse, summary="上传头像")
async def upload_avatar(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """上传用户头像到 OSS，更新 avatar_url。"""
    # 校验文件类型
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型 {file.content_type}，仅支持 JPG/PNG/WebP/GIF",
        )

    # 校验文件大小（最大 5MB）
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="头像文件不能超过 5MB",
        )

    # 上传到 OSS
    from app.utils.oss import oss_client
    import os
    ext = os.path.splitext(file.filename or "avatar.jpg")[1]
    avatar_url = oss_client.upload_bytes(
        content,
        filename=f"avatar_{user_id}{ext}",
        directory="avatars",
    )

    # 更新用户记录
    repo = UserRepository(db)
    user = await repo.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    user = await repo.update(user, {"avatar_url": avatar_url})
    await db.commit()
    return user
