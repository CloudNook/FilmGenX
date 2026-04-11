"""
交互式 Agent CLI。

运行方式：
    cd backend
    python scripts/agent_cli.py

或：
    cd backend
    python -m scripts.agent_cli
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.agent import DoneEvent, ErrorEvent, TextEvent, ThinkingEvent, ToolEndEvent, ToolStartEvent, create_agent
from app.core.agent.base import AgentResult
from app.core.agent.persist import RedisPersistStrategy
from app.core.middleware import FinalSchemaResponseMiddleware, LoggingMiddleware
from app.core.tools import ToolRegistry
from app.core.tools.examples import *  # noqa: F401, F403

DEFAULT_PROMPT = (
    "你是一个可观测的多轮助手。"
    "当用户的问题需要计算、天气、时间或搜索时，请优先使用工具。"
    "你可以进行内部思考，但面向用户的最终自然语言回答应当简洁、清楚。"
)


class InteractiveTurnSchema(BaseModel):
    answer: str = Field(..., description="本轮给用户的最终回答")
    summary: str = Field(..., description="对本轮结论的简要业务摘要")
    used_tools: list[str] = Field(default_factory=list, description="本轮实际使用过的工具名称列表")


def is_exit_command(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized in {"exit", "quit", "/exit", "/quit"}


def is_clear_command(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized in {"clear", "/clear"}


def render_result_block(result: AgentResult) -> str:
    schema_text = (
        json.dumps(result.schema_data, ensure_ascii=False, indent=2)
        if result.schema_data is not None
        else "null"
    )
    usage_text = (
        json.dumps(result.usage, ensure_ascii=False, indent=2)
        if result.usage is not None
        else "null"
    )
    return (
        "\n[Business Result]\n"
        f"finished    : {result.finished}\n"
        f"loop_count  : {result.loop_count}\n"
        f"raw_output  : {result.raw_output}\n"
        f"schema_data : {schema_text}\n"
        f"schema_error: {result.schema_error}\n"
        f"usage       : {usage_text}\n"
    )


class TurnPrinter:
    """
    将流式事件打印成较适合命令行观察的格式。
    """

    def __init__(self) -> None:
        self._thinking_open = False
        self._text_open = False
        self.saw_thinking = False

    def _close_open_blocks(self) -> None:
        if self._thinking_open or self._text_open:
            print()
        self._thinking_open = False
        self._text_open = False

    def handle(self, event) -> None:
        if isinstance(event, ThinkingEvent):
            self.saw_thinking = True
            if self._text_open:
                print()
                self._text_open = False
            if not self._thinking_open:
                print("[Thinking] ", end="", flush=True)
                self._thinking_open = True
            print(event.content, end="", flush=True)
            return

        if isinstance(event, TextEvent):
            if self._thinking_open:
                print()
                self._thinking_open = False
            if not self._text_open:
                print("[Assistant] ", end="", flush=True)
                self._text_open = True
            print(event.content, end="", flush=True)
            return

        self._close_open_blocks()

        if isinstance(event, ToolStartEvent):
            args_text = json.dumps(event.arguments, ensure_ascii=False)
            print(f"[ToolStart] {event.tool_name}({args_text})")
        elif isinstance(event, ToolEndEvent):
            print(f"[ToolEnd] {event.tool_name} -> {event.result}")
        elif isinstance(event, ErrorEvent):
            print(f"[Error] {event.error}")
        elif isinstance(event, DoneEvent):
            print("[Done] 本轮结束，准备展示最终 schema")
        else:
            print(f"[Event] {event}")

    def finish(self) -> None:
        self._close_open_blocks()


def build_agent(*, session_id: str, model: str, max_loop: int):
    ToolRegistry.discover("app.core.tools.examples")
    tools = [
        tool
        for tool in ToolRegistry.get_all_schemas()
        if tool["name"] not in ("load_skill", "load_skill_lite")
    ]

    return create_agent(
        agent_name="assistant",
        session_id=session_id,
        prompt=DEFAULT_PROMPT,
        model=model,
        tools=tools,
        max_loop=max_loop,
        persist=RedisPersistStrategy(),
        middlewares=[
            LoggingMiddleware(),
            FinalSchemaResponseMiddleware(InteractiveTurnSchema),
        ],
    )


async def clear_session(session_id: str) -> None:
    from app.utils import redis_client

    await redis_client.delete(f"agent:messages:{session_id}")
    print(f"[System] Session cleared: {session_id}")


async def chat_once(agent, user_input: str) -> AgentResult:
    printer = TurnPrinter()
    final_result: Optional[AgentResult] = None

    try:
        async for event in agent.stream(user_input):
            printer.handle(event)
            if isinstance(event, DoneEvent):
                final_result = event.result
    finally:
        printer.finish()

    if final_result is None:
        raise RuntimeError("本轮对话未收到 DoneEvent，无法取得最终结果")

    if not printer.saw_thinking:
        print(
            "[System] 本轮未收到 ThinkingEvent。"
            "这通常表示当前模型没有返回思考片段，"
            "而不是 CLI 没有打印。"
        )

    return final_result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="交互式 Agent CLI")
    parser.add_argument("--model", default="gemini-3-pro-preview", help="使用的模型名称")
    parser.add_argument("--max-loop", type=int, default=10, help="Agent 最大循环次数")
    parser.add_argument("--session-id", default=f"cli_{uuid4().hex[:8]}", help="会话 ID")
    parser.add_argument("--resume", action="store_true", help="保留已有 session 历史，不在启动时清空")
    return parser


async def async_main() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass

    args = build_arg_parser().parse_args()
    agent = build_agent(session_id=args.session_id, model=args.model, max_loop=args.max_loop)

    print("=" * 72)
    print("Interactive Agent CLI")
    print("=" * 72)
    print(f"session_id : {args.session_id}")
    print(f"model      : {args.model}")
    print("commands   : /clear 清空会话, /exit 退出")
    print("说明       : 命令行会实时打印 thinking / text / tool 过程；回合结束后展示最终 schema。")
    print("提示       : 如果某一轮没有 [Thinking]，通常是模型本轮没有返回 thought chunk。")

    if not args.resume:
        await clear_session(args.session_id)

    while True:
        try:
            user_input = input("\nYou > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[System] Bye")
            return

        if not user_input:
            continue
        if is_exit_command(user_input):
            print("[System] Bye")
            return
        if is_clear_command(user_input):
            await clear_session(args.session_id)
            continue

        result = await chat_once(agent, user_input)
        print(render_result_block(result))


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
