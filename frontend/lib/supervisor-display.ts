export interface SupervisorRunSummary {
  id: number;
}

export interface SupervisorDisplayEntry {
  id: string;
  kind:
    | 'user'
    | 'decision'
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
  decisionAction?: 'approve' | 'reject';
  finalResult?: string;
  toolCallId?: string;
  toolArguments?: Record<string, unknown>;
  isError?: boolean;
  pendingApproval?: boolean;
  isComplete?: boolean;
  timestamp?: string | null;
}

export interface SupervisorSessionGroup {
  sessionId: string;
  source: string;
  title: string;
  entries: SupervisorDisplayEntry[];
}

type AppendableEvent =
  | {
      type: 'supervisor_started';
      workflow_id: number;
      supervisor_session_id: string;
      status: string;
      workflow_profile: string;
      auto_run: boolean;
    }
  | { type: 'user_message'; content: string; timestamp?: string | null }
  | { type: 'thinking'; content: string; source?: string; session_id?: string }
  | { type: 'text'; content: string; source?: string; session_id?: string }
  | {
      type: 'tool_start';
      tool_call_id: string;
      tool_name: string;
      arguments: Record<string, unknown>;
      source?: string;
      session_id?: string;
    }
  | {
      type: 'tool_end';
      tool_call_id: string;
      tool_name: string;
      result: unknown;
      is_error: boolean;
      source?: string;
      session_id?: string;
    }
  | {
      type: 'sub_agent_start';
      sub_agent_name: string;
      session_id: string;
      task_description: string;
      source?: string;
    }
  | {
      type: 'sub_agent_end';
      sub_agent_name: string;
      session_id: string;
      result: Record<string, unknown>;
      source?: string;
    }
  | { type: 'review_start'; sub_agent_name: string; criteria: string[]; source?: string }
  | {
      type: 'review_end';
      sub_agent_name: string;
      score: number;
      passed: boolean;
      feedback: string;
      suggestions?: string[] | null;
      source?: string;
    }
  | {
      type: 'interrupt';
      tool_name: string;
      tool_call_id?: string;
      session_id?: string;
      source?: string;
    }
  | { type: 'supervisor_done'; final_result: string; source?: string }
  | {
      type: 'done';
      usage: Record<string, unknown> | null;
      loop_count: number;
      finished: boolean;
      source?: string;
      session_id?: string;
    }
  | {
      type: 'usage';
      usage: Record<string, unknown>;
      accumulated_usage?: Record<string, unknown> | null;
      loop_count: number;
      source?: string;
      session_id?: string;
    }
  | { type: 'error'; error: string; source?: string; session_id?: string };

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
  const findMatchingToolIndex = (
    currentEntries: SupervisorDisplayEntry[],
    toolCallId?: string,
    sessionId?: string,
  ): number => {
    if (!toolCallId) {
      return -1;
    }

    return currentEntries.findLastIndex(
      (entry) =>
        entry.toolCallId === toolCallId &&
        (entry.kind === 'tool_start' || entry.kind === 'tool_end') &&
        (
          entry.sessionId === sessionId ||
          entry.sessionId == null ||
          sessionId == null
        ),
    );
  };

  const completeLatestThinking = (
    currentEntries: SupervisorDisplayEntry[],
    source?: string,
    sessionId?: string,
  ): SupervisorDisplayEntry[] => {
    const targetSource = source || 'supervisor';
    const index = currentEntries.findLastIndex(
      (entry) =>
        entry.kind === 'thinking' &&
        !entry.isComplete &&
        (entry.source || 'supervisor') === targetSource &&
        entry.sessionId === sessionId,
    );

    if (index === -1) {
      return currentEntries;
    }

    return [
      ...currentEntries.slice(0, index),
      {
        ...currentEntries[index],
        isComplete: true,
      },
      ...currentEntries.slice(index + 1),
    ];
  };

  if (event.type === 'supervisor_started') {
    return entries;
  }

  if (event.type === 'user_message') {
    return [
      ...entries,
      buildSupervisorUserEntry(event.content, {
        timestamp: event.timestamp || null,
      }),
    ];
  }

  if (event.type === 'thinking' || event.type === 'text') {
    const kind = event.type;
    const source = event.source || 'supervisor';
    const baseEntries =
      event.type === 'text'
        ? completeLatestThinking(entries, source, event.session_id)
        : entries;
    const last = baseEntries[baseEntries.length - 1];
    if (
      last &&
      last.kind === kind &&
      last.source === source &&
      last.sessionId === event.session_id
    ) {
      return [
        ...baseEntries.slice(0, -1),
        {
          ...last,
          content: `${last.content || ''}${event.content}`,
        },
      ];
    }

    return [
      ...baseEntries,
      {
        id: `${kind}-${source}-${event.session_id || 'root'}-${baseEntries.length}`,
        kind,
        source,
        sessionId: event.session_id,
        content: event.content,
        isComplete: kind === 'text',
      },
    ];
  }

  if (event.type === 'sub_agent_start') {
    const nextEntries = completeLatestThinking(entries, event.source, event.session_id);
    // Supervisor 反复 call 同一个 sub-agent 时 session_id 会复用（agent loop 才能
    // 自动加载历史对话）。前端用"该 session 已发生的 start/end 事件总数"作 turn 序号，
    // 让每一轮的 start/end 卡片有唯一 React key。end 事件到达时会保留这个 id 把 start
    // 原地改写成 end，所以一轮始终是一张卡片。
    const turnIndex = nextEntries.filter(
      (e) =>
        (e.kind === 'sub_agent_start' || e.kind === 'sub_agent_end') &&
        e.sessionId === event.session_id,
    ).length;
    return [
      ...nextEntries,
      {
        id: `sub-agent-${event.session_id}-${turnIndex}`,
        kind: 'sub_agent_start',
        source: event.source || 'supervisor',
        subAgentName: event.sub_agent_name,
        sessionId: event.session_id,
        taskDescription: event.task_description,
      },
    ];
  }

  if (event.type === 'tool_start') {
    const nextEntries = completeLatestThinking(entries, event.source, event.session_id);
    // 历史上有 provider（早期 Gemini 适配器）用 Python id() 当 tool_call_id，
    // 不同轮次的 function_call 对象内存地址会被回收复用，导致 persisted event_history
    // 里出现重复 tool_call_id。这里用 nextEntries.length 当 React-key 后缀做兜底，
    // 即便 tool_call_id 重复也保持每条 entry 的 React 身份唯一。配对仍走 toolCallId
    // 字段，不依赖这个 id 字符串。
    return [
      ...nextEntries,
      {
        id: `tool-start-${event.tool_call_id}-${event.session_id || 'root'}-${nextEntries.length}`,
        kind: 'tool_start',
        source: event.source || 'supervisor',
        sessionId: event.session_id,
        toolCallId: event.tool_call_id,
        toolName: event.tool_name,
        toolArguments: event.arguments,
        pendingApproval: false,
      },
    ];
  }

  if (event.type === 'tool_end') {
    const baseEntries = completeLatestThinking(entries, event.source, event.session_id);
    const existingIndex = findMatchingToolIndex(
      baseEntries,
      event.tool_call_id,
      event.session_id,
    );
    const nextEntry: SupervisorDisplayEntry = {
      // 仅在 orphan 分支（找不到匹配的 tool_start）使用；带 length 后缀避免与
      // 既有 entry 撞 key。命中匹配时下面会保留 existingEntry.id。
      id: `tool-end-${event.tool_call_id}-${event.session_id || 'root'}-${baseEntries.length}`,
      kind: 'tool_end',
      source: event.source || 'supervisor',
      sessionId: event.session_id,
      toolCallId: event.tool_call_id,
      toolName: event.tool_name,
      result: event.result,
      isError: event.is_error,
      pendingApproval: false,
    };

    if (existingIndex === -1) {
      return [...baseEntries, nextEntry];
    }

    const existingEntry = baseEntries[existingIndex];
    return [
      ...baseEntries.slice(0, existingIndex),
      {
        ...existingEntry,
        ...nextEntry,
        id: existingEntry.id,
        toolArguments: existingEntry.toolArguments,
      },
      ...baseEntries.slice(existingIndex + 1),
    ];
  }

  if (event.type === 'sub_agent_end') {
    const baseEntries = completeLatestThinking(entries, event.source, event.session_id);
    // 找该 session 最近一个还没"收尾"的 start，把它原地改写成 end ——同 session 多
    // 轮调用时，每一轮各自的 start 已经按 turn 序号编 id（见 sub_agent_start 分支），
    // 所以不会撞车。每一轮始终是 1 张卡片：先 loader（start），完成后变成可折叠的
    // 结果卡片（end），不会出现僵尸 loader。
    const existingIndex = baseEntries.findLastIndex(
      (entry) =>
        entry.sessionId === event.session_id &&
        entry.kind === 'sub_agent_start',
    );
    const matchingStart = existingIndex !== -1 ? baseEntries[existingIndex] : null;
    // Orphan end：framework 在 sub-agent 没真正启动就早期失败时（unknown agent /
    // workflow guard 等）emit 没 session_id 的 sub_agent_end。带 length 后缀保证
    // 同一会话出现多次此类失败时 React key 唯一。匹配逻辑走 sessionId + kind，
    // 不依赖此 id 字符串。
    const nextEntry: SupervisorDisplayEntry = {
      id:
        matchingStart?.id ||
        `sub-agent-${event.session_id || 'root'}-orphan-end-${baseEntries.length}`,
      kind: 'sub_agent_end',
      source: event.source || 'supervisor',
      subAgentName: event.sub_agent_name,
      sessionId: event.session_id,
      result: event.result,
      taskDescription: matchingStart?.taskDescription,
    };

    if (existingIndex === -1) {
      return [...baseEntries, nextEntry];
    }

    return [
      ...baseEntries.slice(0, existingIndex),
      { ...baseEntries[existingIndex], ...nextEntry },
      ...baseEntries.slice(existingIndex + 1),
    ];
  }

  if (event.type === 'review_start') {
    const nextEntries = completeLatestThinking(entries, event.source);
    return [
      ...nextEntries,
      {
        id: `review-start-${event.sub_agent_name}-${nextEntries.length}`,
        kind: 'review_start',
        source: event.source || 'supervisor',
        subAgentName: event.sub_agent_name,
        criteria: event.criteria,
      },
    ];
  }

  if (event.type === 'review_end') {
    const nextEntries = completeLatestThinking(entries, event.source);
    // 找到尚未合并的最近一条 review_start（同一个 sub-agent）就地升级为
    // review_end，保留 review_start 已有的 criteria；这样一轮 review 在 UI
    // 上就是一张卡片，而不是两张分别的"开始 / 结束"卡片。
    // 多轮修订（max_revision_rounds>1）每轮各自有 review_start / review_end，
    // findLast 仍然只升级最新那条未合并的，多轮卡片照样独立。
    const startIndex = nextEntries.findLastIndex(
      (entry) =>
        entry.kind === 'review_start' &&
        entry.subAgentName === event.sub_agent_name,
    );
    if (startIndex !== -1) {
      const startEntry = nextEntries[startIndex];
      return [
        ...nextEntries.slice(0, startIndex),
        {
          ...startEntry,
          kind: 'review_end',
          score: event.score,
          passed: event.passed,
          feedback: event.feedback,
          suggestions: event.suggestions,
        },
        ...nextEntries.slice(startIndex + 1),
      ];
    }
    // 兜底：缺 review_start（理论上不该发生）→ 单独生成一张 review_end
    return [
      ...nextEntries,
      {
        id: `review-end-${event.sub_agent_name}-${nextEntries.length}`,
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
    const nextEntries = completeLatestThinking(entries, event.source, event.session_id);
    const existingToolIndex = findMatchingToolIndex(
      nextEntries,
      event.tool_call_id,
      event.session_id,
    );
    const entriesWithPendingTool =
      existingToolIndex === -1
        ? nextEntries
        : [
            ...nextEntries.slice(0, existingToolIndex),
            {
              ...nextEntries[existingToolIndex],
              pendingApproval: true,
            },
            ...nextEntries.slice(existingToolIndex + 1),
          ];
    return [
      ...entriesWithPendingTool,
      {
        id: `interrupt-${entriesWithPendingTool.length}`,
        kind: 'interrupt',
        source: event.source || 'supervisor',
        sessionId: event.session_id,
        toolCallId: event.tool_call_id,
        toolName: event.tool_name,
      },
    ];
  }

  if (event.type === 'supervisor_done') {
    return completeLatestThinking(entries, event.source);
  }

  // 'done' / 'usage' 都只承载 token 计费数据，timeline 不展示
  if (event.type === 'done' || event.type === 'usage') {
    return entries;
  }

  const nextEntries = completeLatestThinking(entries, event.source, event.session_id);
  return [
    ...nextEntries,
    {
      id: `error-${event.session_id || 'root'}-${nextEntries.length}`,
      kind: 'error',
      source: event.source || 'supervisor',
      sessionId: event.session_id,
      content: event.error,
    },
  ];
}

export function buildSupervisorUserEntry(
  content: string,
  options?: {
    id?: string;
    timestamp?: string | null;
  },
): SupervisorDisplayEntry {
  return {
    id:
      options?.id ||
      `user-${options?.timestamp || Date.now().toString()}`,
    kind: 'user',
    content,
    timestamp: options?.timestamp || null,
  };
}

export function buildSupervisorDecisionEntry(
  action: 'approve' | 'reject',
  options?: {
    id?: string;
    toolName?: string | null;
    timestamp?: string | null;
  },
): SupervisorDisplayEntry {
  return {
    id:
      options?.id ||
      `decision-${action}-${options?.timestamp || Date.now().toString()}`,
    kind: 'decision',
    decisionAction: action,
    toolName: options?.toolName || null,
    timestamp: options?.timestamp || null,
  };
}

export function buildSupervisorDisplayEntries(
  events: AppendableEvent[],
): SupervisorDisplayEntry[] {
  return events.reduce<SupervisorDisplayEntry[]>(
    (entries, event) => appendSupervisorDisplayEvent(entries, event),
    [],
  );
}

export function splitSupervisorDisplayEntries(entries: SupervisorDisplayEntry[]): {
  mainEntries: SupervisorDisplayEntry[];
  sessionGroups: SupervisorSessionGroup[];
} {
  const mainEntries: SupervisorDisplayEntry[] = [];
  const sessionGroups: SupervisorSessionGroup[] = [];
  const sessionGroupMap = new Map<string, SupervisorSessionGroup>();

  for (const entry of entries) {
    if (!entry.sessionId?.startsWith('sub-')) {
      mainEntries.push(entry);
      continue;
    }

    const source = entry.source || 'sub-agent';
    const existing = sessionGroupMap.get(entry.sessionId);
    if (existing) {
      existing.entries.push(entry);
      if (!existing.title && entry.subAgentName) {
        existing.title = entry.subAgentName;
      }
      continue;
    }

    const group: SupervisorSessionGroup = {
      sessionId: entry.sessionId,
      source,
      title: entry.subAgentName || source,
      entries: [entry],
    };
    sessionGroupMap.set(entry.sessionId, group);
    sessionGroups.push(group);
  }

  return { mainEntries, sessionGroups };
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
    const artifact =
      node.artifact && typeof node.artifact === 'object'
        ? (node.artifact as Record<string, unknown>)
        : node.data && typeof node.data === 'object'
          ? (node.data as Record<string, unknown>)
          : {};
    const rawOutput = artifact.output;
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
