"""add shot_groups table and shot_group_id to shots

Revision ID: f7a8b9c0d1e2
Revises: 3aa19733f4b4
Create Date: 2026-04-05 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, Sequence[str], None] = '3aa19733f4b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 创建 shot_groups 表
    op.create_table(
        'shot_groups',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('storyboard_id', sa.Integer(), nullable=False),
        sa.Column('group_code', sa.String(50), nullable=False, comment='组编号，如 DQCK_001_G001'),
        sa.Column('name', sa.String(200), nullable=True, comment='可读名称'),
        sa.Column('sequence', sa.Integer(), nullable=False, comment='组在分镜脚本中的顺序'),
        sa.Column('total_duration_sec', sa.Float(), nullable=True, comment='成员分镜时长之和'),
        sa.Column('video_url', sa.Text(), nullable=True, comment='合并视频 URL'),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft', comment='draft | generating | review | approved | rejected'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['storyboard_id'], ['storyboards.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_shot_groups_storyboard_id', 'shot_groups', ['storyboard_id'])
    op.create_index('ix_shot_groups_group_code', 'shot_groups', ['group_code'])

    # 2. 给 shots 表添加 shot_group_id 列
    op.add_column('shots', sa.Column('shot_group_id', sa.Integer(), nullable=True, comment='所属分镜组 ID'))
    op.create_index('ix_shots_shot_group_id', 'shots', ['shot_group_id'])
    op.create_foreign_key('fk_shots_shot_group_id', 'shots', 'shot_groups', ['shot_group_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_shots_shot_group_id', 'shots', type_='foreignkey')
    op.drop_index('ix_shots_shot_group_id', table_name='shots')
    op.drop_column('shots', 'shot_group_id')
    op.drop_index('ix_shot_groups_group_code', table_name='shot_groups')
    op.drop_index('ix_shot_groups_storyboard_id', table_name='shot_groups')
    op.drop_table('shot_groups')
