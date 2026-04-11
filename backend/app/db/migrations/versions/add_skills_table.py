"""add_skills_table

Revision ID: add_skills_table
Revises:
Create Date: 2026-04-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_skills_table"
down_revision: Union[str, None] = "3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # === Anthropic SKILL.md 标准字段 ===
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column(
            "parameters",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "examples",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "constraints",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        # === 扩展元数据字段 ===
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("difficulty", sa.String(length=32), nullable=True),
        sa.Column(
            "tags",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("author", sa.String(length=64), nullable=True),
        # === 系统字段 ===
        sa.Column("raw_markdown", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "skill_metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 部分唯一索引：name（仅未删除记录），允许软删除后同名重建
    op.execute(
        "CREATE UNIQUE INDEX ix_skills_name ON skills (name) WHERE is_deleted = false"
    )
    # 索引：is_deleted（已有软删除全局查询优化）
    op.create_index("ix_skills_is_deleted", "skills", ["is_deleted"])
    # 索引：category（管理员按领域分类查询）
    op.create_index("ix_skills_category", "skills", ["category"])


def downgrade() -> None:
    op.drop_index("ix_skills_category")
    op.drop_index("ix_skills_is_deleted")
    op.drop_index("ix_skills_name")
    op.drop_table("skills")
