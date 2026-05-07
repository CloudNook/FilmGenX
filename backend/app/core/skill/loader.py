"""
Skill 加载接口（Agent 渐进披露）。

按 Claude SKILL.md 三层模型暴露：
- ``list_meta(db, target_agent=None)`` 返回 L1 元信息（不含 body / references）
- ``load_skill(db, name)`` 返回 L2 主体（body）
- ``load_skill_reference(db, name, ref_key)`` 返回 L3 子文档（references[ref_key].body）

L2 / L3 入口不按 ``target_agents`` 过滤——agent 通过 @skill 引用决策跨域加载时
框架不应阻拦（参见 feedback_agent_autonomy_boundary）。
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from app.services.skill_service import SkillService


async def list_meta(
    db: "AsyncSession",
    *,
    target_agent: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """L1：返回 skill 元信息列表。

    - ``target_agent=None``：所有 active skill 的元信息
    - ``target_agent="outline_agent"``：``target_agents`` 包含该 agent 的 skill
    """
    service = SkillService(db)
    return await service.list_active_meta(target_agent=target_agent)


async def load_skill_body(
    db: "AsyncSession",
    skill_name: str,
) -> Optional[str]:
    """L2：返回 skill 的 body markdown，未找到或已禁用返回 None。"""
    service = SkillService(db)
    return await service.get_body(skill_name)


async def load_skill_reference(
    db: "AsyncSession",
    skill_name: str,
    ref_key: str,
) -> Optional[Dict[str, Any]]:
    """L3：返回 skill 的某个 reference，未找到返回 None。

    返回结构：``{skill_name, key, title, body}``
    """
    service = SkillService(db)
    return await service.get_reference(skill_name, ref_key)
