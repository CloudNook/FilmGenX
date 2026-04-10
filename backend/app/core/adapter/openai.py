"""
OpenAI 适配器。

处理 OpenAI API 的请求/响应/工具 schema 转换。
"""

import json
import logging
import re
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.adapter.base import ProviderAdapter

logger = logging.getLogger(__name__)

# OpenAI 工具调用正则
TOOL_CALL_PATTERNS = [
    # ```json\n{"name": "xxx", "arguments": {...}}\n```
    re.compile(r'```json\s*(\{.*?\})\s*```', re.DOTALL),
    # <tool_call>{"name": "xxx", "arguments": {...}}</tool_call>
    re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL),
]


class OpenAIAdapter(ProviderAdapter):
    """
    OpenAI 适配器。
    """

    provider_name = "openai"

    def to_request(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        转换为 OpenAI API 格式。

        OpenAI 消息格式与统一格式基本一致，直接使用。
        """
        formatted_messages = []
        for msg in messages:
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
            config["response_format"] = {
                "type": "json_object",
            }

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
    ) -> str:
        """OpenAI 非流式生成。"""
        import openai

        req = self.to_request(messages, system_prompt, tools=tools, **kwargs)
        client = openai.AsyncOpenAI()

        response = await client.chat.completions.create(
            messages=req["messages"],
            **req["config"],
        )
        return response.choices[0].message.content or ""

    async def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """OpenAI 流式生成。"""
        import openai

        req = self.to_request(messages, system_prompt, tools=tools, **kwargs)
        client = openai.AsyncOpenAI()

        stream = await client.chat.completions.create(
            messages=req["messages"],
            stream=True,
            **req["config"],
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def to_tool_schema(self, tools: List[Dict[str, Any]]) -> Any:
        """
        转换为 OpenAI 工具格式。

        OpenAI 格式：
        [{"type": "function", "function": {name, description, parameters}}]
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

    def parse_tool_calls(self, response_text: str) -> List[Dict[str, Any]]:
        """从 OpenAI 响应中解析工具调用。"""
        tool_calls = []
        seen_ids = set()

        for pattern in TOOL_CALL_PATTERNS:
            for m in pattern.finditer(response_text):
                try:
                    data = json.loads(m.group(1))
                    name = data.get("name", "")
                    args = data.get("arguments", data)

                    import uuid
                    tc = {
                        "id": str(uuid.uuid4()),
                        "name": name,
                        "arguments": args,
                    }
                    if tc["id"] not in seen_ids:
                        tool_calls.append(tc)
                        seen_ids.add(tc["id"])
                except json.JSONDecodeError:
                    continue

        return tool_calls
