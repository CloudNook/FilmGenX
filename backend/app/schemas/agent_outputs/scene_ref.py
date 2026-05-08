"""
SceneRefSet：场景参考图设计（Layer 3）。

由 scene_ref_agent 在 character_ref 完成后产出。每个不同地点的环境图生图提示词，
后续被 frame_prompt_agent 通过 location 引用作为场景背景锚。

按 ``location`` 去重 —— 同一地点（如"陈墨的出租屋"）即使在多场戏出现，也只在
SceneRefSet 里出现一次；time_variants 字段处理 day / night / rain 等同地点不同
时刻的变体。
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


AspectRatio = Literal["16:9", "9:16", "1:1", "3:4", "4:3"]


class SceneRef(BaseModel):
    """单个场景地点的图生图参考设计。"""

    location: str = Field(
        ...,
        title="地点",
        description="与 script.scenes.location 完全对齐；同名地点全片只出现一次",
    )
    atmosphere: str = Field(
        ...,
        title="氛围",
        description="氛围描述（中文），如 '废墟感，苍凉，火光映衬'",
    )
    architecture: str = Field(
        ...,
        title="建筑",
        description="建筑外观（中文），如 '中式宗门大殿，雕梁画栋，金顶歇山'",
    )
    lighting: str = Field(
        ...,
        title="光照",
        description="光照描述（中文），如 '黄昏侧逆光，斗气橙红色映在墙面'",
    )
    props: Optional[str] = Field(
        None,
        title="道具",
        description="可选关键道具 / 陈设描述",
    )
    time_variants: Dict[str, str] = Field(
        ...,
        min_length=1,
        title="时段变体",
        description="同一地点不同时段 / 天气的变体提示词，key=变体名（day / night / rain / sunset），value=该变体的描述。至少 1 项",
    )
    color_restrictions: str = Field(
        ...,
        title="色调限制",
        description="本场景色调约束（英文 SD 风格），如 'desaturated blues and grays, occasional warm torch orange'",
    )
    mood_keywords: List[str] = Field(
        ...,
        min_length=2,
        title="氛围词",
        description="氛围关键词列表（中文短词），至少 2 项，如 ['废墟感', '苍凉', '压抑']",
    )
    negative_prompt: str = Field(
        ...,
        title="负面",
        description="场景专属负面（如 'no modern buildings, no cars'）",
    )
    reference_image_count: int = Field(
        default=2,
        ge=1,
        le=4,
        title="参考图数量",
        description="该地点需生成几张参考图（不同 angle / 时段），范围 1-4",
    )
    aspect_ratio: AspectRatio = Field(
        default="16:9",
        title="画幅",
        description="场景图画幅，横版 16:9 适合环境展现",
    )


class SceneRefSet(BaseModel):
    """全片场景参考图集合 = scene_ref_agent 的完整输出。"""

    style_anchor_id: str = Field(
        ...,
        title="风格锚 ID",
        description="引用 visual_style 的 scene_art_style 摘要，确认本批场景与全片风格一致",
    )
    scenes: List[SceneRef] = Field(
        ...,
        title="场景列表",
        description="全片去重后的场景地点（与 script.scenes.location 唯一值集合一一对应）",
        min_length=1,
    )

    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        return cls.model_json_schema()
