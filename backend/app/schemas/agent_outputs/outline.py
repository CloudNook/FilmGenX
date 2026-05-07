"""
OutlineOutput：剧情大纲结构化输出 schema。

第一版按行业三幕结构惯例定义，后期可演化（增字段、加校验、加方法）。
LLM 通过 response_schema 直接产出符合 OutlineOutput.model_json_schema() 的 JSON。
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


CharacterRole = Literal[
    "protagonist",
    "antagonist",
    "deuteragonist",
    "supporting",
    "foil",
    "mentor",
]


class CharacterArc(BaseModel):
    """单个角色的弧线。"""

    name: str = Field(..., description="角色名（中文）")
    role: CharacterRole = Field(..., description="角色定位")
    want: str = Field(..., description="角色表层渴望（外在目标）")
    need: str = Field(..., description="角色内在需要（成长目标）")
    arc_summary: str = Field(..., description="从初始状态到结局的一句话弧线")


class Act(BaseModel):
    """三幕之一。"""

    act_number: int = Field(..., ge=1, le=3, description="幕序号 1/2/3")
    title: str = Field(..., description="幕标题")
    goal: str = Field(..., description="本幕主角面对的目标")
    key_events: List[str] = Field(
        default_factory=list,
        description="本幕关键事件列表（按时间顺序）",
    )
    turning_point: str = Field(..., description="本幕末尾的转折点 / 进入下一幕的钩子")


class Beat(BaseModel):
    """关键剧情节拍（可选，用于细化大纲）。"""

    beat_name: str = Field(..., description="节拍名称（如 inciting_incident、midpoint）")
    description: str = Field(..., description="节拍内容")
    act_ref: int = Field(..., ge=1, le=3, description="所属幕")


class OutlineOutput(BaseModel):
    """剧情大纲完整产出。"""

    title: str = Field(..., description="作品标题")
    logline: str = Field(
        ...,
        description="一句话故事梗概（25-40 字最佳）",
    )
    synopsis: str = Field(
        ...,
        description="100-200 字故事概要，覆盖核心冲突、主角弧线、结局走向",
    )
    themes: List[str] = Field(
        default_factory=list,
        description="作品主题列表（如：救赎、家庭、自我认同）",
    )
    characters: List[CharacterArc] = Field(
        default_factory=list,
        description="主要角色弧线，至少包含主角",
    )
    acts: List[Act] = Field(
        ...,
        description="三幕结构，必须 3 项",
        min_length=3,
        max_length=3,
    )
    beats: List[Beat] = Field(
        default_factory=list,
        description="可选：关键节拍细化（如 inciting_incident、plot_point_1、midpoint、plot_point_2、climax）",
    )

    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        """返回喂给 LLM response_schema 的 JSON Schema。"""
        return cls.model_json_schema()
