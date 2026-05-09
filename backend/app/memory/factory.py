"""
``build_project_memory_config(project_id, ...)`` —— 业务装配快捷函数。

FilmGenX 一个 project = 一个剧本，每个 project 有独立的全局记忆。这个 factory
强制 ``project_id`` 必填，把 Provider / Ranker / Extractor / Embedding 一次装好，
返回一个可直接传给 ``create_agent(memory=...)`` 的 ``MemoryConfig``。

业务调用方（supervisor 或 endpoint）只需要：

    cfg = build_project_memory_config(project_id=42)
    agent = create_agent(..., memory=cfg)

Embedding 服务在 Provider 和 Ranker 之间共享同一个实例（避免重复构造客户端）。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.core.agent.memory import FilterChain, MemoryConfig
from app.db.session import AsyncSessionFactory
from app.memory.embeddings import GeminiEmbeddingService
from app.memory.extractors import GeminiLLMExtractor
from app.memory.providers import PgvectorMemoryProvider
from app.memory.rankers import HybridRanker


def build_project_memory_config(
    project_id: int,
    *,
    session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
    pre_extraction_filters: Optional[FilterChain] = None,
    post_extraction_filters: Optional[FilterChain] = None,
    save_tool_enabled: bool = True,
    fallback_compact_every_n_loops: int = 5,
    fallback_compact_message_window: int = 20,
    recall_threshold: float = 0.5,
    recall_max_items: int = 10,
) -> MemoryConfig:
    """构造 project-scoped MemoryConfig。

    Args:
        project_id: FilmGenX 项目 ID（剧本 ID）。Provider 锁定到这个值；
            所有 write / recall 强制按这个 project_id 隔离
        session_factory: 默认用 ``AsyncSessionFactory``，测试时可注入 mock
        pre_extraction_filters / post_extraction_filters: 业务自定义过滤链；
            为空表示不过滤（任何抽出来的候选都落库）
        save_tool_enabled: 是否给 agent 注入 ``memory_save`` 工具（让 LLM 主动存）
        fallback_compact_every_n_loops: 每 N 轮自动跑一次兜底 compact
        fallback_compact_message_window: 兜底 compact 抓最近 N 条 message
        recall_threshold: scored 之后保留 score >= threshold 的条目
        recall_max_items: 召回最多返回多少条
    """
    sf = session_factory or AsyncSessionFactory

    # 共享同一个 embedding 实例：Provider 写入时算向量，Ranker 召回时算 query 向量
    embedding = GeminiEmbeddingService()

    return MemoryConfig(
        provider=PgvectorMemoryProvider(
            session_factory=sf,
            project_id=project_id,
            embedding_service=embedding,
        ),
        extractor=GeminiLLMExtractor(),
        ranker=HybridRanker(embedding_service=embedding),
        pre_extraction_filters=pre_extraction_filters or FilterChain(),
        post_extraction_filters=post_extraction_filters or FilterChain(),
        save_tool_enabled=save_tool_enabled,
        fallback_compact_every_n_loops=fallback_compact_every_n_loops,
        fallback_compact_message_window=fallback_compact_message_window,
        recall_threshold=recall_threshold,
        recall_max_items=recall_max_items,
        # framework 的 scope_metadata 同步设上 project_id —— 给 filter 上下文 / 日志用
        scope_metadata={"project_id": project_id},
    )
