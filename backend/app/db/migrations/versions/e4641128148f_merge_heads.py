"""merge_heads

Revision ID: e4641128148f
Revises: dc6362d2a13e, f6a7b8c9d0e1
Create Date: 2026-04-05 15:09:13.704643

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4641128148f'
down_revision: Union[str, Sequence[str], None] = ('dc6362d2a13e', 'f6a7b8c9d0e1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
