"""
素材（Asset）Repository。
"""

from typing import Dict, List, Optional

from sqlalchemy import func, select
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
        source: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ):
        """查询项目下的素材列表，支持类型 / 来源过滤。"""
        filters = [Asset.project_id == project_id, Asset.is_deleted.is_(False)]
        if asset_type:
            filters.append(Asset.asset_type == asset_type)
        if source:
            filters.append(Asset.source == source)
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
