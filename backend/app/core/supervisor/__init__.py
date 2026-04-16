"""
Supervisor 模块。

重构后的 Supervisor 是高层工作流编排器：
- 用版本化工作流快照管理节点状态
- 用 registry 管理可插拔专家 Agent
- 继续复用底层 Agent runtime
"""

from app.core.supervisor.context import SupervisorContext, ReviewEntry
from app.core.supervisor.session import SupervisorSession
from app.core.supervisor.registry import (
    RegisteredAgent,
    SupervisorAgentRegistry,
    build_default_registry,
    build_default_workflow_definitions,
)
from app.core.supervisor.workflow import (
    SuggestedAction,
    WorkflowNodeDefinition,
    WorkflowNodeState,
    WorkflowSnapshot,
    apply_node_update,
    build_suggested_actions,
    build_workflow_snapshot,
    confirm_node,
)
from app.core.supervisor.events import (
    SubAgentStartEvent,
    SubAgentEndEvent,
    ReviewStartEvent,
    ReviewEndEvent,
    SupervisorDoneEvent,
    SupervisorStreamEvent,
)
from app.core.supervisor.supervisor import SupervisorAgent
from app.core.supervisor.factory import create_supervisor
from app.core.supervisor.tools import (
    call_sub_agent,
    call_reviewer,
    get_workflow_state,
    get_supervisor_tool_schemas,
)
from app.core.supervisor.reviewer import build_reviewer_prompt

__all__ = [
    # Context & Session
    "SupervisorContext",
    "ReviewEntry",
    "SupervisorSession",
    "RegisteredAgent",
    "SupervisorAgentRegistry",
    "WorkflowNodeDefinition",
    "WorkflowNodeState",
    "WorkflowSnapshot",
    "SuggestedAction",
    "build_default_registry",
    "build_default_workflow_definitions",
    "build_workflow_snapshot",
    "build_suggested_actions",
    "apply_node_update",
    "confirm_node",
    # Events
    "SubAgentStartEvent",
    "SubAgentEndEvent",
    "ReviewStartEvent",
    "ReviewEndEvent",
    "SupervisorDoneEvent",
    "SupervisorStreamEvent",
    # Core
    "SupervisorAgent",
    "create_supervisor",
    # Tools
    "call_sub_agent",
    "call_reviewer",
    "get_workflow_state",
    "get_supervisor_tool_schemas",
    # Reviewer
    "build_reviewer_prompt",
]
