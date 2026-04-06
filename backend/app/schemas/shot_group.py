"""分镜组（ShotGroup）的请求/响应 Schema。"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


class ShotGroupCreate(BaseModel):
    """创建分镜组请求体。"""
    group_code: str = Field(..., max_length=50, description="组编号，如 G001")
    name: Optional[str] = Field(None, max_length=200, description="可读名称")
    shot_ids: List[int] = Field(..., description="组成员分镜 ID 列表（按顺序）")


class ShotGroupUpdate(BaseModel):
    """更新分镜组请求体。"""
    name: Optional[str] = Field(None, max_length=200)
    shot_ids: Optional[List[int]] = Field(None, description="替换组成员（按顺序）")
    status: Optional[str] = Field(
        None, pattern="^(draft|generating|review|approved|rejected)$"
    )
    image_references: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="参考图列表：[{char_version_id, location_id, url, label}]",
    )
    image_start_url: Optional[str] = Field(None, description="视频首帧图片URL")
    end_frame_description: Optional[str] = Field(
        None, description="Phase 3 导演输出的本组终态描述（中文），供下一组参考"
    )


class ShotGroupResponse(BaseResponse):
    """分镜组详情响应。"""
    storyboard_id: int
    group_code: str
    name: Optional[str]
    sequence: int
    total_duration_sec: Optional[float]
    video_url: Optional[str]
    status: str
    plan_intent: Optional[str] = None
    shots: Optional[List[dict]] = Field(None, description="成员分镜摘要列表")
    image_references: List[Dict[str, Any]] = Field(
        default_factory=list, description="参考图列表：[{char_version_id, location_id, url, label}]"
    )
    image_start_url: Optional[str] = Field(None, description="视频首帧图片URL")
    prev_shot_group_id: Optional[int] = Field(None, description="前一分镜组 ID")
    end_frame_description: Optional[str] = Field(None, description="本组终态描述，供下一组参考")
