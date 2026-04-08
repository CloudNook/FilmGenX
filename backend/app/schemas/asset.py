from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


class AssetCreate(BaseModel):
    """Create asset request."""

    shot_id: Optional[int] = Field(None, description="Related shot ID")
    location_id: Optional[int] = Field(None, description="Related location ID")
    asset_code: str = Field(..., max_length=100, description="Asset code")
    asset_type: str = Field(..., pattern="^(image|video|audio|reference)$", description="Asset type")
    file_url: str = Field(..., max_length=5000, description="File URL")
    file_format: Optional[str] = Field(None, max_length=10)
    file_size_bytes: Optional[int] = Field(None, gt=0)
    width: Optional[int] = Field(None, gt=0)
    height: Optional[int] = Field(None, gt=0)
    duration_sec: Optional[float] = Field(None, gt=0)
    source: str = Field("uploaded", pattern="^(generated|uploaded)$")
    generator: Optional[str] = Field(None, max_length=50)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    parent_asset_id: Optional[int] = Field(None, description="Parent asset ID")


class AssetResponse(BaseResponse):
    """Asset response."""

    project_id: int
    shot_id: Optional[int]
    location_id: Optional[int]
    asset_code: str
    asset_type: str
    file_url: str
    file_format: Optional[str]
    file_size_bytes: Optional[int]
    width: Optional[int]
    height: Optional[int]
    duration_sec: Optional[float]
    source: str
    generator: Optional[str]
    tags: list
    description: Optional[str]
    version: int
    is_current: bool
    parent_asset_id: Optional[int]


class AssetDashboardResponse(BaseModel):
    """素材总览响应。"""

    total_assets: int = Field(..., description="素材总数")
    asset_type_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="按素材类型统计的数量",
    )
    recent_assets: List[AssetResponse] = Field(
        default_factory=list,
        description="最近更新的素材列表",
    )
