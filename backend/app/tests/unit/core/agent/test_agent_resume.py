"""Tests for Agent.resume() method."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.agent.agent import Agent
from app.core.agent.base import (
    AgentConfig, AgentResult, DoneEvent, TextEvent,
    InterruptEvent, InterruptConfig, LLMResponse,
)
from app.core.agent.checkpoint import AgentCheckpoint


def _make_agent_with_interrupt(interrupt_config=None) -> Agent:
    config = AgentConfig(
        agent_name="test_agent",
        prompt="You are a test agent.",
        max_loop=10,
        interrupt_config=interrupt_config,
    )
    return Agent(config=config, session_id="sv-test-resume")


class TestAgentResume:
    def test_resume_requires_persist(self):
        """resume() raises ValueError if no persist strategy configured."""
        agent = _make_agent_with_interrupt()
        with pytest.raises(ValueError, match="persist strategy"):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                agent.resume("approve").__anext__()
            )

    @pytest.mark.asyncio
    async def test_resume_abort_yields_done(self):
        """resume(action='abort') yields DoneEvent immediately."""
        agent = _make_agent_with_interrupt()
        mock_persist = AsyncMock()
        checkpoint = AgentCheckpoint(
            session_id="sv-test-resume",
            messages=[{"role": "user", "content": "test"}],
            loop_count=1,
            interrupt_tool_name="call_sub_agent",
            interrupt_config=InterruptConfig(enabled=True),
        )
        mock_persist.load_checkpoint = AsyncMock(return_value=checkpoint)
        mock_persist.clear_checkpoint = AsyncMock()
        agent.persist = mock_persist

        events = []
        async for ev in agent.resume("abort"):
            events.append(ev)

        assert any(isinstance(e, DoneEvent) for e in events)
        done = [e for e in events if isinstance(e, DoneEvent)][0]
        assert "Aborted" in (done.result.error or "")

    @pytest.mark.asyncio
    async def test_resume_approve_continues_loop(self):
        """resume(action='approve') restores checkpoint and continues stream."""
        agent = _make_agent_with_interrupt(
            InterruptConfig(enabled=True, tool_names=["test_tool"])
        )
        mock_persist = AsyncMock()
        checkpoint = AgentCheckpoint(
            session_id="sv-test-resume",
            messages=[
                {"role": "user", "content": "test"},
                {"role": "assistant", "content": "", "tool_calls": [{"id": "tc-1", "name": "test_tool", "arguments": {}}]},
                {"role": "tool", "tool_call_id": "tc-1", "tool_name": "test_tool", "content": "result"},
            ],
            loop_count=1,
            interrupt_tool_name="test_tool",
            interrupt_config=InterruptConfig(enabled=True, tool_names=["test_tool"]),
        )
        mock_persist.load_checkpoint = AsyncMock(return_value=checkpoint)
        mock_persist.clear_checkpoint = AsyncMock()
        agent.persist = mock_persist

        mock_llm = MagicMock()

        async def fake_stream(*args, **kwargs):
            yield LLMResponse(content="done", finish_reason="stop")

        mock_llm.generate_stream = fake_stream
        agent._llm = mock_llm
        agent._tool_executor = MagicMock()

        events = []
        async for ev in agent.resume("approve"):
            events.append(ev)

        assert any(isinstance(e, DoneEvent) for e in events)
