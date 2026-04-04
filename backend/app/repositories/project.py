"""
项目（Project）Repository。
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Project, session)

    async def get_by_owner(
        self,
        owner_id: int,
        *,
        page: int = 1,
        page_size: int = 20,
    ):
        """查询指定用户的所有项目（分页）。"""
        return await self.list(
            filters=[Project.owner_id == owner_id],
            order_by=Project.id.desc(),
            page=page,
            page_size=page_size,
        )

    async def get_by_id_and_owner(self, id: int, owner_id: int) -> Optional[Project]:
        """按 ID + 所有者查询，确保用户只能访问自己的项目。"""
        result = await self.session.execute(
            select(Project).where(
                Project.id == id,
                Project.owner_id == owner_id,
                Project.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()
