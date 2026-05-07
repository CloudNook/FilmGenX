"""
Skill Repository。

提供 Skill 的异步 CRUD 操作。新模型按 Claude SKILL.md 风格组织：
- L1: name + description + target_agents + tags（list_meta）
- L2: body
- L3: references
"""

from typing import List, Optional

from sqlalchemy import select
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

    async def list_active_meta(
        self,
        *,
        target_agent: Optional[str] = None,
    ) -> List[dict]:
        """
        返回所有 active skill 的 L1 元信息（不含 body / references）。

        - ``target_agent=None``：列出所有 active skill 的 meta（admin picker 用）
        - ``target_agent="outline_agent"``：仅返回 ``target_agents`` 包含该 agent
          的 skill（agent 启动注入 system prompt 用）

        过滤逻辑使用 Postgres ``@>`` jsonb contains 操作符，需要 GIN 索引支持
        （在迁移里已建 ``ix_skills_target_agents``）。
        """
        stmt = select(
            Skill.name,
            Skill.description,
            Skill.target_agents,
            Skill.tags,
        ).where(
            Skill.is_active.is_(True),
            Skill.is_deleted.is_(False),
        )
        if target_agent is not None:
            stmt = stmt.where(Skill.target_agents.contains([target_agent]))
        stmt = stmt.order_by(Skill.name.asc())

        rows = await self.session.execute(stmt)
        return [
            {
                "name": row[0],
                "description": row[1],
                "target_agents": row[2] or [],
                "tags": row[3] or [],
            }
            for row in rows.all()
        ]

    async def upsert(self, name: str, data: dict) -> Skill:
        """插入或更新 Skill。

        - name 已存在：更新字段，version + 1
        - name 不存在：创建新记录
        """
        existing = await self.get_by_name(name)
        if existing:
            update_data = {
                k: v for k, v in data.items() if k not in ("id", "created_at", "name")
            }
            for key, value in update_data.items():
                setattr(existing, key, value)
            existing.version = existing.version + 1
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        create_data = {**data, "name": name, "version": 1}
        obj = Skill(**create_data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj
