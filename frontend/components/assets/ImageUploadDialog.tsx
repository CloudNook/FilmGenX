'use client';

import { useRef, useState } from 'react';
import { Loader2, Upload } from 'lucide-react';
import { toast } from 'sonner';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { assetsApi } from '@/lib/api';

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  projectId: number;
  onAssetCreated?: () => void;
}

/**
 * 简化版本的素材上传弹窗。
 *
 * 重构后 assets 表只剩 project_id + asset_code + asset_type + url 这一层，
 * 不再绑定 shot / character / location。所以这里只需选文件 + 调
 * `assetsApi.upload(projectId, file)` 即可，后端按 MIME 推断 asset_type。
 */
export function ImageUploadDialog({ open, onOpenChange, projectId, onAssetCreated }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const reset = () => {
    setFile(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const handleSubmit = async () => {
    if (!file) {
      toast.error('请选择文件');
      return;
    }
    setSubmitting(true);
    try {
      await assetsApi.upload(projectId, file);
      toast.success('上传成功');
      reset();
      onOpenChange(false);
      onAssetCreated?.();
    } catch (err) {
      const msg = err instanceof Error ? err.message : '上传失败';
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!submitting) onOpenChange(v);
        if (!v) reset();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>上传素材</DialogTitle>
          <DialogDescription>
            支持图片 / 视频 / 音频。后端按 MIME 自动归类 asset_type。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <input
            ref={inputRef}
            type="file"
            accept="image/*,video/*,audio/*"
            disabled={submitting}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-primary/10 file:px-3 file:py-1.5 file:text-primary"
          />
          {file && (
            <p className="text-xs text-muted-foreground">
              {file.name} · {(file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={submitting}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={!file || submitting}>
            {submitting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Upload className="mr-2 h-4 w-4" />
            )}
            上传
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
