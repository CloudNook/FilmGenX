"""
素材（Asset）Repository。
"""

from typing import List, Optional

from sqlalchemy import select, update
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
        page: int = 1,
        page_size: int = 20,
    ):
        """查询项目下的素材列表，支持按类型过滤。"""
        filters = [Asset.project_id == project_id]
        if asset_type:
            filters.append(Asset.asset_type == asset_type)
        return await self.list(
            filters=filters,
            order_by=Asset.id.desc(),
            page=page,
            page_size=page_size,
        )

    async def get_by_shot(self, shot_id: int, *, current_only: bool = True) -> List[Asset]:
        """获取镜头关联的素材，current_only=True 时只返回当前版本。"""
        cond = [Asset.shot_id == shot_id, Asset.is_deleted.is_(False)]
        if current_only:
            cond.append(Asset.is_current.is_(True))
        result = await self.session.execute(
            select(Asset).where(*cond).order_by(Asset.version.desc())
        )
        return list(result.scalars().all())

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
