from typing import Optional
from sqlalchemy import ForeignKey, Integer, String, Text, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PromptTemplate(Base):
    """提示词版本模板表。管理图像生成提示词的版本历史与性能记录，支持迭代优化。"""

    __tablename__ = "prompt_templates"

    # 所属范围（可以是角色版本、地点、特效等维度的模板）
    template_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="模板业务ID，如 CHAR_XIAO_YAN_v2_battle_stance"
    )
    template_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="模板类型：character / location / effect / scene_style"
    )

    # 版本
    version: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="版本号，如 v1.0 / v1.3"
    )
    is_current: Mapped[bool] = mapped_column(
        default=True,
        comment="是否为该 template_code 的当前最优版本"
    )

    # 提示词内容
    base_prompt: Mapped[str] = mapped_column(Text, nullable=False, comment="基础提示词（英文）")
    style_suffix: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="风格后缀，如 'donghua animation style, cinematic lighting'")
    negative_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="负向提示词")

    # 模型参数
    model_params: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="生成参数，如 {cfg_scale: 7, steps: 30, sampler: 'dpm++'}"
    )
    lora_config: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="LoRA 配置，如 {model: 'xiao_yan_v2', weight: 0.8}"
    )

    # 性能记录
    result_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="该版本平均评分（0-10）")
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="使用次数")

    # 版本变更记录
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="相比上一版本的改动原因")
    issue_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="发现的问题描述（如：面部偏日式风格）")
    fix_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="修复方法描述")

    # 关联上一版本
    parent_template_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("prompt_templates.id", ondelete="SET NULL"),
        nullable=True,
        comment="上一版本的模板ID"
    )
