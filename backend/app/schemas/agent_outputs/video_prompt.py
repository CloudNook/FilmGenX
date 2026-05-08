"""
VideoPromptSet：每个 shot 的视频提示词（Layer 4）。

由 video_prompt_agent 在 frame_prompt 完成后产出。**本期只生成文字驱动的视频
prompt**，不接受参考图字段——等 project-level memory 落地后再加 reference image
输入（届时 video_prompt 会重新引入 seed_image / end_frame 等字段）。

下游：
- ``motion_description`` + ``duration_seconds`` 喂给 ``generate_video`` 工具
- ``model_hint`` 是 LLM 给的偏好（kling / seedance），调用方据此决定 generate_video 的 model 入参
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


AspectRatio = Literal["16:9", "9:16", "1:1"]
Quality = Literal["std", "hq"]
ModelHint = Literal["kling", "seedance"]


class VideoPrompt(BaseModel):
    """单个 shot 的视频提示词（文字驱动）。"""

    shot_number: int = Field(
        ...,
        ge=1,
        title="镜号",
        description="与 storyboard.shots.shot_number / frame_prompt.frames.shot_number 对齐",
    )
    motion_description: str = Field(
        ...,
        title="运动描述",
        description="完整运动 prompt（中文），涵盖运镜（pan / dolly / zoom 等） + 角色动作 + 镜头节奏。约 60-150 字",
    )
    duration_seconds: int = Field(
        ...,
        ge=2,
        le=10,
        title="时长（秒）",
        description="镜头时长，Kling 当前限制 5 / 10；快切 1-3s 优先选 5（按整数取最近值）",
    )
    quality: Quality = Field(
        default="std",
        title="质量",
        description="std = 标准；hq = 高质量（耗时与额度更高，留给关键高潮镜头）",
    )
    aspect_ratio: AspectRatio = Field(
        ...,
        title="画幅",
        description="必须与 frame_prompt.aspect_ratio 一致",
    )
    negative_prompt: Optional[str] = Field(
        None,
        title="负面",
        description="本镜负面（如 '不要抖动，不要切镜'）；为空时使用模型默认",
    )
    model_hint: ModelHint = Field(
        default="kling",
        title="模型偏好",
        description="推荐用哪个视频模型；调用 generate_video 时作为 model 入参；当前 kling 已就绪，seedance 占位",
    )


class VideoPromptSet(BaseModel):
    """全片视频提示词集合 = video_prompt_agent 的完整输出。"""

    videos: List[VideoPrompt] = Field(
        ...,
        title="视频提示词列表",
        description="全片所有 shot 的视频提示词（一一对应 storyboard.shots / frame_prompt.frames）",
        min_length=1,
    )

    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        return cls.model_json_schema()
