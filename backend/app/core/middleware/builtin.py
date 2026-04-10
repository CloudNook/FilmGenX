"""
内置中间件实现。

包含：
- LoggingMiddleware: 请求/响应日志
"""

import logging

from app.core.middleware.chain import AgentMiddleware, MiddlewareContext

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
                f"[Agent:{ctx.agent_name}] Finished request_id={ctx.request_id}, no result"
            )

    async def on_loop_start(self, ctx: MiddlewareContext) -> None:
        logger.debug(f"[Agent:{ctx.agent_name}] Loop start #{ctx.loop_count}")

    async def on_loop_end(self, ctx: MiddlewareContext) -> None:
        logger.debug(f"[Agent:{ctx.agent_name}] Loop end #{ctx.loop_count}")
