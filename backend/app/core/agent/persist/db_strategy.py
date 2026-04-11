"""
数据库持久化策略实现。

将 Agent 消息写入 PostgreSQL（agent_messages 表）。
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import select

from app.core.agent.persist.base import PersistStrategy
from app.core.agent.persist.models import AgentMessageRecord

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


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
                "tool_call_id": r.tool_call_id,
                "tool_name": r.tool_name,
                "metadata": r.extra_metadata or {},
                "seq": r.seq,
            }
            for r in records
        ]

    async def append_message(
        self,
        session_id: str,
        request_id: str,
        agent_name: str,
        role: str,
        content: str,
        seq: int,
        *,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        写入一条消息（不自动 commit）。

        注意：事务管理由调用方负责。
        需要手动调用 flush() 或自行 commit() 以确保写入生效。
        """
        record = AgentMessageRecord(
            session_id=session_id,
            request_id=request_id,
            agent_name=agent_name,
            role=role,
            content=content,
            seq=seq,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            extra_metadata=metadata,
        )
        self.db.add(record)

    async def flush(self) -> None:
        """提交当前事务。"""
        await self.db.commit()
