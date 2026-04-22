"""
Supervisor Workflow 流水线记录表。

存储每次 Supervisor 流水线的执行元数据：
  - 关联项目 / 用户
  - supervisor_session_id（映射到 SupervisorContext）
  - 结构化 workflow 状态（节点 / 依赖单独建模）
  - 执行状态和统计
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import Project
    from app.models.supervisor_workflow_node import (
        SupervisorWorkflowNode,
        SupervisorWorkflowNodeDependency,
    )


class SupervisorWorkflow(Base):
    """
    Supervisor 流水线执行记录。

    每发起一次 /api/v1/supervisor/stream 产生一条记录，
    流水线结束后更新 status / final_result；
    工作流节点状态由结构化子表持久化。
    """

    __tablename__ = "supervisor_workflows"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目",
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="发起用户（用于权限校验）",
    )
    supervisor_session_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Supervisor 会话 ID（sv- 前缀），映射到 SupervisorContext",
    )
    user_request: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="用户原始需求",
    )
    model: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="gemini-3-flash-preview",
        comment="使用的 LLM 模型",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="running",
        index=True,
        comment="running | completed | failed",
    )
    workflow_profile: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="default",
        server_default="default",
        comment="工作流配置名称",
    )
    auto_run: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="是否按建议自动继续执行",
    )
    active_node_key: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="当前活跃节点 key",
    )
    loop_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="实际循环次数",
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="累计消耗 token 数",
    )
    final_result: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Supervisor 最终总结文本",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="执行出错时的错误信息",
    )
    hitl_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Whether HITL is enabled for this run",
    )
    review_nodes: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment="Configured review node names for HITL",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="流水线完成时间",
    )

    # Relations
    project: Mapped["Project"] = relationship("Project", back_populates="supervisor_workflows")
    owner: Mapped["User"] = relationship("User")
    nodes: Mapped[List["SupervisorWorkflowNode"]] = relationship(
        "SupervisorWorkflowNode",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )
    dependencies: Mapped[List["SupervisorWorkflowNodeDependency"]] = relationship(
        "SupervisorWorkflowNodeDependency",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )
