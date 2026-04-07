"""Add end_frame_image_url to shot_groups for cross-group video chaining.

Revision ID: o7p8q9r0s1t2
Revises: m3n4o5p6q7r8
Create Date: 2026-04-07

本字段存储每组分镜组视频的末帧截图 URL。
下一组分镜组生成视频时，读取上一组的末帧截图作为 image_start，
实现组间画面衔接（前一镜头的尾 = 后一镜头的头）。
"""
from alembic import op
import sqlalchemy as sa


revision = "o7p8q9r0s1t2"
down_revision = "m3n4o5p6q7r8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shot_groups",
        sa.Column(
            "end_frame_image_url",
            sa.Text(),
            nullable=True,
            comment="本组视频的末帧截图 URL，用于下一组的 image_start",
        ),
    )


def downgrade() -> None:
    op.drop_column("shot_groups", "end_frame_image_url")
