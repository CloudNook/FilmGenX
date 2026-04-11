import pytest
from unittest.mock import patch, MagicMock


def test_create_supervisor_returns_supervisor_agent():
    from app.core.supervisor.supervisor import SupervisorAgent as RealAgent
    with patch("app.core.supervisor.factory.SupervisorAgent") as mock_agent_cls:
        mock_instance = MagicMock()
        mock_instance._tool_ctx = {}
        mock_agent_cls.return_value = mock_instance
        from app.core.supervisor.factory import create_supervisor
        supervisor = create_supervisor(user_request="生成一个科幻短片")
        assert supervisor is not None
        mock_agent_cls.assert_called_once()


def test_create_supervisor_assigns_session_id():
    from app.core.supervisor.supervisor import SupervisorAgent as RealAgent
    with patch("app.core.supervisor.factory.SupervisorAgent") as mock_agent_cls:
        mock_instance = MagicMock()
        mock_instance._tool_ctx = {}
        mock_agent_cls.return_value = mock_instance
        from app.core.supervisor.factory import create_supervisor
        supervisor = create_supervisor(user_request="测试需求")
        call_kwargs = mock_agent_cls.call_args.kwargs
        assert "supervisor_session_id" in call_kwargs
        assert call_kwargs["supervisor_session_id"].startswith("sv-")


def test_create_supervisor_passes_user_request():
    from app.core.supervisor.supervisor import SupervisorAgent as RealAgent
    with patch("app.core.supervisor.factory.SupervisorAgent") as mock_agent_cls:
        mock_instance = MagicMock()
        mock_instance._tool_ctx = {}
        mock_agent_cls.return_value = mock_instance
        from app.core.supervisor.factory import create_supervisor
        supervisor = create_supervisor(user_request="我的科幻短片剧本")
        call_kwargs = mock_agent_cls.call_args.kwargs
        assert call_kwargs["user_request"] == "我的科幻短片剧本"


def test_create_supervisor_injects_workflow_service():
    """workflow_service 参数被注入到 supervisor._tool_ctx。"""
    from app.core.supervisor.supervisor import SupervisorAgent as RealAgent
    with patch("app.core.supervisor.factory.SupervisorAgent") as mock_agent_cls:
        mock_instance = MagicMock()
        mock_instance._tool_ctx = {}
        mock_agent_cls.return_value = mock_instance
        from app.core.supervisor.factory import create_supervisor
        mock_service = MagicMock()
        supervisor = create_supervisor(user_request="test", workflow_service=mock_service)
        assert supervisor._tool_ctx["workflow_service"] is mock_service
