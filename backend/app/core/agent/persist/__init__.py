"""
Agent 持久化层。

包结构：
- base.py         : PersistStrategy 抽象接口
- models.py       : SQLAlchemy 表模型（AgentSession / AgentMessageRecord）
- redis_strategy.py: Redis 实现
- db_strategy.py  : 数据库实现

使用方式：
    # Redis 持久化
    agent = create_agent(..., persist="redis")

    # 数据库持久化
    from app.core.agent.persist import DBPersistStrategy
    agent = create_agent(..., persist=DBPersistStrategy(db=db_session))

    # 不持久化
    agent = create_agent(..., persist=None)
"""

from app.core.agent.persist.base import PersistStrategy
from app.core.agent.persist.models import AgentMessageRecord, AgentSession
from app.core.agent.persist.redis_strategy import RedisPersistStrategy
from app.core.agent.persist.db_strategy import DBPersistStrategy

__all__ = [
    # 抽象
    "PersistStrategy",
    # 模型
    "AgentSession",
    "AgentMessageRecord",
    # 策略
    "RedisPersistStrategy",
    "DBPersistStrategy",
]
