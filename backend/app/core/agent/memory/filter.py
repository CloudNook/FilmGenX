"""
MemoryFilter Protocol + FilterChain。

评分制：每个 filter 返回 [0, 1] 的 ``FilterScore``，chain 聚合后跟阈值比较。
二元 filter（{0.0, 1.0}）是评分制的特例。

写入流的两条独立 chain：
- ``pre_extraction_filters``：输入 ``PreExtractionContext``（原始对话），粗筛省抽取成本
- ``post_extraction_filters``：输入 ``PostExtractionContext``（含 candidate），细筛保质量

framework 不提供 log sink ——业务 filter 实现自己 log（或外部包一层 decorator）。
"""

from __future__ import annotations

from typing import Literal, Protocol, Union, runtime_checkable

from app.core.agent.memory.types import (
    FilterDecision,
    FilterScore,
    PostExtractionContext,
    PreExtractionContext,
)

FilterContext = Union[PreExtractionContext, PostExtractionContext]


@runtime_checkable
class MemoryFilter(Protocol):
    """单个 filter。按 ``name`` 标识，给上层调试和聚合用。"""

    name: str

    async def score(self, ctx: FilterContext) -> FilterScore:
        ...


Aggregation = Literal["mean", "min", "max", "weighted"]


class FilterChain:
    """评分聚合 + 阈值。空 chain 视为通过。"""

    def __init__(
        self,
        filters: list[MemoryFilter] | None = None,
        *,
        aggregation: Aggregation = "mean",
        weights: list[float] | None = None,
        threshold: float = 0.5,
    ) -> None:
        filters = filters or []
        if aggregation == "weighted":
            if weights is None or len(weights) != len(filters):
                raise ValueError(
                    "weighted aggregation requires weights matching filters length"
                )
            if any(w < 0 for w in weights):
                raise ValueError("weights must be non-negative")
            if sum(weights) <= 0:
                raise ValueError("weights must sum to a positive value")
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be in [0, 1]")

        self.filters = filters
        self.aggregation = aggregation
        self.weights = weights
        self.threshold = threshold

    async def evaluate(self, ctx: FilterContext) -> FilterDecision:
        if not self.filters:
            return FilterDecision(
                passed=True,
                aggregate_score=1.0,
                threshold=self.threshold,
                individual=[],
            )

        scored: list[tuple[str, FilterScore]] = []
        for f in self.filters:
            try:
                s = await f.score(ctx)
            except Exception as exc:  # filter 抛错 → 视为 0 分（保守）
                s = FilterScore(score=0.0, reason=f"filter raised: {exc!r}")
            scored.append((f.name, s))

        agg = self._aggregate([s.score for _, s in scored])

        rejected_by: str | None = None
        if self.aggregation == "min" and agg < self.threshold:
            min_idx = min(range(len(scored)), key=lambda i: scored[i][1].score)
            rejected_by = scored[min_idx][0]

        return FilterDecision(
            passed=agg >= self.threshold,
            aggregate_score=agg,
            threshold=self.threshold,
            individual=scored,
            rejected_by=rejected_by,
        )

    def _aggregate(self, raw: list[float]) -> float:
        if not raw:
            return 1.0
        if self.aggregation == "mean":
            return sum(raw) / len(raw)
        if self.aggregation == "min":
            return min(raw)
        if self.aggregation == "max":
            return max(raw)
        if self.aggregation == "weighted":
            assert self.weights is not None
            total_w = sum(self.weights)
            return sum(s * w for s, w in zip(raw, self.weights)) / total_w
        raise ValueError(f"unknown aggregation: {self.aggregation}")
