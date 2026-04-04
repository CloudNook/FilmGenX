"""refactor shots table - remove location/character foreign keys

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-04 20:00:00.000000

- Remove location_id and location_version_id foreign keys from shots
- Remove character_id foreign key from shots
- Change char_version_id to char_version_ids (JSON array)
- Add characters_config (JSON array) for multi-character support
- Merge location info into environment JSON field

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 删除 shots 表的外键约束和索引
    # 检查并删除 location_id 外键
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_shots_location_id'
                AND table_name = 'shots'
            ) THEN
                ALTER TABLE shots DROP CONSTRAINT fk_shots_location_id;
            END IF;
        END $$;
    """)

    # 检查并删除 location_version_id 外键
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_shots_location_version_id'
                AND table_name = 'shots'
            ) THEN
                ALTER TABLE shots DROP CONSTRAINT fk_shots_location_version_id;
            END IF;
        END $$;
    """)

    # 检查并删除 character_id 外键（如果存在）
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name LIKE '%character%'
                AND table_name = 'shots'
                AND constraint_type = 'FOREIGN KEY'
            ) THEN
                ALTER TABLE shots DROP CONSTRAINT IF EXISTS fk_shots_character_id;
                ALTER TABLE shots DROP CONSTRAINT IF EXISTS shots_character_id_fkey;
            END IF;
        END $$;
    """)

    # 删除相关索引
    op.execute("DROP INDEX IF EXISTS ix_shots_location_id;")
    op.execute("DROP INDEX IF EXISTS ix_shots_location_id_new;")
    op.execute("DROP INDEX IF EXISTS ix_shots_character_id;")

    # 2. 添加新字段
    # 添加 char_version_ids (JSON 数组)
    op.add_column('shots', sa.Column('char_version_ids', sa.JSON(), nullable=True, default=list,
                                     comment='角色版本ID列表'))

    # 添加 characters_config (JSON 数组)
    op.add_column('shots', sa.Column('characters_config', sa.JSON(), nullable=True,
                                      comment='多角色配置'))

    # 3. 迁移数据：将 char_version_id 转换为 char_version_ids 数组
    op.execute("""
        UPDATE shots
        SET char_version_ids = CASE
            WHEN char_version_id IS NOT NULL THEN json_build_array(char_version_id)
            ELSE '[]'::json
        END
        WHERE char_version_ids IS NULL;
    """)

    # 4. 迁移数据：将 location_id/location_version_id 合并到 environment
    op.execute("""
        UPDATE shots
        SET environment = json_build_object(
            'location_id', location_id,
            'location_version_id', location_version_id,
            'time_of_day', COALESCE(environment->>'time_of_day', 'day'),
            'weather', COALESCE(environment->>'weather', 'clear'),
            'lighting', environment->>'lighting',
            'atmosphere', environment->>'atmosphere'
        )
        WHERE location_id IS NOT NULL OR location_version_id IS NOT NULL;
    """)

    # 5. 删除旧字段
    op.drop_column('shots', 'location_id', if_exists=True)
    op.drop_column('shots', 'location_version_id', if_exists=True)
    op.drop_column('shots', 'character_id', if_exists=True)
    op.drop_column('shots', 'char_version_id', if_exists=True)
    op.drop_column('shots', 'character_action', if_exists=True)
    op.drop_column('shots', 'character_expression', if_exists=True)
    op.drop_column('shots', 'character_emotion_intensity', if_exists=True)
    op.drop_column('shots', 'character_sfx', if_exists=True)

    # 6. 设置 char_version_ids 默认值为空数组（如果仍为 NULL）
    op.execute("UPDATE shots SET char_version_ids = '[]'::json WHERE char_version_ids IS NULL;")


def downgrade() -> None:
    # 1. 恢复旧字段
    op.add_column('shots', sa.Column('location_id', sa.Integer(), nullable=True))
    op.add_column('shots', sa.Column('location_version_id', sa.Integer(), nullable=True))
    op.add_column('shots', sa.Column('character_id', sa.Integer(), nullable=True))
    op.add_column('shots', sa.Column('char_version_id', sa.Integer(), nullable=True))
    op.add_column('shots', sa.Column('character_action', sa.Text(), nullable=True))
    op.add_column('shots', sa.Column('character_expression', sa.Text(), nullable=True))
    op.add_column('shots', sa.Column('character_emotion_intensity', sa.Integer(), nullable=True))
    op.add_column('shots', sa.Column('character_sfx', sa.JSON(), nullable=True))

    # 2. 恢复外键约束
    op.create_foreign_key('fk_shots_location_id', 'shots', 'locations',
                          ['location_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_shots_location_version_id', 'shots', 'location_versions',
                          ['location_version_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_shots_character_id', 'shots', 'characters',
                          ['character_id'], ['id'], ondelete='SET NULL')

    # 3. 迁移数据：从 char_version_ids 数组取第一个值
    op.execute("""
        UPDATE shots
        SET char_version_id = (char_version_ids->>0)::integer
        WHERE char_version_ids IS NOT NULL AND json_array_length(char_version_ids) > 0;
    """)

    # 4. 从 environment 恢复 location_id
    op.execute("""
        UPDATE shots
        SET location_id = (environment->>'location_id')::integer
        WHERE environment->>'location_id' IS NOT NULL;
    """)
    op.execute("""
        UPDATE shots
        SET location_version_id = (environment->>'location_version_id')::integer
        WHERE environment->>'location_version_id' IS NOT NULL;
    """)

    # 5. 删除新字段
    op.drop_column('shots', 'char_version_ids')
    op.drop_column('shots', 'characters_config')

    # 6. 创建索引
    op.create_index('ix_shots_location_id', 'shots', ['location_id'])
    op.create_index('ix_shots_character_id', 'shots', ['character_id'])
