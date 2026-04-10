"""
持久化数据模型。

只保留消息表，session 元信息由调用方业务表管理。
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentMessageRecord(Base):
    """
    Agent 消息表。

    记录 Agent 执行过程中的每一条消息，按 session_id + seq 排序还原历史。
    session_id 由外部业务传入，与业务表关联关系由调用方管理。
    """

    __tablename__ = "agent_messages"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="会话 ID，对应业务侧的多轮对话标识",
    )
    request_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="单次执行 ID",
    )
    agent_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="user | assistant | tool",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    seq: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="消息全局序号，session 内单调递增",
    )
    tool_call_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    tool_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
