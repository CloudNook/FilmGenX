"""
Agent 工厂函数。

返回 Agent 实例，具体执行需显式调用 agent.run() / agent.stream()。
"""

import logging
from typing import Any, Dict, List, Literal, Optional, Type, Union

from pydantic import BaseModel

from app.core.agent.agent import Agent
from app.core.agent.base import AgentConfig
from app.core.agent.persist.base import PersistStrategy
from app.core.agent.persist.redis_strategy import RedisPersistStrategy
from app.core.middleware.chain import AgentMiddleware

logger = logging.getLogger(__name__)

# "redis" 是框架内置快捷方式；DB 持久化需调用方自行构造 DBPersistStrategy 实例传入
PersistArg = Union[Literal["redis"], PersistStrategy, None]


def _resolve_persist(persist: PersistArg) -> Optional[PersistStrategy]:
    if persist is None:
        return None
    if isinstance(persist, PersistStrategy):
        return persist
    if persist == "redis":
        return RedisPersistStrategy()
    raise ValueError(f"未知的 persist 参数：{persist!r}，可选值：'redis' | PersistStrategy 实例 | None")


def create_agent(
    agent_name: str,
    session_id: str,
    prompt: str = "",
    *,
    model: str = "gemini-3-flash-preview",
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    response_schema: Optional[Union[Type[BaseModel], Dict[str, Any]]] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    skills: Optional[List[str]] = None,
    max_loop: int = 20,
    persist: PersistArg = None,
    middlewares: Optional[List[AgentMiddleware]] = None,
) -> Agent:
    """
    创建 Agent 实例。

    注意：此方法仅创建实例，不执行。
    实际执行需调用 agent.run() 或 agent.stream()。

    Args:
        agent_name:      Agent 名称
        session_id:      会话 ID，用于多轮对话持久化
        prompt:          系统提示词
        model:           LLM 模型名称
        temperature:     温度参数
        max_tokens:      最大 token 数
        response_schema: 响应数据模型（Pydantic 模型类或 dict）
        tools:           工具列表
        skills:          Skill 名称列表
        max_loop:        最大循环次数
        persist:         持久化策略，"redis" | PersistStrategy 实例 | None
                         DB 持久化示例：persist=DBPersistStrategy(db=session)
        middlewares:     中间件列表

    Returns:
        Agent 实例，需调用 run() / stream() 执行
    """
    schema_dict: Optional[Dict[str, Any]] = None
    if response_schema is not None:
        if isinstance(response_schema, type) and issubclass(response_schema, BaseModel):
            schema_dict = response_schema.model_json_schema()
        elif isinstance(response_schema, dict):
            schema_dict = response_schema
        else:
            logger.warning(f"response_schema 类型不支持：{type(response_schema)}")

    config = AgentConfig(
        agent_name=agent_name,
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_schema=schema_dict,
        tools=tools or [],
        skill_names=skills or [],
        max_loop=max_loop,
    )

    persist_strategy = _resolve_persist(persist)

    logger.info(
        f"[create_agent] agent={agent_name}, "
        f"persist={persist_strategy.name if persist_strategy else 'none'}"
    )

    return Agent(config=config, session_id=session_id, persist=persist_strategy, middlewares=middlewares)
