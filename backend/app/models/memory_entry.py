"""
Memory 事件型条目 —— append-only。

存储语义模糊匹配的 memory：reviewer 反馈、对话片段、episode_outcome 等。
按 created_at 时序累积，靠 vector + scope 索引召回。
"""

from datetime import datetime
from typing import Any, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Gemini text-embedding-004 输出 768 维；如果换 model，迁移时同步建新表 + 数据迁移。
# 这里用一个 sentinel 常量便于全局对齐。
MEMORY_EMBEDDING_DIM = 768


class MemoryEntry(Base):
    """事件型 memory 条目。

    设计要点：
    - **append-only**：每条都是历史的一部分，新条目不替换旧的
    - **vector 召回**：embedding 列做语义匹配
    - **scope 隔离**：scope 用 JSONB 存（{project_id, user_id, ...}），GIN 索引
    - **kind 分类**：kind 是业务自定义字符串，框架不解释
    """

    __tablename__ = "memory_entries"

    scope: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="业务 scope：{project_id, user_id, ...}，框架透传不解释",
    )
    kind: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="业务自定义类型（preference / episode_outcome / fact / 等）",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="自然语言主体，给 LLM 看 + 给 embedding 算",
    )
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(MEMORY_EMBEDDING_DIM),
        nullable=True,
        comment="content 的向量；写入时由 EmbeddingService 算，召回时做 cosine 相似度",
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="触发来源：agent_output / user_correction / explicit_save / inferred",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        server_default="1.0",
        comment="置信度 [0, 1]",
    )
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="业务附加字段（agent_name / session_id / 等）",
    )

    __table_args__ = (
        # GIN：scope @> '{"project_id": 42}' 这种模式匹配走索引
        Index("ix_memory_entries_scope_gin", "scope", postgresql_using="gin"),
        # 按 kind + 时间倒排查询用
        Index("ix_memory_entries_kind_created", "kind", "created_at"),
        # vector ANN 索引在 alembic 里手写（Vector 列的索引需要选择 ivfflat / hnsw + 距离函数）
    )
