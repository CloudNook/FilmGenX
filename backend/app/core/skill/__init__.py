"""
Skill 系统（框架层）。

按 Claude SKILL.md 三层模型暴露加载入口：
- ``list_meta`` — L1 元信息（启动注入）
- ``load_skill_body`` — L2 主体（agent 通过 ``load_skill`` 工具调用）
- ``load_skill_reference`` — L3 子文档（agent 通过 ``load_skill_reference`` 工具调用）

ORM 模型定义在 ``app.models.skill.Skill``；解析器和 Service 在 ``app.services``。
"""

from app.core.skill.loader import (
    list_meta,
    load_skill_body,
    load_skill_reference,
)

__all__ = [
    "list_meta",
    "load_skill_body",
    "load_skill_reference",
]
