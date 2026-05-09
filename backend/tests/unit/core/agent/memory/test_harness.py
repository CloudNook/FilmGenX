"""MemoryHarness 主路径：recall / write / format / 兜底触发。

测试用 inline fakes（FakeProvider / FixedCandidatesExtractor / PassthroughRanker）
验证 framework 自身的协调逻辑，不依赖任何具体业务实现。
"""

from __future__ import annotations

import asyncio

import pytest

from app.core.agent.memory import (
    CandidateMemory,
    FilterChain,
    MemoryConfig,
    MemoryHarness,
    WriteTrigger,
)

from tests.unit.core.agent.memory._fakes import (
    ConstFilter,
    FakeProvider,
    FixedCandidatesExtractor,
    PassthroughRanker,
)


def _make_harness(
    *,
    candidates: list[CandidateMemory] | None = None,
    pre_filters: list | None = None,
    post_filters: list | None = None,
    pre_threshold: float = 0.5,
    post_threshold: float = 0.5,
    scope: dict | None = None,
) -> tuple[MemoryHarness, FakeProvider, FixedCandidatesExtractor]:
    provider = FakeProvider()
    if candidates is None:
        candidates = [CandidateMemory(content="default", kind="fact", confidence=1.0)]
    extractor = FixedCandidatesExtractor(candidates)
    cfg = MemoryConfig(
        provider=provider,
        extractor=extractor,
        ranker=PassthroughRanker(),
        pre_extraction_filters=FilterChain(
            pre_filters or [],
            aggregation="min",
            threshold=pre_threshold,
        ),
        post_extraction_filters=FilterChain(
            post_filters or [],
            aggregation="min",
            threshold=post_threshold,
        ),
        scope_metadata=scope or {"project_id": 42},
    )
    harness = MemoryHarness(cfg, agent_name="test_agent", session_id="sess-1")
    return harness, provider, extractor


# -------------------------- write 主路径 -------------------------- #


@pytest.mark.asyncio
async def test_write_full_pipeline_passes_when_filters_open():
    h, provider, extractor = _make_harness()
    out = await h.write(
        messages=[{"role": "user", "content": "hello"}],
        trigger=WriteTrigger.EXPLICIT_SAVE,
    )
    assert out.candidates_total == 1
    assert out.candidates_written == 1
    assert len(out.written_ids) == 1
    assert len(provider.write_calls) == 1
    assert len(extractor.calls) == 1


@pytest.mark.asyncio
async def test_write_pre_filter_blocks_extractor():
    """pre_filter 失败 → extractor 不应被调用，省 LLM 钱。"""
    h, provider, extractor = _make_harness(
        pre_filters=[ConstFilter("hard_no", 0.0)],
        pre_threshold=0.5,
    )
    out = await h.write(
        messages=[{"role": "user", "content": "hello"}],
        trigger=WriteTrigger.EXPLICIT_SAVE,
    )
    assert out.pre_decision.passed is False
    assert out.candidates_total == 0
    assert out.candidates_written == 0
    assert len(extractor.calls) == 0  # 关键：pre 砍了，extractor 没被调
    assert len(provider.write_calls) == 0


@pytest.mark.asyncio
async def test_write_post_filter_blocks_low_quality_candidate():
    """post_filter 失败 → provider.write 不被调用。"""
    h, provider, _ = _make_harness(
        post_filters=[ConstFilter("hard_no", 0.0)],
        post_threshold=0.5,
    )
    out = await h.write(
        messages=[{"role": "user", "content": "hello"}],
        trigger=WriteTrigger.EXPLICIT_SAVE,
    )
    assert out.pre_decision.passed is True
    assert out.candidates_total == 1
    assert out.candidates_written == 0
    assert all(not d.passed for d in out.post_decisions)
    assert len(provider.write_calls) == 0


@pytest.mark.asyncio
async def test_write_each_candidate_is_evaluated_independently():
    """多个候选时，每个独立通过 post chain。"""
    cands = [
        CandidateMemory(content="keep me", kind="a", confidence=1.0),
        CandidateMemory(content="drop me", kind="b", confidence=0.1),
    ]
    h, provider, _ = _make_harness(
        candidates=cands,
        post_filters=[ConstFilter("conf_proxy", 0.0)],  # 全砍 → 都 drop
        post_threshold=0.5,
    )
    out = await h.write(
        messages=[{"role": "user", "content": "x"}],
        trigger=WriteTrigger.EXPLICIT_SAVE,
    )
    assert out.candidates_total == 2
    assert out.candidates_written == 0
    assert len(out.post_decisions) == 2  # 每个候选独立 evaluate


@pytest.mark.asyncio
async def test_explicit_save_overrides_kind_and_confidence():
    """LLM 调 memory_save 时给的 kind / confidence 接管 extractor 默认。"""
    h, provider, _ = _make_harness(
        candidates=[CandidateMemory(content="x", kind="default", confidence=0.4)],
    )
    out = await h.write(
        messages=[{"role": "user", "content": "x"}],
        trigger=WriteTrigger.EXPLICIT_SAVE,
        explicit_kind="preference",
        explicit_confidence=0.95,
    )
    assert out.candidates_written == 1
    assert provider.write_calls[0].kind == "preference"
    assert provider.write_calls[0].confidence == 0.95


@pytest.mark.asyncio
async def test_user_correction_does_not_override_kind():
    """非 explicit_save trigger 不应被 explicit_* 参数影响。"""
    h, provider, _ = _make_harness(
        candidates=[CandidateMemory(content="x", kind="default", confidence=0.4)],
    )
    out = await h.write(
        messages=[{"role": "user", "content": "x"}],
        trigger=WriteTrigger.USER_CORRECTION,
        explicit_kind="should_be_ignored",
        explicit_confidence=0.99,
    )
    assert out.candidates_written == 1
    # 非 explicit_save 时 kind / confidence 不被覆盖
    assert provider.write_calls[0].kind == "default"
    assert provider.write_calls[0].confidence == 0.4


# -------------------------- recall 主路径 -------------------------- #


@pytest.mark.asyncio
async def test_recall_returns_topk_above_threshold():
    h, provider, _ = _make_harness()
    # 先写两条
    await h.write(
        messages=[{"role": "user", "content": "a"}],
        trigger=WriteTrigger.EXPLICIT_SAVE,
    )
    await h.write(
        messages=[{"role": "user", "content": "b"}],
        trigger=WriteTrigger.EXPLICIT_SAVE,
    )

    scored = await h.recall(initial_input="some task", recent_messages=[])
    # PassthroughRanker score=1.0，全部 >= 0.5 阈值
    assert len(scored) == 2
    assert all(s.score == 1.0 for s in scored)


@pytest.mark.asyncio
async def test_recall_max_items_caps_results():
    h, provider, _ = _make_harness()
    h.config.recall_max_items = 1
    for i in range(3):
        await h.write(
            messages=[{"role": "user", "content": f"m{i}"}],
            trigger=WriteTrigger.EXPLICIT_SAVE,
        )
    scored = await h.recall(initial_input="x")
    assert len(scored) == 1


@pytest.mark.asyncio
async def test_recall_threshold_filters_out_low_score():
    """ranker 给低分的条目被阈值砍。"""

    class _LowScoringRanker:
        async def rank(self, candidates, query):
            from app.core.agent.memory.types import ScoredMemory
            return [ScoredMemory(memory=c, score=0.1) for c in candidates]

    h, provider, _ = _make_harness()
    h.config.ranker = _LowScoringRanker()  # type: ignore[assignment]
    h.config.recall_threshold = 0.5

    await h.write(
        messages=[{"role": "user", "content": "x"}],
        trigger=WriteTrigger.EXPLICIT_SAVE,
    )
    scored = await h.recall(initial_input="x")
    assert scored == []


@pytest.mark.asyncio
async def test_recall_silently_returns_empty_on_provider_error():
    """provider.recall 抛异常 → 静默返回空，不阻塞主流。"""

    class _BoomProvider(FakeProvider):
        async def recall(self, query):
            raise RuntimeError("backend down")

    h, _, _ = _make_harness()
    h.config.provider = _BoomProvider()  # type: ignore[assignment]
    scored = await h.recall(initial_input="x")
    assert scored == []


@pytest.mark.asyncio
async def test_recall_silently_returns_empty_on_timeout():
    class _SlowProvider(FakeProvider):
        async def recall(self, query):
            await asyncio.sleep(5.0)
            return []

    h, _, _ = _make_harness()
    h.config.provider = _SlowProvider()  # type: ignore[assignment]
    h.config.recall_timeout_seconds = 0.05
    scored = await h.recall(initial_input="x")
    assert scored == []


# ------------------------ 兜底 compact 计数 ------------------------ #


def test_tick_loop_fires_every_n_loops():
    h, _, _ = _make_harness()
    h.config.fallback_compact_every_n_loops = 3
    assert h.tick_loop() is False
    assert h.tick_loop() is False
    assert h.tick_loop() is True   # 第 3 次触发
    assert h.tick_loop() is False
    assert h.tick_loop() is False
    assert h.tick_loop() is True


def test_reset_compact_counter():
    h, _, _ = _make_harness()
    h.config.fallback_compact_every_n_loops = 3
    h.tick_loop()
    h.tick_loop()
    h.reset_compact_counter()
    # reset 之后又要 3 次才触发
    assert h.tick_loop() is False
    assert h.tick_loop() is False
    assert h.tick_loop() is True


# ------------------ format_recalled_for_prompt ----------------- #


@pytest.mark.asyncio
async def test_format_recalled_includes_section_title_and_kind():
    h, _, _ = _make_harness(
        candidates=[
            CandidateMemory(content="user prefers cold tones", kind="placeholder", confidence=1.0),
        ],
    )
    await h.write(
        messages=[{"role": "user", "content": "anything"}],
        trigger=WriteTrigger.EXPLICIT_SAVE,
        explicit_kind="preference",  # 覆盖 candidate.kind=placeholder
    )
    scored = await h.recall(initial_input="x")
    block = h.format_recalled_for_prompt(scored)
    assert h.config.inject_section_title in block
    assert "[preference]" in block
    assert "cold tones" in block


def test_format_recalled_empty_returns_empty_string():
    h, _, _ = _make_harness()
    block = h.format_recalled_for_prompt([])
    assert block == ""


@pytest.mark.asyncio
async def test_format_recalled_system_message_strategy():
    h, _, _ = _make_harness()
    h.config.inject_strategy = "system_message"
    await h.write(
        messages=[{"role": "user", "content": "remember X"}],
        trigger=WriteTrigger.EXPLICIT_SAVE,
        explicit_kind="fact",
    )
    scored = await h.recall(initial_input="x")
    block = h.format_recalled_for_prompt(scored)
    assert h.config.inject_section_title in block
    assert "[fact]" in block
