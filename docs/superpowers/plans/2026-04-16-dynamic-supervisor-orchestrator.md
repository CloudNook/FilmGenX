# Dynamic Supervisor Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. It will decide whether each batch should run in parallel or serial subagent mode and will pass only task-local context to each subagent. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new high-level Supervisor orchestration layer with versioned workflow nodes, dependency invalidation, pending-confirmation state, and pluggable agent registration, while keeping `create_agent` and the Agent runtime unchanged.

**Architecture:** The implementation wraps the existing Agent runtime with a new `core/supervisor` domain layer. The new layer owns workflow graph modeling, state transitions, dependency impact analysis, and structured suggested actions. The runtime-facing surface remains `create_supervisor()` plus the existing FastAPI endpoints, but the underlying state becomes a versioned workflow snapshot rather than a fixed linear phase.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, asyncio, pytest, existing Agent runtime (`create_agent`, `AgentLoop`, `ToolExecutor`)

---

### Task 1: Write the Workflow Graph Tests

**Files:**
- Create: `backend/tests/unit/core/supervisor/test_workflow_graph.py`
- Test: `backend/tests/unit/core/supervisor/test_workflow_graph.py`

- [ ] **Step 1: Write the failing test**

```python
from app.core.supervisor.workflow import (
    WorkflowNodeDefinition,
    WorkflowSnapshot,
    apply_node_update,
    build_workflow_snapshot,
)


def _definitions():
    return [
        WorkflowNodeDefinition(key="outline", label="Outline", node_type="text", depends_on=[]),
        WorkflowNodeDefinition(key="script", label="Script", node_type="text", depends_on=["outline"]),
        WorkflowNodeDefinition(key="storyboard", label="Storyboard", node_type="plan", depends_on=["script"]),
    ]


def test_build_workflow_snapshot_marks_root_ready():
    snapshot = build_workflow_snapshot(profile="default", definitions=_definitions())

    assert snapshot.nodes["outline"].status == "ready"
    assert snapshot.nodes["script"].status == "missing"
    assert snapshot.nodes["storyboard"].status == "missing"


def test_updating_upstream_node_invalidates_dependents():
    snapshot = build_workflow_snapshot(profile="default", definitions=_definitions())
    snapshot = apply_node_update(snapshot, "outline", {"summary": "v1"}, updated_by="user")
    snapshot = apply_node_update(snapshot, "script", {"draft": "v1"}, updated_by="user")
    snapshot = apply_node_update(snapshot, "outline", {"summary": "v2"}, updated_by="user")

    assert snapshot.nodes["outline"].version == 2
    assert snapshot.nodes["script"].status == "pending_confirmation"
    assert snapshot.nodes["storyboard"].status == "pending_confirmation"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/unit/core/supervisor/test_workflow_graph.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.supervisor.workflow'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/core/supervisor/workflow.py
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


class WorkflowSnapshot(BaseModel):
    profile: str
    nodes: dict[str, WorkflowNodeState]
    dependency_map: dict[str, list[str]]
    updated_at: datetime | None = None


def build_workflow_snapshot(profile: str, definitions: list[WorkflowNodeDefinition]) -> WorkflowSnapshot:
    nodes = {}
    dependency_map = {}
    for definition in definitions:
        nodes[definition.key] = WorkflowNodeState(
            key=definition.key,
            status="ready" if not definition.depends_on else "missing",
        )
        dependency_map[definition.key] = list(definition.depends_on)
    return WorkflowSnapshot(profile=profile, nodes=nodes, dependency_map=dependency_map)


def apply_node_update(snapshot: WorkflowSnapshot, node_key: str, artifact: dict[str, Any], updated_by: str) -> WorkflowSnapshot:
    node = snapshot.nodes[node_key]
    node.version += 1
    node.status = "fresh"
    node.artifact = artifact
    node.updated_by = updated_by
    snapshot.updated_at = datetime.now(timezone.utc)

    def _mark_dependents(target: str) -> None:
        for key, deps in snapshot.dependency_map.items():
            if target in deps:
                snapshot.nodes[key].status = "pending_confirmation"
                _mark_dependents(key)

    _mark_dependents(node_key)
    return snapshot
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/unit/core/supervisor/test_workflow_graph.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/unit/core/supervisor/test_workflow_graph.py backend/app/core/supervisor/workflow.py
git commit -m "feat(supervisor): add workflow graph state model"
```

### Task 2: Add Suggested Actions and Confirmation Tests

**Files:**
- Modify: `backend/tests/unit/core/supervisor/test_workflow_graph.py`
- Modify: `backend/app/core/supervisor/workflow.py`

- [ ] **Step 1: Write the failing test**

```python
from app.core.supervisor.workflow import build_suggested_actions, confirm_node


def test_pending_confirmation_generates_revise_suggestion():
    snapshot = build_workflow_snapshot(profile="default", definitions=_definitions())
    snapshot = apply_node_update(snapshot, "outline", {"summary": "v1"}, updated_by="user")
    snapshot = apply_node_update(snapshot, "script", {"draft": "v1"}, updated_by="user")
    snapshot = apply_node_update(snapshot, "outline", {"summary": "v2"}, updated_by="user")

    actions = build_suggested_actions(snapshot)

    assert any(action.target_node == "script" for action in actions)


def test_confirming_node_restores_fresh_status():
    snapshot = build_workflow_snapshot(profile="default", definitions=_definitions())
    snapshot = apply_node_update(snapshot, "outline", {"summary": "v1"}, updated_by="user")
    snapshot = apply_node_update(snapshot, "script", {"draft": "v1"}, updated_by="user")
    snapshot = apply_node_update(snapshot, "outline", {"summary": "v2"}, updated_by="user")

    snapshot = confirm_node(snapshot, "script")

    assert snapshot.nodes["script"].status == "fresh"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/unit/core/supervisor/test_workflow_graph.py -v`
Expected: FAIL with `ImportError` for `build_suggested_actions` or `confirm_node`

- [ ] **Step 3: Write minimal implementation**

```python
class SuggestedAction(BaseModel):
    action: str
    target_node: str
    reason: str
    agent_name: str | None = None
    blocking_nodes: list[str] = Field(default_factory=list)


def build_suggested_actions(snapshot: WorkflowSnapshot) -> list[SuggestedAction]:
    actions: list[SuggestedAction] = []
    for key, node in snapshot.nodes.items():
        if node.status == "pending_confirmation":
            actions.append(
                SuggestedAction(
                    action="review_impacts",
                    target_node=key,
                    reason=f"Node '{key}' depends on changed upstream content",
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


def confirm_node(snapshot: WorkflowSnapshot, node_key: str) -> WorkflowSnapshot:
    snapshot.nodes[node_key].status = "fresh"
    snapshot.updated_at = datetime.now(timezone.utc)
    return snapshot
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/unit/core/supervisor/test_workflow_graph.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/unit/core/supervisor/test_workflow_graph.py backend/app/core/supervisor/workflow.py
git commit -m "feat(supervisor): add workflow suggested actions"
```

### Task 3: Refactor Supervisor Context Around Workflow Snapshot

**Files:**
- Modify: `backend/app/core/supervisor/context.py`
- Create: `backend/tests/unit/core/supervisor/test_context.py`
- Test: `backend/tests/unit/core/supervisor/test_context.py`

- [ ] **Step 1: Write the failing test**

```python
from app.core.supervisor.context import SupervisorContext
from app.core.supervisor.workflow import WorkflowNodeDefinition


def test_supervisor_context_initializes_workflow_snapshot():
    ctx = SupervisorContext(
        supervisor_session_id="sv-123",
        user_request="create a new project",
        workflow_profile="cinematic_series",
        workflow_definitions=[
            WorkflowNodeDefinition(key="outline", label="Outline", node_type="text"),
        ],
    )

    assert ctx.workflow.profile == "cinematic_series"
    assert "outline" in ctx.workflow.nodes
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/unit/core/supervisor/test_context.py -v`
Expected: FAIL because `SupervisorContext` has no `workflow`

- [ ] **Step 3: Write minimal implementation**

```python
from pydantic import BaseModel, Field, model_validator
from app.core.supervisor.workflow import WorkflowNodeDefinition, WorkflowSnapshot, build_workflow_snapshot


class SupervisorContext(BaseModel):
    supervisor_session_id: str
    user_request: str
    workflow_profile: str = "default"
    workflow_definitions: list[WorkflowNodeDefinition] = Field(default_factory=list)
    workflow: WorkflowSnapshot | None = None
    sub_agent_sessions: dict[str, str] = Field(default_factory=dict)
    review_history: list[dict] = Field(default_factory=list)
    execution_history: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    auto_run: bool = False

    @model_validator(mode="after")
    def _populate_workflow(self):
        if self.workflow is None:
            self.workflow = build_workflow_snapshot(
                profile=self.workflow_profile,
                definitions=self.workflow_definitions,
            )
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/unit/core/supervisor/test_context.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/supervisor/context.py backend/tests/unit/core/supervisor/test_context.py
git commit -m "feat(supervisor): move context to workflow snapshot model"
```

### Task 4: Add Agent Registry and Dynamic Tool Schema Tests

**Files:**
- Create: `backend/app/core/supervisor/registry.py`
- Create: `backend/tests/unit/core/supervisor/test_registry.py`
- Modify: `backend/app/core/supervisor/tools.py`

- [ ] **Step 1: Write the failing test**

```python
from app.core.supervisor.registry import RegisteredAgent, SupervisorAgentRegistry


def test_registry_returns_registered_agent_names():
    registry = SupervisorAgentRegistry(
        agents=[
            RegisteredAgent(name="outline_agent", label="Outline", description="Writes outlines", node_keys=["outline"]),
            RegisteredAgent(name="script_agent", label="Script", description="Writes scripts", node_keys=["script"]),
        ]
    )

    assert registry.agent_names() == ["outline_agent", "script_agent"]
```

```python
from app.core.supervisor.tools import get_supervisor_tool_schemas


def test_call_sub_agent_schema_uses_registry_names():
    schemas = get_supervisor_tool_schemas(["outline_agent", "script_agent"])
    call_sub_agent = next(schema for schema in schemas if schema["name"] == "call_sub_agent")

    assert call_sub_agent["parameters"]["properties"]["sub_agent_name"]["enum"] == [
        "outline_agent",
        "script_agent",
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/unit/core/supervisor/test_registry.py -v`
Expected: FAIL because registry module does not exist and `get_supervisor_tool_schemas()` does not accept names

- [ ] **Step 3: Write minimal implementation**

```python
class RegisteredAgent(BaseModel):
    name: str
    label: str
    description: str
    node_keys: list[str]
    tools: list[dict[str, Any]] = Field(default_factory=list)
    skill_names: list[str] = Field(default_factory=list)
    model: str = "gemini-3-flash-preview"


class SupervisorAgentRegistry(BaseModel):
    agents: list[RegisteredAgent] = Field(default_factory=list)

    def get(self, name: str) -> RegisteredAgent | None:
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None

    def agent_names(self) -> list[str]:
        return [agent.name for agent in self.agents]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/unit/core/supervisor/test_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/supervisor/registry.py backend/app/core/supervisor/tools.py backend/tests/unit/core/supervisor/test_registry.py
git commit -m "feat(supervisor): add pluggable agent registry"
```

### Task 5: Rebuild Supervisor Tools Around Workflow State

**Files:**
- Modify: `backend/app/core/supervisor/tools.py`
- Create: `backend/tests/unit/core/supervisor/test_tools.py`
- Test: `backend/tests/unit/core/supervisor/test_tools.py`

- [ ] **Step 1: Write the failing test**

```python
from app.core.supervisor.context import SupervisorContext
from app.core.supervisor.registry import RegisteredAgent, SupervisorAgentRegistry
from app.core.supervisor.tools import get_workflow_state
from app.core.supervisor.workflow import WorkflowNodeDefinition


async def test_get_workflow_state_returns_structured_snapshot():
    ctx = SupervisorContext(
        supervisor_session_id="sv-123",
        user_request="start",
        workflow_definitions=[
            WorkflowNodeDefinition(key="outline", label="Outline", node_type="text"),
        ],
    )

    payload = await get_workflow_state(supervisor_context=ctx)

    assert payload["workflow"]["profile"] == "default"
    assert payload["workflow"]["nodes"]["outline"]["status"] == "ready"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/unit/core/supervisor/test_tools.py -v`
Expected: FAIL because `get_workflow_state()` returns the old shape

- [ ] **Step 3: Write minimal implementation**

```python
async def get_workflow_state(
    supervisor_context: Optional[SupervisorContext] = None,
) -> Dict[str, Any]:
    if supervisor_context is None:
        return {"workflow": None}
    return {
        "workflow": supervisor_context.workflow.model_dump(),
        "sub_agent_sessions": dict(supervisor_context.sub_agent_sessions),
        "review_history": list(supervisor_context.review_history),
        "execution_history": list(supervisor_context.execution_history),
        "auto_run": supervisor_context.auto_run,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/unit/core/supervisor/test_tools.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/supervisor/tools.py backend/tests/unit/core/supervisor/test_tools.py
git commit -m "feat(supervisor): expose structured workflow state"
```

### Task 6: Rewrite SupervisorAgent on Top of the New Context

**Files:**
- Modify: `backend/app/core/supervisor/supervisor.py`
- Modify: `backend/app/core/supervisor/factory.py`
- Modify: `backend/app/core/supervisor/__init__.py`
- Test: `backend/tests/unit/core/supervisor/test_registry.py`

- [ ] **Step 1: Write the failing test**

```python
from app.core.supervisor.factory import create_supervisor


def test_create_supervisor_builds_default_registry_and_workflow():
    supervisor = create_supervisor(
        user_request="make a short video",
        persist=None,
    )

    assert supervisor.context.workflow is not None
    assert supervisor.registry.agent_names()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/unit/core/supervisor/test_registry.py -v`
Expected: FAIL because `SupervisorAgent` has no registry or workflow-aware context

- [ ] **Step 3: Write minimal implementation**

```python
class SupervisorAgent:
    def __init__(..., registry: SupervisorAgentRegistry, workflow_definitions: list[WorkflowNodeDefinition], ...):
        self.registry = registry
        self.context = SupervisorContext(
            supervisor_session_id=supervisor_session_id,
            user_request=user_request,
            workflow_profile="default",
            workflow_definitions=workflow_definitions,
            auto_run=auto_run,
        )
        self._agent = create_agent(
            agent_name="supervisor",
            session_id=supervisor_session_id,
            prompt=self._build_system_prompt(),
            tools=get_supervisor_tool_schemas(registry.agent_names()),
            max_loop=max_loop,
            persist=persist,
            middlewares=middlewares,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/unit/core/supervisor/test_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/supervisor/supervisor.py backend/app/core/supervisor/factory.py backend/app/core/supervisor/__init__.py backend/tests/unit/core/supervisor/test_registry.py
git commit -m "feat(supervisor): rebuild supervisor around workflow orchestrator"
```

### Task 7: Adapt API Integration Without Changing `create_agent`

**Files:**
- Modify: `backend/app/api/v1/endpoints/supervisor.py`
- Modify: `backend/app/services/supervisor_workflow_service.py`
- Test: `backend/tests/unit/core/supervisor/test_tools.py`

- [ ] **Step 1: Write the failing test**

```python
from app.core.supervisor.factory import create_supervisor


def test_supervisor_context_artifacts_expose_workflow_snapshot():
    supervisor = create_supervisor(user_request="hello", persist=None)

    assert "workflow" in supervisor.context.metadata or supervisor.context.workflow is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/unit/core/supervisor/test_tools.py -v`
Expected: FAIL because the API/service layer still expects old artifacts/current_phase-only state

- [ ] **Step 3: Write minimal implementation**

```python
# Persist the workflow snapshot into artifacts during stream/resume lifecycle
workflow_payload = supervisor.context.workflow.model_dump() if supervisor.context.workflow else {}
await service.append_artifacts(
    supervisor_session_id=supervisor.supervisor_session_id,
    stage="workflow",
    artifact=workflow_payload,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/unit/core/supervisor/test_tools.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/supervisor.py backend/app/services/supervisor_workflow_service.py backend/tests/unit/core/supervisor/test_tools.py
git commit -m "feat(supervisor): persist workflow snapshot through api integration"
```

### Task 8: Run Focused Verification

**Files:**
- Test: `backend/tests/unit/core/supervisor/test_workflow_graph.py`
- Test: `backend/tests/unit/core/supervisor/test_context.py`
- Test: `backend/tests/unit/core/supervisor/test_registry.py`
- Test: `backend/tests/unit/core/supervisor/test_tools.py`

- [ ] **Step 1: Run focused supervisor unit tests**

Run: `uv run pytest backend/tests/unit/core/supervisor/test_workflow_graph.py backend/tests/unit/core/supervisor/test_context.py backend/tests/unit/core/supervisor/test_registry.py backend/tests/unit/core/supervisor/test_tools.py -v`
Expected: PASS

- [ ] **Step 2: Run existing validation script**

Run: `python backend/validate_supervisor.py`
Expected: Script reports success for `create_supervisor`, tool schema registration, context wiring, and event objects

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-04-16-dynamic-supervisor-design.md docs/superpowers/plans/2026-04-16-dynamic-supervisor-orchestrator.md backend/app/core/supervisor backend/app/api/v1/endpoints/supervisor.py backend/app/services/supervisor_workflow_service.py backend/tests/unit/core/supervisor
git commit -m "feat(supervisor): add dynamic workflow orchestrator foundation"
```
