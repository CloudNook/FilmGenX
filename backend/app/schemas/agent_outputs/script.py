"""
ScriptOutput：剧本结构化输出 schema。

按场景（Scene）数组形式组织，每个场景包含场景头、描写、对白节拍。
对白和动作描写分离，方便后续制作侧消费。
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


SceneTimeOfDay = Literal["DAY", "NIGHT", "DAWN", "DUSK", "CONTINUOUS", "LATER"]
SceneSpace = Literal["INT", "EXT", "INT/EXT"]


class DialogueLine(BaseModel):
    """单条对白行。"""

    character: str = Field(..., description="角色名")
    line: str = Field(..., description="台词内容")
    parenthetical: Optional[str] = Field(
        None,
        description="可选表演提示（如 “低声”、“犹豫地”），克制使用",
    )


class SceneAction(BaseModel):
    """单段动作 / 描写（介于对白之间的场面调度）。"""

    description: str = Field(..., description="可视化的动作 / 镜头描写，避免心理活动")


SceneEvent = Dict[str, Any]


class Scene(BaseModel):
    """单个场景。"""

    scene_number: int = Field(..., ge=1, description="场号")
    space: SceneSpace = Field(..., description="内景/外景")
    location: str = Field(..., description="地点（如 “客厅”、“地铁站台”）")
    time_of_day: SceneTimeOfDay = Field(..., description="时间")
    heading: str = Field(
        ...,
        description="标准场头（自动拼装：{space}. {location} - {time_of_day}）",
    )
    summary: str = Field(..., description="本场目的，一句话说明这场戏推进了什么")
    emotional_beat: str = Field(
        ...,
        description="本场核心情绪节拍（进入情绪 → 转折 → 留白）",
    )
    actions: List[SceneAction] = Field(
        default_factory=list,
        description="动作 / 描写片段，按时间顺序",
    )
    dialogues: List[DialogueLine] = Field(
        default_factory=list,
        description="对白序列，与 actions 共同构成场景叙事",
    )
    duration_estimate_seconds: Optional[int] = Field(
        None,
        ge=1,
        description="估算时长（秒），用于后续节奏评估",
    )


class ScriptOutput(BaseModel):
    """剧本完整产出。"""

    title: str = Field(..., description="作品标题（与 outline 一致）")
    based_on_outline: str = Field(
        ...,
        description="对应大纲版本号或 logline 摘要，便于回溯",
    )
    scenes: List[Scene] = Field(
        ...,
        description="场景序列，按拍摄/叙事顺序",
        min_length=1,
    )

    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        return cls.model_json_schema()
