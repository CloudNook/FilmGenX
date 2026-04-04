"""
FastAPI 依赖注入公共模块。

目前提供：
  - get_db：数据库会话（从 session.py 转发，统一从此处导入）
  - get_current_user_id：从请求头中提取用户ID（简化版，后续替换为 JWT 鉴权）
"""

from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db  # noqa: F401（由外部 import 使用）


async def get_current_user_id(x_user_id: int = Header(..., description="当前用户ID（临时方案，后续改为 JWT）")) -> int:
    """从请求头 X-User-Id 中获取当前用户ID。

    开发阶段使用 Header 传递用户ID，避免引入完整鉴权系统阻塞开发进度。
    生产环境上线前需替换为 JWT Token 解码逻辑。
    """
    if x_user_id <= 0:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的用户ID")
    return x_user_id
