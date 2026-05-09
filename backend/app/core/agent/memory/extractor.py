"""
MemoryExtractor Protocol —— 把原始消息序列压缩为候选 memory 条目。

典型业务实现是 LLM-based：用便宜模型 summarize / 抽事实，标注 confidence 和 kind。
也可以是规则式（直接构造 candidate，无需 LLM）。

实现放在 ``app/memory/extractors/`` 下。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.core.agent.memory.types import CandidateMemory


@runtime_checkable
class MemoryExtractor(Protocol):
    async def extract(
        self,
        messages: list[dict[str, Any]],
        scope_metadata: dict[str, Any],
    ) -> list[CandidateMemory]:
        """从 messages 中抽出可写入的候选 memory 列表。

        Args:
            messages: 输入对话片段（来自 fallback compact / explicit save / user correction）
            scope_metadata: 业务 scope，extractor 可参考但不必使用

        Returns:
            候选条目列表；返回空列表表示"这段没什么值得记的"，pipeline 直接结束
        """
        ...
