from app.core.supervisor.registry import RegisteredAgent, SupervisorAgentRegistry
from app.core.supervisor.tools import get_supervisor_tool_schemas


def test_registry_returns_registered_agent_names():
    registry = SupervisorAgentRegistry(
        agents=[
            RegisteredAgent(
                name="outline_agent",
                label="Outline",
                description="Writes outlines",
                node_keys=["outline"],
            ),
            RegisteredAgent(
                name="script_agent",
                label="Script",
                description="Writes scripts",
                node_keys=["script"],
            ),
        ]
    )

    assert registry.agent_names() == ["outline_agent", "script_agent"]


def test_call_sub_agent_schema_uses_registry_names():
    schemas = get_supervisor_tool_schemas(["outline_agent", "script_agent"])
    call_sub_agent = next(schema for schema in schemas if schema["name"] == "call_sub_agent")

    assert call_sub_agent["parameters"]["properties"]["sub_agent_name"]["enum"] == [
        "outline_agent",
        "script_agent",
    ]
