"""Tests for InterruptConfig and InterruptEvent.

Uses importlib.util to load base.py directly, avoiding the circular import
triggered by app.core.agent.__init__ -> agent -> loop -> tool -> tools -> supervisor -> agent.
"""
import importlib.util
import pathlib

import pytest
from pydantic import ValidationError

# Load base.py directly to bypass the circular import chain
_base_path = pathlib.Path(__file__).resolve().parents[5] / "app" / "core" / "agent" / "base.py"
_spec = importlib.util.spec_from_file_location("app.core.agent.base", _base_path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

InterruptConfig = _base.InterruptConfig
InterruptMode = _base.InterruptMode
InterruptEvent = _base.InterruptEvent
StreamEvent = _base.StreamEvent


class TestInterruptConfig:
    def test_defaults(self):
        cfg = InterruptConfig()
        assert cfg.enabled is False
        assert cfg.mode == InterruptMode.AFTER_TOOL
        assert cfg.tool_names == []
        assert cfg.context == {}

    def test_custom_values(self):
        cfg = InterruptConfig(
            enabled=True,
            mode=InterruptMode.BEFORE_TOOL,
            tool_names=["call_sub_agent"],
            context={"review_sub_agents": ["outline_writer"]},
        )
        assert cfg.enabled is True
        assert cfg.mode == InterruptMode.BEFORE_TOOL
        assert cfg.tool_names == ["call_sub_agent"]

    def test_mode_enum_values(self):
        assert InterruptMode.AFTER_TOOL == "after_tool"
        assert InterruptMode.BEFORE_TOOL == "before_tool"


class TestInterruptEvent:
    def test_basic_construction(self):
        ev = InterruptEvent(
            session_id="sv-123",
            tool_name="call_sub_agent",
            tool_call_id="tc-1",
            tool_result={"output": "hello", "sub_agent_name": "outline_writer"},
        )
        assert ev.type == "interrupt"
        assert ev.session_id == "sv-123"
        assert ev.tool_name == "call_sub_agent"
        assert ev.available_actions == ["approve", "reject", "edit", "skip", "abort"]
        assert ev.context == {}

    def test_with_context(self):
        ev = InterruptEvent(
            session_id="sv-123",
            tool_name="call_sub_agent",
            tool_call_id="tc-1",
            context={"artifacts_snapshot": {"outline_writer": "..."}},
        )
        assert ev.context["artifacts_snapshot"]["outline_writer"] == "..."

    def test_serialization(self):
        ev = InterruptEvent(
            session_id="sv-123",
            tool_name="call_sub_agent",
            tool_call_id="tc-1",
            tool_result={"output": "test"},
        )
        data = ev.model_dump()
        assert data["type"] == "interrupt"
        assert data["session_id"] == "sv-123"
        assert data["tool_result"] == {"output": "test"}

    def test_in_stream_event_union(self):
        ev = InterruptEvent(
            session_id="sv-123",
            tool_name="call_sub_agent",
            tool_call_id="tc-1",
        )
        assert isinstance(ev, StreamEvent)


def test_create_agent_with_interrupt_config():
    """create_agent passes interrupt_config to AgentConfig."""
    from app.core.agent.factory import create_agent
    from app.core.agent.base import InterruptConfig as RealInterruptConfig

    cfg = RealInterruptConfig(enabled=True, tool_names=["call_sub_agent"])
    agent = create_agent(
        agent_name="test",
        session_id="s1",
        interrupt_config=cfg,
    )
    assert agent.config.interrupt_config is not None
    assert agent.config.interrupt_config.enabled is True
    assert agent.config.interrupt_config.tool_names == ["call_sub_agent"]
