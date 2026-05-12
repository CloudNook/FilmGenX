"""
CharacterRefSet：角色参考图设计（Layer 3）。

由 character_ref_agent 在 visual_style 完成后产出。每个出场角色的图生图提示词
（基础三视图 + 表情变体 + 服装 + 配件），产物 asset_code 后续被 video_prompt_agent
作为 ``generate_video`` 的参考图（Seedance reference-to-video）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


AspectRatio = Literal["16:9", "9:16", "1:1", "3:4", "4:3"]


class ExpressionVariant(BaseModel):
    """单个表情变体（name + prompt 配对）。

    用 ``List[ExpressionVariant]`` 而不是 ``Dict[str, str]`` 是为了让 Gemini
    response_schema 的 ``minItems`` 真正生效——Dict（``additionalProperties`` 形式）
    在 Gemini 上不强制 ``minProperties``，LLM 容易交 ``{}`` 蒙混。
    """

    name: str = Field(
        ...,
        title="表情名",
        description="表情关键词，如 angry / determined / exhausted / sad / smile",
    )
    prompt: str = Field(
        ...,
        title="提示词补充",
        description="该表情对应的提示词补充（与 base_prompt 配合时差异化的部分）",
    )


class CharacterRef(BaseModel):
    """单个角色的图生图参考设计。"""

    name: str = Field(
        ...,
        title="角色名",
        description="与 outline.characters.name 完全对齐",
    )
    version: str = Field(
        default="v1",
        title="版本",
        description="设计版本号，便于角色形象迭代时区分（如 v1 / v2-redesign）",
    )
    base_prompt: str = Field(
        ...,
        title="基础描述",
        description="中文基础外观描述（发型 + 发色 + 瞳色 + 体型 + 服装核心），用作所有变体共享 base",
    )
    expressions: List[ExpressionVariant] = Field(
        ...,
        min_length=3,
        title="表情变体",
        description="表情变体列表（至少 3 项，主角建议 4-5 项）。每项含表情名 + 提示词补充",
    )
    clothing_detail: str = Field(
        ...,
        title="服装",
        description="服装详细描述（材质 / 配色 / 装饰），独立于 base_prompt 让换装更自由",
    )
    accessories: Optional[str] = Field(
        None,
        title="配饰",
        description="可选配饰（武器 / 首饰 / 道具）",
    )
    negative_prompt: str = Field(
        ...,
        title="负面",
        description="角色专属负面提示词（如 'female, child, modern clothing'）",
    )
    style_preset: str = Field(
        ...,
        title="风格预设",
        description="配套风格 preset 名（如 'intense / dramatic'），由 visual_style 决定",
    )
    reference_image_count: int = Field(
        default=2,
        ge=1,
        le=5,
        title="参考图数量",
        description="该角色需生成几张参考图（不同表情 / 角度），范围 1-5",
    )
    aspect_ratio: AspectRatio = Field(
        default="9:16",
        title="画幅",
        description="角色图画幅，竖版 9:16 适合人物半身 / 全身",
    )


class CharacterRefSet(BaseModel):
    """全片角色参考图集合 = character_ref_agent 的完整输出。"""

    style_anchor_id: str = Field(
        ...,
        title="风格锚 ID",
        description="引用 visual_style 的 art_genre + character_art_style 摘要，确认本批角色与全片风格一致",
    )
    characters: List[CharacterRef] = Field(
        ...,
        title="角色列表",
        description="全片所有出场角色（与 outline.characters 一一对应，至少包含主角）",
        min_length=1,
    )

    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        return cls.model_json_schema()
