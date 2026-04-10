"""
Redis 持久化策略实现。

将 Agent 执行数据存储到 Redis。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.agent.persist.base import PersistStrategy


class RedisPersistStrategy(PersistStrategy):
    """
    Redis 持久化策略。

    数据存储结构：
    - agent:session:{session_id} -> Session JSON
    - agent:messages:{session_id} -> [Message JSON, ...]

    注意：需确保 Redis 服务可用。
    """

    name = "redis"

    async def save_session(
        self,
        session_id: str,
        request_id: str,
        agent_name: str,
        initial_input: str,
        started_at: datetime,
    ) -> None:
        from app.utils import redis_client

        data = {
            "session_id": session_id,
            "request_id": request_id,
            "agent_name": agent_name,
            "initial_input": initial_input,
            "loop_count": 0,
            "schema_data": None,
            "raw_output": None,
            "error": None,
            "finished": False,
            "started_at": started_at.isoformat() if started_at else None,
            "finished_at": None,
        }
        await redis_client.set_json(f"agent:session:{session_id}", data)

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
        from app.utils import redis_client

        msg = {
            "request_id": request_id,
            "role": role,
            "content": content,
            "agent_name": agent_name,
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "metadata": extra_metadata or {},
            "seq": seq,
        }
        key = f"agent:messages:{session_id}"
        messages: list = (await redis_client.get_json(key)) or []
        messages.append(msg)
        await redis_client.set_json(key, messages)

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
        from app.utils import redis_client

        key = f"agent:session:{session_id}"
        data = await redis_client.get_json(key)
        if data is None:
            return

        data.update({
            "loop_count": loop_count,
            "schema_data": schema_data,
            "raw_output": raw_output,
            "error": error,
            "finished": finished,
            "finished_at": finished_at.isoformat() if finished_at else None,
        })
        await redis_client.set_json(key, data)

    async def load_messages(
        self,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        from app.utils import redis_client

        data = await redis_client.get_json(f"agent:messages:{session_id}")
        return data or []

    async def load_session(
        self,
        session_id: str,
    ) -> Optional[Dict[str, Any]]:
        from app.utils import redis_client

        return await redis_client.get_json(f"agent:session:{session_id}")
