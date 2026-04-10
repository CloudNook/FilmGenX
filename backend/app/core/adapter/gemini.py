"""
Google Gemini 适配器。

使用 Gemini 原生 function calling API（tools + function_declarations），
返回结构化 LLMResponse。
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.adapter.base import ProviderAdapter
from app.core.agent.base import LLMResponse, StructuredToolCall
from app.core.config import settings

logger = logging.getLogger(__name__)

# Gemini 不支持的 JSON Schema 关键字
_UNSUPPORTED_SCHEMA_KEYS = frozenset({
    "exclusiveMinimum", "exclusiveMaximum", "prefixItems", "contains",
    "propertyNames", "if", "then", "else", "allOf", "anyOf", "oneOf", "not",
    "additionalProperties",
})


class GeminiAdapter(ProviderAdapter):
    """
    Google Gemini 适配器。

    使用 Gemini 原生 function calling（tools.function_declarations），
    不再依赖文本解析工具调用。
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
        [{"role": "user"|"model", "parts": [{"text": "..."}] or [...]}]
        """
        contents = []
        for msg in messages:
            role = msg.get("role", "user")

            # 透传 Provider 原生 tool 消息格式
            if role == "tool":
                # Gemini 的 tool 结果通过 functionResponse 格式返回
                contents.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": msg.get("tool_name", ""),
                            "response": {"result": msg.get("content", "")},
                        }
                    }],
                })
                continue

            if role == "assistant" and msg.get("tool_calls"):
                # Assistant 消息带原生 function_call parts
                parts = []
                if msg.get("content"):
                    parts.append({"text": msg["content"]})
                for tc in msg["tool_calls"]:
                    parts.append({
                        "functionCall": {
                            "name": tc["name"],
                            "args": tc["arguments"],
                        }
                    })
                contents.append({"role": "model", "parts": parts})
                continue

            # 普通消息
            if role == "system":
                # Gemini 没有 system role，合并到第一条 user 消息
                continue

            text = msg.get("content", "")
            contents.append({
                "role": "user" if role == "user" else "model",
                "parts": [{"text": text}] if text else [],
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
    ) -> LLMResponse:
        """Gemini 非流式生成，使用原生 function calling。"""
        from google import genai
        from google.genai import types

        req = self.to_request(messages, system_prompt, tools=tools, **kwargs)
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)

        response = await client.aio.models.generate_content(
            model=kwargs.get("model", "gemini-3-flash-preview"),
            contents=req["contents"],
            config=types.GenerateContentConfig(**req["config"]),
        )

        # 解析原生 function_call parts
        tool_calls = []
        text_parts = []

        for candidate in response.candidates:
            parts_info = []
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    text_parts.append(part.text)
                    parts_info.append(f"text:{repr(part.text)[:50]}")
                elif hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    name = fc.name or ""
                    # Gemini 返回的 tool name 可能带 default_api: 前缀，需剥离
                    if name.startswith("default_api:"):
                        name = name[len("default_api:"):]

                    args = fc.args
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {"_raw": args}
                    elif not isinstance(args, dict):
                        args = {"_raw": str(args)}

                    tool_calls.append(StructuredToolCall(
                        id=str(id(fc)),  # Gemini 原生无 id，用对象 id 代替
                        name=name,
                        arguments=args,
                        raw={"fc": str(fc)},
                    ))
                    parts_info.append(f"fc:{name}")

        content = "".join(text_parts)

        # 解析 usage
        usage = None
        if hasattr(response, "usage_metadata"):
            um = response.usage_metadata
            usage = {
                "prompt_tokens": getattr(um, "prompt_token_count", None),
                "completion_tokens": getattr(um, "candidates_token_count", None),
                "total_tokens": getattr(um, "total_token_count", None),
            }

        # DEBUG: 打印原始响应
        logger.info(
            f"[GeminiAdapter] parts_info={parts_info!r}, "
            f"tool_calls={[tc.name for tc in tool_calls]}, "
            f"finish_reason={response.candidates[0].finish_reason if response.candidates else None!r}"
        )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=response.candidates[0].finish_reason if response.candidates else None,
            usage=usage,
            raw={"model_name": kwargs.get("model")},
        )

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
        """
        declarations = []
        for tool in tools:
            params = tool.get("parameters", {})
            if "additionalProperties" in params:
                params = {k: v for k, v in params.items() if k != "additionalProperties"}

            declarations.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": self._inline_schema(params),
            })

        return [{"function_declarations": declarations}] if declarations else []
