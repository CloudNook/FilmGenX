"""merge shot_group continuity fields into main branch

Revision ID: n5o6p7q8r9s0
Revises: 6c5286c1ae4a, m3n4o5p6q7r8
Create Date: 2026-04-06 16:05:00.000000

Merge two parallel branches:
- 6c5286c1ae4a: add char_image_refs and location_image_refs to shots
- m3n4o5p6q7r8: add prev_shot_group_id and end_frame_description to shot_groups

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'n5o6p7q8r9s0'
down_revision: Union[str, None] = ('6c5286c1ae4a', 'm3n4o5p6q7r8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass  # No-op: schema changes already applied by individual branch migrations


def downgrade() -> None:
    pass  # No-op: do not reverse merge
