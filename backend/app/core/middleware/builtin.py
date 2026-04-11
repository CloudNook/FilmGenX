"""
内置中间件实现。

包含：
- LoggingMiddleware
- FinalSchemaResponseMiddleware
- CreditMiddleware
- SummaryMiddleware
"""

import inspect
import json
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from app.core.agent.usage import merge_usage
from app.core.middleware.chain import AgentMiddleware, MiddlewareContext

logger = logging.getLogger(__name__)

SchemaInput = Union[Type[BaseModel], Dict[str, Any]]
UsageRecorder = Callable[[MiddlewareContext, Dict[str, Any]], Awaitable[None] | None]
SummaryFn = Callable[[MiddlewareContext, List[Dict[str, Any]]], Awaitable[str] | str]
TokenEstimator = Callable[[List[Dict[str, Any]]], int]


def _normalize_schema(schema: SchemaInput) -> Dict[str, Any]:
    if isinstance(schema, type) and issubclass(schema, BaseModel):
        return schema.model_json_schema()
    if isinstance(schema, dict):
        return schema
    raise TypeError(f"Unsupported schema type: {type(schema)}")


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _merge_context_usage(ctx: MiddlewareContext, usage: Optional[Dict[str, Any]]) -> None:
    ctx.metadata["usage"] = merge_usage(ctx.metadata.get("usage"), usage)


class LoggingMiddleware(AgentMiddleware):
    """
    日志中间件。

    记录 Agent 执行的请求参数和执行结果。
    """

    name = "logging"

    async def before(self, ctx: MiddlewareContext) -> None:
        logger.info(
            f"[Agent:{ctx.agent_name}] Starting request_id={ctx.request_id}, "
            f"input={ctx.initial_input[:100]}..."
        )

    async def after(self, ctx: MiddlewareContext) -> None:
        if ctx.result:
            logger.info(
                f"[Agent:{ctx.agent_name}] Finished request_id={ctx.request_id}, "
                f"loop={ctx.loop_count}, finished={ctx.result.finished}, "
                f"error={ctx.result.error}"
            )
        else:
            logger.info(
                f"[Agent:{ctx.agent_name}] Finished request_id={ctx.request_id}, no result"
            )

    async def on_loop_start(self, ctx: MiddlewareContext) -> None:
        logger.debug(f"[Agent:{ctx.agent_name}] Loop start #{ctx.loop_count}")

    async def on_loop_end(self, ctx: MiddlewareContext) -> None:
        logger.debug(f"[Agent:{ctx.agent_name}] Loop end #{ctx.loop_count}")


class FinalSchemaResponseMiddleware(AgentMiddleware):
    """
    在 Agent 结束后追加一次结构化整理请求。

    不干扰主循环的 think/act/observe，只处理最终业务输出。
    """

    name = "final_schema_response"

    def __init__(
        self,
        response_schema: SchemaInput,
        *,
        system_prompt: str | None = None,
    ) -> None:
        self.response_schema = _normalize_schema(response_schema)
        self.system_prompt = system_prompt or (
            "你是结构化结果整理器。"
            "请根据给定的最终回答，输出严格符合 JSON Schema 的 JSON。"
            "不要输出 JSON 之外的任何文本。"
        )

    def _build_prompt(self, ctx: MiddlewareContext, raw_output: str) -> str:
        return (
            f"用户请求：\n{ctx.initial_input}\n\n"
            f"最终回答：\n{raw_output}\n\n"
            "请将最终回答整理成结构化 JSON。"
        )

    @staticmethod
    def _parse_response(ctx: MiddlewareContext, content: str) -> Optional[Dict[str, Any]]:
        if getattr(ctx.llm, "parse_json", None):
            return ctx.llm.parse_json(content)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None

    async def finalize_result(self, ctx: MiddlewareContext, result: Any) -> Any:
        if not result.finished or result.error or not result.raw_output or result.schema_data is not None:
            return result
        if ctx.llm is None:
            result.schema_error = "Final schema middleware requires llm in middleware context"
            return result

        try:
            response = await ctx.llm.generate(
                messages=[{"role": "user", "content": self._build_prompt(ctx, result.raw_output)}],
                system_prompt=self.system_prompt,
                tools=[],
                response_schema=self.response_schema,
            )
            result.usage = merge_usage(result.usage, response.usage)
            parsed = self._parse_response(ctx, response.content)
            if parsed is None:
                result.schema_error = f"Failed to parse final schema response: {response.content[:200]}"
                return result
            result.schema_data = parsed
            result.schema_error = None
        except Exception as exc:
            logger.exception("[FinalSchemaResponseMiddleware] format failed: %s", exc)
            result.schema_error = f"Failed to format final schema response: {exc}"

        return result


class CreditMiddleware(AgentMiddleware):
    """
    记录最终 usage，便于后续接入积分/账单系统。
    """

    name = "credit"

    def __init__(self, *, recorder: UsageRecorder | None = None) -> None:
        self.recorder = recorder

    async def after(self, ctx: MiddlewareContext) -> None:
        usage = getattr(ctx.result, "usage", None) if ctx.result else None
        if not usage:
            return

        if self.recorder is not None:
            await _maybe_await(self.recorder(ctx, usage))
            return

        logger.info(
            f"[Credit:{ctx.agent_name}] request_id={ctx.request_id}, usage={usage}"
        )


class SummaryMiddleware(AgentMiddleware):
    """
    当上下文过长时，对旧消息做一次压缩，保留最近若干条原始消息。
    """

    name = "summary"

    def __init__(
        self,
        *,
        max_tokens: int,
        keep_last_messages: int = 6,
        token_estimator: TokenEstimator | None = None,
        summarizer: SummaryFn | None = None,
        summary_prompt: str | None = None,
    ) -> None:
        self.max_tokens = max_tokens
        self.keep_last_messages = max(1, keep_last_messages)
        self.token_estimator = token_estimator or self._estimate_tokens
        self.summarizer = summarizer
        self.summary_prompt = summary_prompt or (
            "请将以下对话压缩成可继续推理的工作记忆。"
            "保留用户目标、关键事实、已完成的工具调用结果、未解决问题和约束。"
            "输出简洁中文。"
        )

    @staticmethod
    def _estimate_tokens(messages: List[Dict[str, Any]]) -> int:
        total_chars = sum(len(json.dumps(message, ensure_ascii=False)) for message in messages)
        return max(1, total_chars // 4)

    @staticmethod
    def _format_summary_message(summary: str) -> Dict[str, str]:
        return {
            "role": "system",
            "content": "以下是压缩后的历史上下文，请基于它继续对话：\n" + summary.strip(),
        }

    @staticmethod
    def _render_messages(messages: List[Dict[str, Any]]) -> str:
        lines = []
        for message in messages:
            role = message.get("role", "user")
            if role == "tool":
                name = message.get("tool_name", "tool")
                lines.append(f"[tool:{name}] {message.get('content', '')}")
                continue
            lines.append(f"[{role}] {message.get('content', '')}")
        return "\n".join(lines)

    async def _default_summarizer(
        self,
        ctx: MiddlewareContext,
        messages: List[Dict[str, Any]],
    ) -> str:
        if ctx.llm is None:
            return ""

        transcript = self._render_messages(messages)
        if not transcript.strip():
            return ""

        response = await ctx.llm.generate(
            messages=[{"role": "user", "content": transcript}],
            system_prompt=self.summary_prompt,
            tools=[],
        )
        _merge_context_usage(ctx, response.usage)
        return response.content.strip()

    async def on_loop_start(self, ctx: MiddlewareContext) -> None:
        if ctx.loop is None:
            return

        messages = list(ctx.loop.messages)
        if len(messages) <= self.keep_last_messages + 1:
            return
        if self.token_estimator(messages) <= self.max_tokens:
            return

        split_index = len(messages) - self.keep_last_messages
        to_summarize = messages[:split_index]
        if not to_summarize:
            return

        if self.summarizer is not None:
            summary = await _maybe_await(self.summarizer(ctx, to_summarize))
        else:
            summary = await self._default_summarizer(ctx, to_summarize)

        summary = (summary or "").strip()
        if not summary:
            return

        ctx.loop.messages = [
            self._format_summary_message(summary),
            *messages[-self.keep_last_messages:],
        ]
        ctx.metadata["summary_count"] = ctx.metadata.get("summary_count", 0) + 1
        logger.info(
            f"[Summary:{ctx.agent_name}] compressed context before loop {ctx.loop_count}, "
            f"messages {len(messages)} -> {len(ctx.loop.messages)}"
        )
