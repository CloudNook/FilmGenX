"""add_character_id_to_assets

Revision ID: dc6362d2a13e
Revises: e5f6a7b8c0d
Create Date: 2026-04-05 14:56:35.492860

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc6362d2a13e'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'assets'
                  AND column_name = 'character_id'
            ) THEN
                ALTER TABLE assets
                ADD COLUMN character_id INTEGER NULL;

                ALTER TABLE assets
                ADD CONSTRAINT fk_assets_character_id
                FOREIGN KEY (character_id)
                REFERENCES characters(id)
                ON DELETE SET NULL;

                CREATE INDEX IF NOT EXISTS ix_assets_character_id
                ON assets(character_id);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'assets'
                  AND column_name = 'character_id'
            ) THEN
                DROP INDEX IF EXISTS ix_assets_character_id;
                ALTER TABLE assets DROP CONSTRAINT IF EXISTS fk_assets_character_id;
                ALTER TABLE assets DROP COLUMN character_id;
            END IF;
        END $$;
        """
    )
