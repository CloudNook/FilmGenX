"""
Agent 框架核心单元测试。

覆盖范围：
  - GeminiAdapter._normalize_finish_reason()
  - AgentLoop._check_finished()
  - AgentLoop.run() — mock LLM，测试 think→act→observe 完整循环
  - AgentLoop.stream_run() — mock LLM，测试 TextEvent / ToolStartEvent / ToolEndEvent / DoneEvent
  - ToolRegistry 注册 & schema 推断
  - MiddlewareChain before/after / stream 钩子顺序
  - LLMAdapter.generate() / generate_stream() 委托给 provider

所有测试均不依赖外部服务（LLM / Redis / DB）。
"""

import asyncio
import json
import sys
import types as python_types
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ──────────────────────────────────────────────────────────────────
# 路径设置：让 pytest 能找到 app 包
# ──────────────────────────────────────────────────────────────────
BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.agent.base import (
    AgentConfig,
    AgentResult,
    DoneEvent,
    ErrorEvent,
    LLMResponse,
    StructuredToolCall,
    TextEvent,
    ThinkingEvent,
    ToolCall,
    ToolEndEvent,
    ToolResult,
    ToolStartEvent,
)
from app.core.agent.agent import Agent
from app.core.agent.llm import LLMAdapter
from app.core.agent.loop import AgentLoop
from app.core.agent.persist.db_strategy import DBPersistStrategy
from app.core.middleware.chain import AgentMiddleware, MiddlewareChain, MiddlewareContext
from app.core.middleware.builtin import (
    FinalSchemaResponseMiddleware,
)
from app.core.tools.registry import ToolFunc, ToolRegistry, register_tool


# ═══════════════════════════════════════════════════════════════════
# 1. GeminiAdapter._normalize_finish_reason
# ═══════════════════════════════════════════════════════════════════

class TestGeminiNormalizeFinishReason:
    """finish_reason 归一化在适配层完成，loop 只需比较 'stop'。"""

    @pytest.fixture(autouse=True)
    def adapter(self):
        # 避免真实初始化（需要 API key / google-genai）
        from app.core.adapter.gemini import GeminiAdapter
        self.normalize = GeminiAdapter._normalize_finish_reason

    def test_none_returns_empty(self):
        assert self.normalize(None) == ""

    def test_enum_stop(self):
        """模拟 Gemini FinishReason.STOP 枚举（有 .name = 'STOP'）"""
        mock = MagicMock()
        mock.name = "STOP"
        assert self.normalize(mock) == "stop"

    def test_enum_max_tokens(self):
        mock = MagicMock()
        mock.name = "MAX_TOKENS"
        assert self.normalize(mock) == "length"

    def test_enum_safety(self):
        mock = MagicMock()
        mock.name = "SAFETY"
        assert self.normalize(mock) == "content_filter"

    def test_string_1_maps_to_stop(self):
        """Gemini 有时用 '1' 表示 STOP"""
        mock = MagicMock()
        mock.name = "1"
        assert self.normalize(mock) == "stop"

    def test_unknown_lowercased(self):
        mock = MagicMock()
        mock.name = "OTHER_REASON"
        assert self.normalize(mock) == "other_reason"

    @pytest.mark.asyncio
    async def test_generate_with_empty_candidates_returns_empty_response(self):
        from app.core.adapter.gemini import GeminiAdapter

        fake_types = python_types.SimpleNamespace(
            GenerateContentConfig=lambda **kwargs: python_types.SimpleNamespace(**kwargs),
            ThinkingConfig=lambda **kwargs: python_types.SimpleNamespace(**kwargs),
        )
        fake_google = python_types.ModuleType("google")
        fake_genai = python_types.ModuleType("google.genai")
        fake_genai.types = fake_types
        fake_google.genai = fake_genai

        adapter = object.__new__(GeminiAdapter)
        adapter._client = python_types.SimpleNamespace(
            aio=python_types.SimpleNamespace(
                models=python_types.SimpleNamespace(
                    generate_content=AsyncMock(return_value=python_types.SimpleNamespace(
                        candidates=[],
                        usage_metadata=None,
                    ))
                )
            )
        )

        with patch.dict(sys.modules, {"google": fake_google, "google.genai": fake_genai}):
            response = await adapter.generate(messages=[{"role": "user", "content": "hi"}], model="gemini-3-pro-preview")

        assert response.content == ""
        assert response.thinking == ""
        assert response.tool_calls == []
        assert response.finish_reason == ""


# ═══════════════════════════════════════════════════════════════════
# 2. AgentLoop._check_finished
# ═══════════════════════════════════════════════════════════════════

class TestCheckFinished:
    @pytest.fixture
    def loop(self):
        config = AgentConfig(agent_name="test", prompt="")
        llm = MagicMock(spec=LLMAdapter)
        return AgentLoop(config=config, llm=llm)

    def _response(self, finish_reason: Optional[str]) -> LLMResponse:
        return LLMResponse(content="hello", finish_reason=finish_reason)

    def test_stop_finishes(self, loop):
        resp = self._response("stop")
        finished = loop._check_finished(resp, "hello")
        assert finished is True

    def test_none_does_not_finish(self, loop):
        resp = self._response(None)
        finished = loop._check_finished(resp, "hello")
        assert finished is False

    def test_tool_calls_does_not_finish(self, loop):
        resp = self._response("tool_calls")
        finished = loop._check_finished(resp, "")
        assert finished is False

    def test_stop_signal_in_text(self, loop):
        resp = self._response(None)
        finished = loop._check_finished(resp, "<stop>")
        assert finished is True

    def test_non_stop_finish_reason(self, loop):
        resp = self._response("length")
        finished = loop._check_finished(resp, "some text")
        assert finished is False

    def test_gemini_finish_reason_dot_stop_no_longer_accepted(self, loop):
        """适配层归一化后，loop 不再接受 'finish_reason.stop'"""
        resp = self._response("finish_reason.stop")
        finished = loop._check_finished(resp, "some text")
        assert finished is False  # 不再是有效停止信号

# ═══════════════════════════════════════════════════════════════════
# 3. AgentLoop.run() — 纯文本响应（无工具调用）
# ═══════════════════════════════════════════════════════════════════

class TestAgentLoopRun:
    """使用 mock LLM 测试 run() 循环逻辑，不依赖任何外部服务。"""

    def _make_loop(self, responses: List[LLMResponse]) -> AgentLoop:
        config = AgentConfig(agent_name="test", prompt="You are helpful.", max_loop=10)
        llm = MagicMock(spec=LLMAdapter)
        llm.generate = AsyncMock(side_effect=responses)
        llm.parse_json = MagicMock(return_value=None)
        return AgentLoop(config=config, llm=llm)

    @pytest.mark.asyncio
    async def test_single_turn_finishes(self):
        loop = self._make_loop([
            LLMResponse(content="我是助手", finish_reason="stop"),
        ])
        result = await loop.run("你好")
        assert result.finished is True
        assert result.loop_count == 1
        assert result.raw_output == "我是助手"

    @pytest.mark.asyncio
    async def test_thinking_stored_in_message(self):
        """thinking 模型响应：thinking 和 content 均写入 assistant 消息"""
        loop = self._make_loop([
            LLMResponse(
                content="这是最终回答",
                thinking="我先分析一下用户的问题...",
                finish_reason="stop",
            ),
        ])
        result = await loop.run("问题")
        assert result.finished is True
        assistant_msgs = [m for m in result.messages if m.role == "assistant"]
        assert len(assistant_msgs) == 1
        assert assistant_msgs[0].thinking == "我先分析一下用户的问题..."
        assert assistant_msgs[0].content == "这是最终回答"

    @pytest.mark.asyncio
    async def test_max_loop_exceeded(self):
        """LLM 始终不返回 stop → 达到 max_loop 退出"""
        config = AgentConfig(agent_name="test", prompt="", max_loop=3)
        llm = MagicMock(spec=LLMAdapter)
        llm.generate = AsyncMock(return_value=LLMResponse(content="思考中", finish_reason=None))
        llm.parse_json = MagicMock(return_value=None)
        loop = AgentLoop(config=config, llm=llm)

        result = await loop.run("问题")
        assert result.finished is False
        assert result.loop_count == 3
        assert "Max loop" in result.error

    @pytest.mark.asyncio
    async def test_tool_call_then_stop(self):
        """第一轮 tool_call，第二轮 stop"""
        tool_call = StructuredToolCall(id="tc1", name="calculate", arguments={"expression": "1+1"})
        responses = [
            LLMResponse(content="", tool_calls=[tool_call], finish_reason="tool_calls"),
            LLMResponse(content="结果是2", finish_reason="stop"),
        ]
        config = AgentConfig(agent_name="test", prompt="", max_loop=10)
        llm = MagicMock(spec=LLMAdapter)
        llm.generate = AsyncMock(side_effect=responses)
        llm.parse_json = MagicMock(return_value=None)

        tool_executor = MagicMock()
        tool_executor.execute_all = AsyncMock(return_value=[
            ToolResult(tool_call_id="tc1", tool_name="calculate", result="2", is_error=False)
        ])

        loop = AgentLoop(config=config, llm=llm, tool_executor=tool_executor)
        result = await loop.run("1+1等于几")

        assert result.finished is True
        assert result.loop_count == 2
        assert result.raw_output == "结果是2"
        # 消息历史：user + assistant(tool_call) + tool + assistant(final)
        roles = [m.role for m in result.messages]
        assert roles == ["user", "assistant", "tool", "assistant"]

    @pytest.mark.asyncio
    async def test_exception_sets_error(self):
        config = AgentConfig(agent_name="test", prompt="", max_loop=5)
        llm = MagicMock(spec=LLMAdapter)
        llm.generate = AsyncMock(side_effect=RuntimeError("API timeout"))
        loop = AgentLoop(config=config, llm=llm)

        result = await loop.run("问题")
        assert result.finished is False
        assert "API timeout" in result.error

    @pytest.mark.asyncio
    async def test_persist_called_on_each_message(self):
        """有 persist 时，每条消息都触发 append_message"""
        persist = MagicMock()
        persist.load_messages = AsyncMock(return_value=[])
        persist.append_message = AsyncMock()
        persist.flush = AsyncMock()

        tool_call = StructuredToolCall(id="tc1", name="get_weather", arguments={"city": "北京"})
        responses = [
            LLMResponse(content="", tool_calls=[tool_call], finish_reason="tool_calls"),
            LLMResponse(content="北京晴天", finish_reason="stop"),
        ]
        config = AgentConfig(agent_name="test", prompt="", max_loop=10)
        llm = MagicMock(spec=LLMAdapter)
        llm.generate = AsyncMock(side_effect=responses)
        llm.parse_json = MagicMock(return_value=None)

        tool_executor = MagicMock()
        tool_executor.execute_all = AsyncMock(return_value=[
            ToolResult(tool_call_id="tc1", tool_name="get_weather", result="晴，25°C", is_error=False)
        ])

        loop = AgentLoop(
            config=config, llm=llm,
            tool_executor=tool_executor,
            persist=persist, session_id="s1", request_id="r1",
        )
        await loop.run("北京天气")

        # user + assistant(loop1) + tool + assistant(loop2) = 4 条
        assert persist.append_message.call_count == 4

    @pytest.mark.asyncio
    async def test_persist_preserves_tool_context_for_history_replay(self):
        persist = MagicMock()
        persist.load_messages = AsyncMock(return_value=[])
        persist.append_message = AsyncMock()
        persist.flush = AsyncMock()

        tool_call = StructuredToolCall(
            id="tc1",
            name="calculate",
            arguments={"expression": "1+1"},
        )
        responses = [
            LLMResponse(content="", tool_calls=[tool_call], finish_reason="tool_calls"),
            LLMResponse(content="结果是2", finish_reason="stop"),
        ]
        config = AgentConfig(agent_name="test", prompt="", max_loop=10)
        llm = MagicMock(spec=LLMAdapter)
        llm.generate = AsyncMock(side_effect=responses)
        llm.parse_json = MagicMock(return_value=None)

        tool_executor = MagicMock()
        tool_executor.execute_all = AsyncMock(return_value=[
            ToolResult(tool_call_id="tc1", tool_name="calculate", result="2", is_error=False)
        ])

        loop = AgentLoop(
            config=config,
            llm=llm,
            tool_executor=tool_executor,
            persist=persist,
            session_id="s1",
            request_id="r1",
        )
        await loop.run("1+1等于几")

        persisted = [call.kwargs for call in persist.append_message.await_args_list]
        assistant_call = persisted[1]
        tool_call_msg = persisted[2]

        assert assistant_call["metadata"]["tool_calls"] == [
            {
                "id": "tc1",
                "name": "calculate",
                "arguments": {"expression": "1+1"},
            }
        ]
        assert tool_call_msg["content"] == "2"

        replay_persist = MagicMock()
        replay_persist.load_messages = AsyncMock(return_value=[
            {
                "role": msg["role"],
                "content": msg["content"],
                "tool_call_id": msg.get("tool_call_id"),
                "tool_name": msg.get("tool_name"),
                "metadata": msg.get("metadata") or {},
                "seq": msg["seq"],
            }
            for msg in persisted
        ])

        replay = AgentLoop(config=config, llm=llm, persist=replay_persist, session_id="s1")
        await replay._load_history()

        assert replay.messages[1]["tool_calls"] == [
            {
                "id": "tc1",
                "name": "calculate",
                "arguments": {"expression": "1+1"},
            }
        ]
        assert replay.messages[2]["content"] == "2"


# ═══════════════════════════════════════════════════════════════════
# 4. AgentLoop.stream_run() — 流式事件序列
# ═══════════════════════════════════════════════════════════════════

class TestAgentLoopStreamRun:
    """验证 stream_run() 产出正确的事件类型和顺序。"""

    async def _collect(self, gen) -> list:
        events = []
        async for e in gen:
            events.append(e)
        return events

    def _make_stream(self, chunks: List[LLMResponse]):
        """构造一个 mock generate_stream，逐 chunk yield。"""
        async def _gen(*args, **kwargs) -> AsyncGenerator[LLMResponse, None]:
            for chunk in chunks:
                yield chunk
        return _gen

    @pytest.mark.asyncio
    async def test_text_then_done(self):
        chunks = [
            LLMResponse(content="你好", finish_reason=None),
            LLMResponse(content="世界", finish_reason=None),
            LLMResponse(content="", finish_reason="stop"),  # 终止 chunk
        ]
        config = AgentConfig(agent_name="test", prompt="", max_loop=5)
        llm = MagicMock(spec=LLMAdapter)
        llm.generate_stream = self._make_stream(chunks)
        llm.parse_json = MagicMock(return_value=None)

        loop = AgentLoop(config=config, llm=llm)
        events = await self._collect(loop.stream_run("hi"))

        types = [e.type for e in events]
        assert types == ["text", "text", "done"]
        assert events[0].content == "你好"
        assert events[1].content == "世界"
        assert isinstance(events[-1], DoneEvent)
        assert events[-1].result.finished is True

    @pytest.mark.asyncio
    async def test_thinking_then_text_then_done(self):
        """thinking 模型：先收到思考内容，再收到最终文本，正常结束"""
        chunks = [
            LLMResponse(thinking="我先思考一下...", finish_reason=None),
            LLMResponse(content="这是回答", finish_reason=None),
            LLMResponse(content="", finish_reason="stop"),
        ]
        config = AgentConfig(agent_name="test", prompt="", max_loop=5)
        llm = MagicMock(spec=LLMAdapter)
        llm.generate_stream = self._make_stream(chunks)
        llm.parse_json = MagicMock(return_value=None)

        loop = AgentLoop(config=config, llm=llm)
        events = await self._collect(loop.stream_run("问题"))

        types = [e.type for e in events]
        assert types == ["thinking", "text", "done"]
        assert isinstance(events[0], ThinkingEvent)
        assert events[0].content == "我先思考一下..."
        assert events[1].content == "这是回答"

        # 消息历史里 assistant 消息应包含 thinking 和 content
        done: DoneEvent = events[-1]
        assistant_msgs = [m for m in done.result.messages if m.role == "assistant"]
        assert len(assistant_msgs) == 1
        assert assistant_msgs[0].thinking == "我先思考一下..."
        assert assistant_msgs[0].content == "这是回答"

    @pytest.mark.asyncio
    async def test_tool_call_events(self):
        """tool_call 流：ToolStartEvent → ToolEndEvent → 下一轮文本 → DoneEvent"""
        tool_call = StructuredToolCall(id="tc1", name="calculate", arguments={"expression": "2*3"})
        call1_chunks = [
            LLMResponse(content="", tool_calls=[tool_call], finish_reason="tool_calls"),
        ]
        call2_chunks = [
            LLMResponse(content="结果是", finish_reason=None),
            LLMResponse(content="6", finish_reason=None),
            LLMResponse(content="", finish_reason="stop"),
        ]

        call_count = 0

        async def _gen(*args, **kwargs):
            nonlocal call_count
            chunks = call1_chunks if call_count == 0 else call2_chunks
            call_count += 1
            for c in chunks:
                yield c

        config = AgentConfig(agent_name="test", prompt="", max_loop=5)
        llm = MagicMock(spec=LLMAdapter)
        llm.generate_stream = _gen
        llm.parse_json = MagicMock(return_value=None)

        tool_executor = MagicMock()
        tool_executor.execute_all = AsyncMock(return_value=[
            ToolResult(tool_call_id="tc1", tool_name="calculate", result="6", is_error=False)
        ])

        loop = AgentLoop(config=config, llm=llm, tool_executor=tool_executor)
        events = await self._collect(loop.stream_run("2乘以3"))

        types = [e.type for e in events]
        assert types == ["tool_start", "tool_end", "text", "text", "done"]
        assert isinstance(events[0], ToolStartEvent)
        assert events[0].tool_name == "calculate"
        assert isinstance(events[1], ToolEndEvent)
        assert events[1].result == "6"

    @pytest.mark.asyncio
    async def test_error_event_on_exception(self):
        async def _gen(*args, **kwargs):
            raise RuntimeError("stream broken")
            yield  # 让 Python 识别为 async generator

        config = AgentConfig(agent_name="test", prompt="", max_loop=5)
        llm = MagicMock(spec=LLMAdapter)
        llm.generate_stream = _gen
        loop = AgentLoop(config=config, llm=llm)

        events = await self._collect(loop.stream_run("hi"))
        types = [e.type for e in events]
        assert "error" in types
        assert "done" in types
        error_event = next(e for e in events if e.type == "error")
        assert "stream broken" in error_event.error

    @pytest.mark.asyncio
    async def test_max_loop_yields_error_done(self):
        """每轮以 finish_reason='length'（非 stop）结束，最终触发 max_loop 退出"""
        async def _gen(*args, **kwargs):
            yield LLMResponse(content="思考中", finish_reason=None)
            # 终止 chunk：有 finish_reason 但不是 stop，loop 不会结束而是 continue
            yield LLMResponse(content="", finish_reason="length")

        config = AgentConfig(agent_name="test", prompt="", max_loop=2)
        llm = MagicMock(spec=LLMAdapter)
        llm.generate_stream = _gen
        llm.parse_json = MagicMock(return_value=None)
        loop = AgentLoop(config=config, llm=llm)

        events = await self._collect(loop.stream_run("hi"))
        types = [e.type for e in events]
        assert "error" in types
        assert types[-1] == "done"
        error_event = next(e for e in events if e.type == "error")
        assert "Max loop" in error_event.error


# ═══════════════════════════════════════════════════════════════════
# 5. ToolRegistry
# ═══════════════════════════════════════════════════════════════════

class TestToolRegistry:
    def setup_method(self):
        # 每个测试前清空注册表，避免跨测试污染
        ToolRegistry._tools.clear()

    def test_register_and_get(self):
        @register_tool(name="my_tool", description="test tool")
        def my_tool(x: int, y: str) -> str:
            return f"{x}{y}"

        tf = ToolRegistry.get("my_tool")
        assert tf is not None
        assert tf.name == "my_tool"

    def test_schema_inference_types(self):
        @register_tool(name="typed_tool")
        def typed_tool(a: int, b: float, c: bool, d: str):
            pass

        schema = ToolRegistry.get("typed_tool").parameters_schema
        props = schema["properties"]
        assert props["a"]["type"] == "integer"
        assert props["b"]["type"] == "number"
        assert props["c"]["type"] == "boolean"
        assert props["d"]["type"] == "string"

    def test_schema_required_vs_optional(self):
        @register_tool(name="req_tool")
        def req_tool(required_arg: str, optional_arg: str = "default"):
            pass

        schema = ToolRegistry.get("req_tool").parameters_schema
        assert "required_arg" in schema["required"]
        assert "optional_arg" not in schema["required"]

    def test_schema_inference_typing_list_and_optional(self):
        @register_tool(name="typing_tool")
        def typing_tool(skill_names: List[str], fields: Optional[List[str]] = None):
            pass

        schema = ToolRegistry.get("typing_tool").parameters_schema
        props = schema["properties"]
        assert props["skill_names"]["type"] == "array"
        assert props["fields"]["type"] == "array"
        assert "skill_names" in schema["required"]
        assert "fields" not in schema["required"]

    def test_db_param_excluded_from_schema(self):
        """框架注入参数 db 不暴露给 LLM"""
        @register_tool(name="db_tool")
        def db_tool(query: str, db=None):
            pass

        schema = ToolRegistry.get("db_tool").parameters_schema
        assert "db" not in schema["properties"]
        assert "query" in schema["properties"]

    def test_get_all_schemas(self):
        @register_tool(name="tool_a")
        def tool_a(x: str): pass

        @register_tool(name="tool_b")
        def tool_b(y: int): pass

        schemas = ToolRegistry.get_all_schemas()
        names = [s["name"] for s in schemas]
        assert "tool_a" in names
        assert "tool_b" in names

    def test_overwrite_warning(self, caplog):
        import logging
        @register_tool(name="dup_tool")
        def tool_v1(x: str): pass

        with caplog.at_level(logging.WARNING):
            @register_tool(name="dup_tool")
            def tool_v2(x: str): pass

        assert "already registered" in caplog.text

    @pytest.mark.asyncio
    async def test_execute_sync_tool(self):
        @register_tool(name="sync_tool")
        def sync_tool(x: int) -> str:
            return str(x * 2)

        tf = ToolRegistry.get("sync_tool")
        result = await tf.execute(x=5)
        assert result == "10"

    @pytest.mark.asyncio
    async def test_execute_async_tool(self):
        @register_tool(name="async_tool")
        async def async_tool(x: int) -> str:
            return str(x + 1)

        tf = ToolRegistry.get("async_tool")
        result = await tf.execute(x=9)
        assert result == "10"


# ═══════════════════════════════════════════════════════════════════
# 6. MiddlewareChain
# ═══════════════════════════════════════════════════════════════════

class RecordingMiddleware(AgentMiddleware):
    """记录所有钩子调用顺序，用于验证执行顺序。"""
    name = "recorder"

    def __init__(self, label: str, log: list):
        self.label = label
        self.log = log

    async def before(self, ctx): self.log.append(f"{self.label}:before")
    async def after(self, ctx): self.log.append(f"{self.label}:after")
    async def on_loop_start(self, ctx): self.log.append(f"{self.label}:loop_start")
    async def on_loop_end(self, ctx): self.log.append(f"{self.label}:loop_end")


def _make_ctx() -> MiddlewareContext:
    return MiddlewareContext(
        session_id="s", request_id="r",
        agent_name="test", agent_id="a",
        initial_input="hi",
    )


class TestMiddlewareChain:
    @pytest.mark.asyncio
    async def test_run_onion_order(self):
        """before 正序，after 逆序（洋葱模型）"""
        log = []
        m1 = RecordingMiddleware("m1", log)
        m2 = RecordingMiddleware("m2", log)
        chain = MiddlewareChain([m1, m2])

        async def handler():
            log.append("handler")
            return "result"

        result = await chain.run(_make_ctx(), handler)
        assert result == "result"
        assert log == ["m1:before", "m2:before", "handler", "m2:after", "m1:after"]

    @pytest.mark.asyncio
    async def test_run_after_called_even_on_exception(self):
        log = []
        m1 = RecordingMiddleware("m1", log)
        chain = MiddlewareChain([m1])

        async def failing_handler():
            raise ValueError("oops")

        with pytest.raises(ValueError):
            await chain.run(_make_ctx(), failing_handler)

        assert "m1:before" in log
        assert "m1:after" in log

    @pytest.mark.asyncio
    async def test_stream_before_after_called(self):
        log = []
        m1 = RecordingMiddleware("m1", log)
        chain = MiddlewareChain([m1])

        async def gen():
            log.append("yield1")
            yield "a"
            log.append("yield2")
            yield "b"

        collected = []
        async for item in chain.stream(_make_ctx(), gen()):
            collected.append(item)

        assert collected == ["a", "b"]
        assert log[0] == "m1:before"
        assert log[-1] == "m1:after"
        assert "yield1" in log
        assert "yield2" in log

    @pytest.mark.asyncio
    async def test_stream_after_called_on_exception(self):
        """流异常时，after 仍然保证执行"""
        log = []
        m1 = RecordingMiddleware("m1", log)
        chain = MiddlewareChain([m1])

        async def broken_gen():
            yield "ok"
            raise RuntimeError("stream error")

        with pytest.raises(RuntimeError):
            async for _ in chain.stream(_make_ctx(), broken_gen()):
                pass

        assert "m1:before" in log
        assert "m1:after" in log

    @pytest.mark.asyncio
    async def test_on_loop_start_end_order(self):
        log = []
        m1 = RecordingMiddleware("m1", log)
        m2 = RecordingMiddleware("m2", log)
        chain = MiddlewareChain([m1, m2])

        await chain.on_loop_start(_make_ctx())
        await chain.on_loop_end(_make_ctx())

        assert log == ["m1:loop_start", "m2:loop_start", "m1:loop_end", "m2:loop_end"]

    @pytest.mark.asyncio
    async def test_empty_chain_runs_handler(self):
        chain = MiddlewareChain([])

        async def handler():
            return 42

        result = await chain.run(_make_ctx(), handler)
        assert result == 42

    @pytest.mark.asyncio
    async def test_finalize_result_runs_in_order(self):
        log = []

        class FinalizingMiddleware(AgentMiddleware):
            def __init__(self, label: str):
                self.label = label
                self.name = label

            async def finalize_result(self, ctx, result):
                log.append(f"{self.label}:finalize")
                result.raw_output = f"{result.raw_output}|{self.label}"
                return result

        chain = MiddlewareChain([FinalizingMiddleware("m1"), FinalizingMiddleware("m2")])
        result = AgentResult(agent_name="test", raw_output="base")

        finalized = await chain.finalize_result(_make_ctx(), result)

        assert finalized.raw_output == "base|m1|m2"
        assert log == ["m1:finalize", "m2:finalize"]


# ═══════════════════════════════════════════════════════════════════
# 7. Agent + Middleware 集成
# ═══════════════════════════════════════════════════════════════════

class InspectFinalizeMiddleware(AgentMiddleware):
    name = "inspect_finalize"

    def __init__(self, log: list[str]):
        self.log = log

    async def finalize_result(self, ctx, result):
        self.log.append("finalize")
        result.raw_output = f"{result.raw_output}!"
        return result

    async def after(self, ctx):
        self.log.append(f"after:{ctx.result.raw_output}")


class TestAgentMiddlewareIntegration:
    @pytest.mark.asyncio
    async def test_run_applies_finalize_result_before_after(self):
        log: list[str] = []
        llm = MagicMock(spec=LLMAdapter)
        llm.generate = AsyncMock(return_value=LLMResponse(content="hello", finish_reason="stop"))

        agent = Agent(
            config=AgentConfig(agent_name="test", prompt=""),
            session_id="s1",
            middlewares=[InspectFinalizeMiddleware(log)],
        )
        agent._llm = llm
        agent._tool_executor = MagicMock()

        result = await agent.run("hi")

        assert result.raw_output == "hello!"
        assert log == ["finalize", "after:hello!"]

    @pytest.mark.asyncio
    async def test_stream_applies_finalize_result_before_done_event(self):
        log: list[str] = []

        async def _stream(*args, **kwargs):
            yield LLMResponse(content="hello", finish_reason=None)
            yield LLMResponse(content="", finish_reason="stop")

        llm = MagicMock(spec=LLMAdapter)
        llm.generate_stream = _stream

        agent = Agent(
            config=AgentConfig(agent_name="test", prompt=""),
            session_id="s1",
            middlewares=[InspectFinalizeMiddleware(log)],
        )
        agent._llm = llm
        agent._tool_executor = MagicMock()

        events = []
        async for event in agent.stream("hi"):
            events.append(event)

        done = events[-1]
        assert isinstance(done, DoneEvent)
        assert done.result.raw_output == "hello!"
        assert log == ["finalize", "after:hello!"]


class TestBuiltinMiddlewares:
    @pytest.mark.asyncio
    async def test_final_schema_middleware_formats_result_and_merges_usage(self):
        schema = {
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
        }
        llm = MagicMock(spec=LLMAdapter)
        llm.generate = AsyncMock(side_effect=[
            LLMResponse(
                content="天空是蓝色的，因为大气对短波长光散射更强。",
                finish_reason="stop",
                usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            ),
            LLMResponse(
                content='{"answer":"瑞利散射"}',
                finish_reason="stop",
                usage={"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            ),
        ])
        llm.parse_json = MagicMock(return_value={"answer": "瑞利散射"})

        agent = Agent(
            config=AgentConfig(agent_name="test", prompt=""),
            session_id="s1",
            middlewares=[FinalSchemaResponseMiddleware(schema)],
        )
        agent._llm = llm
        agent._tool_executor = MagicMock()

        result = await agent.run("为什么天空是蓝色的？")

        assert result.finished is True
        assert result.raw_output == "天空是蓝色的，因为大气对短波长光散射更强。"
        assert result.schema_data == {"answer": "瑞利散射"}
        assert result.schema_error is None
        assert result.usage == {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}

        second_call = llm.generate.await_args_list[1].kwargs
        assert second_call["response_schema"] == schema
        assert second_call["tools"] == []

    @pytest.mark.asyncio
    async def test_final_schema_middleware_sets_schema_error_on_parse_failure(self):
        schema = {
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
        }
        llm = MagicMock(spec=LLMAdapter)
        llm.generate = AsyncMock(side_effect=[
            LLMResponse(content="自由文本答案", finish_reason="stop"),
            LLMResponse(content="not-json", finish_reason="stop"),
        ])
        llm.parse_json = MagicMock(return_value=None)

        agent = Agent(
            config=AgentConfig(agent_name="test", prompt=""),
            session_id="s1",
            middlewares=[FinalSchemaResponseMiddleware(schema)],
        )
        agent._llm = llm
        agent._tool_executor = MagicMock()

        result = await agent.run("问题")

        assert result.finished is True
        assert result.schema_data is None
        assert "Failed to parse" in result.schema_error

    @pytest.mark.asyncio
    async def test_final_schema_middleware_applies_before_stream_done_event(self):
        schema = {
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
        }

        async def _stream(*args, **kwargs):
            yield LLMResponse(content="先给一段自由文本", finish_reason=None)
            yield LLMResponse(
                content="",
                finish_reason="stop",
                usage={"prompt_tokens": 6, "completion_tokens": 4, "total_tokens": 10},
            )

        llm = MagicMock(spec=LLMAdapter)
        llm.generate_stream = _stream
        llm.generate = AsyncMock(return_value=LLMResponse(
            content='{"answer":"结构化结论"}',
            finish_reason="stop",
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        ))
        llm.parse_json = MagicMock(return_value={"answer": "结构化结论"})

        agent = Agent(
            config=AgentConfig(agent_name="test", prompt=""),
            session_id="s1",
            middlewares=[FinalSchemaResponseMiddleware(schema)],
        )
        agent._llm = llm
        agent._tool_executor = MagicMock()

        events = []
        async for event in agent.stream("问题"):
            events.append(event)

        done = events[-1]
        assert isinstance(done, DoneEvent)
        assert done.result.schema_data == {"answer": "结构化结论"}
        assert done.result.usage == {"prompt_tokens": 7, "completion_tokens": 5, "total_tokens": 12}



# ═══════════════════════════════════════════════════════════════════
# 8. LLMAdapter — provider 委托
# ═══════════════════════════════════════════════════════════════════

class TestLLMAdapter:
    """验证 LLMAdapter 正确委托给 provider，不做额外处理。"""

    def _make_adapter(self, provider_mock) -> LLMAdapter:
        config = AgentConfig(agent_name="test", model="gemini-3-flash-preview")
        with patch("app.core.agent.llm.get_adapter", return_value=provider_mock):
            return LLMAdapter(config=config, tools=[])

    @pytest.mark.asyncio
    async def test_generate_delegates_to_provider(self):
        expected = LLMResponse(content="hello", finish_reason="stop")
        provider = MagicMock()
        provider.generate = AsyncMock(return_value=expected)
        provider.to_tool_schema = MagicMock(return_value=[])

        adapter = self._make_adapter(provider)
        result = await adapter.generate(messages=[{"role": "user", "content": "hi"}])

        assert result is expected
        provider.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_supports_one_off_response_schema(self):
        expected = LLMResponse(content='{"ok": true}', finish_reason="stop")
        provider = MagicMock()
        provider.generate = AsyncMock(return_value=expected)
        provider.to_tool_schema = MagicMock(return_value=[])

        adapter = self._make_adapter(provider)
        schema = {"type": "object"}
        result = await adapter.generate(
            messages=[{"role": "user", "content": "hi"}],
            response_schema=schema,
            tools=[],
        )

        assert result is expected
        call_kwargs = provider.generate.await_args.kwargs
        assert call_kwargs["response_schema"] == schema
        assert call_kwargs["tools"] == []

    @pytest.mark.asyncio
    async def test_generate_stream_delegates_to_provider(self):
        chunks = [
            LLMResponse(content="a", finish_reason=None),
            LLMResponse(content="b", finish_reason="stop"),
        ]

        async def _stream(*args, **kwargs):
            for c in chunks:
                yield c

        provider = MagicMock()
        provider.generate_stream = _stream
        provider.to_tool_schema = MagicMock(return_value=[])

        adapter = self._make_adapter(provider)
        received = []
        async for chunk in adapter.generate_stream(messages=[{"role": "user", "content": "hi"}]):
            received.append(chunk)

        assert len(received) == 2
        assert received[0].content == "a"
        assert received[1].finish_reason == "stop"

    def test_get_tool_schemas_calls_provider(self):
        provider = MagicMock()
        provider.to_tool_schema = MagicMock(return_value=[{"type": "function"}])

        tools = [{"name": "calc", "description": "...", "parameters": {}}]
        config = AgentConfig(agent_name="test", model="gpt-4o", tools=tools)
        with patch("app.core.agent.llm.get_adapter", return_value=provider):
            adapter = LLMAdapter(config=config, tools=tools)

        schemas = adapter.get_tool_schemas()
        provider.to_tool_schema.assert_called_once_with(tools)
        assert schemas == [{"type": "function"}]


class TestAdapterFactory:
    def test_unknown_model_fails_fast(self):
        from app.core.adapter.factory import get_adapter

        with patch.dict("app.core.adapter.factory._ADAPTER_CACHE", {}, clear=True):
            with pytest.raises(ValueError, match="Unsupported model"):
                get_adapter("my-custom-model")


class TestDBPersistStrategy:
    @pytest.mark.asyncio
    async def test_flush_uses_session_flush_without_commit(self):
        db = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()

        strategy = DBPersistStrategy(db)
        await strategy.flush()

        db.flush.assert_awaited_once()
        db.commit.assert_not_called()
