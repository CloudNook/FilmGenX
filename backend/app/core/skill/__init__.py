"""
Skill 系统。

定义 Skill 数据模型、解析器、加载接口和业务服务。
"""

from app.core.skill.base import Skill, SkillLite
from app.core.skill.field import SkillField
from app.core.skill.loader import (
    invalidate_cache,
    list_active_skills,
    load_skill,
    load_skill_lite,
)
from app.core.skill.parser import ParseResult, parse_skill_markdown
from app.core.skill.service import SkillService

__all__ = [
    # 数据模型
    "Skill",
    "SkillLite",
    "SkillField",
    # 解析器
    "parse_skill_markdown",
    "ParseResult",
    # 加载接口
    "load_skill",
    "load_skill_lite",
    "list_active_skills",
    "invalidate_cache",
    # 业务服务
    "SkillService",
]
