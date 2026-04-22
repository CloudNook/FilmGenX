"""normalize supervisor workflow state

Revision ID: y2z3a4b5c6d7
Revises: x1y2z3a4b5c6
Create Date: 2026-04-21

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "y2z3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "x1y2z3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "supervisor_workflow_nodes",
        sa.Column("workflow_id", sa.Integer(), nullable=False, comment="所属 supervisor workflow ID"),
        sa.Column("node_key", sa.String(length=100), nullable=False, comment="节点唯一 key"),
        sa.Column("label", sa.String(length=100), nullable=False, comment="节点展示名称"),
        sa.Column("node_type", sa.String(length=50), nullable=False, comment="节点类型，如 text / plan"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="missing", comment="节点状态"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0", comment="节点版本号"),
        sa.Column("produces_artifact", sa.Boolean(), nullable=False, server_default="true", comment="是否产出 artifact"),
        sa.Column("can_run_automatically", sa.Boolean(), nullable=False, server_default="true", comment="是否允许自动执行"),
        sa.Column("artifact_content", sa.Text(), nullable=True, comment="节点当前产出文本"),
        sa.Column("updated_by", sa.String(length=50), nullable=True, comment="最近更新来源，如 user / agent"),
        sa.Column("last_agent", sa.String(length=100), nullable=True, comment="最近写入该节点的 agent"),
        sa.Column("node_updated_at", sa.DateTime(timezone=True), nullable=True, comment="节点业务更新时间"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键，自增整数"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="记录创建时间（UTC）"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="记录最后更新时间（UTC），每次 UPDATE 自动刷新"),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="软删除标记。True 表示已删除，业务查询必须过滤此字段"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间（UTC），is_deleted 为 True 时记录"),
        sa.ForeignKeyConstraint(["workflow_id"], ["supervisor_workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_id", "node_key", name="uq_supervisor_workflow_nodes_workflow_id_node_key"),
    )
    op.create_index(op.f("ix_supervisor_workflow_nodes_is_deleted"), "supervisor_workflow_nodes", ["is_deleted"], unique=False)
    op.create_index(op.f("ix_supervisor_workflow_nodes_node_key"), "supervisor_workflow_nodes", ["node_key"], unique=False)
    op.create_index(op.f("ix_supervisor_workflow_nodes_workflow_id"), "supervisor_workflow_nodes", ["workflow_id"], unique=False)

    op.create_table(
        "supervisor_workflow_node_dependencies",
        sa.Column("workflow_id", sa.Integer(), nullable=False, comment="所属 supervisor workflow ID"),
        sa.Column("node_key", sa.String(length=100), nullable=False, comment="当前节点 key"),
        sa.Column("depends_on_key", sa.String(length=100), nullable=False, comment="依赖的上游节点 key"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键，自增整数"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="记录创建时间（UTC）"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="记录最后更新时间（UTC），每次 UPDATE 自动刷新"),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="软删除标记。True 表示已删除，业务查询必须过滤此字段"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间（UTC），is_deleted 为 True 时记录"),
        sa.ForeignKeyConstraint(["workflow_id"], ["supervisor_workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_id", "node_key", "depends_on_key", name="uq_supervisor_workflow_node_dependencies_edge"),
    )
    op.create_index(op.f("ix_supervisor_workflow_node_dependencies_depends_on_key"), "supervisor_workflow_node_dependencies", ["depends_on_key"], unique=False)
    op.create_index(op.f("ix_supervisor_workflow_node_dependencies_is_deleted"), "supervisor_workflow_node_dependencies", ["is_deleted"], unique=False)
    op.create_index(op.f("ix_supervisor_workflow_node_dependencies_node_key"), "supervisor_workflow_node_dependencies", ["node_key"], unique=False)
    op.create_index(op.f("ix_supervisor_workflow_node_dependencies_workflow_id"), "supervisor_workflow_node_dependencies", ["workflow_id"], unique=False)

    with op.batch_alter_table("supervisor_workflows") as batch_op:
        batch_op.drop_column("workflow_snapshot")


def downgrade() -> None:
    with op.batch_alter_table("supervisor_workflows") as batch_op:
        batch_op.add_column(
            sa.Column(
                "workflow_snapshot",
                sa.JSON(),
                nullable=True,
                comment="版本化 workflow 快照",
            )
        )

    op.drop_index(op.f("ix_supervisor_workflow_node_dependencies_workflow_id"), table_name="supervisor_workflow_node_dependencies")
    op.drop_index(op.f("ix_supervisor_workflow_node_dependencies_node_key"), table_name="supervisor_workflow_node_dependencies")
    op.drop_index(op.f("ix_supervisor_workflow_node_dependencies_is_deleted"), table_name="supervisor_workflow_node_dependencies")
    op.drop_index(op.f("ix_supervisor_workflow_node_dependencies_depends_on_key"), table_name="supervisor_workflow_node_dependencies")
    op.drop_table("supervisor_workflow_node_dependencies")

    op.drop_index(op.f("ix_supervisor_workflow_nodes_workflow_id"), table_name="supervisor_workflow_nodes")
    op.drop_index(op.f("ix_supervisor_workflow_nodes_node_key"), table_name="supervisor_workflow_nodes")
    op.drop_index(op.f("ix_supervisor_workflow_nodes_is_deleted"), table_name="supervisor_workflow_nodes")
    op.drop_table("supervisor_workflow_nodes")
