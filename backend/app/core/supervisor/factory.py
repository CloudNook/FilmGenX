"""
Supervisor Agent 工厂函数。
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.agent.persist.db_strategy import DBPersistStrategy
from app.core.agent.persist.base import PersistStrategy
from app.core.agent.persist.redis_strategy import RedisPersistStrategy
from app.core.agent.factory import PersistArg
from app.core.middleware import HumanInTheLoopMiddleware
from app.core.middleware.chain import AgentMiddleware
from app.core.supervisor.registry import (
    SupervisorAgentRegistry,
    WorkflowNodeDefinition,
    build_default_registry,
    build_default_workflow_definitions,
)
from app.core.supervisor.supervisor import SupervisorAgent
from app.db.session import AsyncSessionFactory

logger = logging.getLogger(__name__)


def _resolve_persist(
    persist: PersistArg,
    *,
    db: Any = None,
    supervisor_session_id: str | None = None,
) -> Optional[PersistStrategy]:
    if persist is None and db is not None:
        return DBPersistStrategy(
            session_factory=AsyncSessionFactory,
            supervisor_session_id=supervisor_session_id,
        )
    if persist is None:
        return None
    if isinstance(persist, PersistStrategy):
        return persist
    if persist == "redis":
        return RedisPersistStrategy()
    raise ValueError(
        f"未知的 persist 参数：{persist!r}，可选值：'redis' | PersistStrategy 实例 | None"
    )


def _resolve_middlewares(
    middlewares: Optional[List[AgentMiddleware]],
    *,
    auto_run: bool,
    hitl_enabled: bool,
    review_nodes: Optional[List[str]],
) -> List[AgentMiddleware]:
    """决定 supervisor 是否挂载 HITL 中间件 + 白名单粒度。

    两个独立维度：
    - ``auto_run=False`` → ``call_sub_agent`` 必须经过人工确认；其它工具
      （memory_save / load_skill / get_workflow_state）放行
    - ``hitl_enabled=True`` → 严格模式，所有工具（除了只读的 get_workflow_state）
      都触发人工确认

    两个都没开 → 不挂中间件，全自动。
    两个都开 → 严格模式取并集（更严的 hitl_enabled 生效）。
    """
    resolved = list(middlewares or [])

    needs_hitl = hitl_enabled or (not auto_run)
    if not needs_hitl:
        return resolved
    if any(isinstance(m, HumanInTheLoopMiddleware) for m in resolved):
        return resolved

    if hitl_enabled:
        # 严格：只放行只读状态查询
        auto_list = ["get_workflow_state"]
    else:
        # auto_run=False 单独触发：只 gate call_sub_agent，其它放行
        auto_list = [
            "get_workflow_state",
            "memory_save",
            "load_skill",
            "load_skill_reference",
        ]

    resolved.append(
        HumanInTheLoopMiddleware(
            auto_tool_list=auto_list,
            context={"review_sub_agents": review_nodes or []},
        )
    )
    return resolved


def create_supervisor(
    user_request: str,
    *,
    supervisor_session_id: Optional[str] = None,
    model: str = "gemini-3-flash-preview",
    max_loop: int = 50,
    persist: PersistArg = "redis",
    middlewares: Optional[List[AgentMiddleware]] = None,
    sub_agent_configs: Optional[Dict[str, Any]] = None,
    registry: Optional[SupervisorAgentRegistry] = None,
    workflow_definitions: Optional[List[WorkflowNodeDefinition]] = None,
    workflow_profile: str = "default",
    auto_run: bool = False,
    hitl_enabled: bool = False,
    review_nodes: Optional[List[str]] = None,
    db: Any = None,
    domain_id: int | str | None = None,
    memory_enabled: bool = True,
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
    Returns:
        SupervisorAgent 实例
    """
    session_id = supervisor_session_id or f"sv-{uuid4()}"
    persist_strategy = _resolve_persist(
        persist,
        db=db,
        supervisor_session_id=session_id,
    )
    resolved_middlewares = _resolve_middlewares(
        middlewares,
        auto_run=auto_run,
        hitl_enabled=hitl_enabled,
        review_nodes=review_nodes,
    )
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
        middlewares=resolved_middlewares,
        persist=persist_strategy,
        model=model,
        max_loop=max_loop,
        registry=resolved_registry,
        workflow_definitions=resolved_workflow_definitions,
        workflow_profile=workflow_profile,
        auto_run=auto_run,
        hitl_enabled=hitl_enabled,
        review_nodes=review_nodes,
        db=db,
        domain_id=domain_id,
        memory_enabled=memory_enabled,
    )

    return supervisor
