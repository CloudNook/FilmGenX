'use client';

import { use, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
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
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { SubAgentResultCard } from '@/components/supervisor/sub-agent-result-card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import {
  appendSupervisorDisplayEvent,
  buildSupervisorDecisionEntry,
  buildSupervisorDisplayEntries,
  buildSupervisorUserEntry,
  buildWorkflowNodeSummaries,
  resolveInitialSupervisorRunId,
  type SupervisorDisplayEntry,
} from '@/lib/supervisor-display';
import {
  Activity,
  Bot,
  Brain,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
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

type TimelineBlock =
  | {
      kind: 'entry';
      id: string;
      entry: SupervisorDisplayEntry;
    }
  | {
      kind: 'sub_session';
      id: string;
      sessionId: string;
      source: string;
      title: string;
      entries: SupervisorDisplayEntry[];
    };

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

function stripResolvedInterruptEntries(entries: SupervisorDisplayEntry[]) {
  return entries
    .filter((entry) => entry.kind !== 'interrupt')
    .map((entry) =>
      entry.pendingApproval
        ? {
            ...entry,
            pendingApproval: false,
          }
        : entry
    );
}

function AutoCollapseDetails({
  entryId,
  autoCollapse,
  summary,
  children,
}: {
  entryId: string;
  autoCollapse: boolean;
  summary?: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(!autoCollapse);

  return (
    <Collapsible
      key={`${entryId}-${autoCollapse ? 'collapsed' : 'open'}`}
      open={open}
      onOpenChange={setOpen}
      className="space-y-2"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] text-muted-foreground">
          {open ? '详情已展开' : (summary || '详情已折叠')}
        </span>
        <CollapsibleTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-[11px] text-muted-foreground"
          >
            {open ? (
              <ChevronDown className="mr-1 h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="mr-1 h-3.5 w-3.5" />
            )}
            {open ? '收起' : '展开'}
          </Button>
        </CollapsibleTrigger>
      </div>
      <CollapsibleContent className="space-y-2">
        {children}
      </CollapsibleContent>
    </Collapsible>
  );
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

  const messageScrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const shouldStickToBottomRef = useRef(true);

  const selectedRun =
    runs.find((run) => run.id === selectedRunId) || null;
  const shouldUseLiveState =
    (isStreaming || isResuming) &&
    liveEntries.length > 0 &&
    (
      activeRunId == null ||
      selectedRunId == null ||
      selectedRunId === activeRunId
    );
  const displayedWorkflow =
    shouldUseLiveState && liveWorkflow
      ? liveWorkflow
      : selectedRunDetail?.workflow_snapshot || null;
  const persistedEntries = useMemo(() => {
    const entries = buildSupervisorDisplayEntries(selectedRunDetail?.event_history || []);
    if (!selectedRunDetail?.user_request) {
      return entries;
    }
    return [
      buildSupervisorUserEntry(selectedRunDetail.user_request, {
        id: `initial-user-${selectedRunDetail.id}`,
        timestamp: selectedRunDetail.created_at,
      }),
      ...entries,
    ];
  }, [selectedRunDetail]);
  const displayedEntries =
    shouldUseLiveState && liveEntries.length > 0
      ? liveEntries
      : persistedEntries;
  const visibleEntries = useMemo(() => {
    if (selectedRunDetail?.status === 'waiting_review') {
      if (hitl) {
        return displayedEntries.filter((entry) => entry.kind !== 'interrupt');
      }
      return displayedEntries;
    }
    return stripResolvedInterruptEntries(displayedEntries);
  }, [displayedEntries, hitl, selectedRunDetail?.status]);
  const timelineBlocks = useMemo<TimelineBlock[]>(() => {
    const blocks: TimelineBlock[] = [];
    const sessionIndex = new Map<string, number>();

    for (const entry of visibleEntries) {
      const sessionId = entry.sessionId;
      if (!sessionId?.startsWith('sub-')) {
        blocks.push({
          kind: 'entry',
          id: `entry-${entry.id}`,
          entry,
        });
        continue;
      }

      const blockIndex = sessionIndex.get(sessionId);
      if (blockIndex == null) {
        blocks.push({
          kind: 'sub_session',
          id: `sub-session-${sessionId}`,
          sessionId,
          source: entry.source || 'sub-agent',
          title: entry.subAgentName || entry.source || sessionId,
          entries: [entry],
        });
        sessionIndex.set(sessionId, blocks.length - 1);
        continue;
      }

      const block = blocks[blockIndex];
      if (block.kind !== 'sub_session') {
        continue;
      }
      block.entries.push(entry);
      if (
        (!block.title || block.title === block.source || block.title === block.sessionId) &&
        entry.subAgentName
      ) {
        block.title = entry.subAgentName;
      }
    }

    return blocks;
  }, [visibleEntries]);

  // 主对话只展示 supervisor 自己的 entry；sub-agent 的内部活动（thinking / text /
  // review_*）走右侧抽屉。用户点 supervisor 的 call_sub_agent tool_end 也能看到
  // 结构化输出（Phase 1），抽屉里则是它的 play-by-play 完整过程。
  const mainBlocks = useMemo(
    () => timelineBlocks.filter((b) => b.kind !== 'sub_session'),
    [timelineBlocks],
  );
  const subSessionBlocks = useMemo(
    () =>
      timelineBlocks.filter(
        (b): b is Extract<TimelineBlock, { kind: 'sub_session' }> =>
          b.kind === 'sub_session',
      ),
    [timelineBlocks],
  );
  const hasAssistantEntries = useMemo(
    () => visibleEntries.some((entry) => entry.kind !== 'user'),
    [visibleEntries],
  );
  const lastEntrySignature = useMemo(() => {
    const lastEntry = visibleEntries[visibleEntries.length - 1];
    if (!lastEntry) {
      return selectedRunDetail?.final_result || '';
    }
    return JSON.stringify({
      id: lastEntry.id,
      kind: lastEntry.kind,
      content: lastEntry.content,
      finalResult: lastEntry.finalResult,
      result: lastEntry.result,
      toolName: lastEntry.toolName,
      timestamp: lastEntry.timestamp,
    });
  }, [selectedRunDetail?.final_result, visibleEntries]);
  const workflowNodes = buildWorkflowNodeSummaries(displayedWorkflow);
  const userFallback = user?.username?.slice(0, 1) || 'U';

  const getMessageViewport = useCallback(() => {
    return messageScrollAreaRef.current?.querySelector(
      '[data-slot="scroll-area-viewport"]'
    ) as HTMLDivElement | null;
  }, []);

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
      setRuns((prev) =>
        prev.map((run) =>
          run.id === detail.id
            ? {
                ...run,
                status: detail.status,
                active_node_key: detail.active_node_key,
                loop_count: detail.loop_count,
                total_tokens: detail.total_tokens,
                final_result: detail.final_result,
                error_message: detail.error_message,
                completed_at: detail.completed_at,
                updated_at: detail.updated_at,
              }
            : run
        )
      );
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
    if (!selectedRunId || isStreaming || isResuming) return;
    if (activeRunId != null && selectedRunId === activeRunId) return;
    if (
      selectedRunDetail?.status !== 'running' &&
      selectedRunDetail?.status !== 'waiting_review'
    ) {
      return;
    }

    const timer = window.setInterval(() => {
      void reloadRuns();
      void reloadSelectedRun(selectedRunId);
    }, 3000);

    return () => window.clearInterval(timer);
  }, [
    activeRunId,
    isResuming,
    isStreaming,
    reloadRuns,
    reloadSelectedRun,
    selectedRunDetail?.status,
    selectedRunId,
  ]);

  useEffect(() => {
    const viewport = getMessageViewport();
    if (!viewport) return;

    const handleScroll = () => {
      const distanceToBottom =
        viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight;
      shouldStickToBottomRef.current = distanceToBottom < 96;
    };

    handleScroll();
    viewport.addEventListener('scroll', handleScroll, { passive: true });
    return () => viewport.removeEventListener('scroll', handleScroll);
  }, [getMessageViewport, selectedRunId]);

  useEffect(() => {
    if (!shouldUseLiveState && selectedRunDetail?.status !== 'waiting_review') {
      return;
    }
    if (!shouldStickToBottomRef.current) {
      return;
    }
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [
    lastEntrySignature,
    selectedRunDetail?.final_result,
    selectedRunDetail?.status,
    shouldUseLiveState,
  ]);

  useEffect(() => {
    const sessionId = selectedRunDetail?.supervisor_session_id;
    if (!sessionId || selectedRunDetail.status !== 'waiting_review') {
      setHitl(null);
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

  const applyLocalRunStatus = useCallback(
    (
      workflowId: number,
      sessionId: string,
      requestText: string,
      status: 'completed' | 'failed',
      finalResult?: string | null,
    ) => {
      const now = new Date().toISOString();
      upsertRunSummary(workflowId, sessionId, requestText, status, finalResult);
      setSelectedRunDetail((prev) => {
        if (!prev || prev.id !== workflowId) {
          return prev;
        }
        return {
          ...prev,
          status,
          final_result: finalResult ?? prev.final_result,
          completed_at: status === 'completed' ? now : prev.completed_at,
          updated_at: now,
        };
      });
    },
    [upsertRunSummary],
  );

  const handleStartSupervisor = useCallback(async () => {
    if (!inputValue.trim() || isStreaming || isResuming) return;

    const userRequest = inputValue.trim();
    const continuingRun =
      selectedRunId != null &&
      selectedRunDetail != null &&
      !!selectedRunDetail.supervisor_session_id;
    const requestSessionId = continuingRun
      ? selectedRunDetail.supervisor_session_id
      : undefined;
    const runRequestText = continuingRun
      ? selectedRunDetail.user_request
      : userRequest;
    let startedWorkflowId: number | null = null;
    let startedSessionId: string | null = requestSessionId || null;
    let receivedInterrupt = false;
    let receivedTerminalEvent = false;
    let receivedError = false;

    if (selectedRunDetail?.status === 'waiting_review') {
      setLiveEntries((prev) =>
        appendSupervisorDisplayEvent(prev, {
          type: 'error',
          error: '当前 Supervisor 正在等待审批，请先 approve/reject 后再继续对话。',
        })
      );
      return;
    }

    setIsStreaming(true);
    setInputValue('');
    setHitl(null);
    setLiveEntries([
      ...(continuingRun ? displayedEntries : []),
      buildSupervisorUserEntry(userRequest, {
        timestamp: new Date().toISOString(),
      }),
    ]);
    if (continuingRun) {
      setActiveRunId(selectedRunId);
      setLiveWorkflow(displayedWorkflow);
    } else {
      setSelectedRunId(null);
      setSelectedRunDetail(null);
      setActiveRunId(null);
      setLiveWorkflow(null);
    }

    try {
      const response = await supervisorApi.chat(projectIdNum, userRequest, {
        sessionId: requestSessionId,
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
            runRequestText,
            event.status,
          );
          return;
        }

        if (event.type === 'interrupt') {
          receivedInterrupt = true;
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
              runRequestText,
              'waiting_review',
            );
          }
        }

        if (event.type === 'supervisor_done') {
          receivedTerminalEvent = true;
          setLiveWorkflow(event.workflow);
          startedSessionId = event.supervisor_session_id;
          if (startedWorkflowId) {
            upsertRunSummary(
              startedWorkflowId,
              event.supervisor_session_id,
              runRequestText,
              'completed',
              event.final_result,
            );
          }
        }

        if (event.type === 'error' && startedWorkflowId && startedSessionId) {
          receivedError = true;
          upsertRunSummary(
            startedWorkflowId,
            startedSessionId,
            runRequestText,
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
        const detail = await reloadSelectedRun(finalRunId);
        if (
          !receivedInterrupt &&
          !receivedError &&
          !receivedTerminalEvent &&
          detail?.status === 'running'
        ) {
          applyLocalRunStatus(
            finalRunId,
            startedSessionId || detail.supervisor_session_id,
            runRequestText,
            'completed',
            detail.final_result,
          );
        }
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
    displayedEntries,
    displayedWorkflow,
    reloadRuns,
    reloadSelectedRun,
    selectedRunDetail,
    selectedRunId,
    applyLocalRunStatus,
    upsertRunSummary,
    workflowProfile,
  ]);

  const handleResume = useCallback(
    async (action: 'approve' | 'reject') => {
      const sessionId = hitl?.sessionId || selectedRunDetail?.supervisor_session_id;
      if (!sessionId || !selectedRunId || isResuming) return;
      let receivedInterrupt = false;
      let receivedTerminalEvent = false;
      let receivedError = false;

      setIsResuming(true);
      setIsStreaming(true);
      setHitl(null);
      setActiveRunId(selectedRunId);
      setLiveWorkflow(displayedWorkflow);
      setLiveEntries(stripResolvedInterruptEntries(displayedEntries));

      try {
        const response = await supervisorApi.resume(projectIdNum, sessionId, action);
        if (!response.ok) {
          throw new Error(`Resume request failed: ${response.status}`);
        }
        if (action === 'reject') {
          setLiveEntries((prev) => [
            ...prev,
            buildSupervisorDecisionEntry(action, {
              toolName: hitl?.toolName || null,
              timestamp: new Date().toISOString(),
            }),
          ]);
        }

        await readSupervisorSSEStream(response, (event: SupervisorSSEEvent) => {
          if (event.type === 'interrupt') {
            receivedInterrupt = true;
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
            receivedTerminalEvent = true;
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
            receivedError = true;
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
        const detail = await reloadSelectedRun(selectedRunId);
        if (
          !receivedInterrupt &&
          !receivedError &&
          !receivedTerminalEvent &&
          detail?.status === 'running'
        ) {
          applyLocalRunStatus(
            selectedRunId,
            sessionId,
            selectedRunDetail?.user_request || '',
            'completed',
            detail.final_result,
          );
        }
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
      applyLocalRunStatus,
      projectIdNum,
      reloadRuns,
      reloadSelectedRun,
      displayedEntries,
      displayedWorkflow,
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

            <ScrollArea ref={messageScrollAreaRef} className="flex-1 min-h-0 p-6">
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

                {mainBlocks.map((block) => {
                  if (block.kind === 'entry') {
                    return (
                      <SupervisorTimelineEntryCard
                        key={block.id}
                        entry={block.entry}
                        userFallback={userFallback}
                      />
                    );
                  }
                  return null;
                })}

                {!visibleEntries.some((entry) => entry.kind === 'text') &&
                  selectedRunDetail?.final_result && (
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

                {isStreaming && !hasAssistantEntries && (
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
                {subSessionBlocks.length > 0 && (
                  <SubAgentDrawerTrigger
                    sessions={subSessionBlocks}
                    userFallback={userFallback}
                  />
                )}
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

type SubSessionBlock = Extract<TimelineBlock, { kind: 'sub_session' }>;

/**
 * 浮在输入区上方的 sub-agent 活动指示条 + 抽屉。
 *
 * 主对话只展示 supervisor 自己的 entry，sub-agent 的 thinking / text / review
 * 全在右侧抽屉里。指示条显示总数和"运行中"状态，点击展开抽屉看完整 play-by-play。
 */
function SubAgentDrawerTrigger({
  sessions,
  userFallback,
}: {
  sessions: SubSessionBlock[];
  userFallback: string;
}) {
  const [open, setOpen] = useState(false);
  const runningCount = useMemo(
    () =>
      sessions.filter(
        (s) => !s.entries.some((e) => e.kind === 'sub_agent_end'),
      ).length,
    [sessions],
  );
  const completedCount = sessions.length - runningCount;

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <button
          type="button"
          className={cn(
            'flex w-full items-center gap-2 rounded-2xl border bg-secondary/30 px-3 py-2 text-left text-sm transition-colors',
            'hover:bg-secondary/60',
            runningCount > 0
              ? 'border-primary/40'
              : 'border-border',
          )}
        >
          <Sparkles
            className={cn(
              'h-4 w-4 shrink-0',
              runningCount > 0 ? 'text-primary' : 'text-muted-foreground',
            )}
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-foreground">
                {sessions.length} 个 Sub-Agent 活动
              </span>
              {runningCount > 0 && (
                <span className="inline-flex items-center gap-1 text-[11px] text-primary">
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/60" />
                    <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-primary" />
                  </span>
                  {runningCount} 运行中
                </span>
              )}
              {completedCount > 0 && runningCount === 0 && (
                <span className="text-[11px] text-muted-foreground">
                  全部完成
                </span>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground line-clamp-1">
              {sessions
                .map((s) => s.title || s.source || s.sessionId)
                .join(' · ')}
            </p>
          </div>
          <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
        </button>
      </SheetTrigger>
      <SheetContent
        side="right"
        className="w-[min(640px,90vw)] sm:max-w-none flex flex-col gap-0 p-0"
      >
        <SheetHeader className="shrink-0 border-b border-border px-5 py-4">
          <SheetTitle>Sub-Agent 活动</SheetTitle>
          <SheetDescription>
            {sessions.length} 个会话 ·{' '}
            {runningCount > 0
              ? `${runningCount} 运行中 · ${completedCount} 完成`
              : '全部完成'}
          </SheetDescription>
        </SheetHeader>
        <ScrollArea className="flex-1 min-h-0">
          <div className="space-y-4 p-5">
            {sessions.map((s) => (
              <SubAgentSessionCard
                key={s.id}
                title={s.title}
                source={s.source}
                sessionId={s.sessionId}
                entries={s.entries}
                userFallback={userFallback}
              />
            ))}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}

function SubAgentSessionCard({
  title,
  source,
  sessionId,
  entries,
  userFallback,
}: {
  title: string;
  source: string;
  sessionId: string;
  entries: SupervisorDisplayEntry[];
  userFallback: string;
}) {
  const hasCompleted = entries.some((entry) => entry.kind === 'sub_agent_end');
  const hasError = entries.some(
    (entry) =>
      entry.kind === 'error' ||
      (entry.kind === 'tool_end' && entry.isError),
  );
  const waitingReview = entries.some(
    (entry) =>
      entry.kind === 'interrupt' ||
      entry.pendingApproval === true,
  );

  const status: string = hasError
    ? 'failed'
    : waitingReview
      ? 'waiting_review'
      : hasCompleted
        ? 'completed'
        : 'running';
  const statusLabel = hasError
    ? '错误'
    : waitingReview
      ? '等待审批'
      : hasCompleted
        ? '完成'
        : '运行中';

  const latestText = [...entries]
    .reverse()
    .find((entry) => entry.kind === 'text' && entry.content?.trim());
  const preview = latestText?.content?.trim().slice(0, 96);

  const [open, setOpen] = useState(!hasCompleted);
  const hadCompletedRef = useRef(hasCompleted);

  useEffect(() => {
    if (!hadCompletedRef.current && hasCompleted) {
      setOpen(false);
    }
    hadCompletedRef.current = hasCompleted;
  }, [hasCompleted]);

  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      className="rounded-xl border border-border bg-card"
    >
      <CollapsibleTrigger asChild>
        <button
          type="button"
          className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left hover:bg-secondary/30"
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              <span className="text-sm font-medium text-foreground">
                {title}
              </span>
              <Badge
                variant="outline"
                className={cn('text-[10px]', getStatusBadgeClass(status))}
              >
                {statusLabel}
              </Badge>
              <Badge variant="outline" className="text-[10px]">
                {entries.length} 条
              </Badge>
            </div>
            <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
              <span>{source || 'sub-agent'}</span>
              <span>·</span>
              <span className="font-mono">{sessionId}</span>
            </div>
            {preview && (
              <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">
                {preview}
              </p>
            )}
          </div>
          <div className="shrink-0 pt-1 text-muted-foreground">
            {open ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </div>
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent className="border-t border-border px-4 py-3">
        <div className="space-y-3">
          {entries.map((entry) => (
            <SupervisorTimelineEntryCard
              key={`${sessionId}-${entry.id}`}
              entry={entry}
              userFallback={userFallback}
            />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

/*
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function SupervisorEntryCard({
  entry,
  userFallback,
}: {
  entry: SupervisorDisplayEntry;
  userFallback: string;
}) {
  if (entry.kind === 'user') {
    void toolStatusLabel;
    return (
      <div className="flex gap-4 flex-row-reverse">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-primary text-primary-foreground">
            {userFallback}
          </AvatarFallback>
        </Avatar>
        <div className="text-right max-w-[80%]">
          <div className="inline-block rounded-2xl px-4 py-3 bg-primary text-primary-foreground rounded-tr-sm">
            <p className="text-sm whitespace-pre-wrap leading-relaxed">
              {entry.content}
            </p>
          </div>
          {entry.timestamp && (
            <div className="flex justify-end mt-1">
              <span className="text-[10px] text-muted-foreground">
                {formatTime(entry.timestamp)}
              </span>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (entry.kind === 'decision') {
    const isApproved = entry.decisionAction === 'approve';
    return (
      <div className="flex gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback
            className={cn(
              'text-xs',
              isApproved
                ? 'bg-green-500/10 text-green-600'
                : 'bg-orange-500/10 text-orange-600'
            )}
          >
            {isApproved ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
          </AvatarFallback>
        </Avatar>
        <div
          className={cn(
            'max-w-[80%] w-full rounded-lg border px-4 py-3',
            isApproved
              ? 'border-green-500/20 bg-green-500/5'
              : 'border-orange-500/20 bg-orange-500/5'
          )}
        >
          <p className="text-sm font-medium text-foreground">
            {isApproved ? '已批准继续执行' : '已拒绝本次执行'}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            {entry.toolName ? (
              <>
                工具 <span className="font-mono">{entry.toolName}</span>{' '}
                {isApproved ? '已通过人工审批，Supervisor 继续执行。' : '已被人工拒绝。'}
              </>
            ) : isApproved ? (
              '人工审批已通过，Supervisor 继续执行。'
            ) : (
              '人工审批已拒绝。'
            )}
          </p>
          {entry.timestamp && (
            <div className="mt-1">
              <span className="text-[10px] text-muted-foreground">
                {formatTime(entry.timestamp)}
              </span>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (entry.kind === 'thinking') {
    return (
      <div className="flex gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-muted text-muted-foreground">
            <Bot className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
        <div className="max-w-[80%] w-full">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
            {entry.isComplete ? (
              <CheckCircle2 className="h-3 w-3 text-green-600" />
            ) : (
              <Loader2 className="h-3 w-3 animate-spin" />
            )}
            {entry.source || 'supervisor'} {entry.isComplete ? '思考完成' : '思考中'}
          </div>
          <div className="rounded-xl px-4 py-3 bg-muted/50 border border-border text-sm text-muted-foreground italic whitespace-pre-wrap">
            {entry.content}
          </div>
        </div>
      </div>
    );
  }

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
    const toolStatus = entry.pendingApproval
      ? 'waiting_review'
      : entry.kind === 'tool_start'
        ? 'running'
        : entry.isError
          ? 'error'
          : 'completed';
    const autoCollapse =
      entry.kind === 'tool_end' &&
      !entry.pendingApproval &&
      !entry.isError;
    const autoCollapse =
      entry.kind === 'tool_end' &&
      !entry.pendingApproval &&
      !entry.isError;
    const toolStatusLabel = entry.pendingApproval
      ? '等待审批'
      : entry.kind === 'tool_start'
        ? '执行中'
        : entry.isError
          ? '错误'
          : '完成';

    return (
      <div className="flex gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-primary/10 text-primary">
            <Wrench className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
        <div className="max-w-[80%] w-full rounded-lg border border-primary/10 bg-primary/5 px-4 py-3 space-y-2">
          <div className="flex items-center gap-2">
            {entry.pendingApproval ? (
              <ShieldAlert className="h-3.5 w-3.5 text-yellow-600" />
            ) : entry.kind === 'tool_start' ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
            ) : (
              <Wrench className="h-3.5 w-3.5 text-primary" />
            )}
            <span className="text-sm font-medium text-foreground">{entry.toolName}</span>
            <Badge variant="outline" className={cn('text-[10px]', getStatusBadgeClass(toolStatus))}>
              {toolStatusLabel}
            </Badge>
          </div>
          {entry.toolArguments && Object.keys(entry.toolArguments).length > 0 && (
            <pre className="text-xs text-muted-foreground bg-background/60 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
              {JSON.stringify(entry.toolArguments, null, 2)}
            </pre>
          )}
          {entry.kind === 'tool_end' && entry.result != null && (
            entry.toolName === 'call_sub_agent' && !entry.isError ? (
              <SubAgentResultCard
                subAgentName={
                  (entry.toolArguments?.sub_agent_name as string | undefined) ??
                  ''
                }
                result={entry.result}
              />
            ) : (
              <pre
                className={cn(
                  'text-xs bg-background/60 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all',
                  entry.isError ? 'text-destructive' : 'text-muted-foreground'
                )}
              >
                {typeof entry.result === 'string'
                  ? entry.result
                  : JSON.stringify(entry.result, null, 2)}
              </pre>
            )
          )}
        </div>
      </div>
    );
  }

  if (false && (entry.kind === 'tool_start' || entry.kind === 'tool_end')) {
    void entry.pendingApproval;
    const toolStatus = entry.pendingApproval
      ? 'waiting_review'
      : entry.kind === 'tool_start'
        ? 'running'
        : entry.isError
          ? 'error'
          : 'completed';
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const _toolStatusLabel = entry.pendingApproval
      ? '等待审批'
      : entry.kind === 'tool_start'
        ? '执行中'
        : entry.isError
          ? '错误'
          : '完成';
    return (
      <div className="flex gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-primary/10 text-primary">
            <Wrench className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
        <div className="max-w-[80%] w-full rounded-lg border border-primary/10 bg-primary/5 px-4 py-3 space-y-2">
          <div className="flex items-center gap-2">
            {entry.pendingApproval ? (
              <ShieldAlert className="h-3.5 w-3.5 text-yellow-600" />
            ) : entry.kind === 'tool_start' ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
            ) : (
              <Wrench className="h-3.5 w-3.5 text-primary" />
            )}
            <span className="text-sm font-medium text-foreground">{entry.toolName}</span>
            <Badge variant="outline" className={cn('text-[10px]', getStatusBadgeClass(toolStatus))}>
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
    const autoCollapse = entry.kind === 'sub_agent_end';
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
            <SubAgentResultCard
              subAgentName={entry.subAgentName}
              result={entry.result}
            />
          )}
        </div>
      </div>
    );
  }

  if (entry.kind === 'review_start' || entry.kind === 'review_end') {
    const autoCollapse = entry.kind === 'review_end';
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
*/
function SupervisorTimelineEntryCard({
  entry,
  userFallback,
}: {
  entry: SupervisorDisplayEntry;
  userFallback: string;
}) {
  if (entry.kind === 'user') {
    return (
      <div className="flex gap-4 flex-row-reverse">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-primary text-primary-foreground">
            {userFallback}
          </AvatarFallback>
        </Avatar>
        <div className="max-w-[80%] text-right">
          <div className="inline-block rounded-2xl rounded-tr-sm bg-primary px-4 py-3 text-primary-foreground">
            <p className="text-sm whitespace-pre-wrap leading-relaxed">
              {entry.content}
            </p>
          </div>
          {entry.timestamp && (
            <div className="mt-1 flex justify-end">
              <span className="text-[10px] text-muted-foreground">
                {formatTime(entry.timestamp)}
              </span>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (entry.kind === 'decision') {
    const isApproved = entry.decisionAction === 'approve';
    return (
      <div className="flex gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback
            className={cn(
              'text-xs',
              isApproved
                ? 'bg-green-500/10 text-green-600'
                : 'bg-orange-500/10 text-orange-600'
            )}
          >
            {isApproved ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
          </AvatarFallback>
        </Avatar>
        <div
          className={cn(
            'max-w-[80%] w-full rounded-lg border px-4 py-3',
            isApproved
              ? 'border-green-500/20 bg-green-500/5'
              : 'border-orange-500/20 bg-orange-500/5'
          )}
        >
          <p className="text-sm font-medium text-foreground">
            {isApproved ? '已批准继续执行' : '已拒绝本次执行'}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {entry.toolName ? (
              <>
                工具 <span className="font-mono">{entry.toolName}</span>
                {isApproved ? ' 已通过人工审批，Supervisor 继续执行。' : ' 已被人工拒绝。'}
              </>
            ) : isApproved ? (
              '人工审批已通过，Supervisor 继续执行。'
            ) : (
              '人工审批已拒绝。'
            )}
          </p>
          {entry.timestamp && (
            <div className="mt-1">
              <span className="text-[10px] text-muted-foreground">
                {formatTime(entry.timestamp)}
              </span>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (entry.kind === 'thinking') {
    return (
      <div className="flex gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-muted text-muted-foreground">
            <Bot className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
        <div className="max-w-[80%]">
          <div className="mb-1 flex items-center gap-1.5 text-xs text-muted-foreground">
            {entry.isComplete ? (
              <CheckCircle2 className="h-3 w-3 text-green-600" />
            ) : (
              <Loader2 className="h-3 w-3 animate-spin" />
            )}
            {(entry.source || 'supervisor')} {entry.isComplete ? '思考完成' : '思考中'}
          </div>
          <AutoCollapseDetails
            entryId={entry.id}
            autoCollapse={
              entry.kind === 'tool_end' &&
              !entry.pendingApproval &&
              !entry.isError
            }
            summary="思考内容已折叠"
          >
            <div className="rounded-xl border border-border bg-muted/50 px-4 py-3 text-sm italic text-muted-foreground whitespace-pre-wrap">
              {entry.content}
            </div>
          </AutoCollapseDetails>
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
          <div className="mb-1 flex items-center gap-2">
            <Badge variant="outline" className="border-primary/20 text-[10px] text-primary">
              {entry.source || 'supervisor'}
            </Badge>
          </div>
          <div className="inline-block rounded-2xl rounded-tl-sm border border-border bg-card px-4 py-3">
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
    const toolStatus = entry.pendingApproval
      ? 'waiting_review'
      : entry.kind === 'tool_start'
        ? 'running'
        : entry.isError
          ? 'error'
          : 'completed';
    const toolStatusLabel = entry.pendingApproval
      ? '等待审批'
      : entry.kind === 'tool_start'
        ? '执行中'
        : entry.isError
          ? '错误'
          : '完成';

    return (
      <div className="flex gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-primary/10 text-primary">
            <Wrench className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
        <div className="max-w-[80%] w-full space-y-2 rounded-lg border border-primary/10 bg-primary/5 px-4 py-3">
          <div className="flex items-center gap-2">
            {entry.pendingApproval ? (
              <ShieldAlert className="h-3.5 w-3.5 text-yellow-600" />
            ) : entry.kind === 'tool_start' ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
            ) : (
              <Wrench className="h-3.5 w-3.5 text-primary" />
            )}
            <span className="text-sm font-medium text-foreground">{entry.toolName}</span>
            <Badge variant="outline" className={cn('text-[10px]', getStatusBadgeClass(toolStatus))}>
              {toolStatusLabel}
            </Badge>
          </div>
          <AutoCollapseDetails
            entryId={entry.id}
            autoCollapse={
              entry.kind === 'tool_end' &&
              !entry.pendingApproval &&
              !entry.isError
            }
            summary="参数与结果已折叠"
          >
            {entry.toolArguments && Object.keys(entry.toolArguments).length > 0 && (
              <pre className="overflow-x-auto whitespace-pre-wrap break-all rounded bg-background/60 p-2 text-xs text-muted-foreground">
                {JSON.stringify(entry.toolArguments, null, 2)}
              </pre>
            )}
            {entry.kind === 'tool_end' && entry.result != null && (
              entry.toolName === 'call_sub_agent' && !entry.isError ? (
                <SubAgentResultCard
                  subAgentName={
                    (entry.toolArguments?.sub_agent_name as string | undefined) ??
                    ''
                  }
                  result={entry.result}
                />
              ) : (
                <pre
                  className={cn(
                    'overflow-x-auto whitespace-pre-wrap break-all rounded bg-background/60 p-2 text-xs',
                    entry.isError ? 'text-destructive' : 'text-muted-foreground'
                  )}
                >
                  {typeof entry.result === 'string'
                    ? entry.result
                    : JSON.stringify(entry.result, null, 2)}
                </pre>
              )
            )}
          </AutoCollapseDetails>
        </div>
      </div>
    );
  }

  if (entry.kind === 'sub_agent_start' || entry.kind === 'sub_agent_end') {
    const autoCollapse = entry.kind === 'sub_agent_end';
    return (
      <div className="flex gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-primary/10 text-primary">
            <Sparkles className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
        <div className="max-w-[80%] w-full space-y-2 rounded-lg border border-primary/10 bg-primary/5 px-4 py-3">
          <div className="flex items-center gap-2">
            {entry.kind === 'sub_agent_start' ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
            ) : (
              <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
            )}
            <span className="text-sm font-medium text-foreground">{entry.subAgentName}</span>
            <Badge
              variant="outline"
              className={cn(
                'text-[10px]',
                getStatusBadgeClass(entry.kind === 'sub_agent_start' ? 'running' : 'completed')
              )}
            >
              {entry.kind === 'sub_agent_start' ? '执行中' : '完成'}
            </Badge>
          </div>
          <AutoCollapseDetails
            entryId={entry.id}
            autoCollapse={autoCollapse}
            summary="任务说明与结果已折叠"
          >
            {entry.taskDescription && (
              <p className="text-xs text-muted-foreground whitespace-pre-wrap break-words">
                {entry.taskDescription}
              </p>
            )}
            {entry.kind === 'sub_agent_end' && entry.result != null && (
              <SubAgentResultCard
                subAgentName={entry.subAgentName}
                result={entry.result}
              />
            )}
          </AutoCollapseDetails>
        </div>
      </div>
    );
  }

  if (entry.kind === 'review_start' || entry.kind === 'review_end') {
    const autoCollapse = entry.kind === 'review_end';
    return (
      <div className="flex gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-yellow-500/10 text-yellow-600">
            <ShieldAlert className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
        <div className="max-w-[80%] w-full space-y-2 rounded-lg border border-yellow-500/20 bg-yellow-500/5 px-4 py-3">
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
          <AutoCollapseDetails
            entryId={entry.id}
            autoCollapse={autoCollapse}
            summary="评审细节已折叠"
          >
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
          </AutoCollapseDetails>
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
          <p className="mt-1 text-xs text-muted-foreground">
            工具 <span className="font-mono text-yellow-600">{entry.toolName}</span> 正在等待审批
          </p>
        </div>
      </div>
    );
  }

  if (entry.kind === 'done') {
    return null;
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
        <p className="mt-1 whitespace-pre-wrap break-words text-xs text-muted-foreground">
          {entry.content}
        </p>
      </div>
    </div>
  );
}
