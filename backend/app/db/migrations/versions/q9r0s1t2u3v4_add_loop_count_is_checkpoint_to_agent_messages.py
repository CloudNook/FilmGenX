"""add loop_count and is_checkpoint to agent_messages

Revision ID: q9r0s1t2u3v4
Revises: 26768d28b01c
Create Date: 2026-04-13

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "q9r0s1t2u3v4"
down_revision: Union[str, Sequence[str], None] = "26768d28b01c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_messages",
        sa.Column("loop_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "agent_messages",
        sa.Column("is_checkpoint", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("agent_messages", "is_checkpoint")
    op.drop_column("agent_messages", "loop_count")
