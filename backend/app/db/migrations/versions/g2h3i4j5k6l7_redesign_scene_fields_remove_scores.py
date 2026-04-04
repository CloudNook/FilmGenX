"""redesign scene fields: remove scores, add narrative/visual/production fields

Revision ID: g2h3i4j5k6l7
Revises: f1a2b3c4d5e6
Create Date: 2026-04-04

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'g2h3i4j5k6l7'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 删除评分字段
    op.drop_column('scenes', 'score_dramatic_tension')
    op.drop_column('scenes', 'score_visual_potential')
    op.drop_column('scenes', 'score_emotional_resonance')
    op.drop_column('scenes', 'score_narrative_importance')
    op.drop_column('scenes', 'score_audience_familiarity')
    op.drop_column('scenes', 'score_total')

    # 新增叙事结构字段
    op.add_column('scenes', sa.Column('story_arc', sa.Text(), nullable=True, comment='叙事弧，开头→冲突→结尾'))
    op.add_column('scenes', sa.Column('key_events', sa.JSON(), nullable=True, comment='关键剧情节点列表'))
    op.add_column('scenes', sa.Column('emotional_arc', sa.Text(), nullable=True, comment='情绪走势'))

    # 新增角色字段
    op.add_column('scenes', sa.Column('character_focus', sa.Text(), nullable=True, comment='核心角色心理状态和变化'))

    # 新增场景设定字段
    op.add_column('scenes', sa.Column('primary_location', sa.String(200), nullable=True, comment='主要地点'))
    op.add_column('scenes', sa.Column('location_atmosphere', sa.Text(), nullable=True, comment='场景氛围'))

    # 新增视觉与制作字段
    op.add_column('scenes', sa.Column('visual_highlights', sa.JSON(), nullable=True, comment='视觉亮点列表'))
    op.add_column('scenes', sa.Column('color_palette', sa.String(200), nullable=True, comment='主色调方向'))
    op.add_column('scenes', sa.Column('bgm_direction', sa.String(200), nullable=True, comment='音乐方向'))
    op.add_column('scenes', sa.Column('storyboard_style_notes', sa.Text(), nullable=True, comment='给分镜AI的详细风格指导'))

    # 新增上下文衔接字段
    op.add_column('scenes', sa.Column('previous_episode_hint', sa.Text(), nullable=True, comment='上一集结尾简述'))
    op.add_column('scenes', sa.Column('next_episode_hint', sa.Text(), nullable=True, comment='本集结尾悬念/钩子'))

    # 设置 key_events / visual_highlights 默认值
    op.execute("UPDATE scenes SET key_events = '[]' WHERE key_events IS NULL")
    op.execute("UPDATE scenes SET visual_highlights = '[]' WHERE visual_highlights IS NULL")


def downgrade() -> None:
    op.drop_column('scenes', 'next_episode_hint')
    op.drop_column('scenes', 'previous_episode_hint')
    op.drop_column('scenes', 'storyboard_style_notes')
    op.drop_column('scenes', 'bgm_direction')
    op.drop_column('scenes', 'color_palette')
    op.drop_column('scenes', 'visual_highlights')
    op.drop_column('scenes', 'location_atmosphere')
    op.drop_column('scenes', 'primary_location')
    op.drop_column('scenes', 'character_focus')
    op.drop_column('scenes', 'emotional_arc')
    op.drop_column('scenes', 'key_events')
    op.drop_column('scenes', 'story_arc')

    op.add_column('scenes', sa.Column('score_dramatic_tension', sa.Integer(), nullable=True))
    op.add_column('scenes', sa.Column('score_visual_potential', sa.Integer(), nullable=True))
    op.add_column('scenes', sa.Column('score_emotional_resonance', sa.Integer(), nullable=True))
    op.add_column('scenes', sa.Column('score_narrative_importance', sa.Integer(), nullable=True))
    op.add_column('scenes', sa.Column('score_audience_familiarity', sa.Integer(), nullable=True))
    op.add_column('scenes', sa.Column('score_total', sa.Integer(), nullable=True))
