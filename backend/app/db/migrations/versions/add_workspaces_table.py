"""add workspaces table

Revision ID: add_workspaces_table
Revises: -
Create Date: 2026-04-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_workspaces_table"
down_revision: Union[str, None] = "add_skills_table"
branch_labels: Union[str, Sequence[str]] = None
depends_on: Union[str, Sequence[str]] = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False, server_default="新工作台"),
        sa.Column("agent_name", sa.String(100), nullable=False, server_default="general"),
        sa.Column("session_id", sa.String(100), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_workspaces_project_id", "workspaces", ["project_id"])
    op.create_index(
        "ix_workspaces_session_id", "workspaces", ["session_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_workspaces_session_id", table_name="workspaces")
    op.drop_index("ix_workspaces_project_id", table_name="workspaces")
    op.drop_table("workspaces")
