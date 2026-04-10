"""
持久化数据模型。

仅包含 SQLAlchemy 表模型定义，不包含业务逻辑。
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentSession(Base):
    """
    Agent 会话表。

    记录一次 Agent 执行的所有元信息。
    """

    __tablename__ = "agent_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="会话 ID（多轮对话，唯一）",
    )
    agent_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Agent 名称",
    )
    request_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="请求 ID（单次执行）",
    )
    config: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Agent 配置快照",
    )
    initial_input: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="初始输入",
    )
    loop_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="循环次数",
    )
    schema_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="结构化输出数据",
    )
    raw_output: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="原始输出",
    )
    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="错误信息",
    )
    finished: Mapped[bool] = mapped_column(
        Integer,
        nullable=False,
        default=False,
        comment="是否正常结束（0/1）",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now(timezone.utc),
        comment="开始时间",
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="结束时间",
    )


class AgentMessageRecord(Base):
    """
    Agent 消息表。

    记录 Agent 执行过程中的每一条消息。
    """

    __tablename__ = "agent_messages"

    session_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("agent_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属会话 ID（关联 agent_sessions.session_id）",
    )
    request_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="所属请求 ID",
    )
    agent_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Agent 名称",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="user | assistant | system | tool",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="消息内容",
    )
    tool_call_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="工具调用 ID",
    )
    tool_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="调用的工具名称",
    )
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="附加元数据",
    )
    seq: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="消息序号",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now(timezone.utc),
        comment="创建时间",
    )
