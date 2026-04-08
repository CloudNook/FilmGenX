"""
角色（Character）Repository。
"""

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character import Character
from app.repositories.base import BaseRepository


class CharacterRepository(BaseRepository[Character]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Character, session)

    async def get_by_project(
        self,
        project_id: int,
        *,
        page: int = 1,
        page_size: int = 50,
    ):
        """查询项目下的所有角色（分页）。"""
        return await self.list(
            filters=[Character.project_id == project_id],
            order_by=Character.char_code.asc(),
            page=page,
            page_size=page_size,
        )

    async def get_recent_by_project(self, project_id: int, *, limit: int = 5) -> List[Character]:
        """获取项目下最近更新的角色。"""
        result = await self.session.execute(
            select(Character)
            .where(
                Character.project_id == project_id,
                Character.is_deleted.is_(False),
            )
            .order_by(Character.updated_at.desc(), Character.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_dashboard_stats(self, project_id: int) -> int:
        """获取角色总数。"""
        return (
            await self.session.execute(
                select(func.count(Character.id)).where(
                    Character.project_id == project_id,
                    Character.is_deleted.is_(False),
                )
            )
        ).scalar_one()

    async def get_by_code(self, char_code: str, *, include_deleted: bool = False) -> Optional[Character]:
        """按业务ID查询。include_deleted=True 时也查软删除记录（用于唯一性校验）。"""
        filters = [Character.char_code == char_code]
        if not include_deleted:
            filters.append(Character.is_deleted.is_(False))
        result = await self.session.execute(
            select(Character).where(*filters)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_project(self, id: int, project_id: int) -> Optional[Character]:
        """按 ID + 项目ID 查询。"""
        result = await self.session.execute(
            select(Character).where(
                Character.id == id,
                Character.project_id == project_id,
                Character.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()
