"""add char_image_refs and location_image_refs to shots

Revision ID: 6c5286c1ae4a
Revises: k8l9m0n1o2p3
Create Date: 2026-04-06 12:44:17.588095

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6c5286c1ae4a'
down_revision: Union[str, Sequence[str], None] = 'k8l9m0n1o2p3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add reference image columns to shots table."""
    op.add_column(
        'shots',
        sa.Column('char_image_refs', postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'[]'::jsonb"),
                  comment='角色参考图：[{char_version_id, name, urls}]'))
    op.add_column(
        'shots',
        sa.Column('location_image_refs', postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'[]'::jsonb"),
                  comment='场景参考图：[{location_version_id, location_id, name, urls}]'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('shots', 'location_image_refs')
    op.drop_column('shots', 'char_image_refs')
