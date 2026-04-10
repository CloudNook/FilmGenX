"""
Agent LLM 适配器。

使用统一的 Provider Adapter 进行请求/响应/工具 schema 转换。
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.adapter import get_adapter
from app.core.agent.base import AgentConfig

logger = logging.getLogger(__name__)


class LLMAdapter:
    """
    Agent LLM 适配器。

    持有 AgentConfig 和工具列表，通过 Provider Adapter 进行：
    - 请求格式转换
    - 响应格式转换
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

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
    ) -> str:
        """
        非流式生成。

        Args:
            messages: 消息历史
            system_prompt: 系统提示词

        Returns:
            LLM 生成的文本
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

    def parse_tool_calls(self, response_text: str) -> List[Dict[str, Any]]:
        """从响应文本中解析工具调用。"""
        return self._provider.parse_tool_calls(response_text)

    def parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """解析 LLM 输出中的 JSON。"""
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
