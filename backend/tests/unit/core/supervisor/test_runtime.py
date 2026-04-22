from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.agent.base import ResumeDecision
from app.core.supervisor.errors import (
    SupervisorInterruptNotFoundError,
    SupervisorInvalidStateError,
)
from app.core.supervisor.persist import SupervisorWorkflowStore
from app.core.supervisor.runtime import SupervisorRuntime


@pytest.mark.asyncio
async def test_prepare_existing_stream_uses_internal_interrupt_loader():
    db = MagicMock()
    db.commit = AsyncMock()
    store = SupervisorWorkflowStore(db=db)
    runtime = SupervisorRuntime(store)
    workflow = SimpleNamespace(
        status="waiting_review",
        completed_at=None,
        error_message=None,
        final_result=None,
        supervisor_session_id="sv-runtime-001",
    )

    runtime.load_interrupt_checkpoint = AsyncMock(
        return_value=SimpleNamespace(tool_name="call_sub_agent")
    )

    prepared = await runtime.prepare_existing_stream(
        workflow,
        user_message="",
        resume=ResumeDecision(action="approve"),
    )

    assert prepared.stream_input == ""
    assert prepared.resume_decision is not None
    assert prepared.resume_decision.action == "approve"
    runtime.load_interrupt_checkpoint.assert_awaited_once_with("sv-runtime-001")


@pytest.mark.asyncio
async def test_prepare_existing_stream_raises_when_interrupt_checkpoint_missing():
    db = MagicMock()
    db.commit = AsyncMock()
    store = SupervisorWorkflowStore(db=db)
    runtime = SupervisorRuntime(store)
    workflow = SimpleNamespace(
        status="waiting_review",
        completed_at=None,
        error_message=None,
        final_result=None,
        supervisor_session_id="sv-runtime-002",
    )

    runtime.load_interrupt_checkpoint = AsyncMock(return_value=None)

    with pytest.raises(SupervisorInterruptNotFoundError):
        await runtime.prepare_existing_stream(
            workflow,
            user_message="",
            resume=ResumeDecision(action="approve"),
        )


@pytest.mark.asyncio
async def test_prepare_existing_stream_rejects_new_message_while_waiting_review():
    db = MagicMock()
    db.commit = AsyncMock()
    store = SupervisorWorkflowStore(db=db)
    runtime = SupervisorRuntime(store)
    workflow = SimpleNamespace(
        status="waiting_review",
        completed_at=None,
        error_message=None,
        final_result=None,
        supervisor_session_id="sv-runtime-003",
    )

    with pytest.raises(SupervisorInvalidStateError):
        await runtime.prepare_existing_stream(
            workflow,
            user_message="continue with edits",
            resume=None,
        )


@pytest.mark.asyncio
async def test_handle_stream_event_saves_snapshot_after_sub_agent_completion():
    db = MagicMock()
    db.commit = AsyncMock()
    store = SupervisorWorkflowStore(db=db)
    runtime = SupervisorRuntime(store)
    runtime.save_snapshot = AsyncMock()
    supervisor = SimpleNamespace(
        supervisor_session_id="sv-runtime-004",
        context=SimpleNamespace(workflow=SimpleNamespace()),
    )

    await runtime.handle_stream_event(
        supervisor,
        {
            "type": "sub_agent_end",
            "sub_agent_name": "outline_agent",
        },
    )

    runtime.save_snapshot.assert_awaited_once()
    assert runtime.save_snapshot.await_args.args[0] == "sv-runtime-004"
