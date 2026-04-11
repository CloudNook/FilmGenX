import pytest
from app.core.agent.persist.models import AgentMessageRecord, MessageRecord


def test_agent_message_record_has_supervisor_session_id_column():
    """agent_messages 表包含 supervisor_session_id 字段。"""
    col = AgentMessageRecord.__table__.c["supervisor_session_id"]
    assert col.primary_key is False
    assert col.nullable is True


def test_agent_message_record_supervisor_session_id_indexed():
    """supervisor_session_id 字段有索引。"""
    col = AgentMessageRecord.__table__.c["supervisor_session_id"]
    assert col.index is True


def test_message_record_dataclass_has_supervisor_session_id():
    """MessageRecord dataclass包含 supervisor_session_id 字段。"""
    record = MessageRecord(
        role="assistant",
        content="hello",
        seq=1,
        supervisor_session_id="sv-123",
    )
    assert record.supervisor_session_id == "sv-123"


def test_message_record_supervisor_session_id_defaults_to_none():
    """supervisor_session_id 默认为 None。"""
    record = MessageRecord(role="user", content="hi", seq=1)
    assert record.supervisor_session_id is None
