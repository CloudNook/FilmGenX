"""
Memory Provider Protocol —— 存储层抽象。

framework 不在乎你用 PG / Redis / Qdrant / pgvector / 其他向量库 —— 只通过这个
Protocol 调用。具体实现由业务在 ``app/memory/providers/`` 下提供。

接口最小化为三个：
- ``recall(query)`` 召回（读）
- ``commit_extraction(candidates, scope, cursor_key, cursor_marker)`` 写入
  + 推进游标，**单一事务原子完成**
- ``get_extract_cursor(cursor_key)`` 查游标（读）

不再单独提供 ``write`` / ``set_extract_cursor`` —— 所有写入路径必须通过
``commit_extraction``，框架要求"写候选 + 移动游标"必须 all-or-nothing，否则会
出现"部分写入但游标未推进 → 下次重抽"或"游标推进但写入失败 → 数据丢失"的不一致。
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

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

    async def get_extract_cursor(self, cursor_key: str) -> Optional[str]:
        """查询某个 cursor key 上次抽取推进到的 marker。

        ``cursor_key`` 由 framework 构造（通常是 ``{session_id}:{agent_name}``），
        provider 不解释，仅作为存储 key。返回 ``None`` 表示这个 key 从未抽过。

        marker 格式由 framework 决定（``"seq:<n>"`` 或 ``"hash:<sha>"``），
        provider 也不解释——纯字符串往返存储。
        """
        ...

    async def commit_extraction(
        self,
        candidates: list[CandidateMemory],
        scope_metadata: dict[str, Any],
        cursor_key: Optional[str] = None,
        cursor_marker: Optional[str] = None,
    ) -> list[str]:
        """**原子地**写入候选 + 推进游标。

        Args:
            candidates: 已通过 post-extraction filter 的候选列表（可空：候选全被 filter
                砍掉但仍要推进游标的场景）
            scope_metadata: 业务 scope（如 ``{"project_id": ...}``）
            cursor_key: 提供时同步推进抽取游标。``None`` 表示不动游标（如 explicit_save）
            cursor_marker: 给 cursor_key 配的 marker 值。``cursor_key`` 提供时必传

        Returns:
            stored memory id 列表，与 ``candidates`` 顺序对齐

        实现保证：
        - 要么所有 candidate 都成功写入 + cursor 同步推进，要么全部不生效
        - 失败必须抛异常给 caller（caller 决定是否记日志 / 重试）
        - 实现可以做 best-effort batching，但事务边界必须覆盖整批 + cursor
        """
        ...
