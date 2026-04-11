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

    def __init__(self) -> None:
        from google import genai
        self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    @staticmethod
    def _normalize_finish_reason(finish_reason) -> str:
        """
        将 Gemini FinishReason 枚举归一化为标准字符串。

        标准值：
          "stop"           — 正常结束
          "length"         — 达到 token 上限
          "content_filter" — 安全过滤
          "tool_calls"     — 需要执行工具（Gemini 不会返回此值，工具调用通过 parts 传递）
          ""               — 未知 / 未结束
        """
        if finish_reason is None:
            return ""
        # 枚举的 .name 属性是大写字符串，例如 "STOP", "MAX_TOKENS", "SAFETY"
        name = getattr(finish_reason, "name", str(finish_reason)).upper()
        _MAP = {
            "STOP": "stop",
            "1": "stop",
            "MAX_TOKENS": "length",
            "2": "length",
            "SAFETY": "content_filter",
            "3": "content_filter",
            "RECITATION": "content_filter",
            "4": "content_filter",
        }
        return _MAP.get(name, name.lower())

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
                # 统一格式 {id, name, arguments} → Gemini functionCall 格式
                parts = []
                if msg.get("content"):
                    parts.append({"text": msg["content"]})
                for tc in msg["tool_calls"]:
                    # 优先使用原始 part（保留 thought_signature 等 Gemini 特有字段）
                    gemini_part = (tc.get("raw") or {}).get("gemini_part")
                    if gemini_part is not None:
                        parts.append(gemini_part)
                    else:
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
        # thinking_config 在 generate/generate_stream 里单独构造，不走 config dict
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
        from google.genai import types

        req = self.to_request(messages, system_prompt, tools=tools, **kwargs)

        gen_config = types.GenerateContentConfig(**req["config"])
        # 始终开启 thinking（AUTO）+ 结构化 thought parts，不支持的模型会忽略
        gen_config.thinking_config = types.ThinkingConfig(thinking_budget=-1, include_thoughts=True)

        response = await self._client.aio.models.generate_content(
            model=kwargs.get("model", "gemini-3-flash-preview"),
            contents=req["contents"],
            config=gen_config,
        )

        # 解析原生 function_call parts
        tool_calls = []
        text_parts = []
        thinking_parts = []
        parts_info = []

        for candidate in response.candidates or []:
            for part in getattr(candidate.content, "parts", []):
                if hasattr(part, "text") and part.text:
                    # Gemini thinking 模型：thought=True 的 part 是思考过程，不是最终回答
                    if getattr(part, "thought", False):
                        thinking_parts.append(part.text)
                        parts_info.append(f"thought:{repr(part.text)[:50]}")
                    else:
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

                    # 保存原始 part 对象，用于下一轮请求还原 thought_signature
                    # Gemini thinking 模型要求 functionCall parts 必须原样带回
                    tool_calls.append(StructuredToolCall(
                        id=str(id(fc)),
                        name=name,
                        arguments=args,
                        raw={"gemini_part": part},
                    ))
                    parts_info.append(f"fc:{name}")

        content = "".join(text_parts)
        thinking = "".join(thinking_parts)

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
            f"finish_reason={(response.candidates[0].finish_reason if response.candidates else None)!r}"
        )

        return LLMResponse(
            content=content,
            thinking=thinking,
            tool_calls=tool_calls,
            finish_reason=self._normalize_finish_reason(
                response.candidates[0].finish_reason if response.candidates else None
            ),
            usage=usage,
            raw={"model_name": kwargs.get("model")},
        )

    async def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> AsyncGenerator[LLMResponse, None]:
        """
        Gemini 流式生成。

        文本 chunk 逐片 yield（content 非空，tool_calls 为空）。
        最终 chunk 携带完整 finish_reason 和 tool_calls（若有）。
        """
        from google.genai import types

        req = self.to_request(messages, system_prompt, tools=tools, **kwargs)

        gen_config = types.GenerateContentConfig(**req["config"])
        # 始终开启 thinking（AUTO）+ 结构化 thought parts，不支持的模型会忽略
        gen_config.thinking_config = types.ThinkingConfig(thinking_budget=-1, include_thoughts=True)

        accumulated_tool_calls: list[StructuredToolCall] = []
        finish_reason = None

        async for chunk in await self._client.aio.models.generate_content_stream(
            model=kwargs.get("model", "gemini-3-flash-preview"),
            contents=req["contents"],
            config=gen_config,
        ):
            if not chunk.candidates:
                continue

            candidate = chunk.candidates[0]
            finish_reason = candidate.finish_reason

            text_parts = []
            chunk_tool_calls = []

            for part in candidate.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    name = fc.name or ""
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
                    tc = StructuredToolCall(
                        id=str(id(fc)),
                        name=name,
                        arguments=args,
                        raw={"gemini_part": part},
                    )
                    chunk_tool_calls.append(tc)
                    accumulated_tool_calls.append(tc)
                    continue

                text = getattr(part, "text", "") or ""
                if not text:
                    continue

                # include_thoughts=True 时，模型返回 thought=True 的 part
                if getattr(part, "thought", False) is True:
                    yield LLMResponse(thinking=text, tool_calls=[], finish_reason=None)
                else:
                    text_parts.append(text)

            # 当前 chunk 纯文本部分 yield
            if text_parts:
                yield LLMResponse(
                    content="".join(text_parts),
                    tool_calls=[],
                    finish_reason=None,
                )

        # 发出携带完整 finish_reason 和 tool_calls 的终止 chunk
        yield LLMResponse(
            content="",
            tool_calls=accumulated_tool_calls,
            finish_reason=self._normalize_finish_reason(finish_reason),
        )

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
