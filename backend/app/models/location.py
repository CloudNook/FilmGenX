"""
场景地点模型。

管理项目全局的场景/地点定义，如云岚宗广场、乌坦城萧家大院。
支持多版本变体，如「云岚宗广场·夜晚」或「云岚宗广场·战斗损毁」。
"""

from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, Integer, String, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.asset import Asset


class Location(Base):
    """场景地点表。管理项目全局的场景/地点定义。"""

    __tablename__ = "locations"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目ID"
    )

    # === 基础标识 ===
    loc_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        comment="业务ID，如 LOC_YUNLAN_SQUARE、LOC_XIAO_FAMILY_HALL"
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="场景名称，如 '云岚宗广场'"
    )
    aliases: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="别名列表，如 ['云岚宗山门', '云岚宗主殿前']"
    )

    # === 分类 ===
    location_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="outdoor",
        comment="场景类型：indoor(室内) / outdoor(室外) / fantasy(玄幻场景) / mixed(混合)"
    )
    domain: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="所属势力/领域，如 '云岚宗' / '萧家' / '沙漠'"
    )

    # === 场景描述 ===
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="场景详细文字描述"
    )
    architectural_style: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="建筑风格，如 '中国古风' / '异域沙漠' / '玄幻仙宫'"
    )

    # === 标志性元素 ===
    key_elements: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="标志性元素，如 ['九十九级白玉台阶', '巨大石碑', '云雾缭绕']"
    )

    # === 默认环境配置 ===
    default_atmosphere: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="默认氛围配置：{weather, lighting, mood, color_tone}"
    )

    # === 时间变体配置 ===
    time_variants: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="时间变体描述：{dawn: '...', day: '...', dusk: '...', night: '...'}"
    )

    # === 生成提示词 ===
    base_background_prompt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="背景生成基础提示词（英文），变体提示词在此基础上修改"
    )
    negative_prompt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="负面提示词"
    )
    style_preset: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="风格预设"
    )

    # === 参考素材 ===
    reference_image_urls: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="参考图URL列表"
    )

    # === 标签 ===
    tags: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="标签，如 ['云岚宗', '正道', '广场', '室外']"
    )

    # === 状态 ===
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否启用"
    )
    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="被引用次数（统计用）"
    )

    # === Relations ===
    project: Mapped["Project"] = relationship("Project", back_populates="locations")
    versions: Mapped[List["LocationVersion"]] = relationship(
        "LocationVersion",
        back_populates="location",
        cascade="all, delete-orphan",
        order_by="LocationVersion.id"
    )
    assets: Mapped[List["Asset"]] = relationship(
        "Asset",
        back_populates="location",
        primaryjoin="Asset.location_id == Location.id"
    )


class LocationVersion(Base):
    """场景变体表。同一场景的不同状态，如「云岚宗广场·战损状态」或「云岚宗广场·夜晚」。"""

    __tablename__ = "location_versions"

    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属场景ID"
    )

    # === 版本标识 ===
    version_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="版本标识，如 'default' / 'night' / 'battle_damaged' / 'rain'"
    )
    label: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="版本显示名称，如 '夜晚' / '战斗损毁' / '雨天'"
    )

    # === 变体描述 ===
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="该变体的特殊描述，与主场景描述叠加"
    )

    # === 环境覆盖 ===
    atmosphere_override: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="覆盖主场景的氛围配置"
    )
    time_of_day: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="时间：dawn / day / dusk / night"
    )
    weather: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="天气：clear / cloudy / rain / snow / fog / storm"
    )

    # === 特殊元素 ===
    additional_elements: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="额外元素，如 ['战火痕迹', '破碎的石柱']"
    )
    removed_elements: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="移除的元素，如 ['石碑']（被摧毁）"
    )

    # === 生成提示词 ===
    prompt_suffix: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="追加到基础提示词后的内容"
    )
    full_prompt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="完整提示词（如与基础差异大，可直接覆盖）"
    )

    # === 参考素材 ===
    reference_image_urls: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="该变体专属参考图"
    )

    # === 使用场景 ===
    applicable_scene_codes: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="适用的片段code列表（可选，用于推荐）"
    )

    # === 标记 ===
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否为默认版本"
    )

    # === Relations ===
    location: Mapped["Location"] = relationship("Location", back_populates="versions")
