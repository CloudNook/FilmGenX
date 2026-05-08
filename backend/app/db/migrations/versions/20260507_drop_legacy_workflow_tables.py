"""drop legacy workflow tables and slim assets

老的工作流（scenes / storyboards / shots / shot_groups / characters / locations
/ generation_tasks / prompt_templates / conversations / messages）已经被
agent-driven supervisor 链路替代。这次迁移：

1. drop 上面所有老业务表
2. 把 assets 表里 shot_id / location_id / character_id / version / is_current /
   parent_asset_id 这 6 个绑定老业务表的字段删掉

Revision ID: 20260507drop_legacy
Revises: skill_claude_style
Create Date: 2026-05-07
"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260507drop_legacy"
down_revision = "skill_claude_style"
branch_labels = None
depends_on = None


# drop 顺序：先 drop 引用方再 drop 被引用方。CASCADE 兜底跨实例命名差异。
LEGACY_TABLES_DROP_ORDER = [
    "messages",
    "conversations",
    "generation_tasks",
    "prompt_templates",
    "shot_groups",
    "shots",
    "storyboards",
    "scenes",
    "characters",
    "locations",
]

# assets 表上需要 drop 的旧字段。直接 drop column 时 PG 会自动 drop 关联 FK；
# 用 IF EXISTS 兜底跨实例可能不一致的字段命名。
ASSETS_LEGACY_COLUMNS = [
    "shot_id",
    "location_id",
    "character_id",
    "version",
    "is_current",
    "parent_asset_id",
]


def upgrade() -> None:
    # 1. 删 assets 旧字段（FK 跟随字段一起 drop）
    for col in ASSETS_LEGACY_COLUMNS:
        op.execute(f'ALTER TABLE assets DROP COLUMN IF EXISTS {col} CASCADE')

    # 2. drop 所有老业务表
    for table in LEGACY_TABLES_DROP_ORDER:
        op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')


def downgrade() -> None:
    # 不可逆——这次重构已经把 ORM 层老业务全删了，回退也无意义。
    raise RuntimeError(
        "Drop-legacy migration is one-way; agent-driven refactor removed all ORM "
        "definitions for the dropped tables."
    )
