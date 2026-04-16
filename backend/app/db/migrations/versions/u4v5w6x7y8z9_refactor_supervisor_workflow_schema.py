"""refactor supervisor_workflows to workflow-first schema

Revision ID: u4v5w6x7y8z9
Revises: s1t2u3v4w5x6
Create Date: 2026-04-16

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "u4v5w6x7y8z9"
down_revision: Union[str, Sequence[str], None] = "s1t2u3v4w5x6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("supervisor_workflows") as batch_op:
        batch_op.alter_column(
            "current_stage",
            existing_type=sa.String(length=50),
            new_column_name="active_node_key",
            existing_nullable=True,
        )
        batch_op.alter_column(
            "artifacts",
            existing_type=sa.JSON(),
            new_column_name="workflow_snapshot",
            existing_nullable=True,
        )
        batch_op.add_column(
            sa.Column(
                "workflow_profile",
                sa.String(length=100),
                nullable=False,
                server_default="default",
                comment="工作流配置名称",
            )
        )
        batch_op.add_column(
            sa.Column(
                "auto_run",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
                comment="是否按建议自动继续执行",
            )
        )

    op.execute(
        """
        UPDATE supervisor_workflows
        SET active_node_key = CASE active_node_key
            WHEN 'outline_writer' THEN 'outline'
            WHEN 'script_writer' THEN 'script'
            WHEN 'storyboarder' THEN 'storyboard'
            ELSE active_node_key
        END
        """
    )
    op.execute(
        """
        UPDATE supervisor_workflows
        SET workflow_snapshot = CASE
            WHEN workflow_snapshot IS NULL THEN NULL
            WHEN jsonb_typeof(workflow_snapshot::jsonb) = 'object'
                AND workflow_snapshot::jsonb ? 'workflow'
                THEN (workflow_snapshot::jsonb -> 'workflow')::json
            ELSE workflow_snapshot
        END
        """
    )
    op.execute(
        """
        UPDATE supervisor_workflows
        SET workflow_profile = COALESCE(
            NULLIF(workflow_snapshot::jsonb ->> 'profile', ''),
            'default'
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE supervisor_workflows
        SET active_node_key = CASE active_node_key
            WHEN 'outline' THEN 'outline_writer'
            WHEN 'script' THEN 'script_writer'
            WHEN 'storyboard' THEN 'storyboarder'
            ELSE active_node_key
        END
        """
    )
    op.execute(
        """
        UPDATE supervisor_workflows
        SET workflow_snapshot = CASE
            WHEN workflow_snapshot IS NULL THEN NULL
            ELSE json_build_object('workflow', workflow_snapshot)::json
        END
        """
    )

    with op.batch_alter_table("supervisor_workflows") as batch_op:
        batch_op.drop_column("auto_run")
        batch_op.drop_column("workflow_profile")
        batch_op.alter_column(
            "active_node_key",
            existing_type=sa.String(length=100),
            new_column_name="current_stage",
            existing_nullable=True,
        )
        batch_op.alter_column(
            "workflow_snapshot",
            existing_type=sa.JSON(),
            new_column_name="artifacts",
            existing_nullable=True,
        )
