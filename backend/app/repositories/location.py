"""
场景地点（Location / LocationVersion）Repository。
"""

from typing import List, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.location import Location, LocationVersion
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

    async def get_with_versions(self, location_id: int) -> Optional[Location]:
        """获取场景及其所有版本。"""
        result = await self.session.execute(
            select(Location)
            .options(selectinload(Location.versions))
            .where(
                Location.id == location_id,
                Location.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

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


class LocationVersionRepository(BaseRepository[LocationVersion]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(LocationVersion, session)

    async def clear_default_for_location(
        self,
        location_id: int,
        *,
        exclude_id: Optional[int] = None,
    ) -> None:
        """确保同一场景只有一个默认版本。"""
        cond = [
            LocationVersion.location_id == location_id,
            LocationVersion.is_deleted.is_(False),
        ]
        if exclude_id is not None:
            cond.append(LocationVersion.id != exclude_id)

        await self.session.execute(
            update(LocationVersion)
            .where(*cond)
            .values(is_default=False)
        )

    async def get_by_location(self, location_id: int) -> List[LocationVersion]:
        """获取场景所有版本，按 ID 排序。"""
        result = await self.session.execute(
            select(LocationVersion).where(
                LocationVersion.location_id == location_id,
                LocationVersion.is_deleted.is_(False),
            ).order_by(LocationVersion.id.asc())
        )
        return list(result.scalars().all())

    async def get_by_id_and_location(self, id: int, location_id: int) -> Optional[LocationVersion]:
        """按 ID + 场景ID 查询。"""
        result = await self.session.execute(
            select(LocationVersion).where(
                LocationVersion.id == id,
                LocationVersion.location_id == location_id,
                LocationVersion.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_default_version(self, location_id: int) -> Optional[LocationVersion]:
        """获取场景的默认版本。"""
        result = await self.session.execute(
            select(LocationVersion).where(
                LocationVersion.location_id == location_id,
                LocationVersion.is_default == True,
                LocationVersion.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()
