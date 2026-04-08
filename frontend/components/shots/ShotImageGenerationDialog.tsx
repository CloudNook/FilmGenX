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
import { ImagePickerDialog } from '@/components/shots/ImagePickerDialog';
import {
  Loader2,
  Wand2,
  Check,
  Camera,
  AlertCircle,
  X,
} from 'lucide-react';
import {
  shotsApi,
  tasksApi,
  type ImageRef,
  type ShotResponse,
  type TaskResponse,
} from '@/lib/api';

interface ShotImageGenerationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  shot: ShotResponse;
  storyboardId: number;
  projectId: number;
  onShotUpdated: (shot: ShotResponse) => void;
}

type GenerationState = 'idle' | 'generating' | 'done' | 'error';

const STYLE_PRESETS = [
  { value: 'intense', label: 'intense（热血战斗）' },
  { value: 'anime', label: 'anime（通用动漫）' },
  { value: 'cinematic', label: 'cinematic（电影感）' },
  { value: 'realistic', label: 'realistic（写实）' },
  { value: 'sketch', label: 'sketch（手绘）' },
];

export function ShotImageGenerationDialog({
  open,
  onOpenChange,
  shot,
  storyboardId,
  projectId,
  onShotUpdated,
}: ShotImageGenerationDialogProps) {
  // User-editable fields
  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [aspectRatio, setAspectRatio] = useState('16:9');
  const [resolution, setResolution] = useState('1K');
  const [stylePreset, setStylePreset] = useState('cinematic');
  const [selectedRefs, setSelectedRefs] = useState<ImageRef[]>([]);

  // Generation state
  const [genState, setGenState] = useState<GenerationState>('idle');
  const [taskId, setTaskId] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Image picker dialog
  const [imagePickerOpen, setImagePickerOpen] = useState(false);

  // Initialize from shot data when dialog opens
  useEffect(() => {
    if (open) {
      setPrompt(shot.image_prompt || '');
      setNegativePrompt(shot.negative_prompt || '');
      setStylePreset(shot.style_preset || 'cinematic');
      setSelectedRefs(shot.reference_images ? [...shot.reference_images] : []);
      setGenState('idle');
      setErrorMsg(null);
      setTaskId(null);
    }
  }, [open, shot]);

  // Poll task while generating
  useEffect(() => {
    if (!taskId || genState !== 'generating') return;

    const interval = setInterval(async () => {
      try {
        const task: TaskResponse = await tasksApi.get(taskId);

        if (task.status === 'completed') {
          setGenState('done');
          clearInterval(interval);

          // Refresh the shot to get updated generated_images
          const refreshed = await shotsApi.get(storyboardId, shot.id);
          onShotUpdated(refreshed);
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
  }, [taskId, genState, storyboardId, shot.id, onShotUpdated]);

  // Save reference images to shot immediately
  const saveReferenceImages = useCallback(
    async (refs: ImageRef[]) => {
      try {
        const updated = await shotsApi.update(storyboardId, shot.id, {
          reference_images: refs,
        });
        onShotUpdated(updated);
      } catch (err) {
        console.error('保存参考图失败:', err);
      }
    },
    [storyboardId, shot.id, onShotUpdated],
  );

  // Handle image picker confirm
  const handleImagePickerConfirm = async (refs: ImageRef[]) => {
    setSelectedRefs(refs);
    setImagePickerOpen(false);
    await saveReferenceImages(refs);
  };

  // Remove a single ref
  const handleRemoveRef = async (urlToRemove: string) => {
    const nextRefs = selectedRefs.filter((r) => r.url !== urlToRemove);
    setSelectedRefs(nextRefs);
    await saveReferenceImages(nextRefs);
  };

  const handleGenerate = async () => {
    setGenState('generating');
    setErrorMsg(null);

    try {
      const refUrls = selectedRefs.map((r) => r.url);

      const task: TaskResponse = await tasksApi.triggerImage({
        project_id: projectId,
        shot_id: shot.id,
        prompt: prompt || '',
        negative_prompt: negativePrompt || undefined,
        aspect_ratio: aspectRatio,
        resolution,
        style_preset: stylePreset || undefined,
        reference_image_urls: refUrls.length > 0 ? refUrls : undefined,
        save_to_shot: true,
      });

      setTaskId(task.id);
    } catch (err) {
      setGenState('error');
      setErrorMsg(err instanceof Error ? err.message : '提交生成任务失败');
    }
  };

  const handleClose = () => {
    if (genState === 'generating') return;
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
              图像生成
              <Badge variant="outline" className="text-xs">
                {shot.shot_code}
              </Badge>
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {/* ── 参考图 ── */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground">参考图（可选，用于图生图）</label>
              {selectedRefs.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {selectedRefs.map((ref, i) => (
                    <div
                      key={`${ref.url}-${i}`}
                      className="relative w-16 h-16 rounded-md overflow-hidden border border-border group"
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={ref.url}
                        alt={ref.label || ref.name || `参考图 ${i + 1}`}
                        className="w-full h-full object-cover"
                      />
                      <button
                        className="absolute top-0.5 right-0.5 w-4 h-4 bg-black/60 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={() => handleRemoveRef(ref.url)}
                      >
                        <X className="h-2.5 w-2.5 text-white" />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">未选择参考图，将使用纯文字生图。</p>
              )}
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs"
                onClick={() => setImagePickerOpen(true)}
                disabled={isGenerating}
              >
                <Camera className="h-3 w-3 mr-1" />
                {selectedRefs.length > 0 ? '修改参考图' : '选择参考图'}
              </Button>
            </div>

            {/* ── 提示词 ── */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">图像提示词</label>
              <Textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="输入图像生成提示词（英文）"
                rows={4}
                className="text-xs font-mono"
                disabled={isGenerating}
              />
            </div>

            {/* ── 负面提示词 ── */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">负面提示词</label>
              <Input
                value={negativePrompt}
                onChange={(e) => setNegativePrompt(e.target.value)}
                placeholder="不想出现的元素（可选）"
                className="text-xs h-8"
                disabled={isGenerating}
              />
            </div>

            {/* ── 生成参数 ── */}
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
            {isDone && (
              <div className="space-y-1">
                <span className="text-xs font-medium text-green-600 flex items-center gap-1">
                  <Check className="h-3 w-3" />
                  图像已生成，可在右侧属性面板查看
                </span>
              </div>
            )}

            {genState === 'error' && errorMsg && (
              <div className="rounded bg-destructive/10 px-3 py-2 text-xs text-destructive flex items-center gap-1">
                <AlertCircle className="h-3 w-3 shrink-0" />
                {errorMsg}
              </div>
            )}

            {isGenerating && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                生成中，请稍候...
              </div>
            )}
          </div>

          <DialogFooter className="mt-4 gap-2">
            <Button variant="outline" onClick={handleClose} disabled={isGenerating}>
              {isDone ? '关闭' : '取消'}
            </Button>
            <Button onClick={handleGenerate} disabled={!canGenerate || !prompt.trim()}>
              {isGenerating ? (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              ) : (
                <Wand2 className="h-4 w-4 mr-1" />
              )}
              {isGenerating ? '生成中...' : isDone ? '重新生成' : '生成图像'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Image Picker for reference images */}
      <ImagePickerDialog
        open={imagePickerOpen}
        onOpenChange={setImagePickerOpen}
        projectId={projectId}
        existingRefs={selectedRefs}
        existingImageStartUrl={null}
        onConfirm={handleImagePickerConfirm}
      />
    </>
  );
}
