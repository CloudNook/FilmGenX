"""
SupervisorWorkflow Repository。

提供 SupervisorWorkflow 的异步 CRUD 操作。
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.supervisor_workflow import SupervisorWorkflow
from app.repositories.base import BaseRepository


class SupervisorWorkflowRepository(BaseRepository[SupervisorWorkflow]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SupervisorWorkflow, session)

    async def get_by_session_id(
        self,
        supervisor_session_id: str,
    ) -> Optional[SupervisorWorkflow]:
        """按 supervisor_session_id 查询（unique 索引）。"""
        result = await self.session.execute(
            select(SupervisorWorkflow).where(
                SupervisorWorkflow.supervisor_session_id == supervisor_session_id,
                SupervisorWorkflow.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_project(
        self,
        workflow_id: int,
        project_id: int,
    ) -> Optional[SupervisorWorkflow]:
        """按 ID + project_id 查询，用于权限校验。"""
        result = await self.session.execute(
            select(SupervisorWorkflow).where(
                SupervisorWorkflow.id == workflow_id,
                SupervisorWorkflow.project_id == project_id,
                SupervisorWorkflow.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        project_id: int,
        *,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> tuple[List[SupervisorWorkflow], int]:
        """按项目分页查询 workflow 列表。"""
        filters = [SupervisorWorkflow.project_id == project_id]
        if status:
            filters.append(SupervisorWorkflow.status == status)
        return await self.list(
            filters=filters,
            order_by=SupervisorWorkflow.created_at.desc(),
            page=page,
            page_size=page_size,
        )

    async def mark_completed(
        self,
        workflow: SupervisorWorkflow,
        workflow_snapshot: Optional[dict] = None,
        final_result: Optional[str] = None,
    ) -> SupervisorWorkflow:
        """标记流水线完成。"""
        workflow.status = "completed"
        workflow.completed_at = datetime.now(timezone.utc)
        if workflow_snapshot is not None:
            workflow.workflow_snapshot = workflow_snapshot
        if final_result is not None:
            workflow.final_result = final_result
        await self.session.flush()
        await self.session.refresh(workflow)
        return workflow

    async def mark_failed(
        self,
        workflow: SupervisorWorkflow,
        error_message: str,
    ) -> SupervisorWorkflow:
        """标记流水线失败。"""
        workflow.status = "failed"
        workflow.error_message = error_message
        workflow.completed_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(workflow)
        return workflow
