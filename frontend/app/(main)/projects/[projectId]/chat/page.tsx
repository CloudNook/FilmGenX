'use client';

import { use, useState, useRef, useEffect, useCallback } from 'react';
import { AppLayout } from '@/components/layout';
import {
  projectsApi,
  conversationsApi,
  readSSEStream,
  type ProjectResponse,
  type ConversationResponse,
  type ConversationDetailResponse,
  type MessageResponse,
  type LLMConfig,
  type EpisodeOutline,
} from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ContextPanel } from '@/components/chat/context-panel';
import { InlineOutlinePreview } from '@/components/chat/inline-outline-preview';
import { WorkflowStepper } from '@/components/chat/workflow-stepper';
import {
  Send,
  Plus,
  Sparkles,
  MessageSquare,
  Trash2,
  Loader2,
  Swords,
  Heart,
  Star,
  FileText,
  CheckCircle2,
  Bot,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// System Prompt — 专注高光时刻剧本生成
// ---------------------------------------------------------------------------

const HIGHLIGHT_SYSTEM_PROMPT = `你是 FilmGenX 的编剧总监助手，专注于为网络小说生成高光时刻动画剧本。

你的核心能力：
1. 分析小说原文，识别最具戏剧张力和视觉表现力的关键场景
2. 将文字转化为结构化的动画分集剧本大纲
3. 为每个高光时刻设计分镜风格、运镜方案和情感节奏

工作流程：
- 与用户讨论小说内容和创作意图
- 根据讨论生成结构化的剧本大纲（EpisodeOutline）
- 根据用户反馈迭代优化大纲
- 用户确认后系统自动创建分集并生成分镜

评分标准（0-10分）：
- dramatic_tension：戏剧张力，情节转折和冲突强度
- visual_potential：视觉表现力，适合动画呈现的程度
- emotional_resonance：情感共鸣，观众代入感
- narrative_importance：叙事重要性，对整体故事的影响
- audience_familiarity：观众熟悉度，原作粉丝期待值

请用中文回复，保持专业但友好的语气。`;

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------

export default function ChatPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const projectIdNum = Number(projectId);
  const { user } = useAuth();

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [conversations, setConversations] = useState<ConversationResponse[]>([]);
  const [selectedConvId, setSelectedConvId] = useState<number | null>(null);
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [loading, setLoading] = useState(true);

  const [llmConfig, setLlmConfig] = useState<LLMConfig>({
    model: 'gemini-3-flash-preview',
    temperature: 0.7,
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Derive current conversation
  const selectedConv = conversations.find((c) => c.id === selectedConvId) || null;
  const convStatus = (selectedConv?.status || 'active') as 'active' | 'draft_ready' | 'confirmed';
  const currentOutline = selectedConv?.latest_outline as EpisodeOutline | null;

  // Load project + conversations
  useEffect(() => {
    if (isNaN(projectIdNum)) return;

    Promise.all([
      projectsApi.get(projectIdNum).catch(() => null),
      conversationsApi.list(projectIdNum).then((r) => r.items).catch(() => []),
    ]).then(([p, convs]) => {
      setProject(p);
      setConversations(convs);
      if (convs.length > 0 && !selectedConvId) {
        setSelectedConvId(convs[0].id);
      }
      setLoading(false);
    });
  }, [projectIdNum]);

  // Load messages when conversation selected
  useEffect(() => {
    if (!selectedConvId || isNaN(projectIdNum)) return;

    conversationsApi
      .get(projectIdNum, selectedConvId)
      .then((detail: ConversationDetailResponse) => {
        setMessages(detail.messages || []);
      })
      .catch(() => setMessages([]));
  }, [selectedConvId, projectIdNum]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);

  // Helper: reload selected conversation
  const reloadConv = useCallback(async () => {
    if (!selectedConvId) return;
    const detail = await conversationsApi.get(projectIdNum, selectedConvId);
    setMessages(detail.messages || []);
    // Update conversation in list
    setConversations((prev) =>
      prev.map((c) => (c.id === selectedConvId ? { ...c, status: detail.status, latest_outline: detail.latest_outline, scene_id: detail.scene_id } : c)),
    );
  }, [selectedConvId, projectIdNum]);

  // Create new conversation
  const handleNewConversation = useCallback(async () => {
    try {
      const conv = await conversationsApi.create(projectIdNum, '新对话');
      setConversations((prev) => [conv, ...prev]);
      setSelectedConvId(conv.id);
    } catch (err) {
      console.error('Failed to create conversation:', err);
    }
  }, [projectIdNum]);

  // Delete conversation
  const handleDeleteConversation = useCallback(
    async (convId: number) => {
      try {
        await conversationsApi.delete(projectIdNum, convId);
        setConversations((prev) => prev.filter((c) => c.id !== convId));
        if (selectedConvId === convId) {
          setSelectedConvId(null);
          setMessages([]);
        }
      } catch (err) {
        console.error('Failed to delete conversation:', err);
      }
    },
    [projectIdNum, selectedConvId],
  );

  // Send message
  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim() || isStreaming || !selectedConvId) return;
    if (convStatus === 'confirmed') return;

    const userContent = inputValue.trim();
    setInputValue('');
    setIsStreaming(true);
    setStreamingText('');

    // Optimistic user message
    const tempUserMsg: MessageResponse = {
      id: -Date.now(),
      conversation_id: selectedConvId,
      role: 'user',
      type: 'text',
      content: userContent,
      outline_data: null,
      seq: messages.length,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const response = await conversationsApi.chat(
        projectIdNum,
        selectedConvId,
        userContent,
        llmConfig,
        HIGHLIGHT_SYSTEM_PROMPT,
      );

      if (!response.ok) throw new Error(`Chat request failed: ${response.status}`);

      let fullText = '';
      await readSSEStream(response, (chunk) => {
        fullText += chunk;
        setStreamingText(fullText);
      });

      await reloadConv();
    } catch (err) {
      console.error('Chat error:', err);
      setMessages((prev) => [
        ...prev,
        {
          id: -Date.now(),
          conversation_id: selectedConvId,
          role: 'assistant',
          type: 'text',
          content: `出错了：${err instanceof Error ? err.message : '未知错误'}`,
          outline_data: null,
          seq: prev.length,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsStreaming(false);
      setStreamingText('');
    }
  }, [inputValue, isStreaming, selectedConvId, projectIdNum, messages.length, llmConfig, convStatus, reloadConv]);

  // Summarize
  const handleSummarize = useCallback(async () => {
    if (!selectedConvId || isSummarizing) return;

    setIsSummarizing(true);
    try {
      const response = await conversationsApi.summarize(
        projectIdNum,
        selectedConvId,
        llmConfig,
        HIGHLIGHT_SYSTEM_PROMPT,
      );

      if (!response.ok) throw new Error(`Summarize failed: ${response.status}`);

      // Read the stream (we don't show it inline, just wait for completion)
      await readSSEStream(response, () => {});

      await reloadConv();
    } catch (err) {
      console.error('Summarize error:', err);
      setMessages((prev) => [
        ...prev,
        {
          id: -Date.now(),
          conversation_id: selectedConvId!,
          role: 'assistant',
          type: 'text',
          content: `生成大纲失败：${err instanceof Error ? err.message : '未知错误'}`,
          outline_data: null,
          seq: prev.length,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsSummarizing(false);
    }
  }, [selectedConvId, isSummarizing, projectIdNum, llmConfig, reloadConv]);

  // Confirm
  const handleConfirm = useCallback(
    async (outline: EpisodeOutline) => {
      if (!selectedConvId) return;
      await conversationsApi.confirm(projectIdNum, selectedConvId, outline, llmConfig, '', outline.storyboard_shot_count);
      await reloadConv();
      // Also reload conversation list to update status badge
      const list = await conversationsApi.list(projectIdNum).then((r) => r.items);
      setConversations(list);
    },
    [selectedConvId, projectIdNum, llmConfig, reloadConv],
  );

  // Save outline edits
  const handleSaveOutline = useCallback(
    async (outline: EpisodeOutline) => {
      if (!selectedConvId) return;
      await conversationsApi.update(projectIdNum, selectedConvId, { latest_outline: outline });
      await reloadConv();
    },
    [selectedConvId, projectIdNum, reloadConv],
  );

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  };

  const userFallback = user?.username?.slice(0, 1) || 'U';

  // Quick start prompts
  const quickStarts = [
    {
      icon: Swords,
      label: '战斗场景',
      desc: '将激烈战斗改编为动画分集',
      prompt: '请帮我分析小说中最精彩的战斗场景，并设计动画分集剧本。重点关注动作设计和视觉冲击力。',
    },
    {
      icon: Heart,
      label: '情感场景',
      desc: '改编感人至深的情感戏',
      prompt: '我想将小说中最感人的场景改编为动画，希望能突出角色内心变化和情感共鸣。',
    },
    {
      icon: Star,
      label: '角色高光',
      desc: '提取角色最精彩的时刻',
      prompt: '请帮我提取主角在小说中最精彩的几个高光时刻，并为每个设计动画剧本大纲。',
    },
  ];

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
        { label: 'AI 对话' },
      ]}
    >
      <div className="flex h-[calc(100vh-4rem)] w-full min-h-0 overflow-hidden">
        {/* ===== Left Sidebar - Conversation List ===== */}
        <div className="w-72 border-r border-border bg-card flex flex-col min-h-0">
          <div className="p-4 shrink-0 border-b border-border">
            <Button
              className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
              onClick={handleNewConversation}
            >
              <Plus className="h-4 w-4 mr-2" />
              新建对话
            </Button>
          </div>

          <ScrollArea className="flex-1 min-h-0">
            <div className="p-2 space-y-1">
            </div>
          </ScrollArea>
        </div>

        {/* ===== Main Chat Area ===== */}
        <div className="flex-1 flex flex-col min-h-0 bg-background">
          {/* Chat Header with Workflow Stepper */}
          <div className="h-14 shrink-0 border-b border-border px-6 flex items-center justify-between bg-card">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Sparkles className="h-4 w-4 text-primary" />
              </div>
              <div>
                <h2 className="font-medium text-foreground text-sm">
                  {selectedConv?.title || 'FilmGenX AI 助手'}
                </h2>
                <p className="text-[10px] text-muted-foreground">高光时刻剧本生成</p>
              </div>
            </div>
            {selectedConv && <WorkflowStepper status={convStatus} />}
          </div>

          {/* Messages */}
          <ScrollArea className="flex-1 min-h-0 p-6">
            <div className="max-w-3xl mx-auto space-y-6">
              {/* ===== Welcome / Onboarding ===== */}
              {!selectedConvId && (
                <div className="text-center py-12">
                  <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                    <Sparkles className="h-8 w-8 text-primary" />
                  </div>
                  <h3 className="text-xl font-semibold text-foreground mb-2">
                    创建高光时刻剧本
                  </h3>
                  <p className="text-muted-foreground mb-6 max-w-md mx-auto">
                    描述您希望改编的小说片段，AI 将帮您设计动画分集
                  </p>
                  <Button onClick={handleNewConversation} className="bg-primary text-primary-foreground">
                    <Plus className="h-4 w-4 mr-2" />
                    新建对话
                  </Button>
                </div>
              )}

              {selectedConvId && messages.length === 0 && !isStreaming && (
                <div className="text-center py-12">
                  <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                    <Sparkles className="h-8 w-8 text-primary" />
                  </div>
                  <h3 className="text-xl font-semibold text-foreground mb-2">
                    描述您的小说高光时刻
                  </h3>
                  <p className="text-muted-foreground mb-6 max-w-md mx-auto">
                    告诉 AI 您想改编哪个片段，可以参考以下模板开始
                  </p>
                  <div className="grid grid-cols-3 gap-3 max-w-lg mx-auto">
                    {quickStarts.map((qs) => (
                      <button
                        key={qs.label}
                        onClick={() => setInputValue(qs.prompt)}
                        className="flex flex-col items-center gap-2 p-4 rounded-xl border border-border hover:border-primary/50 hover:bg-secondary/50 transition-colors text-center"
                      >
                        <qs.icon className="h-6 w-6 text-primary" />
                        <span className="text-sm font-medium text-foreground">{qs.label}</span>
                        <span className="text-[10px] text-muted-foreground">{qs.desc}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* ===== Message List ===== */}
              {messages.map((message) => {
                // System action messages - centered
                if (message.role === 'system') {
                  return (
                    <div key={message.id} className="flex items-center justify-center gap-2 py-2">
                      <Bot className="h-3 w-3 text-muted-foreground" />
                      <span className="text-xs text-muted-foreground">{message.content}</span>
                    </div>
                  );
                }

                // Outline draft - inline preview
                if (message.type === 'outline_draft' && message.outline_data) {
                  return (
                    <div key={message.id} className="max-w-[80%]">
                      <InlineOutlinePreview
                        outline={message.outline_data as unknown as EpisodeOutline}
                      />
                      <div className="mt-1 text-[10px] text-muted-foreground">
                        {formatTime(message.created_at)}
                      </div>
                    </div>
                  );
                }

                // Outline confirmed - green card
                if (message.type === 'outline_confirmed') {
                  return (
                    <div key={message.id} className="max-w-[80%]">
                      <div className="rounded-xl border border-success/30 bg-success/5 p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <CheckCircle2 className="h-4 w-4 text-success" />
                          <Badge className="bg-success/20 text-success border-success/30 text-xs">
                            大纲已确认
                          </Badge>
                        </div>
                        <p className="text-sm text-foreground">{message.content}</p>
                      </div>
                      <div className="mt-1 text-[10px] text-muted-foreground">
                        {formatTime(message.created_at)}
                      </div>
                    </div>
                  );
                }

                // Regular text messages
                return (
                  <div
                    key={message.id}
                    className={`flex gap-4 ${
                      message.role === 'user' ? 'flex-row-reverse' : ''
                    }`}
                  >
                    <Avatar className="h-8 w-8 shrink-0">
                      {message.role === 'user' ? (
                        <AvatarFallback className="bg-primary text-primary-foreground">
                          {userFallback}
                        </AvatarFallback>
                      ) : (
                        <AvatarFallback className="bg-primary/10 text-primary">
                          <Sparkles className="h-4 w-4" />
                        </AvatarFallback>
                      )}
                    </Avatar>
                    <div
                      className={`flex-1 max-w-[80%] ${
                        message.role === 'user' ? 'text-right' : ''
                      }`}
                    >
                      <div
                        className={`inline-block rounded-2xl px-4 py-3 ${
                          message.role === 'user'
                            ? 'bg-primary text-primary-foreground rounded-tr-sm'
                            : 'bg-card border border-border rounded-tl-sm'
                        }`}
                      >
                        <p className="text-sm whitespace-pre-wrap leading-relaxed">
                          {message.content}
                        </p>
                      </div>
                      <div
                        className={`flex items-center gap-2 mt-1 ${
                          message.role === 'user' ? 'justify-end' : ''
                        }`}
                      >
                        <span className="text-[10px] text-muted-foreground">
                          {formatTime(message.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* Streaming Text */}
              {isStreaming && streamingText && (
                <div className="flex gap-4">
                  <Avatar className="h-8 w-8 shrink-0">
                    <AvatarFallback className="bg-primary/10 text-primary">
                      <Sparkles className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="inline-block rounded-2xl px-4 py-3 bg-card border border-border rounded-tl-sm max-w-[80%]">
                    <p className="text-sm whitespace-pre-wrap leading-relaxed">
                      {streamingText}
                      <span className="inline-block w-1.5 h-4 bg-primary animate-pulse ml-0.5 align-middle" />
                    </p>
                  </div>
                </div>
              )}

              {/* Summarizing indicator */}
              {isSummarizing && (
                <div className="flex gap-4">
                  <Avatar className="h-8 w-8 shrink-0">
                    <AvatarFallback className="bg-primary/10 text-primary">
                      <Sparkles className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="inline-block rounded-2xl px-4 py-3 bg-warning/10 border border-warning/30 rounded-tl-sm">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-warning" />
                      <span className="text-sm text-foreground">正在生成剧本大纲...</span>
                      <Loader2 className="h-3 w-3 animate-spin text-warning" />
                    </div>
                  </div>
                </div>
              )}

              {/* Typing Indicator */}
              {isStreaming && !streamingText && (
                <div className="flex gap-4">
                  <Avatar className="h-8 w-8 shrink-0">
                    <AvatarFallback className="bg-primary/10 text-primary">
                      <Sparkles className="h-4 w-4" />
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
                        convStatus === 'confirmed'
                          ? '此对话已确认，请新建对话继续创作'
                          : selectedConvId
                            ? '描述您想改编的小说片段...'
                            : '请先选择或新建一个对话'
                      }
                      disabled={!selectedConvId || isStreaming || convStatus === 'confirmed'}
                      className="flex-1 border-0 bg-transparent focus-visible:ring-0 px-0"
                    />
                  </div>
                </div>
                <Button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim() || isStreaming || !selectedConvId || convStatus === 'confirmed'}
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
                讨论高光时刻 → 生成大纲草稿 → 多轮修改 → 确认剧本
              </p>
            </div>
          </div>
        </div>

        {/* ===== Right Sidebar - Context Panel ===== */}
        <ContextPanel
          conv={selectedConv}
          llmConfig={llmConfig}
          onLlmConfigChange={setLlmConfig}
          isSummarizing={isSummarizing}
          isStreaming={isStreaming}
          onSummarize={handleSummarize}
          onConfirm={handleConfirm}
          onSaveOutline={handleSaveOutline}
          projectId={projectId}
        />
      </div>
    </AppLayout>
  );
}
