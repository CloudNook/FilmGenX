"""add usage column to agent_messages

Revision ID: add_usage_to_agent_messages
Revises: add_agent_messages_table
Create Date: 2026-04-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_usage_to_agent_messages"
down_revision: Union[str, None] = "add_agent_messages_table"
branch_labels: Union[str, Sequence[str]] = None
depends_on: Union[str, Sequence[str]] = None


def upgrade() -> None:
    op.add_column(
        "agent_messages",
        sa.Column(
            "usage",
            sa.JSON(),
            nullable=True,
            comment="LLM token 用量，仅 assistant 消息填充",
        ),
    )


def downgrade() -> None:
    op.drop_column("agent_messages", "usage")
