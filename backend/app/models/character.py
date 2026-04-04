from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


class Character(Base):
    """角色档案表。存储角色的基础信息，具体外形状态由 CharacterVersion 管理。"""

    __tablename__ = "characters"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目ID"
    )
    char_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
        comment="角色业务ID，如 CHAR_XIAO_YAN"
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="角色名称")
    name_aliases: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="别名列表，如 ['小炎', '药尊']"
    )

    # 固定特征（跨版本不变）
    consistent_features: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="跨版本不变的固定特征，如 {eyes: '漆黑色瞳仁', skin: '小麦色'}"
    )

    # 表情指南
    expression_guide: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="各情绪状态的表情描述，如 {anger: '眉心微蹙...', determination: '眼神直视...'}"
    )

    # 动作指南
    action_guide: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="常见动作姿态描述，如 {standing_default: '...', battle_stance: '...'}"
    )

    # 角色关系（存储关联角色的描述）
    relationships: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="角色关系描述，如 {CHAR_YAO_LAO: {relation: '师徒', desc: '核心导师'}}"
    )

    role_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="角色在故事中的地位和作用简述"
    )

    # Relations
    project: Mapped["Project"] = relationship("Project", back_populates="characters")
    versions: Mapped[List["CharacterVersion"]] = relationship(
        "CharacterVersion",
        back_populates="character",
        cascade="all, delete-orphan",
        order_by="CharacterVersion.id"
    )


class CharacterVersion(Base):
    """角色状态版本表。同一角色在不同阶段的外形、服装、斗气颜色等状态。"""

    __tablename__ = "character_versions"

    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属角色ID"
    )
    version_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="版本标识，如 v1_teen / v2_post_training"
    )
    label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="版本显示名称，如 '少年期（15-16岁）'"
    )

    # 适用范围
    applicable_chapter_start: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="该版本适用的起始章节，如 '第1章'"
    )
    applicable_chapter_end: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="该版本适用的结束章节，如 '第50章'"
    )

    # 外形描述
    age_description: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="年龄描述")
    height_cm: Mapped[Optional[int]] = mapped_column(comment="身高（厘米）")
    build_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="体型描述，如 '瘦削，肩膀略窄'")
    face_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="面部描述")
    hair_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="发型描述")

    # 服装（按场景分类）
    costumes: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="服装配置，如 {default: '白色粗布长袍...', battle: '白袍轻微战损'}"
    )

    # 斗气
    dou_qi_color: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="斗气颜色HEX值，如 #FFB830"
    )
    dou_qi_level: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="对应境界，如 斗灵/斗王/斗皇"
    )

    # 标志性特征
    key_features: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="标志性细节，如 ['左耳佩戴玉坠', '右手无名指疤痕']"
    )

    # 参考图素材路径
    reference_image_urls: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="该版本的参考图URL列表"
    )

    # 三视图（角色标准视图）
    view_front_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="正面视图URL"
    )
    view_side_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="侧面视图URL"
    )
    view_back_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="背面视图URL"
    )

    # 状态图片（按情绪/动作分类）
    state_images: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="状态图片URL字典，如 {anger: 'url', skill_release: 'url', happy: 'url'}"
    )

    # 生成提示词（该版本专属基础提示词）
    base_image_prompt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="该版本的图像生成基础提示词（英文）"
    )

    # Relations
    character: Mapped["Character"] = relationship("Character", back_populates="versions")
