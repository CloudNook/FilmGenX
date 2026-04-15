"""add hitl_enabled and review_nodes to supervisor_workflows

Revision ID: 26768d28b01c
Revises: t3u4v5w6x7y8
Create Date: 2026-04-12

NOTE: supervisor_workflows 表已在 t3u4v5w6x7y8 中创建并包含
hitl_enabled/review_nodes，本迁移不再执行任何操作（仅作历史标记）。
"""

from typing import Sequence, Union

from alembic import op


revision: str = "26768d28b01c"
down_revision: Union[str, Sequence[str], None] = "t3u4v5w6x7y8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass  # columns already exist in f1e2d3c4b5a6


def downgrade() -> None:
    pass  # columns remain in f1e2d3c4b5a6
