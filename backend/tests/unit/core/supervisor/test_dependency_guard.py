"""
S4: Workflow 依赖 guard 测试。

call_sub_agent 在 sub-agent 真实启动前检查 workflow 上游依赖是否 fresh，
不就绪则返回结构化 ToolError，不抛异常，让 supervisor LLM 能从结果里读到
具体阻塞节点并自我纠正。
"""

import pytest

from app.core.agent.base import AgentResult, DoneEvent
from app.core.supervisor.context import SupervisorContext
from app.core.supervisor.registry import (
    RegisteredAgent,
    SupervisorAgentRegistry,
)
from app.core.supervisor.tools import call_sub_agent, _check_dependency_guard
from app.core.supervisor.workflow import (
    WorkflowNodeDefinition,
    apply_node_update,
    build_workflow_snapshot,
)


# ---------------------------------------------------------------------- #
# 纯函数：_check_dependency_guard
# ---------------------------------------------------------------------- #


def test_dependency_guard_allows_when_no_workflow():
    registered = RegisteredAgent(
        name="outline_agent",
        label="Outline",
        description="x",
        node_keys=["outline"],
    )
    assert _check_dependency_guard(None, registered) is None


def test_dependency_guard_allows_when_node_has_no_deps():
    snapshot = build_workflow_snapshot(
        profile="default",
        definitions=[
            WorkflowNodeDefinition(
                key="outline", label="Outline", node_type="text", depends_on=[]
            )
        ],
    )
    registered = RegisteredAgent(
        name="outline_agent",
        label="Outline",
        description="x",
        node_keys=["outline"],
    )
    assert _check_dependency_guard(snapshot, registered) is None


def test_dependency_guard_blocks_when_upstream_missing():
    snapshot = build_workflow_snapshot(
        profile="default",
        definitions=[
            WorkflowNodeDefinition(key="outline", label="Outline", node_type="text"),
            WorkflowNodeDefinition(
                key="script",
                label="Script",
                node_type="text",
                depends_on=["outline"],
            ),
        ],
    )
    # outline 未跑过 → script 上游不 fresh
    registered = RegisteredAgent(
        name="script_agent",
        label="Script",
        description="x",
        node_keys=["script"],
    )

    err = _check_dependency_guard(snapshot, registered)
    assert err is not None
    assert err["ok"] is False
    assert err["error_code"] == "DEPENDENCY_NOT_SATISFIED"
    assert "outline" in err["message"]
    assert err["context"]["sub_agent_name"] == "script_agent"
    assert err["context"]["blocking"][0]["node_key"] == "outline"
    assert err["context"]["blocking"][0]["blocks_node"] == "script"


def test_dependency_guard_allows_when_upstream_fresh():
    snapshot = build_workflow_snapshot(
        profile="default",
        definitions=[
            WorkflowNodeDefinition(key="outline", label="Outline", node_type="text"),
            WorkflowNodeDefinition(
                key="script",
                label="Script",
                node_type="text",
                depends_on=["outline"],
            ),
        ],
    )
    apply_node_update(
        snapshot,
        "outline",
        artifact={"summary": "done"},
        updated_by="agent",
        last_agent="outline_agent",
    )
    assert snapshot.nodes["outline"].status == "fresh"

    registered = RegisteredAgent(
        name="script_agent",
        label="Script",
        description="x",
        node_keys=["script"],
    )
    assert _check_dependency_guard(snapshot, registered) is None


def test_dependency_guard_blocks_when_upstream_pending_confirmation():
    """上游被改动（version > 1）后置为 pending_confirmation，下游应被 guard 拦住。"""
    snapshot = build_workflow_snapshot(
        profile="default",
        definitions=[
            WorkflowNodeDefinition(key="outline", label="Outline", node_type="text"),
            WorkflowNodeDefinition(
                key="script",
                label="Script",
                node_type="text",
                depends_on=["outline"],
            ),
        ],
    )
    # 第一次更新让 outline -> fresh，script -> ready
    apply_node_update(snapshot, "outline", {"v": 1}, updated_by="agent")
    # 让 script 也跑一次，状态 fresh
    apply_node_update(snapshot, "script", {"v": 1}, updated_by="agent")
    # 再次更新 outline -> 自身 fresh，但下游 script 被打回 pending_confirmation
    apply_node_update(snapshot, "outline", {"v": 2}, updated_by="agent")
    assert snapshot.nodes["script"].status == "pending_confirmation"

    # 现在尝试再跑 storyboard：依赖 script，而 script 是 pending_confirmation → 应被拦
    snapshot.dependency_map["storyboard"] = ["script"]
    snapshot.nodes["storyboard"] = snapshot.nodes["script"].model_copy(
        update={"key": "storyboard", "status": "missing", "version": 0, "artifact": None}
    )
    registered = RegisteredAgent(
        name="storyboard_agent",
        label="Storyboard",
        description="x",
        node_keys=["storyboard"],
    )

    err = _check_dependency_guard(snapshot, registered)
    assert err is not None
    assert err["error_code"] == "DEPENDENCY_NOT_SATISFIED"
    blocking = err["context"]["blocking"]
    assert blocking[0]["node_key"] == "script"
    assert blocking[0]["status"] == "pending_confirmation"


# ---------------------------------------------------------------------- #
# call_sub_agent 集成：guard 命中时不启动 sub-agent
# ---------------------------------------------------------------------- #


class _FakeAgent:
    async def stream(self, initial_input: str):  # pragma: no cover - 不应被命中
        yield DoneEvent(
            result=AgentResult(
                agent_name="should-not-run",
                raw_output="should-not-run",
                finished=True,
            )
        )


@pytest.mark.asyncio
async def test_call_sub_agent_dependency_guard_blocks_and_returns_structured_error(monkeypatch):
    """
    上游 outline 还没跑，supervisor LLM 直接调 script_agent —— 必须被 guard 拦住，
    并返回 ok=False / error_code=DEPENDENCY_NOT_SATISFIED 给 LLM 看。

    `_FakeAgent.stream` 不应被进入；guard 需在启动 sub-agent 之前生效。
    """
    create_agent_called = {"value": False}

    def _fake_create_agent(**kwargs):
        create_agent_called["value"] = True
        return _FakeAgent()

    monkeypatch.setattr(
        "app.core.supervisor.tools.create_agent",
        _fake_create_agent,
    )

    ctx = SupervisorContext(
        supervisor_session_id="sv-guard-001",
        user_request="start",
        workflow_definitions=[
            WorkflowNodeDefinition(key="outline", label="Outline", node_type="text"),
            WorkflowNodeDefinition(
                key="script",
                label="Script",
                node_type="text",
                depends_on=["outline"],
            ),
        ],
    )
    registry = SupervisorAgentRegistry(
        agents=[
            RegisteredAgent(
                name="script_agent",
                label="Script",
                description="x",
                node_keys=["script"],
            )
        ]
    )

    events = []
    async for event in call_sub_agent(
        sub_agent_name="script_agent",
        task_description="write script",
        supervisor_context=ctx,
        registry=registry,
    ):
        events.append(event)

    # guard 命中：只 yield 一个 SubAgentEndEvent，不启动 sub-agent
    assert create_agent_called["value"] is False
    assert len(events) == 1
    end = events[0]
    assert end.type == "sub_agent_end"
    assert end.session_id == ""
    result = end.result
    assert result["ok"] is False
    assert result["error_code"] == "DEPENDENCY_NOT_SATISFIED"
    assert "outline" in result["message"]
    assert result["context"]["sub_agent_name"] == "script_agent"


@pytest.mark.asyncio
async def test_call_sub_agent_unknown_agent_returns_structured_error(monkeypatch):
    """未注册的 sub_agent_name 也走 ToolError 结构，统一响应形态。"""
    ctx = SupervisorContext(
        supervisor_session_id="sv-guard-002",
        user_request="start",
        workflow_definitions=[
            WorkflowNodeDefinition(key="outline", label="Outline", node_type="text"),
        ],
    )
    registry = SupervisorAgentRegistry(
        agents=[
            RegisteredAgent(
                name="outline_agent",
                label="Outline",
                description="x",
                node_keys=["outline"],
            )
        ]
    )

    events = []
    async for event in call_sub_agent(
        sub_agent_name="unknown_agent",
        task_description="x",
        supervisor_context=ctx,
        registry=registry,
    ):
        events.append(event)

    assert len(events) == 1
    result = events[0].result
    assert result["ok"] is False
    assert result["error_code"] == "UNKNOWN_SUB_AGENT"
    assert "unknown_agent" in result["message"]
    assert result["context"]["available"] == ["outline_agent"]


@pytest.mark.asyncio
async def test_call_sub_agent_proceeds_when_dependencies_fresh(monkeypatch):
    """上游 fresh 后调下游应正常执行（不被 guard 拦）。"""
    monkeypatch.setattr(
        "app.core.supervisor.tools.create_agent",
        lambda **kwargs: _FakeAgent(),
    )

    ctx = SupervisorContext(
        supervisor_session_id="sv-guard-003",
        user_request="start",
        workflow_definitions=[
            WorkflowNodeDefinition(key="outline", label="Outline", node_type="text"),
            WorkflowNodeDefinition(
                key="script",
                label="Script",
                node_type="text",
                depends_on=["outline"],
            ),
        ],
    )
    # 模拟 outline 已经跑过：节点 fresh
    apply_node_update(
        ctx.workflow,
        "outline",
        artifact={"v": 1},
        updated_by="agent",
        last_agent="outline_agent",
    )

    registry = SupervisorAgentRegistry(
        agents=[
            RegisteredAgent(
                name="script_agent",
                label="Script",
                description="x",
                node_keys=["script"],
            )
        ]
    )

    events = []
    async for event in call_sub_agent(
        sub_agent_name="script_agent",
        task_description="write script",
        supervisor_context=ctx,
        registry=registry,
    ):
        events.append(event)

    # 正常路径：先 SubAgentStart，最后 SubAgentEnd
    assert events[0].type == "sub_agent_start"
    assert events[-1].type == "sub_agent_end"
    # SubAgentEnd.result 不是 ToolError
    final_result = events[-1].result
    assert "error_code" not in final_result or final_result.get("ok") is not False
