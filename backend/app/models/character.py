from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.asset import Asset


class Character(Base):
    """角色档案表。存储角色的基础信息。"""

    __tablename__ = "characters"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目ID"
    )
    char_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        comment="角色业务ID，如 CHAR_XIAO_YAN"
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="角色名称")
    pic_name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="角色图片名称"
    )
    pic_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="角色图片URL"
    )

    # Relations
    project: Mapped["Project"] = relationship("Project", back_populates="characters")
    assets: Mapped[List["Asset"]] = relationship(
        "Asset",
        back_populates="character",
        cascade="all, delete-orphan",
    )
