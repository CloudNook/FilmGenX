import pytest
from unittest.mock import MagicMock, patch


def test_supervisor_agent_holds_context():
    ctx_dict = {}

    def mock_create_agent(**kwargs):
        return MagicMock()

    with patch("app.core.supervisor.supervisor.create_agent", mock_create_agent):
        from app.core.supervisor.supervisor import SupervisorAgent

        agent = SupervisorAgent(
            supervisor_session_id="sv-test",
            user_request="测试需求",
            sub_agent_configs={},
            middlewares=[],
            persist=None,
        )
        assert agent.context.user_request == "测试需求"
        assert agent.context.supervisor_session_id == "sv-test"
        assert agent.session.supervisor_session_id == "sv-test"


def test_supervisor_system_prompt_contains_tools():
    with patch("app.core.supervisor.supervisor.create_agent", MagicMock()):
        from app.core.supervisor.supervisor import SupervisorAgent

        agent = SupervisorAgent(
            supervisor_session_id="sv-test",
            user_request="测试需求",
            sub_agent_configs={},
            middlewares=[],
            persist=None,
        )
        prompt = agent._build_system_prompt()
        assert "call_sub_agent" in prompt
        assert "call_reviewer" in prompt
        assert "get_workflow_state" in prompt
        assert "测试需求" in prompt
