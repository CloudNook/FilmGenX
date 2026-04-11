import pytest
from app.core.supervisor.session import SupervisorSession


def test_register_and_get_sub_session():
    session = SupervisorSession("sv-abc123")
    session.register_sub_session("outline_writer", "sub-outline-001")
    assert session.get_sub_session("outline_writer") == "sub-outline-001"


def test_get_all_sessions():
    session = SupervisorSession("sv-abc123")
    session.register_sub_session("outline_writer", "sub-outline-001")
    session.register_sub_session("script_writer", "sub-script-002")
    all_sessions = session.get_all_sessions()
    assert len(all_sessions) == 2
    assert all_sessions["outline_writer"] == "sub-outline-001"


def test_get_nonexistent_session():
    session = SupervisorSession("sv-abc123")
    assert session.get_sub_session("nonexistent") is None


def test_session_id_format():
    session = SupervisorSession("sv-abc123")
    assert session.supervisor_session_id == "sv-abc123"
