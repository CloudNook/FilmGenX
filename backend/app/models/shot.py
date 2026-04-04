from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, Integer, String, Text, JSON, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.storyboard import Storyboard
    from app.models.asset import Asset
    from app.models.task import GenerationTask
    from app.models.location import Location, LocationVersion


class Shot(Base):
    """单镜头表。分镜脚本中的最小生产单元，存储完整的分镜描述信息。"""

    __tablename__ = "shots"

    storyboard_id: Mapped[int] = mapped_column(ForeignKey("storyboards.id", ondelete="CASCADE"), nullable=False, index=True)

    # 镜头标识
    shot_code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True, comment="业务ID，如 DQCK_001_S003")
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, comment="在分镜脚本中的顺序")
    duration_sec: Mapped[float] = mapped_column(Float, nullable=False, default=3.0)

    # 摄像机参数
    camera: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="摄像机配置：{shot_type, angle, movement, focal_length, depth_of_field}"
    )

    # 构图
    composition: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="构图描述：{subject_position, foreground, midground, background, leading_lines}"
    )

    # 角色
    character_id: Mapped[Optional[int]] = mapped_column(ForeignKey("characters.id", ondelete="SET NULL"), nullable=True, index=True)
    char_version_id: Mapped[Optional[int]] = mapped_column(ForeignKey("character_versions.id", ondelete="SET NULL"), nullable=True)
    character_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="角色动作描述")
    character_expression: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="表情描述")
    character_emotion_intensity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="情绪强度 1-10")
    character_sfx: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="角色特效：{dou_qi_color, dou_qi_pattern, aura_intensity, particle_effects}"
    )

    # 环境
    location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="场景地点ID"
    )
    location_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("location_versions.id", ondelete="SET NULL"),
        nullable=True,
        comment="场景变体ID（使用非默认版本时填写）"
    )
    environment: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="环境配置：{time_of_day, weather, lighting, atmosphere}"
    )

    # 台词
    dialogue_character: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    dialogue_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dialogue_delivery: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="台词情感参数：{tone, pace, pause_positions, emphasis_words, emotion_tags}"
    )

    # 音频
    sound_design: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="音效设计：{ambient, sfx_list, music}"
    )

    # 转场
    transition_in: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="入场转场类型")
    transition_out: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="出场转场类型")
    transition_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 分镜依赖关系
    dependencies: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
        comment="依赖的其他镜头列表：[{type, depends_on_shot_id, dependency_detail}]"
    )

    # 生成提示词
    image_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    style_preset: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 质量审核
    qc_character_consistency: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    qc_lighting_match: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    qc_action_continuity: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    qc_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    qc_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="整体评分 0-100")

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft",
        comment="draft | generating | review | approved | rejected"
    )

    # Relations
    storyboard: Mapped["Storyboard"] = relationship("Storyboard", back_populates="shots")
    location: Mapped[Optional["Location"]] = relationship("Location", back_populates="shots")
    location_version: Mapped[Optional["LocationVersion"]] = relationship("LocationVersion", back_populates="shots")
    assets: Mapped[List["Asset"]] = relationship("Asset", back_populates="shot", cascade="all, delete-orphan")
    generation_tasks: Mapped[List["GenerationTask"]] = relationship("GenerationTask", back_populates="shot", cascade="all, delete-orphan")
