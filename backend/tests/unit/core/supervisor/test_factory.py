from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.agent.base import ResumeDecision
from app.core.agent.persist.db_strategy import DBPersistStrategy
from app.core.middleware import HumanInTheLoopMiddleware
from app.core.supervisor.errors import SupervisorInvalidStateError
from app.core.supervisor.factory import create_supervisor


def test_create_supervisor_builds_default_registry_and_workflow():
    supervisor = create_supervisor(
        user_request="make a short video",
        persist=None,
    )

    assert supervisor.registry.agent_names() == [
        "outline_agent",
        "script_agent",
        "storyboard_agent",
        "visual_style_agent",
        "character_ref_agent",
        "scene_ref_agent",
        "video_prompt_agent",
    ]
    assert supervisor.context.workflow is not None
    assert supervisor.context.workflow.nodes["outline"].status == "ready"


def test_create_supervisor_injects_registry_into_tool_context():
    supervisor = create_supervisor(
        user_request="make a short video",
        persist=None,
    )

    assert supervisor._tool_ctx["registry"] is supervisor.registry
    assert "workflow_store" not in supervisor._tool_ctx
    assert "workflow_service" not in supervisor._tool_ctx


def test_create_supervisor_builds_db_persist_and_hitl_in_core():
    supervisor = create_supervisor(
        user_request="write outline",
        supervisor_session_id="sv-hitl-001",
        persist=None,
        db=object(),
        hitl_enabled=True,
        review_nodes=["outline"],
    )

    assert isinstance(supervisor._agent.persist, DBPersistStrategy)
    assert supervisor._agent.persist.default_supervisor_session_id == "sv-hitl-001"
    assert len(supervisor._agent.middlewares) == 1
    middleware = supervisor._agent.middlewares[0]
    assert isinstance(middleware, HumanInTheLoopMiddleware)
    assert middleware.auto_tool_list == {"get_workflow_state"}
    assert middleware.context == {"review_sub_agents": ["outline"]}


@pytest.mark.asyncio
async def test_supervisor_run_forwards_resume_decision(monkeypatch):
    fake_agent = SimpleNamespace(
        run=AsyncMock(return_value="ok"),
        stream=None,
    )

    monkeypatch.setattr(
        "app.core.supervisor.supervisor.create_agent",
        lambda **kwargs: fake_agent,
    )

    supervisor = create_supervisor(
        user_request="make a short video",
        persist=None,
    )
    decision = ResumeDecision(action="approve")

    result = await supervisor.run("continue", resume=decision)

    assert result == "ok"
    fake_agent.run.assert_awaited_once_with("continue", resume=decision)


@pytest.mark.asyncio
async def test_supervisor_stream_restores_runtime_config_from_existing_workflow(
    monkeypatch,
):
    stored_workflow = SimpleNamespace(
        supervisor_session_id="sv-existing-001",
        owner_id=1,
        status="waiting_review",
        user_request="make a trailer",
        model="gemini-3-thinking-preview",
        workflow_profile="cinematic_series",
        auto_run=True,
        hitl_enabled=True,
        review_nodes=["outline", "script"],
        workflow_snapshot=None,
    )
    fake_agent = SimpleNamespace(
        run=AsyncMock(return_value="ok"),
        config=SimpleNamespace(model="gemini-3-flash-preview", prompt=""),
    )

    async def fake_stream(initial_input, *, resume=None):
        if False:
            yield None

    fake_agent.stream = fake_stream

    monkeypatch.setattr(
        "app.core.supervisor.supervisor.create_agent",
        lambda **kwargs: fake_agent,
    )
    monkeypatch.setattr(
        "app.core.supervisor.persist.SupervisorWorkflowStore.get_workflow_by_session",
        AsyncMock(return_value=stored_workflow),
    )
    monkeypatch.setattr(
        "app.core.supervisor.persist.SupervisorWorkflowStore.load_workflow_state",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.core.supervisor.runtime.SupervisorRuntime.load_interrupt_checkpoint",
        AsyncMock(return_value=SimpleNamespace(tool_name="call_sub_agent")),
    )

    db = SimpleNamespace(
        commit=AsyncMock(),
        refresh=AsyncMock(),
    )

    supervisor = create_supervisor(
        supervisor_session_id="sv-existing-001",
        user_request="temporary request",
        persist=None,
        db=db,
    )

    stream_result = supervisor.stream(
        "",
        project_id=1,
        owner_id=1,
        resume=ResumeDecision(action="approve"),
        require_existing=True,
    )
    if hasattr(stream_result, "__await__"):
        stream_result = await stream_result

    assert supervisor.model == "gemini-3-thinking-preview"
    assert supervisor.workflow_profile == "cinematic_series"
    assert supervisor.context.user_request == "make a trailer"
    assert supervisor.context.auto_run is True
    assert supervisor.hitl_enabled is True
    assert supervisor.review_nodes == ["outline", "script"]
    assert fake_agent.config.model == "gemini-3-thinking-preview"
    assert "make a trailer" in fake_agent.config.prompt
    assert stream_result is not None


@pytest.mark.asyncio
async def test_supervisor_stream_requires_db_runtime():
    supervisor = create_supervisor(
        user_request="make a short video",
        persist=None,
        db=None,
    )

    with pytest.raises(SupervisorInvalidStateError):
        await supervisor.stream(
            "start",
            project_id=1,
            owner_id=1,
        )
