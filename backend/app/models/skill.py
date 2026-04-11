"""
Skill 模型。

对齐 Anthropic SKILL.md 标准 + 视频领域扩展。
支持 Markdown 上传 → 解析 → 补全 → 保存的全流程。
"""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass


class Skill(Base):
    """
    Skill 存储模型。

    与 Anthropic SKILL.md 标准对齐：
    - name: 唯一标识（小写/数字/连字符）
    - title: 人类可读标题
    - description: 激活描述（Agent据此判断何时调用）
    - content: 核心指令（Agent 实际执行的内容）
    - parameters: JSON Schema 参数定义
    - examples: 使用示例列表
    - constraints: 约束条件列表

    扩展字段：
    - category: 领域分类（如：灯光、运镜、剧本）
    - difficulty: 难度级别
    - tags: 标签列表
    - author: 作者
    - raw_markdown: 原始 Markdown 全文（每次上传更新）
    - is_active: 是否启用
    - version: 版本号（每次保存递增）
    - metadata: 扩展元数据
    """

    __tablename__ = "skills"

    # === Anthropic SKILL.md 标准字段 ===
    name: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="唯一标识，小写字母/数字/连字符",
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="人类可读标题，用于界面展示",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="一句话描述，用于 Agent 判断何时激活",
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="核心指令，Agent 实际执行的逻辑",
    )
    parameters: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        comment="JSON Schema 参数定义",
    )
    examples: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        comment="使用示例列表",
    )
    constraints: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        comment="约束条件列表",
    )

    # === 扩展元数据字段 ===
    category: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="领域分类：剧本、灯光、运镜、调色等",
    )
    difficulty: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="难度：beginner / intermediate / advanced",
    )
    tags: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        comment="标签列表",
    )
    author: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="作者",
    )

    # === 原始内容 + 系统字段 ===
    raw_markdown: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="原始 Markdown 全文（每次上传覆盖）",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="是否启用，未启用则 Agent 不会加载",
    )
    version: Mapped[int] = mapped_column(
        default=1,
        nullable=False,
        comment="版本号，每次保存递增",
    )
    skill_metadata: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        comment="扩展元数据（token_cost、related_skills 等）",
    )
