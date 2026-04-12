#!/usr/bin/env python
# coding: utf-8
"""
Middleware 集成测试 — LoggingMiddleware + FinalSchemaResponseMiddleware，stream 多轮对话 + 工具调用，真实 Gemini。

用法:
    cd backend
    python tests/integration/test_middleware.py
"""

import asyncio
import logging
import sys
from pathlib import Path
from uuid import uuid4

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

from app.core.agent import create_agent
from app.core.agent.base import (
    DoneEvent, ErrorEvent,
    ThinkingEvent, TextEvent,
    ToolStartEvent, ToolEndEvent,
)
from app.core.agent.persist import RedisPersistStrategy
from app.core.middleware import (
    FinalSchemaResponseMiddleware,
    LoggingMiddleware,
)
from app.core.tools import ToolRegistry

ToolRegistry.discover("app.core.tools.examples")
ALL_TOOLS = [
    t for t in ToolRegistry.get_all_schemas()
    if t["name"] not in ("load_skill", "load_skill_lite")
]


# ── 事件流打印 ────────────────────────────────────────────────────

def print_event(event) -> None:
    if isinstance(event, ThinkingEvent):
        print(f"    [Thinking] {event.content}")
    elif isinstance(event, TextEvent):
        print(f"    [Text] {event.content}")
    elif isinstance(event, ToolStartEvent):
        args_str = ", ".join(f"{k}={v}" for k, v in event.arguments.items())
        print(f"    [ToolStart] {event.tool_name}({args_str})")
    elif isinstance(event, ToolEndEvent):
        icon = "❌" if event.is_error else "✅"
        print(f"    [ToolEnd] {icon} {event.tool_name} → {event.result}")
    elif isinstance(event, ErrorEvent):
        print(f"    [Error] {event.error}")


def print_result(done: DoneEvent) -> None:
    r = done.result
    print(f"\n  ── 结果 ─────────────────────────────────")
    print(f"    finished    : {r.finished}")
    print(f"    loop_count  : {r.loop_count}")
    if r.error:
        print(f"    error       : {r.error}")
    if r.raw_output:
        print(f"    raw_output  : {r.raw_output[:200]}")
    if r.schema_data:
        print(f"    schema_data : {r.schema_data}")
    if r.schema_error:
        print(f"    schema_error: {r.schema_error}")
    if r.usage:
        print(f"    usage       : {r.usage}")


# ── Main ─────────────────────────────────────────────────────────

async def main() -> None:
    print("\nMiddleware Integration Test — Stream + Real Gemini")
    print("=" * 60)

    schema = {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "所有对话的最终总结",
            },
        },
        "required": ["summary"],
    }

    session_id = f"test_mw_{uuid4().hex[:8]}"

    agent = create_agent(
        agent_name="middleware_test",
        session_id=session_id,
        prompt=(
            "你是一个全能助手。需要计算时用 calculate，需要天气时用 get_weather，"
            "需要时间时用 current_time，需要搜索时用 search_info。"
            "请记住用户提到的所有信息。"
        ),
        model="gemini-3.1-pro-preview",
        tools=ALL_TOOLS,
        max_loop=15,
        persist=RedisPersistStrategy(),
        middlewares=[
            LoggingMiddleware(),
            FinalSchemaResponseMiddleware(schema),
        ],
    )

    rounds = [
        "请帮我做两件事：\n1. 计算 (128+72)*3\n2. 查一下北京的天气",
        "根据刚才的结果，(128+72)*3 的答案对吗？再帮我算一下 999/3",
        "搜一下 Python 的相关信息，顺便查一下当前时间",
    ]

    for i, user_input in enumerate(rounds, 1):
        print(f"\n{'─' * 60}")
        print(f"  Round {i}: {user_input}")
        print(f"{'─' * 60}")

        events = []
        tool_count = 0

        async for event in agent.stream(user_input):
            events.append(event)
            print_event(event)
            if isinstance(event, ToolStartEvent):
                tool_count += 1

        done = next(e for e in events if isinstance(e, DoneEvent))
        print_result(done)

        assert done.result.finished, f"Round {i} failed: {done.result.error}"
        print(f"    工具调用: {tool_count} 次")

    print(f"\n{'=' * 60}")
    print(f"  全部完成 — {len(rounds)} 轮对话")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
