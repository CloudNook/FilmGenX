"""
内置中间件实现。

包含：
- LoggingMiddleware: 请求/响应日志
- PersistMiddleware: 消息持久化
"""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from app.core.middleware.chain import AgentMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from app.core.agent.base import AgentMessage

logger = logging.getLogger(__name__)


class LoggingMiddleware(AgentMiddleware):
    """
    日志中间件。

    记录 Agent 执行的请求参数和执行结果。
    """

    name = "logging"

    async def before(self, ctx: MiddlewareContext) -> None:
        logger.info(
            f"[Agent:{ctx.agent_name}] Starting request_id={ctx.request_id}, "
            f"input={ctx.initial_input[:100]}..."
        )

    async def after(self, ctx: MiddlewareContext) -> None:
        if ctx.result:
            logger.info(
                f"[Agent:{ctx.agent_name}] Finished request_id={ctx.request_id}, "
                f"loop={ctx.loop_count}, finished={ctx.result.finished}, "
                f"error={ctx.result.error}"
            )
        else:
            logger.info(
                f"[Agent:{ctx.agent_name}] Finished request_id={ctx.request_id}, "
                f"no result yet"
            )

    async def on_loop_start(self, ctx: MiddlewareContext) -> None:
        logger.debug(
            f"[Agent:{ctx.agent_name}] Loop start #{ctx.loop_count}"
        )

    async def on_loop_end(self, ctx: MiddlewareContext) -> None:
        logger.debug(
            f"[Agent:{ctx.agent_name}] Loop end #{ctx.loop_count}"
        )


class PersistMiddleware(AgentMiddleware):
    """
    持久化中间件。

    将 Agent 执行过程中的消息通过 ctx.persist_strategy 持久化：
    - before(): 创建会话记录
    - on_loop_end(): 每轮循环的消息写入
    - after(): 更新会话最终状态

    使用方式：
        agent = create_agent(
            agent_name="my_agent",
            persist="redis",  # 或 "db"
            middlewares=[LoggingMiddleware(), PersistMiddleware()],
        )
    """

    name = "persist"

    async def before(self, ctx: MiddlewareContext) -> None:
        if ctx.persist_strategy is None:
            return

        started_at = datetime.now(timezone.utc)
        await ctx.persist_strategy.save_session(
            session_id=ctx.session_id,
            request_id=ctx.request_id,
            agent_name=ctx.agent_name,
            initial_input=ctx.initial_input,
            started_at=started_at,
        )
        logger.debug(
            f"[PersistMiddleware] Saved session {ctx.session_id}/{ctx.request_id}"
        )

    async def on_loop_end(self, ctx: MiddlewareContext) -> None:
        if ctx.persist_strategy is None or not ctx.loop_messages:
            return

        for msg in ctx.loop_messages:
            await ctx.persist_strategy.append_message(
                session_id=ctx.session_id,
                request_id=ctx.request_id,
                agent_name=ctx.agent_name,
                role=msg.role,
                content=msg.content,
                tool_call_id=msg.tool_call_id,
                tool_name=msg.tool_name,
                extra_metadata=msg.metadata,
                seq=ctx.loop_count,
            )
        ctx.loop_messages.clear()

    async def after(self, ctx: MiddlewareContext) -> None:
        if ctx.persist_strategy is None or ctx.result is None:
            return

        await ctx.persist_strategy.update_session(
            session_id=ctx.session_id,
            loop_count=ctx.loop_count,
            schema_data=ctx.result.schema_data,
            raw_output=ctx.result.raw_output,
            error=ctx.result.error,
            finished=ctx.result.finished,
            finished_at=ctx.result.finished_at or datetime.now(timezone.utc),
        )
        logger.debug(
            f"[PersistMiddleware] Updated session {ctx.session_id}/{ctx.request_id}"
        )
