"""add supervisor_session_id to agent_messages

Revision ID: s1t2u3v4w5x6
Revises: r0s1t2u3v4w5
Create Date: 2026-04-15

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "s1t2u3v4w5x6"
down_revision: Union[str, Sequence[str], None] = "r0s1t2u3v4w5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_messages",
        sa.Column(
            "supervisor_session_id",
            sa.String(100),
            nullable=True,
            comment="Supervisor 会话 ID（用于跨 SubAgent 追溯）",
        ),
    )
    op.create_index(
        "ix_agent_messages_supervisor_session_id",
        "agent_messages",
        ["supervisor_session_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_messages_supervisor_session_id", table_name="agent_messages")
    op.drop_column("agent_messages", "supervisor_session_id")
