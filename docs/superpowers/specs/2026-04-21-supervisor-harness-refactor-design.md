# Supervisor Harness In-Place Refactor Design

**Date:** 2026-04-21
**Status:** Approved for implementation

## Goal

Refactor the current `backend/app/core/supervisor` implementation in place so that the supervisor becomes a framework-owned harness instead of a business-managed orchestration wrapper. The refactor will keep the existing module namespace, but it will replace the current ad hoc workflow snapshot/event persistence with typed runtime models and framework-managed lifecycle boundaries.

## Problems in the Current Design

1. `supervisor_workflows` mixes workflow identity, run lifecycle, derived statistics, and JSON snapshots into a single table.
2. Supervisor lifecycle is owned by API endpoints instead of the supervisor harness.
3. Supervisor timeline events are written into `agent_messages` via `role="event"`, which mixes agent execution logs with product-level orchestration events.
4. `SupervisorContext` is partially typed and partially open-ended (`metadata`, `execution_history`, `sub_agent_sessions`), making extension risky.
5. Reviewer execution is split across prompt-only helpers and tool functions rather than modeled as a first-class capability.
6. Sub-agent extensibility depends on manually editing the registry and orchestration code instead of relying on a capability registration surface.

## Target Architecture

The refactor keeps the current package names but changes responsibilities:

- `app.core.supervisor`
  Owns runtime concepts and orchestration lifecycle.
- `app.models.supervisor_*`
  Own strong persistence models for workflow, run, event, task, review, and node state.
- `app.api.v1.endpoints.supervisor`
  Becomes a thin transport layer that delegates to a supervisor harness entrypoint.
- `app.core.agent`
  Continues to own low-level agent execution and `agent_messages`.

## Persistence Direction

### `agent_messages`

`agent_messages` remains the source of truth for low-level agent execution messages, tool calls, checkpoints, and resume state. It should not store supervisor product/timeline events.

### `supervisor_workflows`

The current `supervisor_workflows` table will be repurposed into a typed workflow aggregate. Over time it should stop carrying JSON snapshots and run-level summary fields. Workflow state will instead be represented by typed child tables (nodes, revisions, tasks, reviews, events).

### `supervisor_events`

Supervisor orchestration events will move into a dedicated table. This is the first refactor slice because it removes one of the dirtiest abstraction leaks without requiring a full lifecycle rewrite in the same change.

## Runtime Direction

The framework will eventually own these lifecycle transitions:

1. create supervisor workflow/run
2. append orchestration events
3. update workflow/node state
4. pause for human review
5. resume from checkpoint
6. complete/fail run

The API layer should only validate requests, authorize access, stream responses, and call the harness.

## Extensibility Direction

New sub-agents should be registered through a capability surface, not wired through endpoint logic. The current registry is the seed of that system, but it needs to grow into a stronger contract that can describe:

- owned node types
- default review policy
- allowed automatic execution
- produced artifact type
- runtime model/tools/skills

## Refactor Phases

### Phase 1

- Extract supervisor events out of `agent_messages`
- Add a dedicated `supervisor_events` model/repository/service
- Update current endpoint/history loaders to use it

### Phase 2

- Refactor current `supervisor_workflows` lifecycle ownership into the harness
- Move start/continue/resume/complete/fail transitions out of endpoint code

### Phase 3

- Replace JSON workflow snapshot persistence with typed workflow/node/run/task/review models
- Reduce `SupervisorContext` to typed runtime state only

### Phase 4

- Rebuild frontend supervisor pages and APIs around the new harness contract
- Remove dead compatibility code

## Non-Goals for the First Slice

- Full schema replacement for workflow nodes/tasks/reviews
- Full frontend rewrite in the same patch
- Replacing the low-level `Agent` runtime

## Success Criteria

1. Supervisor events are no longer stored in `agent_messages`.
2. Current supervisor APIs keep functioning while using the dedicated event store.
3. The codebase is structurally ready for subsequent lifecycle and schema refactors inside the existing `supervisor` modules.
