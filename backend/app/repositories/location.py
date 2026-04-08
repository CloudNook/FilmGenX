"""
场景地点（Location）Repository。
"""

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.models.asset import Asset
from app.repositories.base import BaseRepository


class LocationRepository(BaseRepository[Location]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Location, session)

    async def get_by_project(
        self,
        project_id: int,
        *,
        page: int = 1,
        page_size: int = 50,
        is_active: Optional[bool] = None,
    ):
        """查询项目下的所有场景（分页）。"""
        filters = [Location.project_id == project_id]
        if is_active is not None:
            filters.append(Location.is_active == is_active)
        return await self.list(
            filters=filters,
            order_by=Location.name.asc(),
            page=page,
            page_size=page_size,
        )

    async def get_recent_by_project(self, project_id: int, *, limit: int = 5) -> List[Location]:
        """获取项目下最近更新的场景。"""
        result = await self.session.execute(
            select(Location)
            .where(
                Location.project_id == project_id,
                Location.is_deleted.is_(False),
            )
            .order_by(Location.updated_at.desc(), Location.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_dashboard_stats(self, project_id: int) -> tuple[int, int]:
        """获取场景总览统计：场景总数、图片总数（来自素材库）。"""
        total_locations = (
            await self.session.execute(
                select(func.count(Location.id)).where(
                    Location.project_id == project_id,
                    Location.is_deleted.is_(False),
                )
            )
        ).scalar_one()

        total_images = (
            await self.session.execute(
                select(func.count(Asset.id)).where(
                    Asset.project_id == project_id,
                    Asset.location_id.isnot(None),
                    Asset.is_current == True,
                )
            )
        ).scalar_one()

        return total_locations, total_images

    async def get_by_code(self, loc_code: str, *, include_deleted: bool = False) -> Optional[Location]:
        """按业务ID查询。"""
        filters = [Location.loc_code == loc_code]
        if not include_deleted:
            filters.append(Location.is_deleted.is_(False))
        result = await self.session.execute(select(Location).where(*filters))
        return result.scalar_one_or_none()

    async def count_by_project(self, project_id: int, *, include_deleted: bool = True) -> int:
        """返回项目下的场景数量，用于生成下一个 loc_code。"""
        filters = [Location.project_id == project_id]
        if not include_deleted:
            filters.append(Location.is_deleted.is_(False))
        result = await self.session.execute(
            select(func.count()).select_from(Location).where(*filters)
        )
        return result.scalar_one()

    async def get_by_id_and_project(self, id: int, project_id: int) -> Optional[Location]:
        """按 ID + 项目ID 查询。"""
        result = await self.session.execute(
            select(Location).where(
                Location.id == id,
                Location.project_id == project_id,
                Location.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_active_list(self, project_id: int) -> List[Location]:
        """获取项目下所有启用场景的列表（用于下拉选择）。"""
        result = await self.session.execute(
            select(Location).where(
                Location.project_id == project_id,
                Location.is_deleted.is_(False),
                Location.is_active == True,
            ).order_by(Location.name.asc())
        )
        return list(result.scalars().all())
