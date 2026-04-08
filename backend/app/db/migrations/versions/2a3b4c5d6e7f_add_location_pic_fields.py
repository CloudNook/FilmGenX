"""add_location_pic_fields

Revision ID: 2a3b4c5d6e7f
Revises: 1f6731cb7ef2
Create Date: 2026-04-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2a3b4c5d6e7f'
down_revision: Union[str, Sequence[str], None] = '1f6731cb7ef2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pic_name and pic_url to locations."""
    op.add_column('locations', sa.Column('pic_name', sa.String(length=200), nullable=True, comment='场景封面图片名称'))
    op.add_column('locations', sa.Column('pic_url', sa.String(length=500), nullable=True, comment='场景封面图片URL'))


def downgrade() -> None:
    """Remove location pic fields."""
    op.drop_column('locations', 'pic_name')
    op.drop_column('locations', 'pic_url')
