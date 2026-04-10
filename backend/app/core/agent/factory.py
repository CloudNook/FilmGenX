"""
Agent 工厂函数。

返回 Agent 实例，具体执行需显式调用 agent.run() / agent.stream()。
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from pydantic import BaseModel

from app.core.agent.agent import Agent
from app.core.agent.base import AgentConfig
from app.core.middleware.chain import AgentMiddleware

if TYPE_CHECKING:
    from app.core.agent.persist.base import PersistStrategy

logger = logging.getLogger(__name__)


def create_agent(
    agent_name: str,
    prompt: str = "",
    *,
    model: str = "gemini-3-flash-preview",
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    response_schema: Optional[Type[BaseModel] | Dict[str, Any]] = None,
    tools: List[Dict[str, Any]] | None = None,
    skills: List[str] | None = None,
    max_loop: int = 20,
    persist: "PersistStrategy | None" = None,
    middlewares: List[AgentMiddleware] | None = None,
) -> Agent:
    """
    创建 Agent 实例。

    注意：此方法仅创建实例，不执行。
    实际执行需调用 agent.run() 或 agent.stream()。

    Args:
        agent_name: Agent 名称，用于标识和日志
        prompt: 系统提示词
        model: LLM 模型名称
        temperature: 温度参数
        max_tokens: 最大 token 数
        response_schema: 响应数据模型（Pydantic 模型类或 dict）
        tools: 工具列表（dict 格式）
        skills: Skill 名称列表，从注册表加载
        max_loop: 最大循环次数
        persist: 持久化策略（如 RedisPersistStrategy()），None 则不持久化
        middlewares: 中间件列表

    Returns:
        Agent 实例，需调用 run() / stream() 执行
    """
    # 序列化 response_schema
    schema_dict: Optional[Dict[str, Any]] = None
    if response_schema is not None:
        if isinstance(response_schema, type) and issubclass(response_schema, BaseModel):
            schema_dict = response_schema.model_json_schema()
        elif isinstance(response_schema, dict):
            schema_dict = response_schema
        else:
            logger.warning(
                f"response_schema must be BaseModel or dict, got {type(response_schema)}"
            )

    # 构建配置
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
        middleware=[mw.name for mw in (middlewares or [])],
    )

    logger.info(f"[create_agent] Created agent: {agent_name}")

    return Agent(config=config, persist=persist, middlewares=middlewares)
