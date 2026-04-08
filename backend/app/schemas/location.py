"""
场景地点（Location）的请求/响应 Schema。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


# ========== Location Schemas ==========

class LocationCreate(BaseModel):
    """创建场景请求体。"""
    name: str = Field(..., max_length=100, description="场景名称")
    location_type: str = Field(
        "outdoor",
        pattern="^(indoor|outdoor|fantasy|mixed)$",
        description="场景类型"
    )
    domain: Optional[str] = Field(None, max_length=50, description="所属势力/领域")


class LocationUpdate(BaseModel):
    """更新场景请求体。"""
    name: Optional[str] = Field(None, max_length=100)
    location_type: Optional[str] = Field(None, pattern="^(indoor|outdoor|fantasy|mixed)$")
    domain: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class LocationResponse(BaseResponse):
    """场景详情响应。"""
    project_id: int
    loc_code: str
    name: str
    aliases: list
    location_type: str
    domain: Optional[str]
    is_active: bool
    usage_count: int
    # 场景封面图
    pic_name: Optional[str] = None
    pic_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class LocationBrief(BaseModel):
    """场景简略信息（用于下拉选择、列表展示）。"""
    model_config = {"from_attributes": True}

    id: int
    loc_code: str
    name: str
    location_type: str
    domain: Optional[str]
    is_active: bool


# ========== 组合响应 ==========

class LocationDashboardResponse(BaseModel):
    """场景总览响应。"""
    total_locations: int = Field(..., description="场景总数")
    total_images: int = Field(..., description="场景图片总数")
    recent_locations: List[LocationResponse] = Field(
        default_factory=list,
        description="最近更新的场景列表",
    )
