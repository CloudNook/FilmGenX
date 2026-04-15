"""
持久化数据模型。

只保留消息表，session 元信息由调用方业务表管理。
中断状态通过 is_checkpoint=True 的 assistant 消息记录，不需要单独的中断状态表。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


@dataclass
class MessageRecord:
    """
    消息记录的轻量数据类。

    供 Redis 等非 ORM 持久化策略构造，确保 AgentLoop 可用统一字段访问。
    DBPersistStrategy 直接返回 AgentMessageRecord（ORM），字段完全兼容。
    """
    role: str
    content: str
    seq: int
    loop_count: int = 0
    is_checkpoint: bool = False
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    extra_metadata: Optional[Dict[str, Any]] = field(default=None)
    supervisor_session_id: Optional[str] = None


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
    usage: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="LLM token 用量，仅 assistant 消息填充",
    )
    loop_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="消息写入时的 loop 计数",
    )
    is_checkpoint: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="该消息是否为中断检查点",
    )
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    supervisor_session_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Supervisor 会话 ID（用于跨 SubAgent 追溯）",
    )
