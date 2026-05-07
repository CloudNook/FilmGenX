"""skill_claude_style_restructure

把 skills 表重构为 Claude SKILL.md 风格：
- 加 target_agents (JSONB list[str]) / body (Text) / references (JSONB list[obj])
- 把旧 content 数据迁到 body；examples / constraints / parameters 拼到 body 末尾
- 删除 title / content / examples / constraints / parameters / category / difficulty 字段
- 保留 name / description / tags / author / raw_markdown / is_active / version / skill_metadata

向下迁移会还原结构（不还原内容）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "skill_claude_style"
down_revision: Union[str, None] = "y2z3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 加新字段（先 nullable，迁完数据再收紧）
    op.add_column(
        "skills",
        sa.Column(
            "target_agents",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "skills",
        sa.Column("body", sa.Text(), nullable=True),
    )
    op.add_column(
        "skills",
        sa.Column(
            "references",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )

    # 2. 迁数据：content → body；examples / constraints / parameters 拼到 body 末尾的 markdown 章节
    #    旧字段都还在，可以读。这里用 SQL 字符串拼接 + jsonb_pretty 兜底；
    #    若不存在或为空，直接用 content。
    op.execute(
        """
        UPDATE skills
        SET body = (
            COALESCE(content, '')
            || CASE
                WHEN examples IS NOT NULL AND jsonb_array_length(examples) > 0
                THEN E'\\n\\n## examples\\n\\n' || (
                    SELECT string_agg('- ' || (e #>> '{}'), E'\\n')
                    FROM jsonb_array_elements(examples) AS e
                )
                ELSE ''
            END
            || CASE
                WHEN constraints IS NOT NULL AND jsonb_array_length(constraints) > 0
                THEN E'\\n\\n## constraints\\n\\n' || (
                    SELECT string_agg('- ' || (c #>> '{}'), E'\\n')
                    FROM jsonb_array_elements(constraints) AS c
                )
                ELSE ''
            END
            || CASE
                WHEN parameters IS NOT NULL AND parameters::text NOT IN ('{}', 'null')
                THEN E'\\n\\n## parameters\\n\\n```json\\n' || jsonb_pretty(parameters) || E'\\n```'
                ELSE ''
            END
        )
        """
    )

    # 3. 删旧字段
    op.drop_column("skills", "title")
    op.drop_column("skills", "content")
    op.drop_column("skills", "examples")
    op.drop_column("skills", "constraints")
    op.drop_column("skills", "parameters")
    op.drop_index("ix_skills_category", table_name="skills")
    op.drop_column("skills", "category")
    op.drop_column("skills", "difficulty")

    # 4. 给 target_agents 加 GIN 索引，反查时高效
    op.execute(
        "CREATE INDEX ix_skills_target_agents ON skills USING GIN (target_agents)"
    )


def downgrade() -> None:
    # 还原结构（不还原数据；body 内容会丢）
    op.execute("DROP INDEX IF EXISTS ix_skills_target_agents")

    op.add_column(
        "skills",
        sa.Column("difficulty", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "skills",
        sa.Column("category", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_skills_category", "skills", ["category"])
    op.add_column(
        "skills",
        sa.Column(
            "parameters",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "skills",
        sa.Column(
            "constraints",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "skills",
        sa.Column(
            "examples",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "skills",
        sa.Column("content", sa.Text(), nullable=True),
    )
    op.add_column(
        "skills",
        sa.Column("title", sa.String(length=128), nullable=True),
    )

    # 把 body 拷回 content（不还原拼接前的 examples / constraints / parameters）
    op.execute("UPDATE skills SET content = body")

    op.drop_column("skills", "references")
    op.drop_column("skills", "body")
    op.drop_column("skills", "target_agents")
