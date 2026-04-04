/**
 * FilmGenX API 客户端。
 *
 * 统一封装 fetch 请求，自动附加 Authorization header。
 * 后端 base URL 从环境变量 NEXT_PUBLIC_API_URL 读取，默认 http://localhost:8000/api/v1。
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

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

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, noAuth = false, headers: customHeaders, ...rest } = options;

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
  register(email: string, username: string, password: string) {
    return request<TokenResponse>('/auth/register', {
      method: 'POST',
      body: { email, username, password },
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
// Scenes (Episodes) API
// ---------------------------------------------------------------------------

export interface SceneResponse {
  id: number;
  project_id: number;
  scene_code: string;
  title: string;
  synopsis: string | null;
  theme: string | null;
  novel_chapter_start: string | null;
  novel_chapter_end: string | null;
  novel_excerpt: string | null;
  story_arc: string | null;
  key_events: Record<string, unknown>[];
  emotional_arc: string | null;
  characters: string[];
  character_focus: string | null;
  character_ids: number[];
  primary_location: string | null;
  location_atmosphere: string | null;
  visual_highlights: Record<string, unknown>[];
  color_palette: string | null;
  bgm_direction: string | null;
  storyboard_style_notes: string | null;
  previous_episode_hint: string | null;
  next_episode_hint: string | null;
  scene_types: string[];
  priority: string;
  estimated_duration_sec: number | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface SceneCreate {
  scene_code: string;
  title: string;
  synopsis?: string;
  theme?: string;
  novel_chapter_start?: string;
  novel_chapter_end?: string;
  novel_excerpt?: string;
  scene_types?: string[];
  priority?: string;
  character_ids?: number[];
  estimated_duration_sec?: number;
}

export interface SceneUpdate {
  title?: string;
  synopsis?: string;
  theme?: string;
  novel_chapter_start?: string;
  novel_chapter_end?: string;
  novel_excerpt?: string;
  scene_types?: string[];
  priority?: string;
  character_ids?: number[];
  estimated_duration_sec?: number;
  status?: string;
}

export const scenesApi = {
  list(projectId: number, page = 1, pageSize = 20, status?: string, priority?: string) {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (status) params.set('status', status);
    if (priority) params.set('priority', priority);
    return request<PageResponse<SceneResponse>>(
      `/projects/${projectId}/scenes?${params}`,
      { method: 'GET' },
    );
  },

  create(projectId: number, data: SceneCreate) {
    return request<SceneResponse>(`/projects/${projectId}/scenes`, {
      method: 'POST',
      body: data,
    });
  },

  get(projectId: number, sceneId: number) {
    return request<SceneResponse>(
      `/projects/${projectId}/scenes/${sceneId}`,
      { method: 'GET' },
    );
  },

  update(projectId: number, sceneId: number, data: SceneUpdate) {
    return request<SceneResponse>(
      `/projects/${projectId}/scenes/${sceneId}`,
      { method: 'PATCH', body: data },
    );
  },

  delete(projectId: number, sceneId: number) {
    return request<void>(
      `/projects/${projectId}/scenes/${sceneId}`,
      { method: 'DELETE' },
    );
  },
};

// ---------------------------------------------------------------------------
// Conversations API
// ---------------------------------------------------------------------------

export interface MessageResponse {
  id: number;
  conversation_id: number;
  role: string;
  type: string;
  content: string;
  outline_data: Record<string, unknown> | null;
  seq: number;
  created_at: string;
  updated_at: string;
}

export interface ConversationResponse {
  id: number;
  project_id: number;
  title: string;
  status: string;
  latest_outline: Record<string, unknown> | null;
  scene_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetailResponse extends ConversationResponse {
  messages: MessageResponse[];
}

export interface KeyEvent {
  order: number;
  description: string;
  emotional_beat: string;
}

export interface VisualHighlight {
  name: string;
  description: string;
}

export interface EpisodeOutline {
  // 基本信息
  title: string;
  episode_code?: string;
  synopsis: string;
  theme: string;
  // 原著映射
  novel_chapter_start: string;
  novel_chapter_end: string;
  novel_excerpt: string;
  // 叙事结构
  story_arc?: string;
  key_events?: KeyEvent[];
  emotional_arc?: string;
  // 角色
  characters: string[];
  character_focus?: string;
  // 场景设定
  primary_location?: string;
  location_atmosphere?: string;
  // 视觉与制作
  visual_highlights?: VisualHighlight[];
  color_palette?: string;
  bgm_direction?: string;
  // 分镜指导
  storyboard_style_notes: string;
  storyboard_shot_count: number;
  // 制作参数
  priority: string;
  estimated_duration_sec: number;
  scene_types: string[];
  // 上下文衔接
  previous_episode_hint?: string;
  next_episode_hint?: string;
  // 元信息
  version: number;
  generated_at?: string;
}

export interface LLMConfig {
  model: string;
  temperature?: number;
}

export const conversationsApi = {
  list(projectId: number, page = 1, pageSize = 20) {
    return request<PageResponse<ConversationResponse>>(
      `/projects/${projectId}/conversations?page=${page}&page_size=${pageSize}`,
      { method: 'GET' },
    );
  },

  create(projectId: number, title = '新对话') {
    return request<ConversationResponse>(
      `/projects/${projectId}/conversations`,
      { method: 'POST', body: { title } },
    );
  },

  get(projectId: number, conversationId: number) {
    return request<ConversationDetailResponse>(
      `/projects/${projectId}/conversations/${conversationId}`,
      { method: 'GET' },
    );
  },

  update(projectId: number, conversationId: number, data: { title?: string; status?: string; latest_outline?: EpisodeOutline }) {
    return request<ConversationResponse>(
      `/projects/${projectId}/conversations/${conversationId}`,
      { method: 'PATCH', body: data },
    );
  },

  delete(projectId: number, conversationId: number) {
    return request<void>(
      `/projects/${projectId}/conversations/${conversationId}`,
      { method: 'DELETE' },
    );
  },

  /** 流式聊天，返回 Response 对象供前端读取 SSE */
  chat(projectId: number, conversationId: number, content: string, llmConfig: LLMConfig) {
    const token = getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    return fetch(
      `${BASE_URL}/projects/${projectId}/conversations/${conversationId}/chat`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify({ content, llm_config: llmConfig }),
      },
    );
  },

  /** 流式总结，返回 Response 对象供前端读取 SSE */
  summarize(projectId: number, conversationId: number, llmConfig: LLMConfig) {
    const token = getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    return fetch(
      `${BASE_URL}/projects/${projectId}/conversations/${conversationId}/summarize`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify({ llm_config: llmConfig }),
      },
    );
  },

  /** 确认大纲，创建 Scene 并触发分镜生成 */
  confirm(projectId: number, conversationId: number, outline: EpisodeOutline, llmConfig: LLMConfig, shotCount?: number) {
    return request<{ scene_id: number; task_id: number; celery_task_id: string }>(
      `/projects/${projectId}/conversations/${conversationId}/confirm`,
      {
        method: 'POST',
        body: { outline, llm_config: llmConfig, shot_count: shotCount },
      },
    );
  },
};

// ---------------------------------------------------------------------------
// Characters API
// ---------------------------------------------------------------------------

export interface CharacterVersionResponse {
  id: number;
  character_id: number;
  version_code: string;
  label: string;
  applicable_chapter_start: string | null;
  applicable_chapter_end: string | null;
  age_description: string | null;
  height_cm: number | null;
  build_description: string | null;
  face_description: string | null;
  hair_description: string | null;
  costumes: Record<string, unknown> | null;
  dou_qi_color: string | null;
  dou_qi_level: string | null;
  key_features: string[];
  reference_image_urls: string[];
  base_image_prompt: string | null;
  // 三视图
  view_front_url: string | null;
  view_side_url: string | null;
  view_back_url: string | null;
  // 状态图片
  state_images: Record<string, string> | null;
  created_at: string;
  updated_at: string;
}

export interface CharacterResponse {
  id: number;
  project_id: number;
  char_code: string;
  name: string;
  name_aliases: string[];
  consistent_features: Record<string, unknown> | null;
  expression_guide: Record<string, unknown> | null;
  action_guide: Record<string, unknown> | null;
  relationships: Record<string, unknown> | null;
  role_description: string | null;
  created_at: string;
  updated_at: string;
}

export interface CharacterDetailResponse extends CharacterResponse {
  versions: CharacterVersionResponse[];
}

export const charactersApi = {
  list(projectId: number, page = 1, pageSize = 50) {
    return request<PageResponse<CharacterResponse>>(
      `/projects/${projectId}/characters?page=${page}&page_size=${pageSize}`,
      { method: 'GET' },
    );
  },

  create(projectId: number, data: { char_code: string; name: string; [key: string]: unknown }) {
    return request<CharacterResponse>(
      `/projects/${projectId}/characters`,
      { method: 'POST', body: data },
    );
  },

  get(projectId: number, characterId: number) {
    return request<CharacterDetailResponse>(
      `/projects/${projectId}/characters/${characterId}`,
      { method: 'GET' },
    );
  },

  update(projectId: number, characterId: number, data: Record<string, unknown>) {
    return request<CharacterResponse>(
      `/projects/${projectId}/characters/${characterId}`,
      { method: 'PATCH', body: data },
    );
  },

  delete(projectId: number, characterId: number) {
    return request<void>(
      `/projects/${projectId}/characters/${characterId}`,
      { method: 'DELETE' },
    );
  },

  // 角色版本
  listVersions(projectId: number, characterId: number) {
    return request<CharacterVersionResponse[]>(
      `/projects/${projectId}/characters/${characterId}/versions`,
      { method: 'GET' },
    );
  },

  createVersion(projectId: number, characterId: number, data: Record<string, unknown>) {
    return request<CharacterVersionResponse>(
      `/projects/${projectId}/characters/${characterId}/versions`,
      { method: 'POST', body: data },
    );
  },

  updateVersion(projectId: number, characterId: number, versionId: number, data: Record<string, unknown>) {
    return request<CharacterVersionResponse>(
      `/projects/${projectId}/characters/${characterId}/versions/${versionId}`,
      { method: 'PATCH', body: data },
    );
  },

  deleteVersion(projectId: number, characterId: number, versionId: number) {
    return request<void>(
      `/projects/${projectId}/characters/${characterId}/versions/${versionId}`,
      { method: 'DELETE' },
    );
  },

  // 角色图片上传
  uploadReferenceImage(projectId: number, characterId: number, versionId: number, file: File): Promise<CharacterVersionResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return fetch(
      `${BASE_URL}/projects/${projectId}/characters/${characterId}/versions/${versionId}/images/reference`,
      { method: 'POST', headers, body: formData },
    ).then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '上传失败' }));
        throw new Error(err.detail || '上传失败');
      }
      return res.json() as Promise<CharacterVersionResponse>;
    });
  },

  uploadViewImage(projectId: number, characterId: number, versionId: number, viewType: 'front' | 'side' | 'back', file: File): Promise<CharacterVersionResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return fetch(
      `${BASE_URL}/projects/${projectId}/characters/${characterId}/versions/${versionId}/images/view/${viewType}`,
      { method: 'POST', headers, body: formData },
    ).then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '上传失败' }));
        throw new Error(err.detail || '上传失败');
      }
      return res.json() as Promise<CharacterVersionResponse>;
    });
  },

  uploadStateImage(projectId: number, characterId: number, versionId: number, stateType: string, file: File): Promise<CharacterVersionResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return fetch(
      `${BASE_URL}/projects/${projectId}/characters/${characterId}/versions/${versionId}/images/state/${stateType}`,
      { method: 'POST', headers, body: formData },
    ).then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '上传失败' }));
        throw new Error(err.detail || '上传失败');
      }
      return res.json() as Promise<CharacterVersionResponse>;
    });
  },

  // 删除图片
  deleteReferenceImage(projectId: number, characterId: number, versionId: number, imageIndex: number) {
    return request<CharacterVersionResponse>(
      `/projects/${projectId}/characters/${characterId}/versions/${versionId}/images/reference/${imageIndex}`,
      { method: 'DELETE' },
    );
  },

  deleteViewImage(projectId: number, characterId: number, versionId: number, viewType: 'front' | 'side' | 'back') {
    return request<CharacterVersionResponse>(
      `/projects/${projectId}/characters/${characterId}/versions/${versionId}/images/view/${viewType}`,
      { method: 'DELETE' },
    );
  },

  deleteStateImage(projectId: number, characterId: number, versionId: number, stateType: string) {
    return request<CharacterVersionResponse>(
      `/projects/${projectId}/characters/${characterId}/versions/${versionId}/images/state/${stateType}`,
      { method: 'DELETE' },
    );
  },

  // 图片生成
  generateViewImage(projectId: number, characterId: number, versionId: number, viewType: 'front' | 'side' | 'back', promptOverride?: string) {
    return request<{ id: number; task_id: number; task_type: string; status: string; message: string }>(
      `/projects/${projectId}/characters/${characterId}/versions/${versionId}/images/generate/view`,
      { method: 'POST', body: { view_type: viewType, prompt_override: promptOverride } },
    );
  },

  generateStateImage(projectId: number, characterId: number, versionId: number, stateType: string, stateDescription?: string, promptOverride?: string) {
    return request<{ id: number; task_id: number; task_type: string; status: string; message: string }>(
      `/projects/${projectId}/characters/${characterId}/versions/${versionId}/images/generate/state`,
      { method: 'POST', body: { state_type: stateType, state_description: stateDescription, prompt_override: promptOverride } },
    );
  },
};

// ---------------------------------------------------------------------------
// Storyboards API
// ---------------------------------------------------------------------------

export interface StoryboardResponse {
  id: number;
  scene_id: number;
  emotion_curve: unknown[] | null;
  narrative_notes: string | null;
  pacing_ratio: Record<string, unknown> | null;
  total_duration_sec: number | null;
  version: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export const storyboardsApi = {
  get(sceneId: number) {
    return request<StoryboardResponse>(`/scenes/${sceneId}/storyboard`, { method: 'GET' });
  },

  create(sceneId: number, data: Record<string, unknown>) {
    return request<StoryboardResponse>(`/scenes/${sceneId}/storyboard`, {
      method: 'POST',
      body: data,
    });
  },

  update(sceneId: number, data: Record<string, unknown>) {
    return request<StoryboardResponse>(`/scenes/${sceneId}/storyboard`, {
      method: 'PATCH',
      body: data,
    });
  },
};

// ---------------------------------------------------------------------------
// Shots API
// ---------------------------------------------------------------------------

export interface ShotResponse {
  id: number;
  storyboard_id: number;
  shot_code: string;
  sequence: number;
  duration_sec: number;
  camera: Record<string, unknown> | null;
  composition: Record<string, unknown> | null;
  char_version_ids: number[];
  characters_config: Record<string, unknown>[] | null;
  environment: Record<string, unknown> | null;
  dialogue_character: string | null;
  dialogue_text: string | null;
  dialogue_delivery: Record<string, unknown> | null;
  sound_design: Record<string, unknown> | null;
  transition_in: string | null;
  transition_out: string | null;
  transition_notes: string | null;
  dependencies: unknown[];
  image_prompt: string | null;
  negative_prompt: string | null;
  style_preset: string | null;
  qc_character_consistency: boolean;
  qc_lighting_match: boolean;
  qc_action_continuity: boolean;
  qc_approved: boolean;
  qc_score: number | null;
  status: string;
  video_url: string | null;
  created_at: string;
  updated_at: string;
}

export const shotsApi = {
  list(storyboardId: number, status?: string) {
    const params = status ? `?status=${status}` : '';
    return request<ShotResponse[]>(
      `/storyboards/${storyboardId}/shots${params}`,
      { method: 'GET' },
    );
  },

  create(storyboardId: number, data: Record<string, unknown>) {
    return request<ShotResponse>(`/storyboards/${storyboardId}/shots`, {
      method: 'POST',
      body: data,
    });
  },

  get(storyboardId: number, shotId: number) {
    return request<ShotResponse>(
      `/storyboards/${storyboardId}/shots/${shotId}`,
      { method: 'GET' },
    );
  },

  update(storyboardId: number, shotId: number, data: Record<string, unknown>) {
    return request<ShotResponse>(
      `/storyboards/${storyboardId}/shots/${shotId}`,
      { method: 'PATCH', body: data },
    );
  },

  delete(storyboardId: number, shotId: number) {
    return request<void>(
      `/storyboards/${storyboardId}/shots/${shotId}`,
      { method: 'DELETE' },
    );
  },
};

// ---------------------------------------------------------------------------
// Assets API
// ---------------------------------------------------------------------------

export interface AssetResponse {
  id: number;
  project_id: number;
  shot_id: number | null;
  location_id: number | null;
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
  version: number;
  is_current: boolean;
  parent_asset_id: number | null;
  created_at: string;
  updated_at: string;
}

export const assetsApi = {
  list(projectId: number, page = 1, pageSize = 20, filters?: { assetType?: string; shotId?: number; source?: string; isCurrent?: boolean }) {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (filters?.assetType) params.set('asset_type', filters.assetType);
    if (filters?.shotId !== undefined) params.set('shot_id', String(filters.shotId));
    if (filters?.source) params.set('source', filters.source);
    if (filters?.isCurrent !== undefined) params.set('is_current', String(filters.isCurrent));
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

  upload(projectId: number, file: File, shotId?: number, locationId?: number): Promise<AssetResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (shotId !== undefined) {
      formData.append('shot_id', String(shotId));
    }
    if (locationId !== undefined) {
      formData.append('location_id', String(locationId));
    }

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
// Tasks API
// ---------------------------------------------------------------------------

export interface TaskResponse {
  id: number;
  shot_id: number | null;
  celery_task_id: string | null;
  task_type: string;
  status: string;
  progress: number;
  input_params: Record<string, unknown> | null;
  result_asset_id: number | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  retry_count: number;
  max_retries: number;
  created_at: string;
  updated_at: string;
}

export interface ImageGenerationRequest {
  project_id?: number;
  shot_id?: number;
  location_id?: number;
  prompt: string;
  negative_prompt?: string;
  aspect_ratio?: string;
  resolution?: string;
  style_preset?: string;
  reference_image_urls?: string[];
  save_to_shot?: boolean;
}

export const tasksApi = {
  get(taskId: number) {
    return request<TaskResponse>(`/tasks/${taskId}`, { method: 'GET' });
  },

  triggerVideo(data: { shot_id: number; quality?: string; sound?: string; use_image_start?: boolean; callback_url?: string }) {
    return request<TaskResponse>('/tasks/video', {
      method: 'POST',
      body: data,
    });
  },

  triggerStoryboard(data: { scene_id: number; shot_count?: number; style_notes?: string }) {
    return request<TaskResponse>('/tasks/storyboard', {
      method: 'POST',
      body: data,
    });
  },

  triggerImage(data: ImageGenerationRequest) {
    return request<TaskResponse>('/tasks/image', {
      method: 'POST',
      body: data,
    });
  },
};

// ---------------------------------------------------------------------------
// Locations API
// ---------------------------------------------------------------------------

export interface LocationVersionResponse {
  id: number;
  location_id: number;
  version_code: string;
  label: string;
  description: string | null;
  atmosphere_override: Record<string, unknown> | null;
  time_of_day: string | null;
  weather: string | null;
  additional_elements: string[];
  removed_elements: string[];
  prompt_suffix: string | null;
  full_prompt: string | null;
  reference_image_urls: string[];
  applicable_scene_codes: string[];
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface LocationResponse {
  id: number;
  project_id: number;
  loc_code: string;
  name: string;
  aliases: string[];
  location_type: string;
  domain: string | null;
  description: string | null;
  architectural_style: string | null;
  key_elements: string[];
  default_atmosphere: Record<string, unknown> | null;
  time_variants: Record<string, string> | null;
  base_background_prompt: string | null;
  negative_prompt: string | null;
  style_preset: string | null;
  reference_image_urls: string[];
  tags: string[];
  is_active: boolean;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

export interface LocationDetailResponse extends LocationResponse {
  versions: LocationVersionResponse[];
  default_version: LocationVersionResponse | null;
  version_count: number;
}

export const locationsApi = {
  list(projectId: number, page = 1, pageSize = 50, isActive?: boolean) {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (isActive !== undefined) params.set('is_active', String(isActive));
    return request<PageResponse<LocationResponse>>(
      `/projects/${projectId}/locations?${params}`,
      { method: 'GET' },
    );
  },

  listBrief(projectId: number) {
    return request<LocationResponse[]>(
      `/projects/${projectId}/locations/brief`,
      { method: 'GET' },
    );
  },

  create(projectId: number, data: Record<string, unknown>) {
    return request<LocationResponse>(
      `/projects/${projectId}/locations`,
      { method: 'POST', body: data },
    );
  },

  get(projectId: number, locationId: number) {
    return request<LocationDetailResponse>(
      `/projects/${projectId}/locations/${locationId}`,
      { method: 'GET' },
    );
  },

  update(projectId: number, locationId: number, data: Record<string, unknown>) {
    return request<LocationResponse>(
      `/projects/${projectId}/locations/${locationId}`,
      { method: 'PATCH', body: data },
    );
  },

  delete(projectId: number, locationId: number) {
    return request<void>(
      `/projects/${projectId}/locations/${locationId}`,
      { method: 'DELETE' },
    );
  },

  // Versions
  listVersions(projectId: number, locationId: number) {
    return request<LocationVersionResponse[]>(
      `/projects/${projectId}/locations/${locationId}/versions`,
      { method: 'GET' },
    );
  },

  createVersion(projectId: number, locationId: number, data: Record<string, unknown>) {
    return request<LocationVersionResponse>(
      `/projects/${projectId}/locations/${locationId}/versions`,
      { method: 'POST', body: data },
    );
  },

  updateVersion(projectId: number, locationId: number, versionId: number, data: Record<string, unknown>) {
    return request<LocationVersionResponse>(
      `/projects/${projectId}/locations/${locationId}/versions/${versionId}`,
      { method: 'PATCH', body: data },
    );
  },

  deleteVersion(projectId: number, locationId: number, versionId: number) {
    return request<void>(
      `/projects/${projectId}/locations/${locationId}/versions/${versionId}`,
      { method: 'DELETE' },
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
