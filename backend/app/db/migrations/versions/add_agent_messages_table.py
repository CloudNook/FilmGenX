"""add agent_messages table

Revision ID: add_agent_messages_table
Revises: add_workspaces_table
Create Date: 2026-04-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_agent_messages_table"
down_revision: Union[str, None] = "add_workspaces_table"
branch_labels: Union[str, Sequence[str]] = None
depends_on: Union[str, Sequence[str]] = None


def upgrade() -> None:
    op.create_table(
        "agent_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(100), nullable=False),
        sa.Column("request_id", sa.String(100), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("tool_call_id", sa.String(100), nullable=True),
        sa.Column("tool_name", sa.String(100), nullable=True),
        sa.Column("extra_metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_messages_session_id", "agent_messages", ["session_id"])
    op.create_index("ix_agent_messages_request_id", "agent_messages", ["request_id"])
    op.create_index("ix_agent_messages_agent_name", "agent_messages", ["agent_name"])


def downgrade() -> None:
    op.drop_index("ix_agent_messages_agent_name", table_name="agent_messages")
    op.drop_index("ix_agent_messages_request_id", table_name="agent_messages")
    op.drop_index("ix_agent_messages_session_id", table_name="agent_messages")
    op.drop_table("agent_messages")
