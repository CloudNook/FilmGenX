from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey, String, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.shot import Shot


class GenerationTask(Base):
    """AI 生成任务表。追踪所有异步生成任务的状态与结果。"""

    __tablename__ = "generation_tasks"

    shot_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("shots.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="关联镜头ID，场景级任务（如分镜脚本批量生成）可为空"
    )

    # 任务标识
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        comment="Celery 任务ID，用于查询任务状态"
    )
    task_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="任务类型：image_generation / video_generation / storyboard_generation / audio_generation / qc_check"
    )

    # 状态
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="任务状态：pending / running / success / failed / cancelled"
    )
    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="进度百分比 0-100"
    )

    # 输入参数
    input_params: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="任务输入参数快照（提示词、模型参数等），便于重试和审计"
    )

    # 结果
    result_asset_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        comment="生成成功后关联的素材ID"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="失败时的错误信息"
    )

    # 时间记录
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="任务开始时间")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="任务完成时间")

    # 重试次数
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="已重试次数")
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3, comment="最大重试次数")

    # Relations
    shot: Mapped[Optional["Shot"]] = relationship("Shot", back_populates="generation_tasks")
