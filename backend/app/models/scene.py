from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.storyboard import Storyboard
    from app.models.conversation import Conversation


class Scene(Base):
    """高光片段表。记录从原著中选取的高光片段及其完整剧本信息。"""

    __tablename__ = "scenes"

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    # 业务标识
    scene_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, comment="业务ID，如 P1_EP001")

    # 基本信息
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    synopsis: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="200-400字剧情概述")
    theme: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="核心主题，一句话")

    # 原著映射
    novel_chapter_start: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="起始章节")
    novel_chapter_end: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="结束章节")
    novel_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="原著关键段落摘录")

    # 叙事结构（JSON 存储）
    story_arc: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="叙事弧，开头→冲突→结尾")
    key_events: Mapped[list] = mapped_column(JSON, nullable=False, default=list, comment="关键剧情节点列表")
    emotional_arc: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="情绪走势")

    # 角色
    characters: Mapped[list] = mapped_column(JSON, nullable=False, default=list, comment="角色名列表")
    character_focus: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="核心角色心理状态和变化")
    character_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list, comment="关联角色ID列表")

    # 场景设定
    primary_location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="主要地点")
    location_atmosphere: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="场景氛围")

    # 视觉与制作
    visual_highlights: Mapped[list] = mapped_column(JSON, nullable=False, default=list, comment="视觉亮点列表")
    color_palette: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="主色调方向")
    bgm_direction: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="音乐方向")

    # 分镜指导
    storyboard_style_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="给分镜AI的详细风格指导")

    # 上下文衔接
    previous_episode_hint: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="上一集结尾简述")
    next_episode_hint: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="本集结尾悬念/钩子")

    # 分类与制作参数
    scene_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list, comment="场景类型标签")
    priority: Mapped[str] = mapped_column(String(2), nullable=False, default="A", comment="S/A/B/C")
    estimated_duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="预估时长（秒）")

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft",
        comment="draft | in_production | completed"
    )

    # Relations
    project: Mapped["Project"] = relationship("Project", back_populates="scenes")
    storyboard: Mapped[Optional["Storyboard"]] = relationship("Storyboard", back_populates="scene", uselist=False, cascade="all, delete-orphan")
    conversation: Mapped[Optional["Conversation"]] = relationship("Conversation", back_populates="scene", uselist=False)
