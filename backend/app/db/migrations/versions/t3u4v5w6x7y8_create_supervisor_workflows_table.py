"""create supervisor_workflows table

Revision ID: t3u4v5w6x7y8
Revises: add_usage_to_agent_messages
Create Date: 2026-04-13

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "t3u4v5w6x7y8"
down_revision: Union[str, Sequence[str], None] = "add_usage_to_agent_messages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "supervisor_workflows",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("supervisor_session_id", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("user_request", sa.Text(), nullable=False),
        sa.Column("model", sa.String(50), nullable=False, server_default="gemini-3-flash-preview"),
        sa.Column("status", sa.String(20), nullable=False, server_default="running", index=True),
        sa.Column("current_stage", sa.String(50), nullable=True),
        sa.Column("loop_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("artifacts", sa.JSON(), nullable=True),
        sa.Column("final_result", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("hitl_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("review_nodes", sa.JSON(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("supervisor_workflows")
