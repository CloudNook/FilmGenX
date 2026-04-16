"""drop legacy agent_interrupt_state table

Revision ID: w6x7y8z9a0b
Revises: v5w6x7y8z9a
Create Date: 2026-04-16

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "w6x7y8z9a0b"
down_revision: Union[str, Sequence[str], None] = "v5w6x7y8z9a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "agent_interrupt_state" in inspector.get_table_names():
        op.drop_table("agent_interrupt_state")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "agent_interrupt_state" not in inspector.get_table_names():
        op.create_table(
            "agent_interrupt_state",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("session_id", sa.String(100), nullable=False, unique=True, index=True),
            sa.Column("tool_call_id", sa.String(100), nullable=False),
            sa.Column("tool_name", sa.String(100), nullable=False),
            sa.Column("context", sa.JSON(), nullable=True),
            sa.Column("available_actions", sa.JSON(), nullable=True),
            sa.Column("loop_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
