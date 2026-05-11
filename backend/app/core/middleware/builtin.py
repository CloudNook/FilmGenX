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


class HumanInTheLoopMiddleware(AgentMiddleware):
    """
    人工审阅中间件。

    在工具执行前拦截不在白名单的工具，等待人工确认/拒绝/取消后再继续。
    白名单内的工具直接放行，白名单外的工具触发人工审阅。
    AgentLoop 负责持久化中断状态（通过 persist.save_interrupt_state）；
    本中间件只负责判断是否需要中断。

    使用方式：
        agent = create_agent(
            ...,
            middlewares=[HumanInTheLoopMiddleware(auto_tool_list=["load_skill", "load_skill_reference"])]
        )
        # load_skill / load_skill_reference 直接执行
        # 其他所有工具（call_sub_agent / generate_image / memory_save 等）都需要人工确认
    """

    name = "hitl"

    def __init__(
        self,
        auto_tool_list: Optional[list[str]] = None,
        *,
        white_tool_list: Optional[list[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Args:
            auto_tool_list: 直接放行的工具名列表（新参数名）。
                           不在列表内的工具触发人工审阅。
            white_tool_list: auto_tool_list 的兼容别名。
            context: 中断时附加到中断信息的上下文，供前端展示用。
        """
        if auto_tool_list is None and white_tool_list is None:
            raise ValueError("auto_tool_list or white_tool_list is required")
        chosen = auto_tool_list if auto_tool_list is not None else white_tool_list
        self.auto_tool_list = set(chosen or [])
        self.context = context or {}

    async def before_tool_calls(
        self,
        ctx: MiddlewareContext,
        tool_calls: list[Any],
    ) -> MiddlewareContext:
        """
        检查是否有需要人工审阅的工具调用。

        规则：遍历 tool_calls，只要有一个工具不在 auto_tool_list 中，就中断。
        auto_tool_list 内的工具直接放行。

        中断信息写入 ctx.metadata["interrupt"]，AgentLoop 通过检查此字段决定是否中断。
        """
        for tc in tool_calls:
            if tc.name not in self.auto_tool_list:
                logger.info(
                    f"[HumanInTheLoopMiddleware] tool '{tc.name}' not in auto list, "
                    f"interrupting session={ctx.session_id}"
                )
                ctx.metadata["interrupt"] = {
                    "tool_call_id": tc.id,
                    "tool_name": tc.name,
                    "arguments": dict(tc.arguments),
                    "context": self.context,
                    "available_actions": ["approve", "reject"],
                }
                return ctx
        return ctx
