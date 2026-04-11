"""
OpenAI 适配器。

使用 OpenAI 原生 function calling API，返回结构化 LLMResponse。
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.adapter.base import ProviderAdapter
from app.core.agent.base import LLMResponse, StructuredToolCall

logger = logging.getLogger(__name__)


class OpenAIAdapter(ProviderAdapter):
    """
    OpenAI 适配器。

    优先使用 OpenAI 原生 function calling（tool_calls 字段），
    不再依赖文本解析工具调用。
    """

    provider_name = "openai"

    def __init__(self) -> None:
        import openai
        self._client = openai.AsyncOpenAI()

    def to_request(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        转换为 OpenAI API 格式。
        """
        formatted_messages = []
        for msg in messages:
            # 透传 Provider 原生 tool 消息格式（由 LLMAdapter 构建）
            if msg.get("role") == "tool":
                formatted_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id", ""),
                    "content": msg.get("content", ""),
                })
            elif msg.get("role") == "assistant" and msg.get("tool_calls"):
                # 统一格式 {id, name, arguments} → OpenAI 原生格式
                formatted_messages.append({
                    "role": "assistant",
                    "content": msg.get("content") or None,
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                            },
                        }
                        for tc in msg["tool_calls"]
                    ],
                })
            else:
                formatted_messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })

        config: Dict[str, Any] = {"model": kwargs.get("model", "gpt-4o")}
        if system_prompt:
            formatted_messages.insert(0, {"role": "system", "content": system_prompt})
        if "temperature" in kwargs:
            config["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            config["max_tokens"] = kwargs["max_tokens"]
        if kwargs.get("response_schema"):
            config["response_format"] = {"type": "json_object"}

        tool_schemas = self.to_tool_schema(tools) if tools else []
        if tool_schemas:
            config["tools"] = tool_schemas

        return {
            "messages": formatted_messages,
            "config": config,
        }

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> LLMResponse:
        """OpenAI 非流式生成，使用原生 function calling。"""
        req = self.to_request(messages, system_prompt, tools=tools, **kwargs)

        response = await self._client.chat.completions.create(
            messages=req["messages"],
            **req["config"],
        )

        choice = response.choices[0]
        msg = choice.message

        # 解析原生 tool_calls
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                func = tc.function
                args_str = func.arguments or "{}"
                try:
                    args = json.loads(args_str) if isinstance(args_str, str) else args_str
                except json.JSONDecodeError:
                    args = {"_raw": args_str}
                tool_calls.append(StructuredToolCall(
                    id=tc.id or "",
                    name=func.name or "",
                    arguments=args,
                    raw={
                        "index": tc.index,
                        "type": tc.type,
                        "function": {
                            "name": func.name,
                            "arguments": func.arguments,
                        },
                    },
                ))

        # 解析 usage
        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return LLMResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            usage=usage,
            raw={"model": response.model, "id": response.id},
        )

    async def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> AsyncGenerator[LLMResponse, None]:
        """
        OpenAI 流式生成。

        文本 chunk 逐片 yield（content 非空，tool_calls 为空）。
        最终 chunk 携带完整 finish_reason 和 tool_calls（若有）。
        """
        req = self.to_request(messages, system_prompt, tools=tools, **kwargs)

        # tool_calls 按 index 拼接（OpenAI 流式分片发送）
        accumulated_tool_calls: dict[int, dict] = {}
        finish_reason = None

        async for chunk in await self._client.chat.completions.create(
            messages=req["messages"],
            stream=True,
            **req["config"],
        ):
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            finish_reason = chunk.choices[0].finish_reason or finish_reason

            # 文本片段立刻 yield
            if delta.content:
                yield LLMResponse(content=delta.content, finish_reason=None)

            # 积累 tool_call 分片
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in accumulated_tool_calls:
                        accumulated_tool_calls[idx] = {
                            "id": tc_delta.id or "",
                            "name": "",
                            "arguments": "",
                        }
                    if tc_delta.id:
                        accumulated_tool_calls[idx]["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            accumulated_tool_calls[idx]["name"] += tc_delta.function.name
                        if tc_delta.function.arguments:
                            accumulated_tool_calls[idx]["arguments"] += tc_delta.function.arguments

        # 流结束：构建完整 tool_calls
        tool_calls = []
        for tc in sorted(accumulated_tool_calls.values(), key=lambda x: x.get("index", 0)):
            try:
                args = json.loads(tc["arguments"]) if tc["arguments"] else {}
            except json.JSONDecodeError:
                args = {"_raw": tc["arguments"]}
            tool_calls.append(StructuredToolCall(
                id=tc["id"],
                name=tc["name"],
                arguments=args,
            ))

        yield LLMResponse(
            content="",
            tool_calls=tool_calls,
            finish_reason=finish_reason or "stop",
        )

    def to_tool_schema(self, tools: List[Dict[str, Any]]) -> Any:
        """
        转换为 OpenAI 工具格式。
        """
        result = []
        for tool in tools:
            result.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
                },
            })
        return result
