from typing import TYPE_CHECKING, Optional
from sqlalchemy import ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.shot import Shot
    from app.models.location import Location


class Asset(Base):
    """素材表。存储所有生成或上传的文件元数据（图片、视频片段、音频）。"""

    __tablename__ = "assets"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目ID"
    )
    shot_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("shots.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="关联镜头ID，全局素材（如角色参考图、场景素材）可为空"
    )
    location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联场景ID（场景素材时使用）"
    )

    # 文件信息
    asset_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="素材业务ID，遵循命名规范，如 CHAR_XIAO_YAN_v2_portrait_front_normal"
    )
    asset_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="素材类型：image / video / audio / reference"
    )
    file_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="文件存储路径或URL"
    )
    file_format: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="文件格式，如 png / mp4 / wav"
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="文件大小（字节）"
    )

    # 图片/视频尺寸
    width: Mapped[Optional[int]] = mapped_column(comment="宽度（像素）")
    height: Mapped[Optional[int]] = mapped_column(comment="高度（像素）")
    duration_sec: Mapped[Optional[float]] = mapped_column(comment="视频/音频时长（秒）")

    # 来源标记
    source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="generated",
        comment="素材来源：generated（AI生成）/ uploaded（手动上传）"
    )
    generator: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="生成工具，如 stable_diffusion / midjourney / runway / kling"
    )

    # 分类标签
    tags: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="标签列表，便于检索，如 ['萧炎', 'v2', '战斗状态']"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="素材说明")

    # 版本管理
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="版本号，同一镜头重新生成时递增")
    is_current: Mapped[bool] = mapped_column(comment="是否为当前使用版本", default=True)
    parent_asset_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        comment="上一版本的素材ID"
    )

    # Relations
    project: Mapped["Project"] = relationship("Project", back_populates="assets")
    shot: Mapped[Optional["Shot"]] = relationship("Shot", back_populates="assets")
    location: Mapped[Optional["Location"]] = relationship("Location", back_populates="assets")
