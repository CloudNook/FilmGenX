"""
对话会话模型。

一个 Conversation 对应一集动画的完整创作对话：
  - 包含与 AI 的多轮消息（Message）
  - 消息类型包括普通文本、剧本大纲草稿、已确认大纲
  - 所有历史消息永久保留，作为完整上下文
  - 确认后关联到 Scene，并触发分镜生成流程
"""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.scene import Scene


class Conversation(Base):
    """对话会话表。一集动画 = 一个 Conversation。"""

    __tablename__ = "conversations"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目",
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="新对话",
        comment="会话标题，如「第01集 - 药老现身」",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        comment="active | draft_ready | confirmed",
    )
    # 最新版剧本大纲（每次总结后覆盖，历史版本在 messages 中保留）
    latest_outline: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="最新 EpisodeOutline JSON，确认后同步到 Scene",
    )
    # 确认后关联的 Scene
    scene_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="确认后创建的分集 Scene ID",
    )

    # Relations
    project: Mapped["Project"] = relationship("Project", back_populates="conversations")
    scene: Mapped[Optional["Scene"]] = relationship("Scene", back_populates="conversation")
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.seq",
    )


class Message(Base):
    """消息表。Conversation 下的每一条消息，永久保留。"""

    __tablename__ = "messages"

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属会话",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="user | assistant | system",
    )
    # 消息类型，影响前端渲染方式，也是 AI 识别消息语义的标识
    type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="text",
        comment=(
            "text           — 普通对话消息\n"
            "outline_draft  — AI 生成的剧本大纲草稿（含 outline_data）\n"
            "outline_confirmed — 用户最终确认的大纲（只有一条）\n"
            "system_action  — 系统操作记录"
        ),
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="消息正文（Markdown 格式）",
    )
    # outline_draft / outline_confirmed 时存储结构化大纲 JSON
    outline_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="EpisodeOutline JSON，仅 outline_* 类型消息有值",
    )
    # 消息在会话中的顺序
    seq: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="消息序号（升序），用于保证排序稳定",
    )

    # Relations
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
