export interface WorkspaceSummary {
  id: number;
}

export interface WorkspaceMessageLike {
  role: string;
  content: string;
  seq: number;
  tool_call_id: string | null;
  tool_name: string | null;
  usage: Record<string, unknown> | null;
  extra_metadata: Record<string, unknown> | null;
  created_at: string | null;
}

export interface ToolCallDisplay {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: unknown;
  isError?: boolean;
  status: 'pending_review' | 'running' | 'completed' | 'interrupted' | 'error';
}

export interface DisplayGroup {
  id: string;
  type: 'user' | 'assistant' | 'thinking' | 'tool_calls';
  content: string;
  thinking?: string;
  toolCalls?: ToolCallDisplay[];
  seq: number;
  createdAt?: string | null;
}

interface PersistedToolCall {
  id: string;
  name: string;
  arguments?: Record<string, unknown>;
  result?: unknown;
  is_error?: boolean;
}

function parseMaybeJson(content: string): unknown {
  try {
    return JSON.parse(content);
  } catch {
    return content;
  }
}

function isInterruptedResult(result: unknown): boolean {
  return Boolean(
    result &&
      typeof result === 'object' &&
      'status' in result &&
      (result as { status?: unknown }).status === 'interrupted'
  );
}

function buildToolStatus(
  result: unknown,
  isError: boolean,
  hasResult: boolean,
): ToolCallDisplay['status'] {
  if (!hasResult) {
    return 'pending_review';
  }
  if (isInterruptedResult(result)) {
    return 'interrupted';
  }
  if (isError) {
    return 'error';
  }
  return 'completed';
}

function toToolCallDisplay(
  toolCall: PersistedToolCall,
  toolMessage?: WorkspaceMessageLike,
): ToolCallDisplay {
  const toolMessageResult = toolMessage ? parseMaybeJson(toolMessage.content) : undefined;
  const result = toolCall.result !== undefined ? toolCall.result : toolMessageResult;
  const isError = Boolean(
    toolCall.is_error ??
      (toolMessage?.extra_metadata as { is_error?: boolean } | null)?.is_error
  );

  return {
    id: toolCall.id,
    name: toolCall.name,
    arguments: toolCall.arguments || {},
    result,
    isError,
    status: buildToolStatus(result, isError, result !== undefined),
  };
}

function buildStandaloneToolDisplay(message: WorkspaceMessageLike): ToolCallDisplay {
  const result = parseMaybeJson(message.content);
  const isError = Boolean(
    (message.extra_metadata as { is_error?: boolean } | null)?.is_error
  );

  return {
    id: message.tool_call_id || `tool-${message.seq}`,
    name: message.tool_name || 'unknown',
    arguments: {},
    result,
    isError,
    status: buildToolStatus(result, isError, true),
  };
}

export function resolveInitialWorkspaceId(
  workspaces: WorkspaceSummary[],
  previousSelectedId: number | null,
): number | null {
  if (
    previousSelectedId != null &&
    workspaces.some((workspace) => workspace.id === previousSelectedId)
  ) {
    return previousSelectedId;
  }
  return workspaces[0]?.id ?? null;
}

export function groupWorkspaceMessages(
  messages: WorkspaceMessageLike[],
): DisplayGroup[] {
  const groups: DisplayGroup[] = [];
  let i = 0;

  while (i < messages.length) {
    const message = messages[i];

    if (message.role === 'user') {
      groups.push({
        id: `msg-${message.seq}`,
        type: 'user',
        content: message.content,
        seq: message.seq,
        createdAt: message.created_at,
      });
      i += 1;
      continue;
    }

    if (message.role === 'assistant') {
      const metadata = message.extra_metadata || {};
      const thinking = metadata.thinking;
      const toolCallsMeta = Array.isArray(metadata.tool_calls)
        ? (metadata.tool_calls as PersistedToolCall[])
        : [];

      if (typeof thinking === 'string' && thinking) {
        groups.push({
          id: `thinking-${message.seq}`,
          type: 'thinking',
          content: '',
          thinking,
          seq: message.seq,
        });
      }

      if (toolCallsMeta.length > 0) {
        let j = i + 1;
        const followingToolMessages: Record<string, WorkspaceMessageLike> = {};
        while (j < messages.length && messages[j].role === 'tool') {
          const toolMessage = messages[j];
          if (toolMessage.tool_call_id) {
            followingToolMessages[toolMessage.tool_call_id] = toolMessage;
          }
          j += 1;
        }

        groups.push({
          id: `tools-${message.seq}`,
          type: 'tool_calls',
          content: '',
          toolCalls: toolCallsMeta.map((toolCall) =>
            toToolCallDisplay(toolCall, followingToolMessages[toolCall.id])
          ),
          seq: message.seq,
        });
        i = j;
      } else {
        const standaloneTools: ToolCallDisplay[] = [];
        let j = i + 1;
        while (j < messages.length && messages[j].role === 'tool') {
          standaloneTools.push(buildStandaloneToolDisplay(messages[j]));
          j += 1;
        }

        if (standaloneTools.length > 0) {
          groups.push({
            id: `tools-${message.seq}`,
            type: 'tool_calls',
            content: '',
            toolCalls: standaloneTools,
            seq: message.seq,
          });
        }
        i = j;
      }

      if (message.content) {
        groups.push({
          id: `assistant-${message.seq}`,
          type: 'assistant',
          content: message.content,
          seq: message.seq,
          createdAt: message.created_at,
        });
      }
      continue;
    }

    if (message.role === 'tool') {
      groups.push({
        id: `tool-standalone-${message.seq}`,
        type: 'tool_calls',
        content: '',
        toolCalls: [buildStandaloneToolDisplay(message)],
        seq: message.seq,
      });
    }

    i += 1;
  }

  return groups;
}
