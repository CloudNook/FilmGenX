"""
Tool 执行器。

负责：
- 根据 tool_call 查找对应工具
- 执行工具并返回结果
- 处理执行错误
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.agent.base import ToolCall, ToolResult
from app.core.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Tool 执行器。

    根据 tool_call 查找并执行对应工具。
    """

    def __init__(self, db: Any = None):
        """
        Args:
            db: 数据库会话（用于需要 DB 的工具）
        """
        self.db = db

    def get_tool(self, name: str):
        """根据名称获取工具。"""
        return ToolRegistry.get(name)

    async def execute_tool_call(self, tool_call: ToolCall) -> ToolResult:
        """
        执行单次工具调用。

        Args:
            tool_call: 工具调用信息（name + arguments）

        Returns:
            ToolResult 执行结果
        """
        tool_func = self.get_tool(tool_call.name)
        if tool_func is None:
            logger.warning(f"Tool '{tool_call.name}' not found")
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                result={"error": f"Tool '{tool_call.name}' not found"},
                is_error=True,
            )

        try:
            # 注入 db 到参数（如果工具需要）
            kwargs = dict(tool_call.arguments)
            if self.db is not None and "db" not in kwargs:
                kwargs["db"] = self.db

            result = await tool_func.execute(**kwargs)
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                result=result,
                is_error=False,
            )
        except Exception as e:
            logger.exception(f"Tool '{tool_call.name}' execution failed: {e}")
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                result={"error": str(e)},
                is_error=True,
            )

    async def execute_all(
        self,
        tool_calls: List[ToolCall],
        concurrency: int = 4,
    ) -> List[ToolResult]:
        """
        批量执行工具调用，支持并发控制。

        Args:
            tool_calls: 工具调用列表
            concurrency: 最大并发数

        Returns:
            ToolResult 列表
        """
        import asyncio

        semaphore = asyncio.Semaphore(concurrency)

        async def _run(tc: ToolCall) -> ToolResult:
            async with semaphore:
                return await self.execute_tool_call(tc)

        results = await asyncio.gather(*[_run(tc) for tc in tool_calls])
        return list(results)
