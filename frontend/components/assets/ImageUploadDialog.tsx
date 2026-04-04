'use client';

import { useCallback, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import {
  Image as ImageIcon,
  Upload,
  Loader2,
  X,
  Plus,
  Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import { assetsApi, tasksApi, type AssetResponse, type TaskResponse } from '@/lib/api';

// 画幅比例选项
const ASPECT_RATIOS = [
  { value: '1:1', label: '1:1 (正方形)' },
  { value: '16:9', label: '16:9 (横屏)' },
  { value: '9:16', label: '9:16 (竖屏)' },
  { value: '4:3', label: '4:3' },
  { value: '3:4', label: '3:4' },
  { value: '4:5', label: '4:5' },
  { value: '5:4', label: '5:4' },
  { value: '2:3', label: '2:3' },
  { value: '3:2', label: '3:2' },
  { value: '1:4', label: '1:4' },
  { value: '4:1', label: '4:1' },
  { value: '1:8', label: '1:8' },
  { value: '8:1', label: '8:1' },
  { value: '21:9', label: '21:9 (超宽)' },
];

// 分辨率选项
const RESOLUTIONS = [
  { value: '512', label: '512px' },
  { value: '1K', label: '1K (1024px)' },
  { value: '2K', label: '2K (2048px)' },
  { value: '4K', label: '4K (4096px)' },
];

interface ImageUploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: number;
  shotId?: number;
  onAssetCreated?: (asset: AssetResponse) => void;
  onTaskTriggered?: (task: TaskResponse) => void;
}

interface ReferenceImage {
  id: string;
  file: File;
  preview: string;
}

export function ImageUploadDialog({
  open,
  onOpenChange,
  projectId,
  shotId,
  onAssetCreated,
  onTaskTriggered,
}: ImageUploadDialogProps) {
  const [activeTab, setActiveTab] = useState<'upload' | 'generate'>('upload');

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  // Generate state
  const [generating, setGenerating] = useState(false);
  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [aspectRatio, setAspectRatio] = useState('16:9');
  const [resolution, setResolution] = useState('1K');
  const [stylePreset, setStylePreset] = useState('');
  const [referenceImages, setReferenceImages] = useState<ReferenceImage[]>([]);

  // Reset state when dialog closes
  const resetState = useCallback(() => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setPrompt('');
    setNegativePrompt('');
    setAspectRatio('16:9');
    setResolution('1K');
    setStylePreset('');
    setReferenceImages((prev) => {
      prev.forEach((img) => URL.revokeObjectURL(img.preview));
      return [];
    });
  }, []);

  const handleOpenChange = useCallback(
    (newOpen: boolean) => {
      if (!newOpen) {
        resetState();
      }
      onOpenChange(newOpen);
    },
    [onOpenChange, resetState]
  );

  // File selection handler
  const handleFileSelect = useCallback((file: File) => {
    const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
    if (!validTypes.includes(file.type)) {
      toast.error('不支持的文件类型', {
        description: '请选择 JPG、PNG、WebP 或 GIF 格式的图片',
      });
      return;
    }

    // Check file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
      toast.error('文件太大', {
        description: '图片大小不能超过 10MB',
      });
      return;
    }

    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleFileSelect(file);
      }
    },
    [handleFileSelect]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragActive(false);
      const file = e.dataTransfer?.files?.[0];
      if (file) {
        handleFileSelect(file);
      }
    },
    [handleFileSelect]
  );

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(false);
  }, []);

  // Upload handler
  const handleUpload = useCallback(async () => {
    if (!selectedFile) return;

    setUploading(true);
    try {
      const asset = await assetsApi.upload(projectId, selectedFile, shotId);
      toast.success('上传成功');
      onAssetCreated?.(asset);
      handleOpenChange(false);
    } catch (error) {
      toast.error('上传失败', {
        description: error instanceof Error ? error.message : '未知错误',
      });
    } finally {
      setUploading(false);
    }
  }, [selectedFile, projectId, shotId, onAssetCreated, handleOpenChange]);

  // Reference image handlers
  const handleAddReferenceImage = useCallback(
    (file: File) => {
      if (referenceImages.length >= 5) {
        toast.error('参考图数量已达上限', {
          description: '最多只能添加 5 张参考图',
        });
        return;
      }

      const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
      if (!validTypes.includes(file.type)) {
        toast.error('不支持的文件类型');
        return;
      }

      const preview = URL.createObjectURL(file);
      setReferenceImages((prev) => [
        ...prev,
        { id: `${Date.now()}-${Math.random()}`, file, preview },
      ]);
    },
    [referenceImages.length]
  );

  const handleRemoveReferenceImage = useCallback((id: string) => {
    setReferenceImages((prev) => {
      const img = prev.find((i) => i.id === id);
      if (img) {
        URL.revokeObjectURL(img.preview);
      }
      return prev.filter((i) => i.id !== id);
    });
  }, []);

  // Generate handler
  const handleGenerate = useCallback(async () => {
    if (!prompt.trim()) {
      toast.error('请输入提示词');
      return;
    }

    setGenerating(true);
    try {
      // If there are reference images, upload them first to get URLs
      let referenceUrls: string[] = [];
      if (referenceImages.length > 0) {
        const uploadPromises = referenceImages.map(async (img) => {
          const asset = await assetsApi.upload(projectId, img.file);
          return asset.file_url;
        });
        referenceUrls = await Promise.all(uploadPromises);
      }

      const task = await tasksApi.triggerImage({
        project_id: projectId,
        shot_id: shotId,
        prompt: prompt.trim(),
        negative_prompt: negativePrompt.trim() || undefined,
        aspect_ratio: aspectRatio,
        resolution,
        style_preset: stylePreset.trim() || undefined,
        reference_image_urls: referenceUrls.length > 0 ? referenceUrls : undefined,
        save_to_shot: true,
      });

      toast.success('图像生成任务已提交');
      onTaskTriggered?.(task);
      handleOpenChange(false);
    } catch (error) {
      toast.error('提交失败', {
        description: error instanceof Error ? error.message : '未知错误',
      });
    } finally {
      setGenerating(false);
    }
  }, [
    prompt,
    negativePrompt,
    aspectRatio,
    resolution,
    stylePreset,
    referenceImages,
    projectId,
    shotId,
    onTaskTriggered,
    handleOpenChange,
  ]);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-2xl gap-0 p-0 overflow-hidden">
        <DialogHeader className="px-6 pt-6 pb-4 border-b">
          <DialogTitle className="text-lg font-semibold">添加素材</DialogTitle>
        </DialogHeader>

        <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as 'upload' | 'generate')}
          className="w-full"
        >
          <div className="px-6 pt-4">
            <TabsList className="grid w-full grid-cols-2 h-11">
              <TabsTrigger value="upload" className="flex items-center gap-2 text-sm font-medium">
                <Upload className="h-4 w-4" />
                <span>上传图片</span>
              </TabsTrigger>
              <TabsTrigger value="generate" className="flex items-center gap-2 text-sm font-medium">
                <ImageIcon className="h-4 w-4" />
                <span>AI 生成</span>
              </TabsTrigger>
            </TabsList>
          </div>

          <div className="px-6 pb-6">

          {/* Upload Tab */}
          <TabsContent value="upload" className="mt-4 space-y-4">
            <div
              className={`relative border-2 border-dashed rounded-xl p-10 transition-all duration-200 cursor-pointer group ${
                dragActive
                  ? 'border-primary bg-primary/10 shadow-lg shadow-primary/10'
                  : 'border-border/60 hover:border-primary/70 hover:bg-secondary/30'
              }`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => document.getElementById('file-input')?.click()}
            >
              <div className="flex flex-col items-center justify-center gap-3">
                <div className={`p-4 rounded-full transition-colors ${
                  dragActive ? 'bg-primary/20 text-primary' : 'bg-secondary text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary'
                }`}>
                  <Upload className="h-8 w-8" />
                </div>
                <div className="text-center">
                  <p className="text-base font-medium text-foreground">拖拽图片到此处或点击选择</p>
                  <p className="text-sm text-muted-foreground mt-1">支持 JPG、PNG、WebP、GIF，最大 10MB</p>
                </div>
                <input
                  id="file-input"
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleInputChange}
                />
              </div>
            </div>

            {previewUrl && (
              <div className="relative inline-flex justify-center w-full">
                <div className="relative group">
                  <img
                    src={previewUrl}
                    alt="预览"
                    className="max-h-56 rounded-xl object-contain shadow-lg ring-1 ring-border/50"
                  />
                  <button
                    className="absolute -top-2 -right-2 h-7 w-7 rounded-full bg-secondary/80 backdrop-blur-sm border border-border/50 text-muted-foreground hover:bg-destructive hover:text-destructive-foreground hover:border-destructive transition-all duration-200 flex items-center justify-center opacity-0 group-hover:opacity-100"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFile(null);
                      setPreviewUrl(null);
                    }}
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <Button variant="outline" onClick={() => handleOpenChange(false)}>
                取消
              </Button>
              <Button onClick={handleUpload} disabled={!selectedFile || uploading} className="min-w-[100px]">
                {uploading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    上传中...
                  </>
                ) : (
                  '确认上传'
                )}
              </Button>
            </div>
          </TabsContent>

          {/* Generate Tab */}
          <TabsContent value="generate" className="mt-4 space-y-4">
            <div className="space-y-4">
              <div>
                <Label htmlFor="prompt" className="text-sm font-medium">正向提示词 <span className="text-destructive">*</span></Label>
                <Textarea
                  id="prompt"
                  placeholder="描述想要生成的画面..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  rows={3}
                  className="mt-1.5 resize-none"
                />
              </div>

              <div>
                <Label htmlFor="negative-prompt" className="text-sm font-medium text-muted-foreground">负向提示词 <span className="text-xs">(可选)</span></Label>
                <Input
                  id="negative-prompt"
                  placeholder="描述不想要出现的元素..."
                  value={negativePrompt}
                  onChange={(e) => setNegativePrompt(e.target.value)}
                  className="mt-1.5"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm font-medium">画幅比例</Label>
                  <Select value={aspectRatio} onValueChange={setAspectRatio}>
                    <SelectTrigger className="mt-1.5">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ASPECT_RATIOS.map((ar) => (
                        <SelectItem key={ar.value} value={ar.value}>
                          {ar.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label className="text-sm font-medium">分辨率</Label>
                  <Select value={resolution} onValueChange={setResolution}>
                    <SelectTrigger className="mt-1.5">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {RESOLUTIONS.map((r) => (
                        <SelectItem key={r.value} value={r.value}>
                          {r.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div>
                <Label htmlFor="style-preset" className="text-sm font-medium text-muted-foreground">风格预设 <span className="text-xs">(可选)</span></Label>
                <Input
                  id="style-preset"
                  placeholder="cinematic, anime, realistic..."
                  value={stylePreset}
                  onChange={(e) => setStylePreset(e.target.value)}
                  className="mt-1.5"
                />
              </div>

              {/* Reference Images */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label className="text-sm font-medium text-muted-foreground">参考图 <span className="text-xs">(可选，最多 5 张)</span></Label>
                  <Badge variant="secondary" className="text-xs">{referenceImages.length}/5</Badge>
                </div>

                <div className="rounded-xl border border-border/60 overflow-hidden">
                  <ScrollArea className="h-36">
                    <div className="p-3 space-y-2">
                      {referenceImages.map((img) => (
                        <div
                          key={img.id}
                          className="flex items-center gap-3 p-2 rounded-lg bg-secondary/40 group hover:bg-secondary/60 transition-colors"
                        >
                          <img
                            src={img.preview}
                            alt=""
                            className="h-12 w-12 rounded-lg object-cover ring-1 ring-border/30"
                          />
                          <span className="flex-1 text-sm truncate text-foreground/80">
                            {img.file.name}
                          </span>
                          <button
                            className="h-8 w-8 rounded-lg flex items-center justify-center text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                            onClick={() => handleRemoveReferenceImage(img.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      ))}

                      {referenceImages.length < 5 && (
                        <label className="flex items-center justify-center gap-2 p-4 border-2 border-dashed rounded-xl cursor-pointer hover:border-primary/70 hover:bg-secondary/30 text-muted-foreground hover:text-foreground transition-all duration-200 group">
                          <div className="p-2 rounded-full bg-secondary group-hover:bg-primary/10 transition-colors">
                            <Plus className="h-4 w-4" />
                          </div>
                          <span className="text-sm font-medium">添加参考图</span>
                          <input
                            type="file"
                            accept="image/*"
                            className="hidden"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) {
                                handleAddReferenceImage(file);
                              }
                              e.target.value = '';
                            }}
                          />
                        </label>
                      )}
                    </div>
                  </ScrollArea>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2 border-t">
              <Button variant="outline" onClick={() => handleOpenChange(false)}>
                取消
              </Button>
              <Button
                onClick={handleGenerate}
                disabled={!prompt.trim() || generating}
                className="min-w-[100px]"
              >
                {generating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    提交中...
                  </>
                ) : (
                  '生成图像'
                )}
              </Button>
            </div>
          </TabsContent>
          </div>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
