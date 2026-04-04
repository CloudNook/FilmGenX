"""
生成任务（GenerationTask）Repository。
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import GenerationTask
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[GenerationTask]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(GenerationTask, session)

    async def get_by_celery_id(self, celery_task_id: str) -> Optional[GenerationTask]:
        """按 Celery 任务ID 查询，用于回调更新状态。"""
        result = await self.session.execute(
            select(GenerationTask).where(
                GenerationTask.celery_task_id == celery_task_id,
                GenerationTask.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_shot(
        self,
        shot_id: int,
        *,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[GenerationTask]:
        """查询镜头关联的任务列表。"""
        cond = [GenerationTask.shot_id == shot_id, GenerationTask.is_deleted.is_(False)]
        if task_type:
            cond.append(GenerationTask.task_type == task_type)
        if status:
            cond.append(GenerationTask.status == status)
        result = await self.session.execute(
            select(GenerationTask).where(*cond).order_by(GenerationTask.id.desc())
        )
        return list(result.scalars().all())

    async def get_pending_tasks(self, task_type: Optional[str] = None) -> List[GenerationTask]:
        """获取待执行的任务（供调度器使用）。"""
        cond = [
            GenerationTask.status == "pending",
            GenerationTask.is_deleted.is_(False),
        ]
        if task_type:
            cond.append(GenerationTask.task_type == task_type)
        result = await self.session.execute(
            select(GenerationTask).where(*cond).order_by(GenerationTask.id.asc())
        )
        return list(result.scalars().all())
