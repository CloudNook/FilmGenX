"""
Memory 实体型条目 —— upsert by (scope, entity_kind, entity_key)。

存储 KV 精确召回的 memory：角色当前 asset_code、场景当前定义、用户偏好的核心
key、视觉风格锚等"实体当前态"。

不需要 vector 列 —— 业务 Provider 实现时用 (scope, entity_kind, entity_key) 三元组
精确查。如果以后需要语义模糊召回 profile（"找跟陈墨气质类似的角色"），可以让
Provider 顺路同时写一份到 memory_entries 做向量索引，profile 表保持纯 KV。
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MemoryProfile(Base):
    """实体型 memory（当前态快照）。

    设计要点：
    - **upsert**：同 (scope, entity_kind, entity_key) 的新值覆盖旧值
    - **superseded_at**：旧值不删，做软覆盖；为 NULL 表示当前生效
    - **value JSONB**：业务自定义结构（asset_code / 角色档案 / 风格锚 / 等）
    - **scope JSONB + GIN**：与 memory_entries 同款隔离
    """

    __tablename__ = "memory_profile"

    scope: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="业务 scope：{project_id, user_id, ...}",
    )
    entity_kind: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="实体大类：character / scene / asset / preference / visual_style / ...",
    )
    entity_key: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="实体业务 key：'陈墨' / 'preference_color_palette' / 'project_42_visual_style'",
    )
    value: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="实体当前值；业务自定义 JSON 结构",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        server_default="1.0",
        comment="置信度 [0, 1]",
    )
    superseded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="被新版本覆盖的时间；NULL 表示当前生效行",
    )
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="业务附加字段（source / agent_name / 等）",
    )

    __table_args__ = (
        # 当前生效行只允许一条：用 partial unique index（superseded_at IS NULL）
        # 不能直接 UniqueConstraint 因为我们要保留历史行
        Index(
            "uq_memory_profile_active",
            "scope",
            "entity_kind",
            "entity_key",
            unique=True,
            postgresql_where="superseded_at IS NULL AND is_deleted = FALSE",
        ),
        Index("ix_memory_profile_scope_gin", "scope", postgresql_using="gin"),
        Index("ix_memory_profile_entity", "entity_kind", "entity_key"),
    )
