"""Tool execution utilities for agent tool calls."""

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.agent.base import ToolCall, ToolEndEvent, ToolExecutionResult, ToolResult
from app.core.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)
_RUNNER_DONE = object()


class ToolExecutor:
    """Resolves registered tools and executes them."""

    def __init__(self, extra_kwargs: Optional[Dict[str, Any]] = None):
        self.extra_kwargs = extra_kwargs or {}

    def get_tool(self, name: str):
        return ToolRegistry.get(name)

    async def execute_tool_call(
        self, tool_call: ToolCall
    ) -> AsyncGenerator[ToolEndEvent, None]:
        """
        Execute a single tool call.

        Streaming tools may yield intermediate events before a final
        ``ToolEndEvent`` is produced.
        """
        tool_func = self.get_tool(tool_call.name)
        if tool_func is None:
            logger.warning("Tool '%s' not found", tool_call.name)
            yield ToolEndEvent(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                result={"error": f"Tool '{tool_call.name}' not found"},
                is_error=True,
            )
            return

        kwargs = dict(tool_call.arguments)
        import inspect

        tool_params = set(inspect.signature(tool_func.func).parameters)
        for k, v in self.extra_kwargs.items():
            if k not in kwargs and k in tool_params:
                kwargs[k] = v

        try:
            raw_result = await tool_func.execute(**kwargs)

            if hasattr(raw_result, "__aiter__"):
                last_event = None
                async for event in raw_result:
                    yield event
                    last_event = event

                if not isinstance(last_event, ToolEndEvent):
                    result = None
                    if last_event is not None and hasattr(last_event, "result"):
                        result = last_event.result
                    yield ToolEndEvent(
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.name,
                        result=result or {"status": "completed"},
                        is_error=False,
                    )
            else:
                yield ToolEndEvent(
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    result=raw_result,
                    is_error=False,
                )
        except Exception as e:
            logger.exception("Tool '%s' execution failed: %s", tool_call.name, e)
            yield ToolEndEvent(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                result={"error": str(e)},
                is_error=True,
            )

    async def execute_all(
        self,
        tool_calls: List[ToolCall],
        concurrency: int = 4,
    ) -> AsyncGenerator[ToolEndEvent | ToolExecutionResult, None]:
        """
        Execute tool calls concurrently and stream events as they arrive.

        The shared queue acts as an event bus for all running tool tasks, so
        long-lived streaming tools can push intermediate events immediately.
        """
        semaphore = asyncio.Semaphore(concurrency)
        tc_list = list(tool_calls)
        tool_results: List[Optional[ToolResult]] = [None] * len(tc_list)
        event_bus: asyncio.Queue = asyncio.Queue()

        async def _runner(idx: int, tc: ToolCall):
            try:
                async with semaphore:
                    async for ev in self.execute_tool_call(tc):
                        await event_bus.put((idx, ev))
            finally:
                await event_bus.put((idx, _RUNNER_DONE))

        tasks = [
            asyncio.create_task(_runner(i, tc))
            for i, tc in enumerate(tc_list)
        ]

        completed_runners = 0
        while completed_runners < len(tc_list):
            idx, ev = await event_bus.get()
            if ev is _RUNNER_DONE:
                completed_runners += 1
                continue

            yield ev
            if isinstance(ev, ToolEndEvent):
                tool_results[idx] = ToolResult(
                    tool_call_id=tc_list[idx].id,
                    tool_name=tc_list[idx].name,
                    result=ev.result,
                    is_error=ev.is_error,
                )

        await asyncio.gather(*tasks)

        yield ToolExecutionResult(
            results=[result for result in tool_results if result is not None]
        )

    async def execute_streaming_tool(
        self, tool_call: ToolCall
    ) -> AsyncGenerator[ToolEndEvent, None]:
        """Pass through events from a single streaming tool."""
        tool_func = self.get_tool(tool_call.name)
        if tool_func is None:
            yield ToolEndEvent(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                result={"error": f"Tool '{tool_call.name}' not found"},
                is_error=True,
            )
            return

        kwargs = dict(tool_call.arguments)
        import inspect as _inspect

        _tool_params = set(_inspect.signature(tool_func.func).parameters)
        for k, v in self.extra_kwargs.items():
            if k not in kwargs and k in _tool_params:
                kwargs[k] = v

        try:
            raw_result = await tool_func.execute(**kwargs)
            if hasattr(raw_result, "__aiter__"):
                last_event = None
                async for event in raw_result:
                    yield event
                    last_event = event
                if not isinstance(last_event, ToolEndEvent):
                    result = None
                    if last_event is not None and hasattr(last_event, "result"):
                        result = last_event.result
                    yield ToolEndEvent(
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.name,
                        result=result or {"status": "completed"},
                        is_error=False,
                    )
            else:
                yield ToolEndEvent(
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    result=raw_result,
                    is_error=False,
                )
        except Exception as e:
            logger.exception(
                "Tool '%s' streaming execution failed: %s", tool_call.name, e
            )
            yield ToolEndEvent(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                result={"error": str(e)},
                is_error=True,
            )
