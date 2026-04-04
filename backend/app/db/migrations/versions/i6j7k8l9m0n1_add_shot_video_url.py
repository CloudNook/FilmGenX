"""add shot video_url

Revision ID: i6j7k8l9m0n1
Revises: h4i5j6k7l8m9
Create Date: 2026-04-05 00:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i6j7k8l9m0n1'
down_revision: Union[str, None] = 'h4i5j6k7l8m9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add video_url column to shots table for storing generated video URL
    op.add_column('shots', sa.Column('video_url', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove video_url column from shots table
    op.drop_column('shots', 'video_url')
