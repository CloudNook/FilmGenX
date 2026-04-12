'use client';

import { use, useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { AppLayout } from '@/components/layout';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable';
import {
  workspacesApi,
  readAgentSSEStream,
  type ProjectResponse,
  type WorkspaceResponse,
  type WorkspaceDetailResponse,
  type AgentMessageResponse,
  type AgentSSEEvent,
} from '@/lib/api';
import { projectsApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  Send,
  Plus,
  Sparkles,
  MessageSquare,
  Trash2,
  Loader2,
  Brain,
  Wrench,
  ChevronRight,
  Bot,
  Zap,
  Activity,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// 消息分组：将 assistant + thinking + tool_calls + tool results 组合展示
// ---------------------------------------------------------------------------

interface DisplayGroup {
  id: string;
  type: 'user' | 'assistant' | 'thinking' | 'tool_calls';
  content: string;
  thinking?: string;
  toolCalls?: ToolCallDisplay[];
  seq: number;
  createdAt?: string | null;
}

interface ToolCallDisplay {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: unknown;
  isError?: boolean;
  finished?: boolean;
}

function groupMessages(messages: AgentMessageResponse[]): DisplayGroup[] {
  const groups: DisplayGroup[] = [];
  let i = 0;

  while (i < messages.length) {
    const msg = messages[i];

    if (msg.role === 'user') {
      groups.push({
        id: `msg-${msg.seq}`,
        type: 'user',
        content: msg.content,
        seq: msg.seq,
        createdAt: msg.created_at,
      });
      i++;
    } else if (msg.role === 'assistant') {
      const meta = msg.extra_metadata || {};
      const thinking = meta.thinking;
      const toolCallsMeta = meta.tool_calls;

      if (thinking) {
        groups.push({
          id: `thinking-${msg.seq}`,
          type: 'thinking',
          content: '',
          thinking,
          seq: msg.seq,
        });
      }

      // 优先从 extra_metadata.tool_calls 读取（含完整 arguments + result）
      if (toolCallsMeta && toolCallsMeta.length > 0) {
        groups.push({
          id: `tools-${msg.seq}`,
          type: 'tool_calls',
          content: '',
          toolCalls: toolCallsMeta.map((tc) => ({
            id: tc.id,
            name: tc.name,
            arguments: tc.arguments || {},
            result: tc.result,
            isError: tc.is_error ?? false,
          })),
          seq: msg.seq,
        });
        // 跳过紧随其后的 tool 角色消息（它们已经合并进 extra_metadata）
        let j = i + 1;
        while (j < messages.length && messages[j].role === 'tool') {
          j++;
        }
        i = j;
      } else {
        // 兼容旧数据：从后续 tool 消息拼装
        const toolResults: DisplayGroup['toolCalls'] = [];
        let j = i + 1;
        while (j < messages.length && messages[j].role === 'tool') {
          toolResults.push({
            id: messages[j].tool_call_id || `tool-${messages[j].seq}`,
            name: messages[j].tool_name || 'unknown',
            arguments: {},
            result: messages[j].content,
            isError: false,
          });
          j++;
        }
        if (toolResults.length > 0) {
          groups.push({
            id: `tools-${msg.seq}`,
            type: 'tool_calls',
            content: '',
            toolCalls: toolResults,
            seq: msg.seq,
          });
        }
        i = j;
      }

      if (msg.content) {
        groups.push({
          id: `assistant-${msg.seq}`,
          type: 'assistant',
          content: msg.content,
          seq: msg.seq,
          createdAt: msg.created_at,
        });
      }
    } else if (msg.role === 'tool') {
      // 独立的 tool 消息（不应出现，但安全处理）
      groups.push({
        id: `tool-standalone-${msg.seq}`,
        type: 'tool_calls',
        content: '',
        toolCalls: [{
          id: msg.tool_call_id || `tool-${msg.seq}`,
          name: msg.tool_name || 'unknown',
          arguments: {},
          result: msg.content,
          isError: false,
        }],
        seq: msg.seq,
      });
      i++;
    } else {
      i++;
    }
  }

  return groups;
}

// ---------------------------------------------------------------------------
// 流式消息状态
// ---------------------------------------------------------------------------

interface StreamingState {
  thinking: string;
  text: string;
  toolCalls: ToolCallDisplay[];
  usage: { prompt_tokens?: number | null; completion_tokens?: number | null; thinking_tokens?: number | null; total_tokens?: number | null } | null;
  loopCount: number;
}

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------

export default function WorkspacePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const projectIdNum = Number(projectId);
  const { user } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [workspaces, setWorkspaces] = useState<WorkspaceResponse[]>([]);
  const [selectedWsId, setSelectedWsId] = useState<number | null>(null);
  const [messages, setMessages] = useState<AgentMessageResponse[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streaming, setStreaming] = useState<StreamingState>({
    thinking: '',
    text: '',
    toolCalls: [],
    usage: null,
    loopCount: 0,
  });
  const [lastUsage, setLastUsage] = useState<{ prompt_tokens?: number | null; completion_tokens?: number | null; thinking_tokens?: number | null; total_tokens?: number | null } | null>(null);
  const [model, setModel] = useState('gemini-3-flash-preview');
  const [temperature, setTemperature] = useState(0.7);
  const [loading, setLoading] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const selectedWs = workspaces.find((w) => w.id === selectedWsId) || null;

  // Load project + workspaces
  useEffect(() => {
    if (isNaN(projectIdNum)) return;

    Promise.all([
      projectsApi.get(projectIdNum).catch(() => null),
      workspacesApi.list(projectIdNum).then((r) => r.items).catch(() => []),
    ]).then(([p, ws]) => {
      setProject(p);
      setWorkspaces(ws);
      if (ws.length > 0 && !selectedWsId) {
        setSelectedWsId(ws[0].id);
      }
      setLoading(false);
    });
  }, [projectIdNum]);

  // Load messages when workspace selected
  useEffect(() => {
    if (!selectedWsId || isNaN(projectIdNum)) return;

    workspacesApi
      .get(projectIdNum, selectedWsId)
      .then((detail: WorkspaceDetailResponse) => {
        setMessages(detail.messages || []);
        const lastAssistant = [...(detail.messages || [])].reverse().find((m) => m.role === 'assistant' && m.extra_metadata?.accumulated_usage);
        if (lastAssistant?.extra_metadata?.accumulated_usage) setLastUsage(lastAssistant.extra_metadata.accumulated_usage);
      })
      .catch(() => setMessages([]));
  }, [selectedWsId, projectIdNum]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streaming.text, streaming.thinking]);

  // Reload workspace detail
  const reloadWs = useCallback(async () => {
    if (!selectedWsId) return;
    const detail = await workspacesApi.get(projectIdNum, selectedWsId);
    setMessages(detail.messages || []);
    const lastAssistant = [...(detail.messages || [])].reverse().find((m) => m.role === 'assistant' && m.extra_metadata?.accumulated_usage);
    if (lastAssistant?.extra_metadata?.accumulated_usage) setLastUsage(lastAssistant.extra_metadata.accumulated_usage);
    // Update workspace in list (token count, last_message_at)
    setWorkspaces((prev) =>
      prev.map((w) =>
        w.id === selectedWsId
          ? { ...w, total_tokens: detail.total_tokens, last_message_at: detail.last_message_at }
          : w
      ),
    );
  }, [selectedWsId, projectIdNum]);

  // Create new workspace
  const handleNewWorkspace = useCallback(async () => {
    try {
      const ws = await workspacesApi.create(projectIdNum, { title: '新工作台' });
      setWorkspaces((prev) => [ws, ...prev]);
      setSelectedWsId(ws.id);
    } catch (err) {
      console.error('Failed to create workspace:', err);
    }
  }, [projectIdNum]);

  // Delete workspace
  const handleDeleteWorkspace = useCallback(
    async (wsId: number) => {
      try {
        await workspacesApi.delete(projectIdNum, wsId);
        setWorkspaces((prev) => prev.filter((w) => w.id !== wsId));
        if (selectedWsId === wsId) {
          setSelectedWsId(null);
          setMessages([]);
        }
      } catch (err) {
        console.error('Failed to delete workspace:', err);
      }
    },
    [projectIdNum, selectedWsId],
  );

  // Send message
  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim() || isStreaming || !selectedWsId) return;

    const userContent = inputValue.trim();
    setInputValue('');
    setIsStreaming(true);
    setStreaming({ thinking: '', text: '', toolCalls: [], usage: null, loopCount: 0 });

    // Optimistic user message
    const tempUserMsg: AgentMessageResponse = {
      role: 'user',
      content: userContent,
      seq: messages.length,
      tool_call_id: null,
      tool_name: null,
      usage: null,
      extra_metadata: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const response = await workspacesApi.chat(
        projectIdNum,
        selectedWsId,
        userContent,
        { model, temperature },
      );

      if (!response.ok) throw new Error(`Chat request failed: ${response.status}`);

      await readAgentSSEStream(response, (event: AgentSSEEvent) => {
        setStreaming((prev) => {
          switch (event.type) {
            case 'thinking':
              return { ...prev, thinking: prev.thinking + event.content };
            case 'text':
              return { ...prev, text: prev.text + event.content };
            case 'tool_start':
              return {
                ...prev,
                toolCalls: [
                  ...prev.toolCalls,
                  {
                    id: event.tool_call_id,
                    name: event.tool_name,
                    arguments: event.arguments,
                    finished: false,
                  },
                ],
              };
            case 'tool_end':
              return {
                ...prev,
                toolCalls: prev.toolCalls.map((tc) =>
                  tc.id === event.tool_call_id
                    ? { ...tc, result: event.result, isError: event.is_error, finished: true }
                    : tc
                ),
              };
            case 'done':
              if (event.usage) setLastUsage(event.usage);
              return {
                ...prev,
                usage: event.usage,
                loopCount: event.loop_count,
              };
            case 'error':
              return { ...prev, text: prev.text + `\n\n**错误:** ${event.error}` };
            default:
              return prev;
          }
        });
      });

      await reloadWs();
    } catch (err) {
      console.error('Chat error:', err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `出错了：${err instanceof Error ? err.message : '未知错误'}`,
          seq: prev.length,
          tool_call_id: null,
          tool_name: null,
          usage: null,
          extra_metadata: null,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsStreaming(false);
      setStreaming({ thinking: '', text: '', toolCalls: [], usage: null, loopCount: 0 });
    }
  }, [inputValue, isStreaming, selectedWsId, projectIdNum, messages.length, reloadWs, model, temperature]);

  const formatTime = (timestamp: string | null | undefined) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  };

  const formatTokens = (tokens: number) => {
    if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}k`;
    return String(tokens);
  };

  const userFallback = user?.username?.slice(0, 1) || 'U';

  // Group messages for display
  const displayGroups = groupMessages(messages);

  // ----- RENDER -----

  if (loading) {
    return (
      <AppLayout projectId={projectId} showSearch={false}>
        <div className="flex items-center justify-center h-full">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppLayout>
    );
  }

  if (!project) {
    return (
      <AppLayout projectId={projectId} showSearch={false}>
        <div className="flex items-center justify-center h-full">
          <p className="text-muted-foreground">项目不存在</p>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout
      projectId={projectId}
      showSearch={false}
      breadcrumbs={[
        { label: '项目', href: '/projects' },
        { label: project.name, href: `/projects/${projectId}` },
        { label: 'AI 工作台' },
      ]}
    >
      <div className="flex h-[calc(100vh-4rem)] w-full min-h-0 overflow-hidden">
        <ResizablePanelGroup direction="horizontal">
          {/* ===== Left Sidebar - Workspace List ===== */}
          <ResizablePanel defaultSize={18} minSize={14} maxSize={35} className="bg-card flex flex-col min-h-0">
            <div className="p-3 shrink-0 border-b border-border">
              <Button
                className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
                onClick={handleNewWorkspace}
              >
                <Plus className="h-4 w-4 mr-2" />
                新建工作台
              </Button>
            </div>

            <ScrollArea className="flex-1 min-h-0">
              <div className="p-2 space-y-1">
                {workspaces.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <Brain className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">暂无工作台</p>
                    <p className="text-[10px] mt-1">点击上方按钮创建</p>
                  </div>
                )}
                {workspaces.map((ws) => (
                  <div key={ws.id} className="group relative">
                    <button
                      onClick={() => setSelectedWsId(ws.id)}
                      className={cn(
                        'w-full text-left p-3 rounded-lg transition-colors',
                        selectedWsId === ws.id
                          ? 'bg-primary/10 border border-primary/30'
                          : 'hover:bg-secondary/50'
                      )}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <Brain className="h-4 w-4 text-primary" />
                        <span className="font-medium text-foreground text-sm truncate">
                          {ws.title}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {ws.total_tokens > 0 && (
                          <Badge variant="outline" className="text-[10px] border-border">
                            <Zap className="h-2.5 w-2.5 mr-0.5" />
                            {formatTokens(ws.total_tokens)}
                          </Badge>
                        )}
                        {ws.last_message_at && (
                          <span className="text-[10px] text-muted-foreground">
                            {formatTime(ws.last_message_at)}
                          </span>
                        )}
                      </div>
                    </button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute top-2 right-2 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteWorkspace(ws.id);
                      }}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </ResizablePanel>

          <ResizableHandle withHandle />

          {/* ===== Main Chat Area ===== */}
          <ResizablePanel defaultSize={58} minSize={30} className="flex flex-col min-h-0 bg-background">
            {/* Header */}
            <div className="h-14 shrink-0 border-b border-border px-6 flex items-center justify-between bg-card">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <Brain className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <h2 className="font-medium text-foreground text-sm">
                    {selectedWs?.title || 'AI 工作台'}
                  </h2>
                  <p className="text-[10px] text-muted-foreground">Agent 多轮对话</p>
                </div>
              </div>
              {selectedWs && selectedWs.total_tokens > 0 && (
                <Badge variant="outline" className="text-xs">
                  <Zap className="h-3 w-3 mr-1" />
                  {formatTokens(selectedWs.total_tokens)} tokens
                </Badge>
              )}
            </div>

            {/* Messages */}
            <ScrollArea className="flex-1 min-h-0 p-6">
              <div className="max-w-3xl mx-auto space-y-4">
                {/* Welcome */}
                {!selectedWsId && (
                  <div className="text-center py-12">
                    <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                      <Brain className="h-8 w-8 text-primary" />
                    </div>
                    <h3 className="text-xl font-semibold text-foreground mb-2">
                      AI 工作台
                    </h3>
                    <p className="text-muted-foreground mb-6 max-w-md mx-auto">
                      与 AI Agent 进行多轮对话，完成从剧本到视频的全流程创作
                    </p>
                    <Button onClick={handleNewWorkspace} className="bg-primary text-primary-foreground">
                      <Plus className="h-4 w-4 mr-2" />
                      创建工作台
                    </Button>
                  </div>
                )}

                {selectedWsId && displayGroups.length === 0 && !isStreaming && (
                  <div className="text-center py-12">
                    <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                      <Sparkles className="h-8 w-8 text-primary" />
                    </div>
                    <h3 className="text-xl font-semibold text-foreground mb-2">
                      开始对话
                    </h3>
                    <p className="text-muted-foreground max-w-md mx-auto">
                      描述你的创作需求，Agent 会调用工具完成专业任务
                    </p>
                  </div>
                )}

                {/* Message Groups */}
                {displayGroups.map((group) => (
                  <MessageGroup
                    key={group.id}
                    group={group}
                    userFallback={userFallback}
                  />
                ))}

                {/* Streaming State */}
                {isStreaming && (
                  <StreamingMessageGroup
                    streaming={streaming}
                    userFallback={userFallback}
                  />
                )}

                {/* Typing Indicator */}
                {isStreaming && !streaming.text && !streaming.thinking && streaming.toolCalls.length === 0 && (
                  <div className="flex gap-4">
                    <Avatar className="h-8 w-8 shrink-0">
                      <AvatarFallback className="bg-primary/10 text-primary">
                        <Brain className="h-4 w-4" />
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex items-center gap-1 bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3">
                      <div className="h-2 w-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="h-2 w-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="h-2 w-2 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            {/* Input Area */}
            <div className="shrink-0 border-t border-border p-4 bg-card">
              <div className="max-w-3xl mx-auto">
                <div className="flex items-end gap-3">
                  <div className="flex-1 bg-secondary rounded-2xl border border-border focus-within:border-primary/50 transition-colors">
                    <div className="flex items-center gap-2 px-4 py-3">
                      <Input
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSendMessage();
                          }
                        }}
                        placeholder={
                          selectedWsId
                            ? '描述你的创作需求...'
                            : '请先选择或创建一个工作台'
                        }
                        disabled={!selectedWsId || isStreaming}
                        className="flex-1 border-0 bg-transparent focus-visible:ring-0 px-0"
                      />
                    </div>
                  </div>
                  <Button
                    onClick={handleSendMessage}
                    disabled={!inputValue.trim() || isStreaming || !selectedWsId}
                    className="h-12 w-12 rounded-full bg-primary text-primary-foreground hover:bg-primary/90"
                  >
                    {isStreaming ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                      <Send className="h-5 w-5" />
                    )}
                  </Button>
                </div>
                <p className="text-[10px] text-muted-foreground text-center mt-2">
                  Agent 会自动思考并调用工具完成你的需求
                </p>
              </div>
            </div>
          </ResizablePanel>

          <ResizableHandle withHandle />

          {/* ===== Right Sidebar - Agent Info ===== */}
          <ResizablePanel defaultSize={24} minSize={18} maxSize={40} className="bg-card flex flex-col min-h-0">
            <div className="p-4 border-b border-border">
              <h3 className="font-medium text-foreground text-sm flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" />
                Agent 信息
              </h3>
            </div>

            <ScrollArea className="flex-1 min-h-0">
              <div className="p-4 space-y-4">
                {/* Agent Status */}
                <div className="space-y-2">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">状态</p>
                  <div className="flex items-center gap-2">
                    <div className={cn(
                      'h-2 w-2 rounded-full',
                      isStreaming ? 'bg-yellow-500 animate-pulse' : 'bg-green-500'
                    )} />
                    <span className="text-sm text-foreground">
                      {isStreaming ? '思考中...' : '空闲'}
                    </span>
                  </div>
                </div>

                {/* Model Settings */}
                <div className="space-y-2">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">模型设置</p>
                  <div className="space-y-3">
                    <div>
                      <label className="text-xs text-muted-foreground mb-1 block">模型</label>
                      <select
                        value={model}
                        onChange={(e) => setModel(e.target.value)}
                        disabled={isStreaming}
                        className="w-full text-xs bg-secondary border border-border rounded-md px-2 py-1.5 text-foreground focus:outline-none focus:border-primary/50 disabled:opacity-50"
                      >
                        <option value="gemini-3-flash-preview">Gemini 3 Flash Preview</option>
                        <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground mb-1 flex justify-between">
                        <span>温度</span>
                        <span className="font-medium text-foreground">{temperature.toFixed(1)}</span>
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="2"
                        step="0.1"
                        value={temperature}
                        onChange={(e) => setTemperature(Number(e.target.value))}
                        disabled={isStreaming}
                        className="w-full h-1.5 accent-primary disabled:opacity-50"
                      />
                      <div className="flex justify-between text-[10px] text-muted-foreground mt-0.5">
                        <span>精准</span>
                        <span>创意</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Token Usage */}
                {selectedWs && (
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Token 消耗</p>
                    <div className="bg-secondary/50 rounded-lg p-3 space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">累计</span>
                        <span className="font-medium text-foreground">{formatTokens(selectedWs.total_tokens)}</span>
                      </div>
                      {lastUsage && (
                        <>
                          <div className="border-t border-border/50 my-1" />
                          <div className="flex justify-between text-xs text-muted-foreground">
                            <span>上次 prompt</span>
                            <span>{lastUsage.prompt_tokens != null ? String(lastUsage.prompt_tokens) : '-'}</span>
                          </div>
                          <div className="flex justify-between text-xs text-muted-foreground">
                            <span>上次 completion</span>
                            <span>{lastUsage.completion_tokens != null ? String(lastUsage.completion_tokens) : '-'}</span>
                          </div>
                          {lastUsage.thinking_tokens != null && lastUsage.thinking_tokens > 0 && (
                            <div className="flex justify-between text-xs text-muted-foreground">
                              <span>上次 thinking</span>
                              <span>{String(lastUsage.thinking_tokens)}</span>
                            </div>
                          )}
                          <div className="flex justify-between text-xs font-medium text-foreground">
                            <span>上次合计</span>
                            <span>{lastUsage.total_tokens != null ? String(lastUsage.total_tokens) : '-'}</span>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )}

                {/* Loop Count */}
                {(isStreaming || streaming.loopCount > 0) && (
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">循环次数</p>
                    <div className="bg-secondary/50 rounded-lg p-3">
                      <span className="text-sm font-medium text-foreground">{streaming.loopCount}</span>
                      <span className="text-xs text-muted-foreground ml-1">轮</span>
                    </div>
                  </div>
                )}

                {/* Tool Calls */}
                {(streaming.toolCalls.length > 0) && (
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">工具调用</p>
                    <div className="space-y-2">
                      {streaming.toolCalls.map((tc) => (
                        <div key={tc.id} className="bg-secondary/50 rounded-lg p-3">
                          <div className="flex items-center gap-2">
                            <Wrench className="h-3.5 w-3.5 text-primary" />
                            <span className="text-sm font-medium text-foreground">{tc.name}</span>
                            {tc.finished ? (
                              <Badge variant="outline" className="text-[10px] border-green-500/30 text-green-600">
                                完成
                              </Badge>
                            ) : (
                              <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* System Prompt */}
                {selectedWs?.system_prompt && (
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">System Prompt</p>
                    <div className="bg-secondary/50 rounded-lg p-3">
                      <p className="text-xs text-muted-foreground line-clamp-4">
                        {selectedWs.system_prompt}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </AppLayout>
  );
}

// ---------------------------------------------------------------------------
// Message Group Component
// ---------------------------------------------------------------------------

function MessageGroup({
  group,
  userFallback,
}: {
  group: DisplayGroup;
  userFallback: string;
}) {
  if (group.type === 'user') {
    return (
      <div className="flex gap-4 flex-row-reverse">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-primary text-primary-foreground">
            {userFallback}
          </AvatarFallback>
        </Avatar>
        <div className="text-right max-w-[80%]">
          <div className="inline-block rounded-2xl px-4 py-3 bg-primary text-primary-foreground rounded-tr-sm">
            <p className="text-sm whitespace-pre-wrap leading-relaxed">{group.content}</p>
          </div>
          {group.createdAt && (
            <div className="flex justify-end mt-1">
              <span className="text-[10px] text-muted-foreground">{formatTimeStatic(group.createdAt)}</span>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (group.type === 'thinking') {
    return (
      <Collapsible defaultOpen={false}>
        <div className="flex gap-4">
          <Avatar className="h-8 w-8 shrink-0">
            <AvatarFallback className="bg-muted text-muted-foreground">
              <Bot className="h-4 w-4" />
            </AvatarFallback>
          </Avatar>
          <div className="max-w-[80%]">
            <CollapsibleTrigger asChild>
              <button className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors mb-1">
                <ChevronRight className="h-3 w-3 transition-transform [[data-state=open]>&]:rotate-90" />
                <Bot className="h-3 w-3" />
                思考过程
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="rounded-xl px-4 py-3 bg-muted/50 border border-border text-sm text-muted-foreground italic whitespace-pre-wrap">
                {group.thinking}
              </div>
            </CollapsibleContent>
          </div>
        </div>
      </Collapsible>
    );
  }

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

  // assistant text
  return (
    <div className="flex gap-4">
      <Avatar className="h-8 w-8 shrink-0">
        <AvatarFallback className="bg-primary/10 text-primary">
          <Brain className="h-4 w-4" />
        </AvatarFallback>
      </Avatar>
      <div className="max-w-[80%]">
        <div className="inline-block rounded-2xl px-4 py-3 bg-card border border-border rounded-tl-sm">
          <div className="prose prose-custom prose-sm dark:prose-invert max-w-none break-words">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {group.content}
            </ReactMarkdown>
          </div>
        </div>
        {group.createdAt && (
          <div className="mt-1">
            <span className="text-[10px] text-muted-foreground">{formatTimeStatic(group.createdAt)}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function ToolCallDisclosure({
  toolCall,
}: {
  toolCall: ToolCallDisplay;
}) {
  const isFinished = toolCall.finished ?? true;
  const hasArguments = Object.keys(toolCall.arguments || {}).length > 0;

  return (
    <Collapsible defaultOpen={false}>
      <div className="rounded-lg px-3 py-2 bg-primary/5 border border-primary/10 text-xs">
        <CollapsibleTrigger asChild>
          <button className="flex items-center gap-1.5 w-full text-left">
            <ChevronRight className="h-3 w-3 text-primary shrink-0 transition-transform [[data-state=open]>&]:rotate-90" />
            {isFinished ? (
              <Wrench className="h-3 w-3 text-primary shrink-0" />
            ) : (
              <Loader2 className="h-3 w-3 animate-spin text-primary shrink-0" />
            )}
            <span className="font-medium text-foreground">{toolCall.name}</span>
            {toolCall.isError ? (
              <Badge variant="outline" className="text-[10px] border-destructive/30 text-destructive ml-1">
                错误
              </Badge>
            ) : isFinished ? (
              <Badge variant="outline" className="text-[10px] border-primary/30 text-primary ml-1">
                完成
              </Badge>
            ) : (
              <Badge variant="outline" className="text-[10px] border-yellow-500/30 text-yellow-600 ml-1">
                执行中
              </Badge>
            )}
          </button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="mt-2 space-y-2">
            {hasArguments && (
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">参数</p>
                <pre className="text-muted-foreground bg-background/60 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
                  {JSON.stringify(toolCall.arguments, null, 2)}
                </pre>
              </div>
            )}
            {toolCall.result != null ? (
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">结果</p>
                <pre
                  className={`bg-background/60 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all ${
                    toolCall.isError ? 'text-destructive' : 'text-muted-foreground'
                  }`}
                >
                  {typeof toolCall.result === 'string'
                    ? toolCall.result
                    : JSON.stringify(toolCall.result, null, 2)}
                </pre>
              </div>
            ) : (
              !isFinished && (
                <p className="text-[11px] text-muted-foreground">正在等待工具返回结果...</p>
              )
            )}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}

// ---------------------------------------------------------------------------
// Streaming Message Component
// ---------------------------------------------------------------------------

function StreamingMessageGroup({
  streaming,
  userFallback,
}: {
  streaming: StreamingState;
  userFallback: string;
}) {
  return (
    <div className="space-y-3">
      {/* Thinking */}
      {streaming.thinking && (
        <Collapsible defaultOpen={false}>
          <div className="flex gap-4">
            <Avatar className="h-8 w-8 shrink-0">
              <AvatarFallback className="bg-muted text-muted-foreground">
                <Bot className="h-4 w-4" />
              </AvatarFallback>
            </Avatar>
            <div className="max-w-[80%]">
              <CollapsibleTrigger asChild>
                <button className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors mb-1">
                  <ChevronRight className="h-3 w-3 transition-transform [[data-state=open]>&]:rotate-90" />
                  <Loader2 className="h-3 w-3 animate-spin" />
                  思考中...
                </button>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="rounded-xl px-4 py-3 bg-muted/50 border border-border text-sm text-muted-foreground italic whitespace-pre-wrap">
                  {streaming.thinking}
                </div>
              </CollapsibleContent>
            </div>
          </div>
        </Collapsible>
      )}

      {/* Tool Calls */}
      {streaming.toolCalls.length > 0 && (
        <div className="flex gap-4">
          <Avatar className="h-8 w-8 shrink-0">
            <AvatarFallback className="bg-primary/10 text-primary">
              <Wrench className="h-4 w-4" />
            </AvatarFallback>
          </Avatar>
          <div className="max-w-[80%] space-y-1.5">
            {streaming.toolCalls.map((tc) => (
              <ToolCallDisclosure key={tc.id} toolCall={tc} />
            ))}
          </div>
        </div>
      )}

      {/* Text */}
      {streaming.text && (
        <div className="flex gap-4">
          <Avatar className="h-8 w-8 shrink-0">
            <AvatarFallback className="bg-primary/10 text-primary">
              <Brain className="h-4 w-4" />
            </AvatarFallback>
          </Avatar>
          <div className="inline-block rounded-2xl px-4 py-3 bg-card border border-border rounded-tl-sm max-w-[80%]">
            <div className="prose prose-custom prose-sm dark:prose-invert max-w-none break-words">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {streaming.text + ' ▍'}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}

      {/* Done with usage */}
      {streaming.usage && (
        <div className="flex items-center justify-center gap-3 py-1">
          {streaming.usage.total_tokens && (
            <Badge variant="outline" className="text-[10px] border-border">
              <Zap className="h-2.5 w-2.5 mr-0.5" />
              {String(streaming.usage.total_tokens)} tokens
            </Badge>
          )}
          {streaming.loopCount > 0 && (
            <Badge variant="outline" className="text-[10px] border-border">
              <Activity className="h-2.5 w-2.5 mr-0.5" />
              {streaming.loopCount} 轮循环
            </Badge>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTimeStatic(timestamp: string) {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}
