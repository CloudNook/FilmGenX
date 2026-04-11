import pytest
import asyncio
from unittest.mock import MagicMock
from app.core.agent.tool import ToolExecutor
from app.core.agent.base import ToolCall


def test_execute_streaming_tool_yields_events():
    """工具返回 AsyncGenerator 时，execute_streaming_tool 实时 yield 事件。"""
    async def fake_streaming_tool(value: str):
        yield {"type": "text", "content": f"start {value}"}
        yield {"type": "text", "content": f"end {value}"}

    executor = ToolExecutor()
    mock_tool_func = MagicMock()
    mock_tool_func.execute = fake_streaming_tool

    from app.core.agent import tool as tool_module
    original_get = tool_module.ToolRegistry.get
    tool_module.ToolRegistry.get = MagicMock(return_value=mock_tool_func)

    try:
        tc = ToolCall(id="tc-1", name="streaming_tool", arguments={"value": "test"})
        events = []

        async def collect():
            async for event in executor.execute_streaming_tool(tc):
                events.append(event)

        asyncio.run(collect())
        assert len(events) == 2
        assert events[0]["content"] == "start test"
        assert events[1]["content"] == "end test"
    finally:
        tool_module.ToolRegistry.get = original_get


def test_execute_streaming_tool_sync_fallback():
    """工具返回同步结果时，execute_streaming_tool 转为 yield 单个 ToolEndEvent。"""
    async def fake_sync_tool():
        return {"result": "ok"}

    executor = ToolExecutor()
    mock_tool_func = MagicMock()
    mock_tool_func.execute = fake_sync_tool

    from app.core.agent import tool as tool_module
    original_get = tool_module.ToolRegistry.get
    tool_module.ToolRegistry.get = MagicMock(return_value=mock_tool_func)

    try:
        tc = ToolCall(id="tc-1", name="sync_tool", arguments={})
        events = []

        async def collect():
            async for event in executor.execute_streaming_tool(tc):
                events.append(event)

        asyncio.run(collect())
        assert len(events) == 1
        assert events[0].type == "tool_end"
        assert events[0].is_error is False
    finally:
        tool_module.ToolRegistry.get = original_get
