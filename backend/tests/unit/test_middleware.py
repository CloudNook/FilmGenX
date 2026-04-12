"""
Middleware 系统单元测试。

覆盖范围：
  - MiddlewareContext（构造、默认值、repr）
  - MiddlewareChain（run/stream/on_loop_start/on_loop_end/finalize_result 全量边界）
  - LoggingMiddleware（before/after/loop 各分支）
  - FinalSchemaResponseMiddleware（正常格式化、跳过条件、解析失败、异常、Pydantic schema）

所有测试均不依赖外部服务（LLM / Redis / DB）。
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

# ──────────────────────────────────────────────────────────────────
# 路径设置
# ──────────────────────────────────────────────────────────────────
BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.agent.base import AgentResult
from app.core.middleware.chain import AgentMiddleware, MiddlewareChain, MiddlewareContext
from app.core.middleware.builtin import (
    FinalSchemaResponseMiddleware,
    LoggingMiddleware,
    _normalize_schema,
)


# ═══════════════════════════════════════════════════════════════════
# 辅助工具
# ═══════════════════════════════════════════════════════════════════

class RecordingMiddleware(AgentMiddleware):
    """记录所有钩子调用顺序。"""
    name = "recorder"

    def __init__(self, label: str, log: list):
        self.label = label
        self.log = log

    async def before(self, ctx): self.log.append(f"{self.label}:before")
    async def after(self, ctx): self.log.append(f"{self.label}:after")
    async def on_loop_start(self, ctx): self.log.append(f"{self.label}:loop_start")
    async def on_loop_end(self, ctx): self.log.append(f"{self.label}:loop_end")


def _make_ctx(**overrides) -> MiddlewareContext:
    """构造默认 MiddlewareContext，支持关键字覆盖。"""
    defaults = dict(
        session_id="s1", request_id="r1",
        agent_name="test_agent", agent_id="a1",
        initial_input="你好",
    )
    defaults.update(overrides)
    return MiddlewareContext(**defaults)


def _make_result(**overrides) -> AgentResult:
    """构造默认 AgentResult，支持关键字覆盖。"""
    defaults = dict(agent_name="test_agent", raw_output="hello", finished=True)
    defaults.update(overrides)
    return AgentResult(**defaults)


# ═══════════════════════════════════════════════════════════════════
# 1. MiddlewareContext
# ═══════════════════════════════════════════════════════════════════

class TestMiddlewareContext:
    def test_required_fields(self):
        ctx = _make_ctx()
        assert ctx.session_id == "s1"
        assert ctx.request_id == "r1"
        assert ctx.agent_name == "test_agent"
        assert ctx.agent_id == "a1"
        assert ctx.initial_input == "你好"

    def test_default_values(self):
        ctx = _make_ctx()
        assert ctx.loop_count == 0
        assert ctx.loop_messages == []
        assert ctx.agent_config is None
        assert ctx.llm is None
        assert ctx.loop is None
        assert ctx.result is None
        assert ctx.metadata == {}

    def test_repr(self):
        ctx = _make_ctx()
        r = repr(ctx)
        assert "s1" in r
        assert "r1" in r
        assert "loop=0" in r

    def test_metadata_is_independent_between_instances(self):
        ctx1 = _make_ctx()
        ctx2 = _make_ctx()
        ctx1.metadata["key"] = "value"
        assert "key" not in ctx2.metadata

    def test_override_loop_count(self):
        ctx = _make_ctx(loop_count=5)
        assert ctx.loop_count == 5


# ═══════════════════════════════════════════════════════════════════
# 2. MiddlewareChain — run
# ═══════════════════════════════════════════════════════════════════

class TestMiddlewareChainRun:
    @pytest.mark.asyncio
    async def test_onion_order(self):
        """before 正序，after 逆序。"""
        log = []
        chain = MiddlewareChain([
            RecordingMiddleware("m1", log),
            RecordingMiddleware("m2", log),
        ])
        async def handler():
            log.append("handler")
            return "ok"

        result = await chain.run(_make_ctx(), handler)
        assert result == "ok"
        assert log == ["m1:before", "m2:before", "handler", "m2:after", "m1:after"]

    @pytest.mark.asyncio
    async def test_empty_chain(self):
        """空链直接执行 handler。"""
        chain = MiddlewareChain([])
        async def handler():
            return 42

        assert await chain.run(_make_ctx(), handler) == 42

    @pytest.mark.asyncio
    async def test_single_middleware(self):
        log = []
        chain = MiddlewareChain([RecordingMiddleware("only", log)])
        async def handler():
            log.append("handler")
            return "done"

        result = await chain.run(_make_ctx(), handler)
        assert result == "done"
        assert log == ["only:before", "handler", "only:after"]

    @pytest.mark.asyncio
    async def test_after_called_on_exception(self):
        log = []
        chain = MiddlewareChain([RecordingMiddleware("m1", log)])
        async def failing():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await chain.run(_make_ctx(), failing)

        assert "m1:before" in log
        assert "m1:after" in log

    @pytest.mark.asyncio
    async def test_after_called_on_exception_nested(self):
        """多层 middleware，内层异常，所有 after 仍触发。"""
        log = []
        chain = MiddlewareChain([
            RecordingMiddleware("outer", log),
            RecordingMiddleware("inner", log),
        ])
        async def failing():
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError):
            await chain.run(_make_ctx(), failing)

        assert log == ["outer:before", "inner:before", "inner:after", "outer:after"]

    @pytest.mark.asyncio
    async def test_handler_return_value_propagated(self):
        chain = MiddlewareChain([RecordingMiddleware("m", [])])
        async def handler():
            return {"key": "value"}

        result = await chain.run(_make_ctx(), handler)
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_handler_return_none(self):
        chain = MiddlewareChain([RecordingMiddleware("m", [])])
        async def handler():
            return None

        result = await chain.run(_make_ctx(), handler)
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# 3. MiddlewareChain — stream
# ═══════════════════════════════════════════════════════════════════

class TestMiddlewareChainStream:
    @pytest.mark.asyncio
    async def test_basic_stream(self):
        log = []
        chain = MiddlewareChain([RecordingMiddleware("m1", log)])

        async def gen():
            yield "a"
            yield "b"

        items = []
        async for item in chain.stream(_make_ctx(), gen()):
            items.append(item)

        assert items == ["a", "b"]
        assert log[0] == "m1:before"
        assert log[-1] == "m1:after"

    @pytest.mark.asyncio
    async def test_stream_before_all_then_after_reversed(self):
        """stream 中 before 正序全部执行，after 逆序全部执行。"""
        log = []
        chain = MiddlewareChain([
            RecordingMiddleware("m1", log),
            RecordingMiddleware("m2", log),
        ])

        async def gen():
            yield "x"

        items = []
        async for item in chain.stream(_make_ctx(), gen()):
            items.append(item)

        assert items == ["x"]
        assert log[0] == "m1:before"
        assert log[1] == "m2:before"
        assert log[-2] == "m2:after"
        assert log[-1] == "m1:after"

    @pytest.mark.asyncio
    async def test_stream_after_on_exception(self):
        log = []
        chain = MiddlewareChain([RecordingMiddleware("m1", log)])

        async def broken():
            yield "ok"
            raise RuntimeError("stream error")

        with pytest.raises(RuntimeError, match="stream error"):
            async for _ in chain.stream(_make_ctx(), broken()):
                pass

        assert "m1:before" in log
        assert "m1:after" in log

    @pytest.mark.asyncio
    async def test_empty_stream(self):
        log = []
        chain = MiddlewareChain([RecordingMiddleware("m1", log)])

        async def empty_gen():
            return
            yield  # noqa — 让 Python 识别为 async generator

        items = []
        async for item in chain.stream(_make_ctx(), empty_gen()):
            items.append(item)

        assert items == []
        assert "m1:before" in log
        assert "m1:after" in log

    @pytest.mark.asyncio
    async def test_empty_chain_stream(self):
        chain = MiddlewareChain([])

        async def gen():
            yield 1
            yield 2

        items = []
        async for item in chain.stream(_make_ctx(), gen()):
            items.append(item)

        assert items == [1, 2]


# ═══════════════════════════════════════════════════════════════════
# 4. MiddlewareChain — on_loop_start / on_loop_end
# ═══════════════════════════════════════════════════════════════════

class TestMiddlewareChainLoopHooks:
    @pytest.mark.asyncio
    async def test_order(self):
        log = []
        chain = MiddlewareChain([
            RecordingMiddleware("m1", log),
            RecordingMiddleware("m2", log),
        ])
        await chain.on_loop_start(_make_ctx())
        await chain.on_loop_end(_make_ctx())
        assert log == ["m1:loop_start", "m2:loop_start", "m1:loop_end", "m2:loop_end"]

    @pytest.mark.asyncio
    async def test_empty_chain(self):
        chain = MiddlewareChain([])
        await chain.on_loop_start(_make_ctx())
        await chain.on_loop_end(_make_ctx())

    @pytest.mark.asyncio
    async def test_single_middleware(self):
        log = []
        chain = MiddlewareChain([RecordingMiddleware("m", log)])
        await chain.on_loop_start(_make_ctx())
        assert log == ["m:loop_start"]

    @pytest.mark.asyncio
    async def test_multiple_calls(self):
        """多次调用 on_loop_start/end，每次都触发。"""
        log = []
        chain = MiddlewareChain([RecordingMiddleware("m", log)])
        await chain.on_loop_start(_make_ctx())
        await chain.on_loop_end(_make_ctx())
        await chain.on_loop_start(_make_ctx())
        await chain.on_loop_end(_make_ctx())
        assert log == [
            "m:loop_start", "m:loop_end",
            "m:loop_start", "m:loop_end",
        ]


# ═══════════════════════════════════════════════════════════════════
# 5. MiddlewareChain — finalize_result
# ═══════════════════════════════════════════════════════════════════

class TestMiddlewareChainFinalize:
    @pytest.mark.asyncio
    async def test_order(self):
        log = []
        class AppendMiddleware(AgentMiddleware):
            def __init__(self, label):
                self.label = label
                self.name = label
            async def finalize_result(self, ctx, result):
                log.append(f"{self.label}")
                result.raw_output += f"|{self.label}"
                return result

        chain = MiddlewareChain([AppendMiddleware("m1"), AppendMiddleware("m2")])
        result = _make_result(raw_output="base")
        finalized = await chain.finalize_result(_make_ctx(), result)

        assert finalized.raw_output == "base|m1|m2"
        assert log == ["m1", "m2"]

    @pytest.mark.asyncio
    async def test_ctx_result_updated_after_each_finalize(self):
        """finalize_result 中 ctx.result 在每个 middleware 执行完后更新。"""
        updates = []
        class ObserveMiddleware(AgentMiddleware):
            name = "observe"
            async def finalize_result(self, ctx, result):
                updates.append(result.raw_output)
                result.raw_output += "+1"
                return result

        chain = MiddlewareChain([ObserveMiddleware(), ObserveMiddleware()])
        result = _make_result(raw_output="start")
        ctx = _make_ctx()
        await chain.finalize_result(ctx, result)

        assert updates == ["start", "start+1"]
        assert ctx.result.raw_output == "start+1+1"

    @pytest.mark.asyncio
    async def test_empty_chain(self):
        chain = MiddlewareChain([])
        result = _make_result(raw_output="original")
        finalized = await chain.finalize_result(_make_ctx(), result)
        assert finalized.raw_output == "original"

    @pytest.mark.asyncio
    async def test_middleware_can_replace_result(self):
        class ReplaceMiddleware(AgentMiddleware):
            name = "replace"
            async def finalize_result(self, ctx, result):
                return _make_result(raw_output="replaced")

        chain = MiddlewareChain([ReplaceMiddleware()])
        result = _make_result(raw_output="original")
        finalized = await chain.finalize_result(_make_ctx(), result)
        assert finalized.raw_output == "replaced"


# ═══════════════════════════════════════════════════════════════════
# 6. LoggingMiddleware
# ═══════════════════════════════════════════════════════════════════

class TestLoggingMiddleware:
    @pytest.fixture
    def mw(self):
        return LoggingMiddleware()

    @pytest.mark.asyncio
    async def test_before_logs_request(self, mw, caplog):
        ctx = _make_ctx(initial_input="这是一段测试输入，长度超过一百个字符，需要被截断处理，"
                                       "我们继续添加更多文字以确保超过一百个字符的限制")
        with caplog.at_level(logging.INFO, logger="app.core.middleware.builtin"):
            await mw.before(ctx)
        assert ctx.request_id in caplog.text
        assert ctx.agent_name in caplog.text
        assert "Starting" in caplog.text

    @pytest.mark.asyncio
    async def test_after_with_result(self, mw, caplog):
        result = _make_result(loop_count=3, error=None)
        ctx = _make_ctx(loop_count=3)
        ctx.result = result
        with caplog.at_level(logging.INFO, logger="app.core.middleware.builtin"):
            await mw.after(ctx)
        assert "Finished" in caplog.text
        assert "loop=3" in caplog.text

    @pytest.mark.asyncio
    async def test_after_with_error_result(self, mw, caplog):
        result = _make_result(error="timeout", finished=False)
        ctx = _make_ctx()
        ctx.result = result
        with caplog.at_level(logging.INFO, logger="app.core.middleware.builtin"):
            await mw.after(ctx)
        assert "error=timeout" in caplog.text

    @pytest.mark.asyncio
    async def test_after_without_result(self, mw, caplog):
        ctx = _make_ctx()
        with caplog.at_level(logging.INFO, logger="app.core.middleware.builtin"):
            await mw.after(ctx)
        assert "no result" in caplog.text

    @pytest.mark.asyncio
    async def test_on_loop_start(self, mw, caplog):
        ctx = _make_ctx(loop_count=2)
        with caplog.at_level(logging.DEBUG, logger="app.core.middleware.builtin"):
            await mw.on_loop_start(ctx)
        assert "Loop start #2" in caplog.text

    @pytest.mark.asyncio
    async def test_on_loop_end(self, mw, caplog):
        ctx = _make_ctx(loop_count=5)
        with caplog.at_level(logging.DEBUG, logger="app.core.middleware.builtin"):
            await mw.on_loop_end(ctx)
        assert "Loop end #5" in caplog.text


# ═══════════════════════════════════════════════════════════════════
# 7. FinalSchemaResponseMiddleware
# ═══════════════════════════════════════════════════════════════════

class TestFinalSchemaResponseMiddleware:
    def _make_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
        }

    def test_normalize_dict_schema(self):
        schema = {"type": "object"}
        assert _normalize_schema(schema) == schema

    def test_normalize_pydantic_schema(self):
        class MyModel(BaseModel):
            name: str
            age: int = 0

        result = _normalize_schema(MyModel)
        assert result["properties"]["name"]["type"] == "string"
        assert result["properties"]["age"]["type"] == "integer"

    def test_normalize_invalid_type_raises(self):
        with pytest.raises(TypeError, match="Unsupported schema type"):
            _normalize_schema([1, 2, 3])

    def test_default_system_prompt(self):
        mw = FinalSchemaResponseMiddleware(self._make_schema())
        assert "结构化结果整理器" in mw.system_prompt

    def test_custom_system_prompt(self):
        mw = FinalSchemaResponseMiddleware(
            self._make_schema(), system_prompt="自定义提示"
        )
        assert mw.system_prompt == "自定义提示"

    def test_build_prompt_contains_input_and_output(self):
        mw = FinalSchemaResponseMiddleware(self._make_schema())
        ctx = _make_ctx(initial_input="用户问题")
        prompt = mw._build_prompt(ctx, "AI回答")
        assert "用户问题" in prompt
        assert "AI回答" in prompt

    @pytest.mark.asyncio
    async def test_finalize_normal_case(self):
        """正常：追加 LLM 调用，解析 JSON，合并 usage。"""
        schema = self._make_schema()
        llm = MagicMock()
        llm.generate = AsyncMock(return_value=MagicMock(
            content='{"answer":"42"}',
            usage={"prompt_tokens": 2, "completion_tokens": 3},
        ))
        llm.parse_json = MagicMock(return_value={"answer": "42"})

        mw = FinalSchemaResponseMiddleware(schema)
        ctx = _make_ctx(llm=llm)
        result = _make_result(raw_output="答案是42", usage={"prompt_tokens": 10})

        finalized = await mw.finalize_result(ctx, result)
        assert finalized.schema_data == {"answer": "42"}
        assert finalized.schema_error is None
        assert finalized.usage["prompt_tokens"] == 12
        assert finalized.usage["completion_tokens"] == 3

    @pytest.mark.asyncio
    async def test_finalize_skips_unfinished_result(self):
        mw = FinalSchemaResponseMiddleware(self._make_schema())
        result = _make_result(finished=False)
        ctx = _make_ctx()

        finalized = await mw.finalize_result(ctx, result)
        assert finalized.schema_data is None

    @pytest.mark.asyncio
    async def test_finalize_skips_result_with_error(self):
        mw = FinalSchemaResponseMiddleware(self._make_schema())
        result = _make_result(finished=True, error="something failed")
        ctx = _make_ctx()

        finalized = await mw.finalize_result(ctx, result)
        assert finalized.schema_data is None

    @pytest.mark.asyncio
    async def test_finalize_skips_empty_raw_output(self):
        mw = FinalSchemaResponseMiddleware(self._make_schema())
        result = _make_result(finished=True, raw_output="")
        ctx = _make_ctx()

        finalized = await mw.finalize_result(ctx, result)
        assert finalized.schema_data is None

    @pytest.mark.asyncio
    async def test_finalize_skips_already_has_schema_data(self):
        mw = FinalSchemaResponseMiddleware(self._make_schema())
        result = _make_result(
            finished=True, raw_output="text",
            schema_data={"answer": "existing"},
        )
        ctx = _make_ctx()

        finalized = await mw.finalize_result(ctx, result)
        assert finalized.schema_data == {"answer": "existing"}

    @pytest.mark.asyncio
    async def test_finalize_no_llm_sets_error(self):
        mw = FinalSchemaResponseMiddleware(self._make_schema())
        ctx = _make_ctx(llm=None)
        result = _make_result(finished=True, raw_output="content")

        finalized = await mw.finalize_result(ctx, result)
        assert "requires llm" in finalized.schema_error

    @pytest.mark.asyncio
    async def test_finalize_parse_failure_sets_error(self):
        llm = MagicMock()
        llm.generate = AsyncMock(return_value=MagicMock(
            content="not-json", usage=None,
        ))
        llm.parse_json = MagicMock(return_value=None)

        mw = FinalSchemaResponseMiddleware(self._make_schema())
        ctx = _make_ctx(llm=llm)
        result = _make_result(finished=True, raw_output="content")

        finalized = await mw.finalize_result(ctx, result)
        assert finalized.schema_data is None
        assert "Failed to parse" in finalized.schema_error

    @pytest.mark.asyncio
    async def test_finalize_llm_exception_sets_error(self):
        llm = MagicMock()
        llm.generate = AsyncMock(side_effect=RuntimeError("API down"))

        mw = FinalSchemaResponseMiddleware(self._make_schema())
        ctx = _make_ctx(llm=llm)
        result = _make_result(finished=True, raw_output="content")

        finalized = await mw.finalize_result(ctx, result)
        assert "API down" in finalized.schema_error

    @pytest.mark.asyncio
    async def test_parse_response_uses_llm_parse_json(self):
        llm = MagicMock()
        llm.parse_json = MagicMock(return_value={"parsed": True})

        result = FinalSchemaResponseMiddleware._parse_response(
            _make_ctx(llm=llm), '{"parsed": true}'
        )
        assert result == {"parsed": True}

    @pytest.mark.asyncio
    async def test_parse_response_fallback_json_loads(self):
        llm = MagicMock(spec=[])
        result = FinalSchemaResponseMiddleware._parse_response(
            _make_ctx(llm=llm), '{"key": "val"}'
        )
        assert result == {"key": "val"}

    @pytest.mark.asyncio
    async def test_parse_response_invalid_json_returns_none(self):
        llm = MagicMock(spec=[])
        result = FinalSchemaResponseMiddleware._parse_response(
            _make_ctx(llm=llm), "not json at all"
        )
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# 8. middleware_chain 快捷函数
# ═══════════════════════════════════════════════════════════════════

class TestMiddlewareChainHelper:
    def test_middleware_chain_creates_chain(self):
        from app.core.middleware.chain import middleware_chain
        chain = middleware_chain([])
        assert isinstance(chain, MiddlewareChain)

    def test_middleware_chain_preserves_middlewares(self):
        from app.core.middleware.chain import middleware_chain
        m1 = RecordingMiddleware("m1", [])
        m2 = RecordingMiddleware("m2", [])
        chain = middleware_chain([m1, m2])
        assert len(chain.middlewares) == 2
        assert chain.middlewares[0] is m1
        assert chain.middlewares[1] is m2
