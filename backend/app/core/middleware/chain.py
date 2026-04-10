"""
Middleware 链式执行器。

定义 AgentMiddleware 基类和 MiddlewareChain 链式调用机制。
"""

import logging
from abc import ABC
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MiddlewareContext(BaseModel):
    """
    中间件共享上下文。

    在整个 middleware chain 执行过程中传递。
    持有 Agent 执行所需的上下文信息。
    """

    session_id: str  # 会话 ID（多轮对话）
    request_id: str  # 请求 ID（单次执行）
    agent_name: str
    agent_id: str
    initial_input: str
    persist_strategy: Any = None  # PersistStrategy | None
    loop_count: int = 0
    loop_messages: List[Any] = Field(default_factory=list)
    result: Any = None  # AgentResult
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}

    def __repr__(self) -> str:
        return (
            f"MiddlewareContext(session={self.session_id}, "
            f"request={self.request_id}, loop={self.loop_count})"
        )


class AgentMiddleware(ABC):
    """
    Agent 中间件基类。

    子类实现 before / after 方法，在 Agent 每次调用前后执行。
    可用于：日志记录、消息持久化、监控、限流等。
    """

    name: str = "unnamed"

    async def before(self, ctx: MiddlewareContext) -> None:
        """
        Agent 调用前拦截。

        Args:
            ctx: 中间件共享上下文
        """
        pass

    async def after(self, ctx: MiddlewareContext) -> None:
        """
        Agent 调用后拦截。

        Args:
            ctx: 中间件共享上下文
        """
        pass

    async def on_loop_start(self, ctx: MiddlewareContext) -> None:
        """
        每次循环开始前调用。

        Args:
            ctx: 中间件共享上下文
        """
        pass

    async def on_loop_end(self, ctx: MiddlewareContext) -> None:
        """
        每次循环结束后调用。

        Args:
            ctx: 中间件共享上下文
        """
        pass


class MiddlewareChain:
    """
    中间件链。

    按顺序执行所有中间件的 before → handler → after。
    """

    def __init__(self, middlewares: List[AgentMiddleware]):
        self.middlewares = middlewares

    async def run(
        self,
        ctx: MiddlewareContext,
        handler: Callable[[], Awaitable[Any]],
    ) -> Any:
        """
        执行中间件链。

        Args:
            ctx: 中间件共享上下文
            handler: 实际的处理函数（Agent.run）

        Returns:
            handler 的返回值
        """
        async def _execute(index: int) -> Any:
            if index >= len(self.middlewares):
                return await handler()

            mw = self.middlewares[index]
            logger.debug(f"[MiddlewareChain] before: {mw.name}")

            await mw.before(ctx)

            try:
                result = await _execute(index + 1)
                return result
            finally:
                await mw.after(ctx)
                logger.debug(f"[MiddlewareChain] after: {mw.name}")

        return await _execute(0)

    async def on_loop_start(self, ctx: MiddlewareContext) -> None:
        """触发所有中间件的 on_loop_start。"""
        for mw in self.middlewares:
            await mw.on_loop_start(ctx)

    async def on_loop_end(self, ctx: MiddlewareContext) -> None:
        """触发所有中间件的 on_loop_end。"""
        for mw in self.middlewares:
            await mw.on_loop_end(ctx)


def middleware_chain(middlewares: List[AgentMiddleware]) -> MiddlewareChain:
    """
    快捷构造 MiddlewareChain。

    用法：
        chain = middleware_chain([LoggingMiddleware(), PersistMiddleware()])
    """
    return MiddlewareChain(middlewares)
