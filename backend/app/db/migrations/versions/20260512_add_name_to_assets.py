"""add name to assets

Revision ID: 20260512_assets_name
Revises: 20260509ws_sv_settings
Create Date: 2026-05-12

把 ``assets.name`` 加上——前端展示用人类可读的名字（如 "萧炎"、"云岚宗广场"）
代替 asset_code；Seedance prompt 注入 "name=@图片N" 别名时也直接查这一列，
不再走 memory KV 反查。可空——老 asset 没名字直接读 ``asset_code`` 兜底。
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260512_assets_name"
down_revision: Union[str, Sequence[str], None] = "20260509ws_sv_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assets",
        sa.Column(
            "name",
            sa.String(length=120),
            nullable=True,
            comment="Human-readable name (character/scene name, etc). Used as @图N alias in prompts.",
        ),
    )


def downgrade() -> None:
    op.drop_column("assets", "name")
