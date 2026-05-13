"""
ScriptOutput：剧本结构化输出 schema。

Field 双层标记约定：
- ``title``：UI 标签（短，1-6 字）
- ``description``：LLM 指令（边界 / 字数 / 示例）

字段与 script_agent 实际输出 + ``ScriptValue`` KV 保持一致：
- 顶层 ``summary`` / ``scene_count`` / ``total_duration_seconds`` / ``famous_quotes`` 给
  KV / 前端宣发用
- Scene 内 ``action`` 改为单字符串（之前是 ``actions: List[SceneAction]``——分段过细，
  LLM 偏好整段动作描写一气呵成；同一场内多段动作用 ``\n`` 分隔即可）
- ``dialogue``（之前叫 ``dialogues``，与 ``action`` 单复数对齐）
- ``characters_present``：本场出场角色名清单，便于 storyboard / video_prompt 查找参考图
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


SceneTimeOfDay = Literal[
    "DAY", "NIGHT", "DAWN", "DUSK",
    "MORNING", "AFTERNOON", "EVENING",
    "CONTINUOUS", "LATER", "MOMENTS_LATER", "SAME",
]
SceneSpace = Literal["INT", "EXT", "INT/EXT"]


class DialogueLine(BaseModel):
    """单条对白行。"""

    character: str = Field(
        ...,
        title="角色",
        description="角色名（与 outline.characters.name 一字不差）",
    )
    line: str = Field(
        ...,
        title="台词",
        description="台词内容",
    )
    parenthetical: Optional[str] = Field(
        None,
        title="表演提示",
        description=(
            "可选表演提示（如 '低声'、'嘲讽'）。**克制使用**——演员能从台词推断的情绪不写，"
            "只在反讽 / 关键动作 / 易误读时保留。"
        ),
    )


class Scene(BaseModel):
    """单个场景。"""

    scene_number: int = Field(
        ...,
        ge=1,
        title="场号",
        description="场号（全片唯一递增）",
    )
    space: SceneSpace = Field(
        ...,
        title="空间",
        description="内景 INT / 外景 EXT / 混合 INT/EXT",
    )
    location: str = Field(
        ...,
        title="地点",
        description=(
            "地点（如 '云岚宗广场'）。**全片同名地点字符串一字不差**——"
            "下游 scene_ref 按 location 去重出参考图，拼写漂移 = 同一地拍两套图。"
        ),
    )
    time_of_day: SceneTimeOfDay = Field(
        ...,
        title="时间",
        description="时段；同地点跨时段（白天 / 夜晚 / 雨）保持 location 不变，改 time_of_day",
    )
    summary: str = Field(
        ...,
        title="本场目的",
        description="一句话说明这场戏推进了哪个 key_arc / 没了这场剧情塌不塌（存在理由）",
    )
    emotional_beat: str = Field(
        ...,
        title="情绪节拍",
        description="本场 in-beat → turn → out-beat 简写（如 '愤怒 → 受挫 → 决意'）",
    )
    characters_present: List[str] = Field(
        default_factory=list,
        title="出场角色",
        description="本场出场角色名清单，便于 storyboard / video_prompt 按名查参考图",
    )
    action: str = Field(
        ...,
        title="动作描写",
        description=(
            "完整动作 / 场面描写（一段或多段，多段用 ``\\n`` 分隔）。"
            "**只写镜头看得到的**——心理 / 抽象 / 状态必须转化为可见外部信号。"
        ),
    )
    dialogue: List[DialogueLine] = Field(
        default_factory=list,
        title="对白",
        description="对白序列。纯动作戏可空。",
    )
    duration_estimate_seconds: Optional[int] = Field(
        None,
        ge=1,
        title="时长（秒）",
        description=(
            "估算时长（秒）。1 页剧本 ≈ 1 分钟成片（业内通用估算）。"
            "下游 storyboard 用此累加全片 total_duration。"
        ),
    )


class ScriptOutput(BaseModel):
    """剧本完整产出。

    字段约定：
    - 顶层 ``summary`` / ``scene_count`` / ``total_duration_seconds`` / ``famous_quotes``
      → supervisor 抽出写 ``script.main`` KV。
    - ``scenes`` 是完整场景列表，是 storyboard / video_prompt 的输入源。
    """

    summary: str = Field(
        ...,
        title="综述",
        description="200-400 字本剧综述，写实际拍得到什么",
    )
    scene_count: int = Field(
        ...,
        ge=1,
        title="场数",
        description="场景总数（= scenes 长度）",
    )
    total_duration_seconds: int = Field(
        ...,
        gt=0,
        title="总时长",
        description="所有 scene.duration_estimate_seconds 之和（整数秒）",
    )
    scenes: List[Scene] = Field(
        ...,
        title="场景序列",
        description="场景序列（按时序）",
        min_length=1,
    )
    famous_quotes: List[str] = Field(
        default_factory=list,
        title="金句",
        description="可选，本剧 2-4 句金句，给宣发 / 片头剪辑用",
    )

    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        return cls.model_json_schema()
