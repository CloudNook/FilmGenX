"""
持久化策略抽象。

Agent 每次从 LLM 收到消息后，通过此接口写入持久化存储。
进入 run() 时通过 load_messages() 恢复历史上下文。
与 middleware 完全解耦，AgentLoop 内部直接驱动。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from app.core.agent.persist.models import AgentMessageRecord, MessageRecord


class PersistStrategy(ABC):
    """
    持久化策略抽象基类。

    两个职责：
    - load_messages(): run() 开始时加载该 session 的历史消息
    - append_message(): 每条新消息产生后写入
    """

    name: str  # "redis" | "db"

    @abstractmethod
    async def load_messages(
        self,
        session_id: str,
    ) -> "List[Union[AgentMessageRecord, MessageRecord]]":
        """
        加载 session 的全部历史消息，按 seq 升序排列。

        在 AgentLoop.run() 开始时调用，用于恢复多轮对话上下文。

        Returns:
            消息记录列表，字段：role / content / seq / tool_call_id /
            tool_name / usage / extra_metadata
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
        seq: int,
        *,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        usage: Optional[Dict[str, Any]] = None,
        supervisor_session_id: Optional[str] = None,
    ) -> None:
        """
        追加一条消息记录。

        每次 LLM 返回或工具执行完毕后由 AgentLoop 直接调用。

        Args:
            session_id:    会话 ID
            request_id:    单次执行 ID
            agent_name:    Agent 名称
            role:          user / assistant / tool
            content:       消息内容
            seq:           全局序号，= 历史最大 seq + 1，保证跨 request 连续
            tool_call_id:  role=tool 时的调用 ID
            tool_name:     role=tool 时的工具名
            metadata:      附加元数据
            supervisor_session_id: Supervisor session ID（sv- 前缀），SubAgent 消息追溯到 Supervisor 流水线
        """
        ...

