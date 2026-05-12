from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


class Asset(Base):
    """Project-scoped asset (image / video / audio / reference)."""

    __tablename__ = "assets"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Project ID",
    )

    asset_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="Business asset code",
    )
    name: Mapped[Optional[str]] = mapped_column(
        String(120),
        nullable=True,
        comment="Human-readable name (character/scene name, etc). Used as @图N alias in prompts.",
    )
    asset_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="image / video / audio / reference",
    )
    file_url: Mapped[str] = mapped_column(Text, nullable=False, comment="File URL")
    file_format: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="File format",
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="File size in bytes",
    )

    width: Mapped[Optional[int]] = mapped_column(comment="Width in pixels")
    height: Mapped[Optional[int]] = mapped_column(comment="Height in pixels")
    duration_sec: Mapped[Optional[float]] = mapped_column(comment="Duration in seconds")

    source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="generated",
        comment="generated / uploaded",
    )
    generator: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Generator or tool name",
    )

    tags: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="Search tags",
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Description")

    project: Mapped["Project"] = relationship("Project", back_populates="assets")
