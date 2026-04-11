#!/usr/bin/env python
# coding: utf-8
"""
Agent.stream() 流式测试脚本。

测试场景：
  1. agent.stream() 能正常 yield TextEvent / ThinkingEvent / ToolStartEvent / ToolEndEvent / DoneEvent
  2. Middleware 钩子在流式场景下正确执行
  3. ThinkingEvent（思考过程）被正确区分和输出
  4. 多轮工具调用后的流式恢复

直接运行：python tests/integration/test_agent_stream.py
"""

import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 路径设置
BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

from app.core.agent import create_agent, ThinkingEvent, TextEvent, ToolStartEvent, ToolEndEvent, DoneEvent, ErrorEvent
from app.core.agent.persist import RedisPersistStrategy
from app.core.middleware import LoggingMiddleware
from app.core.tools import ToolRegistry
from app.core.tools.examples import *  # noqa: F401, F403

ToolRegistry.discover("app.core.tools.examples")
ALL_TOOLS = [
    t for t in ToolRegistry.get_all_schemas()
    if t["name"] not in ("load_skill", "load_skill_lite")
]

SESSION_ID = "test_stream_session_001"
PERSIST = RedisPersistStrategy()


def _event_label(event) -> str:
    """打印事件类型和内容。"""
    if isinstance(event, ThinkingEvent):
        return f"[Thinking] {event.content[:80]}{'...' if len(event.content) > 80 else ''}"
    if isinstance(event, TextEvent):
        return f"[Text] {event.content[:80]}{'...' if len(event.content) > 80 else ''}"
    if isinstance(event, ToolStartEvent):
        return f"[ToolStart] {event.tool_name}({event.arguments})"
    if isinstance(event, ToolEndEvent):
        return f"[ToolEnd] {event.tool_name} → {str(event.result)[:60]}{'...' if len(str(event.result)) > 60 else ''}"
    if isinstance(event, DoneEvent):
        return f"[Done] finished={event.result.finished}, loops={event.result.loop_count}, error={event.result.error}"
    if isinstance(event, ErrorEvent):
        return f"[Error] {event.error}"
    return f"[{type(event).__name__}]"


async def clear_session():
    from app.utils import redis_client
    await redis_client.delete(f"agent:messages:{SESSION_ID}")
    print(f"[Setup] Cleared session {SESSION_ID}\n")


async def test_stream_simple():
    """场景一：纯文本流式输出，无工具调用"""
    print("\n" + "=" * 60)
    print("场景一：纯文本流式输出")
    print("=" * 60)

    agent = create_agent(
        agent_name="assistant",
        session_id=SESSION_ID,
        prompt="你是一个简洁的助手，请直接回答问题。",
        model="gemini-3.1-pro-preview",
        max_loop=5,
        persist=PERSIST,
        middlewares=[LoggingMiddleware()],
    )

    event_count = 0
    async for event in agent.stream("请介绍一下Python语言"):
        event_count += 1
        print(_event_label(event))

    print(f"\n共收到 {event_count} 个事件")


async def test_stream_with_thinking():
    """场景二：Thinking 模型，验证 ThinkingEvent 输出"""
    print("\n" + "=" * 60)
    print("场景二：思考模型 ThinkingEvent")
    print("=" * 60)

    agent = create_agent(
        agent_name="assistant",
        session_id=SESSION_ID,
        prompt="你是一个严谨的助手。在给出最终回答之前，必须先用思考过程(thinking)详细分析问题、列出推理步骤，最后再给出结论。",
        model="gemini-3-pro-preview",
        max_loop=5,
        persist=PERSIST,
        middlewares=[LoggingMiddleware()],
    )

    event_count = 0
    thinking_buffer = ""
    text_buffer = ""

    async for event in agent.stream("为什么天空是蓝色的？"):
        event_count += 1
        label = _event_label(event)
        print(label)

        if isinstance(event, ThinkingEvent):
            thinking_buffer += event.content
        elif isinstance(event, TextEvent):
            text_buffer += event.content

    print(f"\n共收到 {event_count} 个事件")
    print(f"思考内容长度: {len(thinking_buffer)} 字符")
    print(f"最终文本长度: {len(text_buffer)} 字符")

    if thinking_buffer:
        print(f"思考内容预览: {thinking_buffer[:100]}...")
    else:
        print("注意：未收到 ThinkingEvent（当前模型可能不支持 thinking 输出）")


async def test_stream_with_tools():
    """场景三：工具调用，验证 ToolStartEvent / ToolEndEvent"""
    print("\n" + "=" * 60)
    print("场景三：工具调用流式输出")
    print("=" * 60)

    agent = create_agent(
        agent_name="assistant",
        session_id=SESSION_ID,
        prompt=(
            "你是一个全能助手。遇到数学问题时使用 calculate 工具，"
            "遇到天气问题时使用 get_weather 工具。"
        ),
        model="gemini-3-flash-preview",
        tools=ALL_TOOLS,
        max_loop=10,
        persist=PERSIST,
        middlewares=[LoggingMiddleware()],
    )

    event_count = 0
    tool_starts = 0
    tool_ends = 0

    async for event in agent.stream("请计算 (88 + 12) * 2，然后查询一下北京的天气"):
        event_count += 1
        print(_event_label(event))

        if isinstance(event, ToolStartEvent):
            tool_starts += 1
        elif isinstance(event, ToolEndEvent):
            tool_ends += 1

    print(f"\n共收到 {event_count} 个事件")
    print(f"ToolStartEvent: {tool_starts}, ToolEndEvent: {tool_ends}")


async def test_stream_multi_turn():
    """场景四：多轮对话，验证 session 恢复和历史加载"""
    print("\n" + "=" * 60)
    print("场景四：多轮对话 + session 恢复")
    print("=" * 60)

    agent = create_agent(
        agent_name="assistant",
        session_id=SESSION_ID,
        prompt="你是一个有帮助的助手，请结合对话历史回答问题。",
        model="gemini-3-flash-preview",
        tools=ALL_TOOLS,
        max_loop=10,
        persist=PERSIST,
        middlewares=[LoggingMiddleware()],
    )

    # 第一轮
    print("\n--- 第一轮: 问天气 ---")
    event_count = 0
    async for event in agent.stream("北京今天天气怎么样？请用 calculate 帮我算一下 50+30"):
        event_count += 1
        print(_event_label(event))
    print(f"第一轮共 {event_count} 个事件")

    # 第二轮（验证 session 历史）
    print("\n--- 第二轮: 引用上一轮结果 ---")
    event_count = 0
    async for event in agent.stream("我刚才问的是什么？北京的天气和计算结果分别是多少？"):
        event_count += 1
        print(_event_label(event))
    print(f"第二轮共 {event_count} 个事件")


async def main():
    print(" Agent.stream() 流式测试")
    print(f" session_id = {SESSION_ID}")
    print(f" 模型     = gemini-3-flash-preview")

    await clear_session()

    tests = [
        ("场景一：纯文本流", test_stream_simple),
        ("场景二：思考模型", test_stream_with_thinking),
        ("场景三：工具调用", test_stream_with_tools),
        ("场景四：多轮对话", test_stream_multi_turn),
    ]

    for label, fn in tests:
        try:
            await fn()
        except Exception as e:
            logger.exception(f"{label} 失败: {e}")

    print("\n" + "=" * 60)
    print(" 全部场景执行完毕")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
