"""
Skill 加载接口（Agent 动态加载）。

提供 Skill 的查询接口：
- load_skill_lite: 批量加载 Skill 摘要（不含 content）
- load_skill: 加载单个 Skill 完整信息，支持按字段过滤

所有方法从数据库读取，不做任何缓存（缓存层在 service 层统一处理）。
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from app.core.skill.service import SkillService

logger = logging.getLogger(__name__)


async def load_skill_lite(
    db: "AsyncSession",
    skill_names: List[str],
) -> List[Dict[str, Any]]:
    """
    批量加载指定 Skill 的摘要（不含 content）。

    用于 Agent 启动时注入 Skill 基本信息到提示词。

    Args:
        db: 数据库会话
        skill_names: Skill 名称列表

    Returns:
        SkillLite 列表（name, title, description, parameters）
    """
    service = SkillService(db)
    all_lite = await service.list_lite()

    if not skill_names:
        return all_lite

    # 按 name 过滤
    name_set = set(skill_names)
    return [s for s in all_lite if s["name"] in name_set]


async def load_skill(
    db: "AsyncSession",
    skill_name: str,
    fields: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    加载单个 Skill 完整信息。

    支持按字段过滤返回，实现渐进式披露。

    Args:
        db: 数据库会话
        skill_name: Skill 名称
        fields: 可选，指定要返回的字段列表（对应 SkillField 枚举值）

    Returns:
        Skill 信息字典，未找到返回 None
    """
    service = SkillService(db)
    return await service.get_skill_fields(skill_name, fields=fields)


async def list_active_skills(
    db: "AsyncSession",
) -> List[Dict[str, Any]]:
    """
    获取所有已启用的 Skill 摘要。

    用于 AgentFactory 在构建 system prompt 时注入可用 Skill 列表。

    Args:
        db: 数据库会话

    Returns:
        所有活跃 Skill 的摘要列表
    """
    service = SkillService(db)
    return await service.list_lite()


async def invalidate_cache(skill_name: Optional[str] = None) -> None:
    """
    清除缓存（预留，未来可接入 Redis）。

    Args:
        skill_name: 指定 Skill 名，不传则清除全部
    """
    # TODO: Redis 缓存失效
    # if skill_name:
    #     redis.delete(f"skill:{skill_name}")
    # else:
    #     redis.flushdb("skills")
    logger.debug("Skill cache invalidation called (no-op until Redis is wired in)")
