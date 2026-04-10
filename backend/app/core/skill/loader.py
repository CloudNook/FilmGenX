"""
Skill 加载接口。

提供 Skill 的查询接口：
- load_skill_lite: 批量加载 Skill 摘要（不含 content）
- load_skill: 加载单个 Skill 完整信息，支持按字段过滤

存储层：
- 当前：直接查询数据库
- 未来：Redis 缓存层 + 数据库（确保页面修改后加载最新数据）
"""

import logging
from typing import TYPE_CHECKING

from app.core.skill.base import SkillLite

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def load_skill_lite(
    db: "AsyncSession",
    skill_names: list[str],
) -> list["SkillLite"]:
    """
    批量加载 Skill 摘要（不含 content）。

    用于 Agent 创建时注入 Skill 基本信息到提示词。

    Args:
        db: 数据库会话
        skill_names: Skill 名称列表

    Returns:
        SkillLite 列表
    """
    # TODO: 实现数据库查询
    # SELECT name, title, description, parameters FROM skills WHERE name IN (...)

    return [SkillLite(name=name) for name in skill_names]


async def load_skill(
    db: "AsyncSession",
    skill_name: str,
    fields: list[str] | None = None,
) -> dict:
    """
    加载单个 Skill 完整信息。

    支持按字段过滤返回，实现渐进式披露。

    Args:
        db: 数据库会话
        skill_name: Skill 名称
        fields: 可选，指定要返回的字段列表（对应 SkillField 枚举值）

    Returns:
        Skill 信息字典
    """
    # TODO: 实现数据库查询 + 字段过滤
    # SELECT * FROM skills WHERE name = ...
    return {
        "name": skill_name,
        "status": "not_implemented",
        "message": "load_skill: 后期从数据库加载",
    }


async def invalidate_cache(skill_name: str | None = None) -> None:
    """
    清除缓存（未来 Redis 缓存层使用）。

    Args:
        skill_name: 指定 Skill 名，不传则清除全部
    """
    # TODO: Redis 缓存失效
    # if skill_name:
    #     redis.delete(f"skill:{skill_name}")
    # else:
    #     redis.flushdb("skills")
    pass
