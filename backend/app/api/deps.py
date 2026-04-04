"""
FastAPI 依赖注入公共模块。

提供：
  - get_db：数据库会话（从 session 模块导入，统一从此处引用）
  - get_current_user_id：从 JWT Bearer token 中提取用户ID
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.session import AsyncSessionFactory
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
