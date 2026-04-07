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

  // Sync image_start_url + image_references to backend when ImagePickerDialog confirms
  const syncGroupImageData = useCallback(
    async (refs: ImageRef[], url: string | null) => {
      setSyncingUrl(true);
      try {
        const { shotGroupsApi } = await import('@/lib/api');
        const updated = await shotGroupsApi.update(storyboardId, groupId, {
          image_start_url: url,
          image_references: refs,
        });
        onGroupUpdated?.(updated);
      } catch (err) {
        console.error('同步首帧图数据失败:', err);
      } finally {
        setSyncingUrl(false);
      }
    },
    [storyboardId, groupId, onGroupUpdated],
  );

  // Remove a ref from existingRefs and sync to backend
  const handleRemoveRef = useCallback(
    async (urlToRemove: string) => {
      const nextRefs = (existingRefs || []).filter((r) => r.url !== urlToRemove);
      await syncGroupImageData(nextRefs, imageStartUrl);
    },
    [existingRefs, imageStartUrl, syncGroupImageData],
  );

  // Handle image picker confirm: update local state and persist to backend
  const handleImagePickerConfirm = async (refs: ImageRef[], imgStartUrl: string | null) => {
    setSelectedRefs(refs);
    setImageStartUrl(imgStartUrl);
    setImagePickerOpen(false);
    await syncGroupImageData(refs, imgStartUrl);
  };

  const handleClearImageStart = async () => {
    setImageStartUrl(null);
    await syncGroupImageData(existingRefs || [], null);
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
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto bg-white border border-border [&::-webkit-scrollbar]:hidden" showCloseButton={false} style={{ scrollbarWidth: 'none' }}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Wand2 className="h-4 w-4 text-primary" />
            首帧图生成
            <Badge variant="outline" className="text-xs">
              {groupCode}
            </Badge>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
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
              {/* ── 上一组尾帧描述 ── */}
              {prevGroupEndState !== undefined && (
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                    <Link2 className="h-3 w-3" />
                    上一组尾帧参考（生成当前组首帧时引用）
                  </label>
                  <Textarea
                    value={endFrameDesc}
                    onChange={(e) => setEndFrameDesc(e.target.value)}
                    placeholder="描述上一组尾帧画面状态：角色位置、表情、光照..."
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
                  </div>
                </div>
              )}

              <Separator />

              {/* ── 参考图 + 首帧图 并排布局 ── */}
              <div className="grid grid-cols-2 gap-3">
                {/* 左侧：基础参考图 */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-muted-foreground">基础参考图</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-5 text-xs px-1"
                      onClick={() => setImagePickerOpen(true)}
                      disabled={isGenerating}
                    >
                      <Camera className="h-3 w-3 mr-0.5" />
                      {(existingRefs || []).length > 0
                        ? `${(existingRefs || []).length} 张`
                        : '选择'}
                    </Button>
                  </div>
                  {(existingRefs || []).length > 0 ? (
                    <div className="grid grid-cols-3 gap-1">
                      {(existingRefs || []).map((ref, i) => (
                        <div key={`${ref.url}-${i}`} className="relative group">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={ref.url}
                            alt={ref.label || `ref-${i}`}
                            className="aspect-video w-full rounded border border-border object-cover"
                          />
                          <button
                            onClick={() => handleRemoveRef(ref.url)}
                            className="absolute top-0.5 right-0.5 bg-black/60 text-white rounded-full h-4 w-4 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity text-[10px]"
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <button
                      onClick={() => setImagePickerOpen(true)}
                      className="w-full h-14 rounded border border-dashed border-border flex items-center justify-center text-xs text-muted-foreground hover:border-primary hover:text-primary transition-colors"
                    >
                      + 选择参考图
                    </button>
                  )}
                </div>

                {/* 右侧：首帧图 */}
                <div className="space-y-1.5">
                  <span className="text-xs font-medium text-muted-foreground flex items-center justify-between">
                    首帧图
                    {syncingUrl && (
                      <span className="flex items-center gap-1 text-muted-foreground">
                        <Loader2 className="h-3 w-3 animate-spin" />
                      </span>
                    )}
                  </span>
                  {imageStartUrl ? (
                    <div className="relative group">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={imageStartUrl}
                        alt="首帧图"
                        className="aspect-video w-full rounded border border-border object-cover"
                      />
                      <button
                        onClick={handleClearImageStart}
                        className="absolute top-0.5 right-0.5 bg-black/60 text-white rounded-full h-4 w-4 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity text-[10px]"
                      >
                        ×
                      </button>
                      <span className="absolute bottom-1 left-1 bg-black/60 text-white text-[10px] px-1 rounded">
                        首帧
                      </span>
                    </div>
                  ) : (
                    <div className="aspect-video rounded border border-dashed border-border flex items-center justify-center text-xs text-muted-foreground">
                      在左侧选择星标图
                    </div>
                  )}
                </div>
              </div>

              <Separator />

              {/* ── 图生图提示词 ── */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-muted-foreground">图生图提示词</label>
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
                  rows={3}
                  className="text-xs font-mono"
                  disabled={isGenerating}
                />
                {framePlan.frame_description && (
                  <p className="text-xs text-muted-foreground">
                    画面描述：{framePlan.frame_description}
                  </p>
                )}
              </div>

              {/* ── 机位 / 光效 ── */}
              {(framePlan.camera_notes || framePlan.lighting_notes) && (
                <div className="grid grid-cols-2 gap-2">
                  {framePlan.camera_notes && (
                    <div className="rounded bg-muted/50 p-2">
                      <span className="text-[10px] text-muted-foreground block mb-0.5">机位</span>
                      <p className="text-xs">{framePlan.camera_notes}</p>
                    </div>
                  )}
                  {framePlan.lighting_notes && (
                    <div className="rounded bg-muted/50 p-2">
                      <span className="text-[10px] text-muted-foreground block mb-0.5">光效</span>
                      <p className="text-xs">{framePlan.lighting_notes}</p>
                    </div>
                  )}
                </div>
              )}

              {/* ── 负向提示词 ── */}
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">负向提示词</label>
                <Input
                  value={negativePrompt}
                  onChange={(e) => setNegativePrompt(e.target.value)}
                  placeholder="不想出现的元素（可选）"
                  className="text-xs h-8"
                  disabled={isGenerating}
                />
              </div>

              {/* ── 生成参数横向 ── */}
              <div className="flex items-end gap-3">
                <div className="flex-1">
                  <label className="text-xs text-muted-foreground block mb-1">画幅</label>
                  <select
                    value={aspectRatio}
                    onChange={(e) => setAspectRatio(e.target.value)}
                    className="w-full h-8 rounded border border-input bg-background px-2 text-xs"
                    disabled={isGenerating}
                  >
                    <option value="1:1">1:1</option>
                    <option value="16:9">16:9</option>
                    <option value="9:16">9:16</option>
                    <option value="4:3">4:3</option>
                    <option value="3:4">3:4</option>
                  </select>
                </div>
                <div className="flex-1">
                  <label className="text-xs text-muted-foreground block mb-1">分辨率</label>
                  <select
                    value={resolution}
                    onChange={(e) => setResolution(e.target.value)}
                    className="w-full h-8 rounded border border-input bg-background px-2 text-xs"
                    disabled={isGenerating}
                  >
                    <option value="512">512px</option>
                    <option value="1K">1K</option>
                    <option value="2K">2K</option>
                    <option value="4K">4K</option>
                  </select>
                </div>
                <div className="flex-1">
                  <label className="text-xs text-muted-foreground block mb-1">风格</label>
                  <select
                    value={stylePreset}
                    onChange={(e) => setStylePreset(e.target.value)}
                    className="w-full h-8 rounded border border-input bg-background px-2 text-xs"
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

              {/* ── 生成结果 / 错误 ── */}
              {isDone && imageStartUrl && (
                <div className="space-y-1">
                  <span className="text-xs font-medium text-success flex items-center gap-1">
                    <Check className="h-3 w-3" />
                    首帧图已生成
                  </span>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={imageStartUrl}
                    alt="生成的首帧图"
                    className="w-full rounded border border-border object-cover aspect-video"
                  />
                </div>
              )}

              {genState === 'error' && errorMsg && (
                <div className="flex items-center gap-2 rounded bg-destructive/10 text-destructive p-2 text-xs">
                  <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                  {errorMsg}
                </div>
              )}
            </>
          )}
        </div>

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
              生成完成
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
  );

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
