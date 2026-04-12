"""
Tool 执行器。

负责：
- 根据 tool_call 查找对应工具
- 执行工具并返回结果
- 处理执行错误
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.core.agent.base import ToolCall, ToolEndEvent, ToolResult
from app.core.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Tool 执行器。

    根据 tool_call 查找并执行对应工具。
    """

    def __init__(self, db: Any = None):
        self.db = db

    def get_tool(self, name: str):
        return ToolRegistry.get(name)

    async def execute_tool_call(self, tool_call: ToolCall) -> ToolResult:
        """
        执行单次工具调用。

        对于返回 AsyncGenerator 的工具（如 call_sub_agent），本方法会 yield
        工具产生的所有中间事件，最后 yield ToolResult。

        Yields:
            ToolStartEvent / ToolEndEvent / SubAgentStartEvent 等中间事件
            ToolResult（最后一个）

        Returns:
            ToolResult — 工具的最终结果（通过 async for 循环的返回值获取）
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
        if self.db is not None and "db" not in kwargs:
            kwargs["db"] = self.db

        try:
            raw_result = tool_func.execute(**kwargs)

            if hasattr(raw_result, "__aiter__"):
                # 工具返回 AsyncGenerator：yield 所有中间事件
                async for event in raw_result:
                    yield event
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
    ):
        """
        批量执行工具调用，支持并发控制。

        Yields:
            - 中间事件（ToolStartEvent, ToolEndEvent, SubAgentStartEvent 等）
            - list[ToolResult]（每个工具完成后一次，供调用方获取 .result）

        注意：此方法是一个 async generator。
        - run() 用 `results = [ev async for ev in execute_all(...)]` 获取列表
        - stream_run() 用 `async for ev in execute_all(...):` 获取中间事件
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
                            from app.core.agent.base import ToolEndEvent
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

        # yield ToolResult list（供 run() 收集）
        yield tool_results

    async def execute_streaming_tool(self, tool_call: ToolCall):
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
        if self.db is not None and "db" not in kwargs:
            kwargs["db"] = self.db

        try:
            raw_result = await tool_func.execute(**kwargs)
            if hasattr(raw_result, "__aiter__"):
                async for event in raw_result:
                    yield event
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
