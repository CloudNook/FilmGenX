"""
内置工具实现（Skill 渐进披露相关）。

- ``load_skill(skill_name)``: L2，返回完整 body markdown
- ``load_skill_reference(skill_name, ref_key)``: L3，返回单个 reference

L1 元信息（name + description + target_agents + tags）由框架在 agent 启动时
直接注入 system prompt，**不再暴露为 LLM 工具**——把"看到什么 skill"这件事
固定在系统侧，避免 agent 通过工具调用反复查询造成不稳定。
"""

import logging
from typing import Any, Dict, List, Optional

from app.core.tools.registry import register_tool

logger = logging.getLogger(__name__)


@register_tool(
    name="load_skill",
    description=(
        "按名称加载 Skill 的完整 body markdown。\n"
        "Args:\n"
        "  skill_name: Skill 的唯一名称\n"
        "Returns:\n"
        "  Skill 的 body 文本，未找到或已禁用返回 None\n"
        "用法：当你看到 system prompt 里某个 Skill 的 description 与当前任务匹配，"
        "或者你正在阅读的 Skill body 中出现 @skill:<name> 引用，调用此工具加载它的 body。"
    ),
)
async def load_skill(skill_name: str) -> Optional[str]:
    from app.core.skill.loader import load_skill_body
    from app.db.session import AsyncSessionFactory

    async with AsyncSessionFactory() as db:
        body = await load_skill_body(db=db, skill_name=skill_name)

    if body is None:
        logger.warning(
            "[tool:load_skill] skill %r not found or inactive; returning None",
            skill_name,
        )
    else:
        logger.info(
            "[tool:load_skill] loaded skill=%r (body=%d chars)",
            skill_name,
            len(body),
        )
    return body


@register_tool(
    name="load_skill_reference",
    description=(
        "按 (skill_name, ref_key) 加载某个 Skill 的 reference 子文档。\n"
        "Args:\n"
        "  skill_name: Skill 名称\n"
        "  ref_key: reference 的 key\n"
        "Returns:\n"
        "  {skill_name, key, title, body} 字典；未找到返回 None\n"
        "用法：当你在 Skill body 中看到 @ref:<key> 或 @skill:<name>#<key> 引用，"
        "判断当前任务确实需要这个 reference 时调用此工具。"
    ),
)
async def load_skill_reference(
    skill_name: str,
    ref_key: str,
) -> Optional[Dict[str, Any]]:
    from app.core.skill.loader import load_skill_reference as _load
    from app.db.session import AsyncSessionFactory

    async with AsyncSessionFactory() as db:
        result = await _load(db=db, skill_name=skill_name, ref_key=ref_key)

    if result is None:
        logger.warning(
            "[tool:load_skill_reference] skill=%r ref_key=%r not found",
            skill_name,
            ref_key,
        )
    else:
        body_len = len(result.get("body", "") or "")
        logger.info(
            "[tool:load_skill_reference] loaded skill=%r ref_key=%r (body=%d chars)",
            skill_name,
            ref_key,
            body_len,
        )


@register_tool(
    name="list_tools",
    description=(
        "查询当前 Agent 实际可调用的所有工具清单（**唯一权威来源**）。\n"
        "Args: 无\n"
        "Returns:\n"
        "  [{name, description_short}] 列表，覆盖所有运行时注册的工具。\n"
        "用法：当用户问\"你有什么工具 / 你能做什么 / 你有哪些能力\"等问题时，"
        "**优先调用此工具拿到当前实时清单**，再据此整理回答——不要凭印象或上下文中的"
        "示例片段罗列，那些可能过时。description_short 只截前 200 字符避免上下文膨胀，"
        "需要某个工具完整描述时它本身就在你的 function-calling tools 里。"
    ),
)
async def list_tools() -> List[Dict[str, str]]:
    from app.core.tools.registry import ToolRegistry

    schemas = ToolRegistry.get_all_schemas()
    result: List[Dict[str, str]] = []
    for s in schemas:
        name = s.get("name") or "<unnamed>"
        desc = (s.get("description") or "").strip()
        # 截短：避免一次性把 N 个工具的完整 description 全打进 context
        short = desc[:200] + ("..." if len(desc) > 200 else "")
        # 不暴露 list_tools 自己（避免 LLM 递归调用查询自己）
        if name == "list_tools":
            continue
        result.append({"name": name, "description_short": short})

    logger.info("[tool:list_tools] returned %d tools", len(result))
    return result
