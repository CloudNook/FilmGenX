"""
VisualStyleGuide：全片视觉锚点（Layer 2）。

由 visual_style_agent 在 outline + storyboard 完成后产出，下游 character_ref /
scene_ref / video_prompt 共享这一份风格先验，保证整片视觉调性统一。

Field 双层标记：
- ``title``：UI 标签（短，1-6 字）
- ``description``：LLM 指令（指令式，告诉 LLM 怎么填）
"""

from __future__ import annotations

from typing import Any, Dict, Literal

from pydantic import BaseModel, Field


ArtGenre = Literal[
    "anime",
    "photorealistic",
    "pixar_3d",
    "ghibli",
    "cyberpunk",
    "noir",
    "watercolor",
    "custom",
]


class ColorPalette(BaseModel):
    """色调方案。"""

    primary: str = Field(
        ...,
        title="主色调",
        description="画面主色，如 '深红 + 橙黄（火焰 / 斗气色系）'",
    )
    secondary: str = Field(
        ...,
        title="辅助色",
        description="对比 / 平衡的次要色，如 '冷蓝（冰系 / 阴影色）'",
    )
    accent: str = Field(
        ...,
        title="点缀色",
        description="高光 / 特效点缀，如 '金紫（特效高光）'",
    )
    desaturation: float = Field(
        default=0.2,
        ge=0,
        le=1,
        title="去饱和度",
        description="0=鲜艳，1=黑白；建议 0.0-0.4 区间",
    )


class LightingStyle(BaseModel):
    """全局光照风格。"""

    key_light: str = Field(
        ...,
        title="主光",
        description="主光源描述，如 '强烈侧光 / 逆光，强调角色轮廓'",
    )
    fill: str = Field(
        ...,
        title="补光",
        description="补光强度与色温，如 '低填充，暗部保留细节'",
    )
    practical_sources: str = Field(
        ...,
        title="实感光源",
        description="场景内自然 / 实体光源描述，如 '斗气发光体作为天然光源'",
    )
    default_time_of_day: str = Field(
        ...,
        title="基准时段",
        description="整片基准时段，如 'sunset / golden hour' 或 'night with neon'",
    )


class CompositionStyle(BaseModel):
    """全局构图风格。"""

    framing: str = Field(
        ...,
        title="取景",
        description="取景倾向，如 '动态倾斜构图，强化战斗张力'",
    )
    depth_strategy: str = Field(
        ...,
        title="纵深",
        description="纵深处理，如 '强调前景 - 中景 - 背景三层'",
    )
    rule_of_thirds_strategy: str = Field(
        ...,
        title="三分法",
        description="三分法应用策略，如 '关键帧优先三分法，特写可突破'",
    )


class CharacterArtStyle(BaseModel):
    """角色美术风格。"""

    proportions: str = Field(
        ...,
        title="比例",
        description="人物比例，如 'anime, slightly stylized, 7-8 头身'",
    )
    linework: str = Field(
        ...,
        title="线条",
        description="线条风格，如 '锐利线条，强调力量感'",
    )
    expression_style: str = Field(
        ...,
        title="表情",
        description="表情风格，如 '夸张表情（愤怒 / 决心为主）'",
    )


class SceneArtStyle(BaseModel):
    """场景美术风格。"""

    architecture: str = Field(
        ...,
        title="建筑",
        description="建筑风格，如 '中式玄幻，斗气大陆风格'",
    )
    environment_detail: str = Field(
        ...,
        title="环境细节",
        description="环境细节倾向，如 '废墟 / 宗门 / 山谷为主'",
    )
    weather_atmosphere: str = Field(
        ...,
        title="天气氛围",
        description="天气氛围偏好，如 '偏好黄昏 / 夜晚，火焰 / 雾气增加氛围'",
    )


class VisualStyleGuide(BaseModel):
    """全片视觉锚点 = visual_style_agent 的完整输出。"""

    art_genre: ArtGenre = Field(
        ...,
        title="美术大类",
        description="美术风格大类，从 anime / photorealistic / pixar_3d / ghibli / cyberpunk / noir / watercolor / custom 中选",
    )
    overall_mood: str = Field(
        ...,
        title="整体基调",
        description="一句话描述整片基调，如 '热血燃系，暗黑战斗美学'",
    )
    color_palette: ColorPalette = Field(
        ...,
        title="色调",
        description="主色 / 辅助色 / 点缀色 / 去饱和度",
    )
    lighting_style: LightingStyle = Field(
        ...,
        title="光照",
        description="主光 / 补光 / 实感光源 / 基准时段",
    )
    composition_style: CompositionStyle = Field(
        ...,
        title="构图",
        description="取景 / 纵深 / 三分法应用",
    )
    character_art_style: CharacterArtStyle = Field(
        ...,
        title="角色美术",
        description="比例 / 线条 / 表情风格",
    )
    scene_art_style: SceneArtStyle = Field(
        ...,
        title="场景美术",
        description="建筑 / 环境细节 / 天气氛围",
    )
    negative_anchor: str = Field(
        ...,
        title="负面锚",
        description="全片负面提示词锚点（英文逗号分隔），如 'no realistic photo, no western fantasy, low quality'",
    )

    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        return cls.model_json_schema()
