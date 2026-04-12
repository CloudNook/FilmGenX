import pytest
from app.models.supervisor_workflow import SupervisorWorkflow


def test_supervisor_workflow_tablename():
    assert SupervisorWorkflow.__tablename__ == "supervisor_workflows"


def test_supervisor_workflow_default_status():
    """status 字段默认为 'running'。"""
    assert SupervisorWorkflow.status.default.arg == "running"


def test_supervisor_workflow_default_loop_count():
    """loop_count 字段默认为 0。"""
    assert SupervisorWorkflow.loop_count.default.arg == 0


def test_supervisor_workflow_default_total_tokens():
    """total_tokens 字段默认为 0。"""
    assert SupervisorWorkflow.total_tokens.default.arg == 0


def test_supervisor_workflow_artifacts_is_json():
    """artifacts 字段使用 JSON 类型。"""
    # Verify the column uses JSON type (SQLAlchemy JSON type)
    from sqlalchemy import JSON
    col = SupervisorWorkflow.__table__.c["artifacts"]
    assert isinstance(col.type, JSON)


def test_supervisor_workflow_session_id_unique():
    """supervisor_session_id 字段为 unique。"""
    col = SupervisorWorkflow.__table__.c["supervisor_session_id"]
    assert col.unique is True


def test_supervisor_workflow_has_completed_at_nullable():
    """completed_at 字段可为空（running 状态时未设置）。"""
    col = SupervisorWorkflow.__table__.c["completed_at"]
    assert col.nullable is True
