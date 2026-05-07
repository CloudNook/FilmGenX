"""
SkillService 集成测试（真实 DB）。

跑前提：本地 DEV PostgreSQL 已起，迁移到 head（含 skill_claude_style）。
每个测试用 ``cleanup_skill`` 确保自身造的数据被清理，避免污染他人。
"""

from __future__ import annotations

import pytest

from app.db.session import AsyncSessionFactory
from app.schemas.skill import SkillCreate, SkillReferenceItem, SkillUpdate
from app.services.skill_service import SkillService


async def _delete(name: str) -> None:
    async with AsyncSessionFactory() as db:
        service = SkillService(db)
        await service.delete_skill(name)


@pytest.fixture
async def cleanup_skills():
    created: list[str] = []
    yield created
    for name in created:
        await _delete(name)


@pytest.mark.asyncio
async def test_list_active_meta_filters_by_target_agent(cleanup_skills):
    """target_agents @> [agent_name] 反查只返回相关 skill 的 L1 meta。"""
    async with AsyncSessionFactory() as db:
        service = SkillService(db)
        await service.save_skill(
            SkillCreate(
                name="t-meta-outline",
                description="Use when designing outlines.",
                target_agents=["outline_agent"],
                tags=["story"],
                body="body for outline",
            )
        )
        cleanup_skills.append("t-meta-outline")
        await service.save_skill(
            SkillCreate(
                name="t-meta-script",
                description="Use when writing scripts.",
                target_agents=["script_agent"],
                tags=["dialogue"],
                body="body for script",
            )
        )
        cleanup_skills.append("t-meta-script")
        await service.save_skill(
            SkillCreate(
                name="t-meta-shared",
                description="Use when reviewing both outline and script.",
                target_agents=["outline_agent", "script_agent"],
                tags=["review"],
                body="cross domain",
            )
        )
        cleanup_skills.append("t-meta-shared")

    # 反查：outline_agent 看到 t-meta-outline + t-meta-shared
    async with AsyncSessionFactory() as db:
        service = SkillService(db)
        meta_for_outline = await service.list_active_meta(target_agent="outline_agent")

    names = {row["name"] for row in meta_for_outline}
    assert "t-meta-outline" in names
    assert "t-meta-shared" in names
    assert "t-meta-script" not in names

    # 反查：script_agent 看到 t-meta-script + t-meta-shared
    async with AsyncSessionFactory() as db:
        service = SkillService(db)
        meta_for_script = await service.list_active_meta(target_agent="script_agent")
    names = {row["name"] for row in meta_for_script}
    assert "t-meta-script" in names
    assert "t-meta-shared" in names
    assert "t-meta-outline" not in names

    # admin picker：不指定 target_agent 时三个都返回（active 全集）
    async with AsyncSessionFactory() as db:
        service = SkillService(db)
        all_meta = await service.list_active_meta()
    names = {row["name"] for row in all_meta}
    for n in ("t-meta-outline", "t-meta-script", "t-meta-shared"):
        assert n in names


@pytest.mark.asyncio
async def test_get_body_and_get_reference_progressive_disclosure(cleanup_skills):
    """L2: get_body / L3: get_reference 各自返回独立切面。"""
    async with AsyncSessionFactory() as db:
        service = SkillService(db)
        await service.save_skill(
            SkillCreate(
                name="t-prog-narrative",
                description="Use when ...",
                target_agents=["outline_agent"],
                body="主体内容，看 @ref:act-templates 模板。",
                references=[
                    SkillReferenceItem(
                        key="act-templates",
                        title="Act Templates",
                        body="完整模板内容...",
                    )
                ],
            )
        )
        cleanup_skills.append("t-prog-narrative")

    async with AsyncSessionFactory() as db:
        service = SkillService(db)
        body = await service.get_body("t-prog-narrative")
        assert body and "主体内容" in body

        ref = await service.get_reference("t-prog-narrative", "act-templates")
        assert ref is not None
        assert ref["body"].startswith("完整模板")
        assert ref["title"] == "Act Templates"

        # 不存在的 ref_key 返回 None
        assert await service.get_reference("t-prog-narrative", "nope") is None


@pytest.mark.asyncio
async def test_lint_detects_dead_ref_and_unknown_skill(cleanup_skills):
    async with AsyncSessionFactory() as db:
        service = SkillService(db)
        await service.save_skill(
            SkillCreate(
                name="t-lint-bad",
                description="x",
                body="@ref:nope and @skill:does-not-exist",
                references=[],
            )
        )
        cleanup_skills.append("t-lint-bad")

    async with AsyncSessionFactory() as db:
        service = SkillService(db)
        issues = await service.lint("t-lint-bad")

    assert issues is not None
    codes = sorted({i.code for i in issues})
    assert "DEAD_REF" in codes
    assert "UNKNOWN_SKILL" in codes


@pytest.mark.asyncio
async def test_save_skill_persists_target_agents_and_references(cleanup_skills):
    async with AsyncSessionFactory() as db:
        service = SkillService(db)
        skill = await service.save_skill(
            SkillCreate(
                name="t-persist-x",
                description="Use when persisting works.",
                target_agents=["script_agent"],
                tags=["x"],
                body="@ref:tip",
                references=[
                    SkillReferenceItem(key="tip", title="Tip", body="some tip"),
                ],
            )
        )
        cleanup_skills.append("t-persist-x")
        assert skill.target_agents == ["script_agent"]
        assert skill.body == "@ref:tip"
        assert isinstance(skill.references, list)
        assert skill.references[0]["key"] == "tip"
