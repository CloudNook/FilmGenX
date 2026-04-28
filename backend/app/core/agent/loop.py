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
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Optional

from fastapi.encoders import jsonable_encoder

from app.core.agent.base import (
    AgentConfig, AgentMessage, AgentResult, ToolCall, ToolExecutionResult,
    ToolResult, ThinkingEvent, TextEvent, ToolStartEvent, ToolEndEvent,
    DoneEvent, ErrorEvent, InterruptEvent, InterruptDecision, AgentInterrupted,
    AgentCheckpoint, ResumeDecision, Reviewer,
)
from app.core.agent.llm import LLMAdapter
from app.core.agent.persist.base import PersistStrategy
from app.core.agent.review import ReviewFeedbackMessage, ReviewHarness
from app.core.agent.tool import ToolExecutor
from app.core.agent.usage import merge_usage

if TYPE_CHECKING:
    from app.core.middleware.chain import MiddlewareChain, MiddlewareContext

logger = logging.getLogger(__name__)

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
        tool_executor: Optional[ToolExecutor] = None,
        persist: Optional[PersistStrategy] = None,
        session_id: str = "",
        request_id: str = "",
        on_loop_start: Optional[Any] = None,
        on_loop_end: Optional[Any] = None,
        chain: "MiddlewareChain" = None,
        reviewer: Optional[Reviewer] = None,
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

    async def _handle_candidate_review(
        self,
        *,
        candidate_output: str,
        result: AgentResult,
        ctx: Optional["MiddlewareContext"],
        candidate_seq: int = 0,
    ) -> tuple[str, list[Any]]:
        """
        Review a candidate output and prepare the next loop action.

        Returns:
            (action, events)
            - action: "passed" | "revise" | "failed" | "accept_last"
            - events: list of ReviewStartEvent / ReviewEndEvent for streaming layer
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
            return "passed", events

        if self.review_harness.can_revise(result):
            await self._append_review_feedback(
                result,
                self.review_harness.build_feedback_message(review),
            )
            if self.on_loop_end is not None:
                await self.on_loop_end(result.messages)
            return "revise", events

        # Exhausted — apply on_exhausted policy
        result.review_exhausted = True
        if self.review_harness.on_exhausted == "accept_last":
            if self.on_loop_end is not None:
                await self.on_loop_end(result.messages)
            return "accept_last", events

        result.error = "Review failed"
        result.finished = False
        result.finished_at = datetime.now(timezone.utc)
        result.loop_count = self.loop_count
        if self.on_loop_end is not None:
            await self.on_loop_end(result.messages)
        return "failed", events

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
            else:
                restored: Dict[str, Any] = {
                    "role": r.role,
                    "content": r.content,
                }
                if r.role == "assistant":
                    if metadata.get("thinking"):
                        restored["thinking"] = metadata["thinking"]
                    if metadata.get("tool_calls"):
                        # Rebuild raw for any tool call that had a
                        # thought_signature persisted, so to_request() can
                        # reconstruct a proper Part and satisfy Gemini's
                        # requirement on resume.
                        rebuilt: List[Dict[str, Any]] = []
                        for tc in metadata["tool_calls"]:
                            ts_b64 = tc.get("gemini_thought_signature")
                            if ts_b64:
                                tc = dict(tc)  # don't mutate stored metadata
                                tc["raw"] = {
                                    "gemini_thought_signature": base64.b64decode(ts_b64),
                                    "gemini_fc_name": tc.get("gemini_fc_name", tc["name"]),
                                    "gemini_fc_args": tc.get("gemini_fc_args", tc.get("arguments", {})),
                                }
                            rebuilt.append(tc)
                        restored["tool_calls"] = rebuilt
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

    async def run(
        self,
        initial_input: Optional[str],
        ctx: "MiddlewareContext" = None,
        *,
        checkpoint: Optional["AgentCheckpoint"] = None,
        resume: Optional["ResumeDecision"] = None,
    ) -> AgentResult:
        """
        执行 Agent 循环。

        resume 时：从 checkpoint 恢复 pending tool，执行后继续循环。
        """
        await self._load_history()

        # ── Resume 分支 ────────────────────────────────────────────────────────────
        if checkpoint is not None and resume is not None:
            self.loop_count = checkpoint.loop_count
            result = AgentResult(agent_name=self.config.agent_name, messages=[])

            # 执行 tool；approve 继续循环，reject 结束当前请求
            tool_result = await self._execute_pending_tool(checkpoint, resume)
            if tool_result is None:
                result.loop_count = self.loop_count
                result.error = f"Cannot find pending tool_call: {checkpoint.tool_call_id}"
                result.finished = False
                result.finished_at = datetime.now(timezone.utc)
                return result

            await self._record_tool_result(result, tool_result)
            if self.persist is not None:
                await self.persist.clear_interrupt_state(self.session_id)
            if resume.action == "reject":
                result.loop_count = self.loop_count
                result.error = "Tool call rejected by reviewer"
                result.finished = False
                result.finished_at = datetime.now(timezone.utc)
                return result

            # approve 后继续主循环，不追加新的 user 消息
            initial_input = None
        else:
            result = AgentResult(agent_name=self.config.agent_name, messages=[])

        if initial_input is not None:
            result.messages.append(self._add_message("user", initial_input, seq=self._seq))
            await self._persist("user", initial_input, loop_count=self.loop_count)

        try:
            while self.loop_count < self.config.max_loop:
                self.loop_count += 1
                logger.info(
                    f"[AgentLoop:{self.config.agent_name}] "
                    f"Loop {self.loop_count}/{self.config.max_loop}"
                )

                if self.on_loop_start is not None:
                    await self.on_loop_start()

                # Step 1: Think - 调用 LLM，返回 LLMResponse（结构化响应）
                response = await self.llm.generate(
                    messages=list(self.messages),
                    system_prompt=self._build_system_prompt(),
                    response_schema=self.config.response_schema,
                )

                # Step 2: 将 assistant 消息加入历史
                # 注意：content 即使为空也要写入（content: ""），否则消息历史
                # 中会出现连续两个 role=user 的消息（tool结果 + 新user输入），
                # 导致模型无法正确理解对话结构而拒绝生成文字。
                # 下一轮有内容时会覆盖该空消息。
                assistant_msg_dict: Dict[str, Any] = {
                    "role": "assistant",
                    "content": response.content or "",
                }
                if response.thinking:
                    assistant_msg_dict["thinking"] = response.thinking
                if response.tool_calls:
                    # 统一格式存储，Provider 转换由各自的 to_request() 负责
                    # raw 保留原始 Provider 数据（如 Gemini thought_signature），不参与持久化
                    assistant_msg_dict["tool_calls"] = [
                        {"id": tc.id, "name": tc.name, "arguments": tc.arguments, "raw": tc.raw}
                        for tc in response.tool_calls
                    ]

                self.messages.append(assistant_msg_dict)
                current_assistant_msg_idx = len(result.messages)
                _assistant_seq = self._alloc_seq()
                result.messages.append(
                    AgentMessage(
                        role="assistant",
                        content=response.content,
                        thinking=response.thinking,
                        seq=_assistant_seq,
                        agent_name=self.config.agent_name,
                    )
                )
                self._add_usage(result, response.usage)

                # Step 3: 有 tool_calls → middleware 拦截检查 → 执行工具 → 写 assistant persist
                if response.tool_calls:
                    tool_calls = [
                        ToolCall(
                            id=tc.id,
                            name=tc.name,
                            arguments=tc.arguments,
                        )
                        for tc in response.tool_calls
                    ]

                    # --- HITL 拦截点：before_tool_calls 钩子 ---
                    if self.chain is not None:
                        ctx = await self.chain.before_tool_calls(ctx, tool_calls)
                        if ctx.metadata.get("interrupt"):
                            # 先写 assistant 消息（标记 checkpoint），再持久化中断状态
                            await self._persist(
                                "assistant",
                                response.content,
                                seq=_assistant_seq,
                                loop_count=self.loop_count,
                                metadata=self._build_assistant_metadata(
                                    thinking=response.thinking,
                                    tool_calls=response.tool_calls,
                                    finish_reason=response.finish_reason,
                                    accumulated_usage=self._session_accumulated_usage,
                                ),
                                usage=response.usage,
                                is_checkpoint=True,
                            )
                            await self._persist_interrupt(ctx)
                            raise AgentInterrupted()

                    for tc in tool_calls:
                        logger.info(
                            f"[AgentLoop:{self.config.agent_name}] "
                            f"[Loop {self.loop_count}] Calling tool: {tc.name}({tc.arguments})"
                        )

                    _tool_results_for_persist: List[Any] = []
                    tool_results: List[ToolResult] = []
                    if self.tool_executor is None:
                        logger.warning(
                            f"[AgentLoop:{self.config.agent_name}] "
                            f"No tool_executor configured, skipping {len(tool_calls)} tool calls"
                        )
                    else:
                        # execute_all yields: 中间事件（ToolEndEvent 等） + ToolExecutionResult（最后）
                        execution_result: Optional[ToolExecutionResult] = None
                        async for ev in self.tool_executor.execute_all(tool_calls):
                            if isinstance(ev, ToolEndEvent):
                                pass  # run() 不需要流式中间事件
                            elif isinstance(ev, ToolExecutionResult):
                                execution_result = ev
                        tool_results = execution_result.results if execution_result else []
                        _tool_results_for_persist = tool_results

                        # 构建 Provider 原生格式的 tool 结果消息
                        # 注意：传原始 result 字符串，不传 json.dumps 过的字符串
                        for tr in tool_results:
                            raw_content = self._serialize_tool_result_content(tr.result)
                            # 统一格式写入 self.messages，to_request() 负责转为 Provider 格式
                            self.messages.append({
                                "role": "tool",
                                "tool_call_id": tr.tool_call_id,
                                "tool_name": tr.tool_name,
                                "content": raw_content,
                            })

                        # 先给每个 tool result 预分配 seq（保证顺序连续）
                        tool_persist_items = []
                        for tr in tool_results:
                            formatted = self._format_tool_result(tr.tool_name, tr.result)
                            raw_content = self._serialize_tool_result_content(tr.result)
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
                            tool_persist_items.append((tr, formatted, raw_content, tool_seq))

                    # --- after_tool_calls 钩子 ---
                    await self._handle_after_tool_calls(ctx, tool_calls, tool_results)

                    # assistant 消息（含 tool_calls + results）先写，seq 最小，保证 DB 写入顺序正确
                    await self._persist(
                        "assistant",
                        response.content,
                        seq=_assistant_seq,
                        loop_count=self.loop_count,
                        metadata=self._build_assistant_metadata(
                            thinking=response.thinking,
                            tool_calls=response.tool_calls,
                            tool_results=_tool_results_for_persist,
                            finish_reason=response.finish_reason,
                            accumulated_usage=self._session_accumulated_usage,
                        ),
                        usage=response.usage,
                        is_checkpoint=True,
                    )
                    # tool 消息紧跟 assistant 之后写入（seq 更大，DB row id 也更大）
                    for tr, formatted, raw_content, tool_seq in tool_persist_items:
                        await self._persist(
                            "tool", raw_content,
                            seq=tool_seq,
                            loop_count=self.loop_count,
                            tool_call_id=tr.tool_call_id,
                            tool_name=tr.tool_name,
                            metadata={"display_content": formatted, "is_error": tr.is_error},
                        )

                    # 工具执行完毕，本轮结束，继续循环让模型生成最终答案
                    if self.on_loop_end is not None:
                        await self.on_loop_end(result.messages)
                    continue

                # Step 4: 无 tool_calls → 写 assistant persist，再检查是否可以结束
                await self._persist(
                    "assistant",
                    response.content,
                    seq=_assistant_seq,
                    loop_count=self.loop_count,
                    metadata=self._build_assistant_metadata(
                        thinking=response.thinking,
                        finish_reason=response.finish_reason,
                        accumulated_usage=self._session_accumulated_usage,
                    ),
                    usage=response.usage,
                )
                finished = self._check_finished(response, response.content)
                if finished:
                    review_action, _review_events = await self._handle_candidate_review(
                        candidate_output=response.content,
                        result=result,
                        ctx=ctx,
                        candidate_seq=_assistant_seq,
                    )
                    if review_action == "revise":
                        continue
                    if review_action == "failed":
                        return result

                    # passed or accept_last → return last candidate as final
                    result.finished = True
                    result.finished_at = datetime.now(timezone.utc)
                    result.raw_output = response.content
                    result.loop_count = self.loop_count
                    if self.on_loop_end is not None:
                        await self.on_loop_end(result.messages)

                    return result

                # Fallback：模型返回空内容且无法正常结束
                # 常见于工具执行完毕后模型拒绝生成文字的边缘场景
                if not response.content:
                    fallback_content = self._apply_fallback(result, current_assistant_msg_idx)
                    if fallback_content:
                        if self.on_loop_end is not None:
                            await self.on_loop_end(result.messages)
                        return result

                # 无结束信号也无内容 → 继续循环
                logger.warning(
                    f"[AgentLoop:{self.config.agent_name}] "
                    f"[Loop {self.loop_count}] No content, no stop signal — continuing"
                )

            # 达到最大循环
            logger.warning(
                f"[AgentLoop:{self.config.agent_name}] "
                f"Max loop {self.config.max_loop} reached"
            )
            result.loop_count = self.loop_count
            result.error = f"Max loop reached ({self.config.max_loop})"
            result.finished = False
            result.finished_at = datetime.now(timezone.utc)
            return result

        except AgentInterrupted:
            raise
        except Exception as e:
            logger.exception(f"[AgentLoop:{self.config.agent_name}] Error: {e}")

            result.error = str(e)

            result.loop_count = self.loop_count

            result.finished = False

            result.finished_at = datetime.now(timezone.utc)

            return result


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

    async def _execute_single_tool(self, tool_call: ToolCall) -> ToolResult:
        """
        非流式地执行单个工具调用，返回最终 ToolResult。
        """
        if self.tool_executor is None:
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
                result={"error": "no tool executor"},
                is_error=True,
            )

        execution_result: Optional[ToolExecutionResult] = None
        last_tool_end: Optional[ToolEndEvent] = None
        async for ev in self.tool_executor.execute_all([tool_call]):
            if isinstance(ev, ToolEndEvent):
                last_tool_end = ev
            elif isinstance(ev, ToolExecutionResult):
                execution_result = ev

        if execution_result and execution_result.results:
            return execution_result.results[0]
        if last_tool_end is not None:
            return ToolResult(
                tool_call_id=last_tool_end.tool_call_id,
                tool_name=last_tool_end.tool_name,
                result=last_tool_end.result,
                is_error=last_tool_end.is_error,
            )
        return ToolResult(
            tool_call_id=tool_call.id,
            tool_name=tool_call.name,
            result={"error": "no result"},
            is_error=True,
        )

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

    async def _record_tool_result(
        self,
        result: AgentResult,
        tool_result: ToolResult,
    ) -> None:
        """
        将工具结果同时写入内存消息、结果消息和持久化存储。
        """
        raw_content = self._serialize_tool_result_content(tool_result.result)
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_result.tool_call_id,
            "tool_name": tool_result.tool_name,
            "content": raw_content,
        })
        formatted = self._format_tool_result(tool_result.tool_name, tool_result.result)
        tool_seq = self._alloc_seq()
        result.messages.append(
            AgentMessage(
                role="tool",
                content=formatted,
                seq=tool_seq,
                agent_name=self.config.agent_name,
                tool_call_id=tool_result.tool_call_id,
                tool_name=tool_result.tool_name,
            )
        )
        await self._persist(
            "tool",
            raw_content,
            seq=tool_seq,
            loop_count=self.loop_count,
            tool_call_id=tool_result.tool_call_id,
            tool_name=tool_result.tool_name,
            metadata={"display_content": formatted, "is_error": tool_result.is_error},
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
        result.finished = True
        result.finished_at = datetime.now(timezone.utc)
        result.raw_output = fallback_content
        result.loop_count = self.loop_count
        return fallback_content

    async def _execute_pending_tool(
        self,
        checkpoint: "AgentCheckpoint",
        resume: "ResumeDecision",
    ) -> Optional[ToolResult]:
        """
        执行 pending tool。

        用于 resume 场景（非流式调用）。
        approve/reject 返回 ToolResult。
        """
        # 找到待执行的 tool_call
        tc_to_execute = None
        for msg in reversed(self.messages):
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    if tc.get("id") == checkpoint.tool_call_id:
                        tc_to_execute = ToolCall(
                            id=tc["id"],
                            name=tc["name"],
                            arguments=tc.get("arguments", {}),
                        )
                        break
                break

        if tc_to_execute is None:
            logger.error(
                f"[AgentLoop:{self.config.agent_name}] "
                f"Cannot find tool_call_id={checkpoint.tool_call_id} in messages"
            )
            return None

        self.loop_count += 1

        if resume.action == "approve":
            # 真实执行
            if self.tool_executor is None:
                tool_result = ToolResult(
                    tool_call_id=tc_to_execute.id,
                    tool_name=tc_to_execute.name,
                    result={"error": "no tool executor"},
                    is_error=True,
                )
            else:
                tool_result = await self._execute_single_tool(tc_to_execute)
        elif resume.action == "reject":
            tool_result = self._build_rejected_tool_result(tc_to_execute)
        else:
            raise ValueError(f"Unsupported resume action: {resume.action}")

        logger.info(
            f"[AgentLoop:{self.config.agent_name}] "
            f"[Resume] Executed tool {tc_to_execute.name}, result={str(tool_result.result)[:60]}"
        )
        return tool_result

    async def _resume_from_checkpoint(
        self,
        checkpoint: "AgentCheckpoint",
        resume: "ResumeDecision",
        result: AgentResult,
        ctx: "MiddlewareContext",
    ):
        """
        从 checkpoint 恢复，执行 pending tool，继续循环。

        根据 ResumeDecision.action：
        - approve:   直接执行 tool，将结果加入消息，继续循环
        - reject:    记录“工具调用被拒绝”，结束当前请求
        """
        # 从消息历史中找到 pending tool_call
        tc_to_execute = None
        for msg in reversed(self.messages):
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    if tc.get("id") == checkpoint.tool_call_id:
                        tc_to_execute = ToolCall(
                            id=tc["id"],
                            name=tc["name"],
                            arguments=tc.get("arguments", {}),
                        )
                        break
                break

        if tc_to_execute is None:
            logger.error(
                f"[AgentLoop:{self.config.agent_name}] "
                f"Cannot find tool_call_id={checkpoint.tool_call_id} in messages"
            )
            yield ErrorEvent(error=f"Cannot find pending tool_call: {checkpoint.tool_call_id}")
            yield DoneEvent(result=result)
            return

        # 清除中断状态
        if self.persist is not None:
            await self.persist.clear_interrupt_state(self.session_id)

        self.loop_count += 1

        # 构建 ToolResult（approve/reject 共用）
        tc_for_execute = tc_to_execute
        if resume.action == "approve":
            tool_result_content = None  # 真实执行
            rejected_tool_result = None
        elif resume.action == "reject":
            rejected_tool_result = self._build_rejected_tool_result(tc_to_execute)
            tool_result_content = rejected_tool_result.result
        else:
            raise ValueError(f"Unsupported resume action: {resume.action}")

        # 执行工具
        if tool_result_content is None:
            # 真实执行
            if self.tool_executor is None:
                logger.warning(f"No tool_executor configured")
                tool_result = ToolResult(
                    tool_call_id=tc_for_execute.id,
                    tool_name=tc_for_execute.name,
                    result={"error": "no tool executor"},
                    is_error=True,
                )
            else:
                logger.info(
                    f"[AgentLoop:{self.config.agent_name}] "
                    f"[Resume Loop {self.loop_count}] Executing tool: {tc_for_execute.name} "
                    f"args={tc_for_execute.arguments}"
                )
                yield ToolStartEvent(
                    tool_call_id=tc_for_execute.id,
                    tool_name=tc_for_execute.name,
                    arguments=tc_for_execute.arguments,
                )
                async for ev in self.tool_executor.execute_all([tc_for_execute]):
                    if isinstance(ev, ToolEndEvent):
                        tool_result = ToolResult(
                            tool_call_id=ev.tool_call_id,
                            tool_name=ev.tool_name,
                            result=ev.result,
                            is_error=ev.is_error,
                        )
                        yield ev
                    elif isinstance(ev, ToolExecutionResult):
                        tool_result = ToolResult(
                            tool_call_id=tc_for_execute.id,
                            tool_name=tc_for_execute.name,
                            result=ev.results[0].result if ev.results else {"error": "no result"},
                            is_error=ev.results[0].is_error if ev.results else True,
                        )
                    elif not isinstance(ev, (ToolStartEvent,)):
                        yield ev
        else:
            # 模拟执行结果（reject）
            tool_result = ToolResult(
                tool_call_id=tc_to_execute.id,
                tool_name=tc_to_execute.name,
                result=tool_result_content,
                is_error=rejected_tool_result.is_error if rejected_tool_result else False,
            )

        await self._record_tool_result(result, tool_result)

        # after_tool_calls 钩子
        await self._handle_after_tool_calls(
            ctx, [tc_for_execute], [tool_result]
        )

        # 继续主循环（从下一轮开始）
        if self.on_loop_start is not None:
            await self.on_loop_start()
        if self.on_loop_end is not None:
            await self.on_loop_end(result.messages)

        # 继续执行主循环
        async for ev in self.stream_run("", ctx):
            yield ev

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
        # 从消息历史中找到 pending tool_call
        tc_to_execute = None
        for msg in reversed(self.messages):
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    if tc.get("id") == checkpoint.tool_call_id:
                        tc_to_execute = ToolCall(
                            id=tc["id"],
                            name=tc["name"],
                            arguments=tc.get("arguments", {}),
                        )
                        break
                break

        if tc_to_execute is None:
            logger.error(
                f"[AgentLoop:{self.config.agent_name}] "
                f"Cannot find tool_call_id={checkpoint.tool_call_id} in messages"
            )
            raise LookupError(f"Cannot find pending tool_call: {checkpoint.tool_call_id}")

        # 构建 ToolResult（approve/reject 共用）
        tc_for_execute = tc_to_execute
        if resume.action == "approve":
            tool_result_content = None  # 真实执行
            rejected_tool_result = None
        elif resume.action == "reject":
            rejected_tool_result = self._build_rejected_tool_result(tc_to_execute)
            tool_result_content = rejected_tool_result.result
        else:
            raise ValueError(f"Unsupported resume action: {resume.action}")

        # 执行工具
        if tool_result_content is None:
            # 真实执行（approve）
            if self.tool_executor is None:
                logger.warning(f"No tool_executor configured")
                tool_result = ToolResult(
                    tool_call_id=tc_for_execute.id,
                    tool_name=tc_for_execute.name,
                    result={"error": "no tool executor"},
                    is_error=True,
                )
            else:
                logger.info(
                    f"[AgentLoop:{self.config.agent_name}] "
                    f"[Resume Loop {self.loop_count}] Executing tool: {tc_for_execute.name} "
                    f"args={tc_for_execute.arguments}"
                )
                yield ToolStartEvent(
                    tool_call_id=tc_for_execute.id,
                    tool_name=tc_for_execute.name,
                    arguments=tc_for_execute.arguments,
                )
                async for ev in self.tool_executor.execute_all([tc_for_execute]):
                    if isinstance(ev, ToolEndEvent):
                        tool_result = ToolResult(
                            tool_call_id=ev.tool_call_id,
                            tool_name=ev.tool_name,
                            result=ev.result,
                            is_error=ev.is_error,
                        )
                        yield ev
                    elif isinstance(ev, ToolExecutionResult):
                        tool_result = ToolResult(
                            tool_call_id=tc_for_execute.id,
                            tool_name=tc_for_execute.name,
                            result=ev.results[0].result if ev.results else {"error": "no result"},
                            is_error=ev.results[0].is_error if ev.results else True,
                        )
                    elif not isinstance(ev, ToolStartEvent):
                        yield ev
        else:
            # 模拟执行结果（reject）
            tool_result = ToolResult(
                tool_call_id=tc_to_execute.id,
                tool_name=tc_to_execute.name,
                result=tool_result_content,
                is_error=rejected_tool_result.is_error if rejected_tool_result else False,
            )

        # 写入 tool 结果消息
        raw_content = self._serialize_tool_result_content(tool_result.result)
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_result.tool_call_id,
            "tool_name": tool_result.tool_name,
            "content": raw_content,
        })
        formatted = self._format_tool_result(tool_result.tool_name, tool_result.result)
        result.messages.append(
            AgentMessage(
                role="tool",
                content=formatted,
                seq=self._alloc_seq(),
                agent_name=self.config.agent_name,
                tool_call_id=tool_result.tool_call_id,
                tool_name=tool_result.tool_name,
            )
        )
        await self._persist(
            "tool", raw_content,
            loop_count=self.loop_count,
            tool_call_id=tool_result.tool_call_id,
            tool_name=tool_result.tool_name,
            metadata={"display_content": formatted, "is_error": tool_result.is_error},
        )

        # after_tool_calls 钩子
        await self._handle_after_tool_calls(
            ctx, [tc_for_execute], [tool_result]
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

        if checkpoint is not None and resume is not None:
            self.loop_count = checkpoint.loop_count
            result = AgentResult(agent_name=self.config.agent_name, messages=[])

            self.loop_count += 1  # 消耗一个迭代
            # 执行 tool 并 yield tool 事件
            try:
                async for ev in self._do_resume_tool(checkpoint, resume, result, ctx):
                    yield ev
            except LookupError as e:
                result.loop_count = self.loop_count
                result.error = str(e)
                result.finished = False
                result.finished_at = datetime.now(timezone.utc)
                yield ErrorEvent(error=str(e))
                yield DoneEvent(result=result)
                return
            # 清除中断状态
            if self.persist is not None:
                await self.persist.clear_interrupt_state(self.session_id)
            if resume.action == "reject":
                result.loop_count = self.loop_count
                result.error = "Tool call rejected by reviewer"
                result.finished = False
                result.finished_at = datetime.now(timezone.utc)
                yield DoneEvent(result=result)
                return
            # 进入主循环
            async for ev in self._stream_loop(result, ctx):
                yield ev
            return

        result = AgentResult(
            agent_name=self.config.agent_name,
            messages=[self._add_message("user", initial_input, seq=self._seq)],
        )
        if initial_input is not None:
            await self._persist("user", initial_input, loop_count=self.loop_count)

        async for ev in self._stream_loop(result, ctx):
            yield ev

    async def _stream_loop(self, result: AgentResult, ctx: "MiddlewareContext"):
        try:
            while self.loop_count < self.config.max_loop:
                self.loop_count += 1
                logger.info(
                    f"[AgentLoop:{self.config.agent_name}] "
                    f"Loop {self.loop_count}/{self.config.max_loop}"
                )

                if self.on_loop_start is not None:
                    await self.on_loop_start()

                # --- Think（真正流式）---
                # 边流边 yield ThinkingEvent / TextEvent，终止 chunk 收集完整 tool_calls 和 finish_reason
                accumulated_content = ""
                accumulated_thinking = ""
                final_chunk: Optional[Any] = None  # LLMResponse，终止 chunk
                buffer_text_until_review = self.review_harness.enabled

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
                        if not buffer_text_until_review:
                            yield TextEvent(content=chunk.content)
                    if chunk.finish_reason is not None:
                        # 终止 chunk，不再有文本，携带完整 tool_calls 和 usage
                        final_chunk = chunk

                # usage 只在终止 chunk 上才有值，在 stop 判断完成后统一累加
                if final_chunk is not None:
                    self._add_usage(result, final_chunk.usage)

                # --- 写入 assistant 消息 ---
                assistant_msg_dict: Dict[str, Any] = {
                    "role": "assistant",
                    "content": accumulated_content,
                }
                if accumulated_thinking:
                    assistant_msg_dict["thinking"] = accumulated_thinking
                if final_chunk.tool_calls:
                    assistant_msg_dict["tool_calls"] = [
                        {"id": tc.id, "name": tc.name, "arguments": tc.arguments, "raw": tc.raw}
                        for tc in final_chunk.tool_calls
                    ]

                self.messages.append(assistant_msg_dict)
                current_assistant_msg_idx = len(result.messages)
                _assistant_seq = self._alloc_seq()
                result.messages.append(
                    AgentMessage(
                        role="assistant",
                        content=accumulated_content,
                        thinking=accumulated_thinking,
                        seq=_assistant_seq,
                        agent_name=self.config.agent_name,
                    )
                )
                # --- Act：有 tool_calls → middleware 拦截检查 → 执行工具 → 写 assistant persist ---
                if final_chunk.tool_calls:
                    tool_calls = [
                        ToolCall(id=tc.id, name=tc.name, arguments=tc.arguments)
                        for tc in final_chunk.tool_calls
                    ]

                    # --- HITL 拦截点：before_tool_calls 钩子 ---
                    interrupt_event = await self._handle_before_tool_calls(ctx, tool_calls)
                    if interrupt_event is not None:
                        # 先写 assistant 消息（标记 checkpoint），再 yield interrupt 事件
                        await self._persist(
                            "assistant",
                            accumulated_content,
                            seq=_assistant_seq,
                            loop_count=self.loop_count,
                            metadata=self._build_assistant_metadata(
                                thinking=accumulated_thinking,
                                tool_calls=final_chunk.tool_calls,
                                finish_reason=final_chunk.finish_reason if final_chunk else None,
                                accumulated_usage=self._session_accumulated_usage,
                            ),
                            usage=final_chunk.usage if final_chunk else None,
                            is_checkpoint=True,
                        )
                        await self._persist_interrupt(ctx)
                        yield interrupt_event
                        return

                    _tool_results_for_persist: List[Any] = []
                    tool_results: List[ToolResult] = []
                    if self.tool_executor is None:
                        logger.warning(
                            f"[AgentLoop:{self.config.agent_name}] "
                            f"[Loop {self.loop_count}] No tool_executor configured, skipping {len(tool_calls)} tool calls"
                        )
                    else:
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

                        # execute_all yields: 中间事件 + ToolExecutionResult（最后）
                        execution_result: Optional[ToolExecutionResult] = None
                        async for ev in self.tool_executor.execute_all(tool_calls):
                            if isinstance(ev, ToolEndEvent):
                                # 中间事件：yield 给前端，同时记录到 tool_results
                                tool_results.append(ToolResult(
                                    tool_call_id=ev.tool_call_id,
                                    tool_name=ev.tool_name,
                                    result=ev.result,
                                    is_error=ev.is_error,
                                ))
                                _tool_results_for_persist.append(tool_results[-1])
                                yield ev
                            elif isinstance(ev, ToolExecutionResult):
                                # 批量执行完毕，最后一个产出
                                execution_result = ev
                            else:
                                # 其他中间事件（如 SubAgentStartEvent）直接 yield
                                yield ev
                        # 优先使用 execution_result（更完整），fallback 到已收集的 tool_results
                        tool_results = execution_result.results if execution_result else tool_results

                        # 批量执行完毕后，统一处理 tool_results，预分配 seq 但暂不写 DB
                        tool_persist_items = []
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
                            tool_persist_items.append((tr, formatted, raw_content, tool_seq))

                    # --- after_tool_calls 钩子 ---
                    await self._handle_after_tool_calls(ctx, tool_calls, tool_results)

                    # assistant 先写（seq 最小），tool 紧跟其后，保证 DB 写入顺序与 seq 一致
                    await self._persist(
                        "assistant",
                        accumulated_content,
                        seq=_assistant_seq,
                        loop_count=self.loop_count,
                        metadata=self._build_assistant_metadata(
                            thinking=accumulated_thinking,
                            tool_calls=final_chunk.tool_calls,
                            tool_results=_tool_results_for_persist,
                            finish_reason=final_chunk.finish_reason if final_chunk else None,
                            accumulated_usage=self._session_accumulated_usage,
                        ),
                        usage=final_chunk.usage if final_chunk else None,
                    )
                    for tr, formatted, raw_content, tool_seq in tool_persist_items:
                        await self._persist(
                            "tool", raw_content,
                            seq=tool_seq,
                            loop_count=self.loop_count,
                            tool_call_id=tr.tool_call_id,
                            tool_name=tr.tool_name,
                            metadata={"display_content": formatted, "is_error": tr.is_error},
                        )

                    if self.on_loop_end is not None:
                        await self.on_loop_end(result.messages)
                    continue

                # --- 无 tool_calls：写 assistant persist，再检查结束 ---
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
                finished = self._check_finished(final_chunk, accumulated_content)
                if finished:
                    review_action, review_events = await self._handle_candidate_review(
                        candidate_output=accumulated_content,
                        result=result,
                        ctx=ctx,
                        candidate_seq=_assistant_seq,
                    )
                    for ev in review_events:
                        yield ev
                    if review_action == "revise":
                        continue
                    if review_action == "failed":
                        yield ErrorEvent(error=result.error)
                        yield DoneEvent(result=result)
                        return

                    # passed or accept_last → return last candidate as final
                    result.finished = True
                    result.finished_at = datetime.now(timezone.utc)
                    result.raw_output = accumulated_content
                    result.loop_count = self.loop_count
                    if self.on_loop_end is not None:
                        await self.on_loop_end(result.messages)

                    if buffer_text_until_review and accumulated_content:
                        yield TextEvent(content=accumulated_content)
                    yield DoneEvent(result=result)
                    return

                # Fallback：模型返回空内容，根据工具结果生成兜底内容
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
            result.loop_count = self.loop_count
            result.error = f"Max loop reached ({self.config.max_loop})"
            result.finished = False
            result.finished_at = datetime.now(timezone.utc)
            yield ErrorEvent(error=result.error)
            yield DoneEvent(result=result)

        except Exception as e:
            logger.exception(f"[AgentLoop:{self.config.agent_name}] stream_run error: {e}")

            yield ErrorEvent(error=str(e))

            result.error = str(e)

            result.loop_count = self.loop_count

            result.finished = False

            result.finished_at = datetime.now(timezone.utc)

            yield DoneEvent(result=result)
