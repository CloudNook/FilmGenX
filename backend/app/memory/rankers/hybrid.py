"""
HybridRanker —— 实现 ``MemoryRanker`` Protocol，业务层的默认排序策略。

三个维度加权：
- ``similarity``：candidate.embedding ⟷ query embedding 的 cosine 相似度（[0,1]）。
  缺任一向量退化为常数 0.5（中性）
- ``freshness``：基于 created_at 的指数衰减，half-life 默认 30 天
- ``confidence``：直接取 candidate.confidence

通过 ``EmbeddingService`` 注入提供 query 向量化能力；不传也能跑（相似度全 0.5）。

业务后续可换 ``LLMRanker`` / ``BusinessScoreRanker``（基于业务字段优先级），不需要
动框架 — Protocol 一致即可。
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Optional

from app.core.agent.memory.embedding import EmbeddingService
from app.core.agent.memory.ranker import MemoryRanker
from app.core.agent.memory.types import RecallQuery, RecalledMemory, ScoredMemory

logger = logging.getLogger(__name__)


class HybridRanker(MemoryRanker):
    """实现 ``MemoryRanker`` Protocol。"""

    def __init__(
        self,
        *,
        embedding_service: Optional[EmbeddingService] = None,
        w_similarity: float = 0.5,
        w_freshness: float = 0.3,
        w_confidence: float = 0.2,
        freshness_half_life_days: float = 30.0,
    ) -> None:
        total = w_similarity + w_freshness + w_confidence
        if total <= 0:
            raise ValueError("at least one weight must be > 0")
        self.w_sim = w_similarity / total
        self.w_fresh = w_freshness / total
        self.w_conf = w_confidence / total
        self.half_life_days = freshness_half_life_days
        self._embedding = embedding_service

    async def rank(
        self,
        candidates: list[RecalledMemory],
        query: RecallQuery,
    ) -> list[ScoredMemory]:
        if not candidates:
            return []

        # 优先取 query.metadata 里业务直接放好的 query_embedding；否则现算
        query_vec: Optional[list[float]] = query.metadata.get("query_embedding")
        if query_vec is None and query.initial_input and self._embedding is not None:
            try:
                vecs = await self._embedding.embed([query.initial_input])
                query_vec = vecs[0] if vecs else None
            except Exception:
                logger.warning(
                    "[hybrid-ranker] query embedding failed; "
                    "similarity falls back to neutral 0.5"
                )

        now = datetime.now(timezone.utc)

        scored: list[ScoredMemory] = []
        for c in candidates:
            sim = _cosine_similarity_normalized(c.embedding, query_vec)
            fresh = _freshness(c.created_at, now, self.half_life_days)
            conf = max(0.0, min(1.0, c.confidence))

            score = self.w_sim * sim + self.w_fresh * fresh + self.w_conf * conf
            scored.append(
                ScoredMemory(
                    memory=c,
                    score=score,
                    breakdown={
                        "similarity": sim,
                        "freshness": fresh,
                        "confidence": conf,
                    },
                )
            )

        scored.sort(key=lambda s: s.score, reverse=True)
        return scored


def _cosine_similarity_normalized(
    a: list[float] | None,
    b: list[float] | None,
) -> float:
    """计算 a / b 的 cosine 相似度并归一化到 [0, 1]。任一缺失返回 0.5。"""
    if a is None or b is None or not a or len(a) != len(b):
        return 0.5
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.5
    cosine = dot / (na * nb)  # [-1, 1]
    return max(0.0, min(1.0, (cosine + 1.0) / 2.0))


def _freshness(
    created_at: datetime | None,
    now: datetime,
    half_life_days: float,
) -> float:
    """指数衰减：刚创建 ≈ 1.0，过 half_life_days = 0.5。"""
    if created_at is None:
        return 0.5
    age_days = max(0.0, (now - created_at).total_seconds() / 86400.0)
    return 0.5 ** (age_days / half_life_days)
