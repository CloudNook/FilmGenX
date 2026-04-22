# Supervisor Harness Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. It will decide whether each batch should run in parallel or serial subagent mode and will pass only task-local context to each subagent. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the current supervisor code in place so the harness, not the API layer, owns supervisor persistence and lifecycle, starting with extracting supervisor events out of `agent_messages`.

**Architecture:** The refactor proceeds in slices inside the existing `app.core.supervisor` and related backend modules. The first implementation slice introduces a dedicated `supervisor_events` persistence layer and rewires current history/event endpoints to use it. Later slices will move workflow lifecycle transitions and typed workflow state into the harness.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, Alembic, Pydantic, pytest

---

### Task 1: Extract Supervisor Events Into a Dedicated Persistence Layer

**Files:**
- Create: `backend/app/models/supervisor_event.py`
- Create: `backend/app/repositories/supervisor_event.py`
- Create: `backend/app/services/supervisor_event_service.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/repositories/__init__.py`
- Modify: `backend/app/services/__init__.py`
- Create: `backend/app/db/migrations/versions/x1y2z3a4b5c6_create_supervisor_events_table.py`
- Test: `backend/tests/unit/api/v1/endpoints/test_supervisor_endpoint.py`

- [ ] Write a failing test that proves supervisor resume/start/continue flows can persist and reload supervisor event history without using `AgentMessageRecord(role="event")`.
- [ ] Run the targeted endpoint tests and verify the new expectation fails.
- [ ] Add the `SupervisorEvent` ORM model with typed orchestration event fields and a JSON payload column for event-specific details.
- [ ] Add repository and service helpers for appending and listing supervisor events ordered by creation/id.
- [ ] Add the Alembic migration that creates `supervisor_events` with indexes on workflow/run/session lookups.
- [ ] Update module exports/imports so the new persistence layer can be used by endpoint code.
- [ ] Re-run the targeted endpoint tests and ensure they pass.

### Task 2: Rewire Current Supervisor Endpoint Event Storage

**Files:**
- Modify: `backend/app/api/v1/endpoints/supervisor.py`
- Test: `backend/tests/unit/api/v1/endpoints/test_supervisor_endpoint.py`

- [ ] Write a failing test that asserts `_append_supervisor_event` and workflow detail history reconstruction do not depend on `AgentMessageRecord(role="event")`.
- [ ] Run the targeted endpoint tests and verify the failure points at the old storage path.
- [ ] Replace direct `AgentMessageRecord(role="event")` writes/reads with the new supervisor event service while preserving existing SSE payload shape for the current frontend.
- [ ] Keep agent execution history reconstruction from `agent_messages` for `assistant/tool` messages, but delete the special-case event branch there.
- [ ] Re-run endpoint tests and confirm the event history still renders in the expected order.

### Task 3: Clean the Current Supervisor Event Contract Boundaries

**Files:**
- Modify: `backend/app/core/supervisor/events.py`
- Modify: `backend/app/core/supervisor/supervisor.py`
- Modify: `backend/app/core/supervisor/tools.py`
- Test: `backend/tests/unit/core/supervisor/test_events.py`
- Test: `backend/tests/unit/core/supervisor/test_tools.py`

- [ ] Write failing tests for the current supervisor event model boundaries that should be true after extraction: clear source/session semantics and no dependence on `agent_messages` for synthetic supervisor events.
- [ ] Run the focused supervisor unit tests and verify they fail for the intended reasons.
- [ ] Tighten event models and helper usage so supervisor-generated events remain framework-owned and sub-agent forwarded events remain execution-owned.
- [ ] Re-run the focused supervisor unit tests and confirm they pass.

### Task 4: Verify the First Refactor Slice

**Files:**
- Modify: `docs/superpowers/specs/2026-04-21-supervisor-harness-refactor-design.md`
- Modify: `docs/superpowers/plans/2026-04-21-supervisor-harness-refactor.md`

- [ ] Run: `uv run --project backend pytest backend/tests/unit/api/v1/endpoints/test_supervisor_endpoint.py backend/tests/unit/core/supervisor -v`
- [ ] Confirm all focused supervisor backend tests pass.
- [ ] Update the design/plan docs with any implementation discoveries from the first slice.
- [ ] Summarize the remaining slices needed to move workflow lifecycle ownership and typed workflow state into the harness.
