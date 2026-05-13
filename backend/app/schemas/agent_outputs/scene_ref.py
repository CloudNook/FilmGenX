"""
SceneRefSet：场景参考图设计（Layer 3）。

由 scene_ref_agent 在 character_ref 完成后产出。每个不同地点的环境图生图提示词，
产物 asset_code 后续被 video_prompt_agent 作为 ``generate_video`` 的参考图。

按 ``location`` 去重 —— 同一地点（如"云岚宗广场"）即使在多场戏出现，也只在
SceneRefSet 里出现一次；``time_variants`` 处理同地点不同时刻 / 天气的变体。

字段与 scene_ref_agent 实际产出对齐：
- ``dressing`` / ``scale_reference`` / ``focal_length_intent``：production design 4 层 +
  焦段意图 + 尺度参照（业内 PD 专业字段）
- ``reference_asset_codes``：t2i 基础图 + i2i 时段变体的 asset_code 列表
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


AspectRatio = Literal["16:9", "9:16", "1:1", "3:4", "4:3"]


FocalLengthIntent = Literal[
    "24mm wide",      # 空间压迫 / 全景
    "35mm",           # 自然视角
    "50mm normal",    # 标准
    "85mm tele",      # 长焦 / 压缩背景
]


class TimeVariant(BaseModel):
    """同一地点的时段 / 天气变体。

    用 ``List[TimeVariant]`` 而不是 ``Dict[str, str]`` 是为了让 Gemini
    response_schema 的 ``minItems`` 真正生效——Dict（``additionalProperties`` 形式）
    在 Gemini 上不强制 ``minProperties``，LLM 容易交 ``{}`` 蒙混。
    """

    name: str = Field(
        ...,
        title="变体名",
        description="时段或天气关键词，如 day / night / rain / sunset",
    )
    prompt: str = Field(
        ...,
        title="提示词",
        description="该时段 / 天气下变化的部分（光照 / 氛围 / 颜色差异），不重复 architecture",
    )


class SceneRef(BaseModel):
    """单个场景地点的图生图参考设计。"""

    location: str = Field(
        ...,
        title="地点",
        description="与 script.scenes.location 一字不差；同名地点全片只出现一次",
    )
    atmosphere: str = Field(
        ...,
        title="氛围",
        description=(
            "氛围短句（中文），含 environmental storytelling 状态。"
            "如 '废墟 30 年状态，朱漆斑驳，灰尘踩出小径'"
        ),
    )
    architecture: str = Field(
        ...,
        title="建筑",
        description=(
            "建筑流派 + 年代 + 结构特征（中英混杂可接受）。"
            "如 '明清官式木骨架 + 抬梁式 + 重檐歇山顶 + 朱红柱'"
        ),
    )
    dressing: Optional[str] = Field(
        None,
        title="装饰陈设",
        description=(
            "墙面 / 地面 / 家具 / 挂件等"
            "可移除层（PD 4 层中的第 2 层）。"
            "如 '朱漆斑驳露木胎，青砖地磨出 polished sheen，墙上挂列祖列宗画像'"
        ),
    )
    props: List[str] = Field(
        default_factory=list,
        title="道具",
        description="关键道具列表，如 ['青铜鼎', '玉印', '缺角铁刀']",
    )
    lighting: str = Field(
        ...,
        title="光照",
        description=(
            "光源类型 + 方向 + 色温 + 强度（含 motivation）。"
            "如 'motivated soft natural light from skylight 45° upper-right, 5500K, 1:3 key:fill ratio'"
        ),
    )
    scale_reference: Optional[str] = Field(
        None,
        title="尺度参照",
        description=(
            "尺度参照物（人形 / 已知道具），暗示空间大小。"
            "如 'small monk silhouette walking past at left foreground'"
        ),
    )
    focal_length_intent: Optional[FocalLengthIntent] = Field(
        None,
        title="焦段意图",
        description="基础图按什么焦段画，决定空间感（wide 压迫 / normal 真实 / tele 压缩）",
    )
    time_variants: List[TimeVariant] = Field(
        default_factory=list,
        title="时段变体",
        description="同一地点不同时段 / 天气变体（最多 3 项；只 1 个时段时可为空）",
    )
    color_restrictions: str = Field(
        ...,
        title="色调限制",
        description=(
            "英文 SD-style 标签，含 60/30/10 配色暗示。"
            "如 'desaturated teal and warm rust, occasional crimson accent, 0.4 saturation'"
        ),
    )
    mood_keywords: List[str] = Field(
        default_factory=list,
        title="氛围词",
        description="中文短词，3-6 个，给下游 video_prompt 拼镜头描述时复用",
    )
    negative_prompt: str = Field(
        ...,
        title="负面",
        description="场景类型 + 题材双层挡板（如 'no outdoor, no sky' + 'no modern objects, no neon'）",
    )
    reference_asset_codes: List[str] = Field(
        default_factory=list,
        title="参考图 asset_codes",
        description="基础图 + 时段变体的 asset_code 列表（vid_prompt 引用）",
    )
    reference_image_count: int = Field(
        default=2,
        ge=1,
        le=4,
        title="参考图数量",
        description="该地点参考图总数（基础锚 + 时段变体）",
    )
    aspect_ratio: AspectRatio = Field(
        default="16:9",
        title="画幅",
        description="场景图画幅，横版 16:9 适合环境展现",
    )


class SceneRefSet(BaseModel):
    """全片场景参考图集合 = scene_ref_agent 的完整输出。"""

    scenes: List[SceneRef] = Field(
        ...,
        title="场景列表",
        description="全片去重后的场景地点（与 script.scenes.location 唯一值集合一一对应）",
        min_length=1,
    )

    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        return cls.model_json_schema()
