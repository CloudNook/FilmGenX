"""
内置工具实现（Skill 渐进披露相关）。

- ``load_skill(skill_name)``: L2，返回完整 body markdown
- ``load_skill_reference(skill_name, ref_key)``: L3，返回单个 reference

L1 元信息（name + description + target_agents + tags）由框架在 agent 启动时
直接注入 system prompt，**不再暴露为 LLM 工具**——把"看到什么 skill"这件事
固定在系统侧，避免 agent 通过工具调用反复查询造成不稳定。
"""

import logging
from typing import Any, Dict, Optional

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
    return result
