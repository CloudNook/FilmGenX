"""
认证相关 Schema。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.base import BaseResponse


class RegisterRequest(BaseModel):
    """注册请求体。"""
    email: str = Field(..., description="邮箱地址")
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class LoginRequest(BaseModel):
    """登录请求体。"""
    email: str = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")
    invite_code: Optional[str] = Field(None, description="邀请码")


class TokenResponse(BaseModel):
    """JWT Token 响应。"""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseResponse):
    """用户信息响应。"""
    email: str
    username: str
    is_active: bool
    is_superuser: bool
    avatar_url: Optional[str] = None


class UpdateUserRequest(BaseModel):
    """更新用户信息请求体。"""
    username: Optional[str] = Field(None, min_length=2, max_length=50, description="新用户名")
    avatar_url: Optional[str] = Field(None, max_length=500, description="新头像 URL")
