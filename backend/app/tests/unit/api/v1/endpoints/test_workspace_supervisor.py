import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def test_supervisor_pipeline_request_schema():
    """验证 SupervisorPipelineRequest 字段。"""
    from app.schemas.workspace import SupervisorPipelineRequest

    req = SupervisorPipelineRequest(
        user_request="生成科幻短片",
        model="gemini-pro",
        max_loop=50,
    )
    assert req.user_request == "生成科幻短片"
    assert req.model == "gemini-pro"
    assert req.max_loop == 50


def test_supervisor_pipeline_request_optional_fields():
    """验证可选字段默认值。"""
    from app.schemas.workspace import SupervisorPipelineRequest

    req = SupervisorPipelineRequest()
    assert req.user_request is None
    assert req.model is None
    assert req.max_loop == 30


def test_workspace_chat_request_with_pipeline():
    """验证 WorkspaceChatRequest 接受 pipeline 字段。"""
    from app.schemas.workspace import WorkspaceChatRequest, SupervisorPipelineRequest

    req = WorkspaceChatRequest(
        content="帮我生成一个短片",
        pipeline=SupervisorPipelineRequest(user_request="科幻短片", max_loop=50),
    )
    assert req.content == "帮我生成一个短片"
    assert req.pipeline is not None
    assert req.pipeline.user_request == "科幻短片"
    assert req.pipeline.max_loop == 50


def test_workspace_chat_request_pipeline_optional():
    """pipeline 字段可为空，走普通 Agent 模式。"""
    from app.schemas.workspace import WorkspaceChatRequest

    req = WorkspaceChatRequest(content="你好")
    assert req.pipeline is None
    assert req.content == "你好"


def test_create_supervisor_for_workspace_injects_workflow_service():
    """验证 _create_supervisor_for_workspace 注入 workflow_service。"""
    from app.api.v1.endpoints.workspaces import _create_supervisor_for_workspace

    mock_service = MagicMock()
    supervisor = _create_supervisor_for_workspace(
        user_request="测试",
        model="gemini-3-flash-preview",
        max_loop=10,
        workflow_service=mock_service,
    )
    assert supervisor is not None
    assert supervisor._tool_ctx.get("workflow_service") is mock_service
    assert supervisor.supervisor_session_id.startswith("sv-")
