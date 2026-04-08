from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.character import Character
    from app.models.location import Location
    from app.models.project import Project
    from app.models.shot import Shot


class Asset(Base):
    """Asset metadata for uploaded and generated files."""

    __tablename__ = "assets"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Project ID",
    )
    shot_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("shots.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Related shot ID",
    )
    location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Related location ID",
    )
    character_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Related character ID",
    )

    asset_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="Business asset code",
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

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Asset version number",
    )
    is_current: Mapped[bool] = mapped_column(comment="Whether this is the current version", default=True)
    parent_asset_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        comment="Previous asset version ID",
    )

    project: Mapped["Project"] = relationship("Project", back_populates="assets")
    shot: Mapped[Optional["Shot"]] = relationship("Shot", back_populates="assets")
    location: Mapped[Optional["Location"]] = relationship("Location", back_populates="assets")
    character: Mapped[Optional["Character"]] = relationship("Character", back_populates="assets")
