import pytest
from unittest.mock import patch


def test_create_supervisor_returns_supervisor_agent():
    with patch("app.core.supervisor.factory.SupervisorAgent") as mock_agent_cls:
        mock_instance = mock_agent_cls.return_value
        from app.core.supervisor.factory import create_supervisor
        supervisor = create_supervisor(user_request="生成一个科幻短片")
        assert supervisor is not None
        mock_agent_cls.assert_called_once()


def test_create_supervisor_assigns_session_id():
    with patch("app.core.supervisor.factory.SupervisorAgent") as mock_agent_cls:
        mock_instance = mock_agent_cls.return_value
        from app.core.supervisor.factory import create_supervisor
        supervisor = create_supervisor(user_request="测试需求")
        call_kwargs = mock_agent_cls.call_args.kwargs
        assert "supervisor_session_id" in call_kwargs
        assert call_kwargs["supervisor_session_id"].startswith("sv-")


def test_create_supervisor_passes_user_request():
    with patch("app.core.supervisor.factory.SupervisorAgent") as mock_agent_cls:
        mock_instance = mock_agent_cls.return_value
        from app.core.supervisor.factory import create_supervisor
        supervisor = create_supervisor(user_request="我的科幻短片剧本")
        call_kwargs = mock_agent_cls.call_args.kwargs
        assert call_kwargs["user_request"] == "我的科幻短片剧本"
