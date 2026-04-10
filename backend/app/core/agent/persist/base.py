"""
持久化策略抽象。

定义 PersistStrategy 接口，各实现策略（Redis/DB）遵循此协议。
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class PersistStrategy(ABC):
    """
    持久化策略抽象基类。

    Agent 执行过程中的持久化操作通过策略实现：
    - save_session(): 创建会话记录
    - append_message(): 追加消息
    - update_session(): 更新会话状态

    使用方式：
        agent = create_agent(
            ...
            persist="redis",  # 或 "db"
        )
    """

    name: str  # 策略名称，如 "redis" | "db"

    @abstractmethod
    async def save_session(
        self,
        session_id: str,
        request_id: str,
        agent_name: str,
        initial_input: str,
        started_at: datetime,
    ) -> None:
        """
        创建会话记录。

        Args:
            session_id: 会话 ID（多轮对话）
            request_id: 请求 ID（单次执行）
            agent_name: Agent 名称
            initial_input: 初始输入
            started_at: 开始时间
        """
        ...

    @abstractmethod
    async def append_message(
        self,
        session_id: str,
        request_id: str,
        agent_name: str,
        role: str,
        content: str,
        *,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
        seq: int = 0,
    ) -> None:
        """
        追加一条消息。

        Args:
            session_id: 会话 ID
            request_id: 请求 ID
            agent_name: Agent 名称
            role: 消息角色（user/assistant/system/tool）
            content: 消息内容
            tool_call_id: 工具调用 ID
            tool_name: 工具名称
            extra_metadata: 附加元数据
            seq: 消息序号
        """
        ...

    @abstractmethod
    async def update_session(
        self,
        session_id: str,
        loop_count: int,
        schema_data: Optional[Dict[str, Any]],
        raw_output: Optional[str],
        error: Optional[str],
        finished: bool,
        finished_at: datetime,
    ) -> None:
        """
        更新会话最终状态。

        Args:
            session_id: 会话 ID
            loop_count: 循环次数
            schema_data: 结构化输出
            raw_output: 原始输出
            error: 错误信息
            finished: 是否正常结束
            finished_at: 结束时间
        """
        ...

    @abstractmethod
    async def load_messages(
        self,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        """
        根据 session_id 加载完整消息历史。

        Args:
            session_id: 会话 ID

        Returns:
            消息记录列表（按 seq 排序）
        """
        ...

    @abstractmethod
    async def load_session(
        self,
        session_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        根据 session_id 加载会话信息。

        Args:
            session_id: 会话 ID

        Returns:
            会话信息字典，不存在则 None
        """
        ...
