from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.supervisor_workflow import SupervisorWorkflow
    from app.models.user import User
    from app.models.workspace import Workspace


class Project(Base):
    """项目表。一个 project 即一部作品 / 剧本，跨会话生成不同集数的容器。"""

    __tablename__ = "projects"

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="项目所有者的用户ID，所有查询均需校验此字段实现用户隔离"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="项目名称")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="项目描述")
    novel_title: Mapped[str] = mapped_column(String(100), nullable=False, comment="原著名称")
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="封面图URL")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", comment="active | archived"
    )

    owner: Mapped["User"] = relationship("User", back_populates="projects")
    assets: Mapped[List["Asset"]] = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    workspaces: Mapped[List["Workspace"]] = relationship("Workspace", back_populates="project", cascade="all, delete-orphan")
    supervisor_workflows: Mapped[List["SupervisorWorkflow"]] = relationship("SupervisorWorkflow", back_populates="project", cascade="all, delete-orphan")
