from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, Integer, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.storyboard import Storyboard
    from app.models.shot import Shot


class ShotGroup(Base):
    """分镜组表。多个分镜可归为一组，通过一次 Kling multi_shot 调用生成合并视频。"""

    __tablename__ = "shot_groups"

    storyboard_id: Mapped[int] = mapped_column(
        ForeignKey("storyboards.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 组标识
    group_code: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="组编号，如 DQCK_001_G001"
    )
    name: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="可读名称，如'战斗连段'"
    )
    sequence: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="组在分镜脚本中的顺序"
    )

    # 时长与视频
    total_duration_sec: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="成员分镜时长之和（须 ≤ 15s）"
    )
    video_url: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="合并视频 URL（OSS 永久链接）"
    )

    # 状态
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft",
        comment="draft | generating | review | approved | rejected"
    )

    # Phase 1 规划意图（来自 Planner AI）
    plan_intent: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Phase 1 规划的叙事意图（narrative_intent 字段）"
    )

    # Phase 2 Celery 任务 ID（预留，用于追踪并行创作进度）
    phase2_task_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
        comment="Phase 2 Creator AI 对应的 Celery 任务ID（预留）"
    )

    # Relations
    storyboard: Mapped["Storyboard"] = relationship("Storyboard", back_populates="shot_groups")
    shots: Mapped[List["Shot"]] = relationship(
        "Shot", back_populates="shot_group", order_by="Shot.sequence"
    )
