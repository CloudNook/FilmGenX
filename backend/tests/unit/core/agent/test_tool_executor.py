import asyncio
import time

import pytest

from app.core.agent.base import ThinkingEvent, ToolCall, ToolEndEvent, ToolExecutionResult
from app.core.agent.tool import ToolExecutor


class _StreamingToolExecutor(ToolExecutor):
    async def execute_tool_call(self, tool_call: ToolCall):
        yield ThinkingEvent(content=f"{tool_call.name}-thinking")
        await asyncio.sleep(0.05)
        yield ToolEndEvent(
            tool_call_id=tool_call.id,
            tool_name=tool_call.name,
            result={"name": tool_call.name},
            is_error=False,
        )


@pytest.mark.asyncio
async def test_execute_all_streams_events_before_tool_completion():
    executor = _StreamingToolExecutor()
    stream = executor.execute_all(
        [ToolCall(id="tool-1", name="outline_agent", arguments={})],
        concurrency=1,
    )

    started_at = time.perf_counter()
    first_event = await asyncio.wait_for(anext(stream), timeout=0.02)
    elapsed = time.perf_counter() - started_at

    assert isinstance(first_event, ThinkingEvent)
    assert first_event.content == "outline_agent-thinking"
    assert elapsed < 0.03


@pytest.mark.asyncio
async def test_execute_all_returns_execution_result_for_all_tools():
    executor = _StreamingToolExecutor()
    events = []

    async for event in executor.execute_all(
        [
            ToolCall(id="tool-1", name="outline_agent", arguments={}),
            ToolCall(id="tool-2", name="script_agent", arguments={}),
        ],
        concurrency=2,
    ):
        events.append(event)

    assert isinstance(events[-1], ToolExecutionResult)
    assert len(events[-1].results) == 2
    assert {result.tool_name for result in events[-1].results} == {
        "outline_agent",
        "script_agent",
    }
