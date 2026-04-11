"""
Workspace Repository。
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace
from app.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Workspace, session)

    async def get_by_project(
        self,
        project_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Workspace], int]:
        """获取项目下的工作台列表（按最新更新排序）。"""
        return await self.list(
            filters=[Workspace.project_id == project_id],
            order_by=Workspace.updated_at.desc(),
            page=page,
            page_size=page_size,
        )

    async def get_by_id_and_project(
        self, workspace_id: int, project_id: int
    ) -> Optional[Workspace]:
        result = await self.session.execute(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.project_id == project_id,
                Workspace.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def update_tokens(
        self, workspace_id: int, token_delta: int
    ) -> None:
        """累加 token 消耗并更新 last_message_at。"""
        ws = await self.get(workspace_id)
        if ws:
            ws.total_tokens += token_delta
            ws.last_message_at = datetime.now(timezone.utc)
            await self.session.commit()
