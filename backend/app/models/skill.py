"""
Skill 模型（Claude SKILL.md 风格）。

设计原则与 Anthropic Agent Skills 一致，按渐进式披露三层组织：
- L1 元信息：name + description + target_agents + tags（启动时注入 system prompt）
- L2 主体：body（agent 调 ``load_skill(name)`` 时按需加载）
- L3 引用：references（agent 调 ``load_skill_reference(name, key)`` 时按需加载）

@ 引用语法（在 body / reference body 内书写）：
- @ref:<key>             指向当前 skill 的某个 reference 章节
- @skill:<name>          指向另一个 skill 整体（LLM 决策是否 load_skill）
- @skill:<name>#<key>    指向另一个 skill 的某个 reference（LLM 决策）

跨 skill 引用是 hint，框架不自动 fetch；所有 load 由 LLM 通过工具调用完成。
"""

from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

if TYPE_CHECKING:
    pass


class Skill(Base):
    """Skill 存储模型（Claude SKILL.md 风格 + target_agents 扩展）。"""

    __tablename__ = "skills"

    # === L1 frontmatter 字段 ===
    name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="唯一标识，小写字母/数字/连字符；agent 通过此名调用 load_skill",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="激活条件描述，建议用 'Use when... to...' 句式；agent 据此判断是否 load",
    )
    target_agents: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="此 skill 适用的 sub-agent 列表；L1 注入时按 agent 名反查",
    )
    tags: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="标签列表，用于 admin 端筛选",
    )
    author: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="作者",
    )

    # === L2 主体 ===
    body: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="SKILL.md body markdown；agent 调 load_skill(name) 时返回",
    )

    # === L3 引用文件 ===
    # 结构：[{"key": "...", "title": "...", "body": "..."}, ...]
    # body 中通过 @ref:<key> 引用；agent 调 load_skill_reference(name, key) 时返回
    references: Mapped[List[dict]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="引用文件列表，每项 {key, title, body}；body 内用 @ref:<key> 显式引用",
    )

    # === 系统字段 ===
    raw_markdown: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="原始 Markdown 全文（每次上传覆盖）",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用，未启用则 agent 不会加载",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="版本号，每次保存递增",
    )
    skill_metadata: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="扩展元数据（est_tokens / 变更日志等，半结构化）",
    )
