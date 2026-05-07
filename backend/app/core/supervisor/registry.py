"""
Supervisor 专家 Agent 注册表。

当前先提供最小可插拔结构，让 Supervisor 依赖声明式 registry，
而不是把专家列表写死在 prompt 或工具实现里。
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, ConfigDict, Field, SkipValidation

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


def build_default_registry() -> SupervisorAgentRegistry:
    return SupervisorAgentRegistry(
        agents=[
            RegisteredAgent(
                name="outline_agent",
                label="Outline Agent",
                description="Creates a high-level narrative outline",
                node_keys=["outline"],
                reviewer=create_reviewer_agent(
                    criteria=["叙事结构清晰", "故事钩子有力", "人物关系明确", "情节节拍合理"],
                    min_score=7.5,
                    max_revision_rounds=2,
                    on_exhausted="accept_last",
                ),
            ),
            RegisteredAgent(
                name="script_agent",
                label="Script Agent",
                description="Creates or revises the screenplay",
                node_keys=["script"],
                reviewer=create_reviewer_agent(
                    criteria=["对白自然流畅", "场景描写具体", "情绪推进清晰", "剧情逻辑自洽"],
                    min_score=7.5,
                    max_revision_rounds=2,
                    on_exhausted="accept_last",
                ),
            ),
            RegisteredAgent(
                name="storyboard_agent",
                label="Storyboard Agent",
                description="Creates shot-group and storyboard plans",
                node_keys=["storyboard"],
                reviewer=create_reviewer_agent(
                    criteria=["镜头构图合理", "节奏分配清晰", "画面感强", "与剧本对应准确"],
                    min_score=7.5,
                    max_revision_rounds=2,
                    on_exhausted="accept_last",
                ),
            ),
        ]
    )
