from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.endpoints.supervisor import (
    SupervisorStartRequest,
    SupervisorResumeRequest,
    get_supervisor_workflow,
    list_supervisor_workflows,
    resume_supervisor_pipeline,
    start_supervisor_pipeline,
)
from app.core.supervisor.workflow import WorkflowNodeDefinition, build_workflow_snapshot


@pytest.mark.asyncio
async def test_resume_supervisor_restores_workflow_runtime_config(monkeypatch):
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
        "app.core.agent.persist.redis_strategy.RedisPersistStrategy.load_interrupt_state",
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

    response = await resume_supervisor_pipeline(
        session_id="sv-123",
        body=SupervisorResumeRequest(action="approve"),
        user_id=1,
        db=db,
    )

    assert response.media_type == "text/event-stream"
    assert captured_kwargs["workflow_profile"] == "cinematic_series"
    assert captured_kwargs["auto_run"] is True
    assert captured_kwargs["workflow_service"] is not None


@pytest.mark.asyncio
async def test_start_supervisor_pipeline_emits_started_event(monkeypatch):
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

    response = await start_supervisor_pipeline(
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
async def test_start_supervisor_pipeline_serializes_datetime_event_payload(monkeypatch):
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

    response = await start_supervisor_pipeline(
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
