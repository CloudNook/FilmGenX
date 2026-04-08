"""
角色（Character）的请求/响应 Schema。
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


# ---------------------------------------------------------------------------
# Character
# ---------------------------------------------------------------------------

class CharacterCreate(BaseModel):
    """创建角色请求体。"""
    name: str = Field(..., max_length=50, description="角色名称")
    pic_name: Optional[str] = Field(None, max_length=200, description="角色图片名称")
    pic_url: Optional[str] = Field(None, max_length=500, description="角色图片URL")


class CharacterUpdate(BaseModel):
    """更新角色请求体。"""
    name: Optional[str] = Field(None, max_length=50)
    pic_name: Optional[str] = Field(None, max_length=200)
    pic_url: Optional[str] = Field(None, max_length=500)


class CharacterResponse(BaseResponse):
    """角色详情响应。"""
    project_id: int
    char_code: str
    name: str
    pic_name: Optional[str] = None
    pic_url: Optional[str] = None


class CharacterDashboardResponse(BaseModel):
    """角色总览响应。"""
    total_characters: int = Field(..., description="角色总数")
    recent_characters: list[CharacterResponse] = Field(
        default_factory=list,
        description="最近更新的角色列表",
    )
