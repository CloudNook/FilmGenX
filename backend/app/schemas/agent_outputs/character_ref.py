"""
CharacterRefSet：角色参考图设计（Layer 3）。

由 character_ref_agent 在 visual_style 完成后产出。每个出场角色的图生图提示词
（基础三视图 + 表情变体 + 服装 + 配件），产物 asset_code 后续被 video_prompt_agent
作为 ``generate_video`` 的参考图（Seedance reference-to-video）。

字段与 character_ref_agent 实际产出对齐：
- ``role`` / ``personality`` / ``key_skills``：从 outline.characters 继承，让 video_prompt
  挑表情 / 姿态时有依据
- ``three_view_asset_code``：基础锚（t2i），所有变体 i2i 都以它为参考
- ``reference_asset_codes``：变体（表情 / 服装 / 战斗姿态）的 asset_code 列表
- ``accessories`` 是 ``List[str]``（武器 / 首饰 / 道具分项列），便于 prompt weighting
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


AspectRatio = Literal["16:9", "9:16", "1:1", "3:4", "4:3"]

# 与 outline.CharacterRole 保持一致
CharacterRole = Literal[
    "protagonist",
    "antagonist",
    "deuteragonist",
    "supporting",
    "foil",
    "mentor",
]


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
        description="该表情对应的提示词补充（中文表情描述 + 英文 tag），与 base_prompt 配合时差异化的部分",
    )


class CharacterRef(BaseModel):
    """单个角色的图生图参考设计。"""

    name: str = Field(
        ...,
        title="角色名",
        description="与 outline.characters.name 一字不差",
    )
    role: CharacterRole = Field(
        ...,
        title="定位",
        description="角色定位（与 outline.characters.role 一致）",
    )
    appearance: Optional[str] = Field(
        None,
        title="外观综述",
        description="人话外观综述（含发型 / 五官 / 体型），给 reviewer / 前端阅读用",
    )
    personality: Optional[str] = Field(
        None,
        title="性格",
        description="性格综述，下游 video_prompt 据此挑表情变体 / 设计动作姿态",
    )
    key_skills: List[str] = Field(
        default_factory=list,
        title="核心能力",
        description="可选——角色的能力 / 标志性动作（如 '黑炎'、'佛怒火莲'）",
    )
    base_prompt: str = Field(
        ...,
        title="基础描述",
        description=(
            "anatomically neutral 基础外观 prompt（英文为主，前 80% 权重词在前）。"
            "用作所有变体共享的 base。**禁含表情 / 动作 / 视角 / 情绪光照**——那些是变体的工作。"
        ),
    )
    expressions: List[ExpressionVariant] = Field(
        ...,
        min_length=1,
        title="表情变体",
        description=(
            "表情变体列表。主角 4-5 项，关键反派 3-4 项，次要配角 1-2 项。"
            "覆盖 script 中该角色实际出现的情绪范围（angry / determined / sad / surprised / smile 等）。"
        ),
    )
    clothing_detail: str = Field(
        ...,
        title="服装",
        description=(
            "本次场景的具体服装（材质 / 配色 / 装饰），独立于 base_prompt——"
            "未来角色换装时只换这里，不动 base。"
        ),
    )
    accessories: List[str] = Field(
        default_factory=list,
        title="配饰",
        description=(
            "武器 / 首饰 / 标志道具分项列表。**单独列**——埋在描述里 prompt 一长就被模型遗漏。"
        ),
    )
    negative_prompt: str = Field(
        ...,
        title="负面",
        description=(
            "三层叠加的角色专属负面提示词："
            "(1) 跨片性别 / 年龄防御（女主含 'male, child'），"
            "(2) art_genre 挡板（anime 含 'photorealistic'），"
            "(3) 图像通用挡板（'deformed, extra limbs, text, watermark'）。"
        ),
    )
    three_view_asset_code: Optional[str] = Field(
        None,
        title="三视图 asset_code",
        description=(
            "t2i 出三视图后工具返回的 ``img-xxxxxxxx``。"
            "所有变体 i2i 都以这个 code 为参考；下游 video_prompt 默认参考图也是它。"
        ),
    )
    reference_asset_codes: List[str] = Field(
        default_factory=list,
        title="变体 asset_codes",
        description="i2i 表情 / 服装 / 战斗姿态变体的 asset_code 列表",
    )
    reference_image_count: int = Field(
        default=2,
        ge=1,
        le=8,
        title="参考图数量",
        description="该角色总参考图数量（含三视图）；主角 3-5 张，配角 1-2 张",
    )
    aspect_ratio: AspectRatio = Field(
        default="9:16",
        title="画幅",
        description="角色图画幅，竖版 9:16 适合人物半身 / 全身",
    )


class CharacterRefSet(BaseModel):
    """全片角色参考图集合 = character_ref_agent 的完整输出。"""

    characters: List[CharacterRef] = Field(
        ...,
        title="角色列表",
        description="全片所有出场角色（与 outline.characters 一一对应，至少包含主角）",
        min_length=1,
    )

    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        return cls.model_json_schema()
