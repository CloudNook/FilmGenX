from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。

    每张表自动包含以下公共字段：
      - id:         主键，自增整数
      - created_at: 记录创建时间，由数据库自动填充
      - updated_at: 记录最后更新时间，每次 UPDATE 自动刷新
      - is_deleted: 软删除标记，True 表示已删除。
                    业务查询时必须加 WHERE is_deleted = FALSE，
                    使用 Repository 层的 active() 方法可自动过滤。
      - deleted_at: 软删除时间，is_deleted 置为 True 时同步记录
    """

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        comment="主键，自增整数"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="记录创建时间（UTC）"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="记录最后更新时间（UTC），每次 UPDATE 自动刷新"
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
        comment="软删除标记。True 表示已删除，业务查询必须过滤此字段"
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="软删除时间（UTC），is_deleted 为 True 时记录"
    )
