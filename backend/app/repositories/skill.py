"""
Skill Repository。

提供 Skill 的异步 CRUD 操作。
"""

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import Skill
from app.repositories.base import BaseRepository


class SkillRepository(BaseRepository[Skill]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Skill, session)

    async def get_by_name(self, name: str) -> Optional[Skill]:
        """按 name 查询 Skill（唯一索引）。"""
        result = await self.session.execute(
            select(Skill).where(
                Skill.name == name,
                Skill.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_active(self) -> List[Skill]:
        """查询所有已启用的 Skill。"""
        result = await self.session.execute(
            select(Skill)
            .where(
                Skill.is_active.is_(True),
                Skill.is_deleted.is_(False),
            )
            .order_by(Skill.id.asc())
        )
        return list(result.scalars().all())

    async def list_by_category(
        self,
        category: str,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Skill], int]:
        """按领域分类查询。"""
        return await self.list(
            filters=[Skill.category == category],
            order_by=Skill.name.asc(),
            page=page,
            page_size=page_size,
        )

    async def list_lite(self) -> List[Skill]:
        """
        查询所有活跃 Skill 的摘要字段（不含 content）。
        用于 Agent 启动时注入到 system prompt。
        """
        result = await self.session.execute(
            select(
                Skill.name,
                Skill.title,
                Skill.description,
                Skill.parameters,
            )
            .where(
                Skill.is_active.is_(True),
                Skill.is_deleted.is_(False),
            )
            .order_by(Skill.name.asc())
        )
        rows = result.all()
        # 转为 dict 列表（避免 SQLAlchemy 列映射问题）
        return [
            {
                "name": r[0],
                "title": r[1],
                "description": r[2],
                "parameters": r[3],
            }
            for r in rows
        ]

    async def upsert(self, name: str, data: dict) -> Skill:
        """
        插入或更新 Skill。

        - 如果 name 已存在：更新字段，version + 1
        - 如果 name 不存在：创建新记录
        """
        existing = await self.get_by_name(name)
        if existing:
            # 更新字段（排除 id / created_at / name / version 由 service 层处理）
            update_data = {k: v for k, v in data.items()
                           if k not in ("id", "created_at", "name")}
            for key, value in update_data.items():
                setattr(existing, key, value)
            existing.version = existing.version + 1
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        else:
            # 新建
            create_data = {**data, "name": name, "version": 1}
            obj = Skill(**create_data)
            self.session.add(obj)
            await self.session.flush()
            await self.session.refresh(obj)
            return obj
