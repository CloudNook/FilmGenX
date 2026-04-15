"""
Middleware 链式执行器。

定义 AgentMiddleware 基类和 MiddlewareChain 链式调用机制。
"""

import logging
from abc import ABC
from typing import Any, Awaitable, Callable, Dict, List, TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class MiddlewareContext(BaseModel):
    """
    中间件共享上下文。

    在整个 middleware chain 执行过程中传递，可被每个钩子原地修改。
    """

    model_config = {"arbitrary_types_allowed": True, "frozen": False}

    session_id: str = Field(..., description="当前会话 ID")
    request_id: str = Field(..., description="本次请求 ID")
    agent_name: str = Field(..., description="Agent 名称")
    agent_id: str = Field(..., description="Agent 实例 ID")
    initial_input: str = Field(..., description="本次请求的用户原始输入")
    loop_count: int = Field(default=0, description="当前执行到第几轮循环")
    loop_messages: List[Any] = Field(default_factory=list, description="当前轮次新增的消息列表，便于做增量观测")
    agent_config: Any = Field(default=None, description="当前 AgentConfig，便于 middleware 读取配置")
    llm: Any = Field(default=None, description="当前 LLMAdapter，供 middleware 做额外 LLM 调用")
    loop: Any = Field(default=None, description="当前 AgentLoop，供 middleware 访问或调整内存中的上下文")
    result: Any = Field(default=None, description="最终 AgentResult；在 finalize/after 阶段可稳定读取")  # AgentResult
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "middleware 之间共享的临时上下文。before_tool_calls 等钩子可将中断信息写入此处，"
            "AgentLoop 通过检查此字段决定是否中断。"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"MiddlewareContext(session={self.session_id}, "
            f"request={self.request_id}, loop={self.loop_count})"
        )


class AgentMiddleware(ABC):
    """
    Agent 中间件基类。

    子类实现 before / after / on_loop_start / on_loop_end / finalize_result，
    在 Agent 调用前后、每轮循环前后，以及最终结果返回前执行。
    可用于：日志记录、监控、限流等。
    """

    name: str = "unnamed"

    async def before(self, ctx: MiddlewareContext) -> None:
        """
        请求级前置钩子。

        触发时机：
        - Agent.run() 开始执行时触发一次
        - Agent.stream() 开始执行、首个事件产出前触发一次

        适合做：
        - 初始化请求级上下文
        - 打点、日志、权限校验
        """
        pass

    async def after(self, ctx: MiddlewareContext) -> None:
        """
        请求级后置钩子。

        触发时机：
        - 整个 Agent 请求结束后触发一次
        - 包括正常结束、异常结束、流式结束
        - 在 finalize_result 之后执行，因此可以读取最终 result

        适合做：
        - 收尾日志
        - usage 记录
        - 请求级资源释放
        """
        pass

    async def on_loop_start(self, ctx: MiddlewareContext) -> None:
        """
        单轮循环开始前钩子。

        触发时机：
        - AgentLoop 每进入一轮 think/act/observe 前触发一次
        - 同一个请求内可能触发多次

        适合做：
        - 上下文裁剪/压缩
        - 每轮限流、观测、动态注入元数据
        """
        pass

    async def on_loop_end(self, ctx: MiddlewareContext) -> None:
        """
        单轮循环结束后钩子。

        触发时机：
        - AgentLoop 每一轮结束后触发一次
        - 工具调用轮、最终回答轮都会触发
        - 同一个请求内可能触发多次

        适合做：
        - 记录本轮新增消息
        - 每轮状态观测
        - 基于 loop_messages 的增量处理
        """
        pass

    async def before_tool_calls(
        self,
        ctx: MiddlewareContext,
        tool_calls: List[Any],
    ) -> MiddlewareContext:
        """
        工具调用前钩子。

        触发时机：
        - AgentLoop 每轮 LLM 返回 tool_calls 后、实际执行工具之前触发一次
        - 传入完整的 tool_calls 列表，middleware 可以检查任意一个

        返回值：
        - 返回修改后的 ctx。AgentLoop 通过检查 ctx.metadata.get("interrupt") 是否为真
          来决定是否中断。如果为真，中断信息从 ctx.metadata["interrupt"] 中读取。

        适合做：
        - Human-in-the-loop 人工审阅拦截
        - 工具白名单/黑名单过滤
        - 执行前日志/审批
        """
        return ctx

    async def after_tool_calls(
        self,
        ctx: MiddlewareContext,
        tool_calls: List[Any],
        tool_results: List[Any],
    ) -> MiddlewareContext:
        """
        工具调用后钩子。

        触发时机：
        - AgentLoop 每轮工具执行完毕后触发一次（即使中断发生也在中断前触发）

        返回值：
        - 返回修改后的 ctx。与 before_tool_calls 同理。

        适合做：
        - 工具执行结果的后处理
        - 基于结果的日志或监控
        """
        return ctx

    async def finalize_result(self, ctx: MiddlewareContext, result: Any) -> Any:
        """
        最终结果后处理钩子。

        触发时机：
        - AgentLoop 已经结束，最终 AgentResult 已生成
        - Agent.run() 返回前触发一次
        - Agent.stream() 的 DoneEvent 发出前触发一次

        适合做：
        - 改写最终 result
        - 最终结构化输出
        - 汇总/补充 usage、metadata
        """
        return result


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

    async def stream(self, ctx: MiddlewareContext, generator):
        """
        包裹 async generator，在首个 yield 前执行所有 before，结束后执行所有 after。
        无论正常结束还是异常，after 都保证触发（类似 try/finally）。
        """
        for mw in self.middlewares:
            logger.debug(f"[MiddlewareChain] before: {mw.name}")
            await mw.before(ctx)
        try:
            async for event in generator:
                yield event
        finally:
            for mw in reversed(self.middlewares):
                await mw.after(ctx)
                logger.debug(f"[MiddlewareChain] after: {mw.name}")

    async def on_loop_start(self, ctx: MiddlewareContext) -> None:
        for mw in self.middlewares:
            await mw.on_loop_start(ctx)

    async def on_loop_end(self, ctx: MiddlewareContext) -> None:
        for mw in self.middlewares:
            await mw.on_loop_end(ctx)

    async def before_tool_calls(
        self,
        ctx: MiddlewareContext,
        tool_calls: List[Any],
    ) -> MiddlewareContext:
        """
        依次调用每个 middleware 的 before_tool_calls。
        任何 middleware 在 ctx.metadata["interrupt"] 中写入中断信息则中断。
        """
        for mw in self.middlewares:
            ctx = await mw.before_tool_calls(ctx, tool_calls)
            if ctx.metadata.get("interrupt"):
                logger.debug(f"[MiddlewareChain] {mw.name} triggered interrupt")
                break
        return ctx

    async def after_tool_calls(
        self,
        ctx: MiddlewareContext,
        tool_calls: List[Any],
        tool_results: List[Any],
    ) -> MiddlewareContext:
        """依次调用每个 middleware 的 after_tool_calls。"""
        for mw in self.middlewares:
            ctx = await mw.after_tool_calls(ctx, tool_calls, tool_results)
        return ctx

    async def finalize_result(self, ctx: MiddlewareContext, result: Any) -> Any:
        current = result
        for mw in self.middlewares:
            current = await mw.finalize_result(ctx, current)
            ctx.result = current
        return current


def middleware_chain(middlewares: List[AgentMiddleware]) -> MiddlewareChain:
    """快捷构造 MiddlewareChain。"""
    return MiddlewareChain(middlewares)
