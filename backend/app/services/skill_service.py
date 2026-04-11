"""
Skill 业务逻辑层。

封装 Skill 的业务操作：
- upload_and_parse: 上传 Markdown → 解析 → 返回结果
- save_skill: 解析结果 + 补全字段 → 保存到 DB
- 渐进式披露支持
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.skill_parser import ParseResult, parse_skill_markdown
from app.models.skill import Skill
from app.repositories.skill import SkillRepository
from app.schemas.skill import SkillCreate, SkillUpdate


class SkillService:
    """Skill 业务逻辑封装。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SkillRepository(db)

    # === 上传解析 ===

    async def upload_and_parse(
        self,
        raw_markdown: str,
    ) -> tuple[ParseResult, Optional[Skill], bool]:
        """
        上传 Markdown → 解析 → 返回结果。

        Args:
            raw_markdown: SKILL.md 原始文本

        Returns:
            (ParseResult, existing_skill, is_update)
            - ParseResult: 解析出的结构化数据
            - existing_skill: 如果 name 已存在，返回 DB 中已有记录；否则 None
            - is_update: 是否为更新操作
        """
        parse_result = parse_skill_markdown(raw_markdown)

        existing: Optional[Skill] = None
        is_update = False

        name = parse_result.fields.get("name")
        if name:
            existing = await self.repo.get_by_name(name)
            if existing:
                is_update = True

        return parse_result, existing, is_update

    # === 保存 ===

    async def save_skill(
        self,
        create_data: SkillCreate,
        raw_markdown: Optional[str] = None,
    ) -> Skill:
        """
        保存 Skill（新建或更新）。

        Args:
            create_data: 经过验证和补全的 Skill 数据
            raw_markdown: 原始 Markdown 全文（覆盖）

        Returns:
            保存后的 Skill ORM 对象
        """
        data = create_data.model_dump()
        if raw_markdown is not None:
            data["raw_markdown"] = raw_markdown

        # 清理空字段
        data = {k: v for k, v in data.items() if v is not None}

        skill = await self.repo.upsert(name=create_data.name, data=data)
        await self.db.commit()
        await self.db.refresh(skill)
        return skill

    async def update_skill(
        self,
        name: str,
        update_data: SkillUpdate,
        raw_markdown: Optional[str] = None,
    ) -> Optional[Skill]:
        """
        部分更新 Skill。

        Args:
            name: Skill 名称
            update_data: 要更新的字段
            raw_markdown: 新的 Markdown 原文（可选）

        Returns:
            更新后的 Skill，未找到则返回 None
        """
        existing = await self.repo.get_by_name(name)
        if not existing:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if raw_markdown is not None:
            update_dict["raw_markdown"] = raw_markdown

        update_dict = {k: v for k, v in update_dict.items() if v is not None}

        for key, value in update_dict.items():
            setattr(existing, key, value)

        existing.version = existing.version + 1
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(existing)
        return existing

    # === 查询 ===

    async def get_skill(self, name: str) -> Optional[Skill]:
        """按 name 获取 Skill。"""
        return await self.repo.get_by_name(name)

    async def list_skills(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[List[Skill], int]:
        """分页查询 Skill 列表。"""
        filters = []
        if category:
            filters.append(Skill.category == category)
        if is_active is not None:
            filters.append(Skill.is_active == is_active)

        return await self.repo.list(
            filters=filters if filters else None,
            order_by=Skill.name.asc(),
            page=page,
            page_size=page_size,
        )

    async def list_active_skills(self) -> List[Skill]:
        """获取所有已启用的 Skill。"""
        return await self.repo.list_active()

    async def list_lite(self) -> List[Dict[str, Any]]:
        """获取所有活跃 Skill 的摘要（不含 content）。"""
        return await self.repo.list_lite()

    # === 删除 ===

    async def delete_skill(self, name: str) -> bool:
        """
        软删除 Skill。

        Returns:
            True 删除成功，False 未找到
        """
        existing = await self.repo.get_by_name(name)
        if not existing:
            return False
        await self.repo.soft_delete(existing)
        await self.db.commit()
        return True

    # === 渐进式披露 ===

    async def get_skill_fields(
        self,
        name: str,
        fields: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        按字段渐进式披露 Skill。

        Args:
            name: Skill 名称
            fields: 要返回的字段列表，None 则返回全部

        Returns:
            Skill 字段字典，未找到返回 None
        """
        skill = await self.repo.get_by_name(name)
        if not skill:
            return None

        data = {
            "name": skill.name,
            "title": skill.title,
            "description": skill.description,
            "content": skill.content,
            "parameters": skill.parameters or {},
            "examples": skill.examples or [],
            "constraints": skill.constraints or [],
            "category": skill.category,
            "difficulty": skill.difficulty,
            "tags": skill.tags or [],
            "author": skill.author,
            "skill_metadata": skill.skill_metadata or {},
        }

        if fields is None:
            return data

        return {k: v for k, v in data.items() if k in fields}
