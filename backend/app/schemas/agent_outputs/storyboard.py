"""
StoryboardOutput：分镜结构化输出 schema。

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

    shot_number: int = Field(..., ge=1, description="镜号（全片唯一递增）")
    scene_number: int = Field(..., ge=1, description="所属场号（对应 ScriptOutput.scenes.scene_number）")
    shot_size: ShotSize = Field(..., description="景别")
    camera_movement: CameraMovement = Field(..., description="镜头运动")
    camera_angle: CameraAngle = Field(..., description="机位角度")
    composition_notes: str = Field(
        ...,
        description="构图要点（前景/中景/背景、引导线、留白、三分法应用等）",
    )
    visual_description: str = Field(
        ...,
        description="画面内容详述，包括人物动作、表情、关键道具、光影色彩",
    )
    duration_seconds: float = Field(
        ...,
        gt=0,
        description="镜头时长（秒）",
    )
    audio_notes: Optional[str] = Field(
        None,
        description="可选音效 / 音乐 / 环境声提示",
    )
    transition_to_next: Optional[str] = Field(
        None,
        description="到下一镜的转场（cut / dissolve / match-cut / 等）",
    )


class StoryboardOutput(BaseModel):
    """分镜完整产出。"""

    title: str = Field(..., description="作品标题")
    based_on_script: str = Field(
        ...,
        description="对应剧本版本或场景范围说明",
    )
    shots: List[Shot] = Field(
        ...,
        description="镜头序列，按拍摄/剪辑顺序",
        min_length=1,
    )

    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        return cls.model_json_schema()
