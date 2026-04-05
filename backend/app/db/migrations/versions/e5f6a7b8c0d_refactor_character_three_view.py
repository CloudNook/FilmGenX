"""refactor character three-view fields to single image

Revision ID: e5f6a7b8c0d
Revises: f7a8b9c0d1e2
Create Date: 2026-04-05 20:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "e5f6a7b8c0d"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'character_versions'
                  AND column_name = 'three_view_url'
            ) THEN
                ALTER TABLE character_versions
                ADD COLUMN three_view_url VARCHAR(500);
            END IF;

            ALTER TABLE character_versions DROP COLUMN IF EXISTS view_front_url;
            ALTER TABLE character_versions DROP COLUMN IF EXISTS view_side_url;
            ALTER TABLE character_versions DROP COLUMN IF EXISTS view_back_url;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'character_versions'
                  AND column_name = 'view_front_url'
            ) THEN
                ALTER TABLE character_versions
                ADD COLUMN view_front_url VARCHAR(500);
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'character_versions'
                  AND column_name = 'view_side_url'
            ) THEN
                ALTER TABLE character_versions
                ADD COLUMN view_side_url VARCHAR(500);
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'character_versions'
                  AND column_name = 'view_back_url'
            ) THEN
                ALTER TABLE character_versions
                ADD COLUMN view_back_url VARCHAR(500);
            END IF;

            ALTER TABLE character_versions DROP COLUMN IF EXISTS three_view_url;
        END $$;
        """
    )
