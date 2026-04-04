"""
项目（Project）的请求/响应 Schema。
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


class ProjectCreate(BaseModel):
    """创建项目请求体。"""
    name: str = Field(..., max_length=100, description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    novel_title: str = Field(..., max_length=100, description="原著名称")
    cover_image_url: Optional[str] = Field(None, max_length=500, description="封面图URL")


class ProjectUpdate(BaseModel):
    """更新项目请求体。"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    cover_image_url: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, pattern="^(active|archived)$")


class ProjectResponse(BaseResponse):
    """项目响应。"""
    owner_id: int
    name: str
    description: Optional[str]
    novel_title: str
    cover_image_url: Optional[str]
    status: str
