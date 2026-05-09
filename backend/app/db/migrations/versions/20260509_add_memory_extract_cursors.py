"""add memory_extract_cursors table

跟踪 (session_id, agent_name) 上次抽取到的 marker，让 MemoryHarness 实现增量抽取。

Revision ID: 20260509extract_cursors
Revises: 20260509memory_tables
Create Date: 2026-05-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260509extract_cursors"
down_revision = "20260509memory_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory_extract_cursors",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cursor_key", sa.String(300), nullable=False),
        sa.Column("marker", sa.Text, nullable=False),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_memory_extract_cursors_key "
        "ON memory_extract_cursors (cursor_key)"
    )
    op.execute(
        "CREATE INDEX ix_memory_extract_cursors_is_deleted "
        "ON memory_extract_cursors (is_deleted)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS memory_extract_cursors")
