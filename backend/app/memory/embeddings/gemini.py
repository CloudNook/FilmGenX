"""
Gemini Embedding Service —— ``EmbeddingService`` Protocol 的 Gemini 实现。

调用 ``client.aio.models.embed_content`` 把文本批量转成 768 维向量，与
``MemoryEntry.embedding`` 列宽（vector(768)）对齐。

切换模型时务必检查：
- 新模型的输出维度与 alembic migration 写死的 ``EMBEDDING_DIM`` 一致
- 否则要写新 alembic 迁移 ALTER COLUMN + 重建 HNSW 索引
"""

from __future__ import annotations

import logging
from typing import Optional

from google import genai
from google.genai import types as genai_types

from app.core.agent.memory.embedding import EmbeddingService
from app.core.config import settings

logger = logging.getLogger(__name__)


# Gemini 默认 embedding 模型与维度。维度由 Memory 表 schema 决定，反过来约束这里。
DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"
DEFAULT_DIMENSION = 768


class GeminiEmbeddingService(EmbeddingService):
    """实现 ``EmbeddingService`` Protocol。"""

    def __init__(
        self,
        *,
        model: str = DEFAULT_EMBEDDING_MODEL,
        dimension: int = DEFAULT_DIMENSION,
        task_type: str = "SEMANTIC_SIMILARITY",
    ) -> None:
        """
        Args:
            model: Gemini embedding 模型名
            dimension: 期望的输出维度。必须与表里 ``embedding`` 列宽一致
            task_type: Gemini embedding 的任务类型 hint，影响向量空间。
                ``SEMANTIC_SIMILARITY`` 适合相似度召回；其他选项见 Google 文档。

        API key 走 ``settings.GOOGLE_API_KEY``（``.env`` 配置），不显式传。
        """
        self._model = model
        self._dimension = dimension
        self._task_type = task_type
        self._client: Optional[genai.Client] = None

    @property
    def dimension(self) -> int:
        return self._dimension

    def _get_client(self) -> genai.Client:
        if self._client is None:
            if not settings.GOOGLE_API_KEY:
                raise RuntimeError(
                    "GOOGLE_API_KEY 未配置（请检查 .env）；"
                    "GeminiEmbeddingService 需要 API key"
                )
            self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        return self._client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        client = self._get_client()
        config = genai_types.EmbedContentConfig(
            task_type=self._task_type,
            output_dimensionality=self._dimension,
        )

        try:
            response = await client.aio.models.embed_content(
                model=self._model,
                contents=texts,  # SDK 接受 list[str] 批量
                config=config,
            )
        except Exception:
            logger.exception(
                "[gemini-embedding] embed call failed (model=%s, n=%d)",
                self._model,
                len(texts),
            )
            raise

        # response.embeddings: list[ContentEmbedding]，每个含 .values: list[float]
        result: list[list[float]] = []
        for emb in response.embeddings or []:
            vec = emb.values or []
            if len(vec) != self._dimension:
                # 不该发生，但防御：维度不匹配会让 pgvector 写入失败
                raise RuntimeError(
                    f"Gemini returned embedding with dim={len(vec)}, "
                    f"expected {self._dimension}"
                )
            result.append(list(vec))

        if len(result) != len(texts):
            raise RuntimeError(
                f"Gemini returned {len(result)} embeddings for {len(texts)} inputs"
            )
        return result
