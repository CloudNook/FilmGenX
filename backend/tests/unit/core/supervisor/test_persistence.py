from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.supervisor_workflow import SupervisorWorkflow
from app.models.supervisor_workflow_node import (
    SupervisorWorkflowNode,
    SupervisorWorkflowNodeDependency,
)
from app.core.supervisor.persist import SupervisorWorkflowStore
from app.core.supervisor.workflow import build_workflow_snapshot


def test_supervisor_workflow_model_uses_new_field_names():
    assert not hasattr(SupervisorWorkflow, "workflow_snapshot")
    assert hasattr(SupervisorWorkflow, "active_node_key")
    assert hasattr(SupervisorWorkflow, "workflow_profile")
    assert hasattr(SupervisorWorkflow, "auto_run")
    assert not hasattr(SupervisorWorkflow, "artifacts")
    assert not hasattr(SupervisorWorkflow, "current_stage")
    assert hasattr(SupervisorWorkflowNode, "workflow_id")
    assert hasattr(SupervisorWorkflowNodeDependency, "depends_on_key")


@pytest.mark.asyncio
async def test_save_workflow_state_updates_active_node_key():
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    store = SupervisorWorkflowStore(db=mock_session)

    workflow = SimpleNamespace(
        active_node_key=None,
    )
    workflow_snapshot = build_workflow_snapshot(
        profile="default",
        definitions=[],
    )

    store.get_workflow_by_session = AsyncMock(return_value=workflow)
    store._replace_workflow_state = AsyncMock(return_value=None)

    result = await store.save_workflow_state(
        "sv-test",
        workflow_snapshot,
        active_node_key="outline",
    )

    assert result is workflow
    assert workflow.active_node_key == "outline"
    store._replace_workflow_state.assert_awaited_once()
    assert store._replace_workflow_state.await_args.args == (workflow, workflow_snapshot)
    assert store._replace_workflow_state.await_args.kwargs == {
        "workflow_definitions": None
    }
    mock_session.commit.assert_awaited()
    mock_session.refresh.assert_awaited_with(workflow)


@pytest.mark.asyncio
async def test_create_workflow_persists_workflow_profile_and_auto_run():
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    store = SupervisorWorkflowStore(db=mock_session)

    store._create_workflow_record = AsyncMock(return_value=SimpleNamespace(id=1))

    await store.create_workflow(
        project_id=1,
        owner_id=1,
        supervisor_session_id="sv-1",
        user_request="hello",
        model="gemini-3-flash-preview",
        workflow_profile="cinematic_series",
        auto_run=True,
    )

    kwargs = store._create_workflow_record.await_args.kwargs
    assert kwargs["workflow_profile"] == "cinematic_series"
    assert kwargs["auto_run"] is True
    assert kwargs["owner_id"] == 1


@pytest.mark.asyncio
async def test_load_event_history_merges_agent_and_supervisor_events(monkeypatch):
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    execute = AsyncMock()
    execute.return_value.scalars.return_value.all.return_value = [
        SimpleNamespace(
            id=1,
            role="assistant",
            content="outline ready",
            extra_metadata={"thinking": "planning"},
            agent_name="supervisor",
            session_id="sv-history-001",
            supervisor_session_id="sv-history-001",
            tool_call_id=None,
            tool_name=None,
            created_at=datetime(2026, 4, 21, 8, 0, tzinfo=timezone.utc),
        )
    ]
    mock_session.execute = execute

    store = SupervisorWorkflowStore(db=mock_session)
    monkeypatch.setattr(
        "app.core.supervisor.persist.store.SupervisorEventStore.list_events_by_session",
        AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=2,
                    created_at=datetime(2026, 4, 21, 8, 1, tzinfo=timezone.utc),
                    payload={
                        "type": "supervisor_done",
                        "final_result": "done",
                    },
                )
            ]
        ),
    )

    history = await store.load_event_history("sv-history-001")

    assert history == [
        {
            "type": "thinking",
            "content": "planning",
            "source": "supervisor",
        },
        {
            "type": "text",
            "content": "outline ready",
            "source": "supervisor",
        },
        {
            "type": "supervisor_done",
            "final_result": "done",
        },
    ]
