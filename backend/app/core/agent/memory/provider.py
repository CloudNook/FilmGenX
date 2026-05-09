"""
Memory Provider Protocol —— 存储层抽象。

framework 不在乎你用 PG / Redis / Qdrant / pgvector / 其他向量库 —— 只通过这个
Protocol 调用。具体实现由业务在 ``app/memory/providers/`` 下提供。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.core.agent.memory.types import (
    CandidateMemory,
    RecallQuery,
    RecalledMemory,
)


@runtime_checkable
class MemoryProvider(Protocol):
    """Memory 存储抽象。"""

    async def recall(self, query: RecallQuery) -> list[RecalledMemory]:
        """按 query 找出候选条目（未排序，未过滤阈值）。

        排序由 ``MemoryRanker`` 接管；阈值过滤由 ``MemoryHarness.recall`` 接管。
        provider 自己决定如何把 query 翻译成 SQL / vector search / KV lookup。
        """
        ...

    async def write(
        self,
        candidate: CandidateMemory,
        scope_metadata: dict[str, Any],
    ) -> str:
        """写入一条 memory。

        Args:
            candidate: 已经通过 ``post_extraction_filters`` 的候选条目
            scope_metadata: 业务层 scope（如 ``{"project_id": ...}``）；
                            framework 不解释，provider 决定如何索引

        Returns:
            stored memory 的唯一 id
        """
        ...
