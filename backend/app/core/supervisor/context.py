"""
Supervisor 流水线工作内存。
"""

from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class SupervisorContext(BaseModel):
    """
    Supervisor 的工作内存，所有 SubAgent 可访问。

    注意：SubAgent 不直接访问此对象。
    Supervisor 通过 call_sub_agent 的 context_snapshot 参数选择性注入必要数据。
    """

    supervisor_session_id: str = Field(..., description="Supervisor session ID")
    user_request: str = Field(..., description="用户原始需求")
    current_phase: str = Field(
        default="init",
        description="当前流水线阶段：init | outline | script | storyboard | review | done",
    )
    artifacts: Dict[str, Any] = Field(
        default_factory=dict,
        description="各阶段产物：{outline: {...}, script: {...}, storyboard: {...}}",
    )
    sub_agent_sessions: Dict[str, str] = Field(
        default_factory=dict,
        description="sub_agent_name → session_id 的映射",
    )
    review_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="评估历史：[{agent, score, passed, feedback}, ...]",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="附加元数据",
    )
