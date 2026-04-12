"""
内置中间件实现。

包含：
- LoggingMiddleware
- FinalSchemaResponseMiddleware
"""

import json
import logging
from typing import Any, Dict, Optional, Type, Union

from pydantic import BaseModel

from app.core.agent.usage import merge_usage
from app.core.middleware.chain import AgentMiddleware, MiddlewareContext

logger = logging.getLogger(__name__)

SchemaInput = Union[Type[BaseModel], Dict[str, Any]]


def _normalize_schema(schema: SchemaInput) -> Dict[str, Any]:
    if isinstance(schema, type) and issubclass(schema, BaseModel):
        return schema.model_json_schema()
    if isinstance(schema, dict):
        return schema
    raise TypeError(f"Unsupported schema type: {type(schema)}")


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
