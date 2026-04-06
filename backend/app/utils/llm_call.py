"""
LLM 服务：Google Gemini 流式调用。

使用官方 google-genai SDK。
API Key 从环境变量 settings.GOOGLE_API_KEY 读取，前端无需传递。
"""

import json
import logging
import re
from typing import AsyncGenerator, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def parse_llm_json(text: str) -> Optional[dict]:
    """从 LLM 自由文本响应中提取第一个合法 JSON 对象。

    依次尝试以下策略：
    1. ```json ... ``` 代码块
    2. ``` ... ``` 代码块
    3. 第一个完整的 { ... } 对象（括号深度匹配）
    4. 直接解析整个文本

    Returns:
        解析成功返回 dict，失败返回 None。
    """
    # 1. ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 2. 括号深度匹配，提取第一个完整 {...}
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

    # 3. 整体解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# 允许使用的模型白名单
ALLOWED_MODELS = {
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
}
DEFAULT_MODEL = "gemini-3-flash-preview"


# 不支持的 JSON Schema 关键字（Gemini API 不识别）
_UNSUPPORTED_SCHEMA_KEYS: frozenset = frozenset({
    "exclusiveMinimum", "exclusiveMaximum", "prefixItems", "contains",
    "propertyNames", "if", "then", "else", "allOf", "anyOf", "oneOf", "not",
    "additionalProperties",
})


def _inline_schema(schema: dict) -> dict:
    """将 Pydantic JSON Schema 转为 Gemini 兼容的扁平结构。

    - 移除 $defs 并把所有 $ref 替换为内联定义
    - 过滤掉 Gemini 不支持的关键字
    """
    import copy
    defs = schema.get("$defs", {})

    def _inline(s: dict) -> dict:
        if not isinstance(s, dict):
            return s
        if s.get("type") == "array":
            return {"type": "array", "items": _inline(s.get("items", {}))}
        if "$ref" in s:
            ref_name = s["$ref"].split("/")[-1]
            return _inline(copy.deepcopy(defs.get(ref_name, {})))
        result = {}
        for k, v in s.items():
            if k in _UNSUPPORTED_SCHEMA_KEYS:
                continue
            if k == "properties":
                result[k] = {pk: _inline(pv) for pk, pv in v.items()}
            elif k == "items" and isinstance(v, dict):
                result[k] = _inline(v)
            elif k == "$defs":
                continue
            else:
                result[k] = v
        return result

    return _inline(copy.deepcopy(schema))


async def call_llm(
    *,
    messages: List[dict],
    llm_config: dict,
    system_prompt: str = "",
    response_schema=None,
) -> str:
    """调用 Google Gemini 非流式生成，返回完整文本。

    Args:
        messages:         消息历史 [{"role": "user", "content": "..."}]
        llm_config:       LLM 配置，使用 model / temperature
        system_prompt:    可选系统提示词
        response_schema:  可选 Pydantic 模型，传入后强制 JSON 结构化输出

    Returns:
        生成的文本内容
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

    client = genai.Client(api_key=api_key)

    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    config_kwargs: dict = {}
    if temperature is not None:
        config_kwargs["temperature"] = temperature
    if system_prompt:
        config_kwargs["system_instruction"] = system_prompt
    if response_schema is not None:
        config_kwargs["response_mime_type"] = "application/json"
        config_kwargs["response_schema"] = _inline_schema(response_schema.model_json_schema())

    response = await client.aio.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    return response.text


async def call_llm_stream(
    *,
    messages: List[dict],
    llm_config: dict,
    system_prompt: str = "",
    response_schema=None,
) -> AsyncGenerator[str, None]:
    """调用 Google Gemini 流式生成，逐块 yield 文本。

    Args:
        messages:     消息历史 [{"role": "user", "content": "..."}]
        llm_config:   前端传入的 LLM 配置，仅使用 model / temperature
        system_prompt: 可选的系统提示词覆盖
        response_schema: 可选 Pydantic 模型，传入后强制 JSON 结构化输出

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

    # JSON 强制输出（用于结构化生成）
    if response_schema is not None:
        config_kwargs["response_mime_type"] = "application/json"
        config_kwargs["response_schema"] = _inline_schema(response_schema.model_json_schema())
    elif "JSON" in system_prompt.upper():
        # 系统提示词提到 JSON 时也启用 JSON 模式
        config_kwargs["response_mime_type"] = "application/json"

    # 流式调用
    try:
        print(f"[DEBUG] Gemini call: model={model_name}, contents={len(contents)} msgs, "
              f"system_prompt={'yes' if system_prompt else 'no'}, temp={temperature}, "
              f"json_mode={response_schema is not None or 'JSON' in system_prompt.upper()}")

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
