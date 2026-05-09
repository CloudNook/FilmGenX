"""FilterChain 评分聚合 + 阈值 + 异常保护行为。

framework 不内置任何具体 filter；测试用 inline fakes（``ConstFilter`` /
``RaisingFilter`` / ``MinLengthContentFilter``）验证 chain 自身逻辑。
"""

from __future__ import annotations

import pytest

from app.core.agent.memory.filter import FilterChain
from app.core.agent.memory.types import CandidateMemory

from tests.unit.core.agent.memory._fakes import (
    ConstFilter,
    MinLengthContentFilter,
    RaisingFilter,
    make_post_ctx,
    make_pre_ctx,
)


# ----------------------------- 空 chain ----------------------------- #


@pytest.mark.asyncio
async def test_empty_chain_passes_unconditionally():
    chain = FilterChain([])
    decision = await chain.evaluate(make_pre_ctx([]))
    assert decision.passed is True
    assert decision.aggregate_score == 1.0
    assert decision.individual == []


# ----------------------------- 聚合策略 ----------------------------- #


@pytest.mark.asyncio
async def test_mean_aggregation():
    chain = FilterChain(
        [ConstFilter("a", 0.6), ConstFilter("b", 0.8)],
        aggregation="mean",
        threshold=0.5,
    )
    decision = await chain.evaluate(make_pre_ctx([]))
    assert decision.passed is True
    assert decision.aggregate_score == pytest.approx(0.7)


@pytest.mark.asyncio
async def test_min_aggregation_records_rejecter():
    chain = FilterChain(
        [ConstFilter("a", 0.9), ConstFilter("b", 0.2)],
        aggregation="min",
        threshold=0.5,
    )
    decision = await chain.evaluate(make_pre_ctx([]))
    assert decision.passed is False
    assert decision.aggregate_score == pytest.approx(0.2)
    assert decision.rejected_by == "b"


@pytest.mark.asyncio
async def test_max_aggregation():
    chain = FilterChain(
        [ConstFilter("a", 0.2), ConstFilter("b", 0.9)],
        aggregation="max",
        threshold=0.5,
    )
    decision = await chain.evaluate(make_pre_ctx([]))
    assert decision.passed is True
    assert decision.aggregate_score == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_weighted_aggregation():
    chain = FilterChain(
        [ConstFilter("a", 1.0), ConstFilter("b", 0.0)],
        aggregation="weighted",
        weights=[3.0, 1.0],
        threshold=0.5,
    )
    decision = await chain.evaluate(make_pre_ctx([]))
    # (1*3 + 0*1) / 4 = 0.75
    assert decision.aggregate_score == pytest.approx(0.75)
    assert decision.passed is True


@pytest.mark.asyncio
async def test_weighted_requires_matching_weights_length():
    with pytest.raises(ValueError):
        FilterChain(
            [ConstFilter("a", 1.0)],
            aggregation="weighted",
            weights=[1.0, 2.0],  # 长度不匹配
        )


@pytest.mark.asyncio
async def test_invalid_threshold_rejected():
    with pytest.raises(ValueError):
        FilterChain([], threshold=1.5)


# ----------------------------- 异常保护 ----------------------------- #


@pytest.mark.asyncio
async def test_raising_filter_treated_as_zero_not_propagated():
    chain = FilterChain([RaisingFilter()], threshold=0.5)
    decision = await chain.evaluate(make_pre_ctx([]))
    assert decision.passed is False
    assert decision.aggregate_score == 0.0
    name, score = decision.individual[0]
    assert name == "raises"
    assert "boom" in (score.reason or "")


# ------------------- 业务 filter 在 pre / post 上下文都能跑 -------------------- #


@pytest.mark.asyncio
async def test_filter_can_inspect_pre_extraction_messages():
    f = MinLengthContentFilter(min_length=5)
    s_short = await f.score(make_pre_ctx([{"role": "user", "content": "abc"}]))
    assert s_short.score == 0.0

    s_long = await f.score(make_pre_ctx([{"role": "user", "content": "long enough content"}]))
    assert s_long.score == 1.0


@pytest.mark.asyncio
async def test_filter_can_inspect_post_extraction_candidate():
    f = MinLengthContentFilter(min_length=5)
    cand_short = CandidateMemory(content="ab", kind="x")
    s_short = await f.score(make_post_ctx(cand_short))
    assert s_short.score == 0.0

    cand_long = CandidateMemory(content="long enough content", kind="x")
    s_long = await f.score(make_post_ctx(cand_long))
    assert s_long.score == 1.0
