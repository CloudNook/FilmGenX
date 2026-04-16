export interface SupervisorRunSummary {
  id: number;
}

export interface SupervisorDisplayEntry {
  id: string;
  kind:
    | 'thinking'
    | 'text'
    | 'tool_start'
    | 'tool_end'
    | 'sub_agent_start'
    | 'sub_agent_end'
    | 'review_start'
    | 'review_end'
    | 'interrupt'
    | 'done'
    | 'error';
  source?: string;
  content?: string;
  subAgentName?: string;
  sessionId?: string;
  taskDescription?: string;
  result?: unknown;
  criteria?: string[];
  score?: number;
  passed?: boolean;
  feedback?: string;
  suggestions?: string[] | null;
  toolName?: string;
  finalResult?: string;
  toolCallId?: string;
  toolArguments?: Record<string, unknown>;
  isError?: boolean;
}

type AppendableEvent =
  | { type: 'thinking'; content: string; source?: string }
  | { type: 'text'; content: string; source?: string }
  | { type: 'tool_start'; tool_call_id: string; tool_name: string; arguments: Record<string, unknown>; source?: string }
  | { type: 'tool_end'; tool_call_id: string; tool_name: string; result: unknown; is_error: boolean; source?: string }
  | { type: 'sub_agent_start'; sub_agent_name: string; session_id: string; task_description: string; source?: string }
  | { type: 'sub_agent_end'; sub_agent_name: string; session_id: string; result: Record<string, unknown>; source?: string }
  | { type: 'review_start'; sub_agent_name: string; criteria: string[]; source?: string }
  | { type: 'review_end'; sub_agent_name: string; score: number; passed: boolean; feedback: string; suggestions?: string[] | null; source?: string }
  | { type: 'interrupt'; tool_name: string; source?: string }
  | { type: 'supervisor_done'; final_result: string; source?: string }
  | { type: 'error'; error: string; source?: string };

export function resolveInitialSupervisorRunId(
  runs: SupervisorRunSummary[],
  previousSelectedId: number | null,
): number | null {
  if (
    previousSelectedId != null &&
    runs.some((run) => run.id === previousSelectedId)
  ) {
    return previousSelectedId;
  }
  return runs[0]?.id ?? null;
}

export function appendSupervisorDisplayEvent(
  entries: SupervisorDisplayEntry[],
  event: AppendableEvent,
): SupervisorDisplayEntry[] {
  if (event.type === 'thinking' || event.type === 'text') {
    const kind = event.type;
    const last = entries[entries.length - 1];
    if (last && last.kind === kind && last.source === (event.source || 'supervisor')) {
      return [
        ...entries.slice(0, -1),
        {
          ...last,
          content: `${last.content || ''}${event.content}`,
        },
      ];
    }
    return [
      ...entries,
      {
        id: `${kind}-${entries.length}`,
        kind,
        source: event.source || 'supervisor',
        content: event.content,
      },
    ];
  }

  if (event.type === 'sub_agent_start') {
    return [
      ...entries,
      {
        id: `sub-agent-start-${event.session_id}`,
        kind: 'sub_agent_start',
        source: event.source || 'supervisor',
        subAgentName: event.sub_agent_name,
        sessionId: event.session_id,
        taskDescription: event.task_description,
      },
    ];
  }

  if (event.type === 'tool_start') {
    return [
      ...entries,
      {
        id: `tool-start-${event.tool_call_id}`,
        kind: 'tool_start',
        source: event.source || 'supervisor',
        toolCallId: event.tool_call_id,
        toolName: event.tool_name,
        toolArguments: event.arguments,
      },
    ];
  }

  if (event.type === 'tool_end') {
    return [
      ...entries,
      {
        id: `tool-end-${event.tool_call_id}`,
        kind: 'tool_end',
        source: event.source || 'supervisor',
        toolCallId: event.tool_call_id,
        toolName: event.tool_name,
        result: event.result,
        isError: event.is_error,
      },
    ];
  }

  if (event.type === 'sub_agent_end') {
    return [
      ...entries,
      {
        id: `sub-agent-end-${event.session_id}`,
        kind: 'sub_agent_end',
        source: event.source || 'supervisor',
        subAgentName: event.sub_agent_name,
        sessionId: event.session_id,
        result: event.result,
      },
    ];
  }

  if (event.type === 'review_start') {
    return [
      ...entries,
      {
        id: `review-start-${event.sub_agent_name}-${entries.length}`,
        kind: 'review_start',
        source: event.source || 'supervisor',
        subAgentName: event.sub_agent_name,
        criteria: event.criteria,
      },
    ];
  }

  if (event.type === 'review_end') {
    return [
      ...entries,
      {
        id: `review-end-${event.sub_agent_name}-${entries.length}`,
        kind: 'review_end',
        source: event.source || 'supervisor',
        subAgentName: event.sub_agent_name,
        score: event.score,
        passed: event.passed,
        feedback: event.feedback,
        suggestions: event.suggestions,
      },
    ];
  }

  if (event.type === 'interrupt') {
    return [
      ...entries,
      {
        id: `interrupt-${entries.length}`,
        kind: 'interrupt',
        source: event.source || 'supervisor',
        toolName: event.tool_name,
      },
    ];
  }

  if (event.type === 'supervisor_done') {
    return [
      ...entries,
      {
        id: `done-${entries.length}`,
        kind: 'done',
        source: event.source || 'supervisor',
        finalResult: event.final_result,
      },
    ];
  }

  return [
    ...entries,
    {
      id: `error-${entries.length}`,
      kind: 'error',
      source: event.source || 'supervisor',
      content: event.error,
    },
  ];
}

export interface WorkflowNodeSummary {
  key: string;
  label: string;
  status: string;
  version: number;
  lastAgent: string | null;
  updatedAt: string | null;
  outputPreview: string | null;
}

export function buildWorkflowNodeSummaries(
  workflowSnapshot: Record<string, unknown> | null | undefined,
): WorkflowNodeSummary[] {
  const nodes =
    workflowSnapshot && typeof workflowSnapshot === 'object'
      ? workflowSnapshot['nodes']
      : null;

  if (!nodes || typeof nodes !== 'object') {
    return [];
  }

  return Object.entries(nodes).map(([key, value]) => {
    const node = (value || {}) as Record<string, unknown>;
    const data =
      node.data && typeof node.data === 'object'
        ? (node.data as Record<string, unknown>)
        : {};
    const rawOutput = data.output;
    const outputPreview =
      typeof rawOutput === 'string'
        ? rawOutput.slice(0, 160)
        : rawOutput != null
          ? JSON.stringify(rawOutput).slice(0, 160)
          : null;

    return {
      key,
      label: String(node.label || key),
      status: String(node.status || 'unknown'),
      version: Number(node.version || 0),
      lastAgent:
        node.last_agent != null ? String(node.last_agent) : null,
      updatedAt:
        node.updated_at != null ? String(node.updated_at) : null,
      outputPreview,
    };
  });
}
