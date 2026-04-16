from app.core.supervisor.events import SupervisorDoneEvent


def test_supervisor_done_event_uses_workflow_snapshot():
    event = SupervisorDoneEvent(
        supervisor_session_id="sv-123",
        workflow={"profile": "default", "nodes": {}},
        final_result="done",
    )

    assert event.workflow["profile"] == "default"
    assert not hasattr(event, "artifacts")
