"""add character image fields (views and state images)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-04 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'character_versions' AND column_name = 'view_front_url') THEN
                ALTER TABLE character_versions ADD COLUMN view_front_url VARCHAR(500);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'character_versions' AND column_name = 'view_side_url') THEN
                ALTER TABLE character_versions ADD COLUMN view_side_url VARCHAR(500);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'character_versions' AND column_name = 'view_back_url') THEN
                ALTER TABLE character_versions ADD COLUMN view_back_url VARCHAR(500);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'character_versions' AND column_name = 'state_images') THEN
                ALTER TABLE character_versions ADD COLUMN state_images JSON;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE character_versions DROP COLUMN IF EXISTS view_front_url;
        ALTER TABLE character_versions DROP COLUMN IF EXISTS view_side_url;
        ALTER TABLE character_versions DROP COLUMN IF EXISTS view_back_url;
        ALTER TABLE character_versions DROP COLUMN IF EXISTS state_images;
    """)
