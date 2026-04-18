from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.supervisor import (
    SupervisorResumePayload,
    SupervisorStartRequest,
    _create_supervisor,
    chat_supervisor,
    get_supervisor_workflow,
    list_supervisor_workflows,
)
from app.core.supervisor.workflow import WorkflowNodeDefinition, build_workflow_snapshot


@pytest.mark.asyncio
async def test_chat_supervisor_resume_restores_workflow_runtime_config(monkeypatch):
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
        "app.services.supervisor_workflow_service.SupervisorWorkflowService.get_workflow_by_session",
        AsyncMock(return_value=stored_workflow),
    )
    monkeypatch.setattr(
        "app.services.supervisor_workflow_service.SupervisorWorkflowService.update_status",
        AsyncMock(return_value=stored_workflow),
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.supervisor.DBPersistStrategy.load_interrupt_state",
        AsyncMock(
            return_value=SimpleNamespace(
                tool_name="call_sub_agent",
                arguments={},
                context={},
            )
        ),
    )

    captured_kwargs = {}

    def fake_create_supervisor(**kwargs):
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            context=SimpleNamespace(workflow=None),
            resume=None,
        )

    monkeypatch.setattr(
        "app.core.supervisor.factory.create_supervisor",
        fake_create_supervisor,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.supervisor._append_supervisor_event",
        AsyncMock(return_value=None),
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
    assert captured_kwargs["workflow_profile"] == "cinematic_series"
    assert captured_kwargs["auto_run"] is True
    assert captured_kwargs["workflow_service"] is not None


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
        "app.services.supervisor_workflow_service.SupervisorWorkflowService.create_workflow",
        AsyncMock(return_value=workflow),
    )
    monkeypatch.setattr(
        "app.services.supervisor_workflow_service.SupervisorWorkflowService.save_workflow_snapshot",
        AsyncMock(return_value=workflow),
    )
    monkeypatch.setattr(
        "app.services.supervisor_workflow_service.SupervisorWorkflowService.get_workflow_by_session",
        service_get,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.supervisor._append_supervisor_event",
        AsyncMock(return_value=None),
    )

    fake_supervisor = SimpleNamespace(
        supervisor_session_id="sv-test-001",
        context=SimpleNamespace(
            workflow=SimpleNamespace(model_dump=lambda: {"profile": "default", "nodes": {}})
        ),
        stream=AsyncMock(return_value=_empty_async_iter()),
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.supervisor._create_supervisor",
        lambda body, user_id, workflow_service: fake_supervisor,
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


def test_create_supervisor_human_review_interrupts_call_sub_agent(monkeypatch):
    captured_kwargs = {}

    def fake_create_supervisor(**kwargs):
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            supervisor_session_id="sv-test-hitl",
            context=SimpleNamespace(workflow=None),
            stream=None,
        )

    monkeypatch.setattr(
        "app.core.supervisor.factory.create_supervisor",
        fake_create_supervisor,
    )

    _create_supervisor(
        SupervisorStartRequest(
            project_id=1,
            user_request="write outline",
            human_review=True,
        ),
        user_id=1,
        workflow_service=MagicMock(),
    )

    middlewares = captured_kwargs["middlewares"]
    assert len(middlewares) == 1
    hitl = middlewares[0]
    assert hitl.auto_tool_list == {"get_workflow_state", "call_reviewer"}


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
        "app.services.supervisor_workflow_service.SupervisorWorkflowService.create_workflow",
        AsyncMock(return_value=workflow),
    )
    monkeypatch.setattr(
        "app.services.supervisor_workflow_service.SupervisorWorkflowService.save_workflow_snapshot",
        AsyncMock(return_value=workflow),
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.supervisor._append_supervisor_event",
        AsyncMock(return_value=None),
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

    async def fake_stream(initial_input):
        yield FakeEvent()

    fake_supervisor = SimpleNamespace(
        supervisor_session_id="sv-test-009",
        context=SimpleNamespace(
            workflow=SimpleNamespace(model_dump=lambda: {"profile": "default", "nodes": {}})
        ),
        stream=fake_stream,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.supervisor._create_supervisor",
        lambda body, user_id, workflow_service: fake_supervisor,
    )

    response = await chat_supervisor(
        project_id=1,
        body=SupervisorStartRequest(project_id=1, user_request="测试时间序列化"),
        user_id=1,
        db=db,
    )

    first_chunk = await anext(response.body_iterator)
    second_chunk = await anext(response.body_iterator)
    decoded = second_chunk.decode() if isinstance(second_chunk, bytes) else second_chunk

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
        "app.services.supervisor_workflow_service.SupervisorWorkflowService.get_workflow_by_session",
        AsyncMock(return_value=stored_workflow),
    )
    monkeypatch.setattr(
        "app.services.supervisor_workflow_service.SupervisorWorkflowService.create_workflow",
        AsyncMock(side_effect=AssertionError("should not create a new workflow")),
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.supervisor._append_supervisor_event",
        AsyncMock(return_value=None),
    )

    fake_supervisor = SimpleNamespace(
        supervisor_session_id="sv-continue-001",
        context=SimpleNamespace(
            workflow=SimpleNamespace(model_dump=lambda: {"profile": "default", "nodes": {}})
        ),
        stream=AsyncMock(return_value=_empty_async_iter()),
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.supervisor._create_supervisor",
        lambda body, user_id, workflow_service: fake_supervisor,
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
        "app.services.supervisor_workflow_service.SupervisorWorkflowService.list_workflows",
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
        workflow_snapshot={"profile": "cinematic_series", "nodes": {"storyboard": {"status": "pending_confirmation"}}},
        hitl_enabled=True,
        review_nodes=["storyboard"],
        completed_at=None,
        created_at="2026-04-16T00:00:00Z",
        updated_at="2026-04-16T00:00:00Z",
    )
    monkeypatch.setattr(
        "app.services.supervisor_workflow_service.SupervisorWorkflowService.get_workflow",
        AsyncMock(return_value=workflow),
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.supervisor._load_supervisor_event_history",
        AsyncMock(return_value=[]),
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


async def _empty_async_iter():
    if False:
        yield None
