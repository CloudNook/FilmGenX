"""
Agent 主类。

提供 run() / stream() 显式调用方法。
"""

import logging
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from app.core.agent.base import AgentConfig, AgentMessage, AgentResult
from app.core.agent.loop import AgentLoop
from app.core.agent.llm import LLMAdapter
from app.core.agent.tool import ToolExecutor
from app.core.middleware.chain import AgentMiddleware, MiddlewareChain, MiddlewareContext

if TYPE_CHECKING:
    from app.core.agent.persist.base import PersistStrategy

logger = logging.getLogger(__name__)


class Agent:
    """
    Agent 实例。

    通过 create_agent() 创建，提供 run() / stream() 方法显式执行。

    Skill 相关操作通过内置工具 load_skill / load_skill_lite 实现，
    由 Agent 运行时动态调用，不在初始化时预加载。
    """

    def __init__(
        self,
        config: AgentConfig,
        middlewares: List[AgentMiddleware] | None = None,
        persist: "PersistStrategy | None" = None,
    ):
        self.agent_id = str(uuid4())
        self.config = config
        self.middlewares = middlewares or []
        self.persist_strategy = persist
        self._chain = MiddlewareChain(self.middlewares)
        self._llm: Optional[LLMAdapter] = None
        self._tool_executor: Optional[ToolExecutor] = None

    def _init_llm(self) -> None:
        """初始化 LLM 适配器。"""
        if self._llm is not None:
            return

        self._llm = LLMAdapter(config=self.config, tools=self.config.tools)

    def _init_tool_executor(self) -> None:
        """初始化 Tool 执行器。"""
        if self._tool_executor is not None:
            return
        self._tool_executor = ToolExecutor()

    def _build_context(
        self,
        session_id: str,
        request_id: str,
        initial_input: str,
    ) -> MiddlewareContext:
        """构建中间件上下文。"""
        return MiddlewareContext(
            session_id=session_id,
            agent_name=self.config.agent_name,
            agent_id=self.agent_id,
            request_id=request_id,
            initial_input=initial_input,
            persist_strategy=self.persist_strategy,
        )

    async def run(
        self,
        initial_input: str,
        *,
        session_id: str,
        request_id: str | None = None,
    ) -> AgentResult:
        """
        执行 Agent 循环（非流式）。

        Args:
            initial_input: 用户初始输入
            session_id: 会话 ID（多轮对话标识）
            request_id: 可选的请求 ID，不传则自动生成

        Returns:
            AgentResult 执行结果
        """
        self._init_llm()
        self._init_tool_executor()

        rid = request_id or str(uuid4())
        ctx = self._build_context(session_id, rid, initial_input)

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
                on_loop_start=on_loop_start,
                on_loop_end=on_loop_end,
            )
            result = await loop.run(initial_input)
            result.agent_id = self.agent_id
            result.request_id = rid
            return result

        # 执行中间件链
        result = await self._chain.run(ctx, _do_run)
        ctx.result = result

        return result

    async def stream(
        self,
        initial_input: str,
        *,
        session_id: str,
        request_id: str | None = None,
    ):
        """
        执行 Agent 循环（流式）。

        Args:
            initial_input: 用户初始输入
            session_id: 会话 ID
            request_id: 可选的请求 ID
        """
        self._init_llm()

        rid = request_id or str(uuid4())
        ctx = self._build_context(session_id, rid, initial_input)

        await self._chain.run(ctx, lambda: None)
        ctx.result = None

        # TODO: 实现流式循环
        raise NotImplementedError("stream() not implemented yet")

    async def add_message(self, message: AgentMessage) -> None:
        """
        向 Agent 添加一条消息（用于恢复会话上下文）。

        Args:
            message: 消息对象
        """
        # TODO: 挂载消息历史到 AgentLoop
        raise NotImplementedError("add_message() not implemented yet")
