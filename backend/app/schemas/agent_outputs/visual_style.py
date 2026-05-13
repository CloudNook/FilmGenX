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
        description=(
            "主光源描述（含色温 K + 方向 + 硬软）。"
            "如 'hard 5600K key light at 45° camera-left, 1:8 key:fill ratio'"
        ),
    )
    fill_light: str = Field(
        ...,
        title="补光",
        description="补光强度与色温，如 'low fill, 1:8 ratio, deep shadows in lower half'",
    )
    practical_lights: str = Field(
        ...,
        title="场景灯",
        description=(
            "画面里可见的人造光源（灯笼 / 蜡烛 / 屏幕 / 霓虹等），"
            "含位置 + 颜色。如 'rooftop neon (cyan + magenta), street lamps (warm sodium)'"
        ),
    )
    time_of_day_default: str = Field(
        ...,
        title="基准时段",
        description="整片基准时段，如 'golden hour' / 'night, post-rain' / 'blue hour'",
    )


class CompositionStyle(BaseModel):
    """全局构图风格。"""

    framing: str = Field(
        ...,
        title="取景",
        description="取景倾向，如 'dynamic framing, extreme dutch angles, aggressive diagonal lines'",
    )
    depth: str = Field(
        ...,
        title="纵深",
        description="纵深策略，如 'multi-layered depth with flying debris in foreground, motion-blurred background'",
    )
    rule_of_thirds: str = Field(
        ...,
        title="三分法",
        description="三分法应用策略，如 'weakly applied, favoring off-center extreme close-ups'",
    )


class CharacterArtStyle(BaseModel):
    """角色美术风格。"""

    proportions: str = Field(
        ...,
        title="比例",
        description="人物比例，如 'realistic 7.5-8 head proportion, dynamic anatomy'",
    )
    linework: str = Field(
        ...,
        title="线条",
        description=(
            "线条风格 / 渲染手法，如 'no 2D outlines, high-end 3D CG render, subsurface scattering on skin'"
            " 或 'anime cel-shading, clean 2-tone separation'"
        ),
    )
    expression: str = Field(
        ...,
        title="表情",
        description="表情风格，如 'highly stylized extreme expressions of fury and despair'",
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
