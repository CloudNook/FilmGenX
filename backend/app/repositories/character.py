"""
角色（Character / CharacterVersion）Repository。
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.character import Character, CharacterVersion
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

    async def get_by_code(self, char_code: str) -> Optional[Character]:
        """按业务ID查询。"""
        result = await self.session.execute(
            select(Character).where(
                Character.char_code == char_code,
                Character.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_with_versions(self, character_id: int) -> Optional[Character]:
        """获取角色及其所有版本。"""
        result = await self.session.execute(
            select(Character)
            .options(selectinload(Character.versions))
            .where(
                Character.id == character_id,
                Character.is_deleted.is_(False),
            )
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


class CharacterVersionRepository(BaseRepository[CharacterVersion]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CharacterVersion, session)

    async def get_by_character(self, character_id: int) -> List[CharacterVersion]:
        """获取角色所有版本，按 ID 排序。"""
        result = await self.session.execute(
            select(CharacterVersion).where(
                CharacterVersion.character_id == character_id,
                CharacterVersion.is_deleted.is_(False),
            ).order_by(CharacterVersion.id.asc())
        )
        return list(result.scalars().all())

    async def get_by_id_and_character(self, id: int, character_id: int) -> Optional[CharacterVersion]:
        """按 ID + 角色ID 查询。"""
        result = await self.session.execute(
            select(CharacterVersion).where(
                CharacterVersion.id == id,
                CharacterVersion.character_id == character_id,
                CharacterVersion.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()
