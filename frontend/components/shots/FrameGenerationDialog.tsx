'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
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
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { ImagePickerDialog } from '@/components/shots/ImagePickerDialog';
import {
  Loader2,
  Wand2,
  Check,
  Camera,
  AlertCircle,
  Link2,
  X,
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
  /** 上一组分镜组的 end_frame_description（供用户参考生成当前组首帧） */
  prevGroupEndState?: string | null;
  /** 刷新 shot group 列表 */
  onGroupUpdated?: (group: ShotGroupResponse) => void;
}

type GenerationState = 'idle' | 'loading' | 'generating' | 'done' | 'error';

const STYLE_PRESETS = [
  { value: 'intense', label: 'intense（热血战斗）' },
  { value: 'anime', label: 'anime（通用动漫）' },
  { value: 'cinematic', label: 'cinematic（电影感）' },
  { value: 'realistic', label: 'realistic（写实）' },
  { value: 'sketch', label: 'sketch（手绘）' },
];

export function FrameGenerationDialog({
  open,
  onOpenChange,
  storyboardId,
  groupId,
  groupCode,
  projectId,
  existingImageStartUrl,
  existingRefs = [],
  prevGroupEndState,
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
  const [stylePreset, setStylePreset] = useState('intense');
  const [selectedRefs, setSelectedRefs] = useState<ImageRef[]>([]);
  const [imageStartUrl, setImageStartUrl] = useState<string | null>(null);
  // 用户可编辑的尾帧描述（来自上一组，供生成当前组首帧时参考）
  const [endFrameDesc, setEndFrameDesc] = useState<string>('');

  // Sync state
  const [syncingUrl, setSyncingUrl] = useState(false);
  const [syncingDesc, setSyncingDesc] = useState(false);

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
            setStylePreset(plan.style_preset || 'intense');
          }
        })
        .catch((err) => {
          setPlanError(err instanceof Error ? err.message : '加载首帧方案失败');
        })
        .finally(() => setLoadingPlan(false));
    });
  }, [open, storyboardId, groupId]);

  // Initialize from existing group data when dialog opens
  useEffect(() => {
    if (open) {
      setSelectedRefs([...existingRefs]);
      setImageStartUrl(existingImageStartUrl ?? null);
      setEndFrameDesc(prevGroupEndState ?? '');
    }
  }, [open, existingRefs, existingImageStartUrl, prevGroupEndState]);

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

          // Refresh the group to get updated data
          const { shotGroupsApi } = await import('@/lib/api');
          const refreshedGroup = await shotGroupsApi.get(storyboardId, groupId);
          onGroupUpdated?.(refreshedGroup);
        } else if (task.status === 'failed' || task.status === 'cancelled') {
          setGenState('error');
          setErrorMsg(task.error_message || '生成失败');
          clearInterval(interval);
        }
      } catch {
        // ignore poll errors
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [taskId, genState, storyboardId, groupId, onGroupUpdated]);

  // Sync image_start_url to backend when user selects/deselects in ImagePickerDialog
  const syncImageStartUrl = useCallback(
    async (url: string | null) => {
      setSyncingUrl(true);
      try {
        const { shotGroupsApi } = await import('@/lib/api');
        const updated = await shotGroupsApi.update(storyboardId, groupId, {
          image_start_url: url,
        });
        onGroupUpdated?.(updated);
      } catch (err) {
        console.error('同步首帧图URL失败:', err);
      } finally {
        setSyncingUrl(false);
      }
    },
    [storyboardId, groupId, onGroupUpdated],
  );

  // Sync end_frame_description to backend (debounced via button)
  const syncEndFrameDesc = useCallback(
    async () => {
      if (syncingDesc) return;
      setSyncingDesc(true);
      try {
        const { shotGroupsApi } = await import('@/lib/api');
        const updated = await shotGroupsApi.update(storyboardId, groupId, {
          end_frame_description: endFrameDesc,
        });
        onGroupUpdated?.(updated);
      } catch (err) {
        console.error('同步尾帧描述失败:', err);
      } finally {
        setSyncingDesc(false);
      }
    },
    [syncingDesc, storyboardId, groupId, endFrameDesc, onGroupUpdated],
  );

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
        style_preset: stylePreset || undefined,
        reference_image_urls: refUrls.length > 0 ? refUrls : undefined,
      });

      setTaskId(task.id);
    } catch (err) {
      setGenState('error');
      setErrorMsg(err instanceof Error ? err.message : '提交生成任务失败');
    }
  };

  const handleImagePickerConfirm = async (refs: ImageRef[], imgStartUrl: string | null) => {
    setSelectedRefs(refs);
    setImageStartUrl(imgStartUrl);
    setImagePickerOpen(false);

    // Write image_start_url to backend immediately so it's ready for video generation
    await syncImageStartUrl(imgStartUrl);
  };

  const handleClearImageStart = async () => {
    setImageStartUrl(null);
    await syncImageStartUrl(null);
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
        <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Wand2 className="h-4 w-4 text-primary" />
              首帧图生成
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

              {/* Dialog content when plan loaded */}
              {framePlan && !loadingPlan && (
                <>
                  {/* ── 上一组尾帧描述（可编辑） ── */}
                  {prevGroupEndState !== undefined && (
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <label className="text-sm font-medium flex items-center gap-1">
                          <Link2 className="h-3 w-3 text-muted-foreground" />
                          上一组尾帧参考
                        </label>
                        <span className="text-xs text-muted-foreground">可编辑，基于此生成当前组首帧</span>
                      </div>
                      <Textarea
                        value={endFrameDesc}
                        onChange={(e) => setEndFrameDesc(e.target.value)}
                        placeholder="描述上一组最后一帧的画面状态，角色位置/表情/光照/构图..."
                        rows={2}
                        className="text-xs"
                        disabled={isGenerating}
                      />
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-6 text-xs"
                          onClick={syncEndFrameDesc}
                          disabled={isGenerating || syncingDesc}
                        >
                          {syncingDesc ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
                          {syncingDesc ? '保存中...' : '保存'}
                        </Button>
                        <span className="text-xs text-muted-foreground">
                          点击保存后，下一组生成首帧时会在提示词中引用此描述
                        </span>
                      </div>
                    </div>
                  )}

                  <Separator />

                  {/* Reference images section */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">基础参考图（选填）</span>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs"
                        onClick={() => setImagePickerOpen(true)}
                        disabled={isGenerating}
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

                    {/* Image start url */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">首帧图：</span>
                        {syncingUrl && (
                          <span className="text-xs text-muted-foreground flex items-center gap-1">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            同步中
                          </span>
                        )}
                      </div>
                      {imageStartUrl ? (
                        <div className="relative group">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={imageStartUrl}
                            alt="当前首帧图"
                            className="h-24 w-full rounded-md object-cover border border-border"
                          />
                          <button
                            onClick={handleClearImageStart}
                            className="absolute -top-1 -right-1 bg-destructive text-white rounded-full h-4 w-4 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity text-[10px]"
                          >
                            ×
                          </button>
                        </div>
                      ) : (
                        <div className="h-24 rounded-md border border-dashed border-border flex items-center justify-center">
                          <span className="text-xs text-muted-foreground">
                            点击上方「选择参考图」中的星标指定首帧图
                          </span>
                        </div>
                      )}
                    </div>
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
                  <div className="flex items-center gap-4 flex-wrap">
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
                      <select
                        value={stylePreset}
                        onChange={(e) => setStylePreset(e.target.value)}
                        className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                        disabled={isGenerating}
                      >
                        {STYLE_PRESETS.map((p) => (
                          <option key={p.value} value={p.value}>
                            {p.label}
                          </option>
                        ))}
                      </select>
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
