"""
FramePromptSet：每个 shot 的首帧图提示词（Layer 4）。

由 frame_prompt_agent 在 scene_ref 完成后产出。把 storyboard 的镜头规划（景别 /
机位 / 运动 / 构图描述）+ visual_style 风格锚 + character_ref 角色锚 + scene_ref
场景锚汇聚成一条完整的"可直接喂给图像生成模型"的中文 prompt。

下游：
- 这一层的 image_prompt 直接喂给 ``generate_image_pro`` / ``generate_image_flash`` 工具
- 产出的 OSS URL 再喂给 video_prompt_agent 的 seed_image_url
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


AspectRatio = Literal["16:9", "9:16", "1:1", "3:4", "4:3"]
ImageSize = Literal["512", "1K", "2K", "4K"]
ModelHint = Literal[
    "gemini-3-pro-image-preview",
    "gemini-3.1-flash-image-preview",
]


class FramePrompt(BaseModel):
    """单个 shot 的首帧图提示词。"""

    shot_number: int = Field(
        ...,
        ge=1,
        title="镜号",
        description="与 storyboard.shots.shot_number 对齐",
    )
    scene_number: int = Field(
        ...,
        ge=1,
        title="场号",
        description="与 storyboard.shots.scene_number 对齐",
    )
    image_prompt: str = Field(
        ...,
        title="图像提示词",
        description="完整的中文图生图 prompt，必须涵盖：构图（景别 + 主体位置）+ 角色动作 / 表情 + 场景背景 + 光影色调 + 关键道具 / 视觉锚点。约 80-200 字",
    )
    negative_prompt: str = Field(
        ...,
        title="负面",
        description="本镜头负面提示词（继承 visual_style.negative_anchor + 镜头特异）",
    )
    style_preset: str = Field(
        ...,
        title="风格预设",
        description="风格 preset 名（与 visual_style 匹配）",
    )
    aspect_ratio: AspectRatio = Field(
        ...,
        title="画幅",
        description="本镜画幅，应与全片统一（除非创意需要）",
    )
    image_size: ImageSize = Field(
        default="1K",
        title="分辨率",
        description="生成分辨率，1K 适合大多数情况；高潮镜头可上 2K",
    )
    character_refs: List[str] = Field(
        default_factory=list,
        title="角色锚",
        description=(
            "本镜出现的角色 name 列表（来自 character_ref.characters）。"
            "本期工具不消费此字段——仅用于追溯/人工审阅；等 project-level memory 落地后会"
            "驱动 reference image 检索。空列表表示纯环境镜。"
        ),
    )
    scene_ref: Optional[str] = Field(
        None,
        title="场景锚",
        description=(
            "本镜对应的场景地点（来自 scene_ref.scenes.location）。"
            "本期工具不消费此字段——仅用于追溯/人工审阅；等 memory 落地后会驱动场景参考图检索。"
            "纯人物特写可不填。"
        ),
    )
    key_visual_elements: List[str] = Field(
        ...,
        min_length=1,
        title="视觉锚点",
        description="本镜必须出现的画面元素（与原著情节锚定），至少 1 项，如 ['玄重尺', '绿色异火']",
    )
    lighting_keywords: str = Field(
        ...,
        title="光照关键词",
        description="本镜专属光照（在 visual_style.lighting_style 基础上具体化），如 '火焰逆光，主体边缘镀金边'",
    )
    model_hint: ModelHint = Field(
        default="gemini-3-pro-image-preview",
        title="模型偏好",
        description="推荐生成模型：pro 用于首帧 / 关键画面（慢，质量高）；flash 用于批量草图 / 验证（快，质量稍低）",
    )


class FramePromptSet(BaseModel):
    """全片首帧图提示词集合 = frame_prompt_agent 的完整输出。"""

    style_anchor_id: str = Field(
        ...,
        title="风格锚 ID",
        description="引用 visual_style 的整体摘要",
    )
    frames: List[FramePrompt] = Field(
        ...,
        title="镜头提示词列表",
        description="全片所有 shot 的首帧图提示词（一一对应 storyboard.shots）",
        min_length=1,
    )

    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        return cls.model_json_schema()
