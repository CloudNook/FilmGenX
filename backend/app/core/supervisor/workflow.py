"""
Supervisor 工作流图模型。

用版本化节点图替代固定阶段流水线，支撑：
- 用户从任意节点回退修改
- 下游依赖自动标记为 pending_confirmation
- Supervisor 输出结构化建议动作
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

NodeStatus = Literal[
    "missing",
    "ready",
    "fresh",
    "pending_confirmation",
    "running",
    "completed",
    "failed",
]


class WorkflowNodeDefinition(BaseModel):
    key: str
    label: str
    node_type: str
    depends_on: list[str] = Field(default_factory=list)
    produces_artifact: bool = True
    can_run_automatically: bool = True


class WorkflowNodeState(BaseModel):
    key: str
    version: int = 0
    status: NodeStatus = "missing"
    artifact: dict[str, Any] | None = None
    updated_by: str | None = None
    last_agent: str | None = None
    updated_at: datetime | None = None


class SuggestedAction(BaseModel):
    action: Literal["run_agent", "review_impacts", "confirm_node", "revise_node"]
    target_node: str
    reason: str
    agent_name: str | None = None
    blocking_nodes: list[str] = Field(default_factory=list)


class WorkflowSnapshot(BaseModel):
    profile: str
    nodes: dict[str, WorkflowNodeState]
    dependency_map: dict[str, list[str]]
    suggested_actions: list[SuggestedAction] = Field(default_factory=list)
    updated_at: datetime | None = None


def build_workflow_snapshot(
    profile: str,
    definitions: list[WorkflowNodeDefinition],
) -> WorkflowSnapshot:
    nodes: dict[str, WorkflowNodeState] = {}
    dependency_map: dict[str, list[str]] = {}

    for definition in definitions:
        nodes[definition.key] = WorkflowNodeState(
            key=definition.key,
            status="ready" if not definition.depends_on else "missing",
        )
        dependency_map[definition.key] = list(definition.depends_on)

    snapshot = WorkflowSnapshot(
        profile=profile,
        nodes=nodes,
        dependency_map=dependency_map,
    )
    snapshot.suggested_actions = build_suggested_actions(snapshot)
    return snapshot


def _mark_dependents_pending(snapshot: WorkflowSnapshot, target_key: str) -> None:
    for key, deps in snapshot.dependency_map.items():
        if target_key in deps:
            snapshot.nodes[key].status = "pending_confirmation"
            _mark_dependents_pending(snapshot, key)


def _refresh_ready_states(snapshot: WorkflowSnapshot) -> None:
    for key, node in snapshot.nodes.items():
        if node.status not in {"missing", "ready"}:
            continue

        deps = snapshot.dependency_map.get(key, [])
        if not deps:
            if node.status == "missing":
                node.status = "ready"
            continue

        dep_statuses = {snapshot.nodes[dep].status for dep in deps}
        if dep_statuses <= {"fresh", "completed"}:
            node.status = "ready"


def apply_node_update(
    snapshot: WorkflowSnapshot,
    node_key: str,
    artifact: dict[str, Any],
    *,
    updated_by: str,
    last_agent: str | None = None,
) -> WorkflowSnapshot:
    node = snapshot.nodes[node_key]
    node.version += 1
    node.status = "fresh"
    node.artifact = artifact
    node.updated_by = updated_by
    node.last_agent = last_agent
    node.updated_at = datetime.now(timezone.utc)

    if node.version > 1:
        _mark_dependents_pending(snapshot, node_key)
    _refresh_ready_states(snapshot)
    snapshot.updated_at = datetime.now(timezone.utc)
    snapshot.suggested_actions = build_suggested_actions(snapshot)
    return snapshot


def confirm_node(snapshot: WorkflowSnapshot, node_key: str) -> WorkflowSnapshot:
    snapshot.nodes[node_key].status = "fresh"
    snapshot.updated_at = datetime.now(timezone.utc)
    _refresh_ready_states(snapshot)
    snapshot.suggested_actions = build_suggested_actions(snapshot)
    return snapshot


def build_suggested_actions(snapshot: WorkflowSnapshot) -> list[SuggestedAction]:
    actions: list[SuggestedAction] = []

    for key, node in snapshot.nodes.items():
        if node.status == "pending_confirmation":
            actions.append(
                SuggestedAction(
                    action="review_impacts",
                    target_node=key,
                    reason=f"Node '{key}' depends on updated upstream content",
                )
            )
        elif node.status == "ready":
            actions.append(
                SuggestedAction(
                    action="run_agent",
                    target_node=key,
                    reason=f"Node '{key}' is ready to run",
                )
            )

    return actions
