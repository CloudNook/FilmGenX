'use client';

import type { ConversationResponse, EpisodeOutline, LLMConfig } from '@/lib/api';
import { OutlineCard } from './outline-card';
import { ConfirmDialog } from './confirm-dialog';
import { WorkflowStepper, type ConvStatus } from './workflow-stepper';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Sparkles,
  FileText,
  CheckCircle2,
  Loader2,
  MessageSquare,
  Film,
  Settings2,
  ArrowRight,
} from 'lucide-react';
import { useState, useCallback } from 'react';

interface ContextPanelProps {
  conv: ConversationResponse | null;
  llmConfig: LLMConfig;
  onLlmConfigChange: (config: LLMConfig) => void;
  isSummarizing: boolean;
  isStreaming: boolean;
  onSummarize: () => void;
  onConfirm: (outline: EpisodeOutline) => Promise<void>;
  onSaveOutline: (outline: EpisodeOutline) => Promise<void>;
  projectId: string;
}

export function ContextPanel({
  conv,
  llmConfig,
  onLlmConfigChange,
  isSummarizing,
  isStreaming,
  onSummarize,
  onConfirm,
  onSaveOutline,
  projectId,
}: ContextPanelProps) {
  const [isEditingOutline, setIsEditingOutline] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);

  const status: ConvStatus = (conv?.status as ConvStatus) || 'active';
  const outline = conv?.latest_outline as EpisodeOutline | null;
  const disabled = isSummarizing || isStreaming;

  const handleSaveOutline = useCallback(
    async (edited: EpisodeOutline) => {
      await onSaveOutline(edited);
      setIsEditingOutline(false);
    },
    [onSaveOutline],
  );

  const handleConfirm = useCallback(async () => {
    if (!outline) return;
    setIsConfirming(true);
    try {
      await onConfirm(outline);
    } finally {
      setIsConfirming(false);
      setConfirmOpen(false);
    }
  }, [outline, onConfirm]);

  return (
    <div className="w-full h-full bg-card flex flex-col min-h-0">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-foreground">创作上下文</h3>
          {conv && (
            <Badge
              variant="outline"
              className={`text-[10px] ${
                status === 'confirmed'
                  ? 'border-success/30 text-success'
                  : status === 'draft_ready'
                    ? 'border-warning/30 text-warning'
                    : 'border-border'
              }`}
            >
              {status === 'confirmed' ? '已确认' : status === 'draft_ready' ? '草稿就绪' : '对话中'}
            </Badge>
          )}
        </div>
        <WorkflowStepper status={status} />
      </div>

      <ScrollArea className="flex-1 min-h-0">
        <div className="p-4 space-y-4">
          {/* ========== ACTIVE STATE ========== */}
          {(status === 'active' || !conv) && (
            <>
              {/* Generate Draft Button */}
              <div>
                <Button
                  className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
                  disabled={disabled || !conv}
                  onClick={onSummarize}
                >
                  {isSummarizing ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      正在生成大纲...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4 mr-2" />
                      生成大纲草稿
                    </>
                  )}
                </Button>
                {conv && (
                  <p className="text-[10px] text-muted-foreground mt-1 text-center">
                    AI 将基于对话内容生成结构化剧本大纲
                  </p>
                )}
              </div>

              {/* Conversation Info */}
              {conv && (
                <div className="p-3 bg-secondary rounded-lg">
                  <p className="text-sm font-medium text-foreground">{conv.title}</p>
                  <p className="text-[10px] text-muted-foreground mt-1">
                    在左侧聊天中讨论小说高光时刻，完成后点击上方生成大纲
                  </p>
                </div>
              )}
            </>
          )}

          {/* ========== DRAFT_READY STATE ========== */}
          {status === 'draft_ready' && outline && (
            <>
              {/* Outline Card */}
              <OutlineCard
                outline={outline}
                isEditing={isEditingOutline}
                onEditStart={() => setIsEditingOutline(true)}
                onSave={handleSaveOutline}
                onCancel={() => setIsEditingOutline(false)}
              />

              <Separator />

              {/* Actions */}
              <div className="space-y-2">
                <Button
                  className="w-full bg-success/90 text-white hover:bg-success"
                  disabled={disabled || isConfirming}
                  onClick={() => setConfirmOpen(true)}
                >
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  确认并创建分集
                </Button>

                <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                  <MessageSquare className="h-3 w-3" />
                  也可以继续在左侧聊天中提出修改意见
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  className="w-full border-border"
                  disabled={disabled}
                  onClick={onSummarize}
                >
                  {isSummarizing ? (
                    <>
                      <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                      重新生成中...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-3 w-3 mr-1" />
                      重新生成大纲
                    </>
                  )}
                </Button>
              </div>

              <ConfirmDialog
                open={confirmOpen}
                onOpenChange={setConfirmOpen}
                outline={outline}
                isConfirming={isConfirming}
                onConfirm={handleConfirm}
              />
            </>
          )}

          {/* ========== CONFIRMED STATE ========== */}
          {status === 'confirmed' && (
            <>
              <div className="p-4 bg-success/10 rounded-lg text-center">
                <CheckCircle2 className="h-8 w-8 text-success mx-auto mb-2" />
                <p className="text-sm font-medium text-foreground">剧本已确认</p>
                <p className="text-[10px] text-muted-foreground mt-1">
                  分集已创建，分镜生成任务已启动
                </p>
              </div>

              {conv?.scene_id && (
                <Button variant="outline" className="w-full border-border" asChild>
                  <a href={`/projects/${projectId}/episodes/${conv.scene_id}`}>
                    <Film className="h-4 w-4 mr-2" />
                    查看分集详情
                    <ArrowRight className="h-3 w-3 ml-auto" />
                  </a>
                </Button>
              )}

              <Button variant="outline" className="w-full border-border" asChild>
                <a href={`/projects/${projectId}/episodes`}>
                  查看所有分集
                  <ArrowRight className="h-3 w-3 ml-auto" />
                </a>
              </Button>
            </>
          )}

          <Separator />

          {/* ========== MODEL CONFIG (always visible) ========== */}
          <div>
            <div className="flex items-center gap-1 mb-2">
              <Settings2 className="h-3 w-3 text-muted-foreground" />
              <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
                模型配置
              </span>
            </div>
            <Select
              value={llmConfig.model}
              onValueChange={(m) => onLlmConfigChange({ ...llmConfig, model: m })}
            >
              <SelectTrigger className="w-full bg-secondary border-border h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="gemini-3-flash-preview">Gemini 3 Flash（快速）</SelectItem>
                <SelectItem value="gemini-3.1-pro-preview">Gemini 3.1 Pro（高质量）</SelectItem>
              </SelectContent>
            </Select>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-[10px] text-muted-foreground">温度</span>
              <input
                type="range"
                min={0}
                max={2}
                step={0.1}
                value={llmConfig.temperature ?? 0.7}
                onChange={(e) =>
                  onLlmConfigChange({ ...llmConfig, temperature: parseFloat(e.target.value) })
                }
                className="flex-1 h-1.5 accent-primary cursor-pointer"
              />
              <span className="text-[10px] text-muted-foreground w-6 text-right">
                {llmConfig.temperature?.toFixed(1)}
              </span>
            </div>
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
