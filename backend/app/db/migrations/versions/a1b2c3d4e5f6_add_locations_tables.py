"""add locations and location_versions tables

Revision ID: a1b2c3d4e5f6
Revises: ed5c756b9728
Create Date: 2026-04-04 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e948853f5a72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 创建 locations 表
    op.create_table(
        'locations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),

        # 基础标识
        sa.Column('loc_code', sa.String(length=50), nullable=False,
                  comment='业务ID，如 LOC_YUNLAN_SQUARE'),
        sa.Column('name', sa.String(length=100), nullable=False,
                  comment='场景名称'),
        sa.Column('aliases', sa.JSON(), nullable=False, default=list,
                  comment='别名列表'),

        # 分类
        sa.Column('location_type', sa.String(length=20), nullable=False, default='outdoor',
                  comment='场景类型：indoor/outdoor/fantasy/mixed'),
        sa.Column('domain', sa.String(length=50), nullable=True,
                  comment='所属势力/领域'),

        # 场景描述
        sa.Column('description', sa.Text(), nullable=True,
                  comment='场景详细文字描述'),
        sa.Column('architectural_style', sa.String(length=100), nullable=True,
                  comment='建筑风格'),

        # 标志性元素
        sa.Column('key_elements', sa.JSON(), nullable=False, default=list,
                  comment='标志性元素'),

        # 默认环境配置
        sa.Column('default_atmosphere', sa.JSON(), nullable=True,
                  comment='默认氛围配置'),
        sa.Column('time_variants', sa.JSON(), nullable=True,
                  comment='时间变体描述'),

        # 生成提示词
        sa.Column('base_background_prompt', sa.Text(), nullable=True,
                  comment='背景生成基础提示词'),
        sa.Column('negative_prompt', sa.Text(), nullable=True,
                  comment='负面提示词'),
        sa.Column('style_preset', sa.String(length=100), nullable=True,
                  comment='风格预设'),

        # 参考素材
        sa.Column('reference_image_urls', sa.JSON(), nullable=False, default=list,
                  comment='参考图URL列表'),

        # 标签
        sa.Column('tags', sa.JSON(), nullable=False, default=list,
                  comment='标签'),

        # 状态
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True,
                  comment='是否启用'),
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0,
                  comment='被引用次数'),

        # 时间戳
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('loc_code'),
    )
    op.create_index(op.f('ix_locations_project_id'), 'locations', ['project_id'], unique=False)

    # 2. 创建 location_versions 表
    op.create_table(
        'location_versions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=False),

        # 版本标识
        sa.Column('version_code', sa.String(length=30), nullable=False,
                  comment='版本标识'),
        sa.Column('label', sa.String(length=100), nullable=False,
                  comment='版本显示名称'),

        # 变体描述
        sa.Column('description', sa.Text(), nullable=True,
                  comment='该变体的特殊描述'),

        # 环境覆盖
        sa.Column('atmosphere_override', sa.JSON(), nullable=True,
                  comment='覆盖主场景的氛围配置'),
        sa.Column('time_of_day', sa.String(length=20), nullable=True,
                  comment='时间：dawn/day/dusk/night'),
        sa.Column('weather', sa.String(length=30), nullable=True,
                  comment='天气'),

        # 特殊元素
        sa.Column('additional_elements', sa.JSON(), nullable=False, default=list,
                  comment='额外元素'),
        sa.Column('removed_elements', sa.JSON(), nullable=False, default=list,
                  comment='移除的元素'),

        # 生成提示词
        sa.Column('prompt_suffix', sa.Text(), nullable=True,
                  comment='追加到基础提示词后的内容'),
        sa.Column('full_prompt', sa.Text(), nullable=True,
                  comment='完整提示词'),

        # 参考素材
        sa.Column('reference_image_urls', sa.JSON(), nullable=False, default=list,
                  comment='该变体专属参考图'),

        # 使用场景
        sa.Column('applicable_scene_codes', sa.JSON(), nullable=False, default=list,
                  comment='适用的片段code列表'),

        # 标记
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False,
                  comment='是否为默认版本'),

        # 时间戳
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_location_versions_location_id'), 'location_versions', ['location_id'], unique=False)

    # 3. 为 shots 表添加 location 相关字段
    # 首先创建新的 location_id 列（整数外键）
    op.add_column('shots', sa.Column('location_id_new', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_shots_location_id', 'shots', 'locations', ['location_id_new'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_shots_location_id_new'), 'shots', ['location_id_new'], unique=False)

    # 添加 location_version_id 列
    op.add_column('shots', sa.Column('location_version_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_shots_location_version_id', 'shots', 'location_versions', ['location_version_id'], ['id'], ondelete='SET NULL')

    # 删除旧的 location_id 列，重命名新列
    op.drop_column('shots', 'location_id')
    op.alter_column('shots', 'location_id_new', new_column_name='location_id')

    # 4. 为 assets 表添加 location_id 字段
    op.add_column('assets', sa.Column('location_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_assets_location_id', 'assets', 'locations', ['location_id'], ['id'], ondelete='SET NULL')
    op.create_index(op.f('ix_assets_location_id'), 'assets', ['location_id'], unique=False)


def downgrade() -> None:
    # 1. 从 assets 表删除 location_id
    op.drop_index(op.f('ix_assets_location_id'), table_name='assets')
    op.drop_constraint('fk_assets_location_id', 'assets', type_='foreignkey')
    op.drop_column('assets', 'location_id')

    # 2. 从 shots 表恢复原来的 location_id（字符串）
    op.add_column('shots', sa.Column('location_id_new', sa.String(length=50), nullable=True))
    # 迁移数据：从 locations 表获取 loc_code
    op.execute("""
        UPDATE shots s
        SET location_id_new = (SELECT loc_code FROM locations WHERE id = s.location_id)
        WHERE s.location_id IS NOT NULL
    """)
    op.drop_constraint('fk_shots_location_version_id', 'shots', type_='foreignkey')
    op.drop_column('shots', 'location_version_id')
    op.drop_index(op.f('ix_shots_location_id'), table_name='shots')
    op.drop_constraint('fk_shots_location_id', 'shots', type_='foreignkey')
    op.drop_column('shots', 'location_id')
    op.alter_column('shots', 'location_id_new', new_column_name='location_id')

    # 3. 删除 location_versions 表
    op.drop_index(op.f('ix_location_versions_location_id'), table_name='location_versions')
    op.drop_table('location_versions')

    # 4. 删除 locations 表
    op.drop_index(op.f('ix_locations_project_id'), table_name='locations')
    op.drop_table('locations')
