"""
Google Gemini 适配器。

处理 Gemini API 的请求/响应/工具 schema 转换。
"""

import json
import logging
import re
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.adapter.base import ProviderAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)

# Gemini 不支持的 JSON Schema 关键字
_UNSUPPORTED_SCHEMA_KEYS = frozenset({
    "exclusiveMinimum", "exclusiveMaximum", "prefixItems", "contains",
    "propertyNames", "if", "then", "else", "allOf", "anyOf", "oneOf", "not",
    "additionalProperties",
})

# 工具调用正则（支持多种格式）
TOOL_CALL_PATTERNS = [
    # <tool_call>{"name": "xxx", "arguments": {...}}</tool_call>
    re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL),
    # tool_call: xxx({...})
    re.compile(r"tool_call:\s*(\w+)\s*\(\s*(\{.*?\})\s*\)", re.DOTALL),
]


class GeminiAdapter(ProviderAdapter):
    """
    Google Gemini 适配器。
    """

    provider_name = "gemini"

    def to_request(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        转换为 Gemini API 格式。

        Gemini 消息格式：
        [{"role": "user"|"model", "parts": [{"text": "..."}]}]
        """
        contents = []
        for msg in messages:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg.get("content", "")}],
            })

        config: Dict[str, Any] = {}
        if system_prompt:
            config["system_instruction"] = {"parts": [{"text": system_prompt}]}
        if "temperature" in kwargs:
            config["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            config["max_output_tokens"] = kwargs["max_tokens"]
        if kwargs.get("response_schema"):
            config["response_mime_type"] = "application/json"
            config["response_schema"] = self._inline_schema(kwargs["response_schema"])

        tool_schemas = self.to_tool_schema(tools) if tools else []
        if tool_schemas:
            config["tools"] = tool_schemas

        return {
            "contents": contents,
            "config": config,
        }

    def _inline_schema(self, schema: dict) -> dict:
        """将 JSON Schema 转为 Gemini 扁平结构。"""
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
            if "anyOf" in s:
                alternatives = [_inline(alt) for alt in s["anyOf"]]
                for alt in alternatives:
                    if alt.get("type") == "array":
                        return {"type": "array", "items": alt.get("items", {})}
                for alt in alternatives:
                    if alt.get("type") != "null":
                        return alt
                return {"type": "null"}
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

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> str:
        """Gemini 非流式生成。"""
        from google import genai
        from google.genai import types

        req = self.to_request(messages, system_prompt, tools=tools, **kwargs)
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)

        response = await client.aio.models.generate_content(
            model=kwargs.get("model", "gemini-3-flash-preview"),
            contents=req["contents"],
            config=types.GenerateContentConfig(**req["config"]),
        )

        # 优先取纯文本
        if response.text:
            return response.text

        # response_schema 模式下返回 function_call，需要从 parts 中提取 JSON
        parts = []
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    parts.append(part.text)
                elif hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    args_str = fc.args
                    if isinstance(args_str, str):
                        parts.append(args_str)
                    else:
                        import json as _json
                        parts.append(_json.dumps(args_str, ensure_ascii=False))

        if parts:
            return "".join(parts)

        logger.warning("Gemini response has no text or function_call parts")
        return ""

    async def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Gemini 流式生成。"""
        from google import genai
        from google.genai import types

        req = self.to_request(messages, system_prompt, tools=tools, **kwargs)
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)

        response = await client.aio.models.generate_content_stream(
            model=kwargs.get("model", "gemini-3-flash-preview"),
            contents=req["contents"],
            config=types.GenerateContentConfig(**req["config"]),
        )

        async for chunk in response:
            if chunk.text:
                yield chunk.text

    def to_tool_schema(self, tools: List[Dict[str, Any]]) -> Any:
        """
        转换为 Gemini 工具格式。

        Gemini 格式：
        [{"function_declarations": [{name, description, parameters}]}]
        """
        declarations = []
        for tool in tools:
            params = tool.get("parameters", {})
            # Gemini 不支持 additionalProperties
            if "additionalProperties" in params:
                params = {k: v for k, v in params.items() if k != "additionalProperties"}

            declarations.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": self._inline_schema(params),
            })

        return [{"function_declarations": declarations}] if declarations else []

    def parse_tool_calls(self, response_text: str) -> List[Dict[str, Any]]:
        """从 Gemini 响应中解析工具调用。"""
        tool_calls = []
        seen_ids = set()

        for pattern in TOOL_CALL_PATTERNS:
            for m in pattern.finditer(response_text):
                try:
                    if pattern.groups == 1:
                        data = json.loads(m.group(1))
                        name = data.get("name", "")
                        args = data.get("arguments", data)
                    else:
                        name = m.group(1)
                        args = json.loads(m.group(2).replace("'", '"'))

                    # Gemini 返回的 tool name 可能带 default_api: 前缀，需剥离
                    if name.startswith("default_api:"):
                        name = name[len("default_api:") :]

                    import uuid
                    tc = {
                        "id": str(uuid.uuid4()),
                        "name": name,
                        "arguments": args,
                    }
                    if tc["id"] not in seen_ids:
                        tool_calls.append(tc)
                        seen_ids.add(tc["id"])
                except (json.JSONDecodeError, KeyError):
                    continue

        return tool_calls
