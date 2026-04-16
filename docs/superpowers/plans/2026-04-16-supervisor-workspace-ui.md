# Supervisor Workspace UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. It will decide whether each batch should run in parallel or serial subagent mode and will pass only task-local context to each subagent. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated Supervisor workspace page that can start Supervisor runs, render `call_sub_agent` activity live, and inspect persisted workflow runs.

**Architecture:** Extend the Supervisor backend with run list/detail endpoints and an initial `supervisor_started` SSE event, then build a new frontend page and API client modeled on the existing workspace layout. Keep the Supervisor runtime and `create_agent` core intact.

**Tech Stack:** FastAPI, Pydantic, Next.js App Router, React, TypeScript, existing FilmGenX UI components

---

### Task 1: Lock down the backend contract with failing tests

**Files:**
- Modify: `backend/tests/unit/api/v1/endpoints/test_supervisor_endpoint.py`
- Modify: `backend/app/api/v1/endpoints/supervisor.py`

- [ ] **Step 1: Write failing tests for a started event and run endpoints**

Add tests that expect:
- `start_supervisor_pipeline()` to emit an initial `supervisor_started` event containing workflow id and session id
- new run list/detail endpoints to return Supervisor workflow metadata

- [ ] **Step 2: Run the focused test file to verify it fails**

Run: `uv run --project backend pytest backend/tests/unit/api/v1/endpoints/test_supervisor_endpoint.py -v`
Expected: FAIL because the started event and endpoints do not exist yet

- [ ] **Step 3: Implement the minimal backend endpoint changes**

Add:
- summary/detail response models
- list/get endpoints
- initial started event emission

- [ ] **Step 4: Run the focused backend test file again**

Run: `uv run --project backend pytest backend/tests/unit/api/v1/endpoints/test_supervisor_endpoint.py -v`
Expected: PASS

### Task 2: Add frontend Supervisor API support

**Files:**
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Add a small failing integration target by relying on missing types/usages in the new page**

The new page will require:
- `supervisorApi`
- `SupervisorSSEEvent`
- `readSupervisorSSEStream`
- run summary/detail response types

- [ ] **Step 2: Implement the minimal frontend API client**

Add API methods for:
- `list`
- `get`
- `start`
- `state`
- `resume`
- `readSupervisorSSEStream`

- [ ] **Step 3: Build the frontend to surface missing references**

Run: `npm run build`
Expected: FAIL until the page and route are wired correctly

### Task 3: Build the new Supervisor page

**Files:**
- Create: `frontend/app/(main)/projects/[projectId]/supervisor/page.tsx`
- Create: `frontend/lib/supervisor-display.ts`
- Modify: `frontend/components/layout/sidebar.tsx`

- [ ] **Step 1: Add the new page using the existing workspace layout as the reference**

Implement:
- sidebar run list
- main transcript area
- workflow summary panel
- bottom composer

- [ ] **Step 2: Render live Supervisor events**

Handle:
- `thinking`
- `text`
- `sub_agent_start`
- `sub_agent_end`
- `review_start`
- `review_end`
- `interrupt`
- `supervisor_done`
- `error`

- [ ] **Step 3: Add sidebar navigation entry**

Expose the page from the project sidebar so it is reachable in the app.

- [ ] **Step 4: Run the frontend build again**

Run: `npm run build`
Expected: PASS

### Task 4: Verify end-to-end behavior

**Files:**
- Modify as needed: `backend/app/api/v1/endpoints/supervisor.py`
- Modify as needed: `frontend/app/(main)/projects/[projectId]/supervisor/page.tsx`

- [ ] **Step 1: Run the focused backend tests**

Run: `uv run --project backend pytest backend/tests/unit/api/v1/endpoints/test_supervisor_endpoint.py backend/tests/unit/core/supervisor/test_tools.py backend/tests/unit/core/supervisor/test_factory.py -v`
Expected: PASS

- [ ] **Step 2: Run backend validation**

Run: `uv run --project backend python backend/validate_supervisor.py`
Expected: PASS aside from the known external Gemini region limitation

- [ ] **Step 3: Run the frontend production build**

Run: `npm run build`
Expected: PASS
