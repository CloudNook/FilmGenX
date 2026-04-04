"""
LLM 服务：Google Gemini 流式调用。

使用官方 google-genai SDK。
"""

import logging
from typing import AsyncGenerator, List

logger = logging.getLogger(__name__)


async def call_llm_stream(
    *,
    messages: List[dict],
    llm_config: dict,
    system_prompt: str = "",
) -> AsyncGenerator[str, None]:
    """调用 Google Gemini 流式生成，逐块 yield 文本。

    Args:
        messages:     消息历史 [{"role": "user", "content": "..."}]
        llm_config:   LLM 配置字典，含 model/api_key/temperature
        system_prompt: 可选的系统提示词覆盖

    Yields:
        文本片段（chunk）
    """
    from google import genai
    from google.genai import types

    model_name = llm_config.get("model", "gemini-2.0-flash")
    api_key = llm_config.get("api_key")
    temperature = llm_config.get("temperature")

    if not api_key:
        raise ValueError("Google API key is required")

    # 初始化客户端
    client = genai.Client(api_key=api_key)

    # 转换消息格式（Gemini 格式）
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    # 构建配置
    config_kwargs: dict = {}
    if temperature is not None:
        config_kwargs["temperature"] = temperature

    # 系统提示词
    if system_prompt:
        config_kwargs["system_instruction"] = system_prompt

    # 流式调用
    try:
        response = await client.aio.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        async for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise
