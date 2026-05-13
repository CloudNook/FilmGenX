"""
StoryboardOutput：分镜结构化输出 schema。

Field 双层标记约定：
- ``title``：UI 标签（短，1-6 字）
- ``description``：LLM 指令（边界 / 示例 / 选枚举的语义）

按镜头（Shot）数组形式组织，每个镜头与剧本场景对应，包含镜头语言要素：
景别、机位、运动、构图、视觉描述、时长。
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


ShotSize = Literal[
    "ELS",   # extreme long shot 大远景
    "LS",    # long shot 远景
    "FS",    # full shot 全景
    "MS",    # medium shot 中景
    "MCU",   # medium close up 中近景
    "CU",    # close up 特写
    "ECU",   # extreme close up 大特写
    "OTS",   # over the shoulder 过肩
    "POV",   # point of view 主观镜头
    "INSERT",  # 插入镜头
]


CameraMovement = Literal[
    "STATIC",
    "PAN",       # 摇
    "TILT",      # 俯仰
    "DOLLY",     # 推拉
    "TRUCK",     # 横移
    "CRANE",     # 升降
    "HANDHELD",  # 手持
    "STEADICAM",
    "ZOOM",
    "WHIP_PAN",  # 急摇
]


CameraAngle = Literal[
    "EYE_LEVEL",
    "HIGH_ANGLE",
    "LOW_ANGLE",
    "DUTCH_ANGLE",
    "BIRDS_EYE",
    "WORMS_EYE",
]


class Shot(BaseModel):
    """单个分镜。"""

    shot_number: int = Field(
        ...,
        ge=1,
        title="镜号",
        description="镜号（全片唯一递增）",
    )
    scene_number: int = Field(
        ...,
        ge=1,
        title="场号",
        description="所属场号（对应 ScriptOutput.scenes.scene_number）",
    )
    shot_size: ShotSize = Field(
        ...,
        title="景别",
        description="景别",
    )
    camera_movement: CameraMovement = Field(
        ...,
        title="运镜",
        description="镜头运动",
    )
    camera_angle: CameraAngle = Field(
        ...,
        title="机位",
        description="机位角度",
    )
    composition_notes: str = Field(
        ...,
        title="构图",
        description="构图要点（前景/中景/背景、引导线、留白、三分法应用等）",
    )
    visual_description: str = Field(
        ...,
        title="画面描述",
        description="画面内容详述，包括人物动作、表情、关键道具、光影色彩",
    )
    characters_in_shot: List[str] = Field(
        default_factory=list,
        title="出场角色",
        description=(
            "本镜出场角色名清单（与 outline / script 中的姓名一字不差）。"
            "下游 video_prompt_agent 按此挑选 character_ref 的参考图变体。"
        ),
    )
    duration_seconds: float = Field(
        ...,
        gt=0,
        title="时长",
        description="镜头时长（秒）",
    )
    time_start_seconds: float = Field(
        ...,
        ge=0,
        title="起始时间",
        description=(
            "本镜在整片中的**绝对起始时间**（秒，从 0 开始）。"
            "由 storyboard 阶段累加生成：shot[i].time_start = shot[i-1].time_end。"
            "下游 video_prompt 必须依赖这个字段维持时间连贯性。"
        ),
    )
    time_end_seconds: float = Field(
        ...,
        gt=0,
        title="结束时间",
        description="本镜在整片中的**绝对结束时间**（秒）= time_start_seconds + duration_seconds",
    )
    audio_notes: Optional[str] = Field(
        None,
        title="音效",
        description="可选音效 / 音乐 / 环境声提示",
    )
    transition_to_next: Optional[str] = Field(
        None,
        title="转场",
        description="到下一镜的转场（cut / dissolve / match-cut / 等）",
    )


class StoryboardOutput(BaseModel):
    """分镜完整产出。"""

    title: str = Field(
        ...,
        title="标题",
        description="作品标题",
    )
    based_on_script: str = Field(
        ...,
        title="基于剧本",
        description="对应剧本版本或场景范围说明",
    )
    total_duration_seconds: float = Field(
        ...,
        gt=0,
        title="总时长",
        description=(
            "全片总时长（秒）= 所有 shot.duration_seconds 之和；"
            "也等于最后一个 shot 的 time_end_seconds。下游用此校验时间轴累加正确。"
        ),
    )
    shots: List[Shot] = Field(
        ...,
        title="镜头序列",
        description="镜头序列，按拍摄/剪辑顺序",
        min_length=1,
    )

    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        return cls.model_json_schema()
