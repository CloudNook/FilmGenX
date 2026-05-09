"""
MemoryRanker Protocol —— 召回结果排序策略。

framework 不内置具体排序算法。业务自己决定怎么打分：
- 相似度 / 新鲜度 / 置信度 加权
- 用 LLM 评分
- 业务字段优先级
- 等等

实现放在 ``app/memory/rankers/`` 下。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.core.agent.memory.types import RecallQuery, RecalledMemory, ScoredMemory


@runtime_checkable
class MemoryRanker(Protocol):
    async def rank(
        self,
        candidates: list[RecalledMemory],
        query: RecallQuery,
    ) -> list[ScoredMemory]:
        """给每条 RecalledMemory 打 [0, 1] 分并按降序返回。

        阈值过滤由 ``MemoryHarness.recall`` 在调用方按 ``recall_threshold`` 收口，
        ranker 不关心阈值。
        """
        ...
