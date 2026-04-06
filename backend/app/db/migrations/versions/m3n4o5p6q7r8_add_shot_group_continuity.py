"""add shot_group continuity fields (prev_shot_group_id, end_frame_description)

Revision ID: m3n4o5p6q7r8
Revises: k8l9m0n1o2p3
Create Date: 2026-04-06 16:00:00.000000

- Add prev_shot_group_id FK for cross-group continuity chain
- Add end_frame_description (TEXT) for Phase 3 Director output

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'm3n4o5p6q7r8'
down_revision: Union[str, None] = 'k8l9m0n1o2p3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # prev_shot_group_id: 前一分镜组 ID（自引用 FK）
    op.add_column(
        'shot_groups',
        sa.Column(
            'prev_shot_group_id',
            sa.Integer(),
            sa.ForeignKey('shot_groups.id', ondelete='SET NULL'),
            nullable=True,
            index=True,
            comment='前一分镜组 ID，用于组间画面连续性',
        ),
    )
    # end_frame_description: Phase 3 导演输出的终态描述
    op.add_column(
        'shot_groups',
        sa.Column(
            'end_frame_description',
            sa.Text(),
            nullable=True,
            comment='Phase 3 导演输出的本组终态描述（中文），供下一组参考',
        ),
    )


def downgrade() -> None:
    op.drop_column('shot_groups', 'end_frame_description')
    op.drop_column('shot_groups', 'prev_shot_group_id')
