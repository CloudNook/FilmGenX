"""remove_version_tables_and_simplify_character

Revision ID: 1f6731cb7ef2
Revises: ff631c82aeb7
Create Date: 2026-04-09 00:16:19.026497

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1f6731cb7ef2'
down_revision: Union[str, Sequence[str], None] = 'ff631c82aeb7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove version tables, simplify character model."""
    # 1. assets 表：先删除 location_version_id（外键依赖 location_versions）
    op.drop_index(op.f('ix_assets_location_version_id'), table_name='assets')
    op.drop_constraint(op.f('fk_assets_location_version_id'), 'assets', type_='foreignkey')
    op.drop_column('assets', 'location_version_id')

    # 2. 删除版本表（assets FK 已移除，可安全删除）
    op.drop_index(op.f('ix_location_versions_is_deleted'), table_name='location_versions')
    op.drop_index(op.f('ix_location_versions_location_id'), table_name='location_versions')
    op.drop_table('location_versions')
    op.drop_index(op.f('ix_character_versions_character_id'), table_name='character_versions')
    op.drop_index(op.f('ix_character_versions_is_deleted'), table_name='character_versions')
    op.drop_table('character_versions')

    # 3. characters 表：精简字段
    op.add_column('characters', sa.Column('pic_name', sa.String(length=200), nullable=True, comment='角色图片名称'))
    op.add_column('characters', sa.Column('pic_url', sa.String(length=500), nullable=True, comment='角色图片URL'))
    op.drop_column('characters', 'name_aliases')
    op.drop_column('characters', 'consistent_features')
    op.drop_column('characters', 'expression_guide')
    op.drop_column('characters', 'action_guide')
    op.drop_column('characters', 'relationships')
    op.drop_column('characters', 'role_description')


def downgrade() -> None:
    """Revert: restore version tables and character fields."""
    # 3. characters 表：恢复字段
    op.add_column('characters', sa.Column('role_description', sa.TEXT(), nullable=True))
    op.add_column('characters', sa.Column('relationships', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('characters', sa.Column('action_guide', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('characters', sa.Column('expression_guide', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('characters', sa.Column('consistent_features', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('characters', sa.Column('name_aliases', postgresql.JSON(astext_type=sa.Text()), nullable=False))
    op.drop_column('characters', 'pic_url')
    op.drop_column('characters', 'pic_name')

    # 2. 恢复版本表（先创建表，再恢复 assets FK）
    op.create_table('character_versions',
        sa.Column('character_id', sa.INTEGER(), nullable=False),
        sa.Column('version_code', sa.VARCHAR(length=30), nullable=False),
        sa.Column('label', sa.VARCHAR(length=100), nullable=False),
        sa.Column('applicable_chapter_start', sa.VARCHAR(length=50), nullable=True),
        sa.Column('applicable_chapter_end', sa.VARCHAR(length=50), nullable=True),
        sa.Column('age_description', sa.VARCHAR(length=50), nullable=True),
        sa.Column('height_cm', sa.INTEGER(), nullable=True),
        sa.Column('build_description', sa.TEXT(), nullable=True),
        sa.Column('face_description', sa.TEXT(), nullable=True),
        sa.Column('hair_description', sa.TEXT(), nullable=True),
        sa.Column('costumes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('dou_qi_color', sa.VARCHAR(length=10), nullable=True),
        sa.Column('dou_qi_level', sa.VARCHAR(length=20), nullable=True),
        sa.Column('key_features', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('reference_image_urls', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('base_image_prompt', sa.TEXT(), nullable=True),
        sa.Column('three_view_url', sa.VARCHAR(length=500), nullable=True),
        sa.Column('state_images', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.BOOLEAN(), server_default=sa.text('false'), nullable=False),
        sa.Column('deleted_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_character_versions_character_id'), 'character_versions', ['character_id'], unique=False)
    op.create_index(op.f('ix_character_versions_is_deleted'), 'character_versions', ['is_deleted'], unique=False)

    op.create_table('location_versions',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('location_id', sa.INTEGER(), nullable=False),
        sa.Column('version_code', sa.VARCHAR(length=30), nullable=False),
        sa.Column('label', sa.VARCHAR(length=100), nullable=False),
        sa.Column('description', sa.TEXT(), nullable=True),
        sa.Column('atmosphere_override', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('time_of_day', sa.VARCHAR(length=20), nullable=True),
        sa.Column('weather', sa.VARCHAR(length=30), nullable=True),
        sa.Column('additional_elements', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('removed_elements', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('prompt_suffix', sa.TEXT(), nullable=True),
        sa.Column('full_prompt', sa.TEXT(), nullable=True),
        sa.Column('reference_image_urls', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('applicable_scene_codes', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('is_default', sa.BOOLEAN(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.BOOLEAN(), server_default=sa.text('false'), nullable=False),
        sa.Column('deleted_at', postgresql.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_location_versions_location_id'), 'location_versions', ['location_id'], unique=False)
    op.create_index(op.f('ix_location_versions_is_deleted'), 'location_versions', ['is_deleted'], unique=False)

    # 1. assets 表：恢复 location_version_id（版本表已恢复，可创建 FK）
    op.add_column('assets', sa.Column('location_version_id', sa.INTEGER(), nullable=True))
    op.create_foreign_key(op.f('fk_assets_location_version_id'), 'assets', 'location_versions', ['location_version_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_assets_location_version_id'), 'assets', ['location_version_id'], unique=False)
