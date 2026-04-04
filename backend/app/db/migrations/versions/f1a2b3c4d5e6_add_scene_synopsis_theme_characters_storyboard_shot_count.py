"""add scene synopsis/theme/characters and storyboard shot_count

Revision ID: f1a2b3c4d5e6
Revises: a1b2c3d4e5f6
Create Date: 2026-04-04

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # scenes 表新增剧本内容字段
    op.add_column('scenes', sa.Column('synopsis', sa.Text(), nullable=True, comment='剧情概述，100-300字'))
    op.add_column('scenes', sa.Column('theme', sa.String(200), nullable=True, comment='核心主题，一句话'))
    op.add_column('scenes', sa.Column('characters', sa.JSON(), nullable=True, comment='角色名列表'))

    # storyboards 表新增计划镜头数量
    op.add_column('storyboards', sa.Column('shot_count', sa.Integer(), nullable=True, comment='计划生成的镜头数量'))


def downgrade() -> None:
    op.drop_column('storyboards', 'shot_count')
    op.drop_column('scenes', 'characters')
    op.drop_column('scenes', 'theme')
    op.drop_column('scenes', 'synopsis')
