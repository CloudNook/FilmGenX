"""
分镜组（ShotGroup）Repository。
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.shot_group import ShotGroup
from app.repositories.base import BaseRepository


class ShotGroupRepository(BaseRepository[ShotGroup]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ShotGroup, session)

    async def get(self, id: int) -> Optional[ShotGroup]:
        """按主键查询单条分镜组，并预加载成员镜头。"""
        result = await self.session.execute(
            select(ShotGroup)
            .where(
                ShotGroup.id == id,
                ShotGroup.is_deleted.is_(False),
            )
            .options(selectinload(ShotGroup.shots))
        )
        return result.scalar_one_or_none()

    async def get_by_storyboard(self, storyboard_id: int) -> List[ShotGroup]:
        """获取分镜脚本下的所有组，按 sequence 排序（含成员 shots eager load）。"""
        result = await self.session.execute(
            select(ShotGroup)
            .where(
                ShotGroup.storyboard_id == storyboard_id,
                ShotGroup.is_deleted.is_(False),
            )
            .options(selectinload(ShotGroup.shots))
            .order_by(ShotGroup.sequence.asc())
        )
        return list(result.scalars().all())

    async def get_by_code(self, group_code: str) -> Optional[ShotGroup]:
        """按组编号查询。"""
        result = await self.session.execute(
            select(ShotGroup).where(
                ShotGroup.group_code == group_code,
                ShotGroup.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_storyboard(
        self, group_id: int, storyboard_id: int
    ) -> Optional[ShotGroup]:
        """按 ID + 分镜脚本 ID 查询（含成员 shots eager load）。"""
        result = await self.session.execute(
            select(ShotGroup)
            .where(
                ShotGroup.id == group_id,
                ShotGroup.storyboard_id == storyboard_id,
                ShotGroup.is_deleted.is_(False),
            )
            .options(selectinload(ShotGroup.shots))
        )
        return result.scalar_one_or_none()
