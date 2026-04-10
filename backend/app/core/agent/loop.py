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

from app.core.agent.base import AgentConfig, AgentMessage, AgentResult, ToolCall, ToolResult
from app.core.agent.llm import LLMAdapter
from app.core.agent.tool import ToolExecutor

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
        2. Check: 检查 finish_reason / stop signals / schema 完成
        3. Act: 执行工具（基于结构化 StructuredToolCall）
        4. Observe: 将工具结果加入消息历史（Provider 原生格式）
        5. 继续下一轮循环

    结束条件：
        - finish_reason == "stop" 且无 tool_calls → 正常结束
        - finish_reason == "tool_calls" 但数量为 0 → 结束
        - response_schema 模式下：LLM 输出了合法 JSON → 结束
        - 达到 max_loop 上限 → 超限退出
    """

    def __init__(
        self,
        config: AgentConfig,
        llm: LLMAdapter,
        tool_executor: Optional[ToolExecutor] = None,
        persist: Any = None,  # PersistStrategy | None
        session_id: str = "",
        request_id: str = "",
        on_loop_start: Optional[Any] = None,
        on_loop_end: Optional[Any] = None,
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
        self.loop_count = 0
        self._seq = 0  # 全局序号，run() 开始时从历史最大 seq + 1 初始化

    def _build_system_prompt(self) -> str:
        prompt = self.config.prompt

        tool_schemas = self.llm.get_tool_schemas()
        if tool_schemas:
            tool_section = (
                "\n\n## 可用工具\n"
                "当需要完成特定任务时，你可以调用以下工具：\n"
            )
            for schema in tool_schemas:
                if "function_declarations" in schema:
                    for fn in schema["function_declarations"]:
                        tool_section += f"- {fn['name']}: {fn.get('description', '')}\n"
                elif "type" in schema and schema["type"] == "function":
                    fn = schema["function"]
                    tool_section += f"- {fn['name']}: {fn.get('description', '')}\n"
                else:
                    tool_section += f"- {schema.get('name', '')}: {schema.get('description', '')}\n"

            tool_section += (
                "\n\n## 工具使用规则\n"
                "- 当你需要完成特定任务时，请主动调用合适的工具\n"
                "- 工具调用结果返回后，继续分析或汇总结果\n"
            )
            prompt = prompt + tool_section

        if self.config.response_schema:
            prompt = prompt + (
                "\n\n## 输出格式要求\n"
                "请严格按照以下 JSON Schema 输出最终结果：\n"
                + json.dumps(self.config.response_schema, ensure_ascii=False, indent=2)
                + "\n\n当完成所有分析后，直接输出 JSON 结果（不需要工具调用）。"
            )

        return prompt

    def _check_finished(
        self,
        response: Any,
        text: str,
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        检查是否应该结束循环。

        优先级：
        1. finish_reason == "stop" → 正常结束
        2. finish_reason == "tool_calls" 但无实际调用 → 结束
        3. 停止信号 → 结束（兼容旧模式）
        4. response_schema 模式：解析 JSON → 结束

        Returns:
            (should_finish, schema_data)
        """
        finish_reason = getattr(response, "finish_reason", None)
        if finish_reason == "stop":
            return True, None

        # 停止信号（兼容纯文本模式）
        if is_stop_signal(text):
            return True, None

        # response_schema 模式
        if self.config.response_schema and text:
            parsed = self.llm.parse_json(text)
            if parsed is not None:
                return True, parsed

        return False, None

    def _add_message(self, role: str, content: str, **kwargs) -> AgentMessage:
        msg = {"role": role, "content": content, **kwargs}
        self.messages.append(msg)
        return AgentMessage(role=role, content=content, agent_name=self.config.agent_name, **kwargs)

    async def _persist(
        self,
        role: str,
        content: str,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> None:
        """写入一条消息，seq 使用当前值后自增。"""
        if self.persist is None:
            return
        await self.persist.append_message(
            session_id=self.session_id,
            request_id=self.request_id,
            agent_name=self.config.agent_name,
            role=role,
            content=content,
            seq=self._seq,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
        )
        self._seq += 1

    async def _load_history(self) -> None:
        """从持久化存储加载历史消息，注入 self.messages，初始化 self._seq。"""
        if self.persist is None:
            return

        history = await self.persist.load_messages(self.session_id)
        if not history:
            return

        for msg in history:
            self.messages.append({
                "role": msg["role"],
                "content": msg["content"],
                **({"tool_call_id": msg["tool_call_id"]} if msg.get("tool_call_id") else {}),
                **({"tool_name": msg["tool_name"]} if msg.get("tool_name") else {}),
            })

        self._seq = max(msg.get("seq", 0) for msg in history) + 1
        logger.info(
            f"[AgentLoop:{self.config.agent_name}] "
            f"Loaded {len(history)} history messages, next seq={self._seq}"
        )

    async def run(self, initial_input: str) -> AgentResult:
        """
        执行 Agent 循环。

        先加载历史消息恢复上下文，再追加本轮用户输入，进入循环。
        """
        await self._load_history()

        result = AgentResult(
            agent_name=self.config.agent_name,
            messages=[self._add_message("user", initial_input)],
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
                    messages=self.messages,
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
                if response.tool_calls:
                    assistant_msg_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "name": tc.name,
                            "arguments": tc.arguments,
                        }
                        for tc in response.tool_calls
                    ]

                self.messages.append(assistant_msg_dict)
                current_assistant_msg_idx = len(result.messages)
                result.messages.append(
                    AgentMessage(
                        role="assistant",
                        content=response.content,
                        agent_name=self.config.agent_name,
                    )
                )
                await self._persist("assistant", response.content)

                # Step 3: 有 tool_calls → 执行工具（优先于 finish_reason 判断）
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

                    if self.tool_executor is None:
                        logger.warning(
                            f"[AgentLoop:{self.config.agent_name}] "
                            f"No tool_executor configured, skipping {len(tool_calls)} tool calls"
                        )
                    else:
                        tool_results = await self.tool_executor.execute_all(tool_calls)

                        # 构建 Provider 原生格式的 tool 结果消息
                        # 注意：传原始 result 字符串，不传 json.dumps 过的字符串
                        tool_result_dicts = [
                            {
                                "tool_call_id": tr.tool_call_id,
                                "tool_name": tr.tool_name,
                                "result": tr.result,  # 原始字符串，如 "600" 或 '{"key": "value"}'
                            }
                            for tr in tool_results
                        ]
                        tool_messages = self.llm.build_tool_messages(tool_result_dicts)

                        for i, tm in enumerate(tool_messages):
                            self.messages.append(tm)

                        for tr in tool_results:
                            # 格式化的 tool 消息用于展示/持久化，不参与 API 调用
                            formatted = f"[TOOL: {tr.tool_name}] {json.dumps(tr.result, ensure_ascii=False)}"
                            logger.info(
                                f"[AgentLoop:{self.config.agent_name}] "
                                f"[Loop {self.loop_count}] Tool result: {tr.tool_name} -> {tr.result!r}"
                            )
                            result.messages.append(
                                AgentMessage(
                                    role="tool",
                                    content=formatted,
                                    agent_name=self.config.agent_name,
                                    tool_call_id=tr.tool_call_id,
                                    tool_name=tr.tool_name,
                                )
                            )
                            await self._persist(
                                "tool", formatted,
                                tool_call_id=tr.tool_call_id,
                                tool_name=tr.tool_name,
                            )

                    # 工具执行完毕，本轮结束，继续循环让模型生成最终答案
                    if self.on_loop_end is not None:
                        await self.on_loop_end(result.messages)
                    continue

                # Step 4: 无 tool_calls → 检查是否可以结束
                finished, schema_data = self._check_finished(response, response.content)
                if finished:
                    result.finished = True
                    result.finished_at = datetime.now(timezone.utc)
                    result.schema_data = schema_data
                    result.raw_output = response.content
                    result.loop_count = self.loop_count
                    if self.on_loop_end is not None:
                        await self.on_loop_end(result.messages)
                    return result

                # Fallback：当工具执行完毕后，模型返回空 parts（无 text 无 tool_calls）
                # 说明模型拒绝生成文字，此时直接用工具结果汇总作为最终答案
                if not response.content and not response.tool_calls:
                    # 从历史消息中提取本轮所有 tool 结果
                    tool_results_texts = []
                    for msg in self.messages[-20:]:  # 看最近 20 条
                        if msg.get("role") == "user" and msg.get("parts"):
                            for part in msg["parts"]:
                                if part.get("functionResponse"):
                                    name = part["functionResponse"].get("name", "?")
                                    res = part["functionResponse"].get("response", {}).get("result", "")
                                    tool_results_texts.append(f"{name}: {res}")

                    fallback_content = (
                        "根据工具执行结果，汇总如下：\n"
                        + "\n".join(f"- {t}" for t in tool_results_texts)
                    )
                    logger.warning(
                        f"[AgentLoop:{self.config.agent_name}] "
                        f"[Loop {self.loop_count}] Model returned empty parts after tool execution. "
                        f"Using fallback: {fallback_content[:100]}"
                    )
                    # 把 fallback 内容写入 result.messages（替换当前轮次刚添加的空 assistant 消息）
                    # 注意：不调用 _persist，因为这条消息已在上一步用空 content 持久化了，
                    # 重复追加会导致 Redis List 中出现重复 seq 条目。
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

                # 无 tool_calls、无结束信号、也无内容 → 继续循环
                logger.warning(
                    f"[AgentLoop:{self.config.agent_name}] "
                    f"[Loop {self.loop_count}] No tool_calls, no content, no stop signal — continuing"
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
