"""
Agent 循环逻辑。

控制 Agent 的 think → act → observe 循环流程。
核心变化：使用 LLMResponse 结构化响应，包含原生 tool_calls，
不再依赖文本解析。
持久化由 AgentLoop 在每条消息产生后直接驱动，与 middleware 无关。
"""

import base64
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Literal, Optional

from fastapi.encoders import jsonable_encoder

from app.core.agent.base import (
    AgentConfig, AgentMessage, AgentResult, ToolCall, ToolExecutionResult,
    ToolResult, ThinkingEvent, TextEvent, ToolStartEvent, ToolEndEvent,
    DoneEvent, UsageEvent, ErrorEvent, InterruptEvent, InterruptDecision, AgentInterrupted,
    AgentCheckpoint, ResumeDecision, Reviewer,
)
from app.core.agent.llm import LLMAdapter
from app.core.agent.persist.base import PersistStrategy
from app.core.agent.review import ReviewFeedbackMessage, ReviewHarness
from app.core.agent.tool import ToolExecutor
from app.core.agent.usage import merge_usage

if TYPE_CHECKING:
    from app.core.agent.memory.harness import MemoryHarness
    from app.core.middleware.chain import MiddlewareChain, MiddlewareContext

logger = logging.getLogger(__name__)


ReviewAction = Literal["passed", "revise", "failed", "accept_last"]


@dataclass(frozen=True)
class _PersistTurnItem:
    """``_record_tool_results`` 给 ``_persist_turn`` 准备的 tool 行预分配项。

    ``tool_seq`` 已经在内存里给 ``result.messages`` 用过，这里复用同一个 seq
    保证 in-memory 序号与 DB 行号一致。
    """

    tool_result: ToolResult
    formatted: str
    raw_content: str
    tool_seq: int


@dataclass(frozen=True)
class _LLMStreamResult:
    """In-band sentinel：``_stream_llm_response`` 在流结束时 yield 这个，
    携带累计的 content / thinking + 终止 chunk（含 tool_calls / finish_reason / usage）。"""

    content: str
    thinking: str
    final_chunk: Optional[Any]


@dataclass(frozen=True)
class _CandidateReady:
    """In-band sentinel：内部 think/tool 循环产出了一个等待评审的候选物。

    `_stream_until_candidate` 在产出候选物时 yield 一个 `_CandidateReady`，
    其后立即 return。外层 `_stream_loop` 据此触发 review 决策；如果决策为
    revise，外层会再次进入新的 `_stream_until_candidate`。
    """

    content: str
    assistant_seq: int


@dataclass(frozen=True)
class ReviewDecision:
    """Pure decision produced by `_decide_review_action`.

    决策与副作用分离：决策本身不写消息、不改 result 终态、不触发 on_loop_end，
    由调用方根据 action 选择如何收尾。这样 review 调用点的状态机一目了然。
    """

    action: ReviewAction
    events: List[Any]
    feedback: Optional[ReviewFeedbackMessage] = None
    review_exhausted: bool = False


# 停止信号（仅用于纯文本模式，优先级低于 finish_reason）
STOP_SIGNALS = {"<stop>", "<done>", "<finish>", "<end>"}


def is_stop_signal(text: str) -> bool:
    return text.strip().lower() in STOP_SIGNALS


class AgentLoop:
    """
    Agent 循环控制器。

    循环流程：
        1. Think: 调用 LLM 生成响应（LLMResponse，包含 content + tool_calls）
        2. Check: 检查 finish_reason / stop signals
        3. Act: 执行工具（基于结构化 StructuredToolCall）
        4. Observe: 将工具结果加入消息历史（Provider 原生格式）
        5. 继续下一轮循环

    结束条件：
        - finish_reason == "stop" 且无 tool_calls → 正常结束
        - finish_reason == "tool_calls" 但数量为 0 → 结束
        - 达到 max_loop 上限 → 超限退出
    """

    def __init__(
        self,
        config: AgentConfig,
        llm: LLMAdapter,
        tool_executor: ToolExecutor,
        persist: Optional[PersistStrategy] = None,
        session_id: str = "",
        request_id: str = "",
        on_loop_start: Optional[Any] = None,
        on_loop_end: Optional[Any] = None,
        chain: "MiddlewareChain" = None,
        reviewer: Optional[Reviewer] = None,
        memory: "Optional[MemoryHarness]" = None,
    ):
        self.config = config
        self.llm = llm
        self.tool_executor = tool_executor
        self.persist = persist
        self.session_id = session_id
        self.request_id = request_id
        self.on_loop_start = on_loop_start
        self.on_loop_end = on_loop_end
        self.chain = chain
        self.memory = memory
        self.review_harness = ReviewHarness(
            config=config,
            session_id=session_id,
            request_id=request_id,
            persist=persist,
            reviewer=reviewer,
        )
        self.messages: List[Dict[str, Any]] = []
        self.loop_count = 0
        self._seq = 0  # 全局序号，run() 开始时从历史最大 seq + 1 初始化
        self._system_prompt: Optional[str] = None  # 缓存，内容不随循环变化
        self._session_accumulated_usage: Optional[Dict[str, Any]] = None  # 会话历史累积 usage
        self._memory_recall_done = False  # 同一 stream 只召回一次

    def _build_system_prompt(self) -> str:
        if self._system_prompt is not None:
            return self._system_prompt

        self._system_prompt = self.config.prompt
        return self._system_prompt

    def _check_finished(
        self,
        response: Any,
        text: str,
    ) -> bool:
        """
        检查是否应该结束循环。

        优先级：
        1. finish_reason == "stop" → 正常结束
        2. finish_reason == "tool_calls" 但无实际调用 → 结束
        3. 停止信号 → 结束（兼容旧模式）
        """
        finish_reason = getattr(response, "finish_reason", None)
        # 适配器层已归一化为标准字符串，这里只需比较 "stop"
        finish_reason_str = (finish_reason or "").lower()
        if finish_reason_str == "stop":
            return True

        # 停止信号（兼容纯文本模式）
        if is_stop_signal(text):
            return True

        return False

    async def _emit_hitl_interrupt(
        self,
        interrupt_event: "InterruptEvent",
        *,
        ctx: "MiddlewareContext",
        accumulated_content: str,
        accumulated_thinking: str,
        assistant_seq: int,
        final_chunk: Any,
    ):
        """HITL 拦截 tool_call 时的"标 checkpoint + 写 interrupt 快照 + yield 事件" 一条龙。

        调用方收到这个 generator 后 ``yield from`` 完了直接 ``return`` 即可——
        async generator 不能在 helper 里 return 上层栈。
        """
        await self._persist(
            "assistant",
            accumulated_content,
            seq=assistant_seq,
            loop_count=self.loop_count,
            metadata=self._build_assistant_metadata(
                thinking=accumulated_thinking,
                tool_calls=final_chunk.tool_calls if final_chunk else None,
                finish_reason=final_chunk.finish_reason if final_chunk else None,
                accumulated_usage=self._session_accumulated_usage,
            ),
            usage=final_chunk.usage if final_chunk else None,
            is_checkpoint=True,
        )
        await self._persist_interrupt(ctx)
        yield interrupt_event

    async def _persist_interrupt(self, ctx: "MiddlewareContext") -> None:
        """
        将中断时的完整快照持久化到 persist。

        包含：被拦截的 tool_call + 消息历史 + loop_count。
        resume 时用于完整恢复状态。
        """
        interrupt_info = ctx.metadata.get("interrupt")
        if self.persist is None or interrupt_info is None:
            return
        from app.core.agent.base import AgentCheckpoint

        checkpoint = AgentCheckpoint(
            tool_call_id=interrupt_info["tool_call_id"],
            tool_name=interrupt_info["tool_name"],
            arguments=interrupt_info["arguments"],
            context=interrupt_info.get("context", {}),
            available_actions=interrupt_info.get(
                "available_actions", ["approve", "reject"]
            ),
            messages=list(self.messages),
            loop_count=self.loop_count,
        )
        await self.persist.save_interrupt_state(self.session_id, checkpoint)
        logger.info(
            f"[AgentLoop:{self.config.agent_name}] "
            f"Checkpoint saved for session={self.session_id}, "
            f"tool={checkpoint.tool_name}, loop={checkpoint.loop_count}"
        )

    def _add_message(self, role: str, content: str, seq: int = 0, **kwargs) -> AgentMessage:
        msg = {"role": role, "content": content, "seq": seq, **kwargs}
        self.messages.append(msg)
        return AgentMessage(role=role, content=content, seq=seq, agent_name=self.config.agent_name, **kwargs)

    @staticmethod
    def _rebuild_persisted_tool_calls(
        persisted: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Resume 时把持久化里的 tool_calls 还原成 to_request() 能消费的形态。

        关键是把 ``gemini_thought_signature`` 从 base64 解码并还原到 ``raw``，
        否则 Gemini 在 resume 时会拒绝接 tool 结果（拿不到 Part 的 signature）。
        """
        rebuilt: List[Dict[str, Any]] = []
        for tc in persisted:
            ts_b64 = tc.get("gemini_thought_signature")
            if ts_b64:
                tc = dict(tc)  # 不改原 metadata
                tc["raw"] = {
                    "gemini_thought_signature": base64.b64decode(ts_b64),
                    "gemini_fc_name": tc.get("gemini_fc_name", tc["name"]),
                    "gemini_fc_args": tc.get("gemini_fc_args", tc.get("arguments", {})),
                }
            rebuilt.append(tc)
        return rebuilt

    @staticmethod
    def _serialize_tool_calls(
        tool_calls: List[Any],
        tool_results: Optional[List[Any]] = None,
    ) -> List[Dict[str, Any]]:
        """序列化工具调用列表，可选地注入执行结果。"""
        results_by_id: Dict[str, Any] = {}
        if tool_results:
            for tr in tool_results:
                results_by_id[tr.tool_call_id] = tr
        out = []
        for tc in tool_calls:
            entry: Dict[str, Any] = {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
            if tc.id in results_by_id:
                tr = results_by_id[tc.id]
                entry["result"] = tr.result
                entry["is_error"] = tr.is_error
            # Persist Gemini thought_signature so it can be restored on resume.
            # thought_signature lives on the Part object (not on function_call).
            raw: Dict[str, Any] = getattr(tc, "raw", None) or {}
            gemini_part = raw.get("gemini_part")
            if gemini_part is not None:
                ts = getattr(gemini_part, "thought_signature", None)
                if ts is not None:
                    # bytes → base64 string for JSON serialisation
                    entry["gemini_thought_signature"] = base64.b64encode(ts).decode()
                    entry["gemini_fc_name"] = tc.name
                    entry["gemini_fc_args"] = tc.arguments
            out.append(entry)
        return out

    @staticmethod
    def _serialize_tool_result_content(result: Any) -> str:
        return result if isinstance(result, str) else AgentLoop._to_json_string(result)

    @staticmethod
    def _format_tool_result(tool_name: str, result: Any) -> str:
        return f"[TOOL: {tool_name}] {AgentLoop._to_json_string(result)}"

    @staticmethod
    def _to_json_string(value: Any) -> str:
        """
        将任意工具结果转成稳定 JSON 字符串。

        先使用 jsonable_encoder 处理 datetime/date/UUID/Decimal 等常见类型，
        再通过 default=str 兜底，避免序列化阶段中断整个 AgentLoop。
        """
        return json.dumps(
            jsonable_encoder(value),
            ensure_ascii=False,
            default=str,
        )

    def _build_assistant_metadata(
        self,
        *,
        thinking: str = "",
        tool_calls: Optional[List[Any]] = None,
        tool_results: Optional[List[Any]] = None,
        finish_reason: Optional[str] = None,
        accumulated_usage: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        metadata: Dict[str, Any] = {}
        if thinking:
            metadata["thinking"] = thinking
        if tool_calls:
            metadata["tool_calls"] = self._serialize_tool_calls(tool_calls, tool_results)
        if finish_reason:
            metadata["finish_reason"] = finish_reason
        if accumulated_usage:
            metadata["accumulated_usage"] = accumulated_usage
        return metadata or None

    async def _append_review_feedback(
        self,
        result: AgentResult,
        feedback: ReviewFeedbackMessage,
    ) -> None:
        self.messages.append({
            "role": "user",
            "content": feedback.content,
            "metadata": feedback.metadata,
        })
        seq = self._alloc_seq()
        result.messages.append(
            AgentMessage(
                role="user",
                content=feedback.content,
                seq=seq,
                agent_name=self.config.agent_name,
                metadata=feedback.metadata,
            )
        )
        await self._persist(
            "user",
            feedback.content,
            seq=seq,
            loop_count=self.loop_count,
            metadata=feedback.metadata,
        )

    async def _decide_review_action(
        self,
        *,
        candidate_output: str,
        result: AgentResult,
        ctx: Optional["MiddlewareContext"],
        candidate_seq: int = 0,
    ) -> ReviewDecision:
        """评审候选物并返回决策，不做副作用。

        review_history 由 ReviewHarness 自身在 review_candidate 内部追加，
        其余的状态变更（写 feedback 到消息历史、置 result 终态、触发 on_loop_end、
        yield 事件等）都由调用方根据返回的 ReviewDecision 处理。
        """

        outcome = await self.review_harness.review_candidate(
            candidate_output=candidate_output,
            result=result,
            ctx=ctx,
            messages=self.messages,
            loop_count=self.loop_count,
            candidate_seq=candidate_seq,
        )
        review = outcome.review
        events = outcome.events

        if review is None or review.passed:
            return ReviewDecision(action="passed", events=events)

        if self.review_harness.can_revise(result):
            return ReviewDecision(
                action="revise",
                events=events,
                feedback=self.review_harness.build_feedback_message(review),
            )

        # Exhausted — apply on_exhausted policy
        if self.review_harness.on_exhausted == "accept_last":
            return ReviewDecision(
                action="accept_last", events=events, review_exhausted=True
            )

        return ReviewDecision(
            action="failed", events=events, review_exhausted=True
        )

    def _finalize_terminal(
        self,
        result: AgentResult,
        *,
        error: Optional[str] = None,
        raw_output: Optional[str] = None,
    ) -> None:
        """把 result 写入终态：``error=None`` 视为成功 (``finished=True``)，
        否则失败 (``finished=False`` + ``error``)。

        统一替换原来散落在多处的 ``result.error/finished/finished_at/loop_count`` 赋值。
        """
        result.error = error
        result.finished = error is None
        result.finished_at = datetime.now(timezone.utc)
        result.loop_count = self.loop_count
        if raw_output is not None:
            result.raw_output = raw_output

    def _add_usage(self, result: AgentResult, usage: Optional[Dict[str, Any]]) -> None:
        """将本轮 LLM usage 累加到 result.usage（本次请求合计，供积分系统使用），
        并同步更新 _session_accumulated_usage（会话全局累积，供 persist 写入）。"""
        result.usage = merge_usage(result.usage, usage)
        self._session_accumulated_usage = merge_usage(self._session_accumulated_usage, usage)

    def _alloc_seq(self) -> int:
        """预分配一个 seq，但不写入——用于需要延迟写入的消息占位。"""
        seq = self._seq
        self._seq += 1
        return seq

    async def _persist(
        self,
        role: str,
        content: str,
        seq: Optional[int] = None,
        loop_count: int = 0,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        usage: Optional[Dict[str, Any]] = None,
        is_checkpoint: bool = False,
    ) -> None:
        """写入一条消息。seq 可预分配传入，否则自动分配并自增。"""
        if self.persist is None:
            return
        if seq is None:
            seq = self._seq
            self._seq += 1
        await self.persist.append_message(
            session_id=self.session_id,
            request_id=self.request_id,
            agent_name=self.config.agent_name,
            role=role,
            content=content,
            seq=seq,
            loop_count=loop_count,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            metadata=metadata,
            usage=usage,
            is_checkpoint=is_checkpoint,
        )

    async def _persist_turn(
        self,
        *,
        assistant_seq: int,
        assistant_content: str,
        assistant_metadata: Optional[Dict[str, Any]],
        assistant_usage: Optional[Dict[str, Any]],
        tool_persist_items: List["_PersistTurnItem"],
        is_checkpoint: bool = False,
    ) -> None:
        """Persist an assistant message followed by its tool result messages.

        Assistant 写在前（seq 最小），tool 紧随其后，保证 DB 行序与 seq 顺序一致，
        便于回放和 trace。
        """
        await self._persist(
            "assistant",
            assistant_content,
            seq=assistant_seq,
            loop_count=self.loop_count,
            metadata=assistant_metadata,
            usage=assistant_usage,
            is_checkpoint=is_checkpoint,
        )
        for item in tool_persist_items:
            await self._persist(
                "tool",
                item.raw_content,
                seq=item.tool_seq,
                loop_count=self.loop_count,
                tool_call_id=item.tool_result.tool_call_id,
                tool_name=item.tool_result.tool_name,
                metadata={"display_content": item.formatted, "is_error": item.tool_result.is_error},
            )


    async def _load_history(self) -> None:
        """从持久化存储加载历史消息，注入 self.messages，初始化 self._seq。"""
        if self.persist is None:
            return

        # 防止同一实例多次 run() 时重复加载
        if self.messages:
            return

        history = await self.persist.load_messages(self.session_id)
        if not history:
            return

        for r in history:
            metadata = r.extra_metadata or {}
            if r.role == "tool":
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": r.tool_call_id or "",
                    "tool_name": r.tool_name or "",
                    "content": r.content,
                })
                continue

            restored: Dict[str, Any] = {
                "role": r.role,
                "content": r.content,
            }
            if r.role == "assistant":
                if metadata.get("thinking"):
                    restored["thinking"] = metadata["thinking"]
                if metadata.get("tool_calls"):
                    restored["tool_calls"] = self._rebuild_persisted_tool_calls(
                        metadata["tool_calls"]
                    )
                if r.usage:
                    self._session_accumulated_usage = merge_usage(
                        self._session_accumulated_usage, r.usage
                    )
            self.messages.append(restored)

        self._seq = max(r.seq for r in history) + 1
        logger.info(
            f"[AgentLoop:{self.config.agent_name}] "
            f"Loaded {len(history)} history messages, next seq={self._seq}, "
            f"session_accumulated_usage={self._session_accumulated_usage}"
        )

    async def _maybe_inject_recalled_memories(self, initial_input: Optional[str]) -> None:
        """显式调用 memory 召回，按 inject_strategy 注入到 messages / system prompt。

        - 没挂 memory → no-op
        - 同一 stream 内只跑一次（resume 路径不再注入）
        - 失败 / 超时 / 空召回都已经在 ``MemoryHarness.recall`` 内静默处理
        """
        if self.memory is None or self._memory_recall_done:
            return
        self._memory_recall_done = True

        recent_msgs = list(self.messages)[-5:] if self.messages else []
        scored = await self.memory.recall(
            initial_input=initial_input,
            recent_messages=recent_msgs,
        )
        if not scored:
            return

        block = self.memory.format_recalled_for_prompt(scored)
        if not block:
            return

        strategy = self.memory.config.inject_strategy
        if strategy == "system_message":
            # 把召回块作为新的 system 消息插在最前
            self.messages.insert(
                0,
                {"role": "system", "content": block, "metadata": {"source": "memory_recall"}},
            )
        else:
            # structured_block / user_preamble 都作为一条 user 消息追加，
            # 紧接 _load_history 恢复的内容、initial_input 进入 messages 之前
            self.messages.append(
                {"role": "user", "content": block, "metadata": {"source": "memory_recall"}},
            )

        logger.info(
            "[AgentLoop:%s] injected %d recalled memory item(s) (strategy=%s)",
            self.config.agent_name,
            len(scored),
            strategy,
        )

    async def run(
        self,
        initial_input: Optional[str],
        ctx: "MiddlewareContext" = None,
        *,
        checkpoint: Optional["AgentCheckpoint"] = None,
        resume: Optional["ResumeDecision"] = None,
    ) -> AgentResult:
        """非流式入口：消费 stream_run 的事件流，仅取最终 AgentResult。

        与 stream_run 共享同一份内核循环，避免 think/act/observe/review 的双份实现。
        HITL 中断在 stream_run 中以 InterruptEvent 形式送出，这里翻译回
        AgentInterrupted 以保持 Agent.run() 的捕获契约。
        """
        final_result: Optional[AgentResult] = None
        async for event in self.stream_run(
            initial_input if initial_input is not None else "",
            ctx,
            checkpoint=checkpoint,
            resume=resume,
        ):
            if isinstance(event, InterruptEvent):
                raise AgentInterrupted()
            if isinstance(event, DoneEvent):
                final_result = event.result

        if final_result is None:
            return AgentResult(
                agent_name=self.config.agent_name,
                messages=[],
                error="stream_run did not produce DoneEvent",
                finished=False,
                finished_at=datetime.now(timezone.utc),
                loop_count=self.loop_count,
            )
        return final_result


    async def _handle_before_tool_calls(
        self,
        ctx: Optional["MiddlewareContext"],
        tool_calls: List[ToolCall],
    ) -> Optional[InterruptEvent]:
        """
        执行 before_tool_calls 钩子，检查是否需要中断。

        调用方：
            event = await self._handle_before_tool_calls(ctx, tool_calls)
            if event is not None:
                yield event
                return

        Returns:
            中断：返回 InterruptEvent，调用方负责 yield 并 return
            无中断：返回 None，继续执行工具
        """
        if self.chain is None:
            return None

        ctx = await self.chain.before_tool_calls(ctx, tool_calls)
        if not ctx.metadata.get("interrupt"):
            return None

        interrupt_info = ctx.metadata["interrupt"]
        return InterruptEvent(
            session_id=self.session_id,
            tool_name=interrupt_info["tool_name"],
            tool_call_id=interrupt_info["tool_call_id"],
            arguments=interrupt_info["arguments"],
            available_actions=interrupt_info.get(
                "available_actions", ["approve", "reject"]
            ),
            context=interrupt_info.get("context", {}),
        )

    async def _handle_after_tool_calls(
        self,
        ctx: Optional["MiddlewareContext"],
        tool_calls: List[ToolCall],
        tool_results: List[ToolResult],
    ) -> None:
        """
        执行 after_tool_calls 钩子。

        在工具执行完毕、所有结果处理完成后调用。
        用于 middleware 对工具结果做后处理、监控或记录。
        """
        if self.chain is None:
            return
        await self.chain.after_tool_calls(ctx, tool_calls, tool_results)

    def _lookup_pending_tool_call(self, tool_call_id: str) -> Optional[ToolCall]:
        """从消息历史中找到指定 id 的待执行 tool_call。

        从最近一条 assistant 消息向前回溯，命中即返回；找不到返回 None，
        由调用方决定是 raise 还是返回错误。
        """
        for msg in reversed(self.messages):
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    if tc.get("id") == tool_call_id:
                        return ToolCall(
                            id=tc["id"],
                            name=tc["name"],
                            arguments=tc.get("arguments", {}),
                        )
                return None
        return None

    async def _execute_tool_calls_streaming(self, tool_calls: List[ToolCall]):
        """Yield ToolStartEvent for each call, then 转发 execute_all 的所有事件。

        调用方负责扫描 yielded ToolEndEvent / ToolExecutionResult 收集 ToolResult。
        统一被 ``_stream_until_candidate`` 和 ``_do_resume_tool`` 复用。
        """
        for tc in tool_calls:
            logger.info(
                f"[AgentLoop:{self.config.agent_name}] "
                f"[Loop {self.loop_count}] Calling tool: {tc.name}({tc.arguments})"
            )
            yield ToolStartEvent(
                tool_call_id=tc.id,
                tool_name=tc.name,
                arguments=tc.arguments,
            )

        async for ev in self.tool_executor.execute_all(tool_calls):
            yield ev

    def _record_tool_results(
        self,
        tool_results: List[ToolResult],
        result: AgentResult,
    ) -> List["_PersistTurnItem"]:
        """把工具结果写入 self.messages + result.messages，预分配 seq。

        返回 ``_PersistTurnItem`` 列表，可直接喂给 ``_persist_turn`` 或单独
        ``_persist`` 写入；in-memory ``result.messages`` 与 DB seq 复用同一个
        ``tool_seq``，保证两边序号一致。
        """
        items: List[_PersistTurnItem] = []
        for tr in tool_results:
            raw_content = self._serialize_tool_result_content(tr.result)
            self.messages.append({
                "role": "tool",
                "tool_call_id": tr.tool_call_id,
                "tool_name": tr.tool_name,
                "content": raw_content,
            })
            formatted = self._format_tool_result(tr.tool_name, tr.result)
            logger.info(
                f"[AgentLoop:{self.config.agent_name}] "
                f"[Loop {self.loop_count}] Tool result: {tr.tool_name} -> {tr.result!r}"
            )
            tool_seq = self._alloc_seq()
            result.messages.append(
                AgentMessage(
                    role="tool",
                    content=formatted,
                    seq=tool_seq,
                    agent_name=self.config.agent_name,
                    tool_call_id=tr.tool_call_id,
                    tool_name=tr.tool_name,
                )
            )
            items.append(_PersistTurnItem(
                tool_result=tr,
                formatted=formatted,
                raw_content=raw_content,
                tool_seq=tool_seq,
            ))
        return items

    def _build_rejected_tool_result(self, tool_call: ToolCall) -> ToolResult:
        """
        构造“工具调用被人工拒绝”的伪工具结果，供后续对话感知。
        """
        return ToolResult(
            tool_call_id=tool_call.id,
            tool_name=tool_call.name,
            result={
                "status": "interrupted",
                "reason": "human_review_rejected",
                "message": (
                    f"Tool call '{tool_call.name}' interrupted: "
                    "rejected by reviewer."
                ),
            },
            is_error=True,
        )

    def _apply_fallback(
        self,
        result: AgentResult,
        current_assistant_msg_idx: int,
    ) -> Optional[str]:
        """
        当模型返回空内容时，根据工具执行结果生成兜底内容并标记结束。

        Returns:
            兜底内容字符串（模型继续返回空且有工具结果时）
            None（无工具结果，无需 fallback）
        """
        tool_results_texts = [
            msg.content
            for msg in result.messages
            if msg.role == "tool" and msg.content
        ]
        if not tool_results_texts:
            return None

        fallback_content = (
            "根据工具执行结果，汇总如下：\n"
            + "\n".join(f"- {t}" for t in tool_results_texts)
        )
        logger.warning(
            f"[AgentLoop:{self.config.agent_name}] "
            f"[Loop {self.loop_count}] Empty response after tool execution, using fallback"
        )
        result.messages[current_assistant_msg_idx] = AgentMessage(
            role="assistant",
            content=fallback_content,
            agent_name=self.config.agent_name,
        )
        self._finalize_terminal(result, raw_output=fallback_content)
        return fallback_content

    async def _do_resume_tool(
        self,
        checkpoint: "AgentCheckpoint",
        resume: "ResumeDecision",
        result: AgentResult,
        ctx: "MiddlewareContext",
    ) -> AsyncGenerator[ToolEndEvent, None]:
        """
        Resume 时执行 pending tool（流式 yield ToolStartEvent/ToolEndEvent）。

        用于 stream_run resume 分支。
        """
        tc_to_execute = self._lookup_pending_tool_call(checkpoint.tool_call_id)
        if tc_to_execute is None:
            logger.error(
                f"[AgentLoop:{self.config.agent_name}] "
                f"Cannot find tool_call_id={checkpoint.tool_call_id} in messages"
            )
            raise LookupError(f"Cannot find pending tool_call: {checkpoint.tool_call_id}")

        if resume.action == "approve":
            # approve：通过共享的 _execute_tool_calls_streaming 真实执行
            tool_results: List[ToolResult] = []
            execution_result: Optional[ToolExecutionResult] = None
            async for ev in self._execute_tool_calls_streaming([tc_to_execute]):
                if isinstance(ev, ToolEndEvent):
                    tool_results.append(ToolResult(
                        tool_call_id=ev.tool_call_id,
                        tool_name=ev.tool_name,
                        result=ev.result,
                        is_error=ev.is_error,
                    ))
                    yield ev
                elif isinstance(ev, ToolExecutionResult):
                    execution_result = ev
                else:
                    yield ev
            tool_results = execution_result.results if execution_result else tool_results
            tool_result = tool_results[0] if tool_results else ToolResult(
                tool_call_id=tc_to_execute.id,
                tool_name=tc_to_execute.name,
                result={"error": "no result"},
                is_error=True,
            )
        elif resume.action == "reject":
            # reject：合成 rejected ToolResult，无需真实执行
            tool_result = self._build_rejected_tool_result(tc_to_execute)
        else:
            raise ValueError(f"Unsupported resume action: {resume.action}")

        # 写入 tool 结果消息（in-memory + result.messages + DB persist）
        tool_persist_items = self._record_tool_results([tool_result], result)
        for item in tool_persist_items:
            await self._persist(
                "tool", item.raw_content,
                seq=item.tool_seq,
                loop_count=self.loop_count,
                tool_call_id=item.tool_result.tool_call_id,
                tool_name=item.tool_result.tool_name,
                metadata={"display_content": item.formatted, "is_error": item.tool_result.is_error},
            )

        # after_tool_calls 钩子
        await self._handle_after_tool_calls(
            ctx, [tc_to_execute], [tool_result]
        )

        # 继续主循环（从下一轮开始）
        if self.on_loop_start is not None:
            await self.on_loop_start()
        if self.on_loop_end is not None:
            await self.on_loop_end(result.messages)

    async def stream_run(
        self,
        initial_input: str,
        ctx: "MiddlewareContext" = None,
        *,
        checkpoint: Optional["AgentCheckpoint"] = None,
        resume: Optional["ResumeDecision"] = None,
    ):

        # ── Resume 分支：执行 pending tool 后直接进入主循环 ──────────────────────
        # 先加载历史消息（持久化层可能有之前中断后的消息）
        await self._load_history()

        # Memory 召回（显式调用，不在 hook 里）：在历史回放后、用户消息接入前注入。
        # 失败 / 超时 / 空召回都静默跳过，不阻塞主流。
        await self._maybe_inject_recalled_memories(initial_input)

        if checkpoint is not None and resume is not None:
            self.loop_count = checkpoint.loop_count
            result = AgentResult(agent_name=self.config.agent_name, messages=[])

            self.loop_count += 1  # 消耗一个迭代
            # 执行 tool 并 yield tool 事件
            try:
                async for ev in self._do_resume_tool(checkpoint, resume, result, ctx):
                    yield ev
            except LookupError as e:
                self._finalize_terminal(result, error=str(e))
                yield ErrorEvent(error=str(e))
                yield DoneEvent(result=result)
                return
            # 清除中断状态
            if self.persist is not None:
                await self.persist.clear_interrupt_state(self.session_id)
            if resume.action == "reject":
                self._finalize_terminal(result, error="Tool call rejected by reviewer")
                yield DoneEvent(result=result)
                return
            # 进入主循环
            async for ev in self._stream_loop(result, ctx):
                yield ev
            return

        # 非 resume 入口：仅当 initial_input 真的有内容时，才追加 user 消息。
        # 既能与原 run() 行为对齐，也避免在空字符串下污染历史。
        result = AgentResult(agent_name=self.config.agent_name, messages=[])
        if initial_input:
            result.messages.append(self._add_message("user", initial_input, seq=self._seq))
            await self._persist("user", initial_input, loop_count=self.loop_count)

        async for ev in self._stream_loop(result, ctx):
            yield ev

    async def _stream_loop(self, result: AgentResult, ctx: "MiddlewareContext"):
        """两层结构：内层产出候选物，外层做评审/修订编排。

        - 内层 `_stream_until_candidate` 跑 think/tool 迭代直到产出候选物或终态
          （max_loop / fallback / HITL 中断 / 异常）；候选物以 `_CandidateReady`
          sentinel 形式回传，终态由内层自行 yield Error/Done/Interrupt 事件后退出。
        - 外层根据 ReviewDecision 决定：revise 则继续下一轮内层产出；passed /
          accept_last 则收尾并 yield Done；failed 则 yield Error/Done。
        """
        buffer_text_until_review = self.review_harness.enabled

        try:
            while True:
                candidate: Optional[_CandidateReady] = None
                async for ev in self._stream_until_candidate(result, ctx):
                    if isinstance(ev, _CandidateReady):
                        candidate = ev
                        # 内层会在产出候选后立即 return，无更多事件
                        continue
                    yield ev

                if candidate is None:
                    # 内层已 yield 终态事件（max_loop / fallback / HITL / 异常路径）
                    return

                # 先把候选内容推给前端，让用户看到正在被评审的内容，
                # 再启动 reviewer，避免 review 结果先于正文出现。
                if buffer_text_until_review and candidate.content:
                    yield TextEvent(content=candidate.content)

                decision = await self._decide_review_action(
                    candidate_output=candidate.content,
                    result=result,
                    ctx=ctx,
                    candidate_seq=candidate.assistant_seq,
                )
                for ev in decision.events:
                    yield ev
                if decision.review_exhausted:
                    result.review_exhausted = True

                if decision.action == "revise":
                    await self._append_review_feedback(result, decision.feedback)
                    if self.on_loop_end is not None:
                        await self.on_loop_end(result.messages)
                    continue

                if decision.action == "failed":
                    self._finalize_terminal(result, error="Review failed")
                    if self.on_loop_end is not None:
                        await self.on_loop_end(result.messages)
                    yield ErrorEvent(error=result.error)
                    yield DoneEvent(result=result)
                    return

                # passed or accept_last → 收尾返回最终候选
                self._finalize_terminal(result, raw_output=candidate.content)
                if self.on_loop_end is not None:
                    await self.on_loop_end(result.messages)
                yield DoneEvent(result=result)
                return

        except Exception as e:
            logger.exception(f"[AgentLoop:{self.config.agent_name}] stream_run error: {e}")
            yield ErrorEvent(error=str(e))
            self._finalize_terminal(result, error=str(e))
            yield DoneEvent(result=result)

    async def _stream_llm_response(self, *, buffer_text: bool):
        """流式拉一次 LLM 响应：边流边 yield ThinkingEvent / TextEvent
        （TextEvent 受 ``buffer_text`` 抑制，给 reviewer 启用时把候选物文本
        留到 review 通过后再吐），最后 yield 一个 ``_LLMStreamResult`` sentinel
        汇总累计内容和终止 chunk。
        """
        accumulated_content = ""
        accumulated_thinking = ""
        final_chunk: Optional[Any] = None

        async for chunk in self.llm.generate_stream(
            messages=list(self.messages),
            system_prompt=self._build_system_prompt(),
            response_schema=self.config.response_schema,
        ):
            if chunk.thinking:
                accumulated_thinking += chunk.thinking
                yield ThinkingEvent(content=chunk.thinking)
            if chunk.content:
                accumulated_content += chunk.content
                if not buffer_text:
                    yield TextEvent(content=chunk.content)
            if chunk.finish_reason is not None:
                final_chunk = chunk

        yield _LLMStreamResult(
            content=accumulated_content,
            thinking=accumulated_thinking,
            final_chunk=final_chunk,
        )

    def _record_assistant_message(
        self,
        *,
        content: str,
        thinking: str,
        final_chunk: Optional[Any],
        result: AgentResult,
    ) -> tuple[int, int]:
        """把当前 LLM 响应作为 assistant 消息**仅记账**到内存（``self.messages``
        + ``result.messages``），DB 持久化由调用方稍后通过 ``_persist_turn`` /
        ``_persist`` 触发。

        返回 ``(assistant_seq, assistant_msg_idx_in_result)``。后者供 fallback
        路径覆盖该槽位用。
        """
        assistant_msg_dict: Dict[str, Any] = {
            "role": "assistant",
            "content": content,
        }
        if thinking:
            assistant_msg_dict["thinking"] = thinking
        if final_chunk is not None and final_chunk.tool_calls:
            assistant_msg_dict["tool_calls"] = [
                {"id": tc.id, "name": tc.name, "arguments": tc.arguments, "raw": tc.raw}
                for tc in final_chunk.tool_calls
            ]
        self.messages.append(assistant_msg_dict)

        msg_idx = len(result.messages)
        seq = self._alloc_seq()
        result.messages.append(
            AgentMessage(
                role="assistant",
                content=content,
                thinking=thinking,
                seq=seq,
                agent_name=self.config.agent_name,
            )
        )
        return seq, msg_idx

    async def _stream_until_candidate(
        self,
        result: AgentResult,
        ctx: "MiddlewareContext",
    ):
        """跑 think/tool 迭代直到产出一个候选物或进入终态。

        正常出口：在产出可评审候选物时 yield 一个 `_CandidateReady` 后返回。
        终态出口：max_loop / fallback / HITL 中断 由本方法直接 yield
        Error/Done/Interrupt 事件并返回，不再 yield `_CandidateReady`，
        由外层 `_stream_loop` 据此判断是否结束整段流程。
        """
        buffer_text_until_review = self.review_harness.enabled

        while self.loop_count < self.config.max_loop:
            self.loop_count += 1
            logger.info(
                f"[AgentLoop:{self.config.agent_name}] "
                f"Loop {self.loop_count}/{self.config.max_loop}"
            )

            if self.on_loop_start is not None:
                await self.on_loop_start()

            # --- Think：流式 LLM 调用 ---
            stream_result: Optional[_LLMStreamResult] = None
            async for ev in self._stream_llm_response(buffer_text=buffer_text_until_review):
                if isinstance(ev, _LLMStreamResult):
                    stream_result = ev
                else:
                    yield ev
            assert stream_result is not None  # 上面循环必然会 yield 一次 sentinel
            accumulated_content = stream_result.content
            accumulated_thinking = stream_result.thinking
            final_chunk = stream_result.final_chunk

            if final_chunk is not None:
                self._add_usage(result, final_chunk.usage)
                # 每次 LLM call 结束都 fire 一次 UsageEvent，给前端 / 上层流水线
                # 做实时 token 累计计费用。usage 可能为 None（adapter 没返）这种情况
                # 不 fire——caller 看不到就当 0 处理。
                if final_chunk.usage:
                    yield UsageEvent(
                        usage=dict(final_chunk.usage),
                        accumulated_usage=(
                            dict(self._session_accumulated_usage)
                            if self._session_accumulated_usage else None
                        ),
                        loop_count=self.loop_count,
                    )

            # --- 把 assistant 消息记账到内存 ---
            _assistant_seq, current_assistant_msg_idx = self._record_assistant_message(
                content=accumulated_content,
                thinking=accumulated_thinking,
                final_chunk=final_chunk,
                result=result,
            )

            # --- Act：tool_calls 路径 ---
            if final_chunk.tool_calls:
                tool_calls = [
                    ToolCall(id=tc.id, name=tc.name, arguments=tc.arguments)
                    for tc in final_chunk.tool_calls
                ]

                # HITL 拦截
                interrupt_event = await self._handle_before_tool_calls(ctx, tool_calls)
                if interrupt_event is not None:
                    async for ev in self._emit_hitl_interrupt(
                        interrupt_event,
                        ctx=ctx,
                        accumulated_content=accumulated_content,
                        accumulated_thinking=accumulated_thinking,
                        assistant_seq=_assistant_seq,
                        final_chunk=final_chunk,
                    ):
                        yield ev
                    return

                tool_results: List[ToolResult] = []
                execution_result: Optional[ToolExecutionResult] = None
                async for ev in self._execute_tool_calls_streaming(tool_calls):
                    if isinstance(ev, ToolEndEvent):
                        tool_results.append(ToolResult(
                            tool_call_id=ev.tool_call_id,
                            tool_name=ev.tool_name,
                            result=ev.result,
                            is_error=ev.is_error,
                        ))
                        yield ev
                    elif isinstance(ev, ToolExecutionResult):
                        execution_result = ev
                    else:
                        yield ev
                tool_results = execution_result.results if execution_result else tool_results

                tool_persist_items = self._record_tool_results(tool_results, result)

                await self._handle_after_tool_calls(ctx, tool_calls, tool_results)

                await self._persist_turn(
                    assistant_seq=_assistant_seq,
                    assistant_content=accumulated_content,
                    assistant_metadata=self._build_assistant_metadata(
                        thinking=accumulated_thinking,
                        tool_calls=final_chunk.tool_calls,
                        tool_results=tool_results,
                        finish_reason=final_chunk.finish_reason if final_chunk else None,
                        accumulated_usage=self._session_accumulated_usage,
                    ),
                    assistant_usage=final_chunk.usage if final_chunk else None,
                    tool_persist_items=tool_persist_items,
                )

                if self.on_loop_end is not None:
                    await self.on_loop_end(result.messages)
                continue

            # --- 无 tool_calls：写 assistant persist ---
            await self._persist(
                "assistant",
                accumulated_content,
                seq=_assistant_seq,
                loop_count=self.loop_count,
                metadata=self._build_assistant_metadata(
                    thinking=accumulated_thinking,
                    finish_reason=final_chunk.finish_reason if final_chunk else None,
                    accumulated_usage=self._session_accumulated_usage,
                ),
                usage=final_chunk.usage if final_chunk else None,
            )

            if self._check_finished(final_chunk, accumulated_content):
                # 候选物就绪：交给外层做 review/revise 决策
                yield _CandidateReady(
                    content=accumulated_content,
                    assistant_seq=_assistant_seq,
                )
                return

            # Fallback：模型返回空内容时根据工具结果生成兜底内容并直接结束
            if not accumulated_content:
                fallback_content = self._apply_fallback(result, current_assistant_msg_idx)
                if fallback_content:
                    if self.on_loop_end is not None:
                        await self.on_loop_end(result.messages)
                    yield TextEvent(content=fallback_content)
                    yield DoneEvent(result=result)
                    return

            logger.warning(
                f"[AgentLoop:{self.config.agent_name}] "
                f"[Loop {self.loop_count}] No content, no stop signal — continuing"
            )

        # 达到最大循环
        self._finalize_terminal(result, error=f"Max loop reached ({self.config.max_loop})")
        yield ErrorEvent(error=result.error)
        yield DoneEvent(result=result)
