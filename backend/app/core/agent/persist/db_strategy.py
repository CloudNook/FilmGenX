"""
数据库持久化策略实现。

将 Agent 执行数据存储到 PostgreSQL。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import select

from app.core.agent.persist.base import PersistStrategy
from app.core.agent.persist.models import AgentMessageRecord, AgentSession

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class DBPersistStrategy(PersistStrategy):
    """
    数据库持久化策略。

    需要在构造时注入 db session。

    使用方式：
        strategy = DBPersistStrategy(db=db_session)
        agent = create_agent(..., persist=strategy)
    """

    name = "db"

    def __init__(self, db: "AsyncSession"):
        self.db = db

    async def save_session(
        self,
        session_id: str,
        request_id: str,
        agent_name: str,
        initial_input: str,
        started_at: datetime,
    ) -> None:
        session = AgentSession(
            session_id=session_id,
            request_id=request_id,
            agent_name=agent_name,
            initial_input=initial_input,
            loop_count=0,
            started_at=started_at,
        )
        self.db.add(session)
        await self.db.flush()

    async def append_message(
        self,
        session_id: str,
        request_id: str,
        agent_name: str,
        role: str,
        content: str,
        *,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
        seq: int = 0,
    ) -> None:
        record = AgentMessageRecord(
            session_id=session_id,
            request_id=request_id,
            agent_name=agent_name,
            role=role,
            content=content,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            extra_metadata=extra_metadata,
            seq=seq,
        )
        self.db.add(record)
        await self.db.flush()

    async def update_session(
        self,
        session_id: str,
        loop_count: int,
        schema_data: Optional[Dict[str, Any]],
        raw_output: Optional[str],
        error: Optional[str],
        finished: bool,
        finished_at: datetime,
    ) -> None:
        from sqlalchemy import update

        stmt = (
            update(AgentSession)
            .where(AgentSession.session_id == session_id)
            .values(
                loop_count=loop_count,
                schema_data=schema_data,
                raw_output=raw_output,
                error=error,
                finished=finished,
                finished_at=finished_at,
            )
        )
        await self.db.execute(stmt)

    async def load_messages(
        self,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(AgentMessageRecord)
            .where(AgentMessageRecord.session_id == session_id)
            .order_by(AgentMessageRecord.seq)
        )
        rows = await self.db.execute(stmt)
        records = rows.scalars().all()

        return [
            {
                "role": r.role,
                "content": r.content,
                "agent_name": r.agent_name,
                "tool_call_id": r.tool_call_id,
                "tool_name": r.tool_name,
                "metadata": r.extra_metadata or {},
                "seq": r.seq,
            }
            for r in records
        ]

    async def load_session(
        self,
        session_id: str,
    ) -> Optional[Dict[str, Any]]:
        stmt = (
            select(AgentSession)
            .where(AgentSession.session_id == session_id)
            .limit(1)
        )
        row = await self.db.execute(stmt)
        record = row.scalar_one_or_none()
        if record is None:
            return None

        return {
            "session_id": record.session_id,
            "request_id": record.request_id,
            "agent_name": record.agent_name,
            "initial_input": record.initial_input,
            "loop_count": record.loop_count,
            "schema_data": record.schema_data,
            "raw_output": record.raw_output,
            "error": record.error,
            "finished": record.finished,
            "started_at": record.started_at.isoformat() if record.started_at else None,
            "finished_at": record.finished_at.isoformat() if record.finished_at else None,
        }
