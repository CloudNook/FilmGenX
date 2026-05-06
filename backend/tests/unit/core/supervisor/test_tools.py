import pytest

from app.core.agent.base import (
    AgentResult,
    DoneEvent,
    TextEvent,
    ThinkingEvent,
    ToolEndEvent,
    ToolStartEvent,
)
from app.core.agent.persist.db_strategy import DBPersistStrategy
from app.core.supervisor.concurrency import SubAgentConcurrencyLimiter
from app.core.supervisor.context import SupervisorContext
from app.core.supervisor.registry import RegisteredAgent, SupervisorAgentRegistry
from app.core.supervisor.tools import call_sub_agent
from app.core.supervisor.tools import get_workflow_state
from app.core.supervisor.workflow import WorkflowNodeDefinition


@pytest.mark.asyncio
async def test_get_workflow_state_returns_structured_snapshot():
    ctx = SupervisorContext(
        supervisor_session_id="sv-123",
        user_request="start",
        workflow_definitions=[
            WorkflowNodeDefinition(
                key="outline",
                label="Outline",
                node_type="text",
                depends_on=[],
            ),
        ],
    )

    payload = await get_workflow_state(supervisor_context=ctx)

    assert payload["workflow"]["profile"] == "default"
    assert payload["workflow"]["nodes"]["outline"]["status"] == "ready"
    assert payload["sub_agent_sessions"] == {}
    assert payload["review_history"] == []
    assert "current_phase" not in payload
    assert "artifacts" not in payload


@pytest.mark.asyncio
async def test_get_workflow_state_serializes_typed_context_records():
    ctx = SupervisorContext(
        supervisor_session_id="sv-typed-001",
        user_request="start",
        workflow_definitions=[
            WorkflowNodeDefinition(
                key="outline",
                label="Outline",
                node_type="text",
                depends_on=[],
            ),
        ],
    )
    ctx.register_sub_agent_session("outline_agent", "sub-outline-001")
    ctx.record_execution(
        agent_name="outline_agent",
        session_id="sub-outline-001",
        status="completed",
        node_keys=["outline"],
    )

    payload = await get_workflow_state(supervisor_context=ctx)

    assert payload["sub_agent_sessions"] == {"outline_agent": "sub-outline-001"}
    assert payload["execution_history"] == [
        {
            "agent_name": "outline_agent",
            "session_id": "sub-outline-001",
            "status": "completed",
            "node_keys": ["outline"],
        }
    ]


class _FakeAgent:
    async def stream(self, initial_input: str):
        yield DoneEvent(
            result=AgentResult(
                agent_name="outline_agent",
                raw_output="outline result",
                finished=True,
            )
        )


class _StreamingFakeAgent:
    async def stream(self, initial_input: str):
        yield ThinkingEvent(content="thinking")
        yield TextEvent(content="text")
        yield ToolStartEvent(
            tool_call_id="tool-1",
            tool_name="draft_outline",
            arguments={"tone": "cinematic"},
        )
        yield ToolEndEvent(
            tool_call_id="tool-1",
            tool_name="draft_outline",
            result={"ok": True},
            is_error=False,
        )
        yield DoneEvent(
            result=AgentResult(
                agent_name="outline_agent",
                raw_output="outline result",
                finished=True,
            )
        )


class _FailingAgent:
    async def stream(self, initial_input: str):
        raise RuntimeError("sub-agent boom")
        yield


@pytest.mark.asyncio
async def test_call_sub_agent_updates_workflow_snapshot(monkeypatch):
    monkeypatch.setattr("app.core.supervisor.tools.create_agent", lambda **kwargs: _FakeAgent())

    ctx = SupervisorContext(
        supervisor_session_id="sv-123",
        user_request="start",
        workflow_definitions=[
            WorkflowNodeDefinition(
                key="outline",
                label="Outline",
                node_type="text",
                depends_on=[],
            ),
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
                name="outline_agent",
                label="Outline",
                description="Writes outlines",
                node_keys=["outline"],
            )
        ]
    )

    events = []
    async for event in call_sub_agent(
        sub_agent_name="outline_agent",
        task_description="Generate outline",
        supervisor_context=ctx,
        registry=registry,
    ):
        events.append(event)

    assert events[-1].type == "sub_agent_end"
    assert ctx.workflow is not None
    assert ctx.workflow.nodes["outline"].version == 1
    assert ctx.workflow.nodes["outline"].status == "fresh"
    assert ctx.workflow.nodes["script"].status == "ready"


@pytest.mark.asyncio
async def test_call_sub_agent_uses_concurrency_limiter(monkeypatch):
    monkeypatch.setattr("app.core.supervisor.tools.create_agent", lambda **kwargs: _FakeAgent())

    called = {"value": False}

    class _Permit:
        async def __aenter__(self):
            called["value"] = True
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return False

    class _Limiter:
        async def acquire(self, sub_agent_name: str):
            return _Permit()

    monkeypatch.setattr(
        SubAgentConcurrencyLimiter,
        "get_instance",
        classmethod(lambda cls: _Limiter()),
    )

    ctx = SupervisorContext(
        supervisor_session_id="sv-123",
        user_request="start",
        workflow_definitions=[
            WorkflowNodeDefinition(
                key="outline",
                label="Outline",
                node_type="text",
                depends_on=[],
            ),
        ],
    )
    registry = SupervisorAgentRegistry(
        agents=[
            RegisteredAgent(
                name="outline_agent",
                label="Outline",
                description="Writes outlines",
                node_keys=["outline"],
            )
        ]
    )

    async for _event in call_sub_agent(
        sub_agent_name="outline_agent",
        task_description="Generate outline",
        supervisor_context=ctx,
        registry=registry,
    ):
        pass

    assert called["value"] is True


@pytest.mark.asyncio
async def test_call_sub_agent_forwards_stream_events_with_source_and_session(monkeypatch):
    monkeypatch.setattr(
        "app.core.supervisor.tools.create_agent",
        lambda **kwargs: _StreamingFakeAgent(),
    )

    ctx = SupervisorContext(
        supervisor_session_id="sv-123",
        user_request="start",
        workflow_definitions=[
            WorkflowNodeDefinition(
                key="outline",
                label="Outline",
                node_type="text",
                depends_on=[],
            ),
        ],
    )
    registry = SupervisorAgentRegistry(
        agents=[
            RegisteredAgent(
                name="outline_agent",
                label="Outline",
                description="Writes outlines",
                node_keys=["outline"],
            )
        ]
    )

    events = []
    async for event in call_sub_agent(
        sub_agent_name="outline_agent",
        task_description="Generate outline",
        supervisor_context=ctx,
        registry=registry,
    ):
        events.append(event)

    assert events[0].type == "sub_agent_start"
    assert events[1].type == "thinking"
    assert events[1].source == "outline_agent"
    assert events[1].session_id.startswith("sub-outline_agent-")
    assert events[2].type == "text"
    assert events[2].source == "outline_agent"
    assert events[3].type == "tool_start"
    assert events[3].source == "outline_agent"
    assert events[4].type == "tool_end"
    assert events[4].source == "outline_agent"
    assert events[-1].type == "sub_agent_end"


@pytest.mark.asyncio
async def test_call_sub_agent_emits_error_event_without_mutating_base_model(monkeypatch):
    monkeypatch.setattr(
        "app.core.supervisor.tools.create_agent",
        lambda **kwargs: _FailingAgent(),
    )

    ctx = SupervisorContext(
        supervisor_session_id="sv-123",
        user_request="start",
        workflow_definitions=[
            WorkflowNodeDefinition(
                key="outline",
                label="Outline",
                node_type="text",
                depends_on=[],
            ),
        ],
    )
    registry = SupervisorAgentRegistry(
        agents=[
            RegisteredAgent(
                name="outline_agent",
                label="Outline",
                description="Writes outlines",
                node_keys=["outline"],
            )
        ]
    )

    events = []
    async for event in call_sub_agent(
        sub_agent_name="outline_agent",
        task_description="Generate outline",
        supervisor_context=ctx,
        registry=registry,
    ):
        events.append(event)

    assert events[1].type == "error"
    assert events[1].error == "sub-agent boom"
    assert events[1].source == "outline_agent"
    assert events[1].session_id.startswith("sub-outline_agent-")
    assert events[-1].type == "sub_agent_end"
    assert events[-1].result["error"] == "sub-agent boom"


@pytest.mark.asyncio
async def test_call_sub_agent_binds_db_persist_to_supervisor_session(monkeypatch):
    captured = {}

    def _fake_create_agent(**kwargs):
        captured.update(kwargs)
        return _FakeAgent()

    monkeypatch.setattr("app.core.supervisor.tools.create_agent", _fake_create_agent)

    ctx = SupervisorContext(
        supervisor_session_id="sv-persist-001",
        user_request="start",
        workflow_definitions=[
            WorkflowNodeDefinition(
                key="outline",
                label="Outline",
                node_type="text",
                depends_on=[],
            ),
        ],
    )
    registry = SupervisorAgentRegistry(
        agents=[
            RegisteredAgent(
                name="outline_agent",
                label="Outline",
                description="Writes outlines",
                node_keys=["outline"],
            )
        ]
    )

    async for _event in call_sub_agent(
        sub_agent_name="outline_agent",
        task_description="Generate outline",
        supervisor_context=ctx,
        registry=registry,
    ):
        pass

    persist = captured["persist"]
    assert isinstance(persist, DBPersistStrategy)
    assert persist.default_supervisor_session_id == "sv-persist-001"


