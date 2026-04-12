"""
Agent 循环逻辑。

控制 Agent 的 think → act → observe 循环流程。
核心变化：使用 LLMResponse 结构化响应，包含原生 tool_calls，
不再依赖文本解析。
持久化由 AgentLoop 在每条消息产生后直接驱动，与 middleware 无关。
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.agent.base import (
    AgentConfig, AgentMessage, AgentResult, ToolCall, ToolResult,
    ThinkingEvent, TextEvent, ToolStartEvent, ToolEndEvent, DoneEvent, ErrorEvent,
    InterruptEvent,
)
from app.core.agent.llm import LLMAdapter
from app.core.agent.persist.base import PersistStrategy
from app.core.agent.tool import ToolExecutor
from app.core.agent.usage import merge_usage

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
        interrupt_config=None,
        initial_messages=None,
        initial_loop_count: int = 0,
    ):
        self.config = config
        self.llm = llm
        self.tool_executor = tool_executor
        self.persist = persist
        self.session_id = session_id
        self.request_id = request_id
        self.on_loop_start = on_loop_start
        self.on_loop_end = on_loop_end
        self.messages: List[Dict[str, Any]] = []
        self.loop_count = initial_loop_count
        self._seq = 0  # 全局序号，run() 开始时从历史最大 seq + 1 初始化
        self._system_prompt: Optional[str] = None  # 缓存，内容不随循环变化
        self._session_accumulated_usage: Optional[Dict[str, Any]] = None  # 会话历史累积 usage
        self.interrupt_config = interrupt_config
        if initial_messages is not None:
            self.messages = initial_messages

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

    def _should_interrupt(
        self,
        tool_name: str,
        tool_result: Any = None,
    ) -> bool:
        """Check if this tool execution should trigger an interrupt."""
        if self.interrupt_config is None or not self.interrupt_config.enabled:
            return False
        if self.interrupt_config.mode.value != "after_tool":
            return False
        if not self.interrupt_config.tool_names:
            pass
        elif tool_name not in self.interrupt_config.tool_names:
            return False
        review_filter = self.interrupt_config.context.get("review_sub_agents")
        if review_filter and tool_result is not None:
            if isinstance(tool_result, dict):
                sub_name = tool_result.get("sub_agent_name", "")
                if sub_name and sub_name not in review_filter:
                    return False
        return True

    async def _save_checkpoint(self, tool_name: str) -> None:
        """Save interrupt checkpoint via persist strategy."""
        if self.persist is None or self.interrupt_config is None:
            return
        from app.core.agent.checkpoint import AgentCheckpoint
        checkpoint = AgentCheckpoint(
            session_id=self.session_id,
            messages=list(self.messages),
            loop_count=self.loop_count,
            interrupt_tool_name=tool_name,
            interrupt_config=self.interrupt_config,
        )
        await self.persist.save_checkpoint(checkpoint)
        logger.info(
            f"[AgentLoop:{self.config.agent_name}] "
            f"Checkpoint saved for session={self.session_id}, tool={tool_name}"
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
            out.append(entry)
        return out

    @staticmethod
    def _serialize_tool_result_content(result: Any) -> str:
        return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)

    @staticmethod
    def _format_tool_result(tool_name: str, result: Any) -> str:
        return f"[TOOL: {tool_name}] {json.dumps(result, ensure_ascii=False)}"

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
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        usage: Optional[Dict[str, Any]] = None,
        seq: Optional[int] = None,
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
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            metadata=metadata,
            usage=usage,
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
                        restored["tool_calls"] = metadata["tool_calls"]
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

    async def run(self, initial_input: str) -> AgentResult:
        """
        执行 Agent 循环。

        先加载历史消息恢复上下文，再追加本轮用户输入，进入循环。
        """
        await self._load_history()

        result = AgentResult(
            agent_name=self.config.agent_name,
            messages=[self._add_message("user", initial_input, seq=self._seq)],
        )
        await self._persist("user", initial_input)

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

                # Step 3: 有 tool_calls → 先执行工具，再写 assistant persist（以便携带 result）
                if response.tool_calls:
                    # Step 5: Act - 执行工具
                    tool_calls = [
                        ToolCall(
                            id=tc.id,
                            name=tc.name,
                            arguments=tc.arguments,
                        )
                        for tc in response.tool_calls
                    ]

                    for tc in tool_calls:
                        logger.info(
                            f"[AgentLoop:{self.config.agent_name}] "
                            f"[Loop {self.loop_count}] Calling tool: {tc.name}({tc.arguments})"
                        )

                    _tool_results_for_persist: List[Any] = []
                    if self.tool_executor is None:
                        logger.warning(
                            f"[AgentLoop:{self.config.agent_name}] "
                            f"No tool_executor configured, skipping {len(tool_calls)} tool calls"
                        )
                    else:
                        # execute_all yields: intermediate events + list[ToolResult] (last)
                        tool_results: List[Any] = []
                        pending_list: List[Any] = []
                        async for ev in self.tool_executor.execute_all(tool_calls):
                            if isinstance(ev, list):
                                pending_list.append(ev)
                            elif isinstance(ev, (ToolEndEvent, ToolResult)):
                                tool_results.append(ev)
                        # 最后一个 list 是完整结果
                        if pending_list:
                            tool_results = pending_list[-1]
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

                        for tr in tool_results:
                            # 格式化的 tool 消息用于展示/持久化，不参与 API 调用
                            formatted = self._format_tool_result(tr.tool_name, tr.result)
                            raw_content = self._serialize_tool_result_content(tr.result)
                            logger.info(
                                f"[AgentLoop:{self.config.agent_name}] "
                                f"[Loop {self.loop_count}] Tool result: {tr.tool_name} -> {tr.result!r}"
                            )
                            result.messages.append(
                                AgentMessage(
                                    role="tool",
                                    content=formatted,
                                    seq=self._seq,
                                    agent_name=self.config.agent_name,
                                    tool_call_id=tr.tool_call_id,
                                    tool_name=tr.tool_name,
                                )
                            )
                            await self._persist(
                                "tool", raw_content,
                                tool_call_id=tr.tool_call_id,
                                tool_name=tr.tool_name,
                                metadata={"display_content": formatted, "is_error": tr.is_error},
                            )

                    # 工具执行完毕后写 assistant 消息（携带 tool_results，使用预分配 seq）
                    await self._persist(
                        "assistant",
                        response.content,
                        seq=_assistant_seq,
                        metadata=self._build_assistant_metadata(
                            thinking=response.thinking,
                            tool_calls=response.tool_calls,
                            tool_results=_tool_results_for_persist,
                            finish_reason=response.finish_reason,
                            accumulated_usage=self._session_accumulated_usage,
                        ),
                        usage=response.usage,
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
                    metadata=self._build_assistant_metadata(
                        thinking=response.thinking,
                        finish_reason=response.finish_reason,
                        accumulated_usage=self._session_accumulated_usage,
                    ),
                    usage=response.usage,
                )
                finished = self._check_finished(response, response.content)
                if finished:
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
                    tool_results_texts = [
                        msg.content
                        for msg in result.messages
                        if msg.role == "tool" and msg.content
                    ]
                    fallback_content = (
                        "根据工具执行结果，汇总如下：\n"
                        + "\n".join(f"- {t}" for t in tool_results_texts)
                    ) if tool_results_texts else ""

                    if fallback_content:
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

        except Exception as e:
            logger.exception(f"[AgentLoop:{self.config.agent_name}] Error: {e}")
            result.error = str(e)
            result.loop_count = self.loop_count
            result.finished = False
            result.finished_at = datetime.now(timezone.utc)
            return result

    async def stream_run(self, initial_input: str):
        """
        执行 Agent 循环（流式）。

        每轮：
          1. 流式调用 LLM，文本 chunk 实时 yield TextEvent
          2. 终止 chunk 到达后判断：
             - 有 tool_calls → yield ToolStartEvent → 执行 → yield ToolEndEvent → 继续循环
             - 无 tool_calls → 检查结束条件 → yield DoneEvent
        """
        await self._load_history()

        result = AgentResult(
            agent_name=self.config.agent_name,
            messages=[self._add_message("user", initial_input, seq=self._seq)],
        )
        await self._persist("user", initial_input)

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

                async for chunk in self.llm.generate_stream(
                    messages=list(self.messages),
                    system_prompt=self._build_system_prompt(),
                ):
                    if chunk.thinking:
                        accumulated_thinking += chunk.thinking
                        yield ThinkingEvent(content=chunk.thinking)
                    if chunk.content:
                        accumulated_content += chunk.content
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
                # --- Act：有 tool_calls → 先执行工具，再写 assistant persist（携带 result）---
                if final_chunk.tool_calls:
                    tool_calls = [
                        ToolCall(id=tc.id, name=tc.name, arguments=tc.arguments)
                        for tc in final_chunk.tool_calls
                    ]

                    _tool_results_for_persist: List[Any] = []
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

                        tool_results: List[Any] = []
                        pending_list: List[Any] = []
                        async for ev in self.tool_executor.execute_all(tool_calls):
                            if isinstance(ev, list):
                                pending_list.append(ev)
                                continue
                            elif isinstance(ev, ToolResult):
                                tr = ev
                                tool_results.append(ev)
                                _tool_results_for_persist.append(ev)
                            elif isinstance(ev, ToolEndEvent):
                                tr = ToolResult(
                                    tool_call_id=ev.tool_call_id,
                                    tool_name=ev.tool_name,
                                    result=ev.result,
                                    is_error=ev.is_error,
                                )
                                tool_results.append(tr)
                                _tool_results_for_persist.append(tr)
                            else:
                                # Intermediate event (e.g. SubAgentStartEvent) — yield directly
                                yield ev
                                continue

                            # Process ToolResult
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
                            result.messages.append(
                                AgentMessage(
                                    role="tool",
                                    content=formatted,
                                    seq=self._seq,
                                    agent_name=self.config.agent_name,
                                    tool_call_id=tr.tool_call_id,
                                    tool_name=tr.tool_name,
                                )
                            )
                            await self._persist(
                                "tool", raw_content,
                                tool_call_id=tr.tool_call_id,
                                tool_name=tr.tool_name,
                                metadata={"display_content": formatted, "is_error": tr.is_error},
                            )
                            yield ToolEndEvent(
                                tool_call_id=tr.tool_call_id,
                                tool_name=tr.tool_name,
                                result=tr.result,
                                is_error=tr.is_error,
                            )
                            # --- Framework-level HITL interrupt check ---
                            if self._should_interrupt(tr.tool_name, tr.result):
                                # Save checkpoint BEFORE yielding, because
                                # the caller may switch to resume() generator
                                # and abandon this one (code after yield won't run).
                                await self._save_checkpoint(tr.tool_name)
                                yield InterruptEvent(
                                    session_id=self.session_id,
                                    tool_name=tr.tool_name,
                                    tool_call_id=tr.tool_call_id,
                                    tool_result=tr.result,
                                    arguments=tc.arguments,
                                    context=self.interrupt_config.context if self.interrupt_config else {},
                                )
                                return

                    # 工具执行完毕后写 assistant 消息（携带 tool_results，使用预分配 seq）
                    await self._persist(
                        "assistant",
                        accumulated_content,
                        seq=_assistant_seq,
                        metadata=self._build_assistant_metadata(
                            thinking=accumulated_thinking,
                            tool_calls=final_chunk.tool_calls,
                            tool_results=_tool_results_for_persist,
                            finish_reason=final_chunk.finish_reason if final_chunk else None,
                            accumulated_usage=self._session_accumulated_usage,
                        ),
                        usage=final_chunk.usage if final_chunk else None,
                    )

                    if self.on_loop_end is not None:
                        await self.on_loop_end(result.messages)
                    continue

                # --- 无 tool_calls：写 assistant persist，再检查结束 ---
                await self._persist(
                    "assistant",
                    accumulated_content,
                    seq=_assistant_seq,
                    metadata=self._build_assistant_metadata(
                        thinking=accumulated_thinking,
                        finish_reason=final_chunk.finish_reason if final_chunk else None,
                        accumulated_usage=self._session_accumulated_usage,
                    ),
                    usage=final_chunk.usage if final_chunk else None,
                )
                finished = self._check_finished(final_chunk, accumulated_content)
                if finished:
                    result.finished = True
                    result.finished_at = datetime.now(timezone.utc)
                    result.raw_output = accumulated_content
                    result.loop_count = self.loop_count
                    if self.on_loop_end is not None:
                        await self.on_loop_end(result.messages)

                    yield DoneEvent(result=result)
                    return

                # Fallback：模型返回空内容
                if not accumulated_content:
                    tool_results_texts = [
                        msg.content
                        for msg in result.messages
                        if msg.role == "tool" and msg.content
                    ]
                    if tool_results_texts:
                        fallback_content = (
                            "根据工具执行结果，汇总如下：\n"
                            + "\n".join(f"- {t}" for t in tool_results_texts)
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
                        yield TextEvent(content=fallback_content)
                        if self.on_loop_end is not None:
                            await self.on_loop_end(result.messages)
    
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
