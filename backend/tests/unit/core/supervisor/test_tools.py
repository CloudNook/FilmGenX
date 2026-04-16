import pytest

from app.core.agent.base import AgentResult, DoneEvent
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


class _FakeAgent:
    async def stream(self, initial_input: str):
        yield DoneEvent(
            result=AgentResult(
                agent_name="outline_agent",
                raw_output="outline result",
                finished=True,
            )
        )


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
