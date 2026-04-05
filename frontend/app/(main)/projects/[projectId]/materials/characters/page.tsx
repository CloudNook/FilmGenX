'use client';

import { use, useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  charactersApi,
  projectsApi,
  tasksApi,
  type CharacterResponse,
  type CharacterDetailResponse,
  type CharacterVersionResponse,
  type ProjectResponse,
} from '@/lib/api';
import { AppLayout } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Plus,
  Search,
  Trash2,
  Sparkles,
  Users,
  Loader2,
  Upload,
  Image as ImageIcon,
  Wand2,
  Eye,
  ImagePlus,
  X,
  Layers,
  FileImage,
  ArrowRight,
} from 'lucide-react';
import { assetsApi, type AssetResponse } from '@/lib/api';
import { toast } from 'sonner';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const BACKEND_ORIGIN = (() => {
  try {
    return new URL(API_BASE_URL).origin;
  } catch {
    return 'http://localhost:8000';
  }
})();

function normalizeImageUrl(rawUrl: string | null | undefined): string | null {
  if (typeof rawUrl !== 'string') return null;

  let value = rawUrl.trim();
  if (!value || value === 'null' || value === 'undefined') return null;

  if (
    (value.startsWith('[') && value.endsWith(']'))
    || (value.startsWith('"') && value.endsWith('"'))
    || (value.startsWith("'") && value.endsWith("'"))
  ) {
    try {
      const parsed = JSON.parse(value.replace(/^'|'$/g, '"'));
      if (typeof parsed === 'string') {
        value = parsed.trim();
      } else if (Array.isArray(parsed) && typeof parsed[0] === 'string') {
        value = parsed[0].trim();
      }
    } catch {
      value = value.replace(/^['"]|['"]$/g, '').trim();
    }
  }

  if (!value) return null;

  value = value.replace(/\\/g, '/');

  if (/^(blob:|data:|https?:\/\/)/i.test(value)) return value;
  if (value.startsWith('//')) return `https:${value}`;
  if (value.startsWith('/')) return `${BACKEND_ORIGIN}${value}`;

  return `${BACKEND_ORIGIN}/${value.replace(/^\.?\//, '')}`;
}

function normalizeImageUrls(urls: Array<string | null | undefined>): string[] {
  const seen = new Set<string>();

  return urls
    .map((url) => normalizeImageUrl(url))
    .filter((url): url is string => {
      if (!url || seen.has(url)) return false;
      seen.add(url);
      return true;
    });
}

// 图像比例选项
const ASPECT_RATIOS = [
  { value: '2:3', label: '2:3 竖版（角色）' },
  { value: '1:1', label: '1:1 方图' },
  { value: '3:4', label: '3:4 竖版' },
  { value: '16:9', label: '16:9 横版' },
];

// 分辨率选项
const RESOLUTIONS = [
  { value: '1K', label: '1K (推荐)' },
  { value: '512', label: '512' },
  { value: '2K', label: '2K' },
  { value: '4K', label: '4K' },
];

// 图片上传组件
function ImageUploader({
  onUpload,
  disabled = false,
  className = '',
}: {
  onUpload: (file: File) => Promise<void>;
  disabled?: boolean;
  className?: string;
}) {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (file: File) => {
    if (disabled || uploading) return;
    setUploading(true);
    try {
      await onUpload(file);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      handleUpload(file);
    }
  };

  return (
    <div
      className={`relative border-2 border-dashed rounded-lg transition-colors cursor-pointer ${
        dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
      } ${className}`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
        disabled={disabled || uploading}
      />
      <div className="flex flex-col items-center justify-center p-3">
        {uploading ? (
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
        ) : (
          <Upload className="h-5 w-5 text-muted-foreground" />
        )}
        <span className="text-xs text-muted-foreground mt-1">
          {uploading ? '上传中' : '上传'}
        </span>
      </div>
    </div>
  );
}

// 图片预览卡片
function ImageCard({
  url,
  label,
  onDelete,
  onView,
}: {
  url: string | null;
  label: string;
  onDelete?: () => void;
  onView?: () => void;
}) {
  if (!url) return null;

  return (
    <div className="group relative aspect-[2/3] bg-secondary rounded-lg overflow-hidden border border-border">
      <img src={url} alt={label} className="w-full h-full object-cover" />
      <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
        {onView && (
          <Button size="icon" variant="secondary" onClick={onView}>
            <Eye className="h-4 w-4" />
          </Button>
        )}
        {onDelete && (
          <Button size="icon" variant="destructive" onClick={onDelete}>
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </div>
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-2">
        <span className="text-xs text-white font-medium">{label}</span>
      </div>
    </div>
  );
}

// AI 生成对话框
function AIGenerateDialog({
  open,
  onOpenChange,
  onGenerate,
  title,
  defaultPrompt = '',
  referenceImages = [],
  generating = false,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onGenerate: (params: { prompt: string; negativePrompt?: string; aspectRatio: string; resolution: string; referenceUrls: string[] }) => void;
  title: string;
  defaultPrompt?: string;
  referenceImages?: string[];
  generating?: boolean;
}) {
  const [prompt, setPrompt] = useState(defaultPrompt);
  const [negativePrompt, setNegativePrompt] = useState('');
  const [aspectRatio, setAspectRatio] = useState('2:3');
  const [resolution, setResolution] = useState('1K');
  const [selectedRefs, setSelectedRefs] = useState<string[]>([]);

  useEffect(() => {
    if (open) {
      setPrompt(defaultPrompt);
      setSelectedRefs([]);
    }
  }, [open, defaultPrompt]);

  const toggleRef = (url: string) => {
    setSelectedRefs(prev =>
      prev.includes(url) ? prev.filter(u => u !== url) : [...prev, url]
    );
  };

  const handleGenerate = () => {
    onGenerate({
      prompt,
      negativePrompt: negativePrompt || undefined,
      aspectRatio,
      resolution,
      referenceUrls: selectedRefs,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>输入描述生成图片，支持文生图和图生图</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {referenceImages.length > 0 && (
            <div className="space-y-2">
              <label className="text-sm font-medium">参考图（可选）</label>
              <div className="grid grid-cols-6 gap-2">
                {referenceImages.map((url, idx) => (
                  <div
                    key={idx}
                    className={`relative aspect-square rounded-lg overflow-hidden border-2 cursor-pointer transition-all ${
                      selectedRefs.includes(url) ? 'border-primary' : 'border-transparent'
                    }`}
                    onClick={() => toggleRef(url)}
                  >
                    <img src={url} alt={`ref-${idx}`} className="w-full h-full object-cover" />
                    {selectedRefs.includes(url) && (
                      <div className="absolute inset-0 bg-primary/30 flex items-center justify-center">
                        <div className="w-5 h-5 rounded-full bg-primary text-white text-xs flex items-center justify-center">
                          {selectedRefs.indexOf(url) + 1}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">选择参考图将启用图生图模式</p>
            </div>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium">描述提示词 *</label>
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="描述你想要生成的图片内容..."
              rows={4}
              className="resize-none"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">负向提示词（可选）</label>
            <Textarea
              value={negativePrompt}
              onChange={(e) => setNegativePrompt(e.target.value)}
              placeholder="描述不想要出现的内容..."
              rows={2}
              className="resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">画幅比例</label>
              <Select value={aspectRatio} onValueChange={setAspectRatio}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {ASPECT_RATIOS.map((ar) => (
                    <SelectItem key={ar.value} value={ar.value}>{ar.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">分辨率</label>
              <Select value={resolution} onValueChange={setResolution}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {RESOLUTIONS.map((res) => (
                    <SelectItem key={res.value} value={res.value}>{res.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={handleGenerate} disabled={!prompt.trim() || generating}>
            {generating ? (
              <><Loader2 className="h-4 w-4 mr-2 animate-spin" />生成中...</>
            ) : (
              <><Wand2 className="h-4 w-4 mr-2" />开始生成</>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// 全屏图片预览
function FullscreenPreview({ url, open, onOpenChange }: { url: string | null; open: boolean; onOpenChange: (open: boolean) => void }) {
  if (!url) return null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl p-0 overflow-hidden">
        <img src={url} alt="Preview" className="w-full h-auto" />
      </DialogContent>
    </Dialog>
  );
}

// 文件拖放区域
function SafeImage({
  src,
  alt,
  className,
  fallbackLabel = '图片不可用',
}: {
  src: string | null;
  alt: string;
  className: string;
  fallbackLabel?: string;
}) {
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
  }, [src]);

  if (!src || failed) {
    return (
      <div
        className={`${className} flex items-center justify-center bg-secondary/30 p-4 text-center text-xs text-muted-foreground`}
        title={src || fallbackLabel}
      >
        <div className="flex flex-col items-center gap-2">
          <ImageIcon className="h-5 w-5 opacity-60" />
          <span>{fallbackLabel}</span>
        </div>
      </div>
    );
  }

  return <img src={src} alt={alt} className={className} onError={() => setFailed(true)} />;
}

function FileDropZone({
  onSelect,
  disabled,
  title,
  description,
}: {
  onSelect: (files: FileList | null) => void;
  disabled?: boolean;
  title: string;
  description: string;
}) {
  return (
    <label className={`block rounded-xl border-2 border-dashed p-6 transition ${disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer hover:border-primary/50 hover:bg-secondary/30'}`}>
      <input
        className="hidden"
        type="file"
        accept="image/*"
        multiple
        disabled={disabled}
        onChange={(event) => {
          onSelect(event.target.files);
          event.target.value = '';
        }}
      />
      <div className="flex flex-col items-center justify-center gap-3 text-center">
        <div className="rounded-full bg-secondary p-3 text-muted-foreground">
          <Upload className="h-6 w-6" />
        </div>
        <div>
          <p className="font-medium text-foreground">{title}</p>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
      </div>
    </label>
  );
}


// 参考图网格（支持删除）
function ReferenceImageGrid({
  projectId,
  characterId,
  versionId,
  referenceImages,
  onRefresh,
}: {
  projectId: number;
  characterId: number;
  versionId: number | null;
  referenceImages: string[];
  onRefresh: () => void;
}) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);

  const handleDelete = async (index: number) => {
    if (!versionId) return;
    if (!confirm('确定删除这张参考图吗？')) return;
    setDeleting(index);
    try {
      await charactersApi.deleteReferenceImage(projectId, characterId, versionId, index);
      toast.success('删除成功');
      onRefresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    } finally {
      setDeleting(null);
    }
  };

  if (referenceImages.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <ImageIcon className="h-12 w-12 mx-auto mb-3 opacity-50" />
        <p>暂无参考图</p>
        <p className="text-sm">通过上传或AI生成添加参考图</p>
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-2 gap-2">
        {referenceImages.map((url, idx) => (
          <div
            key={idx}
            className="group relative aspect-[2/3] rounded-lg overflow-hidden border border-border"
          >
            <img src={url} alt={`ref-${idx}`} className="w-full h-full object-cover cursor-pointer" onClick={() => setPreviewUrl(url)} />
            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
              <Button size="icon" variant="secondary" onClick={() => setPreviewUrl(url)}>
                <Eye className="h-4 w-4" />
              </Button>
              {versionId && (
                <Button
                  size="icon"
                  variant="destructive"
                  onClick={() => handleDelete(idx)}
                  disabled={deleting === idx}
                >
                  {deleting === idx ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4" />
                  )}
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
      <FullscreenPreview
        url={previewUrl}
        open={!!previewUrl}
        onOpenChange={() => setPreviewUrl(null)}
      />
    </>
  );
}

// 三视图管理组件
function ThreeViewManager({
  projectId,
  characterId,
  versionId,
  threeViewUrl,
  onRefresh,
}: {
  projectId: number;
  characterId: number;
  versionId: number | null;
  threeViewUrl: string | null;
  onRefresh: () => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (file: File) => {
    if (!versionId) {
      toast.error('请先创建角色版本');
      return;
    }
    setUploading(true);
    try {
      await charactersApi.uploadThreeViewImage(projectId, characterId, versionId, file);
      toast.success('三视图上传成功');
      onRefresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '上传失败');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async () => {
    if (!versionId || !threeViewUrl) return;
    if (!confirm('确定删除三视图吗？')) return;
    setDeleting(true);
    try {
      await charactersApi.deleteThreeViewImage(projectId, characterId, versionId);
      toast.success('删除成功');
      onRefresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-sm">三视图</h4>
        {threeViewUrl && versionId && (
          <Button size="sm" variant="destructive" onClick={handleDelete} disabled={deleting}>
            {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4 mr-1" />}
            删除
          </Button>
        )}
      </div>
      {threeViewUrl ? (
        <div
          className="group relative aspect-[2/3] rounded-lg overflow-hidden border border-border cursor-pointer max-w-xs"
          onClick={() => setPreviewUrl(threeViewUrl)}
        >
          <img src={threeViewUrl} alt="三视图" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <Button size="icon" variant="secondary">
              <Eye className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ) : (
        <div
          className={`relative border-2 border-dashed rounded-lg aspect-[2/3] max-w-xs transition-colors cursor-pointer ${
            uploading ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
          } ${!versionId ? 'opacity-50 cursor-not-allowed' : ''}`}
          onClick={() => !uploading && versionId && inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
            disabled={uploading || !versionId}
          />
          <div className="flex flex-col items-center justify-center h-full">
            {uploading ? (
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            ) : (
              <>
                <Upload className="h-8 w-8 text-muted-foreground mb-2" />
                <span className="text-sm text-muted-foreground">上传三视图</span>
              </>
            )}
          </div>
        </div>
      )}
      {!versionId && (
        <p className="text-xs text-muted-foreground">请先创建角色版本</p>
      )}
      <FullscreenPreview
        url={previewUrl}
        open={!!previewUrl}
        onOpenChange={() => setPreviewUrl(null)}
      />
    </div>
  );
}

// 状态图片管理组件
function StateImagesManager({
  projectId,
  characterId,
  versionId,
  stateImages,
  onRefresh,
}: {
  projectId: number;
  characterId: number;
  versionId: number | null;
  stateImages: Record<string, string> | null;
  onRefresh: () => void;
}) {
  const [uploading, setUploading] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const inputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const STATE_TYPES = [
    { key: 'anger', label: '愤怒' },
    { key: 'happy', label: '开心' },
    { key: 'sad', label: '悲伤' },
    { key: 'determination', label: '坚定' },
    { key: 'skill_release', label: '释放技能' },
    { key: 'battle_stance', label: '战斗姿态' },
  ];

  const handleUpload = async (stateType: string, file: File) => {
    if (!versionId) {
      toast.error('请先创建角色版本');
      return;
    }
    setUploading(stateType);
    try {
      await charactersApi.uploadStateImage(projectId, characterId, versionId, stateType, file);
      toast.success(`${STATE_TYPES.find(s => s.key === stateType)?.label || stateType} 上传成功`);
      onRefresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '上传失败');
    } finally {
      setUploading(null);
    }
  };

  const handleDelete = async (stateType: string) => {
    if (!versionId) return;
    if (!confirm(`确定删除${STATE_TYPES.find(s => s.key === stateType)?.label || stateType}状态图吗？`)) return;
    setDeleting(stateType);
    try {
      await charactersApi.deleteStateImage(projectId, characterId, versionId, stateType);
      toast.success('删除成功');
      onRefresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="space-y-3">
      <h4 className="font-medium text-sm">状态图片</h4>
      <div className="grid grid-cols-3 gap-3">
        {STATE_TYPES.map((state) => {
          const imageUrl = stateImages?.[state.key];
          return (
            <div key={state.key} className="space-y-1">
              <p className="text-xs text-muted-foreground">{state.label}</p>
              {imageUrl ? (
                <div className="group relative aspect-[2/3] rounded-lg overflow-hidden border border-border">
                  <img src={imageUrl} alt={state.label} className="w-full h-full object-cover cursor-pointer" onClick={() => setPreviewUrl(imageUrl)} />
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <Button size="icon" variant="destructive" onClick={() => handleDelete(state.key)} disabled={deleting === state.key}>
                      {deleting === state.key ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
              ) : (
                <div
                  className={`relative border-2 border-dashed rounded-lg aspect-[2/3] transition-colors cursor-pointer ${
                    uploading === state.key ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
                  } ${!versionId ? 'opacity-50 cursor-not-allowed' : ''}`}
                  onClick={() => !uploading && versionId && inputRefs.current[state.key]?.click()}
                >
                  <input
                    ref={(el) => { inputRefs.current[state.key] = el; }}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => e.target.files?.[0] && handleUpload(state.key, e.target.files[0])}
                    disabled={uploading === state.key || !versionId}
                  />
                  <div className="flex flex-col items-center justify-center h-full">
                    {uploading === state.key ? (
                      <Loader2 className="h-6 w-6 animate-spin text-primary" />
                    ) : (
                      <Plus className="h-6 w-6 text-muted-foreground" />
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <FullscreenPreview
        url={previewUrl}
        open={!!previewUrl}
        onOpenChange={() => setPreviewUrl(null)}
      />
    </div>
  );
}

// 待上传文件
interface PendingImageFile {
  id: string;
  file: File;
  preview: string;
}

// 角色版本卡片
function VersionCard({
  version,
  onDelete,
  onOpenStudio,
  onOpenDetail,
  onEdit,
}: {
  version: CharacterVersionResponse;
  onDelete: () => void;
  onOpenStudio: (versionId: number) => void;
  onOpenDetail: (versionId: number) => void;
  onEdit: () => void;
}) {
  const previewImages = normalizeImageUrls([version.three_view_url, ...(version.reference_image_urls || [])]);
  const previewCount = previewImages.length;

  return (
    <Card
      className="cursor-pointer bg-card border-border transition hover:border-primary/40"
      onClick={() => onOpenStudio(version.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onOpenStudio(version.id);
        }
      }}
    >
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base">{version.label}</CardTitle>
            <CardDescription>{version.version_code}</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline">{version.three_view_url ? '有三视图' : '无三视图'}</Badge>
            <Badge variant="secondary">{previewCount} 张图片</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3 text-sm">
          {version.age_description ? <div><span className="text-muted-foreground">年龄：</span><span>{version.age_description}</span></div> : null}
          {version.height_cm ? <div><span className="text-muted-foreground">身高：</span><span>{version.height_cm}cm</span></div> : null}
          {version.dou_qi_level ? <div><span className="text-muted-foreground">境界：</span><span>{version.dou_qi_level}</span></div> : null}
          {version.dou_qi_color ? <div className="flex items-center gap-1"><span className="text-muted-foreground">斗气：</span><span className="w-4 h-4 rounded-full border" style={{ backgroundColor: version.dou_qi_color }} /></div> : null}
        </div>

        {previewImages.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {previewImages.slice(0, 4).map((url, index) => (
              <div key={`${url}-${index}`} className="overflow-hidden rounded-xl border bg-card">
                <SafeImage src={url} alt="" className="aspect-[2/3] w-full object-cover" />
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
            当前版本还没有图片，点击卡片进入图库上传或生成。
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={(event) => {
              event.stopPropagation();
              onOpenStudio(version.id);
            }}
          >
            <Sparkles className="h-4 w-4 mr-1" />
            图片工作台
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={(event) => {
              event.stopPropagation();
              onOpenDetail(version.id);
            }}
          >
            <ArrowRight className="h-4 w-4 mr-1" />
            详情
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={(event) => {
              event.stopPropagation();
              onEdit();
            }}
          >
            编辑版本
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={(event) => {
              event.stopPropagation();
              onDelete();
            }}
          >
            <Trash2 className="h-4 w-4 mr-1 text-muted-foreground" />
            删除版本
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// 版本对话框
function VersionDialog({
  open,
  onOpenChange,
  onSubmit,
  submitting,
  initialVersion,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: { version_code: string; label: string }) => void;
  submitting: boolean;
  initialVersion?: CharacterVersionResponse | null;
}) {
  const [versionCode, setVersionCode] = useState('');
  const [label, setLabel] = useState('');

  useEffect(() => {
    if (!open) {
      setVersionCode('');
      setLabel('');
      return;
    }
    setVersionCode(initialVersion?.version_code || '');
    setLabel(initialVersion?.label || '');
  }, [initialVersion?.label, initialVersion?.version_code, open]);

  const handleSubmit = () => {
    if (!versionCode.trim() || !label.trim()) return;
    onSubmit({ version_code: versionCode.trim(), label: label.trim() });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{initialVersion ? '编辑角色版本' : '创建角色版本'}</DialogTitle>
          <DialogDescription>
            {initialVersion ? '更新当前角色版本的基础信息。' : '为角色创建一个新的版本，用于管理不同阶段的形象。'}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">版本编号 *</label>
            <Input value={versionCode} onChange={(e) => setVersionCode(e.target.value)} placeholder="例如: v1_teen, v2_adult" />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">版本名称 *</label>
            <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="例如: 少年期（15-16岁）" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={handleSubmit} disabled={!versionCode.trim() || !label.trim() || submitting}>
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            {initialVersion ? '保存版本' : '创建'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// 三视图系统提示词
const THREE_VIEW_SYSTEM_PROMPT = `Character reference sheet, three-view turnaround design.
Front view, side view, and back view of the same character on a single image.
Clean white background, professional character design sheet.
Consistent character design across all three views.
Same outfit, same facial features, same proportions.
Standard turnaround pose: facing front, facing right, facing back.
High quality, detailed character design, anime/manga style.
Clean lines, clear silhouette, character reference for animation.`;

// 角色出图工作区 - 参照场景页面的布局
function CharacterStudioWorkspace({
  projectId,
  charDetail,
  selectedVersionId,
  onRefresh,
  onVersionChange,
}: {
  projectId: number;
  charDetail: CharacterDetailResponse;
  selectedVersionId: number;
  onRefresh: () => void;
  onVersionChange: (versionId: number) => void;
}) {
  const version = charDetail.versions.find((item) => item.id === selectedVersionId);
  const versionImageItems = useMemo(() => {
    // 直接从 charDetail 中查找版本，确保依赖正确
    const ver = charDetail.versions.find((item) => item.id === selectedVersionId);
    if (!ver) {
      return [] as Array<{
        key: string;
        kind: 'three_view' | 'reference';
        url: string;
        label: string;
        referenceIndex?: number;
      }>;
    }

    const items: Array<{
      key: string;
      kind: 'three_view' | 'reference';
      url: string;
      label: string;
      referenceIndex?: number;
    }> = [];

    const threeViewUrl = normalizeImageUrl(ver.three_view_url);
    if (threeViewUrl) {
      items.push({
        key: `three-view-${threeViewUrl}`,
        kind: 'three_view',
        url: threeViewUrl,
        label: '三视图',
      });
    }

    (ver.reference_image_urls || []).forEach((rawUrl, index) => {
      const normalizedUrl = normalizeImageUrl(rawUrl);
      if (!normalizedUrl) return;
      items.push({
        key: `reference-${index}-${normalizedUrl}`,
        kind: 'reference',
        url: normalizedUrl,
        label: `版本素材 #${index + 1}`,
        referenceIndex: index,
      });
    });

    return items;
  }, [charDetail, selectedVersionId]);

  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [aspectRatio, setAspectRatio] = useState('2:3');
  const [resolution, setResolution] = useState('1K');
  const [threeViewGenerating, setThreeViewGenerating] = useState(false);
  const [charImageGenerating, setCharImageGenerating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deletingImageKey, setDeletingImageKey] = useState<string | null>(null);
  const [showAssetPicker, setShowAssetPicker] = useState(false);
  const [assetList, setAssetList] = useState<AssetResponse[]>([]);
  const [loadingAssets, setLoadingAssets] = useState(false);
  const [assetPage, setAssetPage] = useState(1);
  const [assetTotal, setAssetTotal] = useState(0);
  const [referencingAssetId, setReferencingAssetId] = useState<number | null>(null);
  const [selectedRefUrls, setSelectedRefUrls] = useState<string[]>([]);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const assetPageSize = 12;
  const totalPages = Math.max(1, Math.ceil(assetTotal / assetPageSize));
  const galleryUrlSet = useMemo(() => new Set(versionImageItems.map((item) => item.url)), [versionImageItems]);

  useEffect(() => {
    setSelectedRefUrls((prev) => prev.filter((url) => galleryUrlSet.has(url)));
  }, [galleryUrlSet]);

  const toggleRefImage = useCallback((url: string) => {
    setSelectedRefUrls((prev) => {
      if (prev.includes(url)) {
        return prev.filter((item) => item !== url);
      }
      if (prev.length >= 5) {
        toast.error('最多选择 5 张参考图');
        return prev;
      }
      return [...prev, url];
    });
  }, []);

  const pollTask = useCallback((taskId: number, onComplete: () => void) => {
    let attempts = 0;
    const poll = async () => {
      try {
        const task = await tasksApi.get(taskId);
        if (task.status === 'success') {
          toast.success('生成完成');
          onComplete();
          return;
        }
        if (task.status === 'failed') {
          toast.error(task.error_message || '生成失败');
          onComplete();
          return;
        }
        if (++attempts < 60) {
          setTimeout(poll, 5000);
        } else {
          toast.warning('生成时间较长，请稍后刷新查看');
          onComplete();
        }
      } catch {
        if (++attempts < 60) {
          setTimeout(poll, 5000);
        } else {
          onComplete();
        }
      }
    };
    poll();
  }, []);

  const handleGenerateThreeView = useCallback(async () => {
    if (!version || !prompt.trim()) {
      toast.error('请输入角色外观描述');
      return;
    }
    setThreeViewGenerating(true);
    try {
      const fullPrompt = `${THREE_VIEW_SYSTEM_PROMPT}\n\nCharacter description: ${prompt.trim()}`;
      const result = await tasksApi.triggerImage({
        project_id: projectId,
        character_id: charDetail.id,
        character_version_id: version.id,
        prompt: fullPrompt,
        aspect_ratio: '2:3',
        resolution: '1K',
        character_image_kind: 'three_view',
        reference_image_urls: selectedRefUrls.length > 0 ? selectedRefUrls : undefined,
        save_to_shot: true,
      });
      toast.success('三视图生成任务已提交');
      pollTask(result.id, () => {
        setThreeViewGenerating(false);
        onRefresh();
      });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '生成失败');
      setThreeViewGenerating(false);
    }
  }, [charDetail.id, onRefresh, pollTask, projectId, prompt, selectedRefUrls, version]);

  const handleGenerateCharacterImage = useCallback(async () => {
    if (!version || !prompt.trim()) {
      toast.error('请输入角色状态描述');
      return;
    }
    setCharImageGenerating(true);
    try {
      const result = await tasksApi.triggerImage({
        project_id: projectId,
        character_id: charDetail.id,
        character_version_id: version.id,
        prompt: prompt.trim(),
        negative_prompt: negativePrompt.trim() || undefined,
        aspect_ratio: aspectRatio,
        resolution,
        reference_image_urls: selectedRefUrls.length > 0 ? selectedRefUrls : undefined,
        save_to_shot: true,
      });
      toast.success('角色图生成任务已提交');
      pollTask(result.id, () => {
        setCharImageGenerating(false);
        onRefresh();
      });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '生成失败');
      setCharImageGenerating(false);
    }
  }, [aspectRatio, charDetail.id, negativePrompt, onRefresh, pollTask, projectId, prompt, resolution, selectedRefUrls, version]);

  const handleUploadSelection = useCallback(async (files: FileList | null) => {
    if (!version || !files || files.length === 0) return;
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        await charactersApi.uploadReferenceImage(projectId, charDetail.id, version.id, file);
      }
      toast.success('图片已加入当前版本图库');
      await onRefresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '上传失败');
    } finally {
      setUploading(false);
    }
  }, [charDetail.id, onRefresh, projectId, version]);

  const loadAssets = useCallback(async (page: number) => {
    setLoadingAssets(true);
    try {
      const result = await assetsApi.list(projectId, page, assetPageSize, {
        assetType: 'image',
        isCurrent: true,
      });
      setAssetList(result.items.filter((asset) => Boolean(asset.file_url)));
      setAssetTotal(result.total);
    } catch {
      setAssetList([]);
      setAssetTotal(0);
      toast.error('加载素材库失败');
    } finally {
      setLoadingAssets(false);
    }
  }, [projectId]);

  const handleReferenceAsset = useCallback(async (asset: AssetResponse) => {
    if (!version) return;
    if (galleryUrlSet.has(asset.file_url)) {
      toast.info('该图片已经在当前版本图库中');
      return;
    }
    setReferencingAssetId(asset.id);
    try {
      await charactersApi.addReferenceImageFromUrl(projectId, charDetail.id, version.id, asset.file_url);
      toast.success('已加入当前版本图库');
      await onRefresh();
      setShowAssetPicker(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '加入失败');
    } finally {
      setReferencingAssetId(null);
    }
  }, [charDetail.id, galleryUrlSet, onRefresh, projectId, version]);

  const handleDeleteImage = useCallback(async (item: { key: string; kind: 'three_view' | 'reference'; url: string; referenceIndex?: number }) => {
    if (!version) return;
    setDeletingImageKey(item.key);
    try {
      if (item.kind === 'three_view') {
        await charactersApi.deleteThreeViewImage(projectId, charDetail.id, version.id);
      } else if (item.referenceIndex !== undefined) {
        await charactersApi.deleteReferenceImage(projectId, charDetail.id, version.id, item.referenceIndex);
      }
      setSelectedRefUrls((prev) => prev.filter((url) => url !== item.url));
      toast.success('已从当前版本图库移除');
      await onRefresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    } finally {
      setDeletingImageKey(null);
    }
  }, [charDetail.id, onRefresh, projectId, version]);

  useEffect(() => {
    if (!showAssetPicker) {
      setAssetList([]);
      setAssetPage(1);
      setAssetTotal(0);
      setReferencingAssetId(null);
      return;
    }
    loadAssets(assetPage).catch(() => undefined);
  }, [assetPage, loadAssets, showAssetPicker]);

  if (!version) return null;

  return (
    <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wand2 className="h-5 w-5" />
            角色图生成
          </CardTitle>
          <CardDescription>
            当前版本：{version.label || version.version_code}。支持直接文生图，也支持先在右侧选中参考图后切换为图生图。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">角色描述</label>
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={5}
              placeholder={`描述角色外观或状态，例如：\n${charDetail.name}，古风少年，黑发飘逸，眼神坚毅，身着白色长袍。\n\n也可以描述动态状态：\n${charDetail.name}释放技能，周身环绕雷电，双手结印。`}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">负面提示词</label>
            <Input
              value={negativePrompt}
              onChange={(e) => setNegativePrompt(e.target.value)}
              placeholder="例如：blurry, low quality, watermark, bad anatomy"
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">画幅比例</label>
              <Select value={aspectRatio} onValueChange={setAspectRatio}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ASPECT_RATIOS.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">分辨率</label>
              <Select value={resolution} onValueChange={setResolution}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {RESOLUTIONS.map((item) => (
                    <SelectItem key={item.value} value={item.value}>
                      {item.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {selectedRefUrls.length > 0 ? (
            <div className="space-y-3 rounded-xl border border-primary/20 bg-primary/5 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">已选中参考图</div>
                  <div className="text-xs text-muted-foreground">当前会按图生图模式生成，可在下方取消选择。</div>
                </div>
                <Badge variant="secondary">{selectedRefUrls.length}/5</Badge>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {selectedRefUrls.map((url) => (
                  <div key={url} className="overflow-hidden rounded-xl border border-primary ring-2 ring-primary/20">
                    <button
                      type="button"
                      onClick={() => setPreviewUrl(url)}
                      className="group relative block w-full overflow-hidden"
                    >
                      <SafeImage src={url} alt="参考图预览" className="aspect-[2/3] w-full object-cover transition group-hover:scale-[1.01]" />
                      <div className="absolute inset-x-0 bottom-0 flex items-center justify-end bg-gradient-to-t from-black/55 to-transparent p-3 opacity-0 transition group-hover:opacity-100">
                        <span className="inline-flex items-center gap-1 rounded-full bg-white/90 px-2 py-1 text-xs font-medium text-foreground">
                          <Eye className="h-3 w-3" />
                          预览
                        </span>
                      </div>
                    </button>
                    <div className="flex justify-end p-2">
                      <Button variant="ghost" size="sm" onClick={() => toggleRefImage(url)}>
                        取消选择
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed p-4 text-sm text-muted-foreground">
              当前未选中参考图。你可以直接文生图，或者在右侧图库中点击“设为参考图”切换为图生图。
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <Button
              className="flex-1"
              variant="outline"
              onClick={handleGenerateThreeView}
              disabled={threeViewGenerating || charImageGenerating || !prompt.trim()}
            >
              {threeViewGenerating ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Layers className="mr-2 h-4 w-4" />
              )}
              生成三视图
            </Button>
            <Button
              className="flex-1"
              onClick={handleGenerateCharacterImage}
              disabled={threeViewGenerating || charImageGenerating || !prompt.trim()}
            >
              {charImageGenerating ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="mr-2 h-4 w-4" />
              )}
              生成角色图
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <FileImage className="h-5 w-5" />
                版本图库
              </CardTitle>
              <CardDescription className="mt-1">
                上传本地图片或从项目素材库选择图片，都会直接进入当前角色版本图库。
              </CardDescription>
            </div>
            <div className="w-full md:w-[180px]">
              <Select value={String(selectedVersionId)} onValueChange={(value) => onVersionChange(Number(value))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {charDetail.versions.map((v) => (
                    <SelectItem key={v.id} value={String(v.id)}>
                      {v.label || v.version_code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-sm font-medium">上传到当前版本图库</div>
                <div className="text-xs text-muted-foreground">点击或拖拽图片到这里，上传后会立即加入右侧图库。</div>
              </div>
              {uploading ? (
                <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  正在上传
                </div>
              ) : null}
            </div>

            <FileDropZone
              onSelect={handleUploadSelection}
              disabled={uploading}
              title="上传角色图片"
              description="支持 JPG、PNG、WebP、GIF，上传后立即加入当前版本"
            />
          </div>

          <div className="rounded-xl border bg-secondary/10 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="space-y-1">
                <div className="text-sm font-medium">引用素材库图片</div>
                <div className="text-xs text-muted-foreground">在弹窗中分页浏览项目素材库图片，选择后直接加入当前版本图库。</div>
              </div>
              <Button variant="outline" onClick={() => setShowAssetPicker(true)}>
                <ImagePlus className="mr-2 h-4 w-4" />
                从素材库选择图片
              </Button>
            </div>
          </div>

          {versionImageItems.length === 0 ? (
            <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
              当前版本还没有图片。你可以先生成三视图、上传本地图片，或者从素材库引用已有图片。
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {versionImageItems.map((item, index) => {
                const isSelected = selectedRefUrls.includes(item.url);
                const isDeleting = deletingImageKey === item.key;

                return (
                  <div key={item.key} className="overflow-hidden rounded-xl border bg-card">
                    <button
                      type="button"
                      onClick={() => setPreviewUrl(item.url)}
                      className="group relative block w-full overflow-hidden"
                    >
                      <SafeImage src={item.url} alt={item.label} className="aspect-[2/3] w-full object-cover transition group-hover:scale-[1.01]" />
                      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-black/55 via-black/15 to-transparent" />
                      <div className="absolute left-3 top-3">
                        <Badge variant="outline" className="border-white/40 bg-black/35 text-white backdrop-blur">
                          {item.kind === 'three_view' ? '三视图' : `版本素材 #${index + 1}`}
                        </Badge>
                      </div>
                      <div className="absolute inset-x-0 bottom-0 flex items-center justify-end p-3 opacity-0 transition group-hover:opacity-100">
                        <span className="inline-flex items-center gap-1 rounded-full bg-white/90 px-2 py-1 text-xs font-medium text-foreground">
                          <Eye className="h-3 w-3" />
                          预览
                        </span>
                      </div>
                    </button>

                    <div className="flex items-center justify-between gap-2 p-3">
                      <div className="text-xs text-muted-foreground">{item.label}</div>
                      <div className="flex items-center gap-2">
                        <Button variant={isSelected ? 'default' : 'outline'} size="sm" onClick={() => toggleRefImage(item.url)}>
                          {isSelected ? '已选中' : '设为参考图'}
                        </Button>
                        <Button variant="ghost" size="icon" disabled={isDeleting} onClick={() => handleDeleteImage(item)}>
                          {isDeleting ? (
                            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                          ) : (
                            <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                          )}
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={showAssetPicker} onOpenChange={setShowAssetPicker}>
        <DialogContent className="max-w-6xl gap-0 overflow-hidden p-0">
          <DialogHeader className="border-b bg-gradient-to-r from-secondary/70 via-background to-background px-6 py-5 text-left">
            <DialogTitle className="text-xl">选择素材库图片加入当前版本</DialogTitle>
            <DialogDescription className="max-w-3xl text-sm leading-6">
              弹窗中按页浏览项目素材库图片，选择后会直接加入当前角色版本图库。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-5 px-6 py-5">
            <div className="flex flex-col gap-3 rounded-2xl border bg-muted/30 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary" className="rounded-full px-3 py-1 text-xs font-medium">
                  {assetTotal > 0 ? `第 ${(assetPage - 1) * assetPageSize + 1}-${Math.min(assetPage * assetPageSize, assetTotal)} 张` : '当前无可选图片'}
                </Badge>
                <Badge variant="outline" className="rounded-full px-3 py-1 text-xs font-medium">
                  共 {assetTotal} 张
                </Badge>
              </div>
              <div className="text-xs font-medium tracking-wide text-muted-foreground">每页 {assetPageSize} 张</div>
            </div>

            <ScrollArea className="max-h-[62vh] pr-2">
              {loadingAssets ? (
                <div className="flex min-h-[360px] items-center justify-center rounded-2xl border border-dashed bg-muted/20">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : assetList.length === 0 ? (
                <div className="rounded-2xl border border-dashed bg-muted/20 py-20 text-center text-sm text-muted-foreground">
                  当前素材库中还没有图片
                </div>
              ) : (
                <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
                  {assetList.map((asset) => {
                    const isIncluded = galleryUrlSet.has(asset.file_url);
                    const isSubmitting = referencingAssetId === asset.id;
                    const assetLabel = asset.asset_code || `素材图 #${asset.id}`;

                    return (
                      <div
                        key={asset.id}
                        className={`group overflow-hidden rounded-2xl border bg-card shadow-sm transition-all duration-200 ${
                          isIncluded ? 'border-border/70 bg-muted/20' : 'border-border/60 hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lg'
                        }`}
                      >
                        <div className="relative overflow-hidden bg-muted">
                          <img src={asset.file_url} alt={assetLabel} className="aspect-[2/3] w-full object-cover transition duration-300 group-hover:scale-[1.02]" />
                          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/45 via-black/10 to-transparent" />
                          <div className="absolute left-3 top-3">
                            <Badge
                              variant={isIncluded ? 'secondary' : 'outline'}
                              className={isIncluded ? 'rounded-full px-2.5 py-1 text-[11px] font-medium' : 'rounded-full border border-white/40 bg-black/35 px-2.5 py-1 text-[11px] font-medium text-white backdrop-blur'}
                            >
                              {isIncluded ? '已在当前图库' : '素材库图片'}
                            </Badge>
                          </div>
                        </div>

                        <div className="space-y-3 p-4">
                          <div className="space-y-1">
                            <div className="line-clamp-1 text-sm font-semibold text-foreground" title={assetLabel}>
                              {assetLabel}
                            </div>
                            <div className="text-xs text-muted-foreground">素材 #{asset.id}</div>
                          </div>
                          <Button
                            className="w-full"
                            size="sm"
                            variant={isIncluded ? 'secondary' : 'outline'}
                            disabled={isIncluded || Boolean(referencingAssetId)}
                            onClick={() => handleReferenceAsset(asset)}
                          >
                            {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                            {isIncluded ? '已加入当前版本' : '加入当前版本'}
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </ScrollArea>

            {totalPages > 1 ? (
              <div className="border-t pt-4">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-muted-foreground">第 {assetPage} / {totalPages} 页</div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" disabled={assetPage <= 1 || loadingAssets} onClick={() => setAssetPage((current) => current - 1)}>
                      上一页
                    </Button>
                    <Button variant="outline" size="sm" disabled={assetPage >= totalPages || loadingAssets} onClick={() => setAssetPage((current) => current + 1)}>
                      下一页
                    </Button>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </DialogContent>
      </Dialog>

      <FullscreenPreview
        url={previewUrl}
        open={!!previewUrl}
        onOpenChange={() => setPreviewUrl(null)}
      />
    </div>
  );
}

// 主页面
export default function CharactersPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = use(params);
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectIdNum = Number(projectId);

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [characters, setCharacters] = useState<CharacterResponse[]>([]);
  const [selectedCharId, setSelectedCharId] = useState<number | null>(null);
  const [charDetail, setCharDetail] = useState<CharacterDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newCharName, setNewCharName] = useState('');
  const [newCharDesc, setNewCharDesc] = useState('');
  const [creating, setCreating] = useState(false);
  const [isVersionDialogOpen, setIsVersionDialogOpen] = useState(false);
  const [editingVersion, setEditingVersion] = useState<CharacterVersionResponse | null>(null);
  const [savingVersion, setSavingVersion] = useState(false);
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState<'studio' | 'versions' | 'details'>('studio');
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
  const lastAppliedRouteSelectionRef = useRef<string | null>(null);
  const routeTargetCharId = Number(searchParams.get('charId') || '');
  const routeTargetVersionId = Number(searchParams.get('versionId') || '');
  const routeTargetTab = searchParams.get('tab');
  const routeSelectionKey = `${searchParams.get('charId') || ''}|${searchParams.get('versionId') || ''}|${routeTargetTab || ''}`;

  // 当角色详情变化时，默认选中一个有效版本
  useEffect(() => {
    if (!charDetail) {
      setSelectedVersionId(null);
      return;
    }
    if (charDetail.versions.length === 0) {
      setSelectedVersionId(null);
      return;
    }
    if (selectedVersionId && charDetail.versions.some((version) => version.id === selectedVersionId)) {
      return;
    }
    setSelectedVersionId(charDetail.versions[0].id);
  }, [charDetail, selectedVersionId]);

  useEffect(() => {
    if (isNaN(projectIdNum)) return;

    Promise.all([
      projectsApi.get(projectIdNum).catch(() => null),
      charactersApi.list(projectIdNum),
    ])
      .then(([projectRes, charsRes]) => {
        setProject(projectRes);
        setCharacters(charsRes.items);
        if (charsRes.items.length > 0) setSelectedCharId(charsRes.items[0].id);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load data:', err);
        setLoading(false);
      });
  }, [projectIdNum]);

  const loadCharDetail = useCallback(async () => {
    if (!selectedCharId || isNaN(projectIdNum)) {
      setCharDetail(null);
      return null;
    }
    try {
      const detail = await charactersApi.get(projectIdNum, selectedCharId);
      setCharDetail(detail);
      return detail;
    } catch {
      setCharDetail(null);
      return null;
    }
  }, [selectedCharId, projectIdNum]);

  useEffect(() => {
    loadCharDetail();
  }, [loadCharDetail]);

  useEffect(() => {
    if ((!searchParams.get('charId') && !searchParams.get('versionId') && !routeTargetTab) || routeSelectionKey === lastAppliedRouteSelectionRef.current) {
      return;
    }

    if (routeTargetTab === 'studio' || routeTargetTab === 'versions' || routeTargetTab === 'details') {
      setActiveWorkspaceTab(routeTargetTab);
    }

    if (!Number.isNaN(routeTargetCharId) && characters.some((char) => char.id === routeTargetCharId)) {
      if (selectedCharId !== routeTargetCharId) {
        setSelectedCharId(routeTargetCharId);
      }
    }

    const canApplyVersion = !Number.isNaN(routeTargetVersionId)
      && charDetail
      && (!Number.isNaN(routeTargetCharId) ? charDetail.id === routeTargetCharId : true)
      && charDetail.versions.some((version) => version.id === routeTargetVersionId);

    if (canApplyVersion) {
      setSelectedVersionId(routeTargetVersionId);
      lastAppliedRouteSelectionRef.current = routeSelectionKey;
      return;
    }

    if (searchParams.get('versionId') && !charDetail) {
      return;
    }

    if (!searchParams.get('versionId')) {
      lastAppliedRouteSelectionRef.current = routeSelectionKey;
    }
  }, [
    charDetail,
    characters,
    routeSelectionKey,
    routeTargetCharId,
    routeTargetTab,
    routeTargetVersionId,
    searchParams,
    selectedCharId,
  ]);

  const handleCreateCharacter = useCallback(async () => {
    if (!newCharName.trim()) return;
    setCreating(true);
    try {
      const char = await charactersApi.create(projectIdNum, { name: newCharName.trim(), role_description: newCharDesc.trim() || undefined });
      setCharacters(prev => [char, ...prev]);
      setSelectedCharId(char.id);
      setIsCreateDialogOpen(false);
      setNewCharName(''); setNewCharDesc('');
      toast.success('角色创建成功');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '创建失败');
    } finally {
      setCreating(false);
    }
  }, [projectIdNum, newCharName, newCharDesc]);

  const handleDeleteCharacter = useCallback(async (charId: number) => {
    if (!confirm('确定要删除这个角色吗？')) return;
    try {
      await charactersApi.delete(projectIdNum, charId);
      setCharacters(prev => prev.filter(c => c.id !== charId));
      if (selectedCharId === charId) { setSelectedCharId(null); setCharDetail(null); }
      toast.success('角色已删除');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    }
  }, [projectIdNum, selectedCharId]);

  const handleSaveVersion = useCallback(async (data: { version_code: string; label: string }) => {
    if (!selectedCharId) return;
    setSavingVersion(true);
    try {
      if (editingVersion) {
        await charactersApi.updateVersion(projectIdNum, selectedCharId, editingVersion.id, data);
      } else {
        await charactersApi.createVersion(projectIdNum, selectedCharId, data);
      }
      toast.success('版本创建成功');
      setIsVersionDialogOpen(false);
      setEditingVersion(null);
      loadCharDetail();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '创建失败');
    } finally {
      setSavingVersion(false);
    }
  }, [editingVersion, projectIdNum, selectedCharId, loadCharDetail]);

  const handleDeleteVersion = useCallback(async (versionId: number) => {
    if (!confirm('确定要删除这个版本吗？')) return;
    try {
      await charactersApi.deleteVersion(projectIdNum, selectedCharId!, versionId);
      toast.success('版本已删除');
      loadCharDetail();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    }
  }, [projectIdNum, selectedCharId, loadCharDetail]);

  const openCreateVersionDialog = useCallback(() => {
    setEditingVersion(null);
    setIsVersionDialogOpen(true);
  }, []);

  const openEditVersionDialog = useCallback((version: CharacterVersionResponse) => {
    setEditingVersion(version);
    setIsVersionDialogOpen(true);
  }, []);

  const openVersionDetailPage = useCallback((versionId: number) => {
    if (!charDetail) return;
    router.push(`/projects/${projectId}/materials/characters?charId=${charDetail.id}&versionId=${versionId}&tab=studio`);
  }, [charDetail, projectId, router]);

  const filteredCharacters = characters.filter(char =>
    char.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (char.role_description || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    char.char_code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <AppLayout projectId={projectId}>
        <div className="h-full flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout
      projectId={projectId}
      breadcrumbs={[
        { label: '项目', href: '/projects' },
        { label: project?.name || '加载中...', href: `/projects/${projectId}` },
        { label: '素材库', href: `/projects/${projectId}/materials` },
        { label: '角色管理' },
      ]}
    >
      <div className="h-[calc(100vh-4rem)] flex">
        <div className="w-80 border-r border-border bg-card flex flex-col">
          <div className="p-4 border-b border-border space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">角色列表</h2>
              <Badge variant="outline">{characters.length}</Badge>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input placeholder="搜索角色..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-9" />
            </div>
            <Button className="w-full" onClick={() => setIsCreateDialogOpen(true)}><Plus className="h-4 w-4 mr-2" />创建角色</Button>
            <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
              <DialogContent>
                <DialogHeader><DialogTitle>创建新角色</DialogTitle></DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2"><label className="text-sm font-medium">角色名称 *</label><Input placeholder="输入角色名称" value={newCharName} onChange={(e) => setNewCharName(e.target.value)} /></div>
                  <div className="space-y-2"><label className="text-sm font-medium">角色描述</label><Textarea placeholder="描述角色的背景..." rows={3} value={newCharDesc} onChange={(e) => setNewCharDesc(e.target.value)} /></div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>取消</Button>
                  <Button onClick={handleCreateCharacter} disabled={!newCharName.trim() || creating}>{creating && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}创建</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
          <ScrollArea className="flex-1">
            <div className="p-3 space-y-2">
              {filteredCharacters.map(char => (
                <div key={char.id} className="group relative">
                  <div onClick={() => setSelectedCharId(char.id)} className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all ${selectedCharId === char.id ? 'bg-primary/10 border border-primary/30' : 'hover:bg-secondary/50 border border-transparent'}`}>
                    <Avatar className="h-10 w-10 shrink-0"><AvatarFallback className="bg-primary/10 text-primary text-lg">{char.name.slice(0, 1)}</AvatarFallback></Avatar>
                    <div className="flex-1 min-w-0"><span className="font-medium text-sm truncate block">{char.name}</span><p className="text-xs text-muted-foreground truncate">{char.role_description || char.char_code}</p></div>
                    <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100 shrink-0 text-muted-foreground hover:text-destructive" onClick={(e) => { e.stopPropagation(); handleDeleteCharacter(char.id); }}><Trash2 className="h-4 w-4" /></Button>
                  </div>
                </div>
              ))}
              {filteredCharacters.length === 0 && <div className="py-8 text-center text-muted-foreground"><Users className="h-12 w-12 mx-auto mb-3 opacity-50" /><p>没有找到角色</p></div>}
            </div>
          </ScrollArea>
        </div>
        <div className="flex-1 bg-background overflow-y-auto">
          {charDetail ? (
            <div className="p-6 space-y-6">
              {/* 角色头部信息 */}
              <div className="flex flex-col gap-4 rounded-2xl border bg-card p-6 lg:flex-row lg:items-start lg:justify-between">
                <div className="flex items-start gap-4">
                  <Avatar className="h-16 w-16">
                    <AvatarFallback className="bg-primary/10 text-primary text-2xl">
                      {charDetail.name.slice(0, 1)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <h1 className="text-2xl font-bold text-foreground">{charDetail.name}</h1>
                      <Badge variant="outline">{charDetail.char_code}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {charDetail.role_description || '暂无描述'}
                    </p>
                    <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                      <span>版本：<span className="text-foreground">{charDetail.versions.length} 个</span></span>
                    </div>
                  </div>
                </div>
              </div>

              {/* 标签页工作区 */}
              <Tabs value={activeWorkspaceTab} onValueChange={(value) => setActiveWorkspaceTab(value as 'studio' | 'versions' | 'details')} className="space-y-4">
                <TabsList>
                  <TabsTrigger value="studio">角色出图工作区</TabsTrigger>
                  <TabsTrigger value="versions">角色版本</TabsTrigger>
                  <TabsTrigger value="details">角色信息</TabsTrigger>
                </TabsList>

                <TabsContent value="studio" className="space-y-6">
                  {charDetail.versions.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <ImageIcon className="h-12 w-12 mx-auto mb-3 opacity-50" />
                      <p>请先创建角色版本</p>
                      <p className="text-sm">在"角色版本"标签页创建版本后再生成图片</p>
                    </div>
                  ) : !selectedVersionId ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <ImageIcon className="h-12 w-12 mx-auto mb-3 opacity-50" />
                      <p>请选择一个版本</p>
                    </div>
                  ) : (
                    <CharacterStudioWorkspace
                      projectId={projectIdNum}
                      charDetail={charDetail}
                      selectedVersionId={selectedVersionId}
                      onRefresh={loadCharDetail}
                      onVersionChange={setSelectedVersionId}
                    />
                  )}
                </TabsContent>

                {/* 角色版本 */}
                <TabsContent value="versions" className="space-y-4">
                  <Card>
                    <CardContent className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between">
                      <div>
                        <div className="font-medium text-foreground">角色版本管理</div>
                        <div className="text-sm text-muted-foreground">
                          为同一个角色维护不同阶段、形象或状态版本，并分别管理每个版本的角色图片。
                        </div>
                      </div>
                      <Button size="sm" onClick={openCreateVersionDialog}>
                        <Plus className="h-4 w-4 mr-1" />创建版本
                      </Button>
                    </CardContent>
                  </Card>
                  {charDetail.versions.length === 0 ? (
                    <Card>
                      <CardContent className="py-12 text-center text-sm text-muted-foreground">
                        当前角色还没有版本。后续可以通过版本区分不同阶段形象，并分别维护版本图库。
                      </CardContent>
                    </Card>
                  ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      {charDetail.versions.map(version => (
                        <VersionCard
                          key={version.id}
                          version={version}
                          onDelete={() => handleDeleteVersion(version.id)}
                          onOpenStudio={(versionId) => {
                            setSelectedVersionId(versionId);
                            setActiveWorkspaceTab('studio');
                          }}
                          onOpenDetail={openVersionDetailPage}
                          onEdit={() => openEditVersionDialog(version)}
                        />
                      ))}
                    </div>
                  )}
                </TabsContent>

                {/* 角色信息 */}
                <TabsContent value="details" className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle>基本信息</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">角色名称</span>
                          <p className="font-medium">{charDetail.name}</p>
                        </div>
                        <div>
                          <span className="text-muted-foreground">角色编号</span>
                          <p className="font-medium">{charDetail.char_code}</p>
                        </div>
                      </div>
                      <Separator />
                      <div>
                        <span className="text-muted-foreground text-sm">角色描述</span>
                        <p className="mt-1">{charDetail.role_description || '暂无描述'}</p>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-center">
              <div>
                <Users className="h-16 w-16 mx-auto text-muted-foreground mb-4 opacity-50" />
                <h3 className="text-lg font-semibold mb-2">选择一个角色</h3>
                <p className="text-muted-foreground">从左侧列表选择角色</p>
              </div>
            </div>
          )}
        </div>
      </div>
      <VersionDialog
        open={isVersionDialogOpen}
        onOpenChange={setIsVersionDialogOpen}
        onSubmit={handleSaveVersion}
        submitting={savingVersion}
        initialVersion={editingVersion}
      />
    </AppLayout>
  );
}
