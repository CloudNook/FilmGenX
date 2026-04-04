"""change asset file_url to text

Revision ID: h4i5j6k7l8m9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-04 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h4i5j6k7l8m9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change file_url from VARCHAR(500) to TEXT to accommodate long signed URLs
    op.alter_column(
        'assets',
        'file_url',
        existing_type=sa.String(500),
        type_=sa.Text,
        existing_nullable=False,
        comment='文件存储路径或URL'
    )


def downgrade() -> None:
    # Revert file_url back to VARCHAR(500)
    op.alter_column(
        'assets',
        'file_url',
        existing_type=sa.Text,
        type_=sa.String(500),
        existing_nullable=False,
        comment='文件存储路径或URL'
    )
