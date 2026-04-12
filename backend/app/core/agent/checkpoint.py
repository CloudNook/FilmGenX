"""
Agent checkpoint model for interrupt/resume HITL.

Serialized snapshot of Agent state at interrupt point,
used to restore execution when human submits review.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.core.agent.base import InterruptConfig


class AgentCheckpoint(BaseModel):
    """
    Snapshot of Agent state at interrupt point.

    Saved by AgentLoop when an interrupt is detected.
    Loaded by Agent.resume() to restore execution.
    """
    session_id: str
    messages: List[Dict[str, Any]]
    loop_count: int
    interrupt_tool_name: str
    interrupt_config: InterruptConfig
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
