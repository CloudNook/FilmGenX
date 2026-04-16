from app.core.supervisor.workflow import (
    apply_node_update,
    build_suggested_actions,
    build_workflow_snapshot,
    confirm_node,
    WorkflowNodeDefinition,
)


def _definitions():
    return [
        WorkflowNodeDefinition(
            key="outline",
            label="Outline",
            node_type="text",
            depends_on=[],
        ),
        WorkflowNodeDefinition(
            key="script",
            label="Script",
            node_type="text",
            depends_on=["outline"],
        ),
        WorkflowNodeDefinition(
            key="storyboard",
            label="Storyboard",
            node_type="plan",
            depends_on=["script"],
        ),
    ]


def test_build_workflow_snapshot_marks_root_nodes_ready():
    snapshot = build_workflow_snapshot(profile="default", definitions=_definitions())

    assert snapshot.profile == "default"
    assert snapshot.nodes["outline"].status == "ready"
    assert snapshot.nodes["script"].status == "missing"
    assert snapshot.nodes["storyboard"].status == "missing"


def test_updating_upstream_node_invalidates_dependents():
    snapshot = build_workflow_snapshot(profile="default", definitions=_definitions())
    snapshot = apply_node_update(snapshot, "outline", {"summary": "v1"}, updated_by="user")
    snapshot = apply_node_update(snapshot, "script", {"draft": "v1"}, updated_by="user")
    snapshot = apply_node_update(snapshot, "outline", {"summary": "v2"}, updated_by="user")

    assert snapshot.nodes["outline"].version == 2
    assert snapshot.nodes["outline"].status == "fresh"
    assert snapshot.nodes["script"].status == "pending_confirmation"
    assert snapshot.nodes["storyboard"].status == "pending_confirmation"


def test_pending_confirmation_generates_suggested_action():
    snapshot = build_workflow_snapshot(profile="default", definitions=_definitions())
    snapshot = apply_node_update(snapshot, "outline", {"summary": "v1"}, updated_by="user")
    snapshot = apply_node_update(snapshot, "script", {"draft": "v1"}, updated_by="user")
    snapshot = apply_node_update(snapshot, "outline", {"summary": "v2"}, updated_by="user")

    actions = build_suggested_actions(snapshot)

    assert any(action.target_node == "script" for action in actions)
    assert any(action.target_node == "storyboard" for action in actions)


def test_first_generation_makes_downstream_ready_instead_of_pending_confirmation():
    snapshot = build_workflow_snapshot(profile="default", definitions=_definitions())
    snapshot = apply_node_update(snapshot, "outline", {"summary": "v1"}, updated_by="user")

    assert snapshot.nodes["script"].status == "ready"

    snapshot = apply_node_update(snapshot, "script", {"draft": "v1"}, updated_by="user")

    assert snapshot.nodes["storyboard"].status == "ready"


def test_confirm_node_restores_fresh_status():
    snapshot = build_workflow_snapshot(profile="default", definitions=_definitions())
    snapshot = apply_node_update(snapshot, "outline", {"summary": "v1"}, updated_by="user")
    snapshot = apply_node_update(snapshot, "script", {"draft": "v1"}, updated_by="user")
    snapshot = apply_node_update(snapshot, "outline", {"summary": "v2"}, updated_by="user")

    snapshot = confirm_node(snapshot, "script")

    assert snapshot.nodes["script"].status == "fresh"
