'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import {
  Loader2,
  Play,
  Video,
  ImageIcon,
  AlertCircle,
  Wand2,
} from 'lucide-react';
import type { ShotGroupResponse } from '@/lib/api';

interface VideoGenerationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** 当前选中的分镜组（用于 multi-shot） */
  group?: ShotGroupResponse | null;
  /** 当前选中的镜头 ID（用于 single-shot） */
  shotId?: number;
  /** 是否为 multi-shot 模式 */
  mode: 'multi-shot' | 'single-shot';
  onGenerated?: () => void;
}

export function VideoGenerationDialog({
  open,
  onOpenChange,
  group,
  shotId,
  mode,
  onGenerated,
}: VideoGenerationDialogProps) {
  const [quality, setQuality] = useState<'720p' | '1080p'>('1080p');
  const [sound, setSound] = useState<boolean>(true);
  const [useImageStart, setUseImageStart] = useState<boolean>(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasImageStart = !!group?.image_start_url;
  const groupCode = group?.group_code ?? '';
  const shotCount = group?.shots?.length ?? 0;
  const totalDuration = group?.total_duration_sec ?? 0;

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const { tasksApi } = await import('@/lib/api');

      if (mode === 'multi-shot' && group) {
        await tasksApi.triggerMultiShotVideo({
          shot_group_id: group.id,
          quality,
          sound: sound ? 'on' : 'off',
        });
      } else if (mode === 'single-shot' && shotId) {
        await tasksApi.triggerVideo({
          shot_id: shotId,
          quality,
          sound: sound ? 'on' : 'off',
          use_image_start: useImageStart,
        });
      }

      onOpenChange(false);
      onGenerated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : '提交失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Video className="h-4 w-4 text-primary" />
            {mode === 'multi-shot' ? '多镜头视频生成' : '视频生成'}
            {groupCode && (
              <Badge variant="outline" className="text-xs">
                {groupCode}
              </Badge>
            )}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Group info (multi-shot only) */}
          {mode === 'multi-shot' && group && (
            <div className="rounded-md bg-muted/50 p-3 space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">分镜组</span>
                <span className="font-medium">{groupCode}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">镜头数</span>
                <span>{shotCount} 个</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">总时长</span>
                <span>{totalDuration > 0 ? `${totalDuration.toFixed(1)}s` : '-'}</span>
              </div>
            </div>
          )}

          {/* Quality */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">分辨率</label>
            <div className="flex gap-3">
              {(['720p', '1080p'] as const).map((q) => (
                <label
                  key={q}
                  className={`flex-1 flex items-center justify-center gap-2 h-9 rounded-md border cursor-pointer transition-colors text-sm ${
                    quality === q
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border hover:bg-muted/50'
                  }`}
                >
                  <input
                    type="radio"
                    name="quality"
                    value={q}
                    checked={quality === q}
                    onChange={() => setQuality(q)}
                    className="sr-only"
                  />
                  {q}
                </label>
              ))}
            </div>
          </div>

          {/* Sound */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-sm font-medium">音效</Label>
              <p className="text-xs text-muted-foreground">生成视频时附带音效</p>
            </div>
            <Switch
              checked={sound}
              onCheckedChange={(checked) => setSound(!!checked)}
            />
          </div>

          {/* Image start (multi-shot) */}
          {mode === 'multi-shot' && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="text-sm font-medium flex items-center gap-1">
                    <ImageIcon className="h-3 w-3" />
                    首帧图
                  </Label>
                  <p className="text-xs text-muted-foreground">以首帧图作为视频起始帧</p>
                </div>
                <div className="flex items-center gap-2">
                  {hasImageStart ? (
                    <span className="text-xs text-success">已设置</span>
                  ) : (
                    <span className="text-xs text-muted-foreground">未设置</span>
                  )}
                  <Switch
                    checked={useImageStart}
                    onCheckedChange={(checked) => setUseImageStart(!!checked)}
                    disabled={!hasImageStart}
                  />
                </div>
              </div>
              {!hasImageStart && (
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  请先在「首帧图」弹窗中生成首帧图
                </p>
              )}
              {hasImageStart && (
                <div className="relative rounded-md overflow-hidden border border-border">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={group!.image_start_url!}
                    alt="首帧图预览"
                    className="w-full h-24 object-cover"
                  />
                </div>
              )}
            </div>
          )}

          {/* Image start (single-shot) */}
          {mode === 'single-shot' && (
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-sm font-medium flex items-center gap-1">
                  <ImageIcon className="h-3 w-3" />
                  使用首帧图
                </Label>
                <p className="text-xs text-muted-foreground">以首帧图作为视频起始帧</p>
              </div>
              <Switch
                checked={useImageStart}
                onCheckedChange={(checked) => setUseImageStart(!!checked)}
              />
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 rounded-md bg-destructive/10 text-destructive p-3 text-sm">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            取消
          </Button>
          <Button onClick={handleGenerate} disabled={loading}>
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5 mr-1" />
            )}
            开始生成
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
