"""
素材（Asset）Repository。
"""

from typing import Dict, List, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.repositories.base import BaseRepository


class AssetRepository(BaseRepository[Asset]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Asset, session)

    async def get_by_project(
        self,
        project_id: int,
        *,
        asset_type: Optional[str] = None,
        shot_id: Optional[int] = None,
        location_id: Optional[int] = None,
        location_version_id: Optional[int] = None,
        source: Optional[str] = None,
        is_current: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ):
        """查询项目下的素材列表，支持多条件过滤。"""
        filters = [Asset.project_id == project_id, Asset.is_deleted.is_(False)]
        if asset_type:
            filters.append(Asset.asset_type == asset_type)
        if shot_id is not None:
            filters.append(Asset.shot_id == shot_id)
        if location_id is not None:
            filters.append(Asset.location_id == location_id)
        if location_version_id is not None:
            filters.append(Asset.location_version_id == location_version_id)
        if source:
            filters.append(Asset.source == source)
        if is_current is not None:
            filters.append(Asset.is_current == is_current)
        return await self.list(
            filters=filters,
            order_by=Asset.id.desc(),
            page=page,
            page_size=page_size,
        )

    async def get_recent_by_project(self, project_id: int, *, limit: int = 6) -> List[Asset]:
        """获取项目下最近更新的素材。"""
        result = await self.session.execute(
            select(Asset)
            .where(
                Asset.project_id == project_id,
                Asset.is_deleted.is_(False),
            )
            .order_by(Asset.updated_at.desc(), Asset.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_shot(self, shot_id: int, *, current_only: bool = True) -> List[Asset]:
        """获取镜头关联的素材，current_only=True 时只返回当前版本。"""
        cond = [Asset.shot_id == shot_id, Asset.is_deleted.is_(False)]
        if current_only:
            cond.append(Asset.is_current.is_(True))
        result = await self.session.execute(
            select(Asset).where(*cond).order_by(Asset.version.desc())
        )
        return list(result.scalars().all())

    async def get_stats_by_project(self, project_id: int) -> Dict[str, int]:
        """统计项目下各类型素材数量。"""
        result = await self.session.execute(
            select(Asset.asset_type, func.count(Asset.id))
            .where(
                Asset.project_id == project_id,
                Asset.is_deleted.is_(False),
            )
            .group_by(Asset.asset_type)
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_stats_by_shot(self, shot_id: int) -> Dict[str, int]:
        """统计镜头下各类型素材数量。"""
        result = await self.session.execute(
            select(Asset.asset_type, func.count(Asset.id))
            .where(
                Asset.shot_id == shot_id,
                Asset.is_deleted.is_(False),
            )
            .group_by(Asset.asset_type)
        )
        return {row[0]: row[1] for row in result.all()}

    async def deprecate_shot_assets(self, shot_id: int, asset_type: str) -> None:
        """将指定镜头、指定类型的当前素材全部标记为非当前版本。

        在新版本素材入库前调用，实现版本轮换。
        """
        await self.session.execute(
            update(Asset)
            .where(
                Asset.shot_id == shot_id,
                Asset.asset_type == asset_type,
                Asset.is_current.is_(True),
                Asset.is_deleted.is_(False),
            )
            .values(is_current=False)
        )
