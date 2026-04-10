"""
Middleware 系统 - Agent 调用拦截与链式执行。

使用方式：
    from app.core.middleware import AgentMiddleware, middleware_chain

    class LoggingMiddleware(AgentMiddleware):
        name = "logging"

        async def before(self, ctx):
            print(f"[{self.name}] Before: {ctx.agent_name}")

        async def after(self, ctx):
            print(f"[{self.name}] After: {ctx.loop_count}")

    chain = middleware_chain([LoggingMiddleware(), AnotherMiddleware()])
    await chain.run(ctx, next_handler)
"""

from app.core.middleware.builtin import LoggingMiddleware, PersistMiddleware
from app.core.middleware.chain import AgentMiddleware, MiddlewareChain, MiddlewareContext, middleware_chain

__all__ = [
    "AgentMiddleware",
    "MiddlewareChain",
    "MiddlewareContext",
    "middleware_chain",
    "LoggingMiddleware",
    "PersistMiddleware",
]
