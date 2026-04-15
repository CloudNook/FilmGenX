"""
Tool 执行器。

负责：
- 根据 tool_call 查找对应工具
- 执行工具并返回结果
- 处理执行错误
"""

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.agent.base import ToolCall, ToolEndEvent, ToolExecutionResult, ToolResult
from app.core.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Tool 执行器。

    根据 tool_call 查找并执行对应工具。
    """

    def __init__(self, extra_kwargs: Optional[Dict[str, Any]] = None):
        self.extra_kwargs = extra_kwargs or {}

    def get_tool(self, name: str):
        return ToolRegistry.get(name)

    async def execute_tool_call(
        self, tool_call: ToolCall
    ) -> AsyncGenerator[ToolEndEvent, None]:
        """
        执行单次工具调用。

        对于返回 AsyncGenerator 的工具（如 call_sub_agent），本方法会 yield
        工具产生的所有中间事件，最后 yield ToolEndEvent。

        Yields:
            ToolEndEvent — 工具执行结果（含 result / is_error）
        """
        tool_func = self.get_tool(tool_call.name)
        if tool_func is None:
            logger.warning(f"Tool '{tool_call.name}' not found")
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
                # 工具返回 AsyncGenerator：yield 所有中间事件，最后补 ToolEndEvent
                last_event = None
                async for event in raw_result:
                    yield event
                    last_event = event
                # async generator 工具可能不产出 ToolEndEvent，
                # 但 execute_all 需要它来构建 tool_results，必须补一个
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
                # 工具返回同步结果
                yield ToolEndEvent(
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    result=raw_result,
                    is_error=False,
                )
        except Exception as e:
            logger.exception(f"Tool '{tool_call.name}' execution failed: {e}")
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
        批量执行工具调用，支持并发控制。

        Yields:
            ToolEndEvent         — 工具执行完毕事件，流式实时产出
            ToolExecutionResult  — 全部工具执行完毕后最后产出，供调用方收集结果
        """
        semaphore = asyncio.Semaphore(concurrency)
        tc_list = list(tool_calls)
        n = len(tc_list)
        tool_results: List[ToolResult] = [None] * n
        queues: List[asyncio.Queue] = [asyncio.Queue() for _ in range(n)]
        done_events: List[asyncio.Event] = [asyncio.Event() for _ in range(n)]

        async def _runner(idx: int, tc: ToolCall):
            async with semaphore:
                async for ev in self.execute_tool_call(tc):
                    await queues[idx].put(ev)
                done_events[idx].set()

        # 启动所有任务
        pending: set[asyncio.Task] = {
            asyncio.create_task(_runner(i, tc)) for i, tc in enumerate(tc_list)
        }

        # 等待所有任务完成，同时 yield 事件
        while pending:
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
            for i, evt in enumerate(done_events):
                if evt.is_set():
                    evt.clear()
                    while not queues[i].empty():
                        try:
                            ev = queues[i].get_nowait()
                            yield ev
                            if isinstance(ev, ToolEndEvent):
                                tool_results[i] = ToolResult(
                                    tool_call_id=tc_list[i].id,
                                    tool_name=tc_list[i].name,
                                    result=ev.result,
                                    is_error=ev.is_error,
                                )
                        except asyncio.QueueEmpty:
                            break

        # 最后 drain 剩余事件（防止 race condition）
        for q in queues:
            while not q.empty():
                try:
                    ev = q.get_nowait()
                    yield ev
                except asyncio.QueueEmpty:
                    break

        # yield ToolExecutionResult（供调用方收集本批结果）
        yield ToolExecutionResult(results=tool_results)

    async def execute_streaming_tool(
        self, tool_call: ToolCall
    ) -> AsyncGenerator[ToolEndEvent, None]:
        """透传流式工具的所有事件。用于 call_sub_agent 等。"""
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
            logger.exception(f"Tool '{tool_call.name}' streaming execution failed: {e}")
            yield ToolEndEvent(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                result={"error": str(e)},
                is_error=True,
            )
