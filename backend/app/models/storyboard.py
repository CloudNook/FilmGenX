from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, Integer, String, Text, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.scene import Scene
    from app.models.shot import Shot


class Storyboard(Base):
    """分镜脚本表。一个高光片段（Scene）对应一份分镜脚本。"""

    __tablename__ = "storyboards"

    scene_id: Mapped[int] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # 叙事设计
    emotion_curve: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="情感弧线数据，格式：[{time_sec: 0, intensity: 2, label: '压抑开场'}, ...]"
    )
    narrative_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="叙事设计备注")
    pacing_ratio: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="节奏比例，格式：{buildup: 30, climax: 40, resolution: 30}"
    )

    # 计划镜头数量（由 confirm 时传入）
    shot_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="计划生成的镜头数量")

    # 整体时长（秒）
    total_duration_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 版本与状态
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft",
        comment="draft | generating | review | approved"
    )

    # Relations
    scene: Mapped["Scene"] = relationship("Scene", back_populates="storyboard")
    shots: Mapped[List["Shot"]] = relationship(
        "Shot", back_populates="storyboard", cascade="all, delete-orphan", order_by="Shot.sequence"
    )
