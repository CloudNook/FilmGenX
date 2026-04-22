from app.core.supervisor.context import SupervisorContext
from app.core.supervisor.workflow import WorkflowNodeDefinition


def test_supervisor_context_initializes_workflow_snapshot():
    ctx = SupervisorContext(
        supervisor_session_id="sv-123",
        user_request="create a new project",
        workflow_profile="cinematic_series",
        workflow_definitions=[
            WorkflowNodeDefinition(
                key="outline",
                label="Outline",
                node_type="text",
                depends_on=[],
            ),
        ],
    )

    assert ctx.workflow is not None
    assert ctx.workflow.profile == "cinematic_series"
    assert "outline" in ctx.workflow.nodes
    assert ctx.workflow.nodes["outline"].status == "ready"
    dumped = ctx.model_dump()
    assert "artifacts" not in dumped


def test_supervisor_context_tracks_sub_agents_and_execution_records():
    ctx = SupervisorContext(
        supervisor_session_id="sv-ctx-001",
        user_request="build a trailer",
        workflow_definitions=[
            WorkflowNodeDefinition(
                key="outline",
                label="Outline",
                node_type="text",
                depends_on=[],
            ),
        ],
    )

    ctx.register_sub_agent_session("outline_agent", "sub-outline-001")
    ctx.record_execution(
        agent_name="outline_agent",
        session_id="sub-outline-001",
        status="completed",
        node_keys=["outline"],
    )

    assert ctx.sub_agent_sessions["outline_agent"].session_id == "sub-outline-001"
    assert ctx.execution_history[0].agent_name == "outline_agent"
    assert ctx.execution_history[0].node_keys == ["outline"]
