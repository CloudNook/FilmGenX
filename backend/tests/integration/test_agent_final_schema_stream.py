#!/usr/bin/env python
# coding: utf-8
"""
Agent 流式过程 + 最终结构化结果集成测试脚本。

目标：
  1. 验证前端侧可以实时接收 Agent 内部过程事件
  2. 验证 DoneEvent.result 中能拿到最终 schema_data，供业务代码消费
  3. 验证在工具调用场景下，过程流和最终结构化结果可以同时成立

直接运行：
    python tests/integration/test_agent_final_schema_stream.py
"""

import asyncio
import logging
import sys
from pathlib import Path

from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 路径设置
BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

from app.core.agent import (  # noqa: E402
    DoneEvent,
    ErrorEvent,
    TextEvent,
    ThinkingEvent,
    ToolEndEvent,
    ToolStartEvent,
    create_agent,
)
from app.core.agent.persist import RedisPersistStrategy  # noqa: E402
from app.core.middleware import FinalSchemaResponseMiddleware, LoggingMiddleware  # noqa: E402
from app.core.tools import ToolRegistry  # noqa: E402
from app.core.tools.examples import *  # noqa: F401, F403, E402

ToolRegistry.discover("app.core.tools.examples")

ALL_TOOLS = [
    t for t in ToolRegistry.get_all_schemas()
    if t["name"] not in ("load_skill", "load_skill_lite")
]
CALCULATE_TOOLS = [t for t in ALL_TOOLS if t["name"] == "calculate"]
PERSIST = RedisPersistStrategy()


class ScienceAnswerSchema(BaseModel):
    answer: str
    reason: str


class CalculationAnswerSchema(BaseModel):
    expression: str
    result: str
    final_answer: str


def _event_label(event) -> str:
    if isinstance(event, ThinkingEvent):
        return f"[Thinking] {event.content[:100]}{'...' if len(event.content) > 100 else ''}"
    if isinstance(event, TextEvent):
        return f"[Text] {event.content[:100]}{'...' if len(event.content) > 100 else ''}"
    if isinstance(event, ToolStartEvent):
        return f"[ToolStart] {event.tool_name}({event.arguments})"
    if isinstance(event, ToolEndEvent):
        return f"[ToolEnd] {event.tool_name} -> {event.result}"
    if isinstance(event, DoneEvent):
        return (
            f"[Done] finished={event.result.finished}, "
            f"loop={event.result.loop_count}, "
            f"schema_ok={bool(event.result.schema_data)}, "
            f"schema_error={event.result.schema_error}"
        )
    if isinstance(event, ErrorEvent):
        return f"[Error] {event.error}"
    return f"[{type(event).__name__}]"


async def clear_session(session_id: str) -> None:
    from app.utils import redis_client

    await redis_client.delete(f"agent:messages:{session_id}")
    print(f"[Setup] Cleared session {session_id}")


async def stream_and_collect(agent, prompt: str):
    events = []
    async for event in agent.stream(prompt):
        events.append(event)
        print(_event_label(event))
    return events


async def scenario_plain_text_final_schema() -> None:
    session_id = "test_final_schema_plain_001"
    await clear_session(session_id)

    print("\n" + "=" * 60)
    print("场景一：纯文本过程流 + 最终 schema_data")
    print("=" * 60)

    agent = create_agent(
        agent_name="assistant",
        session_id=session_id,
        prompt=(
            "你是一个科普助手。"
            "可以进行内部分析，但最终面向用户的文字回答要简洁清楚。"
        ),
        model="gemini-3-pro-preview",
        max_loop=5,
        persist=PERSIST,
        middlewares=[
            LoggingMiddleware(),
            FinalSchemaResponseMiddleware(ScienceAnswerSchema),
        ],
    )

    events = await stream_and_collect(
        agent,
        "为什么天空是蓝色的？请先正常回答，再在最终结果中整理结构化结论。",
    )

    done = next((event for event in events if isinstance(event, DoneEvent)), None)
    if done is None:
        raise RuntimeError("未收到 DoneEvent")

    print("\n[Business Result]")
    print(f"raw_output   : {done.result.raw_output}")
    print(f"schema_data  : {done.result.schema_data}")
    print(f"schema_error : {done.result.schema_error}")
    print(f"usage        : {done.result.usage}")

    if not done.result.schema_data:
        raise RuntimeError("场景一失败：最终 schema_data 为空")


async def scenario_tool_stream_and_final_schema() -> None:
    session_id = "test_final_schema_tool_001"
    await clear_session(session_id)

    print("\n" + "=" * 60)
    print("场景二：工具过程流 + 最终 schema_data")
    print("=" * 60)

    agent = create_agent(
        agent_name="assistant",
        session_id=session_id,
        prompt=(
            "你是一个严谨的助手。"
            "遇到数学表达式时必须调用 calculate 工具，不能直接心算。"
            "对用户展示的最终文字要简洁。"
        ),
        model="gemini-3-flash-preview",
        tools=CALCULATE_TOOLS,
        max_loop=8,
        persist=PERSIST,
        middlewares=[
            LoggingMiddleware(),
            FinalSchemaResponseMiddleware(CalculationAnswerSchema),
        ],
    )

    events = await stream_and_collect(
        agent,
        "请计算 (88 + 12) * 2，然后告诉我结果，并整理成结构化结论。",
    )

    done = next((event for event in events if isinstance(event, DoneEvent)), None)
    tool_start_count = sum(1 for event in events if isinstance(event, ToolStartEvent))
    tool_end_count = sum(1 for event in events if isinstance(event, ToolEndEvent))

    if done is None:
        raise RuntimeError("未收到 DoneEvent")

    print("\n[Business Result]")
    print(f"raw_output   : {done.result.raw_output}")
    print(f"schema_data  : {done.result.schema_data}")
    print(f"schema_error : {done.result.schema_error}")
    print(f"usage        : {done.result.usage}")
    print(f"tool_starts  : {tool_start_count}")
    print(f"tool_ends    : {tool_end_count}")

    if tool_start_count == 0 or tool_end_count == 0:
        raise RuntimeError("场景二失败：未观察到工具调用事件")
    if not done.result.schema_data:
        raise RuntimeError("场景二失败：最终 schema_data 为空")


async def main() -> None:
    print("Agent 流式过程 + 最终结构化结果测试")
    print("说明：过程事件给前端看，DoneEvent.result 给业务代码用。")

    scenarios = [
        ("场景一：纯文本 + 结构化结果", scenario_plain_text_final_schema),
        ("场景二：工具流 + 结构化结果", scenario_tool_stream_and_final_schema),
    ]

    for label, fn in scenarios:
        try:
            await fn()
        except Exception as exc:
            logger.exception("%s 失败: %s", label, exc)

    print("\n" + "=" * 60)
    print("测试执行完毕")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
