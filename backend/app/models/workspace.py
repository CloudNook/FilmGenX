"""
AI 工作台模型。

一个 Workspace 对应一个 Agent 会话：
  - session_id 映射到 agent_messages 表，复用 Agent persist 系统
  - 不需要独立的 messages 表
  - 为未来多 Agent 预留 agent_name 字段
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


class Workspace(Base):
    """AI 工作台表。"""

    __tablename__ = "workspaces"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目",
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="新工作台",
        comment="工作台标题",
    )
    agent_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="general",
        comment="Agent 名称",
    )
    session_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Agent persist session_id，映射到 agent_messages 表",
    )
    system_prompt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="自定义 system prompt，NULL 使用默认 prompt",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        comment="active | archived",
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="累计消耗 token 数",
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后一条消息时间",
    )
    model: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="gemini-3-flash-preview",
        server_default="gemini-3-flash-preview",
        comment="使用的 LLM 模型",
    )
    temperature: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.7,
        server_default="0.7",
        comment="LLM temperature",
    )
    hitl_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="是否启用 human-in-the-loop",
    )
    review_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="是否启用 review agent",
    )
    memory_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="是否启用项目级 memory（按 project_id 作为 domain_id）",
    )

    # Relations
    project: Mapped["Project"] = relationship("Project", back_populates="workspaces")
