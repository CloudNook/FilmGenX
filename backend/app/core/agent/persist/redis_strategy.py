"""
Redis 持久化策略实现。

每条消息用 RPUSH 追加到 Redis List（agent:messages:{session_id}），
读取时用 LRANGE 全量拉取，按 seq 排序，返回 MessageRecord 列表。
"""

import json
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from app.core.agent.persist.base import PersistStrategy
from app.core.agent.persist.models import MessageRecord

if TYPE_CHECKING:
    from app.core.agent.base import AgentCheckpoint

# 会话消息默认保留 7 天
_DEFAULT_TTL_SECONDS = 7 * 24 * 3600


class RedisPersistStrategy(PersistStrategy):
    """
    Redis 持久化策略。

    数据结构：
        agent:messages:{session_id}  ->  Redis List
            每个元素是一条消息的 JSON 字符串，按写入顺序排列。

    使用方式：
        agent = create_agent(..., persist="redis")
    """

    name = "redis"

    def __init__(self, ttl: int = _DEFAULT_TTL_SECONDS) -> None:
        self.ttl = ttl

    async def load_messages(
        self,
        session_id: str,
    ) -> List[MessageRecord]:
        from app.utils import redis_client

        raw_list = await redis_client.lrange(f"agent:messages:{session_id}", 0, -1)
        records = [json.loads(item) for item in raw_list]
        records.sort(key=lambda m: m.get("seq", 0))
        return [
            MessageRecord(
                role=r["role"],
                content=r["content"],
                seq=r["seq"],
                loop_count=r.get("loop_count", 0),
                is_checkpoint=r.get("is_checkpoint", False),
                tool_call_id=r.get("tool_call_id"),
                tool_name=r.get("tool_name"),
                usage=r.get("usage"),
                extra_metadata=r.get("metadata") or {},
                supervisor_session_id=r.get("supervisor_session_id"),
            )
            for r in records
        ]

    async def append_message(
        self,
        session_id: str,
        request_id: str,
        agent_name: str,
        role: str,
        content: str,
        seq: int,
        loop_count: int = 0,
        *,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        usage: Optional[Dict[str, Any]] = None,
        supervisor_session_id: Optional[str] = None,
        is_checkpoint: bool = False,
    ) -> None:
        from app.utils import redis_client

        key = f"agent:messages:{session_id}"
        msg = {
            "session_id": session_id,
            "request_id": request_id,
            "agent_name": agent_name,
            "role": role,
            "content": content,
            "seq": seq,
            "loop_count": loop_count,
            "is_checkpoint": is_checkpoint,
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "usage": usage,
            "metadata": metadata or {},
            "supervisor_session_id": supervisor_session_id,
        }
        await redis_client.rpush(key, json.dumps(msg, ensure_ascii=False))
        await redis_client.expire(key, self.ttl)

    async def save_interrupt_state(
        self,
        session_id: str,
        checkpoint: "AgentCheckpoint",
    ) -> None:
        """
        保存中断时的最小快照：tool_call_id + tool_name + loop_count + context。

        中断信息存储在独立的 key 中。
        """
        from app.utils import redis_client

        key = f"agent:interrupt:{session_id}"
        data = {
            "tool_call_id": checkpoint.tool_call_id,
            "tool_name": checkpoint.tool_name,
            "loop_count": checkpoint.loop_count,
            "context": checkpoint.context,
            "available_actions": checkpoint.available_actions,
        }
        await redis_client.set(key, json.dumps(data, ensure_ascii=False).encode())
        await redis_client.expire(key, self.ttl)

    async def load_interrupt_state(
        self,
        session_id: str,
    ) -> "Optional[AgentCheckpoint]":
        """
        加载中断快照。

        从 Redis 独立 key 读取 tool_call_id + loop_count，
        从最后一条 is_checkpoint=True 的 assistant 消息恢复 tool_calls。
        """
        from app.utils import redis_client

        key = f"agent:interrupt:{session_id}"
        raw = await redis_client.get(key)
        if raw is None:
            return None
        data = json.loads(raw)

        # tool_calls 从 AgentMessageRecord 的 extra_metadata.tool_calls 中恢复
        from app.core.agent.base import AgentCheckpoint
        return AgentCheckpoint(
            tool_call_id=data["tool_call_id"],
            tool_name=data["tool_name"],
            arguments={},  # 从 tool_calls 中查找
            context=data.get("context", {}),
            available_actions=data.get("available_actions", ["approve", "reject"]),
            messages=[],  # 不再需要，resume 时从 load_messages 恢复
            loop_count=data.get("loop_count", 0),
        )

    async def clear_interrupt_state(self, session_id: str) -> None:
        from app.utils import redis_client

        key = f"agent:interrupt:{session_id}"
        await redis_client.delete(key)
