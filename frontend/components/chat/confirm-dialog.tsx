'use client';

import type { EpisodeOutline } from '@/lib/api';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, Loader2, Film, Clock, MapPin } from 'lucide-react';

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  outline: EpisodeOutline | null;
  isConfirming: boolean;
  onConfirm: () => void;
}

const priorityLabels: Record<string, string> = { S: 'S 级', A: 'A 级', B: 'B 级', C: 'C 级' };

export function ConfirmDialog({
  open,
  onOpenChange,
  outline,
  isConfirming,
  onConfirm,
}: ConfirmDialogProps) {
  if (!outline) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-success" />
            确认剧本大纲
          </DialogTitle>
          <DialogDescription>
            确认后将自动创建分集并生成分镜脚本，此操作不可撤销。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <div className="flex items-center justify-between">
            <h4 className="font-medium">{outline.title}</h4>
            <Badge>{priorityLabels[outline.priority] || outline.priority}</Badge>
          </div>

          {outline.theme && (
            <p className="text-sm text-warning">{outline.theme}</p>
          )}

          <p className="text-sm text-muted-foreground line-clamp-3">{outline.synopsis}</p>

          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="font-medium">{outline.estimated_duration_sec}秒</span>
            </div>
            <div className="flex items-center gap-1">
              <Film className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="font-medium">{outline.storyboard_shot_count} 镜头</span>
            </div>
            {outline.primary_location && (
              <div className="flex items-center gap-1 col-span-2">
                <MapPin className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="font-medium">{outline.primary_location}</span>
              </div>
            )}
          </div>

          {(outline.characters || []).length > 0 && (
            <div className="flex flex-wrap gap-1">
              {outline.characters.map((char) => (
                <Badge key={char} variant="outline" className="text-xs">{char}</Badge>
              ))}
            </div>
          )}

          {outline.story_arc && (
            <p className="text-xs text-muted-foreground italic">{outline.story_arc}</p>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isConfirming}>
            取消
          </Button>
          <Button onClick={onConfirm} disabled={isConfirming}>
            {isConfirming ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                创建中...
              </>
            ) : (
              <>
                <Film className="h-4 w-4 mr-2" />
                确认并创建分集
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
