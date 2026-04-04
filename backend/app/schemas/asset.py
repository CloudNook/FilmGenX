"""
素材（Asset）的请求/响应 Schema。
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


class AssetCreate(BaseModel):
    """手动创建素材记录请求体（AI 生成任务完成后由系统自动创建，此处用于上传场景）。"""
    shot_id: Optional[int] = Field(None, description="关联镜头ID，全局素材可为空")
    asset_code: str = Field(..., max_length=100, description="素材业务ID")
    asset_type: str = Field(..., pattern="^(image|video|audio|reference)$", description="素材类型")
    file_url: str = Field(..., max_length=500, description="文件URL")
    file_format: Optional[str] = Field(None, max_length=10)
    file_size_bytes: Optional[int] = Field(None, gt=0)
    width: Optional[int] = Field(None, gt=0)
    height: Optional[int] = Field(None, gt=0)
    duration_sec: Optional[float] = Field(None, gt=0)
    source: str = Field("uploaded", pattern="^(generated|uploaded)$")
    generator: Optional[str] = Field(None, max_length=50)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    parent_asset_id: Optional[int] = Field(None, description="上一版本素材ID")


class AssetResponse(BaseResponse):
    """素材详情响应。"""
    project_id: int
    shot_id: Optional[int]
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
