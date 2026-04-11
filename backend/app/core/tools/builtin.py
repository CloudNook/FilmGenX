"""
内置工具实现。

包含：
- load_skill: 按名称加载完整 Skill（渐进式披露，支持按字段过滤）
- load_skill_lite: 按名称加载 Skill 摘要（title、description、parameters）
"""

from typing import Any, Dict, List, Optional

from app.core.tools.registry import register_tool


@register_tool(
    name="load_skill",
    description=(
        "按名称加载完整 Skill，获取其所有详细信息。\n"
        "支持渐进式披露：通过 fields 参数过滤返回字段。\n"
        "Args:\n"
        "  skill_name: Skill 的唯一名称\n"
        "  fields: 可选，要查看的字段列表，如 ['content', 'parameters', 'examples']\n"
        "        可选值：name, title, description, content, parameters, examples, constraints\n"
        "Returns:\n"
        "  Skill 的完整信息或指定字段，未找到返回 None"
    ),
)
async def load_skill(
    skill_name: str,
    fields: Optional[List[str]] = None,
    db: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """
    按名称加载完整 Skill。

    渐进式披露：只返回调用方请求的字段，避免一次性暴露过多信息。

    Args:
        skill_name: Skill 名称
        fields: 可选，指定要返回的字段列表
        db: 数据库会话

    Returns:
        Skill 信息字典，未找到返回 None
    """
    from app.core.skill.loader import load_skill as _load_skill

    if db is None:
        return {"error": "数据库会话未提供"}

    return await _load_skill(db=db, skill_name=skill_name, fields=fields)


@register_tool(
    name="load_skill_lite",
    description=(
        "批量加载 Skill 摘要信息（title、description、parameters）。\n"
        "用于 Agent 创建时注入 Skill 的基本信息到提示词中。\n"
        "Args:\n"
        "  skill_names: Skill 名称列表，为空则返回所有活跃 Skill\n"
        "Returns:\n"
        "  每个 Skill 的基本信息列表"
    ),
)
async def load_skill_lite(
    skill_names: List[str],
    db: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    批量加载 Skill 摘要。

    用于 Agent 初始化时获取 Skill 的基本信息，注入到提示词中。

    Args:
        skill_names: Skill 名称列表，为空则返回所有活跃 Skill
        db: 数据库会话

    Returns:
        Skill 摘要列表
    """
    from app.core.skill.loader import load_skill_lite as _load_skill_lite

    if db is None:
        return [{"error": "数据库会话未提供"}]

    all_lite = await _load_skill_lite(db=db)
    if not skill_names:
        return all_lite
    name_set = set(skill_names)
    return [s for s in all_lite if s["name"] in name_set]
