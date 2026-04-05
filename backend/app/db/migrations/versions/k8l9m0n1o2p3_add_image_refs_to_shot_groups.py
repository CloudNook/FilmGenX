"""add image reference fields to shot_groups

Revision ID: k8l9m0n1o2p3
Revises: j7k8l9m0n1o2
Create Date: 2026-04-05 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k8l9m0n1o2p3'
down_revision: Union[str, None] = 'j7k8l9m0n1o2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add structured image_references column
    op.add_column(
        'shot_groups',
        sa.Column(
            'image_references',
            sa.JSON(),
            nullable=False,
            server_default='[]',
            comment='参考图列表：[{char_version_id, url, label}]'
        )
    )
    op.add_column(
        'shot_groups',
        sa.Column(
            'image_start_url',
            sa.Text(),
            nullable=True,
            comment='视频首帧图片URL'
        )
    )
    # Drop legacy columns if they exist (from earlier version of this migration)
    op.execute("ALTER TABLE shot_groups DROP COLUMN IF EXISTS character_image_urls")
    op.execute("ALTER TABLE shot_groups DROP COLUMN IF EXISTS location_image_urls")


def downgrade() -> None:
    op.drop_column('shot_groups', 'image_start_url')
    op.drop_column('shot_groups', 'image_references')
