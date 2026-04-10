"""
LLM Provider 适配器基类。

定义统一接口，所有 Provider 适配器需实现以下转换：
- to_request(): 将统一消息格式转为 Provider 请求格式
- to_response(): 将 Provider 响应转为统一格式
- to_tool_schema(): 将统一工具定义转为 Provider 工具格式
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.agent.base import LLMResponse


class ProviderAdapter(ABC):
    """
    LLM Provider 适配器基类。

    统一封装不同 Provider（OpenAI、Gemini、Claude 等）的：
    - 请求格式转换
    - 响应格式转换
    - 工具 schema 转换
    """

    provider_name: str = ""

    @abstractmethod
    def to_request(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        将统一消息格式转为 Provider 请求格式。

        Args:
            messages: 统一消息格式 [{"role": "user", "content": "..."}]
            system_prompt: 系统提示词
            **kwargs: 其他参数（temperature、max_tokens 等）

        Returns:
            Provider 特定的请求字典
        """
        ...

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        **kwargs,
    ) -> LLMResponse:
        """
        非流式生成。

        返回结构化响应，包含文本内容和原生 tool_calls。
        优先使用 Provider 原生 function calling API，
        不再依赖文本解析。

        Args:
            messages: 消息列表
            system_prompt: 系统提示词
            **kwargs: 其他参数

        Returns:
            LLMResponse 结构化响应
        """
        ...

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        流式生成。

        Args:
            messages: 消息列表
            system_prompt: 系统提示词
            **kwargs: 其他参数

        Yields:
            文本片段
        """
        ...

    @abstractmethod
    def to_tool_schema(self, tools: List[Dict[str, Any]]) -> Any:
        """
        将统一工具定义转为 Provider 工具格式。

        Args:
            tools: 统一工具定义 [{"name": "xxx", "description": "...", "parameters": {...}}]

        Returns:
            Provider 特定的工具格式
        """
        ...
