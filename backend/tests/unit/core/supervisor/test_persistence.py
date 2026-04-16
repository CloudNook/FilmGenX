from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.supervisor_workflow import SupervisorWorkflow
from app.services.supervisor_workflow_service import SupervisorWorkflowService


def test_supervisor_workflow_model_uses_new_field_names():
    assert hasattr(SupervisorWorkflow, "workflow_snapshot")
    assert hasattr(SupervisorWorkflow, "active_node_key")
    assert hasattr(SupervisorWorkflow, "workflow_profile")
    assert hasattr(SupervisorWorkflow, "auto_run")
    assert not hasattr(SupervisorWorkflow, "artifacts")
    assert not hasattr(SupervisorWorkflow, "current_stage")


@pytest.mark.asyncio
async def test_save_workflow_snapshot_updates_new_columns():
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    service = SupervisorWorkflowService(db=mock_session)

    workflow = SimpleNamespace(
        workflow_snapshot=None,
        active_node_key=None,
    )

    service.repo.get_by_session_id = AsyncMock(return_value=workflow)

    result = await service.save_workflow_snapshot(
        "sv-test",
        workflow_snapshot={"profile": "default", "nodes": {}},
        active_node_key="outline",
    )

    assert result is workflow
    assert workflow.workflow_snapshot == {"profile": "default", "nodes": {}}
    assert workflow.active_node_key == "outline"
    mock_session.commit.assert_awaited()
    mock_session.refresh.assert_awaited_with(workflow)


@pytest.mark.asyncio
async def test_create_workflow_persists_workflow_profile_and_auto_run():
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    service = SupervisorWorkflowService(db=mock_session)

    service.repo.create = AsyncMock(return_value=SimpleNamespace(id=1))

    with pytest.MonkeyPatch.context() as m:
        project_repo = AsyncMock(return_value=SimpleNamespace(id=1))
        m.setattr(
            "app.repositories.project.ProjectRepository.get_by_id_and_owner",
            project_repo,
        )

        await service.create_workflow(
            project_id=1,
            owner_id=1,
            supervisor_session_id="sv-1",
            user_request="hello",
            model="gemini-3-flash-preview",
            workflow_profile="cinematic_series",
            auto_run=True,
        )

    kwargs = service.repo.create.await_args.kwargs
    assert kwargs["workflow_profile"] == "cinematic_series"
    assert kwargs["auto_run"] is True
