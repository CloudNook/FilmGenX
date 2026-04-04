"""
高光片段（Scene）的请求/响应 Schema。
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


# ---------------------------------------------------------------------------
# 创建
# ---------------------------------------------------------------------------

class ScoreDetail(BaseModel):
    """各维度评分（0-10）。"""
    dramatic_tension: Optional[int] = Field(None, ge=0, le=10, description="戏剧张力")
    visual_potential: Optional[int] = Field(None, ge=0, le=10, description="视觉化潜力")
    emotional_resonance: Optional[int] = Field(None, ge=0, le=10, description="情感共鸣度")
    narrative_importance: Optional[int] = Field(None, ge=0, le=10, description="叙事重要性")
    audience_familiarity: Optional[int] = Field(None, ge=0, le=10, description="粉丝熟知度")


class SceneCreate(BaseModel):
    """创建高光片段请求体。"""
    scene_code: str = Field(..., max_length=20, description="业务ID，如 DQCK_001")
    title: str = Field(..., max_length=200, description="片段标题")
    novel_chapter_start: Optional[str] = Field(None, max_length=50, description="起始章节")
    novel_chapter_end: Optional[str] = Field(None, max_length=50, description="结束章节")
    novel_excerpt: Optional[str] = Field(None, description="原著关键段落摘录")
    scene_types: List[str] = Field(default_factory=list, description="片段类型列表")
    priority: str = Field("A", pattern="^[SABC]$", description="优先级：S/A/B/C")
    scores: Optional[ScoreDetail] = None
    character_ids: List[int] = Field(default_factory=list, description="涉及角色ID列表")
    estimated_duration_sec: Optional[int] = Field(None, gt=0, description="预估时长（秒）")


class SceneUpdate(BaseModel):
    """更新高光片段请求体（所有字段可选）。"""
    title: Optional[str] = Field(None, max_length=200)
    novel_chapter_start: Optional[str] = Field(None, max_length=50)
    novel_chapter_end: Optional[str] = Field(None, max_length=50)
    novel_excerpt: Optional[str] = None
    scene_types: Optional[List[str]] = None
    priority: Optional[str] = Field(None, pattern="^[SABC]$")
    scores: Optional[ScoreDetail] = None
    character_ids: Optional[List[int]] = None
    estimated_duration_sec: Optional[int] = Field(None, gt=0)
    status: Optional[str] = Field(
        None,
        pattern="^(draft|scored|in_production|completed)$",
        description="状态：draft / scored / in_production / completed",
    )


# ---------------------------------------------------------------------------
# 响应
# ---------------------------------------------------------------------------

class SceneResponse(BaseResponse):
    """高光片段详情响应。"""
    project_id: int
    scene_code: str
    title: str
    novel_chapter_start: Optional[str]
    novel_chapter_end: Optional[str]
    novel_excerpt: Optional[str]
    scene_types: List[str]
    priority: str
    score_dramatic_tension: Optional[int]
    score_visual_potential: Optional[int]
    score_emotional_resonance: Optional[int]
    score_narrative_importance: Optional[int]
    score_audience_familiarity: Optional[int]
    score_total: Optional[int]
    character_ids: List[int]
    estimated_duration_sec: Optional[int]
    status: str
