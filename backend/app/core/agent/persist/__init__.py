"""
Agent 持久化层。

包结构：
- base.py           : PersistStrategy 抽象接口（load_messages + append_message）
- models.py         : SQLAlchemy 表模型（AgentMessageRecord）
- redis_strategy.py : Redis 实现
- db_strategy.py    : PostgreSQL 实现

使用方式：
    agent = create_agent(..., persist="redis")
    agent = create_agent(..., persist="db", db=db_session)
    agent = create_agent(..., persist=MyPersistStrategy())
    agent = create_agent(..., persist=None)
"""

from app.core.agent.persist.base import PersistStrategy
from app.core.agent.persist.models import AgentMessageRecord
from app.core.agent.persist.redis_strategy import RedisPersistStrategy
from app.core.agent.persist.db_strategy import DBPersistStrategy

__all__ = [
    "PersistStrategy",
    "AgentMessageRecord",
    "RedisPersistStrategy",
    "DBPersistStrategy",
]
