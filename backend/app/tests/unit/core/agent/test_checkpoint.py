"""Tests for AgentCheckpoint model.

Uses importlib.util to load modules directly, avoiding the circular import
triggered by app.core.agent.__init__ -> agent -> loop -> tool -> tools -> supervisor -> agent.
"""
import importlib.util
import pathlib

import pytest
from datetime import datetime, timezone

# Load base.py directly to bypass the circular import chain
_base_path = pathlib.Path(__file__).resolve().parents[5] / "app" / "core" / "agent" / "base.py"
_base_spec = importlib.util.spec_from_file_location("app.core.agent.base", _base_path)
_base_mod = importlib.util.module_from_spec(_base_spec)
_base_spec.loader.exec_module(_base_mod)

# Load checkpoint.py directly (it imports from base, give it the already-loaded module)
_checkpoint_path = pathlib.Path(__file__).resolve().parents[5] / "app" / "core" / "agent" / "checkpoint.py"
_checkpoint_spec = importlib.util.spec_from_file_location("app.core.agent.checkpoint", _checkpoint_path)
_checkpoint_mod = importlib.util.module_from_spec(_checkpoint_spec)

import sys
sys.modules["app.core.agent.base"] = _base_mod
sys.modules["app.core.agent.checkpoint"] = _checkpoint_mod

_checkpoint_spec.loader.exec_module(_checkpoint_mod)

AgentCheckpoint = _checkpoint_mod.AgentCheckpoint
InterruptConfig = _base_mod.InterruptConfig
InterruptMode = _base_mod.InterruptMode


class TestAgentCheckpoint:
    def test_basic_construction(self):
        cp = AgentCheckpoint(
            session_id="sv-123",
            messages=[{"role": "user", "content": "hello"}],
            loop_count=3,
            interrupt_tool_name="call_sub_agent",
            interrupt_config=InterruptConfig(enabled=True, tool_names=["call_sub_agent"]),
        )
        assert cp.session_id == "sv-123"
        assert len(cp.messages) == 1
        assert cp.loop_count == 3
        assert cp.interrupt_tool_name == "call_sub_agent"
        assert cp.created_at is not None

    def test_auto_timestamp(self):
        cp = AgentCheckpoint(
            session_id="sv-123",
            messages=[],
            loop_count=0,
            interrupt_tool_name="call_sub_agent",
            interrupt_config=InterruptConfig(),
        )
        assert isinstance(cp.created_at, datetime)

    def test_serialization_roundtrip(self):
        original = AgentCheckpoint(
            session_id="sv-456",
            messages=[
                {"role": "user", "content": "create a video"},
                {"role": "assistant", "content": "thinking..."},
                {"role": "tool", "tool_call_id": "tc-1", "tool_name": "call_sub_agent", "content": '{"output": "outline text"}'},
            ],
            loop_count=5,
            interrupt_tool_name="call_sub_agent",
            interrupt_config=InterruptConfig(
                enabled=True,
                tool_names=["call_sub_agent"],
                context={"review_sub_agents": ["outline_writer"]},
            ),
        )
        data = original.model_dump()
        restored = AgentCheckpoint(**data)
        assert restored.session_id == original.session_id
        assert restored.messages == original.messages
        assert restored.loop_count == original.loop_count
        assert restored.interrupt_config.context["review_sub_agents"] == ["outline_writer"]
