"""
单镜头（Shot）Repository。
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shot import Shot
from app.repositories.base import BaseRepository


class ShotRepository(BaseRepository[Shot]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Shot, session)

    async def get_by_storyboard(
        self,
        storyboard_id: int,
        *,
        status: Optional[str] = None,
    ) -> List[Shot]:
        """获取分镜脚本下的所有镜头，按 sequence 排序。"""
        cond = [Shot.storyboard_id == storyboard_id, Shot.is_deleted.is_(False)]
        if status:
            cond.append(Shot.status == status)
        result = await self.session.execute(
            select(Shot).where(*cond).order_by(Shot.sequence.asc())
        )
        return list(result.scalars().all())

    async def get_by_code(self, shot_code: str) -> Optional[Shot]:
        """按业务ID查询。"""
        result = await self.session.execute(
            select(Shot).where(Shot.shot_code == shot_code, Shot.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    async def get_by_shot_group(self, shot_group_id: int) -> List[Shot]:
        """获取指定分镜组的所有镜头，按 sequence 排序。"""
        result = await self.session.execute(
            select(Shot).where(
                Shot.shot_group_id == shot_group_id,
                Shot.is_deleted.is_(False),
            ).order_by(Shot.sequence.asc())
        )
        return list(result.scalars().all())

    async def get_by_id_and_storyboard(self, id: int, storyboard_id: int) -> Optional[Shot]:
        """按 ID + 分镜脚本ID 查询，防止越权访问。"""
        result = await self.session.execute(
            select(Shot).where(
                Shot.id == id,
                Shot.storyboard_id == storyboard_id,
                Shot.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()
