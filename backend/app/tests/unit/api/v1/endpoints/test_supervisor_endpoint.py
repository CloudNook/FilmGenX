import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from pydantic import ValidationError


def test_supervisor_start_request_schema():
    """验证 SupervisorStartRequest 的字段定义。"""
    from app.api.v1.endpoints.supervisor import SupervisorStartRequest

    req = SupervisorStartRequest(
        project_id=1,
        user_request="生成一个科幻短片",
        model="gemini-3-flash-preview",
        max_loop=30,
        persist="redis",
    )
    assert req.project_id == 1
    assert req.user_request == "生成一个科幻短片"
    assert req.model == "gemini-3-flash-preview"
    assert req.max_loop == 30
    assert req.persist == "redis"


def test_supervisor_start_request_defaults():
    """验证默认值。"""
    from app.api.v1.endpoints.supervisor import SupervisorStartRequest

    req = SupervisorStartRequest(project_id=1, user_request="测试")
    assert req.model == "gemini-3-flash-preview"
    assert req.max_loop == 30
    assert req.persist == "redis"
    assert req.sub_agent_configs == {}


def test_router_has_stream_endpoint():
    """验证 router 注册了 /stream 端点。"""
    from app.api.v1.endpoints.supervisor import router

    routes = {r.path for r in router.routes}
    assert "/stream" in routes


def test_create_supervisor_injects_workflow_service():
    """验证 _create_supervisor 将 workflow_service 注入到 factory。"""
    from app.api.v1.endpoints.supervisor import SupervisorStartRequest

    body = SupervisorStartRequest(
        project_id=1,
        user_request="测试需求",
        model="gemini-pro",
        max_loop=10,
        persist="redis",
        sub_agent_configs={"outline_writer": {"model": "gemini-flash"}},
    )
    mock_service = MagicMock()

    with patch("app.api.v1.endpoints.supervisor._create_supervisor") as mock_factory:
        mock_factory.return_value = MagicMock()

        from app.api.v1.endpoints.supervisor import _create_supervisor
        _create_supervisor(body, user_id=42, workflow_service=mock_service)

        mock_factory.assert_called_once_with(body, user_id=42, workflow_service=mock_service)


def test_supervisor_start_request_hitl_fields():
    """SupervisorStartRequest accepts human_review and review_nodes."""
    from app.api.v1.endpoints.supervisor import SupervisorStartRequest

    req = SupervisorStartRequest(
        project_id=1,
        user_request="test",
        human_review=True,
        review_nodes=["outline_writer", "storyboarder"],
    )
    assert req.human_review is True
    assert req.review_nodes == ["outline_writer", "storyboarder"]


def test_supervisor_start_request_hitl_defaults():
    from app.api.v1.endpoints.supervisor import SupervisorStartRequest

    req = SupervisorStartRequest(project_id=1, user_request="test")
    assert req.human_review is False
    assert req.review_nodes is None


def test_supervisor_resume_request_action_validation():
    """ResumeRequest validates action values."""
    from app.api.v1.endpoints.supervisor import SupervisorResumeRequest

    req = SupervisorResumeRequest(action="approve")
    assert req.action == "approve"


def test_supervisor_resume_request_optional_fields():
    """ResumeRequest accepts optional feedback and edited_content."""
    from app.api.v1.endpoints.supervisor import SupervisorResumeRequest

    req = SupervisorResumeRequest(
        action="reject",
        feedback="Needs improvement",
        edited_content=None,
    )
    assert req.action == "reject"
    assert req.feedback == "Needs improvement"
    assert req.edited_content is None


def test_supervisor_interrupt_state_schema():
    """SupervisorInterruptState schema works correctly."""
    from app.api.v1.endpoints.supervisor import SupervisorInterruptState

    state = SupervisorInterruptState(
        status="waiting_review",
        interrupt={
            "tool_name": "call_sub_agent",
            "context": {"review_sub_agents": ["outline_writer"]},
            "loop_count": 3,
        },
        artifacts={"outline_writer": {"title": "Test Outline"}},
    )
    assert state.status == "waiting_review"
    assert state.interrupt["tool_name"] == "call_sub_agent"
    assert state.artifacts["outline_writer"]["title"] == "Test Outline"


def test_router_has_state_and_resume_endpoints():
    """Verify router registered /{session_id}/state and /{session_id}/resume."""
    from app.api.v1.endpoints.supervisor import router

    routes = {r.path for r in router.routes}
    assert "/{session_id}/state" in routes
    assert "/{session_id}/resume" in routes
