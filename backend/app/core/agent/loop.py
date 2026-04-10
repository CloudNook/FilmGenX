"""
Agent 循环逻辑。

控制 Agent 的 think → act → observe 循环流程。
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.agent.base import AgentConfig, AgentMessage, AgentResult, ToolCall
from app.core.agent.llm import LLMAdapter
from app.core.agent.tool import ToolExecutor

logger = logging.getLogger(__name__)

# 停止信号
STOP_SIGNALS = {"<stop>", "<done>", "<finish>", "<end>"}


def is_stop_signal(text: str) -> bool:
    """判断是否为停止信号。"""
    return text.strip().lower() in STOP_SIGNALS


class AgentLoop:
    """
    Agent 循环控制器。

    循环流程：
        1. Think: 调用 LLM 生成响应
        2. Parse: 解析 LLM 输出，区分工具调用和最终答案
        3. Act: 执行工具
        4. Observe: 将工具结果加入消息历史，回到步骤 1
        5. Finish: 检测到最终答案，结束循环

    结束条件：
        - LLM 返回停止信号（<stop> / <done> 等）
        - LLM 直接输出了完整的 schema_data（JSON）
        - 达到 max_loop 上限
    """

    def __init__(
        self,
        config: AgentConfig,
        llm: LLMAdapter,
        tool_executor: Optional[ToolExecutor] = None,
        on_loop_start: Optional[Any] = None,
        on_loop_end: Optional[Any] = None,
    ):
        self.config = config
        self.llm = llm
        self.tool_executor = tool_executor
        self.on_loop_start = on_loop_start
        self.on_loop_end = on_loop_end
        self.messages: List[Dict[str, Any]] = []
        self.loop_count = 0

    def _build_system_prompt(self) -> str:
        """构建系统提示词。"""
        prompt = self.config.prompt

        # 注入工具说明
        tool_schemas = self.llm.get_tool_schemas()
        if tool_schemas:
            tool_section = (
                "\n\n## 可用工具\n"
                "当需要完成特定任务时，你可以调用以下工具：\n"
            )
            for schema in tool_schemas:
                # 统一格式
                if "function_declarations" in schema:
                    for fn in schema["function_declarations"]:
                        tool_section += f"- {fn['name']}: {fn.get('description', '')}\n"
                elif "type" in schema and schema["type"] == "function":
                    fn = schema["function"]
                    tool_section += f"- {fn['name']}: {fn.get('description', '')}\n"
                else:
                    tool_section += f"- {schema.get('name', '')}: {schema.get('description', '')}\n"

            tool_section += (
                "\n调用格式：<tool_call>{\"name\": \"工具名\", \"arguments\": {...}}</tool_call>\n"
                "返回结果后，模型继续推理，必要时可再次调用工具。"
            )
            prompt = prompt + tool_section

        # 注入 schema 输出要求
        if self.config.response_schema:
            prompt = prompt + (
                "\n\n## 输出格式要求\n"
                "请严格按照以下 JSON Schema 输出最终结果：\n"
                + json.dumps(self.config.response_schema, ensure_ascii=False, indent=2)
                + "\n\n当完成所有分析后，直接输出 JSON 结果（不需要工具调用）。"
            )

        return prompt

    def _check_finished(self, text: str) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        检查是否应该结束循环。

        Returns:
            (should_finish, schema_data)
        """
        if is_stop_signal(text):
            return True, None

        # 尝试解析 JSON Schema 数据
        if self.config.response_schema:
            parsed = self.llm.parse_json(text)
            if parsed is not None:
                return True, parsed

        return False, None

    def _add_message(self, role: str, content: str, **kwargs) -> AgentMessage:
        """添加消息到历史并返回 AgentMessage。"""
        msg = {"role": role, "content": content, **kwargs}
        self.messages.append(msg)
        return AgentMessage(role=role, content=content, agent_name=self.config.agent_name, **kwargs)

    async def run(self, initial_input: str) -> AgentResult:
        """
        执行 Agent 循环。

        Args:
            initial_input: 用户初始输入

        Returns:
            AgentResult 执行结果
        """
        result = AgentResult(
            agent_name=self.config.agent_name,
            messages=[self._add_message("user", initial_input)],
        )

        try:
            while self.loop_count < self.config.max_loop:
                self.loop_count += 1
                logger.info(
                    f"[AgentLoop:{self.config.agent_name}] Loop {self.loop_count}/{self.config.max_loop}"
                )

                if self.on_loop_start is not None:
                    await self.on_loop_start()

                # Step 1: Think - 调用 LLM
                response_text = await self.llm.generate(
                    messages=self.messages,
                    system_prompt=self._build_system_prompt(),
                )

                self._add_message("assistant", response_text)
                result.messages.append(
                    AgentMessage(
                        role="assistant",
                        content=response_text,
                        agent_name=self.config.agent_name,
                    )
                )

                # Step 2: 检查结束条件
                finished, schema_data = self._check_finished(response_text)
                if finished:
                    result.finished = True
                    result.finished_at = datetime.now(timezone.utc)
                    result.schema_data = schema_data
                    result.raw_output = response_text
                    result.loop_count = self.loop_count
                    return result

                # Step 3: 解析工具调用
                raw_calls = self.llm.parse_tool_calls(response_text)
                if not raw_calls:
                    # 没有工具调用，也没有结束信号 → 视为最终答案
                    result.finished = True
                    result.finished_at = datetime.now(timezone.utc)
                    result.raw_output = response_text
                    result.loop_count = self.loop_count
                    return result

                tool_calls = [ToolCall(**call) for call in raw_calls]

                # Step 4: Act - 执行工具
                for tc in tool_calls:
                    logger.info(
                        f"[AgentLoop:{self.config.agent_name}] "
                        f"[Loop {self.loop_count}] Calling tool: {tc.name}({tc.arguments})"
                    )

                if self.tool_executor is None:
                    logger.warning(f"No tool_executor configured, skipping {len(tool_calls)} tool calls")
                else:
                    tool_results = await self.tool_executor.execute_all(tool_calls)
                    for tr in tool_results:
                        result_text = json.dumps(tr.result, ensure_ascii=False)
                        logger.info(
                            f"[AgentLoop:{self.config.agent_name}] "
                            f"[Loop {self.loop_count}] Tool result: {tr.tool_name} -> {result_text[:200]}"
                        )
                        tool_msg = f"[TOOL: {tr.tool_name}] {result_text}"
                        self._add_message("tool", tool_msg, tool_call_id=tr.tool_call_id, tool_name=tr.tool_name)
                        result.messages.append(
                            AgentMessage(
                                role="tool",
                                content=tool_msg,
                                agent_name=self.config.agent_name,
                                tool_call_id=tr.tool_call_id,
                                tool_name=tr.tool_name,
                            )
                        )

                if self.on_loop_end is not None:
                    await self.on_loop_end(result.messages)

                # Step 5: Observe - 继续下一轮循环

            # 达到最大循环
            logger.warning(f"[AgentLoop:{self.config.agent_name}] Max loop {self.config.max_loop} reached")
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
