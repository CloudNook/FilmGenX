#!/usr/bin/env python
"""
Agent 框架测试脚本。

测试 Agent 的基本功能：
- 工具注册与调用
- LLM 生成
- 循环执行
"""

import asyncio
import logging
import sys
import os

# 配置 logging 输出到终端
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.agent import create_agent
from app.core.agent.persist import RedisPersistStrategy
from app.core.middleware import LoggingMiddleware
from app.core.tools import ToolRegistry

# 导入所有测试工具（触发 @register_tool 装饰器）
from app.core.tools.examples import *  # noqa: F401, F403

# 手动注册测试工具（确保被发现）
ToolRegistry.discover("app.core.tools.examples")

# 过滤掉需要 db 的内置 Skill 工具，测试只需要 examples 里的工具
ALL_TOOLS = [t for t in ToolRegistry.get_all_schemas() if t["name"] not in ("load_skill", "load_skill_lite")]


async def test_basic_agent():
    """测试基本 Agent 功能。"""
    print("=" * 60)
    print("Test 1: Basic Agent with tools")
    print("=" * 60)

    agent = create_agent(
        agent_name="test_agent",
        prompt="""你是一个智能助手，可以调用工具来完成任务。
当你需要计算或获取信息时，请使用工具。
完成任务后，返回最终答案。""",
        model="gemini-3-flash-preview",
        tools=ALL_TOOLS,
        persist=RedisPersistStrategy(),
        middlewares=[LoggingMiddleware()],
    )

    result = await agent.run("请计算 (15 + 25) * 2 的结果", session_id="test_session_1")

    print(f"\n[Result]")
    print(f"  finished: {result.finished}")
    print(f"  loop_count: {result.loop_count}")
    print(f"  raw_output: {result.raw_output[:200] if result.raw_output else 'N/A'}")
    print(f"  schema_data: {result.schema_data}")
    print(f"  error: {result.error}")

    return result


async def test_weather_agent():
    """测试天气查询 Agent。"""
    print("\n" + "=" * 60)
    print("Test 2: Weather Query Agent")
    print("=" * 60)

    agent = create_agent(
        agent_name="weather_agent",
        prompt="""你是一个天气助手，根据用户询问的城市返回天气信息。
直接调用天气工具获取信息，然后返回给用户。""",
        model="gemini-3-flash-preview",
        tools=ALL_TOOLS,
        persist=RedisPersistStrategy(),
        middlewares=[LoggingMiddleware()],
    )

    result = await agent.run("北京今天的天气怎么样？", session_id="test_session_2")

    print(f"\n[Result]")
    print(f"  finished: {result.finished}")
    print(f"  loop_count: {result.loop_count}")
    print(f"  raw_output: {result.raw_output if result.raw_output else 'N/A'}")
    print(f"  error: {result.error}")

    return result


async def test_multi_tool_agent():
    """测试多工具 Agent。"""
    print("\n" + "=" * 60)
    print("Test 3: Multi-tool Agent")
    print("=" * 60)

    agent = create_agent(
        agent_name="assistant_agent",
        prompt="""你是一个全能助手，可以使用多种工具。
请根据用户需求选择合适的工具完成任务。

可用工具：
- calculate: 数学计算
- get_weather: 查询天气
- search_info: 搜索信息
- current_time: 获取当前时间

完成多个任务后，给出总结。""",
        model="gemini-3-flash-preview",
        tools=ALL_TOOLS,
        max_loop=10,
        persist=RedisPersistStrategy(),
        middlewares=[LoggingMiddleware()],
    )

    result = await agent.run(
        "请帮我完成以下任务：\n"
        "1. 计算 100 除以 25 再乘以 8\n"
        "2. 查询深圳的天气\n"
        "3. 告诉我现在的时间\n"
        "4. 搜索一下 Python 相关信息",
        session_id="test_session_3",
    )

    print(f"\n[Result]")
    print(f"  finished: {result.finished}")
    print(f"  loop_count: {result.loop_count}")
    print(f"  messages count: {len(result.messages)}")
    print(f"  raw_output: {result.raw_output if result.raw_output else 'N/A'}")
    print(f"  error: {result.error}")

    # 打印消息历史
    print(f"\n[Messages]")
    for i, msg in enumerate(result.messages):
        role = msg.role
        content = msg.content  if len(msg.content) > 100 else msg.content
        print(f"  {i+1}. [{role}] {content}")

    return result


async def test_schema_output():
    """测试结构化输出。"""
    print("\n" + "=" * 60)
    print("Test 4: Schema Output")
    print("=" * 60)

    from pydantic import BaseModel

    class MathResult(BaseModel):
        expression: str
        result: float
        steps: list[str]
        is_correct: bool

    agent = create_agent(
        agent_name="math_agent",
        prompt="""你是一个数学老师。计算数学表达式并返回结构化结果。
计算完成后，直接输出 JSON 结果。""",
        model="gemini-3-flash-preview",
        tools=ALL_TOOLS,
        response_schema=MathResult,
        persist=RedisPersistStrategy(),
        middlewares=[LoggingMiddleware()],
    )

    result = await agent.run("请计算 125 / 5，并给出计算步骤", session_id="test_session_4")

    print(f"\n[Result]")
    print(f"  finished: {result.finished}")
    print(f"  loop_count: {result.loop_count}")
    print(f"  schema_data: {result.schema_data}")
    print(f"  raw_output: {result.raw_output if result.raw_output else 'N/A'}")
    print(f"  error: {result.error}")

    return result


async def main():
    """运行所有测试。"""
    print("\n🚀 Agent Framework Test Suite")
    print("=" * 60)

    try:
        await test_basic_agent()
    except Exception as e:
        print(f"Test 1 failed: {e}")

    try:
        await test_weather_agent()
    except Exception as e:
        print(f"Test 2 failed: {e}")

    try:
        await test_multi_tool_agent()
    except Exception as e:
        print(f"Test 3 failed: {e}")

    try:
        await test_schema_output()
    except Exception as e:
        print(f"Test 4 failed: {e}")

    print("\n" + "=" * 60)
    print("✅ All tests completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
