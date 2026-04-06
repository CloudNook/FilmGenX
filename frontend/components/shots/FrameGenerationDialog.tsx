'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ImagePickerDialog } from '@/components/shots/ImagePickerDialog';
import {
  Loader2,
  Wand2,
  ImageIcon,
  Check,
  RefreshCw,
  ExternalLink,
  Camera,
  AlertCircle,
} from 'lucide-react';
import type { ImageRef, FramePlanResponse, TaskResponse, ShotGroupResponse } from '@/lib/api';

interface FrameGenerationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  storyboardId: number;
  groupId: number;
  groupCode: string;
  projectId: number;
  existingImageStartUrl?: string | null;
  existingRefs?: ImageRef[];
  /** 刷新 shot group 列表 */
  onGroupUpdated?: (group: ShotGroupResponse) => void;
}

type GenerationState = 'idle' | 'loading' | 'generating' | 'done' | 'error';

export function FrameGenerationDialog({
  open,
  onOpenChange,
  storyboardId,
  groupId,
  groupCode,
  projectId,
  existingImageStartUrl,
  existingRefs = [],
  onGroupUpdated,
}: FrameGenerationDialogProps) {
  // Frame plan loaded from backend
  const [framePlan, setFramePlan] = useState<FramePlanResponse | null>(null);
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);

  // User-editable fields
  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [aspectRatio, setAspectRatio] = useState('16:9');
  const [resolution, setResolution] = useState('1K');
  const [selectedRefs, setSelectedRefs] = useState<ImageRef[]>([]);
  const [imageStartUrl, setImageStartUrl] = useState<string | null>(null);

  // Generation state
  const [genState, setGenState] = useState<GenerationState>('idle');
  const [taskId, setTaskId] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Image picker dialog
  const [imagePickerOpen, setImagePickerOpen] = useState(false);

  // Load frame plan when dialog opens
  useEffect(() => {
    if (!open) return;
    setLoadingPlan(true);
    setPlanError(null);
    setGenState('idle');
    setErrorMsg(null);

    import('@/lib/api').then(({ shotGroupsApi }) => {
      shotGroupsApi
        .getFramePlan(storyboardId, groupId)
        .then((plan) => {
          setFramePlan(plan);
          if (plan) {
            setPrompt(plan.image_prompt || '');
            setNegativePrompt(plan.negative_prompt || '');
          }
        })
        .catch((err) => {
          setPlanError(err instanceof Error ? err.message : '加载首帧方案失败');
        })
        .finally(() => setLoadingPlan(false));
    });
  }, [open, storyboardId, groupId]);

  // Initialize refs / image start url from existing group data when dialog opens
  useEffect(() => {
    if (open) {
      setSelectedRefs([...existingRefs]);
      setImageStartUrl(existingImageStartUrl ?? null);
    }
  }, [open, existingRefs, existingImageStartUrl]);

  // Poll task while generating
  useEffect(() => {
    if (!taskId || genState !== 'generating') return;

    const interval = setInterval(async () => {
      try {
        const { tasksApi } = await import('@/lib/api');
        const task: TaskResponse = await tasksApi.get(taskId);

        if (task.status === 'completed') {
          setGenState('done');
          clearInterval(interval);

          // Write image_start_url back to shot group
          const resultParams = task.input_params as Record<string, unknown> | null;
          const assetShotGroupId = resultParams?.shot_group_id as number | undefined;

          // Refresh the group to get updated data
          const { shotGroupsApi } = await import('@/lib/api');
          const refreshedGroup = await shotGroupsApi.get(storyboardId, groupId);
          onGroupUpdated?.(refreshedGroup);
        } else if (task.status === 'failed' || task.status === 'cancelled') {
          setGenState('error');
          setErrorMsg(task.error_message || '生成失败');
          clearInterval(interval);
        }
        // else: still generating, keep polling
      } catch {
        // ignore poll errors
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [taskId, genState, storyboardId, groupId, onGroupUpdated]);

  const handleGenerate = async () => {
    setGenState('generating');
    setErrorMsg(null);

    try {
      const { shotGroupsApi } = await import('@/lib/api');
      const refUrls = selectedRefs.map((r) => r.url);

      const task: TaskResponse = await shotGroupsApi.generateFrame(storyboardId, groupId, {
        prompt: prompt || undefined,
        negative_prompt: negativePrompt || undefined,
        aspect_ratio: aspectRatio,
        resolution,
        reference_image_urls: refUrls.length > 0 ? refUrls : undefined,
      });

      setTaskId(task.id);
    } catch (err) {
      setGenState('error');
      setErrorMsg(err instanceof Error ? err.message : '提交生成任务失败');
    }
  };

  const handleImagePickerConfirm = (refs: ImageRef[], imgStartUrl: string | null) => {
    setSelectedRefs(refs);
    setImageStartUrl(imgStartUrl);
    setImagePickerOpen(false);
  };

  const handleClose = () => {
    if (genState === 'generating') return; // prevent accidental close during generation
    onOpenChange(false);
  };

  const canGenerate = genState === 'idle' || genState === 'done' || genState === 'error';
  const isGenerating = genState === 'generating';
  const isDone = genState === 'done';

  return (
    <>
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Wand2 className="h-4 w-4 text-primary" />
              分镜组首帧图生成
              <Badge variant="outline" className="text-xs">
                {groupCode}
              </Badge>
            </DialogTitle>
          </DialogHeader>

          <ScrollArea className="flex-1 min-h-0 pr-2">
            <div className="space-y-4 py-2 pr-2">
              {/* Loading plan */}
              {loadingPlan && (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                  <span className="ml-2 text-sm text-muted-foreground">加载首帧方案...</span>
                </div>
              )}

              {/* Plan error */}
              {planError && (
                <div className="flex items-center gap-2 rounded-md bg-destructive/10 text-destructive p-3 text-sm">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  {planError}
                </div>
              )}

              {/* Frame plan loaded */}
              {framePlan && !loadingPlan && (
                <>
                  {/* Reference images section */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">基础参考图（选填）</span>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs"
                        onClick={() => setImagePickerOpen(true)}
                      >
                        <Camera className="h-3 w-3 mr-1" />
                        {selectedRefs.length > 0
                          ? `已选 ${selectedRefs.length} 张`
                          : '选择参考图'}
                      </Button>
                    </div>

                    {selectedRefs.length > 0 && (
                      <div className="grid grid-cols-4 gap-2">
                        {selectedRefs.map((ref, i) => (
                          <div key={`${ref.url}-${i}`} className="relative group">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                              src={ref.url}
                              alt={ref.label || `ref-${i}`}
                              className="aspect-square w-full rounded-md object-cover border border-border"
                            />
                            <button
                              onClick={() =>
                                setSelectedRefs((prev) => prev.filter((r) => r.url !== ref.url))
                              }
                              className="absolute -top-1 -right-1 bg-destructive text-white rounded-full h-4 w-4 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity text-[10px]"
                            >
                              ×
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {imageStartUrl && (
                      <div className="space-y-1">
                        <span className="text-xs text-muted-foreground">已选首帧图：</span>
                        <div className="relative group">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={imageStartUrl}
                            alt="当前首帧图"
                            className="h-24 w-full rounded-md object-cover border border-border"
                          />
                          <button
                            onClick={() => setImageStartUrl(null)}
                            className="absolute -top-1 -right-1 bg-destructive text-white rounded-full h-4 w-4 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity text-[10px]"
                          >
                            ×
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Prompt */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium">图生图提示词</label>
                      {framePlan.key_elements.length > 0 && (
                        <div className="flex gap-1 flex-wrap">
                          {framePlan.key_elements.slice(0, 3).map((el, i) => (
                            <Badge key={i} variant="secondary" className="text-[10px] h-4 px-1">
                              {el}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                    <Textarea
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      placeholder="输入或修改图生图提示词"
                      rows={4}
                      className="text-xs font-mono"
                      disabled={isGenerating}
                    />
                    {framePlan.frame_description && (
                      <p className="text-xs text-muted-foreground italic">
                        画面描述：{framePlan.frame_description}
                      </p>
                    )}
                  </div>

                  {/* Camera / lighting notes */}
                  {(framePlan.camera_notes || framePlan.lighting_notes) && (
                    <div className="grid grid-cols-2 gap-3">
                      {framePlan.camera_notes && (
                        <div className="rounded-md bg-muted/50 p-2">
                          <span className="text-[10px] font-medium text-muted-foreground block mb-0.5">
                            机位
                          </span>
                          <p className="text-xs">{framePlan.camera_notes}</p>
                        </div>
                      )}
                      {framePlan.lighting_notes && (
                        <div className="rounded-md bg-muted/50 p-2">
                          <span className="text-[10px] font-medium text-muted-foreground block mb-0.5">
                            光效
                          </span>
                          <p className="text-xs">{framePlan.lighting_notes}</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Negative prompt */}
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium">负向提示词</label>
                    <Input
                      value={negativePrompt}
                      onChange={(e) => setNegativePrompt(e.target.value)}
                      placeholder="不想出现的元素（可选）"
                      className="text-xs"
                      disabled={isGenerating}
                    />
                  </div>

                  {/* Generation params */}
                  <div className="flex items-center gap-4">
                    <div className="space-y-1">
                      <label className="text-xs font-medium text-muted-foreground">画幅</label>
                      <select
                        value={aspectRatio}
                        onChange={(e) => setAspectRatio(e.target.value)}
                        className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                        disabled={isGenerating}
                      >
                        <option value="1:1">1:1</option>
                        <option value="16:9">16:9</option>
                        <option value="9:16">9:16</option>
                        <option value="4:3">4:3</option>
                        <option value="3:4">3:4</option>
                      </select>
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs font-medium text-muted-foreground">分辨率</label>
                      <select
                        value={resolution}
                        onChange={(e) => setResolution(e.target.value)}
                        className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                        disabled={isGenerating}
                      >
                        <option value="512">512px</option>
                        <option value="1K">1K</option>
                        <option value="2K">2K</option>
                        <option value="4K">4K</option>
                      </select>
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs font-medium text-muted-foreground">风格</label>
                      <div className="h-8 rounded-md border border-input bg-background px-2 flex items-center text-xs">
                        {framePlan.style_preset}
                      </div>
                    </div>
                  </div>

                  {/* Done state: show result */}
                  {isDone && imageStartUrl && (
                    <div className="space-y-1.5">
                      <span className="text-sm font-medium text-success flex items-center gap-1">
                        <Check className="h-3.5 w-3.5" />
                        首帧图已生成
                      </span>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={imageStartUrl}
                        alt="生成的首帧图"
                        className="w-full rounded-md border border-border object-cover aspect-video"
                      />
                    </div>
                  )}

                  {/* Error state */}
                  {genState === 'error' && errorMsg && (
                    <div className="flex items-center gap-2 rounded-md bg-destructive/10 text-destructive p-3 text-sm">
                      <AlertCircle className="h-4 w-4 shrink-0" />
                      {errorMsg}
                    </div>
                  )}
                </>
              )}
            </div>
          </ScrollArea>

          <DialogFooter className="flex items-center gap-2 pt-2">
            {genState === 'generating' && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground mr-auto">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                生成中，请稍候...
              </div>
            )}
            {genState === 'done' && (
              <div className="flex items-center gap-2 text-sm text-success mr-auto">
                <Check className="h-3.5 w-3.5" />
                生成完成，首帧图已保存
              </div>
            )}
            <Button variant="outline" onClick={handleClose} disabled={isGenerating}>
              {isGenerating ? '生成中...' : isDone ? '关闭' : '取消'}
            </Button>
            {canGenerate && framePlan && !isDone && (
              <Button
                onClick={handleGenerate}
                disabled={!prompt.trim() || isGenerating}
              >
                {isGenerating ? (
                  <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                ) : (
                  <Wand2 className="h-3.5 w-3.5 mr-1" />
                )}
                生成首帧图
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Image picker for reference images */}
      <ImagePickerDialog
        open={imagePickerOpen}
        onOpenChange={setImagePickerOpen}
        projectId={projectId}
        existingRefs={selectedRefs}
        existingImageStartUrl={imageStartUrl}
        onConfirm={handleImagePickerConfirm}
      />
    </>
  );
}
