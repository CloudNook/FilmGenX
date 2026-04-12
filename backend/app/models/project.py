from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.scene import Scene
    from app.models.character import Character
    from app.models.asset import Asset
    from app.models.conversation import Conversation
    from app.models.location import Location
    from app.models.workspace import Workspace
    from app.models.supervisor_workflow import SupervisorWorkflow


class Project(Base):
    """项目表。一个项目对应一部作品（如《斗破苍穹》系列），包含该作品的所有生产数据。"""

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

    # Relations
    owner: Mapped["User"] = relationship("User", back_populates="projects")
    scenes: Mapped[List["Scene"]] = relationship("Scene", back_populates="project", cascade="all, delete-orphan")
    characters: Mapped[List["Character"]] = relationship("Character", back_populates="project", cascade="all, delete-orphan")
    locations: Mapped[List["Location"]] = relationship("Location", back_populates="project", cascade="all, delete-orphan")
    assets: Mapped[List["Asset"]] = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    conversations: Mapped[List["Conversation"]] = relationship("Conversation", back_populates="project", cascade="all, delete-orphan")
    workspaces: Mapped[List["Workspace"]] = relationship("Workspace", back_populates="project", cascade="all, delete-orphan")
    supervisor_workflows: Mapped[List["SupervisorWorkflow"]] = relationship("SupervisorWorkflow", back_populates="project", cascade="all, delete-orphan")
