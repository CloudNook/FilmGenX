import pytest
from app.core.supervisor.context import SupervisorContext


def test_supervisor_context_defaults():
    ctx = SupervisorContext(
        supervisor_session_id="sv-abc123",
        user_request="生成一个科幻短片剧本",
    )
    assert ctx.supervisor_session_id == "sv-abc123"
    assert ctx.user_request == "生成一个科幻短片剧本"
    assert ctx.current_phase == "init"
    assert ctx.artifacts == {}
    assert ctx.sub_agent_sessions == {}
    assert ctx.review_history == []


def test_supervisor_context_update_artifacts():
    ctx = SupervisorContext(
        supervisor_session_id="sv-abc123",
        user_request="生成一个科幻短片剧本",
    )
    ctx.artifacts["outline"] = {"title": "星际穿越", "scenes": 5}
    assert ctx.artifacts["outline"]["title"] == "星际穿越"


def test_supervisor_context_register_sub_session():
    ctx = SupervisorContext(
        supervisor_session_id="sv-abc123",
        user_request="生成一个科幻短片剧本",
    )
    ctx.sub_agent_sessions["outline_writer"] = "sub-outline-001"
    assert ctx.sub_agent_sessions["outline_writer"] == "sub-outline-001"
