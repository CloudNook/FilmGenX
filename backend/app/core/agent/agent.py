"""
Agent 主类。

提供 run() / stream() 显式调用方法。
持久化通过 PersistStrategy 直接在 AgentLoop 内驱动，与 middleware 无关。
"""

import logging
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from app.core.agent.base import AgentConfig, AgentResult, DoneEvent, AgentInterrupted, InterruptEvent, ErrorEvent, ResumeDecision, Reviewer
from app.core.agent.loop import AgentLoop
from app.core.agent.llm import LLMAdapter
from app.core.agent.tool import ToolExecutor
from app.core.agent.usage import merge_usage
from app.core.middleware.chain import AgentMiddleware, MiddlewareChain, MiddlewareContext

if TYPE_CHECKING:
    from app.core.agent.memory.harness import MemoryHarness
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
        skill_names: List[str] | None = None,
        reviewer: Reviewer | None = None,
        memory: "Optional[MemoryHarness]" = None,
    ):
        self.agent_id = str(uuid4())
        self.config = config
        self.session_id = session_id
        self.middlewares = middlewares or []
        self.persist = persist
        self.skill_names = skill_names or []
        self.reviewer = reviewer
        self.memory = memory
        self._chain = MiddlewareChain(self.middlewares)
        self._llm: Optional[LLMAdapter] = None
        self._tool_executor: Optional[ToolExecutor] = None
        self._skills_injected = False

    def _init_llm(self) -> None:
        if self._llm is not None:
            return
        self._llm = LLMAdapter(config=self.config, tools=self.config.tools)

    def _init_tool_executor(self) -> None:
        if self._tool_executor is not None:
            return
        # 当挂载了 memory，把 harness 注入 ToolExecutor.extra_kwargs，让
        # memory_save 工具能拿到 harness 实例（等同于 supervisor 注入 supervisor_context）
        extra_kwargs: dict = {}
        if self.memory is not None:
            extra_kwargs["memory_harness"] = self.memory
        self._tool_executor = ToolExecutor(extra_kwargs=extra_kwargs)

    async def _inject_skills(self) -> None:
        """加载 L1 skill 元信息并注入 system prompt（启动时一次）。

        路由口径：
        - ``self.skill_names`` 显式给出 → 按名取（admin / 测试覆盖通道）
        - 缺省 → 按 ``target_agents @> [agent_name]`` 反查（业务主流程）

        注：L2 / L3 由 LLM 通过 ``load_skill`` / ``load_skill_reference`` 工具按需加载，
        本步骤只把 L1 元信息（name + description + target_agents + tags）固定到 system prompt。
        """
        if self._skills_injected:
            return

        from app.core.skill.loader import list_meta
        from app.core.agent.factory import _build_system_prompt_with_skills
        from app.db.session import AsyncSessionFactory

        agent_name = self.config.agent_name
        route = "explicit_names" if self.skill_names else "target_agents_lookup"

        async with AsyncSessionFactory() as db:
            if self.skill_names:
                # 显式 skill_names：先取全部 active meta，再按名子集
                all_meta = await list_meta(db=db)
                name_set = set(self.skill_names)
                meta_list = [m for m in all_meta if m["name"] in name_set]
            else:
                meta_list = await list_meta(db=db, target_agent=agent_name)

        if not meta_list:
            self._skills_injected = True
            logger.info(
                "[Agent:%s] _inject_skills(route=%s): no matching skills "
                "(skill_names=%r); skipping injection",
                agent_name,
                route,
                self.skill_names,
            )
            return

        self.config.prompt = _build_system_prompt_with_skills(
            self.config.prompt, meta_list
        )
        self._skills_injected = True
        logger.info(
            "[Agent:%s] _inject_skills(route=%s): injected %d skill(s) into "
            "system prompt: %s",
            agent_name,
            route,
            len(meta_list),
            [m["name"] for m in meta_list],
        )

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

    async def _prepare_request(
        self,
        initial_input: str,
        request_id: str | None,
        resume: Optional[ResumeDecision],
    ):
        """run() / stream() 共享的请求级 setup。

        - 懒注入 skills、初始化 llm 与 tool_executor
        - 生成 rid，按需 load interrupt checkpoint
        - 构造 MiddlewareContext + AgentLoop（绑定 on_loop_start/end 闭包）

        Returns:
            (rid, ctx, loop, checkpoint)
        """
        await self._inject_skills()
        self._init_llm()
        self._init_tool_executor()

        rid = request_id or str(uuid4())

        checkpoint = None
        if resume is not None:
            if self.persist is None:
                raise ValueError("Cannot resume without a persist strategy")
            checkpoint = await self.persist.load_interrupt_state(self.session_id)
            if checkpoint is None:
                raise ValueError(f"No interrupt state found for session {self.session_id}")

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

            # 已停用：每 N 轮跑 extractor 兜底 compact 的路径。FilmGenX 业务约定
            # 所有 KV 写入都由 supervisor 在 call_sub_agent 返回后显式调 memory_save 完成；
            # extractor 路径会把每轮对话重新抽一遍，产生大量"略不同的同 key 重写"，
            # 即便改成 UPDATE-in-place 也仍然在每个 loop 浪费一次 LLM extractor 调用。
            # 留接口（``self.memory.write`` 和 ``tick_loop()``）以便业务自行重启该路径。
            #
            # if self.memory is not None and self.memory.tick_loop():
            #     from app.core.agent.memory.types import WriteTrigger
            #     window = self.memory.fallback_message_window
            #     recent = list(messages)[-window:]
            #     try:
            #         await self.memory.write(
            #             messages=recent,
            #             trigger=WriteTrigger.FALLBACK_COMPACT,
            #             loop_count=loop.loop_count,
            #         )
            #     except Exception:
            #         logger.exception(
            #             "[Agent:%s] fallback memory compact failed",
            #             self.config.agent_name,
            #         )

        loop = AgentLoop(
            config=self.config,
            llm=self._llm,
            tool_executor=self._tool_executor,
            persist=self.persist,
            session_id=self.session_id,
            request_id=rid,
            chain=self._chain,
            on_loop_start=on_loop_start,
            on_loop_end=on_loop_end,
            reviewer=self.reviewer,
            memory=self.memory,
        )
        ctx.llm = self._llm
        ctx.loop = loop

        return rid, ctx, loop, checkpoint

    async def run(
        self,
        initial_input: str,
        *,
        request_id: str | None = None,
        resume: Optional[ResumeDecision] = None,
    ) -> AgentResult:
        """执行 Agent 循环（非流式），返回最终 AgentResult。"""
        rid, ctx, loop, checkpoint = await self._prepare_request(
            initial_input, request_id, resume,
        )

        async def _do_run() -> AgentResult:
            try:
                result = await loop.run(
                    initial_input, ctx,
                    checkpoint=checkpoint, resume=resume,
                )
            except AgentInterrupted:
                result = AgentResult(
                    agent_id=self.agent_id,
                    agent_name=self.config.agent_name,
                    request_id=rid,
                    error="interrupted",
                    finished=False,
                )
                ctx.result = result
                return result
            result.usage = merge_usage(ctx.metadata.get("usage"), result.usage)
            # finalize_result 是"主循环结束后、返回给业务前"的最后加工阶段，
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
        resume: Optional[ResumeDecision] = None,
    ):
        """执行 Agent 循环（流式），yield StreamEvent。

        事件顺序：ThinkingEvent → TextEvent → ToolStartEvent → ToolEndEvent →
        DoneEvent（携带最终 AgentResult）。出错时 yield ErrorEvent。
        """
        rid, ctx, loop, checkpoint = await self._prepare_request(
            initial_input or "", request_id, resume,
        )

        async def _generate():
            async for event in loop.stream_run(
                initial_input or "", ctx,
                checkpoint=checkpoint, resume=resume,
            ):
                if isinstance(event, DoneEvent):
                    event.result.usage = merge_usage(ctx.metadata.get("usage"), event.result.usage)
                    event.result = await self._chain.finalize_result(ctx, event.result)
                    event.result.agent_id = self.agent_id
                    event.result.request_id = rid
                    ctx.result = event.result
                elif isinstance(event, InterruptEvent):
                    ctx.result = AgentResult(
                        agent_id=self.agent_id,
                        agent_name=self.config.agent_name,
                        request_id=rid,
                        error="interrupted",
                        finished=False,
                    )
                yield event

        async for event in self._chain.stream(ctx, _generate()):
            yield event
