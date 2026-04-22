"""create supervisor events table

Revision ID: x1y2z3a4b5c6
Revises: w6x7y8z9a0b
Create Date: 2026-04-21

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "x1y2z3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "w6x7y8z9a0b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "supervisor_events",
        sa.Column("supervisor_session_id", sa.String(length=100), nullable=False, comment="Supervisor 会话 ID"),
        sa.Column("event_type", sa.String(length=50), nullable=False, comment="事件类型，如 supervisor_started / interrupt / supervisor_done"),
        sa.Column("source", sa.String(length=100), nullable=False, server_default="supervisor", comment="事件来源，如 supervisor / 某个 sub-agent 名称"),
        sa.Column("source_session_id", sa.String(length=100), nullable=True, comment="事件所属的子会话 ID"),
        sa.Column("payload", sa.JSON(), nullable=False, comment="事件的完整结构化载荷"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键，自增整数"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="记录创建时间（UTC）"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="记录最后更新时间（UTC），每次 UPDATE 自动刷新"),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="软删除标记。True 表示已删除，业务查询必须过滤此字段"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间（UTC），is_deleted 为 True 时记录"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_supervisor_events_event_type"), "supervisor_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_supervisor_events_is_deleted"), "supervisor_events", ["is_deleted"], unique=False)
    op.create_index(op.f("ix_supervisor_events_source_session_id"), "supervisor_events", ["source_session_id"], unique=False)
    op.create_index(op.f("ix_supervisor_events_supervisor_session_id"), "supervisor_events", ["supervisor_session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_supervisor_events_supervisor_session_id"), table_name="supervisor_events")
    op.drop_index(op.f("ix_supervisor_events_source_session_id"), table_name="supervisor_events")
    op.drop_index(op.f("ix_supervisor_events_is_deleted"), table_name="supervisor_events")
    op.drop_index(op.f("ix_supervisor_events_event_type"), table_name="supervisor_events")
    op.drop_table("supervisor_events")
