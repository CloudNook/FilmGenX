"""add missing Base columns to supervisor_workflows

Revision ID: v5w6x7y8z9a
Revises: u4v5w6x7y8z9
Create Date: 2026-04-16

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "v5w6x7y8z9a"
down_revision: Union[str, Sequence[str], None] = "u4v5w6x7y8z9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {
        column["name"] for column in inspector.get_columns("supervisor_workflows")
    }
    existing_indexes = {
        index["name"] for index in inspector.get_indexes("supervisor_workflows")
    }

    with op.batch_alter_table("supervisor_workflows") as batch_op:
        if "created_at" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.text("now()"),
                    comment="记录创建时间（UTC）",
                )
            )
        if "updated_at" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.text("now()"),
                    comment="记录最后更新时间（UTC）",
                )
            )
        if "is_deleted" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "is_deleted",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("false"),
                    comment="软删除标记。True 表示已删除，业务查询必须过滤此字段",
                )
            )
        if "deleted_at" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "deleted_at",
                    sa.DateTime(timezone=True),
                    nullable=True,
                    comment="软删除时间（UTC），is_deleted 为 True 时记录",
                )
            )

    if "ix_supervisor_workflows_is_deleted" not in existing_indexes:
        op.create_index(
            "ix_supervisor_workflows_is_deleted",
            "supervisor_workflows",
            ["is_deleted"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {
        column["name"] for column in inspector.get_columns("supervisor_workflows")
    }
    existing_indexes = {
        index["name"] for index in inspector.get_indexes("supervisor_workflows")
    }

    if "ix_supervisor_workflows_is_deleted" in existing_indexes:
        op.drop_index("ix_supervisor_workflows_is_deleted", table_name="supervisor_workflows")

    with op.batch_alter_table("supervisor_workflows") as batch_op:
        if "deleted_at" in existing_columns:
            batch_op.drop_column("deleted_at")
        if "is_deleted" in existing_columns:
            batch_op.drop_column("is_deleted")
        if "updated_at" in existing_columns:
            batch_op.drop_column("updated_at")
        if "created_at" in existing_columns:
            batch_op.drop_column("created_at")
