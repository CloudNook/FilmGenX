# Workspace Tool Call Flattening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. It will decide whether each batch should run in parallel or serial subagent mode and will pass only task-local context to each subagent. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the extra "工具调用" accordion level from the workspace page so each tool name is shown directly and can be expanded on its own.

**Architecture:** Keep the existing workspace API and message grouping unchanged. Limit the change to the workspace page presentation layer by rendering each tool call as a first-class collapsible item for both persisted message groups and streaming tool-call state.

**Tech Stack:** Next.js App Router, React 19, TypeScript, Radix `Collapsible`, ESLint

---

### Task 1: Flatten persisted tool-call rendering

**Files:**
- Modify: `frontend/app/(main)/projects/[projectId]/workspace/page.tsx`
- Test: `frontend/app/(main)/projects/[projectId]/workspace/page.tsx`

- [ ] **Step 1: Update the `tool_calls` branch in `MessageGroup`**

```tsx
if (group.type === 'tool_calls') {
  return (
    <div className="flex gap-4">
      <Avatar className="h-8 w-8 shrink-0">
        <AvatarFallback className="bg-primary/10 text-primary">
          <Wrench className="h-4 w-4" />
        </AvatarFallback>
      </Avatar>
      <div className="max-w-[80%] space-y-1.5">
        {group.toolCalls?.map((tc) => (
          <ToolCallDisclosure key={tc.id} toolCall={tc} />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Keep arguments/result rendering inside each tool item**

```tsx
{tc.arguments && Object.keys(tc.arguments).length > 0 && (
  <div>
    <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">参数</p>
    <pre className="text-muted-foreground bg-background/60 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
      {JSON.stringify(tc.arguments, null, 2)}
    </pre>
  </div>
)}
```

### Task 2: Reuse the same flattened presentation for streaming state

**Files:**
- Modify: `frontend/app/(main)/projects/[projectId]/workspace/page.tsx`
- Test: `frontend/app/(main)/projects/[projectId]/workspace/page.tsx`

- [ ] **Step 1: Introduce a small shared tool-call disclosure component**

```tsx
function ToolCallDisclosure({
  toolCall,
}: {
  toolCall: ToolCallDisplay;
}) {
  return (
    <Collapsible defaultOpen={false}>
      <div className="rounded-lg px-3 py-2 bg-primary/5 border border-primary/10 text-xs">
        <CollapsibleTrigger asChild>
          <button className="flex items-center gap-1.5 w-full text-left">
            <ChevronRight className="h-3 w-3 text-primary shrink-0 transition-transform [[data-state=open]>&]:rotate-90" />
            <span className="font-medium text-foreground">{toolCall.name}</span>
          </button>
        </CollapsibleTrigger>
      </div>
    </Collapsible>
  );
}
```

- [ ] **Step 2: Replace the streaming tool-call mapping with the shared component**

```tsx
<div className="max-w-[80%] space-y-1.5">
  {streaming.toolCalls.map((tc) => (
    <ToolCallDisclosure key={tc.id} toolCall={tc} />
  ))}
</div>
```

### Task 3: Validate the UI change with available tooling

**Files:**
- Modify: `frontend/app/(main)/projects/[projectId]/workspace/page.tsx`
- Test: `frontend/package.json`

- [ ] **Step 1: Run frontend lint**

```bash
cd frontend && npm run lint
```

Expected: lint completes without new errors from `workspace/page.tsx`.

- [ ] **Step 2: Review the diff to confirm the removed layer**

```bash
git diff -- frontend/app/\(main\)/projects/[projectId]/workspace/page.tsx docs/superpowers/plans/2026-04-12-workspace-tool-call-flattening.md
```

Expected: the outer "工具调用" collapsible is removed, while each tool item remains expandable.
