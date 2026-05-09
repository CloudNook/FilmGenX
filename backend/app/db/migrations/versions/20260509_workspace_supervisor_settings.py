"""add workspace + supervisor_workflow settings columns

为 AI 工作台 / AI Supervisor 持久化前端 toggle：
  - workspaces: model / temperature / hitl_enabled / review_enabled / memory_enabled
  - supervisor_workflows: memory_enabled

刷新页面后从这两张表恢复默认。

Revision ID: 20260509ws_sv_settings
Revises: 20260509extract_cursors
Create Date: 2026-05-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260509ws_sv_settings"
down_revision = "20260509extract_cursors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column(
            "model",
            sa.String(50),
            nullable=False,
            server_default="gemini-3-flash-preview",
        ),
    )
    op.add_column(
        "workspaces",
        sa.Column(
            "temperature",
            sa.Float,
            nullable=False,
            server_default="0.7",
        ),
    )
    op.add_column(
        "workspaces",
        sa.Column(
            "hitl_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "workspaces",
        sa.Column(
            "review_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "workspaces",
        sa.Column(
            "memory_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "supervisor_workflows",
        sa.Column(
            "memory_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("supervisor_workflows", "memory_enabled")
    op.drop_column("workspaces", "memory_enabled")
    op.drop_column("workspaces", "review_enabled")
    op.drop_column("workspaces", "hitl_enabled")
    op.drop_column("workspaces", "temperature")
    op.drop_column("workspaces", "model")
