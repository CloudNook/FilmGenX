"""
Supervisor 工具：call_sub_agent / get_workflow_state。
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import uuid4

from app.core.agent.factory import create_agent
from app.core.agent.persist.db_strategy import DBPersistStrategy
from app.core.agent.tool_errors import tool_error
from app.core.agent.base import (
    ToolStartEvent,
    ToolEndEvent,
    ThinkingEvent,
    TextEvent,
    DoneEvent,
    ReviewStartEvent as AgentReviewStartEvent,
    ReviewEndEvent as AgentReviewEndEvent,
)
from app.core.supervisor.context import SupervisorContext
from app.core.supervisor.concurrency import SubAgentConcurrencyLimiter
from app.core.supervisor.events import (
    SubAgentEndEvent,
    SubAgentStartEvent,
    SupervisorErrorEvent,
    SupervisorTextEvent,
    SupervisorThinkingEvent,
    SupervisorToolEndEvent,
    SupervisorToolStartEvent,
    ReviewStartEvent,
    ReviewEndEvent,
)
from app.core.supervisor.registry import (
    RegisteredAgent,
    SupervisorAgentRegistry,
    build_default_registry,
)
from app.core.supervisor.workflow import WorkflowSnapshot, apply_node_update
from app.core.tools.registry import register_tool
from app.db.session import AsyncSessionFactory

logger = logging.getLogger(__name__)


# 上游依赖只有处于这两个状态时，下游才允许 run。
# - fresh：节点 artifact 是最新的，未被上游变更冲掉
# - completed：节点曾运行成功（兼容历史数据）
_OK_DEPENDENCY_STATUSES = frozenset({"fresh", "completed"})


def _build_workflow_context_block(
    workflow: WorkflowSnapshot,
    current_node_keys: list[str],
) -> str:
    """构造给 sub-agent 看的整体工作流上下文块。

    sub-agent 们各自跑独立 session，不直接共享 in-memory 历史。如果不主动注入工作流
    状态，下游 sub-agent 只能依赖 supervisor LLM 临场摘录上游产物，漏一处就生不出
    对应内容（character_ref 漏了角色名 / frame_prompt 漏了风格锚都会塌）。

    所以每次 ``call_sub_agent`` 时把当前 ``WorkflowSnapshot`` 编码成两段贴在 sub_prompt
    末尾：

    - ``## 工作流状态``：完整链路 + 每个节点的 status，标记 ``← 当前``
    - ``## 上游产出``：所有已完成上游节点的 raw_output（从 ``node.artifact["output"]``
      取出），用 ``json`` 围栏保留原始结构

    "上游" 由 ``WorkflowSnapshot.nodes`` 的插入序列定义——本期工作流是线性的
    （outline → … → video_prompt），插入序与拓扑序一致。后续做并行 / DAG 编排时这
    里要换成 ``dependency_map`` 的拓扑遍历。
    """
    current_set = set(current_node_keys)

    status_lines = [
        "## 工作流状态",
        "",
        "| 节点 | 状态 |",
        "| --- | --- |",
    ]
    for key, node in workflow.nodes.items():
        marker = " ← 当前" if key in current_set else ""
        status_lines.append(f"| {key} | {node.status}{marker} |")

    upstream: list[tuple[str, str]] = []
    for key, node in workflow.nodes.items():
        if key in current_set:
            break  # 自己 + 之后的节点都不展示
        if node.artifact and isinstance(node.artifact, dict):
            output = node.artifact.get("output")
            if isinstance(output, str) and output.strip():
                upstream.append((key, output))

    parts = ["\n".join(status_lines)]
    if upstream:
        out_lines = ["", "## 上游产出"]
        for key, output in upstream:
            out_lines.append(f"\n### {key}")
            out_lines.append("```json")
            out_lines.append(output)
            out_lines.append("```")
        parts.append("\n".join(out_lines))

    return "\n\n".join(parts)


def _check_dependency_guard(
    workflow: Optional[WorkflowSnapshot],
    registered: RegisteredAgent,
) -> Optional[Dict[str, Any]]:
    """
    检查 sub-agent 的 node_keys 上游依赖是否就绪。

    Returns:
        None: 依赖满足或无 workflow 上下文，可以继续执行。
        dict: 依赖未满足，返回结构化 ToolError，调用方直接放进 SubAgentEndEvent.result。

    设计：
    - 不抛异常。LLM 看不到异常细节就只能盲目重试或放弃；结构化错误能让 LLM
      读到"哪些 node 没就绪、应该先做什么"并自我纠正。
    - 没有 workflow（一些直跑场景）时跳过 guard，保持向下兼容。
    """
    if workflow is None:
        return None

    blocking: List[Dict[str, str]] = []
    for node_key in registered.node_keys:
        deps = workflow.dependency_map.get(node_key, [])
        for dep in deps:
            dep_node = workflow.nodes.get(dep)
            dep_status = dep_node.status if dep_node is not None else "missing"
            if dep_status not in _OK_DEPENDENCY_STATUSES:
                blocking.append(
                    {
                        "node_key": dep,
                        "status": dep_status,
                        "blocks_node": node_key,
                    }
                )

    if not blocking:
        return None

    blocked_node_names = sorted({b["node_key"] for b in blocking})
    return tool_error(
        error_code="DEPENDENCY_NOT_SATISFIED",
        message=(
            f"Cannot run {registered.name}: upstream node(s) "
            f"{', '.join(blocked_node_names)} not fresh."
        ),
        hint=(
            "Run the upstream sub-agent(s) first to bring the workflow node(s) to 'fresh' status, "
            "or confirm the existing node artifact if it is acceptable."
        ),
        context={
            "sub_agent_name": registered.name,
            "node_keys": list(registered.node_keys),
            "blocking": blocking,
        },
    )


def _build_call_sub_agent_schema(agent_names: Optional[List[str]] = None) -> Dict[str, Any]:
    available_names = agent_names or build_default_registry().agent_names()
    return {
        "name": "call_sub_agent",
        "description": (
            "调用指定的 SubAgent 执行任务，实时返回流式事件。\n"
            "Args:\n"
            f"  sub_agent_name: SubAgent 名称，可选值：{' | '.join(available_names)}\n"
            "  task_description: 给 SubAgent 的具体任务描述（包含角色定义 + 任务 + 参考产物）\n"
            "  context_snapshot: 前序 SubAgent 产物的 JSON 字符串（选择性注入上下文）\n"
            "Returns: 流式事件（SubAgentStart → Thinking/Text/ToolStart/ToolEnd → SubAgentEnd）\n"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sub_agent_name": {
                    "type": "string",
                    "description": f"SubAgent 名称：{' | '.join(available_names)}",
                    "enum": available_names,
                },
                "task_description": {
                    "type": "string",
                    "description": "Supervisor 构造的 prompt：角色 + 具体任务 + 参考产物",
                },
                "context_snapshot": {
                    "type": "string",
                    "description": "前序产物 JSON，供 SubAgent 参考（如大纲 JSON）",
                },
            },
            "required": ["sub_agent_name", "task_description"],
        },
    }


@register_tool(
    name="call_sub_agent",
    description=(
        "调用指定的 SubAgent 执行任务，实时返回流式事件。\n"
        "Args:\n"
        "  sub_agent_name: SubAgent 名称，由当前 registry 决定\n"
        "  task_description: 给 SubAgent 的具体任务描述（包含角色定义 + 任务 + 参考产物）\n"
        "  context_snapshot: 前序 SubAgent 产物的 JSON 字符串（选择性注入上下文）\n"
        "Returns: 流式事件（SubAgentStart → Thinking/Text/ToolStart/ToolEnd → SubAgentEnd）\n"
    ),
)
async def call_sub_agent(
    sub_agent_name: str,
    task_description: str,
    context_snapshot: str = "",
    supervisor_context: SupervisorContext | None = None,
    registry: Optional[SupervisorAgentRegistry] = None,
) -> AsyncGenerator:
    """
    调用指定的 SubAgent 执行任务，实时 yield 所有流式事件。

    设计要点：
    - SubAgent 不访问 supervisor_context，只通过 task_description 接收必要数据
    - session_id 格式：sub-{agent_name}-{uuid4()[:8]}
    - 流式事件实时透传到 SSE
    """
    active_registry = registry or build_default_registry()
    registered = active_registry.get(sub_agent_name)
    if registered is None:
        yield SubAgentEndEvent(
            sub_agent_name=sub_agent_name,
            session_id="",
            result=tool_error(
                error_code="UNKNOWN_SUB_AGENT",
                message=f"Unknown sub_agent_name: {sub_agent_name}",
                hint=(
                    "Check the available sub_agent_name values returned by the call_sub_agent "
                    "schema (or call get_workflow_state to see registered agents)."
                ),
                context={
                    "sub_agent_name": sub_agent_name,
                    "available": active_registry.agent_names(),
                },
            ),
        )
        return

    if supervisor_context is None:
        raise RuntimeError("call_sub_agent requires supervisor_context")

    # Workflow 依赖 guard：上游 node 未 fresh 时拒绝运行。
    # 结构化错误返回，supervisor LLM 据此选择先调上游 sub-agent 或 confirm 现有产物。
    guard_error = _check_dependency_guard(supervisor_context.workflow, registered)
    if guard_error is not None:
        yield SubAgentEndEvent(
            sub_agent_name=sub_agent_name,
            session_id="",
            result=guard_error,
        )
        return

    # Session 复用：同一个 supervisor 会话内多次调同一个 sub-agent 时，复用上次
    # session_id。agent loop 的 _load_history 会按 session_id 从 DB 读回所有历史
    # 消息（task / 候选输出 / reviewer feedback），LLM 看到的是连续对话而不是每次
    # 从零开始。第一次调时才分配新 uuid。
    existing_session = supervisor_context.sub_agent_sessions.get(sub_agent_name)
    known_sessions_keys = list(supervisor_context.sub_agent_sessions.keys())
    if existing_session is not None:
        sub_session_id = existing_session.session_id
        logger.info(
            "[call_sub_agent] REUSE session %s for %s (turn N+1, supervisor_session=%s, "
            "known_sub_sessions=%s)",
            sub_session_id,
            sub_agent_name,
            supervisor_context.supervisor_session_id,
            known_sessions_keys,
        )
    else:
        sub_session_id = f"sub-{sub_agent_name}-{str(uuid4())[:8]}"
        logger.info(
            "[call_sub_agent] NEW session %s for %s (first call this supervisor turn, "
            "supervisor_session=%s, known_sub_sessions=%s)",
            sub_session_id,
            sub_agent_name,
            supervisor_context.supervisor_session_id,
            known_sessions_keys,
        )

    sub_prompt = task_description
    if context_snapshot:
        sub_prompt = f"{sub_prompt}\n\n## 参考上下文\n{context_snapshot}"

    # 自动注入工作流整体上下文：状态表 + 已完成上游节点的 raw_output。
    # 这是 sub-agent 之间唯一的串接通道——不靠这一注入，下游 sub-agent 只能信任
    # supervisor LLM 临场摘录。
    if supervisor_context.workflow is not None:
        workflow_block = _build_workflow_context_block(
            supervisor_context.workflow,
            registered.node_keys,
        )
        sub_prompt = f"{sub_prompt}\n\n---\n\n{workflow_block}"

    # 完整 prompt 日志：每次调起 sub-agent 时把 initial_input 全文打到日志，便于
    # 现场审查工作流上下文是否真的注入到位、supervisor LLM 给的 task_description
    # 是否合理。日志量大但定位 sub-agent 输出问题的关键证据。
    logger.info(
        "[call_sub_agent] %s (session=%s) sub_prompt (%d chars):\n"
        "----------- BEGIN sub_prompt -----------\n"
        "%s\n"
        "----------- END sub_prompt -----------",
        sub_agent_name,
        sub_session_id,
        len(sub_prompt),
        sub_prompt,
    )

    limiter = SubAgentConcurrencyLimiter.get_instance()
    persist_strategy = DBPersistStrategy(
        session_factory=AsyncSessionFactory,
        supervisor_session_id=supervisor_context.supervisor_session_id,
    )

    sub_agent = create_agent(
        agent_name=sub_agent_name,
        session_id=sub_session_id,
        prompt=registered.prompt,
        model=registered.model,
        tools=registered.tools,
        skill_names=registered.skill_names,
        max_loop=20,
        persist=persist_strategy,
        reviewer=registered.reviewer,
        response_schema=registered.response_schema,
    )

    accumulated_result = {}

    try:
        async with await limiter.acquire(sub_agent_name):
            supervisor_context.register_sub_agent_session(
                sub_agent_name,
                sub_session_id,
            )
            if supervisor_context.workflow is not None:
                for node_key in registered.node_keys:
                    if node_key in supervisor_context.workflow.nodes:
                        supervisor_context.workflow.nodes[node_key].status = "running"

            logger.info(
                f"[call_sub_agent] starting sub_agent={sub_agent_name}, "
                f"session={sub_session_id}"
            )

            yield SubAgentStartEvent(
                sub_agent_name=sub_agent_name,
                session_id=sub_session_id,
                task_description=task_description,
            )

            async for event in sub_agent.stream(initial_input=sub_prompt):
                if isinstance(event, ThinkingEvent):
                    yield SupervisorThinkingEvent(
                        content=event.content,
                        source=sub_agent_name,
                        session_id=sub_session_id,
                    )
                elif isinstance(event, TextEvent):
                    yield SupervisorTextEvent(
                        content=event.content,
                        source=sub_agent_name,
                        session_id=sub_session_id,
                    )
                elif isinstance(event, ToolStartEvent):
                    yield SupervisorToolStartEvent(
                        tool_call_id=event.tool_call_id,
                        tool_name=event.tool_name,
                        arguments=event.arguments,
                        source=sub_agent_name,
                        session_id=sub_session_id,
                    )
                elif isinstance(event, ToolEndEvent):
                    yield SupervisorToolEndEvent(
                        tool_call_id=event.tool_call_id,
                        tool_name=event.tool_name,
                        result=event.result,
                        is_error=event.is_error,
                        source=sub_agent_name,
                        session_id=sub_session_id,
                    )
                elif isinstance(event, AgentReviewStartEvent):
                    criteria = registered.reviewer.criteria if registered.reviewer else []
                    yield ReviewStartEvent(
                        sub_agent_name=sub_agent_name,
                        criteria=criteria,
                        source=sub_agent_name,
                    )
                elif isinstance(event, AgentReviewEndEvent):
                    yield ReviewEndEvent(
                        sub_agent_name=sub_agent_name,
                        score=event.review.score,
                        passed=event.review.passed,
                        feedback=event.review.feedback,
                        suggestions=event.review.suggestions,
                        source=sub_agent_name,
                    )
                elif isinstance(event, DoneEvent):
                    accumulated_result = {
                        "output": event.result.raw_output or "",
                        "sub_agent_name": sub_agent_name,
                    }
                    if supervisor_context.workflow is not None:
                        for node_key in registered.node_keys:
                            if node_key in supervisor_context.workflow.nodes:
                                apply_node_update(
                                    supervisor_context.workflow,
                                    node_key,
                                    {"output": event.result.raw_output or ""},
                                    updated_by="agent",
                                    last_agent=sub_agent_name,
                                )
                    supervisor_context.record_execution(
                        agent_name=sub_agent_name,
                        session_id=sub_session_id,
                        status="completed",
                        node_keys=registered.node_keys,
                    )
                    logger.info(
                        f"[call_sub_agent] completed sub_agent={sub_agent_name}"
                    )
    except Exception as e:
        logger.exception(f"[call_sub_agent] error in sub_agent={sub_agent_name}: {e}")
        yield SupervisorErrorEvent(
            error=str(e),
            source=sub_agent_name,
            session_id=sub_session_id,
        )
        accumulated_result = {"error": str(e), "sub_agent_name": sub_agent_name}

    yield SubAgentEndEvent(
        sub_agent_name=sub_agent_name,
        session_id=sub_session_id,
        result=accumulated_result,
    )


def _build_get_workflow_state_schema() -> Dict[str, Any]:
    return {
        "name": "get_workflow_state",
        "description": (
            "查询当前工作流状态。\n"
            "Returns: {workflow, review_history, execution_history, sub_agent_sessions, auto_run}\n"
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }


@register_tool(
    name="get_workflow_state",
    description=(
        "查询当前工作流状态（Supervisor 决策参考）。\n"
        "Returns: {workflow, review_history, execution_history, sub_agent_sessions, auto_run}\n"
    ),
)
async def get_workflow_state(
    supervisor_context: SupervisorContext,
) -> Dict[str, Any]:
    """
    查询当前流水线状态。

    供 Supervisor Agent（LLM）做决策参考。
    注意：此工具是给 Supervisor 用的，不是给 SubAgent 用的。
    """
    return {
        "workflow": (
            supervisor_context.workflow.model_dump()
            if supervisor_context.workflow is not None
            else None
        ),
        "review_history": [
            r.model_dump() for r in supervisor_context.review_history
        ],
        "sub_agent_sessions": supervisor_context.sub_agent_session_ids(),
        "execution_history": [
            record.model_dump(exclude={"metadata"}, exclude_defaults=True)
            if not record.metadata
            else record.model_dump()
            for record in supervisor_context.execution_history
        ],
        "auto_run": supervisor_context.auto_run,
    }


def get_supervisor_tool_schemas(agent_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """返回所有 Supervisor 工具的 schema 列表。"""
    return [
        _build_call_sub_agent_schema(agent_names),
        _build_get_workflow_state_schema(),
    ]
