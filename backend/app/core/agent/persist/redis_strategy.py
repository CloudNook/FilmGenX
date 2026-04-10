"""
Redis 持久化策略实现。

每条消息用 RPUSH 追加到 Redis List（agent:messages:{session_id}），
读取时用 LRANGE 全量拉取，按 seq 排序。
"""

from typing import Any, Dict, List, Optional
import json

from app.core.agent.persist.base import PersistStrategy


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

    async def load_messages(
        self,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        from app.utils import redis_client

        raw_list = await redis_client.lrange(f"agent:messages:{session_id}", 0, -1)
        messages = [json.loads(item) for item in raw_list]
        return sorted(messages, key=lambda m: m.get("seq", 0))

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
    ) -> None:
        from app.utils import redis_client

        msg = {
            "session_id": session_id,
            "request_id": request_id,
            "agent_name": agent_name,
            "role": role,
            "content": content,
            "seq": seq,
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "metadata": metadata or {},
        }
        await redis_client.rpush(
            f"agent:messages:{session_id}",
            json.dumps(msg, ensure_ascii=False),
        )
