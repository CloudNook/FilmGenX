"""add memory_entries + memory_profile + pgvector extension

Memory 框架 Phase 1 业务层落地：
- 启用 pgvector 扩展
- ``memory_entries``：事件型 append-only，含 768 维 vector + scope JSONB
- ``memory_profile``：实体型 upsert，靠 (scope, entity_kind, entity_key) 唯一

向量索引选择 ``hnsw`` + ``vector_cosine_ops``。pgvector >= 0.5.0 支持 hnsw；
低版本 PG 实例可改 ``ivfflat``。

Revision ID: 20260509memory_tables
Revises: 20260507drop_legacy
Create Date: 2026-05-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260509memory_tables"
down_revision = "20260507drop_legacy"
branch_labels = None
depends_on = None


# 维度：Gemini text-embedding-004 = 768。换 model 时务必同步 alembic + 模型常量
EMBEDDING_DIM = 768


def upgrade() -> None:
    # 1. pgvector 扩展（幂等）
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. memory_entries 表
    op.create_table(
        "memory_entries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope", JSONB, nullable=False, comment="业务 scope：{project_id, user_id, ...}"),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        # vector 列直接用 raw SQL 表达，避免 alembic autogenerate 不识别
        sa.Column("embedding", sa.dialects.postgresql.ARRAY(sa.Float), nullable=True),  # placeholder，下面 ALTER 替换
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("extra_metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    # 把 embedding 列改成真正的 vector(768)
    op.execute(f"ALTER TABLE memory_entries DROP COLUMN embedding")
    op.execute(f"ALTER TABLE memory_entries ADD COLUMN embedding vector({EMBEDDING_DIM})")

    # 索引
    op.execute("CREATE INDEX ix_memory_entries_is_deleted ON memory_entries (is_deleted)")
    op.execute("CREATE INDEX ix_memory_entries_scope_gin ON memory_entries USING gin (scope)")
    op.execute("CREATE INDEX ix_memory_entries_kind_created ON memory_entries (kind, created_at DESC)")
    # 向量索引：HNSW + cosine
    op.execute(
        "CREATE INDEX ix_memory_entries_embedding_hnsw "
        "ON memory_entries USING hnsw (embedding vector_cosine_ops)"
    )

    # 3. memory_profile 表
    op.create_table(
        "memory_profile",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope", JSONB, nullable=False),
        sa.Column("entity_kind", sa.String(50), nullable=False),
        sa.Column("entity_key", sa.String(200), nullable=False),
        sa.Column("value", JSONB, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.execute("CREATE INDEX ix_memory_profile_is_deleted ON memory_profile (is_deleted)")
    op.execute("CREATE INDEX ix_memory_profile_scope_gin ON memory_profile USING gin (scope)")
    op.execute("CREATE INDEX ix_memory_profile_entity ON memory_profile (entity_kind, entity_key)")
    # 当前生效行的 partial unique：保留历史版本的同时保证 (scope, kind, key) 只有一条 active
    op.execute(
        "CREATE UNIQUE INDEX uq_memory_profile_active "
        "ON memory_profile (scope, entity_kind, entity_key) "
        "WHERE superseded_at IS NULL AND is_deleted = FALSE"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS memory_profile CASCADE")
    op.execute("DROP TABLE IF EXISTS memory_entries CASCADE")
    # 不 DROP EXTENSION vector —— 其它项目可能也在用同一 PG 实例
