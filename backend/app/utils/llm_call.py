"""
LLM 服务：Google Gemini 流式调用。

使用官方 google-genai SDK。
API Key 从环境变量 settings.GOOGLE_API_KEY 读取，前端无需传递。
"""

import logging
from typing import AsyncGenerator, List

from app.core.config import settings

logger = logging.getLogger(__name__)

# 允许使用的模型白名单
ALLOWED_MODELS = {
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
}
DEFAULT_MODEL = "gemini-3-flash-preview"


async def call_llm_stream(
    *,
    messages: List[dict],
    llm_config: dict,
    system_prompt: str = "",
) -> AsyncGenerator[str, None]:
    """调用 Google Gemini 流式生成，逐块 yield 文本。

    Args:
        messages:     消息历史 [{"role": "user", "content": "..."}]
        llm_config:   前端传入的 LLM 配置，仅使用 model / temperature
        system_prompt: 可选的系统提示词覆盖

    Yields:
        文本片段（chunk）
    """
    from google import genai
    from google.genai import types

    model_name = llm_config.get("model") or DEFAULT_MODEL
    if model_name not in ALLOWED_MODELS:
        logger.warning(f"Unsupported model '{model_name}', falling back to {DEFAULT_MODEL}")
        model_name = DEFAULT_MODEL

    api_key = settings.GOOGLE_API_KEY
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not configured in environment")

    temperature = llm_config.get("temperature")

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
        print(f"[DEBUG] Gemini call: model={model_name}, contents={len(contents)} msgs, "
              f"system_prompt={'yes' if system_prompt else 'no'}, temp={temperature}")

        response = await client.aio.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        chunk_count = 0
        async for chunk in response:
            chunk_count += 1
            if chunk.text:
                print(f"[DEBUG] Gemini chunk #{chunk_count}: {chunk.text[:60]}...")
                yield chunk.text
            else:
                print(f"[DEBUG] Gemini chunk #{chunk_count}: NO TEXT, candidates={getattr(chunk, 'candidates', None)}")
        print(f"[DEBUG] Gemini stream done, total chunks={chunk_count}")
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise
