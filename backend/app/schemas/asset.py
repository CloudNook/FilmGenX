from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


class AssetCreate(BaseModel):
    """Create asset request."""

    asset_code: str = Field(..., max_length=100, description="Asset code")
    name: Optional[str] = Field(
        None,
        max_length=120,
        description="Human-readable name (character/scene name, etc).",
    )
    asset_type: str = Field(
        ...,
        pattern="^(image|video|audio|reference)$",
        description="image / video / audio / reference",
    )
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


class AssetResponse(BaseResponse):
    """Asset response."""

    project_id: int
    asset_code: str
    name: Optional[str]
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
