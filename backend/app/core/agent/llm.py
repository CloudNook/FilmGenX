"""
Agent LLM 适配器。

使用统一的 Provider Adapter 进行请求/响应/工具 schema 转换。
核心变化：generate() 返回 LLMResponse（包含原生 tool_calls），
不再依赖文本解析工具调用。
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.adapter import get_adapter
from app.core.agent.base import AgentConfig, LLMResponse, StructuredToolCall, UnifiedToolMessage

logger = logging.getLogger(__name__)


class LLMAdapter:
    """
    Agent LLM 适配器。

    持有 AgentConfig 和工具列表，通过 Provider Adapter 进行：
    - 请求格式转换
    - 响应格式转换（返回 LLMResponse，原生 tool_calls）
    - 工具 schema 转换
    """

    def __init__(
        self,
        config: AgentConfig,
        tools: List[Dict[str, Any]] | None = None,
    ):
        self.config = config
        self.tools = tools or []
        self._provider = get_adapter(config.model)

    def _build_llm_kwargs(self) -> Dict[str, Any]:
        """构建 LLM 调用参数。"""
        kwargs = {
            "model": self.config.model,
        }
        if self.config.temperature is not None:
            kwargs["temperature"] = self.config.temperature
        if self.config.max_tokens is not None:
            kwargs["max_tokens"] = self.config.max_tokens
        if self.config.response_schema:
            kwargs["response_schema"] = self.config.response_schema
        return kwargs

    def get_tool_schemas(self) -> Any:
        """获取当前 Provider 的工具 schema。"""
        if not self.tools:
            return []
        return self._provider.to_tool_schema(self.tools)

    def build_tool_messages(
        self,
        tool_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        将工具执行结果构建为 Provider 原生 tool 消息格式。

        Args:
            tool_results: 工具结果列表，每项包含 tool_call_id / tool_name / result

        Returns:
            Provider 原生格式的 tool 消息列表
        """
        provider = self._provider.provider_name
        messages = []
        for tr in tool_results:
            # tr["result"] 已经是原始字符串，直接传给 UnifiedToolMessage
            # 不要在这里 json.dumps，避免双重序列化
            msg = UnifiedToolMessage(
                tool_call_id=tr["tool_call_id"],
                tool_name=tr["tool_name"],
                content=tr["result"],
            )
            messages.append(msg.to_provider_format(provider))
        return messages

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
    ) -> LLMResponse:
        """
        非流式生成。

        Args:
            messages: 消息历史（统一格式）
            system_prompt: 系统提示词

        Returns:
            LLMResponse 结构化响应（包含 content + 原生 tool_calls）
        """
        full_system = system_prompt or self.config.prompt
        kwargs = self._build_llm_kwargs()

        return await self._provider.generate(
            messages=messages,
            system_prompt=full_system,
            tools=self.tools,
            **kwargs,
        )

    async def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
    ) -> AsyncGenerator[str, None]:
        """
        流式生成。

        Args:
            messages: 消息历史
            system_prompt: 系统提示词

        Yields:
            文本片段
        """
        full_system = system_prompt or self.config.prompt
        kwargs = self._build_llm_kwargs()

        async for chunk in self._provider.generate_stream(
            messages=messages,
            system_prompt=full_system,
            tools=self.tools,
            **kwargs,
        ):
            yield chunk

    # ------------------------------------------------------------------
    # 以下方法已废弃，不再用于主流程
    # 保留用于渐进式迁移和调试场景
    # ------------------------------------------------------------------

    def parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        解析 LLM 输出中的 JSON（仅用于 response_schema 模式）。

        Deprecated: 当 finish_reason == "stop" 且 content 不为空时，
        直接将 content 当作 JSON 解析即可。
        """
        import re

        # 尝试 ```json ... ``` 块
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试括号深度匹配
        start = text.find("{")
        if start != -1:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i + 1])
                        except json.JSONDecodeError:
                            break

        # 尝试整体解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
