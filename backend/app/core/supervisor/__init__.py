"""
Supervisor 模块。

Supervisor Agent 负责动态调度 SubAgent（大纲/剧本/分镜），
通过 call_sub_agent / call_reviewer / get_workflow_state 工具驱动流水线。
"""

from app.core.supervisor.context import SupervisorContext, ReviewEntry
from app.core.supervisor.session import SupervisorSession
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
