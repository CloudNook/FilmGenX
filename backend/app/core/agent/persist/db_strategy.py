"""Database-backed agent persistence."""

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, update

from app.core.agent.persist.base import PersistStrategy
from app.core.agent.persist.models import AgentMessageRecord

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.agent.base import AgentCheckpoint


class DBPersistStrategy(PersistStrategy):
    """Persist agent messages and interrupt checkpoints in the database."""

    name = "db"

    def __init__(
        self,
        db: "AsyncSession | None" = None,
        *,
        session_factory: "Callable[[], Any] | None" = None,
        supervisor_session_id: Optional[str] = None,
    ):
        if db is None and session_factory is None:
            raise ValueError("DBPersistStrategy requires db or session_factory")
        self.db = db
        self.session_factory = session_factory
        self.default_supervisor_session_id = supervisor_session_id

    @asynccontextmanager
    async def _session_scope(self):
        if self.db is not None:
            yield self.db
            return

        async with self.session_factory() as db:
            yield db

    async def load_messages(
        self,
        session_id: str,
    ) -> List[AgentMessageRecord]:
        async with self._session_scope() as db:
            stmt = (
                select(AgentMessageRecord)
                .where(AgentMessageRecord.session_id == session_id)
                .order_by(AgentMessageRecord.seq)
            )
            rows = await db.execute(stmt)
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
        resolved_supervisor_session_id = (
            supervisor_session_id or self.default_supervisor_session_id
        )
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
            extra_metadata=jsonable_encoder(metadata) if metadata is not None else None,
            usage=jsonable_encoder(usage) if usage is not None else None,
            supervisor_session_id=resolved_supervisor_session_id,
        )

        async with self._session_scope() as db:
            db.add(record)
            await db.commit()

    async def save_interrupt_state(
        self,
        session_id: str,
        checkpoint: "AgentCheckpoint",
    ) -> None:
        async with self._session_scope() as db:
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
            rows = await db.execute(stmt)
            record = rows.scalar_one_or_none()
            if record is None:
                return

            await db.refresh(record, ["extra_metadata"])
            meta = dict(record.extra_metadata or {})
            meta["interrupt"] = {
                "tool_call_id": checkpoint.tool_call_id,
                "tool_name": checkpoint.tool_name,
                "arguments": checkpoint.arguments,
                "context": checkpoint.context,
                "available_actions": checkpoint.available_actions,
                "loop_count": checkpoint.loop_count,
            }

            await db.execute(
                update(AgentMessageRecord)
                .where(AgentMessageRecord.id == record.id)
                .values(extra_metadata=meta)
            )
            await db.commit()

    async def load_interrupt_state(
        self,
        session_id: str,
    ) -> "Optional[AgentCheckpoint]":
        from app.core.agent.base import AgentCheckpoint

        async with self._session_scope() as db:
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
            rows = await db.execute(stmt)
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
        async with self._session_scope() as db:
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
            rows = await db.execute(stmt)
            row = rows.first()
            if row is None:
                return

            record_id, extra = row
            meta = dict(extra or {})
            meta.pop("interrupt", None)

            await db.execute(
                update(AgentMessageRecord)
                .where(AgentMessageRecord.id == record_id)
                .values(is_checkpoint=False, extra_metadata=meta if meta else None)
            )
            await db.commit()
