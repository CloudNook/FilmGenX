"""remove_location_redundant_fields

Revision ID: 3b4c5d6e7f8
Revises: 2a3b4c5d6e7f
Create Date: 2026-04-09 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = '2a3b4c5d6e7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove redundant fields from locations table.

    Only drops columns that currently exist in the DB (created by a1b2c3d4e5f6).
    Columns from location_versions table (atmosphere_override, time_of_day, etc.)
    were already dropped when location_versions was removed in 1f6731cb7ef2.
    """
    # 描述字段
    op.drop_column('locations', 'description')
    op.drop_column('locations', 'architectural_style')
    # 标志性元素
    op.drop_column('locations', 'key_elements')
    # 环境配置
    op.drop_column('locations', 'default_atmosphere')
    op.drop_column('locations', 'time_variants')
    # 生成提示词
    op.drop_column('locations', 'base_background_prompt')
    op.drop_column('locations', 'negative_prompt')
    op.drop_column('locations', 'style_preset')
    # 参考图
    op.drop_column('locations', 'reference_image_urls')
    # 标签（冗余）
    op.drop_column('locations', 'tags')


def downgrade() -> None:
    """Restore location redundant fields."""
    op.add_column('locations', sa.Column('tags', sa.JSON(), nullable=False, server_default='[]', comment='标签'))
    op.add_column('locations', sa.Column('reference_image_urls', sa.JSON(), nullable=False, server_default='[]', comment='参考图URL列表'))
    op.add_column('locations', sa.Column('style_preset', sa.String(length=100), nullable=True, comment='风格预设'))
    op.add_column('locations', sa.Column('negative_prompt', sa.Text(), nullable=True, comment='负面提示词'))
    op.add_column('locations', sa.Column('base_background_prompt', sa.Text(), nullable=True, comment='背景生成基础提示词'))
    op.add_column('locations', sa.Column('time_variants', sa.JSON(), nullable=True, comment='时间变体描述'))
    op.add_column('locations', sa.Column('default_atmosphere', sa.JSON(), nullable=True, comment='默认氛围配置'))
    op.add_column('locations', sa.Column('key_elements', sa.JSON(), nullable=False, server_default='[]', comment='标志性元素'))
    op.add_column('locations', sa.Column('architectural_style', sa.String(length=100), nullable=True, comment='建筑风格'))
    op.add_column('locations', sa.Column('description', sa.Text(), nullable=True, comment='场景详细文字描述'))
