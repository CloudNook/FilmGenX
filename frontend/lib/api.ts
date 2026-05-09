/**
 * FilmGenX API 客户端。
 *
 * 统一封装 fetch 请求，自动附加 Authorization header。
 * 后端 base URL 从环境变量 NEXT_PUBLIC_API_URL 读取，默认 /api/v1。
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

function resolveStreamingBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }

  if (typeof window !== 'undefined') {
    const { protocol, hostname } = window.location;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return `${protocol}//${hostname}:8000/api/v1`;
    }
  }

  return BASE_URL;
}

function buildStreamingUrl(path: string): string {
  return `${resolveStreamingBaseUrl()}${path}`;
}

// ---------------------------------------------------------------------------
// Token 管理（localStorage）
// ---------------------------------------------------------------------------

const TOKEN_KEY = 'filmgenx_token';

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// ---------------------------------------------------------------------------
// 通用请求函数
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type BodyValue = Record<string, any> | undefined;

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: BodyValue;
  /** 是否跳过附加 Authorization header */
  noAuth?: boolean;
}

const inFlightGetRequests = new Map<string, Promise<unknown>>();

function buildGetRequestKey(
  path: string,
  headers: Record<string, string>,
): string {
  const normalizedHeaders = Object.entries(headers)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `${key}:${value}`)
    .join('|');
  return `GET:${BASE_URL}${path}:${normalizedHeaders}`;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, noAuth = false, headers: customHeaders, ...rest } = options;
  const method = (rest.method || 'GET').toUpperCase();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(customHeaders as Record<string, string>),
  };

  // 自动附加 Bearer token
  if (!noAuth) {
    const token = getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const executeRequest = async (): Promise<T> => {
    const res = await fetch(`${BASE_URL}${path}`, {
      ...rest,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    // 处理 401：token 过期 → 清除
    if (res.status === 401 && typeof window !== 'undefined') {
      removeToken();
      throw new Error('登录已过期，请重新登录');
    }

    if (!res.ok) {
      let detail = `请求失败 (${res.status})`;
      try {
        const errBody = await res.json();
        detail = errBody.detail || detail;
      } catch {
        // ignore
      }
      throw new Error(detail);
    }

    // 204 No Content
    if (res.status === 204) return undefined as T;

    return res.json();
  };

  // 开发环境下 React Strict Mode 可能导致同一 GET 在挂载阶段并发触发两次，这里复用同一 Promise。
  if (method === 'GET' && !body) {
    const key = buildGetRequestKey(path, headers);
    const existing = inFlightGetRequests.get(key);
    if (existing) {
      return existing as Promise<T>;
    }

    const promise = executeRequest().finally(() => {
      inFlightGetRequests.delete(key);
    });
    inFlightGetRequests.set(key, promise);
    return promise;
  }

  return executeRequest();
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
}

export const authApi = {
  register(email: string, username: string, password: string, inviteCode?: string) {
    return request<TokenResponse>('/auth/register', {
      method: 'POST',
      body: { email, username, password, invite_code: inviteCode || undefined },
      noAuth: true,
    });
  },

  login(email: string, password: string) {
    return request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: { email, password },
      noAuth: true,
    });
  },

  getMe() {
    return request<UserResponse>('/auth/me', { method: 'GET' });
  },

  updateMe(data: { username?: string; avatar_url?: string }) {
    return request<UserResponse>('/auth/me', {
      method: 'PATCH',
      body: data,
    });
  },

  uploadAvatar(file: File) {
    const formData = new FormData();
    formData.append('file', file);

    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    return fetch(`${BASE_URL}/auth/me/avatar`, {
      method: 'POST',
      headers,
      body: formData,
    }).then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '上传失败' }));
        throw new Error(err.detail || '上传失败');
      }
      return res.json() as Promise<UserResponse>;
    });
  },
};

// ---------------------------------------------------------------------------
// 通用分页响应
// ---------------------------------------------------------------------------

export interface PageResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// ---------------------------------------------------------------------------
// Projects API
// ---------------------------------------------------------------------------

export interface ProjectResponse {
  id: number;
  owner_id: number;
  name: string;
  description: string | null;
  novel_title: string;
  cover_image_url: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  novel_title: string;
  cover_image_url?: string;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  cover_image_url?: string;
  status?: 'active' | 'archived';
}

export const projectsApi = {
  list(page = 1, pageSize = 20) {
    return request<PageResponse<ProjectResponse>>(
      `/projects?page=${page}&page_size=${pageSize}`,
      { method: 'GET' },
    );
  },

  create(data: ProjectCreate) {
    return request<ProjectResponse>('/projects', {
      method: 'POST',
      body: data,
    });
  },

  get(projectId: number) {
    return request<ProjectResponse>(`/projects/${projectId}`, { method: 'GET' });
  },

  update(projectId: number, data: ProjectUpdate) {
    return request<ProjectResponse>(`/projects/${projectId}`, {
      method: 'PATCH',
      body: data,
    });
  },

  delete(projectId: number) {
    return request<void>(`/projects/${projectId}`, { method: 'DELETE' });
  },
};








// ---------------------------------------------------------------------------
// Assets API（项目级素材）
// ---------------------------------------------------------------------------

export interface AssetResponse {
  id: number;
  project_id: number;
  asset_code: string;
  asset_type: string;
  file_url: string;
  file_format: string | null;
  file_size_bytes: number | null;
  width: number | null;
  height: number | null;
  duration_sec: number | null;
  source: string;
  generator: string | null;
  tags: string[];
  description: string | null;
  created_at: string;
  updated_at: string;
}

export const assetsApi = {
  list(
    projectId: number,
    page = 1,
    pageSize = 20,
    filters?: {
      assetType?: string;
      source?: string;
    },
  ) {
    const safePageSize = Math.min(Math.max(pageSize, 1), 100);
    const params = new URLSearchParams({ page: String(page), page_size: String(safePageSize) });
    if (filters?.assetType) params.set('asset_type', filters.assetType);
    if (filters?.source) params.set('source', filters.source);
    return request<PageResponse<AssetResponse>>(
      `/projects/${projectId}/assets?${params}`,
      { method: 'GET' },
    );
  },

  stats(projectId: number) {
    return request<Record<string, number>>(
      `/projects/${projectId}/assets/stats`,
      { method: 'GET' },
    );
  },

  upload(projectId: number, file: File): Promise<AssetResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    return fetch(`${BASE_URL}/projects/${projectId}/assets/upload`, {
      method: 'POST',
      headers,
      body: formData,
    }).then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '上传失败' }));
        throw new Error(err.detail || '上传失败');
      }
      return res.json() as Promise<AssetResponse>;
    });
  },

  create(projectId: number, data: Record<string, unknown>) {
    return request<AssetResponse>(`/projects/${projectId}/assets`, {
      method: 'POST',
      body: data,
    });
  },

  get(projectId: number, assetId: number) {
    return request<AssetResponse>(
      `/projects/${projectId}/assets/${assetId}`,
      { method: 'GET' },
    );
  },

  delete(projectId: number, assetId: number) {
    return request<void>(
      `/projects/${projectId}/assets/${assetId}`,
      { method: 'DELETE' },
    );
  },
};



// ---------------------------------------------------------------------------
// Skills API
// ---------------------------------------------------------------------------

export interface SkillParseResult {
  fields: Record<string, unknown>;
  missing_fields: string[];
  warnings: { field: string; message: string }[];
  raw_markdown: string;
}

// Skill 模型遵循 Claude SKILL.md 三层渐进披露：
// - L1：name + description + target_agents + tags（启动注入 prompt）
// - L2：body（agent 调 load_skill 时获取）
// - L3：references[{key, title, body}]（agent 调 load_skill_reference 时获取）
export interface SkillReferenceItem {
  key: string;
  title: string;
  body: string;
}

export interface SkillResponse {
  id: number;
  created_at: string;
  updated_at: string;
  name: string;
  description: string;
  target_agents: string[];
  body: string | null;
  references: SkillReferenceItem[];
  tags: string[];
  author: string | null;
  raw_markdown: string | null;
  is_active: boolean;
  version: number;
  skill_metadata: Record<string, unknown>;
}

export interface SkillMetaResponse {
  name: string;
  description: string;
  target_agents: string[];
  tags: string[];
}

export interface SkillCreate {
  name: string;
  description: string;
  target_agents?: string[];
  body?: string;
  references?: SkillReferenceItem[];
  tags?: string[];
  author?: string;
  raw_markdown?: string;
  is_active?: boolean;
  metadata?: Record<string, unknown>;
}

export interface SkillUpdate {
  description?: string;
  target_agents?: string[];
  body?: string;
  references?: SkillReferenceItem[];
  tags?: string[];
  author?: string;
  raw_markdown?: string;
  is_active?: boolean;
  skill_metadata?: Record<string, unknown>;
}

export interface SkillUploadResponse {
  skill: SkillParseResult;
  existing: SkillResponse | null;
  is_update: boolean;
}

export interface LintIssue {
  level: 'error' | 'warning';
  code: string;
  message: string;
  field: string;
  token: string | null;
}

export interface SkillLintResponse {
  skill_name: string;
  issues: LintIssue[];
}

export const skillsApi = {
  /** 上传并解析 Markdown */
  upload(content: string) {
    return request<SkillUploadResponse>('/admin/skills/upload', {
      method: 'POST',
      body: { content },
    });
  },

  /** 仅解析 Markdown，不保存 */
  preview(content: string) {
    return request<SkillParseResult>('/admin/skills/preview', {
      method: 'POST',
      body: { content },
    });
  },

  list(page = 1, pageSize = 20, isActive?: boolean) {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (isActive !== undefined) params.set('is_active', String(isActive));
    return request<PageResponse<SkillResponse>>(
      `/admin/skills?${params}`,
      { method: 'GET' },
    );
  },

  /** L1 元信息列表，可按 target_agent 反查 */
  meta(targetAgent?: string) {
    const params = new URLSearchParams();
    if (targetAgent) params.set('target_agent', targetAgent);
    const qs = params.toString();
    return request<SkillMetaResponse[]>(
      `/admin/skills/meta${qs ? `?${qs}` : ''}`,
      { method: 'GET' },
    );
  },

  get(name: string) {
    return request<SkillResponse>(`/admin/skills/${name}`, { method: 'GET' });
  },

  /** L3：单个 reference 子文档 */
  getReference(name: string, refKey: string) {
    return request<SkillReferenceItem & { skill_name: string }>(
      `/admin/skills/${name}/reference/${refKey}`,
      { method: 'GET' },
    );
  },

  /** 引用 lint 检查 */
  lint(name: string) {
    return request<SkillLintResponse>(`/admin/skills/${name}/lint`, {
      method: 'GET',
    });
  },

  create(data: SkillCreate) {
    return request<SkillResponse>('/admin/skills', {
      method: 'POST',
      body: data,
    });
  },

  update(name: string, data: SkillUpdate) {
    return request<SkillResponse>(`/admin/skills/${name}`, {
      method: 'PUT',
      body: data,
    });
  },

  delete(name: string) {
    return request<void>(`/admin/skills/${name}`, { method: 'DELETE' });
  },

  downloadMarkdown(name: string) {
    return request<string>(`/admin/skills/${name}/markdown`, { method: 'GET' });
  },
};

// ---------------------------------------------------------------------------
// Agent 输出 schema（前端 SubAgentResultCard 渲染时用 title / description 做标签）
// ---------------------------------------------------------------------------

export const agentSchemasApi = {
  /**
   * 获取所有 sub-agent 的输出 schema。
   * 返回 ``{sub_agent_name: <JSON Schema>}`` 字典。
   */
  list() {
    return request<Record<string, Record<string, unknown>>>(
      '/agent-schemas',
      { method: 'GET' },
    );
  },
};

// ---------------------------------------------------------------------------
// SSE 辅助工具
// ---------------------------------------------------------------------------

/** 读取 SSE 流，逐 chunk 调用 onChunk，遇到 [DONE] 时调用 onDone */
export async function readSSEStream(
  response: Response,
  onChunk: (text: string) => void,
  onDone?: () => void,
) {
  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || !trimmed.startsWith('data: ')) continue;
      const data = trimmed.slice(6);
      if (data === '[DONE]') {
        onDone?.();
        return;
      }
      if (data.startsWith('[ERROR]')) {
        throw new Error(data.slice(8).trim());
      }
      onChunk(data);
    }
  }
}

// ---------------------------------------------------------------------------
// Workspaces API（AI 工作台）
// ---------------------------------------------------------------------------

export interface WorkspaceResponse {
  id: number;
  project_id: number;
  title: string;
  agent_name: string;
  session_id: string;
  system_prompt: string | null;
  status: string;
  total_tokens: number;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
  model: string;
  temperature: number;
  hitl_enabled: boolean;
  review_enabled: boolean;
  memory_enabled: boolean;
}

export interface AgentMessageExtraMetadata {
  thinking?: string | null;
  tool_calls?: {
    id: string;
    name: string;
    arguments: Record<string, unknown>;
    result?: unknown;
    is_error?: boolean;
  }[] | null;
  accumulated_usage?: {
    prompt_tokens?: number | null;
    completion_tokens?: number | null;
    thinking_tokens?: number | null;
    total_tokens?: number | null;
  } | null;
  [key: string]: unknown;
}

export interface AgentMessageResponse {
  role: string;
  content: string;
  seq: number;
  tool_call_id: string | null;
  tool_name: string | null;
  usage: { prompt_tokens?: number | null; completion_tokens?: number | null; thinking_tokens?: number | null; total_tokens?: number | null } | null;
  extra_metadata: AgentMessageExtraMetadata | null;
  created_at: string | null;
}

export interface PendingInterrupt {
  tool_name: string;
  tool_call_id: string;
  arguments: Record<string, unknown>;
  available_actions: string[];
  context: Record<string, unknown>;
}

export interface WorkspaceDetailResponse extends WorkspaceResponse {
  messages: AgentMessageResponse[];
  pending_interrupt: PendingInterrupt | null;
}

/** Agent SSE 事件类型 */
export type AgentSSEEvent =
  | { type: 'thinking'; content: string }
  | { type: 'text'; content: string }
  | { type: 'tool_start'; tool_call_id: string; tool_name: string; arguments: Record<string, unknown> }
  | { type: 'tool_end'; tool_call_id: string; tool_name: string; result: unknown; is_error: boolean }
  | { type: 'done'; usage: { prompt_tokens?: number | null; completion_tokens?: number | null; thinking_tokens?: number | null; total_tokens?: number | null } | null; loop_count: number; finished: boolean }
  | { type: 'error'; error: string }
  | { type: 'interrupt'; session_id: string; tool_name: string; tool_call_id: string; arguments: Record<string, unknown>; available_actions: string[]; context: Record<string, unknown> }
  | { type: 'review_start'; review_round: number; candidate_preview: string }
  | { type: 'review_end'; review_round: number; score: number; passed: boolean; feedback: string; suggestions: string[] };

export const workspacesApi = {
  list(projectId: number, page = 1, pageSize = 20) {
    return request<PageResponse<WorkspaceResponse>>(
      `/projects/${projectId}/workspaces?page=${page}&page_size=${pageSize}`,
      { method: 'GET' },
    );
  },

  create(projectId: number, data: { title?: string; system_prompt?: string } = {}) {
    return request<WorkspaceResponse>(
      `/projects/${projectId}/workspaces`,
      { method: 'POST', body: data },
    );
  },

  get(projectId: number, workspaceId: number) {
    return request<WorkspaceDetailResponse>(
      `/projects/${projectId}/workspaces/${workspaceId}`,
      { method: 'GET' },
    );
  },

  update(
    projectId: number,
    workspaceId: number,
    data: {
      title?: string;
      system_prompt?: string | null;
      status?: string;
      model?: string;
      temperature?: number;
      hitl_enabled?: boolean;
      review_enabled?: boolean;
      memory_enabled?: boolean;
    },
  ) {
    return request<WorkspaceResponse>(
      `/projects/${projectId}/workspaces/${workspaceId}`,
      { method: 'PATCH', body: data },
    );
  },

  delete(projectId: number, workspaceId: number) {
    return request<void>(
      `/projects/${projectId}/workspaces/${workspaceId}`,
      { method: 'DELETE' },
    );
  },

  /** 流式聊天，返回 Response 对象供前端读取 SSE */
  chat(projectId: number, workspaceId: number, content: string, options?: { model?: string; temperature?: number; hitlAutoTools?: string[]; enableReview?: boolean }) {
    const token = getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    return fetch(
      buildStreamingUrl(`/projects/${projectId}/workspaces/${workspaceId}/chat`),
      {
        method: 'POST',
        headers,
        body: JSON.stringify({
          content,
          model: options?.model,
          temperature: options?.temperature,
          hitl_auto_tools: options?.hitlAutoTools,
          enable_review: options?.enableReview ?? false,
        }),
      },
    );
  },

  /** HITL Resume：复用 /chat 端点，传 resume 字段，content 为空 */
  resume(projectId: number, workspaceId: number, action: 'approve' | 'reject') {
    const token = getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    return fetch(
      buildStreamingUrl(`/projects/${projectId}/workspaces/${workspaceId}/chat`),
      {
        method: 'POST',
        headers,
        body: JSON.stringify({ content: '', resume: { action } }),
      },
    );
  },
};

/** 读取 Agent SSE 事件流 */
export async function readAgentSSEStream(
  response: Response,
  onEvent: (event: AgentSSEEvent) => void,
): Promise<void> {
  await readJsonSSEStream(response, onEvent);
}

async function readJsonSSEStream<T>(
  response: Response,
  onEvent: (event: T) => void,
): Promise<void> {
  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || !trimmed.startsWith('data: ')) continue;
      const raw = trimmed.slice(6);
      if (raw === '[DONE]') continue;
      try {
        const event = JSON.parse(raw) as T;
        onEvent(event);
      } catch {
        // 忽略解析失败的行
      }
    }
  }
}

export interface SupervisorWorkflowSummaryResponse {
  id: number;
  project_id: number;
  owner_id: number;
  supervisor_session_id: string;
  user_request: string;
  model: string;
  status: string;
  workflow_profile: string;
  auto_run: boolean;
  active_node_key: string | null;
  loop_count: number;
  total_tokens: number;
  final_result: string | null;
  error_message: string | null;
  hitl_enabled: boolean;
  review_nodes: string[] | null;
  memory_enabled: boolean;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SupervisorWorkflowDetailResponse extends SupervisorWorkflowSummaryResponse {
  workflow_snapshot: Record<string, unknown> | null;
  event_history: SupervisorSSEEvent[];
}

export interface SupervisorInterruptStateResponse {
  status: string;
  interrupt: {
    tool_name: string | null;
    arguments: Record<string, unknown>;
    context: Record<string, unknown>;
  } | null;
  workflow: Record<string, unknown> | null;
}

export type SupervisorSSEEvent =
  | {
      type: 'supervisor_started';
      workflow_id: number;
      supervisor_session_id: string;
      status: string;
      workflow_profile: string;
      auto_run: boolean;
    }
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
      type: 'interrupt';
      session_id: string;
      tool_name: string;
      tool_call_id: string;
      arguments: Record<string, unknown>;
      available_actions: string[];
      context: Record<string, unknown>;
      source?: string;
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
      review_result?: Record<string, unknown> | null;
      source?: string;
    }
  | {
      type: 'review_start';
      sub_agent_name: string;
      criteria: string[];
      source?: string;
    }
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
      type: 'supervisor_done';
      supervisor_session_id: string;
      workflow: Record<string, unknown>;
      final_result: string;
      source?: string;
    }
  | { type: 'user_message'; content: string; timestamp?: string | null }
  | { type: 'error'; error: string; source?: string; session_id?: string };

export const supervisorApi = {
  list(projectId: number, page = 1, pageSize = 20) {
    return request<PageResponse<SupervisorWorkflowSummaryResponse>>(
      `/supervisor/projects/${projectId}/workflows?page=${page}&page_size=${pageSize}`,
      { method: 'GET' },
    );
  },

  get(projectId: number, workflowId: number) {
    return request<SupervisorWorkflowDetailResponse>(
      `/supervisor/projects/${projectId}/workflows/${workflowId}`,
      { method: 'GET' },
    );
  },

  chat(
    projectId: number,
    content: string,
    options?: {
      sessionId?: string;
      resume?: { action: 'approve' | 'reject'; feedback?: string };
      model?: string;
      maxLoop?: number;
      workflowProfile?: string;
      autoRun?: boolean;
      humanReview?: boolean;
      reviewNodes?: string[];
      memoryEnabled?: boolean;
    },
  ) {
    const token = getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    return fetch(buildStreamingUrl(`/supervisor/projects/${projectId}/chat`), {
      method: 'POST',
      headers,
      body: JSON.stringify({
        content,
        session_id: options?.sessionId,
        resume: options?.resume,
        model: options?.model,
        max_loop: options?.maxLoop,
        workflow_profile: options?.workflowProfile,
        auto_run: options?.autoRun,
        human_review: options?.humanReview,
        review_nodes: options?.reviewNodes,
        memory_enabled: options?.memoryEnabled,
      }),
    });
  },

  state(sessionId: string) {
    return request<SupervisorInterruptStateResponse>(
      `/supervisor/${sessionId}/state`,
      { method: 'GET' },
    );
  },

  resume(
    projectId: number,
    sessionId: string,
    action: 'approve' | 'reject',
    feedback?: string,
  ) {
    return this.chat(projectId, '', {
      sessionId,
      resume: {
        action,
        feedback,
      },
    });
  },
};

export async function readSupervisorSSEStream(
  response: Response,
  onEvent: (event: SupervisorSSEEvent) => void,
): Promise<void> {
  await readJsonSSEStream(response, onEvent);
}
