# Supervisor Workspace UI Design

## Goal

Add a dedicated project-level Supervisor workspace page that mirrors the existing AI workspace layout while talking to the new dynamic Supervisor endpoints instead of the legacy workspace chat endpoints.

## Current Problem

The existing page at `frontend/app/(main)/projects/[projectId]/workspace/page.tsx` is wired to `workspacesApi.chat(...)`, which uses the old persisted agent-message flow. The new Supervisor runtime is exposed separately at `/api/v1/supervisor/stream`, `/{session_id}/state`, and `/{session_id}/resume`, and its event model includes `sub_agent_start`, `sub_agent_end`, `review_*`, and `supervisor_done`.

That means the current workspace UI cannot trigger or visualize `call_sub_agent`, even though the backend Supervisor can emit those events.

## Recommended Approach

Create a new dedicated page, not a dual-mode retrofit of the existing workspace page.

### Why

- The old workspace and new Supervisor use different APIs and persistence models.
- The old page expects persisted chat messages; the new Supervisor persists workflow snapshots and run metadata.
- Mixing both in one page would create a brittle state model and make HITL handling harder.

## User Experience

The new page should:

- Reuse the existing split layout and chat-like interaction style.
- Show a left sidebar of Supervisor runs for the current project.
- Let the user start a new Supervisor run from a single composer input.
- Stream Supervisor events live, including `thinking`, `text`, `sub_agent_start`, `sub_agent_end`, `review_*`, `interrupt`, and `supervisor_done`.
- Show the latest persisted workflow snapshot and final result for a selected run.
- Allow HITL resume from the selected run when the run is paused for review.

## Backend Changes

### 1. Add run list/detail endpoints

Add read-only endpoints under the Supervisor router for:

- listing runs by project
- fetching one run by project and run id

These endpoints should expose:

- summary metadata for the sidebar
- workflow snapshot
- final result
- active node key
- auto-run / workflow profile
- waiting-review state

### 2. Emit a `supervisor_started` SSE event

The frontend needs the run id and session id immediately after starting a stream so it can create/select the sidebar entry and poll or resume later if needed.

The stream should therefore emit an initial event with:

- `workflow_id`
- `supervisor_session_id`
- `status`
- `workflow_profile`
- `auto_run`

before other streamed content.

### 3. Keep existing Supervisor runtime behavior

Do not change the `create_agent` core loop. Keep `call_sub_agent` orchestration inside the Supervisor runtime exactly as it works today; this work is about exposing and visualizing it through the UI and run metadata endpoints.

## Frontend Changes

### New route

Add a dedicated page such as:

- `frontend/app/(main)/projects/[projectId]/supervisor/page.tsx`

### API client

Add a new `supervisorApi` section in `frontend/lib/api.ts` for:

- list runs
- get run detail
- start stream
- get interrupt state
- resume run
- read Supervisor SSE events

### Display model

Create a small display helper for Supervisor events and run details so the page can render:

- live event timeline
- sub-agent execution cards
- workflow snapshot summary
- final result

without duplicating parsing logic inside the page component.

## Testing

Use backend unit tests first to lock down:

- the new `supervisor_started` event
- the new list/detail endpoint contract

Frontend verification will rely on `next build` because this repo currently has no frontend test harness.

## Scope Limits

This work does not add:

- persisted Supervisor event transcript storage
- a generic workflow graph editor
- dynamic registry management UI

It only makes the current dynamic Supervisor usable from the product UI and debuggable end-to-end.
