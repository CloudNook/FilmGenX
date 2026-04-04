"""add is_deleted column to locations and location_versions

Revision ID: c3d4e5f6a7b8
Revises: g2h3i4j5k6l7
Create Date: 2026-04-04 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'g2h3i4j5k6l7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 为 locations 表添加 is_deleted 字段（deleted_at 已存在）
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'locations' AND column_name = 'is_deleted'
            ) THEN
                ALTER TABLE locations ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
                CREATE INDEX ix_locations_is_deleted ON locations(is_deleted);
            END IF;
        END $$;
    """)

    # 为 location_versions 表添加 is_deleted 字段
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'location_versions' AND column_name = 'is_deleted'
            ) THEN
                ALTER TABLE location_versions ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
                CREATE INDEX ix_location_versions_is_deleted ON location_versions(is_deleted);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'location_versions' AND column_name = 'deleted_at'
            ) THEN
                ALTER TABLE location_versions ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_location_versions_is_deleted;
        ALTER TABLE location_versions DROP COLUMN IF EXISTS is_deleted;
        ALTER TABLE location_versions DROP COLUMN IF EXISTS deleted_at;
    """)

    op.execute("""
        DROP INDEX IF EXISTS ix_locations_is_deleted;
        ALTER TABLE locations DROP COLUMN IF EXISTS is_deleted;
    """)
