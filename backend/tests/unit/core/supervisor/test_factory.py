from app.core.supervisor.factory import create_supervisor


def test_create_supervisor_builds_default_registry_and_workflow():
    supervisor = create_supervisor(
        user_request="make a short video",
        persist=None,
    )

    assert supervisor.registry.agent_names() == [
        "outline_agent",
        "script_agent",
        "storyboard_agent",
    ]
    assert supervisor.context.workflow is not None
    assert supervisor.context.workflow.nodes["outline"].status == "ready"


def test_create_supervisor_injects_registry_into_tool_context():
    supervisor = create_supervisor(
        user_request="make a short video",
        persist=None,
    )

    assert supervisor._tool_ctx["registry"] is supervisor.registry
