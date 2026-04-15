"""
数据库持久化策略实现。

将 Agent 消息写入 PostgreSQL（agent_messages 表）。
中断状态通过 is_checkpoint=True 的 assistant 消息记录，
中断信息存在该消息的 extra_metadata 里，不需要单独的中断状态表。
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import select, update

from app.core.agent.persist.base import PersistStrategy
from app.core.agent.persist.models import AgentMessageRecord

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.agent.base import AgentCheckpoint


class DBPersistStrategy(PersistStrategy):
    """
    数据库持久化策略。

    需在构造时注入 AsyncSession，生命周期由调用方管理。

    使用方式：
        agent = create_agent(..., persist=DBPersistStrategy(db=session))
    """

    name = "db"

    def __init__(self, db: "AsyncSession"):
        self.db = db

    async def load_messages(
        self,
        session_id: str,
    ) -> List[AgentMessageRecord]:
        stmt = (
            select(AgentMessageRecord)
            .where(AgentMessageRecord.session_id == session_id)
            .order_by(AgentMessageRecord.seq)
        )
        rows = await self.db.execute(stmt)
        return list(rows.scalars().all())

    async def append_message(
        self,
        session_id: str,
        request_id: str,
        agent_name: str,
        role: str,
        content: str,
        seq: int,
        loop_count: int = 0,
        *,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        usage: Optional[Dict[str, Any]] = None,
        supervisor_session_id: Optional[str] = None,
        is_checkpoint: bool = False,
    ) -> None:
        record = AgentMessageRecord(
            session_id=session_id,
            request_id=request_id,
            agent_name=agent_name,
            role=role,
            content=content,
            seq=seq,
            loop_count=loop_count,
            is_checkpoint=is_checkpoint,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            extra_metadata=metadata,
            usage=usage,
            supervisor_session_id=supervisor_session_id,
        )
        self.db.add(record)
        await self.db.commit()

    # ------------------------------------------------------------------
    # 中断状态：通过 is_checkpoint=True 的 assistant 消息管理
    # ------------------------------------------------------------------

    async def save_interrupt_state(
        self,
        session_id: str,
        checkpoint: "AgentCheckpoint",
    ) -> None:
        """
        将中断信息写入最近一条 is_checkpoint=True 的 assistant 消息的 extra_metadata。

        extra_metadata 结构（新增字段）：
          interrupt: {tool_call_id, tool_name, context, available_actions, loop_count}
        """
        # 找到最近一条 checkpoint 记录
        stmt = (
            select(AgentMessageRecord)
            .where(
                AgentMessageRecord.session_id == session_id,
                AgentMessageRecord.role == "assistant",
                AgentMessageRecord.is_checkpoint == True,
            )
            .order_by(AgentMessageRecord.seq.desc())
            .limit(1)
        )
        rows = await self.db.execute(stmt)
        record = rows.scalar_one_or_none()
        if record is None:
            return

        # 读取现有 extra_metadata，追加 interrupt 信息
        await self.db.refresh(record, ["extra_metadata"])
        meta = dict(record.extra_metadata or {})
        meta["interrupt"] = {
            "tool_call_id": checkpoint.tool_call_id,
            "tool_name": checkpoint.tool_name,
            "arguments": checkpoint.arguments,
            "context": checkpoint.context,
            "available_actions": checkpoint.available_actions,
            "loop_count": checkpoint.loop_count,
        }

        await self.db.execute(
            update(AgentMessageRecord)
            .where(AgentMessageRecord.id == record.id)
            .values(extra_metadata=meta)
        )
        await self.db.commit()

    async def load_interrupt_state(
        self,
        session_id: str,
    ) -> "Optional[AgentCheckpoint]":
        """
        从最近一条 is_checkpoint=True 的 assistant 消息读取中断信息。
        """
        from app.core.agent.base import AgentCheckpoint

        stmt = (
            select(AgentMessageRecord.extra_metadata)
            .where(
                AgentMessageRecord.session_id == session_id,
                AgentMessageRecord.role == "assistant",
                AgentMessageRecord.is_checkpoint == True,
            )
            .order_by(AgentMessageRecord.seq.desc())
            .limit(1)
        )
        rows = await self.db.execute(stmt)
        row = rows.scalar_one_or_none()
        if row is None:
            return None

        meta = row or {}
        intr = meta.get("interrupt") if isinstance(meta, dict) else None
        if intr is None:
            return None

        return AgentCheckpoint(
            tool_call_id=intr["tool_call_id"],
            tool_name=intr["tool_name"],
            arguments=intr.get("arguments", {}),
            context=intr.get("context", {}),
            available_actions=intr.get(
                "available_actions", ["approve", "reject"]
            ),
            messages=[],
            loop_count=intr.get("loop_count", 0),
        )

    async def clear_interrupt_state(self, session_id: str) -> None:
        """
        清除 checkpoint 标记和 extra_metadata 中的 interrupt 信息。
        """
        stmt = (
            select(AgentMessageRecord.id, AgentMessageRecord.extra_metadata)
            .where(
                AgentMessageRecord.session_id == session_id,
                AgentMessageRecord.role == "assistant",
                AgentMessageRecord.is_checkpoint == True,
            )
            .order_by(AgentMessageRecord.seq.desc())
            .limit(1)
        )
        rows = await self.db.execute(stmt)
        row = rows.first()
        if row is None:
            return

        record_id, extra = row
        meta = dict(extra or {})
        meta.pop("interrupt", None)

        await self.db.execute(
            update(AgentMessageRecord)
            .where(AgentMessageRecord.id == record_id)
            .values(is_checkpoint=False, extra_metadata=meta if meta else None)
        )
        await self.db.commit()
