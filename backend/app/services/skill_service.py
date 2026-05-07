"""
Skill 业务逻辑层（Claude SKILL.md 风格）。

封装：
- 上传 / 解析 / 保存
- L1 元信息查询（list_meta_for_agent / list_active_meta）
- L2 / L3 渐进披露（get_body / get_reference）
- Lint（语法 + 引用有效性）

注意：
- 没有 `list_lite`：原 lite 概念由 list_active_meta + load_skill 工具替代
- 不再做 category / difficulty 级筛选
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import Skill
from app.repositories.skill import SkillRepository
from app.schemas.skill import SkillCreate, SkillUpdate
from app.services.skill_parser import ParseResult, parse_skill_markdown
from app.services.skill_references import (
    LintIssue,
    SkillLikeView,
    lint_skill,
)


class SkillService:
    """Skill 业务逻辑封装。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SkillRepository(db)

    # ------------------------------------------------------------------ #
    # 上传 / 保存
    # ------------------------------------------------------------------ #

    async def upload_and_parse(
        self,
        raw_markdown: str,
    ) -> tuple[ParseResult, Optional[Skill], bool]:
        """上传 Markdown → 解析 → 返回结果（不保存）。"""
        parse_result = parse_skill_markdown(raw_markdown)

        existing: Optional[Skill] = None
        is_update = False
        name = parse_result.fields.get("name")
        if name:
            existing = await self.repo.get_by_name(name)
            is_update = existing is not None

        return parse_result, existing, is_update

    async def save_skill(
        self,
        create_data: SkillCreate,
        raw_markdown: Optional[str] = None,
    ) -> Skill:
        """保存 Skill（新建或更新）。"""
        data = create_data.model_dump(by_alias=False)
        if raw_markdown is not None:
            data["raw_markdown"] = raw_markdown

        # references 是 list[SkillReferenceItem]，dump 后是 list[dict]
        # 这正是 ORM 字段需要的形态
        # 清理 None（保留空 list / 空 dict 等显式值）
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
        """部分更新 Skill。"""
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

    # ------------------------------------------------------------------ #
    # 查询
    # ------------------------------------------------------------------ #

    async def get_skill(self, name: str) -> Optional[Skill]:
        return await self.repo.get_by_name(name)

    async def list_skills(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        is_active: Optional[bool] = None,
    ) -> tuple[List[Skill], int]:
        filters = []
        if is_active is not None:
            filters.append(Skill.is_active == is_active)

        return await self.repo.list(
            filters=filters or None,
            order_by=Skill.name.asc(),
            page=page,
            page_size=page_size,
        )

    async def list_active_skills(self) -> List[Skill]:
        return await self.repo.list_active()

    async def list_active_meta(
        self,
        *,
        target_agent: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """L1 元信息列表。

        - ``target_agent=None``: 所有 active skill 的 meta（admin picker 用）
        - ``target_agent="outline_agent"``: 仅 ``target_agents`` 包含 outline_agent 的 skill
        """
        return await self.repo.list_active_meta(target_agent=target_agent)

    # ------------------------------------------------------------------ #
    # 渐进披露：L2 / L3
    # ------------------------------------------------------------------ #

    async def get_body(self, name: str) -> Optional[str]:
        """L2: 返回 skill body。"""
        skill = await self.repo.get_by_name(name)
        if skill is None or not skill.is_active:
            return None
        return skill.body or ""

    async def get_reference(
        self,
        name: str,
        ref_key: str,
    ) -> Optional[Dict[str, Any]]:
        """L3: 返回 skill 的某个 reference。"""
        skill = await self.repo.get_by_name(name)
        if skill is None or not skill.is_active:
            return None
        for ref in skill.references or []:
            if isinstance(ref, dict) and ref.get("key") == ref_key:
                return {
                    "skill_name": name,
                    "key": ref.get("key"),
                    "title": ref.get("title", ""),
                    "body": ref.get("body", ""),
                }
        return None

    # ------------------------------------------------------------------ #
    # Lint
    # ------------------------------------------------------------------ #

    async def lint(self, name: str) -> Optional[List[LintIssue]]:
        """对单个 skill 做 lint 检查。

        加载所有 active skill 作为 cross-skill 引用的目标集合。
        """
        skill = await self.repo.get_by_name(name)
        if skill is None:
            return None

        all_active = await self.repo.list_active()
        all_skills_by_name = {
            s.name: SkillLikeView(
                name=s.name,
                is_active=s.is_active,
                body=s.body,
                references=list(s.references or []),
            )
            for s in all_active
        }
        # 把当前 skill 也放进去（即使被禁用），方便指向自己的检查
        all_skills_by_name[skill.name] = SkillLikeView(
            name=skill.name,
            is_active=skill.is_active,
            body=skill.body,
            references=list(skill.references or []),
        )

        return lint_skill(
            all_skills_by_name[skill.name],
            all_skills_by_name=all_skills_by_name,
        )

    # ------------------------------------------------------------------ #
    # 删除
    # ------------------------------------------------------------------ #

    async def delete_skill(self, name: str) -> bool:
        existing = await self.repo.get_by_name(name)
        if not existing:
            return False
        await self.repo.soft_delete(existing)
        await self.db.commit()
        return True
