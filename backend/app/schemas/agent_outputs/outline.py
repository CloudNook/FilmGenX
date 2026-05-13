"""
OutlineOutput：剧情大纲结构化输出 schema。

Field 双层标记约定：
- ``title``：UI 标签（短，1-6 字），前端拿去做卡片字段标签 / 表头
- ``description``：LLM 指令（指令式，告诉 LLM 怎么填、字数 / 边界 / 示例）

字段与 outline_agent 实际输出 + ``OutlineValue`` KV 保持一致：
- 单段式综述 (``summary``) 替代了旧 ``title + synopsis`` 拆分
- ``key_arcs`` 列表替代了旧 3 幕结构（``acts`` / ``beats``）—— 短剧场景下三幕过重
- ``duration_seconds`` 是顶层硬约束，给下游 storyboard / video_prompt 用
- ``CharacterArc.function`` 替代了旧 ``arc_summary`` —— 表达"角色在故事里承担什么功能"
  比"一句话弧线"更适合极短剧
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


CharacterRole = Literal[
    "protagonist",
    "antagonist",
    "deuteragonist",
    "supporting",
    "foil",
    "mentor",
]


class CharacterArc(BaseModel):
    """单个角色的弧线。"""

    name: str = Field(
        ...,
        title="姓名",
        description="角色名（中文）；与下游 character_ref / script / video_prompt 引用的姓名一字不差",
    )
    role: CharacterRole = Field(
        ...,
        title="定位",
        description="角色定位",
    )
    want: str = Field(
        ...,
        title="想要",
        description="角色表层渴望（外在目标，可被夺走）",
    )
    need: str = Field(
        ...,
        title="需要",
        description="角色内在需要（成长目标 / 主角自己不知道或拒绝承认的真相）",
    )
    function: str = Field(
        ...,
        title="叙事功能",
        description=(
            "角色在故事里承担的功能（推动 / 对抗 / 反衬 / 见证）。"
            "比泛泛的'人物弧线'更可执行——下游 character_ref 看这个挑表情变体侧重。"
        ),
    )


class OutlineOutput(BaseModel):
    """剧情大纲完整产出。

    字段约定：
    - ``summary``：剧情综述，整体能量曲线 / 起承转合一段话。这是给下游所有 agent 看的"骨架"。
    - ``logline``：25-40 字一句话故事钩子。
    - ``characters``：主要角色 + 各自的 want / need / 叙事功能。
    - ``key_arcs``：关键情节段落列表（按时序），通常 3-5 项；短剧也按节拍数（不削节拍只削细节）。
    - ``duration_seconds``：预期总时长（秒），下游 storyboard / video_prompt 按此做时间轴累加。
    - ``themes``：可选主题词列表（如：复仇 / 自我认同 / 阶级冲突）。
    """

    summary: str = Field(
        ...,
        title="综述",
        description="200-400 字一段式剧情综述，含三幕主线 + 主角弧 + 整体能量曲线",
    )
    logline: str = Field(
        ...,
        title="Logline",
        description="一句话故事钩子（25-40 字），含 [主角身份] + [外在欲望] + [核心对抗] + [独特风险] 4 要素",
    )
    characters: List[CharacterArc] = Field(
        default_factory=list,
        title="角色",
        description="主要角色弧线（至少包含主角 + 关键反派）",
    )
    key_arcs: List[str] = Field(
        ...,
        title="关键弧",
        description=(
            "关键情节段落列表（按时序），每段 1-2 句描述事件 + 情绪转折，不写镜头。"
            "短剧（≤3 分钟）建议 3-5 项；长剧可 6-8 项。"
        ),
        min_length=2,
    )
    duration_seconds: int = Field(
        ...,
        gt=0,
        title="时长",
        description="预期总时长（秒）。短剧 ≤180s；长片 1800-7200s。下游 storyboard 按此累加时间轴。",
    )
    themes: List[str] = Field(
        default_factory=list,
        title="主题",
        description=(
            "可选主题词列表（如：复仇 / 自我认同 / 阶级冲突）。"
            "**只列标签，不在 summary 里宣讲**——主题通过情节落点浮现。"
        ),
    )

    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        """返回喂给 LLM response_schema 的 JSON Schema。"""
        return cls.model_json_schema()
