"""
FastAPI 依赖注入公共模块。

提供：
  - get_db：数据库会话（从 session 模块导入，统一从此处引用）
  - get_current_user_id：从 JWT Bearer token 中提取用户ID
  - get_current_admin：仅限管理员访问
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionFactory
from app.models.user import User
from app.utils.auth import decode_access_token

_bearer_scheme = HTTPBearer()


async def get_db():
    """数据库会话依赖注入。"""
    async with AsyncSessionFactory() as session:
        yield session


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> int:
    """从 Authorization: Bearer <token> 中解析 JWT，返回用户ID。"""
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或已过期的 token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


async def get_current_admin(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    校验当前用户是否为管理员（is_superuser=True）。

    失败则抛出 403 Forbidden。
    """
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_deleted.is_(False))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user
