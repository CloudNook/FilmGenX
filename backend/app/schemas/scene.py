"""
高光片段（Scene）的请求/响应 Schema。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import BaseResponse


class KeyEventSchema(BaseModel):
    order: int
    description: str
    emotional_beat: str


class VisualHighlightSchema(BaseModel):
    name: str
    description: str


# ---------------------------------------------------------------------------
# 创建 / 更新
# ---------------------------------------------------------------------------

class SceneCreate(BaseModel):
    """创建高光片段请求体（手动创建时使用，confirm 接口直接从 outline 创建）。"""
    scene_code: str = Field(..., max_length=20)
    title: str = Field(..., max_length=200)
    synopsis: Optional[str] = None
    theme: Optional[str] = None
    novel_chapter_start: Optional[str] = Field(None, max_length=50)
    novel_chapter_end: Optional[str] = Field(None, max_length=50)
    novel_excerpt: Optional[str] = None
    story_arc: Optional[str] = None
    key_events: List[Dict[str, Any]] = Field(default_factory=list)
    emotional_arc: Optional[str] = None
    characters: List[str] = Field(default_factory=list)
    character_focus: Optional[str] = None
    character_ids: List[int] = Field(default_factory=list)
    primary_location: Optional[str] = None
    location_atmosphere: Optional[str] = None
    visual_highlights: List[Dict[str, Any]] = Field(default_factory=list)
    color_palette: Optional[str] = None
    bgm_direction: Optional[str] = None
    storyboard_style_notes: Optional[str] = None
    previous_episode_hint: Optional[str] = None
    next_episode_hint: Optional[str] = None
    scene_types: List[str] = Field(default_factory=list)
    priority: str = Field("A", pattern="^[SABC]$")
    estimated_duration_sec: Optional[int] = Field(None, gt=0)


class SceneUpdate(BaseModel):
    """更新高光片段请求体（所有字段可选）。"""
    title: Optional[str] = Field(None, max_length=200)
    synopsis: Optional[str] = None
    theme: Optional[str] = None
    novel_chapter_start: Optional[str] = Field(None, max_length=50)
    novel_chapter_end: Optional[str] = Field(None, max_length=50)
    novel_excerpt: Optional[str] = None
    story_arc: Optional[str] = None
    key_events: Optional[List[Dict[str, Any]]] = None
    emotional_arc: Optional[str] = None
    characters: Optional[List[str]] = None
    character_focus: Optional[str] = None
    character_ids: Optional[List[int]] = None
    primary_location: Optional[str] = None
    location_atmosphere: Optional[str] = None
    visual_highlights: Optional[List[Dict[str, Any]]] = None
    color_palette: Optional[str] = None
    bgm_direction: Optional[str] = None
    storyboard_style_notes: Optional[str] = None
    previous_episode_hint: Optional[str] = None
    next_episode_hint: Optional[str] = None
    scene_types: Optional[List[str]] = None
    priority: Optional[str] = Field(None, pattern="^[SABC]$")
    estimated_duration_sec: Optional[int] = Field(None, gt=0)
    status: Optional[str] = Field(
        None,
        pattern="^(draft|in_production|completed)$",
    )


# ---------------------------------------------------------------------------
# 响应
# ---------------------------------------------------------------------------

class SceneResponse(BaseResponse):
    """高光片段详情响应。"""
    project_id: int
    scene_code: str
    title: str
    synopsis: Optional[str]
    theme: Optional[str]
    novel_chapter_start: Optional[str]
    novel_chapter_end: Optional[str]
    novel_excerpt: Optional[str]
    story_arc: Optional[str]
    key_events: List[Dict[str, Any]]
    emotional_arc: Optional[str]
    characters: List[str]
    character_focus: Optional[str]
    character_ids: List[int]
    primary_location: Optional[str]
    location_atmosphere: Optional[str]
    visual_highlights: List[Dict[str, Any]]
    color_palette: Optional[str]
    bgm_direction: Optional[str]
    storyboard_style_notes: Optional[str]
    previous_episode_hint: Optional[str]
    next_episode_hint: Optional[str]
    scene_types: List[str]
    priority: str
    estimated_duration_sec: Optional[int]
    status: str

    @field_validator('characters', 'character_ids', 'key_events', 'visual_highlights', 'scene_types', mode='before')
    @classmethod
    def coerce_null_to_list(cls, v):
        return v if v is not None else []
