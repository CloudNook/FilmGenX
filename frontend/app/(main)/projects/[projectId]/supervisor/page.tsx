'use client';

import { use, useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { AppLayout } from '@/components/layout';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable';
import {
  projectsApi,
  readSupervisorSSEStream,
  supervisorApi,
  type ProjectResponse,
  type SupervisorInterruptStateResponse,
  type SupervisorSSEEvent,
  type SupervisorWorkflowDetailResponse,
  type SupervisorWorkflowSummaryResponse,
} from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import {
  appendSupervisorDisplayEvent,
  buildWorkflowNodeSummaries,
  resolveInitialSupervisorRunId,
  type SupervisorDisplayEntry,
} from '@/lib/supervisor-display';
import {
  Activity,
  Bot,
  Brain,
  CheckCircle2,
  GitBranch,
  Loader2,
  Plus,
  Send,
  ShieldAlert,
  Sparkles,
  WandSparkles,
  Wrench,
  XCircle,
  Zap,
} from 'lucide-react';

interface HitlState {
  sessionId: string;
  toolName: string;
  toolCallId: string;
  arguments: Record<string, unknown>;
  availableActions: string[];
  context: Record<string, unknown>;
}

function getSupervisorSelectionStorageKey(projectId: number) {
  return `filmgenx_supervisor_selected_${projectId}`;
}

function loadPersistedRunId(projectId: number): number | null {
  if (typeof window === 'undefined') return null;
  const rawValue = window.localStorage.getItem(getSupervisorSelectionStorageKey(projectId));
  if (!rawValue) return null;
  const parsed = Number(rawValue);
  return Number.isNaN(parsed) ? null : parsed;
}

function formatTime(timestamp: string | null | undefined) {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

function formatTokens(tokens: number) {
  if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}k`;
  return String(tokens);
}

function getStatusBadgeClass(status: string) {
  switch (status) {
    case 'running':
      return 'border-yellow-500/30 text-yellow-600';
    case 'waiting_review':
    case 'pending_confirmation':
      return 'border-yellow-500/30 text-yellow-600';
    case 'completed':
    case 'fresh':
      return 'border-green-500/30 text-green-600';
    case 'ready':
      return 'border-blue-500/30 text-blue-600';
    case 'stale':
      return 'border-orange-500/30 text-orange-600';
    case 'failed':
    case 'error':
      return 'border-destructive/30 text-destructive';
    default:
      return 'border-border text-muted-foreground';
  }
}

export default function SupervisorPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const projectIdNum = Number(projectId);
  const { user } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [runs, setRuns] = useState<SupervisorWorkflowSummaryResponse[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [selectedRunDetail, setSelectedRunDetail] =
    useState<SupervisorWorkflowDetailResponse | null>(null);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isResuming, setIsResuming] = useState(false);
  const [model, setModel] = useState('gemini-3-flash-preview');
  const [maxLoop, setMaxLoop] = useState(30);
  const [workflowProfile, setWorkflowProfile] = useState('default');
  const [autoRun, setAutoRun] = useState(true);
  const [humanReview, setHumanReview] = useState(false);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [liveEntries, setLiveEntries] = useState<SupervisorDisplayEntry[]>([]);
  const [liveWorkflow, setLiveWorkflow] = useState<Record<string, unknown> | null>(null);
  const [hitl, setHitl] = useState<HitlState | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const selectedRun =
    runs.find((run) => run.id === selectedRunId) || null;
  const displayedWorkflow =
    selectedRunId != null && selectedRunId === activeRunId && liveWorkflow
      ? liveWorkflow
      : selectedRunDetail?.workflow_snapshot || null;
  const workflowNodes = buildWorkflowNodeSummaries(displayedWorkflow);
  const userFallback = user?.username?.slice(0, 1) || 'U';

  const reloadRuns = useCallback(async () => {
    const response = await supervisorApi.list(projectIdNum);
    setRuns(response.items);
    return response.items;
  }, [projectIdNum]);

  const reloadSelectedRun = useCallback(
    async (runId?: number | null) => {
      const targetId = runId ?? selectedRunId;
      if (!targetId) return null;
      const detail = await supervisorApi.get(projectIdNum, targetId);
      setSelectedRunDetail(detail);
      return detail;
    },
    [projectIdNum, selectedRunId],
  );

  useEffect(() => {
    if (isNaN(projectIdNum)) return;

    Promise.all([
      projectsApi.get(projectIdNum).catch(() => null),
      supervisorApi.list(projectIdNum).then((response) => response.items).catch(() => []),
    ]).then(([projectResponse, runItems]) => {
      setProject(projectResponse);
      setRuns(runItems);
      const persistedRunId = loadPersistedRunId(projectIdNum);
      setSelectedRunId((current) =>
        resolveInitialSupervisorRunId(runItems, current ?? persistedRunId)
      );
      setLoading(false);
    });
  }, [projectIdNum]);

  useEffect(() => {
    if (isNaN(projectIdNum) || typeof window === 'undefined') return;
    const storageKey = getSupervisorSelectionStorageKey(projectIdNum);
    if (selectedRunId == null) {
      window.localStorage.removeItem(storageKey);
      return;
    }
    window.localStorage.setItem(storageKey, String(selectedRunId));
  }, [projectIdNum, selectedRunId]);

  useEffect(() => {
    if (!selectedRunId || isNaN(projectIdNum)) {
      setSelectedRunDetail(null);
      return;
    }

    supervisorApi
      .get(projectIdNum, selectedRunId)
      .then((detail) => {
        setSelectedRunDetail(detail);
        setWorkflowProfile(detail.workflow_profile);
        setAutoRun(detail.auto_run);
        setHumanReview(detail.hitl_enabled);
      })
      .catch(() => {
        setSelectedRunDetail(null);
      });
  }, [selectedRunId, projectIdNum]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [liveEntries, selectedRunDetail?.final_result]);

  useEffect(() => {
    const sessionId = selectedRunDetail?.supervisor_session_id;
    if (!sessionId || selectedRunDetail.status !== 'waiting_review') {
      if (selectedRunId !== activeRunId) {
        setHitl(null);
      }
      return;
    }

    supervisorApi
      .state(sessionId)
      .then((state: SupervisorInterruptStateResponse) => {
        if (!state.interrupt) return;
        setHitl({
          sessionId,
          toolName: state.interrupt.tool_name || 'unknown',
          toolCallId: '',
          arguments: state.interrupt.arguments || {},
          availableActions: ['approve', 'reject'],
          context: state.interrupt.context || {},
        });
        if (state.workflow) {
          setLiveWorkflow(state.workflow);
        }
      })
      .catch(() => {
        // ignore
      });
  }, [selectedRunDetail, selectedRunId, activeRunId]);

  const handleNewRun = useCallback(() => {
    setSelectedRunId(null);
    setSelectedRunDetail(null);
    setInputValue('');
    setLiveEntries([]);
    setLiveWorkflow(null);
    setHitl(null);
  }, []);

  const upsertRunSummary = useCallback(
    (
      workflowId: number,
      sessionId: string,
      requestText: string,
      status: string,
      finalResult?: string | null,
    ) => {
      const now = new Date().toISOString();
      setRuns((prev) => {
        const existing = prev.find((run) => run.id === workflowId);
        const nextItem: SupervisorWorkflowSummaryResponse = existing
          ? {
              ...existing,
              status,
              final_result: finalResult ?? existing.final_result,
              supervisor_session_id: sessionId,
              updated_at: now,
            }
          : {
              id: workflowId,
              project_id: projectIdNum,
              owner_id: user?.id || 0,
              supervisor_session_id: sessionId,
              user_request: requestText,
              model,
              status,
              workflow_profile: workflowProfile,
              auto_run: autoRun,
              active_node_key: null,
              loop_count: 0,
              total_tokens: 0,
              final_result: finalResult ?? null,
              error_message: null,
              hitl_enabled: humanReview,
              review_nodes: null,
              completed_at: null,
              created_at: now,
              updated_at: now,
            };
        return [nextItem, ...prev.filter((run) => run.id !== workflowId)];
      });
    },
    [autoRun, humanReview, model, projectIdNum, user?.id, workflowProfile],
  );

  const handleStartSupervisor = useCallback(async () => {
    if (!inputValue.trim() || isStreaming || isResuming) return;

    const userRequest = inputValue.trim();
    let startedWorkflowId: number | null = null;
    let startedSessionId: string | null = null;

    setIsStreaming(true);
    setInputValue('');
    setHitl(null);
    setLiveEntries([]);
    setLiveWorkflow(null);

    try {
      const response = await supervisorApi.start(projectIdNum, userRequest, {
        model,
        maxLoop,
        workflowProfile,
        autoRun,
        humanReview,
      });
      if (!response.ok) {
        throw new Error(`Supervisor request failed: ${response.status}`);
      }

      await readSupervisorSSEStream(response, (event: SupervisorSSEEvent) => {
        if (event.type === 'supervisor_started') {
          startedWorkflowId = event.workflow_id;
          startedSessionId = event.supervisor_session_id;
          setActiveRunId(event.workflow_id);
          setSelectedRunId(event.workflow_id);
          upsertRunSummary(
            event.workflow_id,
            event.supervisor_session_id,
            userRequest,
            event.status,
          );
          return;
        }

        if (event.type === 'interrupt') {
          const interruptSessionId = event.session_id || startedSessionId || '';
          setHitl({
            sessionId: interruptSessionId,
            toolName: event.tool_name,
            toolCallId: event.tool_call_id,
            arguments: event.arguments,
            availableActions: event.available_actions,
            context: event.context,
          });
          if (startedWorkflowId && interruptSessionId) {
            upsertRunSummary(
              startedWorkflowId,
              interruptSessionId,
              userRequest,
              'waiting_review',
            );
          }
        }

        if (event.type === 'supervisor_done') {
          setLiveWorkflow(event.workflow);
          startedSessionId = event.supervisor_session_id;
          if (startedWorkflowId) {
            upsertRunSummary(
              startedWorkflowId,
              event.supervisor_session_id,
              userRequest,
              'completed',
              event.final_result,
            );
          }
        }

        if (event.type === 'error' && startedWorkflowId && startedSessionId) {
          upsertRunSummary(
            startedWorkflowId,
            startedSessionId,
            userRequest,
            'failed',
          );
        }

        if (event.type !== 'supervisor_started') {
          setLiveEntries((prev) => appendSupervisorDisplayEvent(prev, event));
        }
      });

      const refreshedRuns = await reloadRuns();
      const finalRunId =
        startedWorkflowId ??
        refreshedRuns.find((run) => run.supervisor_session_id === startedSessionId)?.id ??
        null;
      if (finalRunId != null) {
        setSelectedRunId(finalRunId);
        await reloadSelectedRun(finalRunId);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知错误';
      setLiveEntries((prev) =>
        appendSupervisorDisplayEvent(prev, { type: 'error', error: message })
      );
    } finally {
      setIsStreaming(false);
    }
  }, [
    autoRun,
    humanReview,
    inputValue,
    isResuming,
    isStreaming,
    maxLoop,
    model,
    projectIdNum,
    reloadRuns,
    reloadSelectedRun,
    upsertRunSummary,
    workflowProfile,
  ]);

  const handleResume = useCallback(
    async (action: 'approve' | 'reject') => {
      const sessionId = hitl?.sessionId || selectedRunDetail?.supervisor_session_id;
      if (!sessionId || !selectedRunId || isResuming) return;

      setIsResuming(true);
      setIsStreaming(true);
      setHitl(null);
      setLiveEntries([]);

      try {
        const response = await supervisorApi.resume(sessionId, action);
        if (!response.ok) {
          throw new Error(`Resume request failed: ${response.status}`);
        }

        await readSupervisorSSEStream(response, (event: SupervisorSSEEvent) => {
          if (event.type === 'interrupt') {
            setHitl({
              sessionId: event.session_id,
              toolName: event.tool_name,
              toolCallId: event.tool_call_id,
              arguments: event.arguments,
              availableActions: event.available_actions,
              context: event.context,
            });
            upsertRunSummary(
              selectedRunId,
              event.session_id,
              selectedRunDetail?.user_request || '',
              'waiting_review',
            );
          }

          if (event.type === 'supervisor_done') {
            setLiveWorkflow(event.workflow);
            upsertRunSummary(
              selectedRunId,
              event.supervisor_session_id,
              selectedRunDetail?.user_request || '',
              'completed',
              event.final_result,
            );
          }

          if (event.type === 'error') {
            upsertRunSummary(
              selectedRunId,
              sessionId,
              selectedRunDetail?.user_request || '',
              'failed',
            );
          }

          setLiveEntries((prev) => appendSupervisorDisplayEvent(prev, event));
        });

        await reloadRuns();
        await reloadSelectedRun(selectedRunId);
      } catch (error) {
        const message = error instanceof Error ? error.message : '未知错误';
        setLiveEntries((prev) =>
          appendSupervisorDisplayEvent(prev, { type: 'error', error: message })
        );
      } finally {
        setIsResuming(false);
        setIsStreaming(false);
      }
    },
    [
      hitl,
      isResuming,
      reloadRuns,
      reloadSelectedRun,
      selectedRunDetail,
      selectedRunId,
      upsertRunSummary,
    ],
  );

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
        { label: 'AI Supervisor' },
      ]}
    >
      <div className="flex h-[calc(100vh-4rem)] w-full min-h-0 overflow-hidden">
        <ResizablePanelGroup direction="horizontal">
          <ResizablePanel defaultSize={18} minSize={14} maxSize={35} className="bg-card flex flex-col min-h-0">
            <div className="p-3 shrink-0 border-b border-border">
              <Button
                className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
                onClick={handleNewRun}
                disabled={isStreaming}
              >
                <Plus className="h-4 w-4 mr-2" />
                新建运行
              </Button>
            </div>

            <ScrollArea className="flex-1 min-h-0">
              <div className="p-2 space-y-1">
                {runs.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <WandSparkles className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">暂无 Supervisor 运行</p>
                    <p className="text-[10px] mt-1">在下方输入创作意图并启动</p>
                  </div>
                )}

                {runs.map((run) => (
                  <button
                    key={run.id}
                    onClick={() => setSelectedRunId(run.id)}
                    className={cn(
                      'w-full text-left p-3 rounded-lg transition-colors',
                      selectedRunId === run.id
                        ? 'bg-primary/10 border border-primary/30'
                        : 'hover:bg-secondary/50'
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <GitBranch className="h-4 w-4 text-primary shrink-0" />
                          <span className="font-medium text-foreground text-sm line-clamp-2">
                            {run.user_request}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <Badge
                            variant="outline"
                            className={cn('text-[10px]', getStatusBadgeClass(run.status))}
                          >
                            {run.status}
                          </Badge>
                          {run.total_tokens > 0 && (
                            <Badge variant="outline" className="text-[10px] border-border">
                              <Zap className="h-2.5 w-2.5 mr-0.5" />
                              {formatTokens(run.total_tokens)}
                            </Badge>
                          )}
                        </div>
                      </div>
                      <span className="text-[10px] text-muted-foreground shrink-0">
                        {formatTime(run.updated_at)}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </ScrollArea>
          </ResizablePanel>

          <ResizableHandle withHandle />

          <ResizablePanel defaultSize={54} minSize={32} className="flex flex-col min-h-0 bg-background">
            <div className="h-14 shrink-0 border-b border-border px-6 flex items-center justify-between bg-card">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <WandSparkles className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <h2 className="font-medium text-foreground text-sm">
                    {selectedRun?.user_request || 'AI Supervisor'}
                  </h2>
                  <p className="text-[10px] text-muted-foreground">
                    动态编排专家 Agent，并流式展示 `call_sub_agent`
                  </p>
                </div>
              </div>
              {selectedRun && (
                <Badge variant="outline" className={cn('text-xs', getStatusBadgeClass(selectedRun.status))}>
                  {selectedRun.status}
                </Badge>
              )}
            </div>

            <ScrollArea className="flex-1 min-h-0 p-6">
              <div className="max-w-3xl mx-auto space-y-4">
                {!selectedRunId && !isStreaming && (
                  <div className="text-center py-12">
                    <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                      <WandSparkles className="h-8 w-8 text-primary" />
                    </div>
                    <h3 className="text-xl font-semibold text-foreground mb-2">
                      AI Supervisor 工作台
                    </h3>
                    <p className="text-muted-foreground mb-6 max-w-md mx-auto">
                      从一个创意开始，让 Supervisor 调度大纲、剧本、分镜等专家 Agent。
                    </p>
                  </div>
                )}

                {(selectedRunDetail?.user_request || inputValue) && (
                  <div className="flex gap-4 flex-row-reverse">
                    <Avatar className="h-8 w-8 shrink-0">
                      <AvatarFallback className="bg-primary text-primary-foreground">
                        {userFallback}
                      </AvatarFallback>
                    </Avatar>
                    <div className="text-right max-w-[80%]">
                      <div className="inline-block rounded-2xl px-4 py-3 bg-primary text-primary-foreground rounded-tr-sm">
                        <p className="text-sm whitespace-pre-wrap leading-relaxed">
                          {selectedRunDetail?.user_request || '新的 Supervisor 请求'}
                        </p>
                      </div>
                      {selectedRunDetail?.created_at && (
                        <div className="flex justify-end mt-1">
                          <span className="text-[10px] text-muted-foreground">
                            {formatTime(selectedRunDetail.created_at)}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {liveEntries.map((entry) => (
                  <SupervisorEntryCard key={entry.id} entry={entry} />
                ))}

                {!liveEntries.length && selectedRunDetail?.final_result && (
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
                            {selectedRunDetail.final_result}
                          </ReactMarkdown>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {hitl && (
                  <div className="flex gap-4">
                    <div className="h-8 w-8 shrink-0 rounded-full bg-yellow-500/10 flex items-center justify-center">
                      <ShieldAlert className="h-4 w-4 text-yellow-500" />
                    </div>
                    <div className="flex-1 rounded-2xl rounded-tl-sm border border-yellow-500/30 bg-yellow-500/5 px-4 py-3 space-y-3">
                      <div>
                        <p className="text-sm font-medium text-foreground">Supervisor 暂停等待审批</p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          即将执行工具 <span className="font-mono font-medium text-yellow-600">{hitl.toolName}</span>
                        </p>
                      </div>
                      {Object.keys(hitl.arguments).length > 0 && (
                        <pre className="text-xs text-muted-foreground bg-background/60 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
                          {JSON.stringify(hitl.arguments, null, 2)}
                        </pre>
                      )}
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={() => handleResume('approve')}
                          disabled={isResuming}
                          className="bg-green-600 hover:bg-green-700 text-white h-8 px-3 text-xs"
                        >
                          {isResuming ? (
                            <Loader2 className="h-3 w-3 animate-spin mr-1" />
                          ) : (
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                          )}
                          批准
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleResume('reject')}
                          disabled={isResuming}
                          className="border-destructive/40 text-destructive hover:bg-destructive/10 h-8 px-3 text-xs"
                        >
                          {isResuming ? (
                            <Loader2 className="h-3 w-3 animate-spin mr-1" />
                          ) : (
                            <XCircle className="h-3 w-3 mr-1" />
                          )}
                          拒绝
                        </Button>
                      </div>
                    </div>
                  </div>
                )}

                {isStreaming && !liveEntries.length && (
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

            <div className="shrink-0 border-t border-border p-4 bg-card">
              <div className="max-w-3xl mx-auto space-y-3">
                <div className="rounded-2xl border border-border bg-secondary/50 p-3">
                  <Textarea
                    value={inputValue}
                    onChange={(event) => setInputValue(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault();
                        handleStartSupervisor();
                      }
                    }}
                    placeholder="输入一个创作意图，让 Supervisor 协调子 Agent 开始工作..."
                    disabled={isStreaming || isResuming}
                    className="min-h-24 border-0 bg-transparent px-0 py-0 focus-visible:ring-0"
                  />
                </div>
                <div className="flex items-center justify-between gap-3">
                  <p className="text-[10px] text-muted-foreground">
                    Supervisor 会优先调用 `get_workflow_state` 和 `call_sub_agent` 来推进工作流。
                  </p>
                  <Button
                    onClick={handleStartSupervisor}
                    disabled={!inputValue.trim() || isStreaming || isResuming}
                    className="rounded-full bg-primary text-primary-foreground hover:bg-primary/90"
                  >
                    {isStreaming ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <Send className="h-4 w-4 mr-2" />
                    )}
                    启动 Supervisor
                  </Button>
                </div>
              </div>
            </div>
          </ResizablePanel>

          <ResizableHandle withHandle />

          <ResizablePanel defaultSize={28} minSize={20} maxSize={42} className="bg-card flex flex-col min-h-0">
            <div className="p-4 border-b border-border">
              <h3 className="font-medium text-foreground text-sm flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" />
                运行信息
              </h3>
            </div>

            <ScrollArea className="flex-1 min-h-0">
              <div className="p-4 space-y-4">
                <div className="space-y-2">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">状态</p>
                  <div className="flex items-center gap-2">
                    <div className={cn(
                      'h-2 w-2 rounded-full',
                      isStreaming ? 'bg-yellow-500 animate-pulse' : 'bg-green-500'
                    )} />
                    <span className="text-sm text-foreground">
                      {isStreaming ? '运行中' : selectedRun?.status || '空闲'}
                    </span>
                  </div>
                </div>

                <div className="space-y-2">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Supervisor 配置</p>
                  <div className="space-y-3">
                    <div>
                      <label className="text-xs text-muted-foreground mb-1 block">模型</label>
                      <select
                        value={model}
                        onChange={(event) => setModel(event.target.value)}
                        disabled={isStreaming}
                        className="w-full text-xs bg-secondary border border-border rounded-md px-2 py-1.5 text-foreground focus:outline-none focus:border-primary/50 disabled:opacity-50"
                      >
                        <option value="gemini-3-flash-preview">Gemini 3 Flash Preview</option>
                        <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground mb-1 block">Workflow Profile</label>
                      <select
                        value={workflowProfile}
                        onChange={(event) => setWorkflowProfile(event.target.value)}
                        disabled={isStreaming}
                        className="w-full text-xs bg-secondary border border-border rounded-md px-2 py-1.5 text-foreground focus:outline-none focus:border-primary/50 disabled:opacity-50"
                      >
                        <option value="default">default</option>
                        <option value="cinematic_series">cinematic_series</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground mb-1 block">Max Loop</label>
                      <Input
                        type="number"
                        min={1}
                        max={100}
                        value={maxLoop}
                        onChange={(event) => setMaxLoop(Number(event.target.value || 30))}
                        disabled={isStreaming}
                        className="h-8 text-xs"
                      />
                    </div>
                    <ToggleRow
                      label="自动继续"
                      description="按建议自动调度下一个专家 Agent"
                      checked={autoRun}
                      onChange={() => setAutoRun((value) => !value)}
                    />
                    <ToggleRow
                      label="人工审阅"
                      description="在 call_sub_agent 前进入审批"
                      checked={humanReview}
                      onChange={() => setHumanReview((value) => !value)}
                    />
                  </div>
                </div>

                {selectedRun && (
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">运行元数据</p>
                    <div className="bg-secondary/50 rounded-lg p-3 space-y-2">
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Run ID</span>
                        <span className="font-medium text-foreground">{selectedRun.id}</span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Session</span>
                        <span className="font-mono text-foreground truncate max-w-[140px]">
                          {selectedRun.supervisor_session_id}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Tokens</span>
                        <span className="font-medium text-foreground">{formatTokens(selectedRun.total_tokens)}</span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Active Node</span>
                        <span className="font-medium text-foreground">{selectedRun.active_node_key || '-'}</span>
                      </div>
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Workflow 节点</p>
                  {workflowNodes.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-border px-3 py-4 text-xs text-muted-foreground">
                      暂无 workflow 快照
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {workflowNodes.map((node) => (
                        <div key={node.key} className="rounded-lg border border-border bg-background/60 p-3 space-y-2">
                          <div className="flex items-center justify-between gap-2">
                            <div>
                              <p className="text-sm font-medium text-foreground">{node.label}</p>
                              <p className="text-[10px] text-muted-foreground">{node.key}</p>
                            </div>
                            <Badge
                              variant="outline"
                              className={cn('text-[10px]', getStatusBadgeClass(node.status))}
                            >
                              {node.status}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                            <span>v{node.version}</span>
                            <span>{node.lastAgent || 'no-agent'}</span>
                          </div>
                          {node.outputPreview && (
                            <p className="text-xs text-muted-foreground whitespace-pre-wrap break-words">
                              {node.outputPreview}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </ScrollArea>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </AppLayout>
  );
}

function ToggleRow({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label className="flex items-center justify-between cursor-pointer gap-3">
      <div>
        <p className="text-xs text-foreground">{label}</p>
        <p className="text-[10px] text-muted-foreground">{description}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={onChange}
        className={cn(
          'relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent transition-colors',
          checked ? 'bg-primary' : 'bg-secondary'
        )}
      >
        <span
          className={cn(
            'pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform',
            checked ? 'translate-x-4' : 'translate-x-0'
          )}
        />
      </button>
    </label>
  );
}

function SupervisorEntryCard({
  entry,
}: {
  entry: SupervisorDisplayEntry;
}) {
  if (entry.kind === 'thinking') {
    return (
      <div className="flex gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-muted text-muted-foreground">
            <Bot className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
        <div className="max-w-[80%]">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            {entry.source || 'supervisor'} 思考中
          </div>
          <div className="rounded-xl px-4 py-3 bg-muted/50 border border-border text-sm text-muted-foreground italic whitespace-pre-wrap">
            {entry.content}
          </div>
        </div>
      </div>
    );
  }

  if (entry.kind === 'text') {
    return (
      <div className="flex gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-primary/10 text-primary">
            <Brain className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
        <div className="max-w-[80%]">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="text-[10px] border-primary/20 text-primary">
              {entry.source || 'supervisor'}
            </Badge>
          </div>
          <div className="inline-block rounded-2xl px-4 py-3 bg-card border border-border rounded-tl-sm">
            <div className="prose prose-custom prose-sm dark:prose-invert max-w-none break-words">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {entry.content || ''}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (entry.kind === 'tool_start' || entry.kind === 'tool_end') {
    return (
      <div className="flex gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-primary/10 text-primary">
            <Wrench className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
        <div className="max-w-[80%] w-full rounded-lg border border-primary/10 bg-primary/5 px-4 py-3 space-y-2">
          <div className="flex items-center gap-2">
            {entry.kind === 'tool_start' ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
            ) : (
              <Wrench className="h-3.5 w-3.5 text-primary" />
            )}
            <span className="text-sm font-medium text-foreground">{entry.toolName}</span>
            <Badge variant="outline" className={cn('text-[10px]', getStatusBadgeClass(entry.kind === 'tool_start' ? 'running' : entry.isError ? 'error' : 'completed'))}>
              {entry.kind === 'tool_start' ? '执行中' : entry.isError ? '错误' : '完成'}
            </Badge>
          </div>
          {entry.toolArguments && Object.keys(entry.toolArguments).length > 0 && (
            <pre className="text-xs text-muted-foreground bg-background/60 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
              {JSON.stringify(entry.toolArguments, null, 2)}
            </pre>
          )}
          {entry.kind === 'tool_end' && entry.result != null && (
            <pre className={cn(
              'text-xs bg-background/60 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all',
              entry.isError ? 'text-destructive' : 'text-muted-foreground'
            )}>
              {typeof entry.result === 'string'
                ? entry.result
                : JSON.stringify(entry.result, null, 2)}
            </pre>
          )}
        </div>
      </div>
    );
  }

  if (entry.kind === 'sub_agent_start' || entry.kind === 'sub_agent_end') {
    return (
      <div className="flex gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-primary/10 text-primary">
            <Sparkles className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
        <div className="max-w-[80%] w-full rounded-lg border border-primary/10 bg-primary/5 px-4 py-3 space-y-2">
          <div className="flex items-center gap-2">
            {entry.kind === 'sub_agent_start' ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
            ) : (
              <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
            )}
            <span className="text-sm font-medium text-foreground">
              {entry.subAgentName}
            </span>
            <Badge
              variant="outline"
              className={cn(
                'text-[10px]',
                getStatusBadgeClass(entry.kind === 'sub_agent_start' ? 'running' : 'completed')
              )}
            >
              {entry.kind === 'sub_agent_start' ? '启动' : '完成'}
            </Badge>
          </div>
          {entry.taskDescription && (
            <p className="text-xs text-muted-foreground whitespace-pre-wrap break-words">
              {entry.taskDescription}
            </p>
          )}
          {entry.kind === 'sub_agent_end' && entry.result != null && (
            <pre className="text-xs text-muted-foreground bg-background/60 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
              {typeof entry.result === 'string'
                ? entry.result
                : JSON.stringify(entry.result, null, 2)}
            </pre>
          )}
        </div>
      </div>
    );
  }

  if (entry.kind === 'review_start' || entry.kind === 'review_end') {
    return (
      <div className="flex gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-yellow-500/10 text-yellow-600">
            <ShieldAlert className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
        <div className="max-w-[80%] w-full rounded-lg border border-yellow-500/20 bg-yellow-500/5 px-4 py-3 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-foreground">
              Reviewer · {entry.subAgentName}
            </span>
            {entry.kind === 'review_end' && (
              <Badge
                variant="outline"
                className={cn('text-[10px]', getStatusBadgeClass(entry.passed ? 'completed' : 'error'))}
              >
                {entry.passed ? '通过' : '未通过'}
              </Badge>
            )}
          </div>
          {entry.criteria && (
            <p className="text-xs text-muted-foreground">
              Criteria: {entry.criteria.join(' / ')}
            </p>
          )}
          {entry.feedback && (
            <p className="text-xs text-muted-foreground whitespace-pre-wrap break-words">
              {entry.feedback}
            </p>
          )}
        </div>
      </div>
    );
  }

  if (entry.kind === 'interrupt') {
    return (
      <div className="flex gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-yellow-500/10 text-yellow-600">
            <ShieldAlert className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
        <div className="max-w-[80%] w-full rounded-lg border border-yellow-500/20 bg-yellow-500/5 px-4 py-3">
          <p className="text-sm font-medium text-foreground">等待人工审阅</p>
          <p className="text-xs text-muted-foreground mt-1">
            工具 <span className="font-mono text-yellow-600">{entry.toolName}</span> 正在等待审批
          </p>
        </div>
      </div>
    );
  }

  if (entry.kind === 'done') {
    return (
      <div className="flex gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-green-500/10 text-green-600">
            <CheckCircle2 className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
        <div className="max-w-[80%] w-full rounded-lg border border-green-500/20 bg-green-500/5 px-4 py-3">
          <p className="text-sm font-medium text-foreground">Supervisor 运行完成</p>
          {entry.finalResult && (
            <div className="prose prose-custom prose-sm dark:prose-invert max-w-none break-words mt-2">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {entry.finalResult}
              </ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-4">
      <Avatar className="h-8 w-8 shrink-0">
        <AvatarFallback className="bg-destructive/10 text-destructive">
          <XCircle className="h-4 w-4" />
        </AvatarFallback>
      </Avatar>
      <div className="max-w-[80%] w-full rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3">
        <p className="text-sm font-medium text-foreground">运行错误</p>
        <p className="text-xs text-muted-foreground mt-1 whitespace-pre-wrap break-words">
          {entry.content}
        </p>
      </div>
    </div>
  );
}
