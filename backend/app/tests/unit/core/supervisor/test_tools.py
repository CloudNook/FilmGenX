import pytest
from app.core.supervisor.tools import get_supervisor_tool_schemas


def test_call_sub_agent_schema():
    """验证 call_sub_agent 工具 schema 包含必需字段。"""
    schemas = get_supervisor_tool_schemas()
    names = {s["name"] for s in schemas}
    assert "call_sub_agent" in names
    schema = next(s for s in schemas if s["name"] == "call_sub_agent")
    params = schema["parameters"]
    assert "sub_agent_name" in params["properties"]
    assert "task_description" in params["properties"]
    assert "context_snapshot" in params["properties"]


def test_call_reviewer_schema():
    """验证 call_reviewer 工具 schema 包含必需字段。"""
    schemas = get_supervisor_tool_schemas()
    schema = next(s for s in schemas if s["name"] == "call_reviewer")
    params = schema["parameters"]
    assert "content" in params["properties"]
    assert "review_criteria" in params["properties"]


def test_get_workflow_state_schema():
    """验证 get_workflow_state 工具 schema。"""
    schemas = get_supervisor_tool_schemas()
    schema = next(s for s in schemas if s["name"] == "get_workflow_state")
    assert schema is not None
