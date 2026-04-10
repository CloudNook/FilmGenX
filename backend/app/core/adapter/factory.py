"""
LLM Adapter 工厂。

根据 model name 自动选择对应的 Provider 适配器。
"""

import logging
from typing import Optional

from app.core.adapter.base import ProviderAdapter
from app.core.adapter.gemini import GeminiAdapter
from app.core.adapter.openai import OpenAIAdapter

logger = logging.getLogger(__name__)

# Provider 注册表
_PROVIDERS: dict[str, type[ProviderAdapter]] = {
    "gemini": GeminiAdapter,
    "openai": OpenAIAdapter,
}

# model name 前缀 → provider 映射
_MODEL_PREFIX_MAP: list[tuple[list[str], str]] = [
    (["gemini", "models/gemini"], "gemini"),
    (["gpt", "o1", "o3", "o4"], "openai"),
    (["claude", "sonnet", "haiku"], "openai"),  # Claude 也走 OpenAI 兼容接口
]


def get_adapter(model: str) -> ProviderAdapter:
    """
    根据 model name 选择对应的适配器。

    Args:
        model: 模型名称，如 "gemini-3-flash-preview"、"gpt-4o"

    Returns:
        ProviderAdapter 实例

    Raises:
        ValueError: 不支持的模型
    """
    model_lower = model.lower()

    for prefixes, provider in _MODEL_PREFIX_MAP:
        if any(model_lower.startswith(p) for p in prefixes):
            adapter_cls = _PROVIDERS.get(provider)
            if adapter_cls:
                return adapter_cls()

    # 默认尝试 Gemini
    logger.warning(f"Unknown model '{model}', defaulting to GeminiAdapter")
    return GeminiAdapter()


def register_provider(name: str, adapter_cls: type[ProviderAdapter]) -> None:
    """
    注册新的 Provider 适配器。

    Args:
        name: Provider 名称
        adapter_cls: 适配器类
    """
    _PROVIDERS[name] = adapter_cls
    logger.info(f"[AdapterFactory] Registered provider: {name}")


def register_model_prefix(prefixes: list[str], provider: str) -> None:
    """
    注册 model 前缀到 provider 的映射。

    Args:
        prefixes: model 前缀列表
        provider: Provider 名称
    """
    _MODEL_PREFIX_MAP.append((prefixes, provider))
    logger.info(f"[AdapterFactory] Registered model prefixes: {prefixes} -> {provider}")
