"""
分镜脚本（Storyboard）Repository。
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.storyboard import Storyboard
from app.repositories.base import BaseRepository


class StoryboardRepository(BaseRepository[Storyboard]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Storyboard, session)

    async def get_by_scene(self, scene_id: int) -> Optional[Storyboard]:
        """获取片段对应的分镜脚本（一对一关系）。"""
        result = await self.session.execute(
            select(Storyboard).where(
                Storyboard.scene_id == scene_id,
                Storyboard.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_with_shots(self, storyboard_id: int) -> Optional[Storyboard]:
        """获取分镜脚本及其所有镜头（一次查询，避免 N+1）。"""
        result = await self.session.execute(
            select(Storyboard)
            .options(selectinload(Storyboard.shots))
            .where(
                Storyboard.id == storyboard_id,
                Storyboard.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_project_id(self, storyboard_id: int) -> Optional[int]:
        """获取分镜脚本所属项目的ID（通过 scene 关联）。"""
        from app.models.scene import Scene

        result = await self.session.execute(
            select(Scene.project_id)
            .select_from(Storyboard)
            .join(Scene, Storyboard.scene_id == Scene.id)
            .where(
                Storyboard.id == storyboard_id,
                Storyboard.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()
