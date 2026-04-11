import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_supervisor_workflow_service_has_repo():
    """SupervisorWorkflowService 持有 SupervisorWorkflowRepository。"""
    from app.services.supervisor_workflow_service import SupervisorWorkflowService

    mock_db = MagicMock()
    svc = SupervisorWorkflowService(mock_db)
    from app.repositories.supervisor_workflow import SupervisorWorkflowRepository
    assert isinstance(svc.repo, SupervisorWorkflowRepository)


@pytest.mark.asyncio
async def test_create_workflow_calls_project_repo():
    """create_workflow 先校验 project 归属，未找到则抛出 404。"""
    from app.services.supervisor_workflow_service import SupervisorWorkflowService

    mock_db = MagicMock()
    svc = SupervisorWorkflowService(mock_db)

    with patch.object(svc, "repo") as mock_repo, \
         patch("app.services.supervisor_workflow_service.ProjectRepository") as MockPR:
        mock_proj_repo = MagicMock()
        mock_proj_repo.get_by_id_and_owner = AsyncMock(return_value=None)
        MockPR.return_value = mock_proj_repo

        mock_repo.create = AsyncMock(return_value=MagicMock())

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await svc.create_workflow(
                project_id=1, owner_id=1,
                supervisor_session_id="sv-123", user_request="test"
            )
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_workflow_success():
    """project 归属校验通过时，创建 workflow 记录。"""
    from app.services.supervisor_workflow_service import SupervisorWorkflowService

    mock_db = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    svc = SupervisorWorkflowService(mock_db)

    mock_workflow = MagicMock()
    mock_workflow.id = 1
    mock_workflow.supervisor_session_id = "sv-abc"
    mock_workflow.status = "running"

    with patch.object(svc, "repo") as mock_repo, \
         patch("app.services.supervisor_workflow_service.ProjectRepository") as MockPR:
        mock_proj_repo = MagicMock()
        mock_proj_repo.get_by_id_and_owner = AsyncMock(return_value=MagicMock(id=1))
        MockPR.return_value = mock_proj_repo
        mock_repo.create = AsyncMock(return_value=mock_workflow)

        result = await svc.create_workflow(
            project_id=1,
            owner_id=1,
            supervisor_session_id="sv-abc",
            user_request="test",
        )
        assert result == mock_workflow
        mock_repo.create.assert_awaited_once()
        call_kwargs = mock_repo.create.call_args.kwargs
        assert call_kwargs["status"] == "running"
        assert call_kwargs["supervisor_session_id"] == "sv-abc"


@pytest.mark.asyncio
async def test_increment_loop_count():
    """increment_loop_count 将 loop_count +1。"""
    from app.services.supervisor_workflow_service import SupervisorWorkflowService

    mock_db = MagicMock()
    mock_db.commit = AsyncMock()
    svc = SupervisorWorkflowService(mock_db)

    mock_workflow = MagicMock()
    mock_workflow.loop_count = 5

    with patch.object(svc, "repo") as mock_repo:
        mock_repo.get_by_session_id = AsyncMock(return_value=mock_workflow)

        result = await svc.increment_loop_count("sv-abc")
        assert result == 6
        assert mock_workflow.loop_count == 6


@pytest.mark.asyncio
async def test_increment_loop_count_not_found():
    """session 不存在时返回 None。"""
    from app.services.supervisor_workflow_service import SupervisorWorkflowService

    mock_db = MagicMock()
    svc = SupervisorWorkflowService(mock_db)

    with patch.object(svc, "repo") as mock_repo:
        mock_repo.get_by_session_id = AsyncMock(return_value=None)

        result = await svc.increment_loop_count("sv-nonexistent")
        assert result is None


@pytest.mark.asyncio
async def test_mark_failed_calls_repo():
    """mark_failed 调用 repo.mark_failed。"""
    from app.services.supervisor_workflow_service import SupervisorWorkflowService

    mock_db = MagicMock()
    svc = SupervisorWorkflowService(mock_db)

    mock_workflow = MagicMock()
    mock_workflow.status = "failed"
    mock_workflow.error_message = "boom"

    with patch.object(svc, "repo") as mock_repo:
        mock_repo.get_by_session_id = AsyncMock(return_value=mock_workflow)
        mock_repo.mark_failed = AsyncMock(return_value=mock_workflow)

        result = await svc.mark_failed("sv-abc", "boom")
        mock_repo.mark_failed.assert_awaited_once_with(mock_workflow, "boom")
        assert result == mock_workflow


@pytest.mark.asyncio
async def test_append_artifacts():
    """append_artifacts 将 artifact 写入 artifacts[current_stage]。"""
    from app.services.supervisor_workflow_service import SupervisorWorkflowService

    mock_db = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    svc = SupervisorWorkflowService(mock_db)

    mock_workflow = MagicMock()
    mock_workflow.artifacts = {"outline_writer": {"title": "大纲1"}}

    with patch.object(svc, "repo") as mock_repo:
        mock_repo.get_by_session_id = AsyncMock(return_value=mock_workflow)

        await svc.append_artifacts("sv-abc", "script_writer", {"script": "剧本内容"})
        assert mock_workflow.artifacts["script_writer"] == {"script": "剧本内容"}
        assert mock_workflow.current_stage == "script_writer"


@pytest.mark.asyncio
async def test_append_artifacts_creates_empty_dict():
    """artifacts 为 None 时自动初始化为空字典。"""
    from app.services.supervisor_workflow_service import SupervisorWorkflowService

    mock_db = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    svc = SupervisorWorkflowService(mock_db)

    mock_workflow = MagicMock()
    mock_workflow.artifacts = None

    with patch.object(svc, "repo") as mock_repo:
        mock_repo.get_by_session_id = AsyncMock(return_value=mock_workflow)

        await svc.append_artifacts("sv-abc", "storyboarder", {"shots": []})
        assert mock_workflow.artifacts == {"storyboarder": {"shots": []}}
