"""
分镜脚本（Storyboard）的请求/响应 Schema。
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


class EmotionPoint(BaseModel):
    """情感弧线中的单个数据点。"""
    time_sec: float = Field(..., description="时间点（秒）")
    intensity: int = Field(..., ge=1, le=10, description="情绪强度 1-10")
    label: str = Field(..., description="情绪标签，如 '压抑开场'")


class PacingRatio(BaseModel):
    """节奏比例（三段式，总和应为 100）。"""
    buildup: int = Field(..., ge=0, le=100, description="铺垫占比（%）")
    climax: int = Field(..., ge=0, le=100, description="高潮占比（%）")
    resolution: int = Field(..., ge=0, le=100, description="收尾占比（%）")


class StoryboardCreate(BaseModel):
    """创建分镜脚本请求体（由 AI 生成后入库，也可手动创建）。"""
    emotion_curve: Optional[List[EmotionPoint]] = Field(None, description="情感弧线数据")
    narrative_notes: Optional[str] = Field(None, description="叙事设计备注")
    pacing_ratio: Optional[PacingRatio] = None
    total_duration_sec: Optional[float] = Field(None, gt=0, description="总时长（秒）")


class StoryboardUpdate(BaseModel):
    """更新分镜脚本请求体。"""
    emotion_curve: Optional[List[EmotionPoint]] = None
    narrative_notes: Optional[str] = None
    pacing_ratio: Optional[PacingRatio] = None
    total_duration_sec: Optional[float] = Field(None, gt=0)
    status: Optional[str] = Field(
        None,
        pattern="^(draft|generating|review|approved)$",
        description="状态：draft / generating / review / approved",
    )


class StoryboardResponse(BaseResponse):
    """分镜脚本详情响应。"""
    scene_id: int
    emotion_curve: Optional[list]
    narrative_notes: Optional[str]
    pacing_ratio: Optional[dict]
    total_duration_sec: Optional[float]
    version: int
    status: str
    generation_phase: Optional[str] = None
    plan_data: Optional[dict] = None
