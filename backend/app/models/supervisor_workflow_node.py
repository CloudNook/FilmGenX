"""Structured supervisor workflow node persistence models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.supervisor_workflow import SupervisorWorkflow


class SupervisorWorkflowNode(Base):
    """Persisted workflow node state for a supervisor workflow run."""

    __tablename__ = "supervisor_workflow_nodes"
    __table_args__ = (
        UniqueConstraint(
            "workflow_id",
            "node_key",
            name="uq_supervisor_workflow_nodes_workflow_id_node_key",
        ),
    )

    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("supervisor_workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属 supervisor workflow ID",
    )
    node_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="节点唯一 key",
    )
    label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="节点展示名称",
    )
    node_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="节点类型，如 text / plan",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="missing",
        server_default="missing",
        comment="节点状态",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="节点版本号",
    )
    produces_artifact: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="是否产出 artifact",
    )
    can_run_automatically: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="是否允许自动执行",
    )
    artifact_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="节点当前产出文本",
    )
    updated_by: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="最近更新来源，如 user / agent",
    )
    last_agent: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="最近写入该节点的 agent",
    )
    node_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="节点业务更新时间",
    )

    workflow: Mapped["SupervisorWorkflow"] = relationship(
        "SupervisorWorkflow",
        back_populates="nodes",
    )


class SupervisorWorkflowNodeDependency(Base):
    """Persisted workflow dependency edges for a supervisor workflow run."""

    __tablename__ = "supervisor_workflow_node_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "workflow_id",
            "node_key",
            "depends_on_key",
            name="uq_supervisor_workflow_node_dependencies_edge",
        ),
    )

    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("supervisor_workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属 supervisor workflow ID",
    )
    node_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="当前节点 key",
    )
    depends_on_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="依赖的上游节点 key",
    )

    workflow: Mapped["SupervisorWorkflow"] = relationship(
        "SupervisorWorkflow",
        back_populates="dependencies",
    )
