"""Supervisor read-side queries owned by the framework core."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent.persist.db_strategy import DBPersistStrategy
from app.core.supervisor.errors import (
    SupervisorInvalidStateError,
    SupervisorSessionNotFoundError,
)
from app.core.supervisor.persist import SupervisorWorkflowStore


@dataclass
class SupervisorWorkflowDetailRecord:
    workflow: Any
    workflow_snapshot: dict | None
    event_history: list[dict]
    last_usage: dict | None = None


@dataclass
class SupervisorInterruptStateRecord:
    status: str
    interrupt: dict | None
    workflow: dict | None


class SupervisorQuery:
    """Thin read-model facade for supervisor workflow pages and detail views."""

    def __init__(self, db: AsyncSession) -> None:
        self.workflow_store = SupervisorWorkflowStore(db)

    async def list_workflows(
        self,
        *,
        project_id: int,
        owner_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Any], int]:
        return await self.workflow_store.list_workflows(
            project_id=project_id,
            owner_id=owner_id,
            page=page,
            page_size=page_size,
        )

    async def get_workflow_detail(
        self,
        *,
        workflow_id: int,
        project_id: int,
        owner_id: int,
    ) -> Optional[SupervisorWorkflowDetailRecord]:
        workflow = await self.workflow_store.get_workflow(
            workflow_id=workflow_id,
            project_id=project_id,
            owner_id=owner_id,
        )
        if workflow is None:
            return None

        workflow_state = await self.workflow_store.load_workflow_state(workflow)
        event_history = await self.workflow_store.load_event_history(
            workflow.supervisor_session_id
        )
        last_usage = await self._fetch_last_assistant_usage(
            workflow.supervisor_session_id
        )
        return SupervisorWorkflowDetailRecord(
            workflow=workflow,
            workflow_snapshot=(
                workflow_state.model_dump() if workflow_state is not None else None
            ),
            event_history=event_history,
            last_usage=last_usage,
        )

    async def _fetch_last_assistant_usage(
        self, supervisor_session_id: str
    ) -> Optional[dict]:
        """从 agent_messages 表里捞 supervisor session 最后一条 assistant 消息的
        ``extra_metadata.accumulated_usage``。给前端 hydrate "上次 token" 用——
        历史 run 打开时也能立刻看到累计 usage。"""
        from sqlalchemy import select

        from app.core.agent.persist.models import AgentMessageRecord

        stmt = (
            select(AgentMessageRecord.extra_metadata)
            .where(
                AgentMessageRecord.session_id == supervisor_session_id,
                AgentMessageRecord.role == "assistant",
                AgentMessageRecord.is_deleted.is_(False),
            )
            .order_by(AgentMessageRecord.seq.desc())
            .limit(10)
        )
        rows = (await self.workflow_store.db.execute(stmt)).scalars().all()
        for meta in rows:
            if not isinstance(meta, dict):
                continue
            usage = meta.get("accumulated_usage")
            if isinstance(usage, dict) and usage:
                return usage
        return None

    async def get_interrupt_state(
        self,
        *,
        session_id: str,
        owner_id: int,
    ) -> SupervisorInterruptStateRecord:
        workflow = await self.workflow_store.get_workflow_by_session(
            session_id,
            owner_id=owner_id,
        )
        if workflow is None:
            raise SupervisorSessionNotFoundError(f"Session not found: {session_id}")
        if workflow.status != "waiting_review":
            raise SupervisorInvalidStateError(
                f"Session status is '{workflow.status}', not 'waiting_review'"
            )

        workflow_state = await self.workflow_store.load_workflow_state(workflow)
        checkpoint = await DBPersistStrategy(
            db=self.workflow_store.db
        ).load_interrupt_state(session_id)
        interrupt = None
        if checkpoint is not None:
            interrupt = {
                "tool_name": checkpoint.tool_name,
                "arguments": checkpoint.arguments,
                "context": checkpoint.context,
            }

        return SupervisorInterruptStateRecord(
            status=workflow.status,
            interrupt=interrupt,
            workflow=(
                workflow_state.model_dump() if workflow_state is not None else None
            ),
        )
