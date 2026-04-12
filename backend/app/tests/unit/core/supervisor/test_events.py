import pytest
from app.core.supervisor.events import (
    SubAgentStartEvent,
    SubAgentEndEvent,
    ReviewStartEvent,
    ReviewEndEvent,
    SupervisorDoneEvent,
    SupervisorStreamEvent,
)


def test_sub_agent_start_event():
    event = SubAgentStartEvent(
        sub_agent_name="outline_writer",
        session_id="sub-outline-001",
        task_description="生成视频大纲",
    )
    assert event.type == "sub_agent_start"
    assert event.sub_agent_name == "outline_writer"
    assert event.source == "supervisor"


def test_sub_agent_end_event():
    event = SubAgentEndEvent(
        sub_agent_name="outline_writer",
        session_id="sub-outline-001",
        result={},
    )
    assert event.type == "sub_agent_end"
    assert event.review_result is None


def test_review_end_event():
    event = ReviewEndEvent(
        sub_agent_name="outline_writer",
        score=8.5,
        passed=True,
        feedback="结构完整，逻辑清晰",
    )
    assert event.passed is True
    assert event.score == 8.5


def test_supervisor_done_event():
    event = SupervisorDoneEvent(
        supervisor_session_id="sv-abc123",
        artifacts={"outline": {"title": "星际穿越"}},
        final_result="流水线执行完毕",
    )
    assert event.supervisor_session_id == "sv-abc123"
    assert event.artifacts["outline"]["title"] == "星际穿越"


def test_stream_event_union_type():
    """验证 SupervisorStreamEvent 联合类型包含所有预期事件类型。"""
    from typing import get_args
    event_types = get_args(SupervisorStreamEvent)
    type_names = [t.__name__ for t in event_types]
    assert "SubAgentStartEvent" in type_names
    assert "SubAgentEndEvent" in type_names
    assert "ReviewStartEvent" in type_names
    assert "ReviewEndEvent" in type_names
    assert "SupervisorDoneEvent" in type_names
