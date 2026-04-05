"""add location_version_id to assets

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c0d
Create Date: 2026-04-05 12:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("location_version_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_assets_location_version_id"), "assets", ["location_version_id"], unique=False)
    op.create_foreign_key(
        "fk_assets_location_version_id",
        "assets",
        "location_versions",
        ["location_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_assets_location_version_id", "assets", type_="foreignkey")
    op.drop_index(op.f("ix_assets_location_version_id"), table_name="assets")
    op.drop_column("assets", "location_version_id")
