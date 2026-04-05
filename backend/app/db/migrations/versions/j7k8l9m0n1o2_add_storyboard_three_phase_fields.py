"""add storyboard three-phase generation fields

Revision ID: j7k8l9m0n1o2
Revises: i6j7k8l9m0n1
Create Date: 2026-04-05 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j7k8l9m0n1o2'
down_revision: Union[str, None] = 'e4641128148f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # storyboards: add generation_phase and plan_data for three-phase pipeline
    op.add_column(
        'storyboards',
        sa.Column(
            'generation_phase',
            sa.String(30),
            nullable=True,
            comment='phase1_planning | phase2_creating | phase3_directing | completed'
        )
    )
    op.add_column(
        'storyboards',
        sa.Column(
            'plan_data',
            sa.JSON(),
            nullable=True,
            comment='Phase 1 Planner AI output — group-level plan'
        )
    )

    # shot_groups: add plan_intent and phase2_task_id
    op.add_column(
        'shot_groups',
        sa.Column(
            'plan_intent',
            sa.Text(),
            nullable=True,
            comment='Narrative intent from Phase 1 Planner AI'
        )
    )
    op.add_column(
        'shot_groups',
        sa.Column(
            'phase2_task_id',
            sa.String(100),
            nullable=True,
            comment='Celery task ID for this group Phase 2 Creator task (reserved)'
        )
    )


def downgrade() -> None:
    op.drop_column('shot_groups', 'phase2_task_id')
    op.drop_column('shot_groups', 'plan_intent')
    op.drop_column('storyboards', 'plan_data')
    op.drop_column('storyboards', 'generation_phase')
