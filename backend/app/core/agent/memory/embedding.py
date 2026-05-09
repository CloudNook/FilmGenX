"""
EmbeddingService Protocol —— 文本向量化抽象。

framework 不内置具体 embedding 模型实现。Provider / Ranker / Extractor 任何需要
向量化的组件都通过这个 Protocol 调用，业务在 ``app/memory/embeddings/`` 下接入
具体后端（Gemini / OpenAI / 本地模型 / 等）。

不绑定到 ``MemoryConfig`` —— embedding 是共享工具，由业务在构造 Provider /
Ranker 时显式注入。这样保留了"不需要 embedding 的 Provider 可以完全不依赖
embedding 服务"的灵活性。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingService(Protocol):
    """文本批量向量化。"""

    @property
    def dimension(self) -> int:
        """向量维度。Provider 建表时需要这个数（pgvector 列宽固定）。"""
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """把文本列表转成等长的向量列表。

        Args:
            texts: 待向量化的文本（可能为空列表，应返回空列表）

        Returns:
            ``len(texts)`` 个向量，每个长度 == ``self.dimension``。
            实现应保持顺序对齐。

        Raises:
            实现方决定。recall 路径上调用方应该 try/except 静默降级
            （embedding 挂了不阻塞 agent 主流），write 路径上抛错则该候选放弃。
        """
        ...
