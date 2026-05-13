"""
VideoPromptSet：每个 shot 的视频提示词（Layer 4）。

由 video_prompt_agent 在 scene_ref 完成后产出。video_prompt_agent 通过
``character_ref`` / ``scene_ref`` 输出的 asset_code 拿到参考图，再用文字 prompt
驱动 Seedance reference-to-video 出片——**不再走"先出首帧图再驱动视频"的路径**。

下游：
- ``motion_description`` + ``duration_seconds`` 喂给 ``generate_video`` 工具
- 参考图通过 asset_code 传入 generate_video 的 asset_codes 参数
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


AspectRatio = Literal["16:9", "9:16", "1:1"]
Quality = Literal["std", "hq"]


class VideoPrompt(BaseModel):
    """单个 shot 的视频提示词（文字驱动）。"""

    shot_number: int = Field(
        ...,
        ge=1,
        title="镜号",
        description="与 storyboard.shots.shot_number 对齐",
    )
    time_start_seconds: float = Field(
        ...,
        ge=0,
        title="起始时间",
        description=(
            "本镜在整片中的**绝对起始时间**（秒），与 storyboard.shots[i].time_start_seconds 一致。"
            "Seedance 单次最多 15 秒，整片往往拆成多镜——这个字段告诉模型/审稿人"
            "'当前在整片的哪个时间窗口'，是剧情连贯性判断的依据。"
        ),
    )
    time_end_seconds: float = Field(
        ...,
        gt=0,
        title="结束时间",
        description="本镜在整片中的**绝对结束时间**（秒）= time_start_seconds + duration_seconds",
    )
    recap_previous: Optional[str] = Field(
        None,
        title="前情提要",
        description=(
            "前面剧情的简短摘要（1-2 句，≤80 字），让 Seedance 理解'当前镜头之前发生了什么'。"
            "**第 1 镜（time_start=0）可为空**；其他镜头必填。"
            "示例：'主角刚被纳兰嫣然嘲讽\"废物\"，低头握拳压抑愤怒。'"
        ),
    )
    continuity_from_previous: Optional[str] = Field(
        None,
        title="衔接上一镜",
        description=(
            "与上一镜的视觉衔接（主体位置 / 动作落点 / 情绪状态 / 光照方向）。"
            "**第 1 镜可为空**；其他镜头必填——保证人物不漂移、剧情连贯。"
            "示例：'上一镜主角在画面右三分位低头握拳；本镜衔接抬头转身，"
            "光照仍为黄昏侧逆，主体保持右侧。'"
        ),
    )
    motion_description: str = Field(
        ...,
        title="运动描述",
        description=(
            "完整运动 prompt（中文），按 timing notation 写：0-Xs / X-Ys / Y-Zs 分段。"
            "涵盖运镜（pan / dolly / push-in / static 等）+ 角色动作 + 节奏 + 起手构图。"
            "**不要重复 recap_previous / continuity_from_previous 的内容**——那两个字段是上下文，"
            "本字段只写当前镜头的运动指令。约 80-180 字。"
        ),
    )
    duration_seconds: int = Field(
        ...,
        ge=4,
        le=15,
        title="时长（秒）",
        description=(
            "镜头时长（Seedance 限制 4-15 整数）；"
            "= time_end_seconds - time_start_seconds（取整）"
        ),
    )
    quality: Quality = Field(
        default="std",
        title="质量",
        description="std = 标准；hq = 高质量（耗时与额度更高，留给关键高潮镜头）",
    )
    aspect_ratio: AspectRatio = Field(
        ...,
        title="画幅",
        description="必须与 storyboard 中该 shot 的 aspect_ratio 一致",
    )
    negative_prompt: Optional[str] = Field(
        None,
        title="负面",
        description="本镜负面（如 '不要抖动，不要切镜'）；为空时使用模型默认",
    )


class VideoPromptSet(BaseModel):
    """全片视频提示词集合 = video_prompt_agent 的完整输出。"""

    total_duration_seconds: float = Field(
        ...,
        gt=0,
        title="总时长",
        description="全片总时长（秒），与 storyboard.total_duration_seconds 一致",
    )
    videos: List[VideoPrompt] = Field(
        ...,
        title="视频提示词列表",
        description="全片所有 shot 的视频提示词（一一对应 storyboard.shots），按 time_start 升序",
        min_length=1,
    )

    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        return cls.model_json_schema()
