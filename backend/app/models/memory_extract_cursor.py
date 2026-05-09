"""
Memory 抽取游标 —— 跟踪 (session_id, agent_name) 上次已抽到哪条 message。

Provider 用这张表实现 ``get_extract_cursor`` / ``set_extract_cursor``。framework
不直接感知这个表，通过 Protocol 接口操作。

cursor_key 由 framework 构造（``{session_id}:{agent_name}``），marker 也是 framework
约定的格式（``"seq:<n>"`` 或 ``"hash:<sha>"``）。表只做 KV 存储，不解释 marker 内容。
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MemoryExtractCursor(Base):
    """每个 (session_id, agent_name) 一条记录，记录上次 extract 推进到的 marker。"""

    __tablename__ = "memory_extract_cursors"

    cursor_key: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        unique=True,
        index=True,
        comment="格式 '{session_id}:{agent_name}'，由 MemoryHarness 构造",
    )
    marker: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="不透明字符串：'seq:<n>' 或 'hash:<sha>'，framework 决定语义",
    )
