from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.supervisor.errors import SupervisorInvalidStateError
from app.core.supervisor.query import SupervisorQuery


@pytest.mark.asyncio
async def test_query_get_interrupt_state_uses_store_and_checkpoint(monkeypatch):
    db = MagicMock()
    query = SupervisorQuery(db)
    workflow = SimpleNamespace(
        status="waiting_review",
        supervisor_session_id="sv-query-001",
    )
    workflow_state = SimpleNamespace(
        model_dump=lambda: {"profile": "default", "nodes": {}}
    )

    monkeypatch.setattr(
        "app.core.supervisor.persist.SupervisorWorkflowStore.get_workflow_by_session",
        AsyncMock(return_value=workflow),
    )
    monkeypatch.setattr(
        "app.core.supervisor.persist.SupervisorWorkflowStore.load_workflow_state",
        AsyncMock(return_value=workflow_state),
    )
    monkeypatch.setattr(
        "app.core.supervisor.query.DBPersistStrategy.load_interrupt_state",
        AsyncMock(
            return_value=SimpleNamespace(
                tool_name="call_sub_agent",
                arguments={"task": "outline"},
                context={"node": "outline"},
            )
        ),
    )

    state = await query.get_interrupt_state(session_id="sv-query-001", owner_id=1)

    assert state.status == "waiting_review"
    assert state.interrupt == {
        "tool_name": "call_sub_agent",
        "arguments": {"task": "outline"},
        "context": {"node": "outline"},
    }
    assert state.workflow == {"profile": "default", "nodes": {}}


@pytest.mark.asyncio
async def test_query_get_interrupt_state_rejects_non_waiting_review(monkeypatch):
    db = MagicMock()
    query = SupervisorQuery(db)

    monkeypatch.setattr(
        "app.core.supervisor.persist.SupervisorWorkflowStore.get_workflow_by_session",
        AsyncMock(
            return_value=SimpleNamespace(
                status="completed",
                supervisor_session_id="sv-query-002",
            )
        ),
    )

    with pytest.raises(SupervisorInvalidStateError):
        await query.get_interrupt_state(session_id="sv-query-002", owner_id=1)
