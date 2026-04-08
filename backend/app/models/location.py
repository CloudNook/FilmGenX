"""
场景地点模型。

管理项目全局的场景/地点定义，如云岚宗广场、乌坦城萧家大院。
"""

from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
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

    # === 场景封面图 ===
    pic_name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="场景封面图片名称"
    )
    pic_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="场景封面图片URL"
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
    assets: Mapped[List["Asset"]] = relationship(
        "Asset",
        back_populates="location",
        primaryjoin="Asset.location_id == Location.id"
    )
