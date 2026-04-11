"""
Skill 系统（框架层）。

定义 Skill 数据模型和 Agent 加载接口。
业务逻辑（解析器、Service）位于 app.services。
"""

from app.core.skill.base import Skill, SkillLite
from app.core.skill.field import SkillField
from app.core.skill.loader import (
    invalidate_cache,
    list_active_skills,
    load_skill,
    load_skill_lite,
)

__all__ = [
    # 数据模型
    "Skill",
    "SkillLite",
    "SkillField",
    # 加载接口
    "load_skill",
    "load_skill_lite",
    "list_active_skills",
    "invalidate_cache",
]
