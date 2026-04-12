"""
Supervisor 流水线流式事件扩展。

在 app.core.agent.base.StreamEvent 基础上新增：
- SubAgentStartEvent / SubAgentEndEvent
- ReviewStartEvent / ReviewEndEvent
- SupervisorDoneEvent

每个事件携带 source 字段，用于前端渲染区分来源。
"""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel

from app.core.agent.base import StreamEvent  # noqa: F401 — re-exported for consumers


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


class HumanReviewEvent(BaseModel):
    """SubAgent 完成，等待用户审阅。"""
    type: Literal["human_review"] = "human_review"
    sub_agent_name: str
    output: str
    source: str = "supervisor"


class SupervisorDoneEvent(BaseModel):
    """Supervisor 流水线执行完毕。"""
    type: Literal["supervisor_done"] = "supervisor_done"
    supervisor_session_id: str
    artifacts: Dict[str, Any]
    final_result: str
    source: str = "supervisor"


SupervisorStreamEvent = Union[
    SubAgentStartEvent,
    SubAgentEndEvent,
    ReviewStartEvent,
    ReviewEndEvent,
    HumanReviewEvent,
    SupervisorDoneEvent,
]
