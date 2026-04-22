"""
Supervisor 结构化事件表。

用于持久化 supervisor runtime 自己的时间线事件，避免把产品层事件混进
agent_messages。保留常用索引字段，详细事件载荷单独存储在 payload 中。
"""

from typing import Any, Dict, Optional

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SupervisorEvent(Base):
    """Supervisor 时间线事件。"""

    __tablename__ = "supervisor_events"

    supervisor_session_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Supervisor 会话 ID",
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="事件类型，如 supervisor_started / interrupt / supervisor_done",
    )
    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="supervisor",
        server_default="supervisor",
        comment="事件来源，如 supervisor / 某个 sub-agent 名称",
    )
    source_session_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="事件所属的子会话 ID",
    )
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="事件的完整结构化载荷",
    )

    def to_payload(self) -> Dict[str, Any]:
        """返回事件对外协议使用的 payload。"""
        return dict(self.payload or {})
