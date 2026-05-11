"""
Supervisor 流水线流式事件扩展。

在 app.core.agent.base.StreamEvent 基础上新增：
- 带 source / session_id 的 supervisor 流式事件
- SubAgentStartEvent / SubAgentEndEvent
- ReviewStartEvent / ReviewEndEvent
- SupervisorDoneEvent
"""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel

from app.core.agent.base import StreamEvent  # noqa: F401 – re-exported for consumers


class SupervisorThinkingEvent(BaseModel):
    """带来源信息的 thinking 事件。"""
    type: Literal["thinking"] = "thinking"
    content: str
    source: str = "supervisor"
    session_id: Optional[str] = None


class SupervisorTextEvent(BaseModel):
    """带来源信息的 text 事件。"""
    type: Literal["text"] = "text"
    content: str
    source: str = "supervisor"
    session_id: Optional[str] = None


class SupervisorToolStartEvent(BaseModel):
    """带来源信息的 tool_start 事件。"""
    type: Literal["tool_start"] = "tool_start"
    tool_call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    source: str = "supervisor"
    session_id: Optional[str] = None


class SupervisorToolEndEvent(BaseModel):
    """带来源信息的 tool_end 事件。"""
    type: Literal["tool_end"] = "tool_end"
    tool_call_id: str
    tool_name: str
    result: Any
    is_error: bool = False
    source: str = "supervisor"
    session_id: Optional[str] = None


class SupervisorErrorEvent(BaseModel):
    """带来源信息的 error 事件。"""
    type: Literal["error"] = "error"
    error: str
    source: str = "supervisor"
    session_id: Optional[str] = None


class SubAgentStartEvent(BaseModel):
    """SubAgent 开始执行。"""
    type: Literal["sub_agent_start"] = "sub_agent_start"
    sub_agent_name: str
    session_id: str
    task_description: str
    source: str = "supervisor"


class SubAgentEndEvent(BaseModel):
    """SubAgent 执行完毕。"""
    type: Literal["sub_agent_end"] = "sub_agent_end"
    sub_agent_name: str
    session_id: str
    result: Dict[str, Any]
    review_result: Optional[Dict[str, Any]] = None
    # sub-agent 本次运行的累计 usage（来自其 DoneEvent.result.usage）。
    # supervisor 流里被前端用于实时 token 计费；后端 runtime 用于累加 workflow.total_tokens。
    usage: Optional[Dict[str, Any]] = None
    loop_count: Optional[int] = None
    source: str = "supervisor"


class ReviewStartEvent(BaseModel):
    """Reviewer Agent 开始评估。"""
    type: Literal["review_start"] = "review_start"
    sub_agent_name: str
    criteria: List[str]
    source: str = "supervisor"


class ReviewEndEvent(BaseModel):
    """Reviewer Agent 评估完毕。"""
    type: Literal["review_end"] = "review_end"
    sub_agent_name: str
    score: float
    passed: bool
    feedback: str
    suggestions: Optional[List[str]] = None
    source: str = "supervisor"


class SupervisorStartedEvent(BaseModel):
    """Supervisor 流开始事件。"""

    type: Literal["supervisor_started"] = "supervisor_started"
    workflow_id: int
    supervisor_session_id: str
    status: str
    workflow_profile: str
    auto_run: bool
    source: str = "supervisor"


class SupervisorDoneEvent(BaseModel):
    """Supervisor 流水线执行完毕。"""
    type: Literal["supervisor_done"] = "supervisor_done"
    supervisor_session_id: str
    workflow: Dict[str, Any]
    final_result: str
    source: str = "supervisor"


SupervisorStreamEvent = Union[
    SupervisorThinkingEvent,
    SupervisorTextEvent,
    SupervisorToolStartEvent,
    SupervisorToolEndEvent,
    SupervisorErrorEvent,
    SubAgentStartEvent,
    SubAgentEndEvent,
    ReviewStartEvent,
    ReviewEndEvent,
    SupervisorStartedEvent,
    SupervisorDoneEvent,
]
