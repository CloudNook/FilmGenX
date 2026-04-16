"""
Supervisor 流水线工作内存。
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field, model_validator

from app.core.supervisor.workflow import (
    WorkflowNodeDefinition,
    WorkflowSnapshot,
    build_workflow_snapshot,
)


class ReviewEntry(BaseModel):
    """评估历史条目。"""
    agent: str
    score: float
    passed: bool
    feedback: str
    suggestions: list[str] = []


class SupervisorContext(BaseModel):
    """
    Supervisor 的工作内存，所有 SubAgent 可访问。

    注意：SubAgent 不直接访问此对象。
    Supervisor 通过 call_sub_agent 的 context_snapshot 参数选择性注入必要数据。
    """

    supervisor_session_id: str = Field(..., description="Supervisor session ID")
    user_request: str = Field(..., description="用户原始需求")
    workflow_profile: str = Field(default="default", description="工作流配置名称")
    workflow_definitions: List[WorkflowNodeDefinition] = Field(
        default_factory=list,
        description="工作流节点定义",
    )
    workflow: WorkflowSnapshot | None = Field(
        default=None,
        description="当前版本化工作流快照",
    )
    sub_agent_sessions: Dict[str, str] = Field(
        default_factory=dict,
        description="sub_agent_name → session_id 的映射",
    )
    review_history: List[ReviewEntry] = Field(
        default_factory=list,
        description="评估历史：[{agent, score, passed, feedback}, ...]",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="附加元数据",
    )
    execution_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="结构化执行历史",
    )
    auto_run: bool = Field(
        default=False,
        description="是否允许按建议自动继续执行",
    )

    @model_validator(mode="after")
    def _populate_workflow(self):
        if self.workflow is None:
            self.workflow = build_workflow_snapshot(
                profile=self.workflow_profile,
                definitions=self.workflow_definitions,
            )
        return self
