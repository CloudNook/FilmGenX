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
