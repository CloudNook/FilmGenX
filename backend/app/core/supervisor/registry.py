"""
Supervisor 专家 Agent 注册表。

当前先提供最小可插拔结构，让 Supervisor 依赖声明式 registry，
而不是把专家列表写死在 prompt 或工具实现里。

业务装配（prompt / response_schema / reviewer prompt 等领域文本）来自
``app.agents``，本模块只负责框架结构。
"""

from __future__ import annotations

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
    return [
        WorkflowNodeDefinition(
            key="outline",
            label="Outline",
            node_type="text",
            depends_on=[],
        ),
        WorkflowNodeDefinition(
            key="script",
            label="Script",
            node_type="text",
            depends_on=["outline"],
        ),
        WorkflowNodeDefinition(
            key="storyboard",
            label="Storyboard",
            node_type="plan",
            depends_on=["script"],
        ),
    ]


def _build_registered_agent(
    *,
    name: str,
    label: str,
    description: str,
    node_keys: list[str],
) -> RegisteredAgent:
    """从 app.agents 装配 prompt / schema / reviewer，构造一个 RegisteredAgent。"""
    return RegisteredAgent(
        name=name,
        label=label,
        description=description,
        node_keys=node_keys,
        prompt=SUB_AGENT_PROMPT[name],
        response_schema=SUB_AGENT_RESPONSE_SCHEMA[name],
        reviewer=create_reviewer_agent(
            prompt=REVIEWER_PROMPT[name],
            criteria=REVIEWER_CRITERIA[name],
            min_score=7.5,
            max_revision_rounds=2,
            on_exhausted="accept_last",
        ),
    )


def build_default_registry() -> SupervisorAgentRegistry:
    return SupervisorAgentRegistry(
        agents=[
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
        ]
    )
