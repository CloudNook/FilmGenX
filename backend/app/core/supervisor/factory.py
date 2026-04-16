"""
Supervisor Agent 工厂函数。
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.agent.persist.base import PersistStrategy
from app.core.agent.persist.redis_strategy import RedisPersistStrategy
from app.core.agent.factory import PersistArg
from app.core.middleware.chain import AgentMiddleware
from app.core.supervisor.registry import (
    SupervisorAgentRegistry,
    WorkflowNodeDefinition,
    build_default_registry,
    build_default_workflow_definitions,
)
from app.core.supervisor.supervisor import SupervisorAgent

logger = logging.getLogger(__name__)


def _resolve_persist(persist: PersistArg) -> Optional[PersistStrategy]:
    if persist is None:
        return None
    if isinstance(persist, PersistStrategy):
        return persist
    if persist == "redis":
        return RedisPersistStrategy()
    raise ValueError(
        f"未知的 persist 参数：{persist!r}，可选值：'redis' | PersistStrategy 实例 | None"
    )


def create_supervisor(
    user_request: str,
    *,
    supervisor_session_id: Optional[str] = None,
    supervisor_name: str = "supervisor",
    model: str = "gemini-3-flash-preview",
    max_loop: int = 30,
    persist: PersistArg = "redis",
    middlewares: Optional[List[AgentMiddleware]] = None,
    sub_agent_configs: Optional[Dict[str, Any]] = None,
    registry: Optional[SupervisorAgentRegistry] = None,
    workflow_definitions: Optional[List[WorkflowNodeDefinition]] = None,
    workflow_profile: str = "default",
    auto_run: bool = False,
    workflow_service=None,
) -> SupervisorAgent:
    """
    创建 SupervisorAgent 实例。

    Args:
        user_request: 用户原始需求
        supervisor_name: Supervisor 名称（默认 "supervisor"）
        model: LLM 模型（默认 gemini-3-flash-preview）
        max_loop: 最大循环次数（默认 30，Supervisor 需要更多决策轮次）
        persist: 持久化策略（默认 "redis"）
        middlewares: 中间件列表（如需 HITL，传入 HumanInTheLoopMiddleware）
        sub_agent_configs: SubAgent 配置映射（预留，未来从 DB/Skill 加载）
        workflow_service: SupervisorWorkflowService 实例（可选，用于 call_sub_agent DB 持久化）

    Returns:
        SupervisorAgent 实例
    """
    session_id = supervisor_session_id or f"sv-{uuid4()}"
    persist_strategy = _resolve_persist(persist)
    resolved_registry = registry or build_default_registry()
    resolved_workflow_definitions = workflow_definitions or build_default_workflow_definitions()

    logger.info(
        f"[create_supervisor] supervisor_session={session_id}, "
        f"user_request={user_request[:50]}..., persist={persist}"
    )

    supervisor = SupervisorAgent(
        supervisor_session_id=session_id,
        user_request=user_request,
        sub_agent_configs=sub_agent_configs or {},
        middlewares=middlewares or [],
        persist=persist_strategy,
        model=model,
        max_loop=max_loop,
        registry=resolved_registry,
        workflow_definitions=resolved_workflow_definitions,
        workflow_profile=workflow_profile,
        auto_run=auto_run,
    )

    # 注入 workflow_service，供 call_sub_agent 写入 DB
    supervisor._tool_ctx["workflow_service"] = workflow_service

    return supervisor
