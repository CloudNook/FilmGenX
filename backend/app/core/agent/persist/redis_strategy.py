"""
Redis 持久化策略实现。

每条消息用 RPUSH 追加到 Redis List（agent:messages:{session_id}），
读取时用 LRANGE 全量拉取，按 seq 排序，返回 MessageRecord 列表。
"""

import json
from typing import Any, Dict, List, Optional

from app.core.agent.persist.base import PersistStrategy
from app.core.agent.persist.models import MessageRecord

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
                tool_call_id=r.get("tool_call_id"),
                tool_name=r.get("tool_name"),
                usage=r.get("usage"),
                extra_metadata=r.get("metadata") or {},
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
        *,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        usage: Optional[Dict[str, Any]] = None,
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
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "usage": usage,
            "metadata": metadata or {},
        }
        await redis_client.rpush(key, json.dumps(msg, ensure_ascii=False))
        await redis_client.expire(key, self.ttl)
