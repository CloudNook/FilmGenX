"""
Agent 主类。

提供 run() / stream() 显式调用方法。
持久化通过 PersistStrategy 直接在 AgentLoop 内驱动，与 middleware 无关。
"""

import logging
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from app.core.agent.base import AgentConfig, AgentResult, DoneEvent
from app.core.agent.loop import AgentLoop
from app.core.agent.llm import LLMAdapter
from app.core.agent.tool import ToolExecutor
from app.core.agent.usage import merge_usage
from app.core.middleware.chain import AgentMiddleware, MiddlewareChain, MiddlewareContext

if TYPE_CHECKING:
    from app.core.agent.persist.base import PersistStrategy

logger = logging.getLogger(__name__)


class Agent:
    """
    Agent 实例。

    通过 create_agent() 创建，提供 run() / stream() 方法显式执行。

    使用约定：
    - `run()` 更适合业务代码直接拿最终 `AgentResult`
    - `stream()` 更适合前端实时消费内部过程事件
    """

    def __init__(
        self,
        config: AgentConfig,
        session_id: str,
        middlewares: List[AgentMiddleware] | None = None,
        persist: "PersistStrategy | None" = None,
    ):
        self.agent_id = str(uuid4())
        self.config = config
        self.session_id = session_id
        self.middlewares = middlewares or []
        self.persist = persist
        self._chain = MiddlewareChain(self.middlewares)
        self._llm: Optional[LLMAdapter] = None
        self._tool_executor: Optional[ToolExecutor] = None

    def _init_llm(self) -> None:
        if self._llm is not None:
            return
        self._llm = LLMAdapter(config=self.config, tools=self.config.tools)

    def _init_tool_executor(self) -> None:
        if self._tool_executor is not None:
            return
        self._tool_executor = ToolExecutor()

    def _build_context(
        self,
        request_id: str,
        initial_input: str,
    ) -> MiddlewareContext:
        return MiddlewareContext(
            session_id=self.session_id,
            agent_name=self.config.agent_name,
            agent_id=self.agent_id,
            request_id=request_id,
            initial_input=initial_input,
            agent_config=self.config,
        )

    async def run(
        self,
        initial_input: str,
        *,
        request_id: str | None = None,
    ) -> AgentResult:
        """
        执行 Agent 循环（非流式）。

        Args:
            initial_input: 用户初始输入
            request_id:    可选的请求 ID，不传则自动生成

        Returns:
            AgentResult 执行结果。

            这里返回的是业务侧最终对象，适合：
            - 读取 `schema_data`
            - 保存数据库
            - 作为下游流程输入
        """
        self._init_llm()
        self._init_tool_executor()

        rid = request_id or str(uuid4())
        ctx = self._build_context(rid, initial_input)

        async def _do_run() -> AgentResult:
            prev_msg_count = 0

            async def on_loop_start() -> None:
                ctx.loop_count = loop.loop_count
                await self._chain.on_loop_start(ctx)

            async def on_loop_end(messages: list) -> None:
                nonlocal prev_msg_count
                ctx.loop_count = loop.loop_count
                ctx.loop_messages = messages[prev_msg_count:]
                prev_msg_count = len(messages)
                await self._chain.on_loop_end(ctx)

            loop = AgentLoop(
                config=self.config,
                llm=self._llm,
                tool_executor=self._tool_executor,
                persist=self.persist,
                session_id=self.session_id,
                request_id=rid,
                on_loop_start=on_loop_start,
                on_loop_end=on_loop_end,
            )
            ctx.llm = self._llm
            ctx.loop = loop
            # loop.run() 负责完整的 think/act/observe 主循环，
            # 这里只做请求级封装和最终结果后处理。
            result = await loop.run(initial_input)
            result.usage = merge_usage(ctx.metadata.get("usage"), result.usage)
            # finalize_result 是“主循环结束后、返回给业务前”的最后加工阶段，
            # 适合做最终结构化、usage 汇总等不应干扰主循环的逻辑。
            result = await self._chain.finalize_result(ctx, result)
            result.agent_id = self.agent_id
            result.request_id = rid
            # 在 chain.run() 的 after 钩子触发前写入 ctx，确保 middleware.after() 能读到结果
            ctx.result = result
            return result

        return await self._chain.run(ctx, _do_run)

    async def stream(
        self,
        initial_input: str,
        *,
        request_id: str | None = None,
    ):
        """
        执行 Agent 循环（流式），yield StreamEvent。

        设计目标：
        - 让前端实时看到 Agent 内部过程
        - 同时在最后一个 DoneEvent 中携带完整 AgentResult，供业务层读取

        事件顺序：
            ThinkingEvent  — LLM 思考过程片段（如果模型支持）
            TextEvent      — LLM 文本片段（逐字实时）
            ToolStartEvent — 工具开始执行
            ToolEndEvent   — 工具执行完毕
            DoneEvent      — 循环结束（携带最终 AgentResult）
            ErrorEvent     — 出错
        """
        self._init_llm()
        self._init_tool_executor()

        rid = request_id or str(uuid4())
        ctx = self._build_context(rid, initial_input)

        prev_msg_count = 0

        async def on_loop_start() -> None:
            ctx.loop_count = loop.loop_count
            await self._chain.on_loop_start(ctx)

        async def on_loop_end(messages: list) -> None:
            nonlocal prev_msg_count
            ctx.loop_count = loop.loop_count
            ctx.loop_messages = messages[prev_msg_count:]
            prev_msg_count = len(messages)
            await self._chain.on_loop_end(ctx)

        loop = AgentLoop(
            config=self.config,
            llm=self._llm,
            tool_executor=self._tool_executor,
            persist=self.persist,
            session_id=self.session_id,
            request_id=rid,
            on_loop_start=on_loop_start,
            on_loop_end=on_loop_end,
        )
        ctx.llm = self._llm
        ctx.loop = loop

        async def _generate():
            async for event in loop.stream_run(initial_input):
                if isinstance(event, DoneEvent):
                    event.result.usage = merge_usage(ctx.metadata.get("usage"), event.result.usage)
                    # 在 DoneEvent 发给上层之前，先完成最终结果后处理，
                    # 这样前端拿到过程流，业务代码拿到的是已经整理好的 result。
                    event.result = await self._chain.finalize_result(ctx, event.result)
                    event.result.agent_id = self.agent_id
                    event.result.request_id = rid
                    ctx.result = event.result
                yield event

        async for event in self._chain.stream(ctx, _generate()):
            yield event
