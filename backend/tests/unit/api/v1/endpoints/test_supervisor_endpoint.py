from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.supervisor import (
    SupervisorResumePayload,
    SupervisorStartRequest,
    _stream_supervisor,
    chat_supervisor,
    get_interrupt_state,
    get_supervisor_workflow,
    list_supervisor_workflows,
)
from app.core.supervisor.events import SupervisorStartedEvent
from app.core.supervisor.workflow import WorkflowNodeDefinition, build_workflow_snapshot


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "expected_request"),
    [
        (
            SupervisorStartRequest(
                project_id=1,
                content="make a trailer",
            ),
            SupervisorStartRequest(
                project_id=1,
                content="make a trailer",
            ),
        ),
        (
            SupervisorStartRequest(
                project_id=1,
                session_id="sv-continue-001",
                content="continue with a darker tone",
            ),
            SupervisorStartRequest(
                project_id=1,
                session_id="sv-continue-001",
                content="continue with a darker tone",
            ),
        ),
        (
            SupervisorStartRequest(
                project_id=1,
                session_id="sv-resume-001",
                resume=SupervisorResumePayload(action="approve"),
            ),
            SupervisorStartRequest(
                project_id=1,
                session_id="sv-resume-001",
                resume=SupervisorResumePayload(action="approve"),
            ),
        ),
    ],
)
async def test_chat_supervisor_routes_all_requests_through_stream_entry(
    monkeypatch,
    body,
    expected_request,
):
    db = MagicMock()
    sentinel_response = object()
    stream_supervisor = AsyncMock(return_value=sentinel_response)

    monkeypatch.setattr(
        "app.api.v1.endpoints.supervisor._stream_supervisor",
        stream_supervisor,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.supervisor._start_supervisor_stream",
        AsyncMock(side_effect=AssertionError("legacy start helper should not be used")),
        raising=False,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.supervisor._continue_supervisor_stream",
        AsyncMock(side_effect=AssertionError("legacy continue helper should not be used")),
        raising=False,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.supervisor._resume_supervisor_stream",
        AsyncMock(side_effect=AssertionError("legacy resume helper should not be used")),
        raising=False,
    )

    response = await chat_supervisor(
        project_id=1,
        body=body,
        user_id=7,
        db=db,
    )

    assert response is sentinel_response
    stream_supervisor.assert_awaited_once()
    request = stream_supervisor.await_args.args[0]
    assert request.model_dump() == expected_request.model_dump()
    assert stream_supervisor.await_args.kwargs["user_id"] == 7
    assert stream_supervisor.await_args.kwargs["db"] is db


@pytest.mark.asyncio
async def test_chat_supervisor_resume_restores_workflow_runtime_config(monkeypatch):
    captured_kwargs = {}
    db = MagicMock()
    db.commit = AsyncMock()

    def fake_create_supervisor(**kwargs):
        captured_kwargs.update(kwargs)
        async def fake_stream(*, initial_input, **stream_kwargs):
            if False:
                yield None
        return SimpleNamespace(
            supervisor_session_id="sv-123",
            context=SimpleNamespace(workflow=None),
            stream=fake_stream,
        )

    monkeypatch.setattr(
        "app.core.supervisor.factory.create_supervisor",
        fake_create_supervisor,
    )

    response = await chat_supervisor(
        project_id=1,
        body=SupervisorStartRequest(
            session_id="sv-123",
            resume=SupervisorResumePayload(action="approve"),
        ),
        user_id=1,
        db=db,
    )

    assert response.media_type == "text/event-stream"
    assert captured_kwargs["db"] is db
    assert "workflow_store" not in captured_kwargs
    assert "event_appender" not in captured_kwargs


@pytest.mark.asyncio
async def test_chat_supervisor_resume_uses_stream_api(monkeypatch):
    workflow_snapshot = build_workflow_snapshot(
        profile="cinematic_series",
        definitions=[
            WorkflowNodeDefinition(
                key="outline",
                label="Outline",
                node_type="text",
                depends_on=[],
            ),
        ],
    ).model_dump()
    stored_workflow = SimpleNamespace(
        supervisor_session_id="sv-123",
        owner_id=1,
        status="waiting_review",
        user_request="make a trailer",
        model="gemini-3-flash-preview",
        workflow_snapshot=workflow_snapshot,
        workflow_profile="cinematic_series",
        auto_run=True,
        hitl_enabled=False,
        review_nodes=None,
    )
    db = MagicMock()
    db.commit = AsyncMock()

    monkeypatch.setattr(
        "app.core.supervisor.persist.SupervisorWorkflowStore.get_workflow_by_session",
        AsyncMock(return_value=stored_workflow),
    )
    monkeypatch.setattr(
        "app.core.supervisor.persist.SupervisorWorkflowStore.update_status",
        AsyncMock(return_value=stored_workflow),
    )
    captured = {}

    async def fake_stream(*, initial_input, resume=None, **kwargs):
        captured["initial_input"] = initial_input
        captured["resume"] = resume
        if False:
            yield None

    monkeypatch.setattr(
        "app.core.supervisor.factory.create_supervisor",
        lambda **kwargs: SimpleNamespace(
            supervisor_session_id="sv-123",
            context=SimpleNamespace(workflow=None),
            stream=fake_stream,
        ),
    )

    response = await chat_supervisor(
        project_id=1,
        body=SupervisorStartRequest(
            session_id="sv-123",
            resume=SupervisorResumePayload(action="approve"),
        ),
        user_id=1,
        db=db,
    )

    first_chunk = await anext(response.body_iterator)
    decoded = first_chunk.decode() if isinstance(first_chunk, bytes) else first_chunk

    assert decoded == "data: [DONE]\n\n"
    assert captured["initial_input"] == ""
    assert captured["resume"].action == "approve"
    assert not hasattr(captured["resume"], "feedback")


def test_supervisor_resume_payload_exposes_only_action():
    payload = SupervisorResumePayload(action="approve")

    assert payload.model_dump() == {"action": "approve"}
    assert "feedback" not in SupervisorResumePayload.model_json_schema()["properties"]


@pytest.mark.asyncio
async def test_chat_supervisor_resume_requires_session_id():
    db = MagicMock()
    db.commit = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await chat_supervisor(
            project_id=1,
            body=SupervisorStartRequest(
                resume=SupervisorResumePayload(action="approve"),
            ),
            user_id=1,
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert "session_id" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_chat_supervisor_emits_started_event(monkeypatch):
    workflow = SimpleNamespace(
        id=7,
        status="running",
        workflow_profile="default",
        auto_run=False,
    )
    db = MagicMock()
    db.commit = AsyncMock()

    service_get = AsyncMock(return_value=workflow)
    monkeypatch.setattr(
        "app.core.supervisor.persist.SupervisorWorkflowStore.create_workflow",
        AsyncMock(return_value=workflow),
    )
    monkeypatch.setattr(
        "app.core.supervisor.persist.SupervisorWorkflowStore.save_workflow_state",
        AsyncMock(return_value=workflow),
    )
    monkeypatch.setattr(
        "app.core.supervisor.persist.SupervisorWorkflowStore.get_workflow_by_session",
        service_get,
    )

    async def fake_stream(*, initial_input, project_id=None, owner_id=None, resume=None, require_existing=False):
        yield SupervisorStartedEvent(
            workflow_id=7,
            supervisor_session_id="sv-test-001",
            status="running",
            workflow_profile="default",
            auto_run=False,
        )

    fake_supervisor = SimpleNamespace(
        supervisor_session_id="sv-test-001",
        context=SimpleNamespace(
            workflow=SimpleNamespace(model_dump=lambda: {"profile": "default", "nodes": {}})
        ),
        stream=fake_stream,
    )
    monkeypatch.setattr(
        "app.core.supervisor.factory.create_supervisor",
        lambda **kwargs: fake_supervisor,
    )

    response = await chat_supervisor(
        project_id=1,
        body=SupervisorStartRequest(project_id=1, user_request="生成一个 AI 漫剧"),
        user_id=1,
        db=db,
    )

    first_chunk = await anext(response.body_iterator)
    decoded = first_chunk.decode() if isinstance(first_chunk, bytes) else first_chunk

    assert '"type": "supervisor_started"' in decoded
    assert '"workflow_id": 7' in decoded
    assert '"supervisor_session_id": "sv-test-001"' in decoded


@pytest.mark.asyncio
async def test_chat_supervisor_human_review_uses_core_factory_defaults(monkeypatch):
    captured_kwargs = {}

    def fake_create_supervisor(**kwargs):
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            supervisor_session_id="sv-test-hitl",
            context=SimpleNamespace(workflow=None),
            stream=fake_stream,
        )

    async def fake_stream(*, initial_input, **kwargs):
        if False:
            yield None

    monkeypatch.setattr(
        "app.core.supervisor.factory.create_supervisor",
        fake_create_supervisor,
    )

    response = await chat_supervisor(
        project_id=1,
        body=SupervisorStartRequest(
            project_id=1,
            user_request="write outline",
            human_review=True,
            review_nodes=["outline"],
        ),
        user_id=1,
        db=MagicMock(),
    )

    assert response.media_type == "text/event-stream"
    assert captured_kwargs["hitl_enabled"] is True
    assert captured_kwargs["review_nodes"] == ["outline"]
    assert captured_kwargs["persist"] is None
    assert "middlewares" not in captured_kwargs


@pytest.mark.asyncio
async def test_chat_supervisor_serializes_datetime_event_payload(monkeypatch):
    workflow = SimpleNamespace(
        id=9,
        status="running",
        workflow_profile="default",
        auto_run=False,
    )
    db = MagicMock()
    db.commit = AsyncMock()

    monkeypatch.setattr(
        "app.core.supervisor.persist.SupervisorWorkflowStore.create_workflow",
        AsyncMock(return_value=workflow),
    )
    monkeypatch.setattr(
        "app.core.supervisor.persist.SupervisorWorkflowStore.save_workflow_state",
        AsyncMock(return_value=workflow),
    )
    event_time = datetime(2026, 4, 16, 12, 30, tzinfo=timezone.utc)

    class FakeEvent:
        def model_dump(self):
            return {
                "type": "supervisor_done",
                "supervisor_session_id": "sv-test-009",
                "workflow": {
                    "nodes": {
                        "outline": {
                            "updated_at": event_time,
                        }
                    }
                },
                "final_result": "done",
            }

    async def fake_stream(*, initial_input, **kwargs):
        yield FakeEvent()

    fake_supervisor = SimpleNamespace(
        supervisor_session_id="sv-test-009",
        context=SimpleNamespace(
            workflow=SimpleNamespace(model_dump=lambda: {"profile": "default", "nodes": {}})
        ),
        stream=fake_stream,
    )
    monkeypatch.setattr(
        "app.core.supervisor.factory.create_supervisor",
        lambda **kwargs: fake_supervisor,
    )

    response = await chat_supervisor(
        project_id=1,
        body=SupervisorStartRequest(project_id=1, user_request="测试时间序列化"),
        user_id=1,
        db=db,
    )

    first_chunk = await anext(response.body_iterator)
    decoded = first_chunk.decode() if isinstance(first_chunk, bytes) else first_chunk

    assert '"type": "supervisor_done"' in decoded
    assert '"updated_at": "2026-04-16T12:30:00+00:00"' in decoded


@pytest.mark.asyncio
async def test_chat_supervisor_continues_existing_session_instead_of_creating_new_run(monkeypatch):
    workflow_snapshot = build_workflow_snapshot(
        profile="default",
        definitions=[
            WorkflowNodeDefinition(
                key="outline",
                label="Outline",
                node_type="text",
                depends_on=[],
            ),
        ],
    ).model_dump()
    stored_workflow = SimpleNamespace(
        id=11,
        project_id=1,
        owner_id=1,
        supervisor_session_id="sv-continue-001",
        status="completed",
        user_request="make a trailer",
        model="gemini-3-flash-preview",
        workflow_snapshot=workflow_snapshot,
        workflow_profile="default",
        auto_run=False,
        hitl_enabled=False,
        review_nodes=None,
        completed_at="2026-04-16T00:00:00Z",
        error_message=None,
        final_result="done",
    )
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    monkeypatch.setattr(
        "app.core.supervisor.persist.SupervisorWorkflowStore.get_workflow_by_session",
        AsyncMock(return_value=stored_workflow),
    )
    monkeypatch.setattr(
        "app.core.supervisor.persist.SupervisorWorkflowStore.create_workflow",
        AsyncMock(side_effect=AssertionError("should not create a new workflow")),
    )
    async def fake_continue_stream(*, initial_input, project_id=None, owner_id=None, resume=None, require_existing=False):
        yield SupervisorStartedEvent(
            workflow_id=11,
            supervisor_session_id="sv-continue-001",
            status="running",
            workflow_profile="default",
            auto_run=False,
        )

    fake_supervisor = SimpleNamespace(
        supervisor_session_id="sv-continue-001",
        context=SimpleNamespace(
            workflow=SimpleNamespace(model_dump=lambda: {"profile": "default", "nodes": {}})
        ),
        stream=fake_continue_stream,
    )
    monkeypatch.setattr(
        "app.core.supervisor.factory.create_supervisor",
        lambda **kwargs: fake_supervisor,
    )

    response = await chat_supervisor(
        project_id=1,
        body=SupervisorStartRequest(
            session_id="sv-continue-001",
            content="continue with a darker tone",
        ),
        user_id=1,
        db=db,
    )

    first_chunk = await anext(response.body_iterator)
    decoded = first_chunk.decode() if isinstance(first_chunk, bytes) else first_chunk

    assert '"type": "supervisor_started"' in decoded
    assert '"workflow_id": 11' in decoded
    assert '"supervisor_session_id": "sv-continue-001"' in decoded

@pytest.mark.asyncio
async def test_list_supervisor_workflows_returns_page_response(monkeypatch):
    db = MagicMock()
    workflows = [
        SimpleNamespace(
            id=3,
            project_id=1,
            owner_id=1,
            supervisor_session_id="sv-3",
            user_request="做一版预告片",
            model="gemini-3-flash-preview",
            status="running",
            workflow_profile="default",
            auto_run=False,
            active_node_key="outline",
            loop_count=1,
            total_tokens=120,
            final_result=None,
            error_message=None,
            workflow_snapshot={"profile": "default", "nodes": {}},
            hitl_enabled=False,
            review_nodes=None,
            completed_at=None,
            created_at="2026-04-16T00:00:00Z",
            updated_at="2026-04-16T00:00:00Z",
        )
    ]
    monkeypatch.setattr(
        "app.api.v1.endpoints.supervisor.SupervisorQuery.list_workflows",
        AsyncMock(return_value=(workflows, 1)),
    )

    response = await list_supervisor_workflows(
        project_id=1,
        page=1,
        page_size=20,
        db=db,
        user_id=1,
    )

    assert response.total == 1
    assert response.items[0].supervisor_session_id == "sv-3"
    assert response.items[0].active_node_key == "outline"


@pytest.mark.asyncio
async def test_get_supervisor_workflow_returns_detail_response(monkeypatch):
    db = MagicMock()
    workflow = SimpleNamespace(
        id=5,
        project_id=1,
        owner_id=1,
        supervisor_session_id="sv-5",
        user_request="生成第三集的镜头组",
        model="gemini-3-flash-preview",
        status="waiting_review",
        workflow_profile="cinematic_series",
        auto_run=True,
        active_node_key="storyboard",
        loop_count=4,
        total_tokens=640,
        final_result="流程暂停，等待审批",
        error_message=None,
        hitl_enabled=True,
        review_nodes=["storyboard"],
        completed_at=None,
        created_at="2026-04-16T00:00:00Z",
        updated_at="2026-04-16T00:00:00Z",
    )
    detail_record = SimpleNamespace(
        workflow=workflow,
        event_history=[],
        last_usage=None,
        workflow_snapshot=build_workflow_snapshot(
            profile="cinematic_series",
            definitions=[
                WorkflowNodeDefinition(
                    key="storyboard",
                    label="Storyboard",
                    node_type="plan",
                    depends_on=[],
                ),
            ],
        ).model_dump(),
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.supervisor.SupervisorQuery.get_workflow_detail",
        AsyncMock(
            return_value=detail_record
        ),
    )

    response = await get_supervisor_workflow(
        project_id=1,
        workflow_id=5,
        db=db,
        user_id=1,
    )

    assert response.id == 5
    assert response.supervisor_session_id == "sv-5"
    assert response.workflow_snapshot["profile"] == "cinematic_series"
    assert response.hitl_enabled is True


@pytest.mark.asyncio
async def test_get_interrupt_state_uses_supervisor_query(monkeypatch):
    db = MagicMock()

    monkeypatch.setattr(
        "app.api.v1.endpoints.supervisor.SupervisorQuery.get_interrupt_state",
        AsyncMock(
            return_value=SimpleNamespace(
                status="waiting_review",
                interrupt={"tool_name": "call_sub_agent"},
                workflow={"profile": "default", "nodes": {}},
            )
        ),
    )
    monkeypatch.setattr(
        "app.core.supervisor.factory.create_supervisor",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("interrupt state should not construct supervisor")
        ),
    )

    response = await get_interrupt_state(
        session_id="sv-state-001",
        user_id=1,
        db=db,
    )

    assert response.status == "waiting_review"
    assert response.interrupt == {"tool_name": "call_sub_agent"}
    assert response.workflow == {"profile": "default", "nodes": {}}


async def _empty_async_iter():
    if False:
        yield None
