"""Add reference_images and generated_images to shots.

Revision ID: p8q9r0s1t2u3
Revises: o7p8q9r0s1t2
Create Date: 2026-04-08

reference_images: 用户从角色/场景库选择的参考图（用于图生图）
generated_images: AI生成的图片列表
"""
from alembic import op
import sqlalchemy as sa


revision = "p8q9r0s1t2u3"
down_revision = "c56b7c8365f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shots", sa.Column(
        "reference_images",
        sa.JSON(),
        nullable=False,
        server_default="[]",
        comment="用户选择的参考图：[{url, label, name, ...}]",
    ))
    op.add_column("shots", sa.Column(
        "generated_images",
        sa.JSON(),
        nullable=False,
        server_default="[]",
        comment="AI生成的图片：[{url, created_at, task_id}]",
    ))


def downgrade() -> None:
    op.drop_column("shots", "generated_images")
    op.drop_column("shots", "reference_images")
