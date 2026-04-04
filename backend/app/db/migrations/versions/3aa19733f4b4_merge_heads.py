"""merge_heads

Revision ID: 3aa19733f4b4
Revises: d4e5f6a7b8c9, i6j7k8l9m0n1
Create Date: 2026-04-05 01:07:27.056028

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3aa19733f4b4'
down_revision: Union[str, Sequence[str], None] = ('d4e5f6a7b8c9', 'i6j7k8l9m0n1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
