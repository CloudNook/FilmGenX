#!/usr/bin/env python
"""
Agent 框架集成测试：Redis 持久化 + 长对话 + 工具调用

测试场景：
  同一个 session_id 跑三轮 run()，验证：
  1. 每轮工具调用正常执行
  2. 下一轮 run() 能加载上一轮的历史消息（_load_history）
  3. seq 在整个 session 内单调递增（不重置）
  4. Redis 中的消息数量随轮次累加
"""

import asyncio
import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.agent import create_agent
from app.core.agent.persist import RedisPersistStrategy
from app.core.middleware import LoggingMiddleware
from app.core.tools import ToolRegistry
from app.core.tools.examples import *  # noqa: F401, F403

ToolRegistry.discover("app.core.tools.examples")
ALL_TOOLS = [
    t for t in ToolRegistry.get_all_schemas()
    if t["name"] not in ("load_skill", "load_skill_lite")
]

SESSION_ID = "test_long_session_002"
PERSIST = RedisPersistStrategy()


def _print_messages(messages: list) -> None:
    """打印本轮所有消息，最后一条单独高亮。"""
    print(f"\n[Messages] ({len(messages)} 条)")
    for i, msg in enumerate(messages):
        role = msg.role.upper().ljust(9)
        content = msg.content.replace("\n", " ")
        if len(content) > 200:
            content = content[:200] + "..."
        suffix = f"  tool={msg.tool_name}" if msg.tool_name else ""
        print(f"  {i+1:>2}. [{role}] {content}{suffix}")

    last = messages[-1] if messages else None
    if last:
        print(f"\n[Final Answer]\n  {last.content}")


async def dump_redis_messages(label: str) -> None:
    """打印当前 Redis 中该 session 的所有消息。"""
    from app.utils import redis_client

    raw_list = await redis_client.lrange(f"agent:messages:{SESSION_ID}", 0, -1)
    msgs = [json.loads(item) for item in raw_list]
    print(f"\n{'─' * 60}")
    print(f"[Redis] {label}  ({len(msgs)} 条消息)")
    print(f"{'─' * 60}")
    for m in msgs:
        seq = m.get("seq", "?")
        role = m["role"].upper().ljust(9)
        content = m["content"][:120].replace("\n", " ")
        print(f"  seq={seq:>3}  {role}  {content}")


async def clear_session() -> None:
    """清除 Redis 中该 session 的历史，确保测试从干净状态开始。"""
    from app.utils import redis_client
    await redis_client.delete(f"agent:messages:{SESSION_ID}")
    print(f"[Setup] Cleared session {SESSION_ID}\n")


# ──────────────────────────────────────────────
# Round 1：数学计算 + 天气查询
# ──────────────────────────────────────────────
async def round1() -> None:
    print("\n" + "=" * 60)
    print("Round 1: 数学计算 + 天气查询")
    print("=" * 60)

    agent = create_agent(
        agent_name="assistant",
        session_id=SESSION_ID,
        prompt=(
            "你是一个全能助手，可以使用工具完成任务。\n"
            "需要计算时用 calculate，需要天气时用 get_weather。\n"
            "完成后直接给出结论。"
        ),
        model="gemini-3-flash-preview",
        tools=ALL_TOOLS,
        max_loop=10,
        persist=PERSIST,
        middlewares=[LoggingMiddleware()],
    )

    result = await agent.run(
        "请帮我做两件事：\n"
        "1. 计算 (128 + 72) * 3 的结果\n"
        "2. 查询北京的天气"
    )

    print(f"\n[Round 1 Result]")
    print(f"  finished   : {result.finished}")
    print(f"  loop_count : {result.loop_count}")
    print(f"  error      : {result.error}")
    _print_messages(result.messages)

    await dump_redis_messages("After Round 1")


# ──────────────────────────────────────────────
# Round 2：引用上轮结果 + 时间查询
# ──────────────────────────────────────────────
async def round2() -> None:
    print("\n" + "=" * 60)
    print("Round 2: 引用上轮结果 + 时间查询（验证历史加载）")
    print("=" * 60)

    agent = create_agent(
        agent_name="assistant",
        session_id=SESSION_ID,
        prompt=(
            "你是一个全能助手，可以使用工具完成任务。\n"
            "你记得之前对话的内容，请结合历史回答。\n"
            "需要时间时用 current_time，需要搜索时用 search_info。"
        ),
        model="gemini-3-flash-preview",
        tools=ALL_TOOLS,
        max_loop=10,
        persist=PERSIST,
        middlewares=[LoggingMiddleware()],
    )

    result = await agent.run(
        "根据我们上一轮对话，北京天气怎么样？\n"
        "另外帮我查一下现在的时间，以及搜索一下 Python 的相关信息。"
    )

    print(f"\n[Round 2 Result]")
    print(f"  finished   : {result.finished}")
    print(f"  loop_count : {result.loop_count}")
    print(f"  error      : {result.error}")
    _print_messages(result.messages)

    await dump_redis_messages("After Round 2")


# ──────────────────────────────────────────────
# Round 3：复杂多工具 + 验证 seq 连续性
# ──────────────────────────────────────────────
async def round3() -> None:
    print("\n" + "=" * 60)
    print("Round 3: 多工具综合 + seq 连续性验证")
    print("=" * 60)

    agent = create_agent(
        agent_name="assistant",
        session_id=SESSION_ID,
        prompt=(
            "你是一个全能助手。请依次完成用户要求的所有任务，"
            "每个任务都要调用对应工具，最后给出汇总。"
        ),
        model="gemini-3-flash-preview",
        tools=ALL_TOOLS,
        max_loop=15,
        persist=PERSIST,
        middlewares=[LoggingMiddleware()],
    )

    result = await agent.run(
        "请完成以下四项任务并汇总：\n"
        "1. 计算 999 / 3\n"
        "2. 查询上海的天气\n"
        "3. 获取当前时间\n"
        "4. 搜索 JavaScript 的相关信息"
    )

    print(f"\n[Round 3 Result]")
    print(f"  finished   : {result.finished}")
    print(f"  loop_count : {result.loop_count}")
    print(f"  error      : {result.error}")
    _print_messages(result.messages)

    await dump_redis_messages("After Round 3")

    # ── 验证 seq 单调递增 ──
    from app.utils import redis_client
    raw_list = await redis_client.lrange(f"agent:messages:{SESSION_ID}", 0, -1)
    raw = [json.loads(item) for item in raw_list]
    msgs = sorted(raw or [], key=lambda m: m.get("seq", 0))
    seqs = [m["seq"] for m in msgs]
    is_monotonic = all(seqs[i] + 1 == seqs[i + 1] for i in range(len(seqs) - 1))

    print(f"\n[seq 验证]")
    print(f"  总消息数   : {len(seqs)}")
    print(f"  seq 范围   : {seqs[0]} → {seqs[-1]}")
    print(f"  单调递增   : {'✓ PASS' if is_monotonic else '✗ FAIL  seq=' + str(seqs)}")


async def main() -> None:
    print("\n🚀 Agent Redis Persist Integration Test")
    print(f"   session_id = {SESSION_ID}")

    await clear_session()

    try:
        await round1()
    except Exception as e:
        logger.exception(f"Round 1 failed: {e}")

    try:
        await round2()
    except Exception as e:
        logger.exception(f"Round 2 failed: {e}")

    try:
        await round3()
    except Exception as e:
        logger.exception(f"Round 3 failed: {e}")

    print("\n" + "=" * 60)
    print("✅ All rounds completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
