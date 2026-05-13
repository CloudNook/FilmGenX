"""
Supervisor 专家 Agent 注册表。

当前先提供最小可插拔结构，让 Supervisor 依赖声明式 registry，
而不是把专家列表写死在 prompt 或工具实现里。

业务装配（prompt / response_schema / reviewer prompt 等领域文本）来自
``app.agents``，本模块只负责框架结构。
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Optional

from pydantic import BaseModel, ConfigDict, Field, SkipValidation

from app.agents import (
    REVIEWER_CRITERIA,
    REVIEWER_PROMPT,
    SUB_AGENT_PROMPT,
    SUB_AGENT_RESPONSE_SCHEMA,
)
from app.core.agent.base import Reviewer
from app.core.agent.reviewer import create_reviewer_agent
from app.core.supervisor.workflow import WorkflowNodeDefinition

# 触发 builtin tools (load_skill / load_skill_reference) 的 @register_tool 注册，
# 否则 ToolRegistry 里这两个名字查不到 schema。
from app.core.tools import builtin as _builtin_tools  # noqa: F401
from app.core.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


# 默认给所有 sub-agent 装载的工具：skill 渐进式披露的两个入口。
# 没有这两个工具，sub-agent prompt 里写的 "调 load_skill 加载主体" 完全是死的。
DEFAULT_SUB_AGENT_TOOL_NAMES: list[str] = [
    "load_skill",
    "load_skill_reference",
]


def _default_sub_agent_tool_schemas() -> list[dict[str, Any]]:
    """从 ToolRegistry 取出默认 sub-agent 工具的 schema 列表。"""
    schemas: list[dict[str, Any]] = []
    for tool_name in DEFAULT_SUB_AGENT_TOOL_NAMES:
        tool = ToolRegistry.get(tool_name)
        if tool is None:
            logger.warning(
                "[registry] default sub-agent tool %r not registered; sub-agent will lack this capability",
                tool_name,
            )
            continue
        schemas.append(tool.get_schema())
    return schemas


class RegisteredAgent(BaseModel):
    # Reviewer 是 callable Protocol，不在 Pydantic 已知类型里，需要放开 arbitrary_types。
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    label: str
    description: str
    node_keys: list[str]
    prompt: str = ""
    response_schema: Optional[dict[str, Any]] = None
    tools: list[dict[str, Any]] = Field(default_factory=list)
    skill_names: list[str] = Field(default_factory=list)
    model: str = "gemini-3-flash-preview"
    # Protocol 本身没 @runtime_checkable，Pydantic 默认会尝试 isinstance(value, Reviewer)
    # 而 isinstance 对未标 runtime_checkable 的 Protocol 直接报错；这里跳过校验，
    # 静态类型仍是 Optional[Reviewer]，由调用方 / type checker 保证契约。
    reviewer: Annotated[Optional[Reviewer], SkipValidation()] = None


class SupervisorAgentRegistry(BaseModel):
    agents: list[RegisteredAgent] = Field(default_factory=list)

    def get(self, name: str) -> RegisteredAgent | None:
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None

    def agent_names(self) -> list[str]:
        return [agent.name for agent in self.agents]


def build_default_workflow_definitions() -> list[WorkflowNodeDefinition]:
    """完整生产链路（plan b）的 7 个节点。

    Layer 1 创作层：outline → script → storyboard
    Layer 2 视觉锚点：visual_style
    Layer 3 参考图设计：character_ref → scene_ref（顺序跑；并行编排是 Phase 2）
    Layer 4 视频提示词：video_prompt（直接消费 storyboard + character_ref / scene_ref 参考图，
            走 Seedance reference-to-video，不再有中间"首帧图"节点）
    """
    return [
        # Layer 1
        WorkflowNodeDefinition(
            key="outline", label="Outline", node_type="text", depends_on=[],
        ),
        WorkflowNodeDefinition(
            key="script", label="Script", node_type="text", depends_on=["outline"],
        ),
        WorkflowNodeDefinition(
            key="storyboard", label="Storyboard", node_type="plan", depends_on=["script"],
        ),
        # Layer 2
        WorkflowNodeDefinition(
            key="visual_style", label="Visual Style", node_type="text", depends_on=["storyboard"],
        ),
        # Layer 3
        WorkflowNodeDefinition(
            key="character_ref", label="Character Ref", node_type="plan", depends_on=["visual_style"],
        ),
        WorkflowNodeDefinition(
            key="scene_ref", label="Scene Ref", node_type="plan", depends_on=["character_ref"],
        ),
        # Layer 4
        WorkflowNodeDefinition(
            key="video_prompt", label="Video Prompt", node_type="plan", depends_on=["scene_ref"],
        ),
    ]


def _resolve_tool_schemas(extra_tool_names: list[str]) -> list[dict[str, Any]]:
    """默认 skill 工具 + 额外指定的工具。命中 extra 的工具不存在时记 warning。"""
    schemas = list(_default_sub_agent_tool_schemas())
    for tool_name in extra_tool_names:
        tool = ToolRegistry.get(tool_name)
        if tool is None:
            logger.warning(
                "[registry] extra tool %r not registered; skipping for sub-agent injection",
                tool_name,
            )
            continue
        schemas.append(tool.get_schema())
    return schemas


def _build_registered_agent(
    *,
    name: str,
    label: str,
    description: str,
    node_keys: list[str],
    extra_tool_names: list[str] | None = None,
) -> RegisteredAgent:
    """从 app.agents 装配 prompt / schema / reviewer，构造一个 RegisteredAgent。

    Args:
        extra_tool_names: 在默认 skill 工具之外，额外挂载到此 sub-agent 的工具名列表。
            目前用于给 character_ref / scene_ref / video_prompt agent 暴露 media gen 工具。
    """
    return RegisteredAgent(
        model="gemini-3.1-pro-preview",
        name=name,
        label=label,
        description=description,
        node_keys=node_keys,
        prompt=SUB_AGENT_PROMPT[name],
        response_schema=SUB_AGENT_RESPONSE_SCHEMA[name],
        # 默认装载 load_skill / load_skill_reference + 可选 extra（如 media gen 工具）
        tools=_resolve_tool_schemas(extra_tool_names or []),
        reviewer=create_reviewer_agent(
            prompt=REVIEWER_PROMPT[name],
            criteria=REVIEWER_CRITERIA[name],
            min_score=7.5,
            max_revision_rounds=2,
            on_exhausted="accept_last",
        ),
    )


def build_default_registry() -> SupervisorAgentRegistry:
    """完整生产链路（plan b）的 7 个 sub-agent。

    工具分配按"谁产出资产 KV，谁就有出图工具"：
    - character_ref_agent / scene_ref_agent 挂 ``generate_image``
    - video_prompt_agent 挂 ``generate_video``（Seedance reference-to-video，
      参考图来自 character_ref / scene_ref 的 asset_code）
    - supervisor 不直接挂图像 / 视频工具，要出图就 ``call_sub_agent``

    出图后由 agent 调 ``memory_save`` 把 OSS URL 回填到对应 KV
    （character.three_view_url / scene.reference_image_urls / 等）。
    """
    return SupervisorAgentRegistry(
        agents=[
            # Layer 1 创作层
            _build_registered_agent(
                name="outline_agent",
                label="Outline Agent",
                description="Creates a high-level narrative outline",
                node_keys=["outline"],
            ),
            _build_registered_agent(
                name="script_agent",
                label="Script Agent",
                description="Creates or revises the screenplay",
                node_keys=["script"],
            ),
            _build_registered_agent(
                name="storyboard_agent",
                label="Storyboard Agent",
                description="Creates shot-group and storyboard plans",
                node_keys=["storyboard"],
            ),
            # Layer 2 视觉锚点
            _build_registered_agent(
                name="visual_style_agent",
                label="Visual Style Agent",
                description="Defines global visual anchor (palette / lighting / composition / art style)",
                node_keys=["visual_style"],
            ),
            # Layer 3 参考图设计 —— 出三视图 / 场景参考图，回填 KV
            _build_registered_agent(
                name="character_ref_agent",
                label="Character Ref Agent",
                description="Designs character reference image prompts (base + expressions + outfits) and generates three-view / reference images",
                node_keys=["character_ref"],
                extra_tool_names=["generate_image"],
            ),
            _build_registered_agent(
                name="scene_ref_agent",
                label="Scene Ref Agent",
                description="Designs scene reference image prompts (deduped by location, with time variants) and generates location reference images",
                node_keys=["scene_ref"],
                extra_tool_names=["generate_image"],
            ),
            # Layer 4 视频提示词（直接消费 character_ref / scene_ref 的参考图，
            # 通过 Seedance reference-to-video 出片）
            _build_registered_agent(
                name="video_prompt_agent",
                label="Video Prompt Agent",
                description="Produces per-shot text-to-video prompts ready for Seedance reference-to-video, then concatenates all segments into a final cut",
                node_keys=["video_prompt"],
                # generate_video 出单段；concat_videos 把多段按 storyboard 顺序拼成成片
                extra_tool_names=["generate_video", "concat_videos"],
            ),
        ]
    )
