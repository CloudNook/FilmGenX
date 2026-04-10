"""
LLM Provider 适配器模块。

统一适配不同 LLM Provider（OpenAI、Gemini、Claude 等）的：
- 请求格式转换
- 响应格式转换
- 工具 schema 转换

使用方式：
    from app.core.adapter import get_adapter

    adapter = get_adapter("gemini-3-flash-preview")
    tools = [{"name": "xxx", "description": "...", "parameters": {...}}]
    gemini_tools = adapter.to_tool_schema(tools)
"""

from app.core.adapter.base import ProviderAdapter
from app.core.adapter.factory import (
    get_adapter,
    register_model_prefix,
    register_provider,
)
from app.core.adapter.gemini import GeminiAdapter
from app.core.adapter.openai import OpenAIAdapter

__all__ = [
    "ProviderAdapter",
    "GeminiAdapter",
    "OpenAIAdapter",
    "get_adapter",
    "register_provider",
    "register_model_prefix",
]
