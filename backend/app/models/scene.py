from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.storyboard import Storyboard


class Scene(Base):
    """高光片段表。记录从原著中选取的高光片段及其评分数据。"""

    __tablename__ = "scenes"

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    # 片段基本信息
    scene_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, comment="业务ID，如 DQCK_001")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    novel_chapter_start: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="起始章节")
    novel_chapter_end: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="结束章节")
    novel_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="原著关键段落摘录")

    # 分类
    scene_types: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="片段类型列表：战斗高光/情感高潮/成长节点/世界观展开/反转时刻"
    )
    priority: Mapped[str] = mapped_column(String(2), nullable=False, default="A", comment="S/A/B/C")

    # 评分（各维度 0-10）
    score_dramatic_tension: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="戏剧张力")
    score_visual_potential: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="视觉化潜力")
    score_emotional_resonance: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="情感共鸣度")
    score_narrative_importance: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="叙事重要性")
    score_audience_familiarity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="粉丝熟知度")
    score_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="总分（满50）")

    # 涉及角色（存储 character_id 列表）
    character_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # 预估时长（秒）
    estimated_duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft",
        comment="draft | scored | in_production | completed"
    )

    # Relations
    project: Mapped["Project"] = relationship("Project", back_populates="scenes")
    storyboard: Mapped[Optional["Storyboard"]] = relationship("Storyboard", back_populates="scene", uselist=False, cascade="all, delete-orphan")
