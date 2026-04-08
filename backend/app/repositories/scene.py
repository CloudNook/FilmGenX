"""
高光片段（Scene）Repository。
"""

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scene import Scene
from app.repositories.base import BaseRepository


class SceneRepository(BaseRepository[Scene]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Scene, session)

    async def get_by_project(
        self,
        project_id: int,
        *,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ):
        """查询项目下的片段列表，支持按状态/优先级过滤。"""
        filters = [Scene.project_id == project_id]
        if status:
            filters.append(Scene.status == status)
        if priority:
            filters.append(Scene.priority == priority)
        return await self.list(filters=filters, order_by=Scene.scene_code.asc(), page=page, page_size=page_size)

    async def get_by_code(self, scene_code: str) -> Optional[Scene]:
        """按业务ID查询。"""
        result = await self.session.execute(
            select(Scene).where(Scene.scene_code == scene_code, Scene.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    async def code_exists(self, scene_code: str) -> bool:
        """检查 scene_code 是否已被占用（含软删除记录），用于生成不冲突的唯一编号。"""
        result = await self.session.execute(
            select(func.count()).where(Scene.scene_code == scene_code)
        )
        return result.scalar_one() > 0

    async def count_by_project(self, project_id: int) -> int:
        """返回项目下所有 Scene 数量（含软删除），用于生成下一个序号。"""
        result = await self.session.execute(
            select(func.count()).where(Scene.project_id == project_id)
        )
        return result.scalar_one()

    async def get_by_id_and_project(self, id: int, project_id: int) -> Optional[Scene]:
        """按 ID + 项目ID 查询，防止越权访问。"""
        result = await self.session.execute(
            select(Scene).where(
                Scene.id == id,
                Scene.project_id == project_id,
                Scene.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()
