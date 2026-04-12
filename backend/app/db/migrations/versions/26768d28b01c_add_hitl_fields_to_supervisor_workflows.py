"""add hitl_enabled and review_nodes to supervisor_workflows

Revision ID: 26768d28b01c
Revises: add_usage_to_agent_messages
Create Date: 2026-04-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26768d28b01c'
down_revision: Union[str, Sequence[str], None] = 'add_usage_to_agent_messages'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "supervisor_workflows",
        sa.Column("hitl_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "supervisor_workflows",
        sa.Column("review_nodes", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("supervisor_workflows", "review_nodes")
    op.drop_column("supervisor_workflows", "hitl_enabled")
