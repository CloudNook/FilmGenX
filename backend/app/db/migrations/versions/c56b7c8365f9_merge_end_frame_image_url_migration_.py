"""merge end_frame_image_url migration into head

Revision ID: c56b7c8365f9
Revises: n5o6p7q8r9s0, o7p8q9r0s1t2
Create Date: 2026-04-07 23:47:26.624357

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c56b7c8365f9'
down_revision: Union[str, Sequence[str], None] = ('n5o6p7q8r9s0', 'o7p8q9r0s1t2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
