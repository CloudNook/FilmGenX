'use client';

import { use, useEffect, useState, useCallback, useMemo, useRef } from 'react';
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
} from 'lucide-react';
import { toast } from 'sonner';

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

// 角色出图工作区标签页
function StudioTabs({
  projectId,
  characterId,
  characterName,
  referenceVersionId,
  referenceImages,
  onRefresh,
}: {
  projectId: number;
  characterId: number;
  characterName: string;
  referenceVersionId: number | null;
  referenceImages: string[];
  onRefresh: () => void;
}) {
  // 文生图状态
  const [textPrompt, setTextPrompt] = useState('');
  const [textNegativePrompt, setTextNegativePrompt] = useState('');
  const [textAspectRatio, setTextAspectRatio] = useState('2:3');
  const [textResolution, setTextResolution] = useState('1K');
  const [textGenerating, setTextGenerating] = useState(false);

  // 图生图状态
  const [imgPrompt, setImgPrompt] = useState('');
  const [imgNegativePrompt, setImgNegativePrompt] = useState('');
  const [imgAspectRatio, setImgAspectRatio] = useState('2:3');
  const [imgResolution, setImgResolution] = useState('1K');
  const [selectedRefImages, setSelectedRefImages] = useState<string[]>([]);
  const [imgGenerating, setImgGenerating] = useState(false);

  // 上传状态
  const [uploadFiles, setUploadFiles] = useState<PendingImageFile[]>([]);
  const [uploading, setUploading] = useState(false);

  // 生成唯一ID
  const generateId = () => Math.random().toString(36).substring(2, 9);

  // 添加待上传文件
  const addPendingFiles = (files: FileList | null, type: 'upload') => {
    if (!files) return;
    const newFiles: PendingImageFile[] = Array.from(files).map((file) => ({
      id: generateId(),
      file,
      preview: URL.createObjectURL(file),
    }));
    setUploadFiles((prev) => [...prev, ...newFiles]);
  };

  // 移除待上传文件
  const removePendingFile = (id: string, type: 'upload') => {
    setUploadFiles((prev) => {
      const item = prev.find((f) => f.id === id);
      if (item) URL.revokeObjectURL(item.preview);
      return prev.filter((f) => f.id !== id);
    });
  };

  // 文生图
  const handleGenerateFromPrompt = async () => {
    if (!textPrompt.trim()) return;
    setTextGenerating(true);
    try {
      const result = await tasksApi.triggerImage({
        project_id: projectId,
        character_id: characterId,
        character_version_id: referenceVersionId || undefined,
        prompt: textPrompt,
        negative_prompt: textNegativePrompt || undefined,
        aspect_ratio: textAspectRatio,
        resolution: textResolution,
        save_to_shot: true,
      });
      toast.success('生成任务已提交');
      pollTask(result.id, () => {
        setTextGenerating(false);
        onRefresh();
      });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '生成失败');
      setTextGenerating(false);
    }
  };

  // 图生图
  const handleGenerateFromImage = async () => {
    if (!imgPrompt.trim() || selectedRefImages.length === 0) return;
    setImgGenerating(true);
    try {
      const result = await tasksApi.triggerImage({
        project_id: projectId,
        character_id: characterId,
        character_version_id: referenceVersionId || undefined,
        prompt: imgPrompt,
        negative_prompt: imgNegativePrompt || undefined,
        aspect_ratio: imgAspectRatio,
        resolution: imgResolution,
        reference_image_urls: selectedRefImages,
        save_to_shot: true,
      });
      toast.success('生成任务已提交');
      pollTask(result.id, () => {
        setImgGenerating(false);
        onRefresh();
      });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '生成失败');
      setImgGenerating(false);
    }
  };

  // 上传图片
  const handleUploadImages = async () => {
    if (uploadFiles.length === 0) return;
    if (!referenceVersionId) {
      toast.error('请先创建角色版本，再上传参考图');
      return;
    }
    setUploading(true);
    try {
      // 这里调用上传API
      for (const item of uploadFiles) {
        await charactersApi.uploadReferenceImage(projectId, characterId, referenceVersionId, item.file);
      }
      toast.success('上传成功');
      setUploadFiles([]);
      await Promise.resolve(onRefresh());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '上传失败');
    } finally {
      setUploading(false);
    }
  };

  // 轮询任务状态
  const pollTask = (taskId: number, onComplete: () => void) => {
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
  };

  // 切换参考图选择
  const toggleRefImage = (url: string) => {
    setSelectedRefImages((prev) =>
      prev.includes(url) ? prev.filter((u) => u !== url) : [...prev, url]
    );
  };

  return (
    <Tabs defaultValue="prompt" className="space-y-4">
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="prompt">提示词生图</TabsTrigger>
        <TabsTrigger value="upload">本地上传</TabsTrigger>
        <TabsTrigger value="img2img">图生图</TabsTrigger>
      </TabsList>

      {/* 提示词生图 */}
      <TabsContent value="prompt" className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">正向提示词</label>
          <Textarea
            value={textPrompt}
            onChange={(e) => setTextPrompt(e.target.value)}
            rows={5}
            placeholder={`描述你想要的角色形象，例如：${characterName}，古风少年，黑发飘逸，眼神坚毅，身着白色长袍...`}
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">负面提示词</label>
          <Input
            value={textNegativePrompt}
            onChange={(e) => setTextNegativePrompt(e.target.value)}
            placeholder="例如：blurry, low quality, watermark, bad anatomy"
          />
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="space-y-2">
            <label className="text-sm font-medium">画幅比例</label>
            <Select value={textAspectRatio} onValueChange={setTextAspectRatio}>
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
            <Select value={textResolution} onValueChange={setTextResolution}>
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
        <div className="flex justify-end">
          <Button onClick={handleGenerateFromPrompt} disabled={textGenerating || !textPrompt.trim()}>
            {textGenerating ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Wand2 className="mr-2 h-4 w-4" />
            )}
            生成角色图
          </Button>
        </div>
      </TabsContent>

      {/* 本地上传 */}
      <TabsContent value="upload" className="space-y-4">
        <FileDropZone
          onSelect={(files) => addPendingFiles(files, 'upload')}
          disabled={uploading}
          title="上传角色参考图"
          description="支持 JPG、PNG、WebP，单张不超过 10MB"
        />

        {uploadFiles.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {uploadFiles.map((item) => (
              <div key={item.id} className="rounded-xl border bg-secondary/20 p-2">
                <div className="relative overflow-hidden rounded-lg">
                  <img src={item.preview} alt={item.file.name} className="aspect-[2/3] w-full object-cover" />
                  <Button
                    variant="secondary"
                    size="icon"
                    className="absolute right-2 top-2 h-7 w-7"
                    onClick={() => removePendingFile(item.id, 'upload')}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
                <div className="mt-2 truncate text-xs text-muted-foreground">
                  {item.file.name}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="flex justify-end">
          <Button onClick={handleUploadImages} disabled={uploading || uploadFiles.length === 0}>
            {uploading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <ImagePlus className="mr-2 h-4 w-4" />
            )}
            保存参考图
          </Button>
        </div>
      </TabsContent>

      {/* 图生图 */}
      <TabsContent value="img2img" className="space-y-4">
        {referenceImages.length > 0 && (
          <div className="space-y-2">
            <label className="text-sm font-medium">选择参考图</label>
            <div className="grid grid-cols-4 gap-2">
              {referenceImages.map((url, idx) => (
                <div
                  key={idx}
                  className={`relative aspect-[2/3] rounded-lg overflow-hidden border-2 cursor-pointer transition-all ${
                    selectedRefImages.includes(url) ? 'border-primary' : 'border-transparent'
                  }`}
                  onClick={() => toggleRefImage(url)}
                >
                  <img src={url} alt={`ref-${idx}`} className="w-full h-full object-cover" />
                  {selectedRefImages.includes(url) && (
                    <div className="absolute inset-0 bg-primary/30 flex items-center justify-center">
                      <div className="w-5 h-5 rounded-full bg-primary text-white text-xs flex items-center justify-center">
                        {selectedRefImages.indexOf(url) + 1}
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
          <label className="text-sm font-medium">图生图提示词</label>
          <Textarea
            value={imgPrompt}
            onChange={(e) => setImgPrompt(e.target.value)}
            rows={4}
            placeholder="在已有角色基础上继续细化，例如：保留面部特征和服装风格，调整为夜间场景，加入月光效果..."
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">负面提示词</label>
          <Input
            value={imgNegativePrompt}
            onChange={(e) => setImgNegativePrompt(e.target.value)}
            placeholder="例如：deformed, extra limbs, watermark"
          />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium">画幅比例</label>
            <Select value={imgAspectRatio} onValueChange={setImgAspectRatio}>
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
            <Select value={imgResolution} onValueChange={setImgResolution}>
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
        <div className="flex justify-end">
          <Button
            onClick={handleGenerateFromImage}
            disabled={imgGenerating || !imgPrompt.trim() || selectedRefImages.length === 0}
          >
            {imgGenerating ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Wand2 className="mr-2 h-4 w-4" />
            )}
            图生图
          </Button>
        </div>
      </TabsContent>
    </Tabs>
  );
}

function CharacterStudioWorkspace({
  projectId,
  characterId,
  characterName,
  versions,
  selectedVersionId,
  onSelectVersionId,
  onRefresh,
}: {
  projectId: number;
  characterId: number;
  characterName: string;
  versions: CharacterVersionResponse[];
  selectedVersionId: number | null;
  onSelectVersionId: (versionId: number) => void;
  onRefresh: () => void;
}) {
  const activeVersion = useMemo(
    () => versions.find((version) => version.id === selectedVersionId) ?? null,
    [selectedVersionId, versions],
  );

  const availableReferenceUrls = useMemo(
    () => activeVersion ? [activeVersion.three_view_url, ...(activeVersion.reference_image_urls || [])].filter(Boolean) as string[] : [],
    [activeVersion],
  );

  const reusableVersionImages = useMemo(() => {
    if (!activeVersion) return [];

    return versions
      .filter((version) => version.id !== activeVersion.id)
      .flatMap((version) => {
        const urls = [version.three_view_url, ...(version.reference_image_urls || [])].filter(Boolean) as string[];
        return urls.map((url, index) => ({
          key: `${version.id}-${url}-${index}`,
          url,
          versionLabel: version.label,
          imageLabel: version.three_view_url === url ? '三视图' : `参考图 #${index + (version.three_view_url ? 0 : 1)}`,
        }));
      })
      .filter((item, index, arr) => arr.findIndex((candidate) => candidate.url === item.url) === index)
      .filter((item) => !availableReferenceUrls.includes(item.url));
  }, [activeVersion, availableReferenceUrls, versions]);

  const [textPrompt, setTextPrompt] = useState('');
  const [textNegativePrompt, setTextNegativePrompt] = useState('');
  const [textAspectRatio, setTextAspectRatio] = useState('2:3');
  const [textResolution, setTextResolution] = useState('1K');
  const [textGenerating, setTextGenerating] = useState(false);

  const [imgPrompt, setImgPrompt] = useState('');
  const [imgNegativePrompt, setImgNegativePrompt] = useState('');
  const [imgAspectRatio, setImgAspectRatio] = useState('2:3');
  const [imgResolution, setImgResolution] = useState('1K');
  const [selectedReferenceUrls, setSelectedReferenceUrls] = useState<string[]>([]);
  const [imgGenerating, setImgGenerating] = useState(false);

  const [uploadFiles, setUploadFiles] = useState<PendingImageFile[]>([]);
  const [img2imgFiles, setImg2imgFiles] = useState<PendingImageFile[]>([]);
  const [uploadingReferenceImages, setUploadingReferenceImages] = useState(false);
  const [uploadingThreeView, setUploadingThreeView] = useState(false);
  const [deletingThreeView, setDeletingThreeView] = useState(false);
  const [deletingReferenceIndex, setDeletingReferenceIndex] = useState<number | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const uploadFilesRef = useRef<PendingImageFile[]>([]);
  const img2imgFilesRef = useRef<PendingImageFile[]>([]);

  const resetPreviewFiles = useCallback((files: PendingImageFile[]) => {
    files.forEach((item) => URL.revokeObjectURL(item.preview));
  }, []);

  useEffect(() => {
    uploadFilesRef.current = uploadFiles;
  }, [uploadFiles]);

  useEffect(() => {
    img2imgFilesRef.current = img2imgFiles;
  }, [img2imgFiles]);

  useEffect(() => {
    return () => {
      resetPreviewFiles(uploadFilesRef.current);
      resetPreviewFiles(img2imgFilesRef.current);
    };
  }, [resetPreviewFiles]);

  useEffect(() => {
    setSelectedReferenceUrls((prev) => {
      if (prev.length === 0) {
        return availableReferenceUrls.slice(0, 5);
      }
      return prev.filter((url) => availableReferenceUrls.includes(url));
    });
  }, [availableReferenceUrls]);

  const waitForTask = useCallback(async (taskId: number) => {
    let attempts = 0;
    while (attempts < 60) {
      const task = await tasksApi.get(taskId);
      if (task.status === 'success') return;
      if (task.status === 'failed') throw new Error(task.error_message || '生成失败');
      attempts += 1;
      await new Promise((resolve) => setTimeout(resolve, 5000));
    }
    throw new Error('生成时间较长，请稍后刷新查看');
  }, []);

  const addPendingFiles = useCallback((files: FileList | null, target: 'upload' | 'img2img') => {
    if (!files || files.length === 0) return;

    const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
    const nextFiles: PendingImageFile[] = [];

    Array.from(files).forEach((file) => {
      if (!validTypes.includes(file.type)) {
        toast.error(`${file.name} 不是支持的图片格式`);
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        toast.error(`${file.name} 超过 10MB 限制`);
        return;
      }
      nextFiles.push({
        id: `${Date.now()}-${Math.random()}`,
        file,
        preview: URL.createObjectURL(file),
      });
    });

    if (nextFiles.length === 0) return;

    if (target === 'upload') {
      setUploadFiles((prev) => [...prev, ...nextFiles].slice(0, 10));
    } else {
      setImg2imgFiles((prev) => [...prev, ...nextFiles].slice(0, 5));
    }
  }, []);

  const removePendingFile = useCallback((id: string, target: 'upload' | 'img2img') => {
    const setter = target === 'upload' ? setUploadFiles : setImg2imgFiles;
    setter((prev) => {
      const removed = prev.find((item) => item.id === id);
      if (removed) URL.revokeObjectURL(removed.preview);
      return prev.filter((item) => item.id !== id);
    });
  }, []);

  const uploadReferenceFiles = useCallback(async (files: PendingImageFile[]) => {
    if (!activeVersion) throw new Error('请先选择角色版本');

    let latestVersion = activeVersion;
    for (const item of files) {
      latestVersion = await charactersApi.uploadReferenceImage(projectId, characterId, activeVersion.id, item.file);
    }

    return (latestVersion.reference_image_urls || []).filter((url) => !(activeVersion.reference_image_urls || []).includes(url));
  }, [activeVersion, characterId, projectId]);

  const handleUploadReferenceImages = useCallback(async () => {
    if (!activeVersion || uploadFiles.length === 0) return;

    setUploadingReferenceImages(true);
    try {
      await uploadReferenceFiles(uploadFiles);
      toast.success('角色参考图上传成功');
      resetPreviewFiles(uploadFiles);
      setUploadFiles([]);
      await Promise.resolve(onRefresh());
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '上传失败');
    } finally {
      setUploadingReferenceImages(false);
    }
  }, [activeVersion, onRefresh, resetPreviewFiles, uploadFiles, uploadReferenceFiles]);

  const handleUploadThreeView = useCallback(async (files: FileList | null) => {
    if (!activeVersion) {
      toast.error('请先选择角色版本');
      return;
    }
    const file = files?.[0];
    if (!file) return;

    setUploadingThreeView(true);
    try {
      await charactersApi.uploadThreeViewImage(projectId, characterId, activeVersion.id, file);
      toast.success('三视图上传成功');
      await Promise.resolve(onRefresh());
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '上传失败');
    } finally {
      setUploadingThreeView(false);
    }
  }, [activeVersion, characterId, onRefresh, projectId]);

  const handleDeleteThreeView = useCallback(async () => {
    if (!activeVersion?.three_view_url) return;

    setDeletingThreeView(true);
    try {
      await charactersApi.deleteThreeViewImage(projectId, characterId, activeVersion.id);
      setSelectedReferenceUrls((prev) => prev.filter((url) => url !== activeVersion.three_view_url));
      toast.success('三视图已删除');
      await Promise.resolve(onRefresh());
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '删除失败');
    } finally {
      setDeletingThreeView(false);
    }
  }, [activeVersion, characterId, onRefresh, projectId]);

  const handleDeleteReferenceImage = useCallback(async (index: number) => {
    if (!activeVersion) return;

    setDeletingReferenceIndex(index);
    try {
      const targetUrl = activeVersion.reference_image_urls?.[index];
      await charactersApi.deleteReferenceImage(projectId, characterId, activeVersion.id, index);
      if (targetUrl) {
        setSelectedReferenceUrls((prev) => prev.filter((url) => url !== targetUrl));
      }
      toast.success('角色参考图已删除');
      await Promise.resolve(onRefresh());
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '删除失败');
    } finally {
      setDeletingReferenceIndex(null);
    }
  }, [activeVersion, characterId, onRefresh, projectId]);

  const handleAddReusableImage = useCallback(async (url: string) => {
    if (!activeVersion) return;

    try {
      await charactersApi.updateVersion(projectId, characterId, activeVersion.id, {
        reference_image_urls: Array.from(new Set([...(activeVersion.reference_image_urls || []), url])),
      });
      toast.success('已加入当前版本图库');
      await Promise.resolve(onRefresh());
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '加入图库失败');
    }
  }, [activeVersion, characterId, onRefresh, projectId]);

  const toggleReferenceSelection = useCallback((url: string) => {
    setSelectedReferenceUrls((prev) => {
      if (prev.includes(url)) {
        return prev.filter((item) => item !== url);
      }
      if (prev.length >= 5) {
        toast.error('图生图最多使用 5 张参考图');
        return prev;
      }
      return [...prev, url];
    });
  }, []);

  const handleGenerateFromPrompt = useCallback(async () => {
    if (!activeVersion || !textPrompt.trim()) {
      toast.error('请先输入提示词');
      return;
    }

    setTextGenerating(true);
    try {
      const task = await tasksApi.triggerImage({
        project_id: projectId,
        character_id: characterId,
        character_version_id: activeVersion.id,
        prompt: textPrompt.trim(),
        negative_prompt: textNegativePrompt.trim() || undefined,
        aspect_ratio: textAspectRatio,
        resolution: textResolution,
        save_to_shot: true,
      });
      toast.success('角色图生成任务已提交');
      await waitForTask(task.id);
      await Promise.resolve(onRefresh());
      toast.success('角色图生成完成');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '生成失败');
    } finally {
      setTextGenerating(false);
    }
  }, [activeVersion, characterId, onRefresh, projectId, textAspectRatio, textNegativePrompt, textPrompt, textResolution, waitForTask]);

  const handleGenerateFromImage = useCallback(async () => {
    if (!activeVersion || !imgPrompt.trim()) {
      toast.error('请先输入图生图提示词');
      return;
    }
    if (selectedReferenceUrls.length === 0 && img2imgFiles.length === 0) {
      toast.error('请至少选择或上传一张参考图');
      return;
    }

    setImgGenerating(true);
    try {
      const uploadedUrls = img2imgFiles.length > 0 ? await uploadReferenceFiles(img2imgFiles) : [];
      const referenceUrls = Array.from(new Set([...selectedReferenceUrls, ...uploadedUrls])).slice(0, 5);
      const task = await tasksApi.triggerImage({
        project_id: projectId,
        character_id: characterId,
        character_version_id: activeVersion.id,
        prompt: imgPrompt.trim(),
        negative_prompt: imgNegativePrompt.trim() || undefined,
        aspect_ratio: imgAspectRatio,
        resolution: imgResolution,
        reference_image_urls: referenceUrls,
        save_to_shot: true,
      });
      toast.success('图生图任务已提交');
      await waitForTask(task.id);
      resetPreviewFiles(img2imgFiles);
      setImg2imgFiles([]);
      await Promise.resolve(onRefresh());
      toast.success('图生图生成完成');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '图生图失败');
    } finally {
      setImgGenerating(false);
    }
  }, [activeVersion, characterId, img2imgFiles, imgAspectRatio, imgNegativePrompt, imgPrompt, imgResolution, onRefresh, projectId, resetPreviewFiles, selectedReferenceUrls, uploadReferenceFiles, waitForTask]);

  if (!activeVersion) {
    return (
      <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
        请先创建并选择一个角色版本。
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="font-medium text-foreground">当前出图目标</div>
            <div className="text-sm text-muted-foreground">
              选择角色版本后，上传、生成、图库展示和落库都会自动切换到对应目标。
            </div>
          </div>
          <div className="w-full md:w-72">
            <Select value={String(activeVersion.id)} onValueChange={(value) => onSelectVersionId(Number(value))}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {versions.map((version) => (
                  <SelectItem key={version.id} value={String(version.id)}>
                    {version.label} ({version.version_code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <CardHeader>
            <CardTitle>{activeVersion.label} 生成与上传</CardTitle>
            <CardDescription>
              当前上传、文生图和图生图结果会同步保存到该版本。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Tabs defaultValue="prompt" className="space-y-4">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="prompt">提示词生图</TabsTrigger>
                <TabsTrigger value="img2img">图生图</TabsTrigger>
              </TabsList>

              <TabsContent value="prompt" className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">正向提示词</label>
                  <Textarea
                    value={textPrompt}
                    onChange={(event) => setTextPrompt(event.target.value)}
                    rows={5}
                    placeholder={`描述你想要的角色形象，例如：${characterName}，古风少年，黑发飘逸，眼神坚毅，身着白色长袍...`}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">负面提示词</label>
                  <Input
                    value={textNegativePrompt}
                    onChange={(event) => setTextNegativePrompt(event.target.value)}
                    placeholder="例如：blurry, low quality, watermark, bad anatomy"
                  />
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">画幅比例</label>
                    <Select value={textAspectRatio} onValueChange={setTextAspectRatio}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ASPECT_RATIOS.map((item) => (
                          <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">分辨率</label>
                    <Select value={textResolution} onValueChange={setTextResolution}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {RESOLUTIONS.map((item) => (
                          <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="flex justify-end">
                  <Button onClick={handleGenerateFromPrompt} disabled={textGenerating || !textPrompt.trim()}>
                    {textGenerating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Wand2 className="mr-2 h-4 w-4" />}
                    生成角色图
                  </Button>
                </div>
              </TabsContent>

              <TabsContent value="img2img" className="space-y-4">
                {selectedReferenceUrls.length > 0 ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium">选择已有参考图</div>
                        <div className="text-xs text-muted-foreground">可多选，最多 5 张</div>
                      </div>
                      <Badge variant="secondary">{selectedReferenceUrls.length}/5</Badge>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {selectedReferenceUrls.map((url) => (
                        <button
                          key={url}
                          type="button"
                          onClick={() => toggleReferenceSelection(url)}
                          className="overflow-hidden rounded-xl border border-primary ring-2 ring-primary/20 text-left transition"
                        >
                          <img src={url} alt="" className="aspect-[2/3] w-full object-cover" />
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null}

                <div className="space-y-2">
                  <label className="text-sm font-medium">图生图提示词</label>
                  <Textarea
                    value={imgPrompt}
                    onChange={(event) => setImgPrompt(event.target.value)}
                    rows={4}
                    placeholder="在已有角色基础上继续细化，例如：保留面部特征和服装风格，调整为夜间场景，加入月光效果..."
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">负面提示词</label>
                  <Input
                    value={imgNegativePrompt}
                    onChange={(event) => setImgNegativePrompt(event.target.value)}
                    placeholder="例如：deformed, extra limbs, watermark"
                  />
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">画幅比例</label>
                    <Select value={imgAspectRatio} onValueChange={setImgAspectRatio}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ASPECT_RATIOS.map((item) => (
                          <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">分辨率</label>
                    <Select value={imgResolution} onValueChange={setImgResolution}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {RESOLUTIONS.map((item) => (
                          <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <Separator />

                <div className="space-y-3">
                  <div>
                    <div className="text-sm font-medium">补充新的图生图参考图</div>
                    <div className="text-xs text-muted-foreground">上传后会自动保存到当前角色版本图库。</div>
                  </div>
                  <FileDropZone
                    onSelect={(files) => addPendingFiles(files, 'img2img')}
                    disabled={imgGenerating}
                    title="添加参考图"
                    description="可补充新的底图或动作角度参考"
                  />
                  {img2imgFiles.length > 0 ? (
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {img2imgFiles.map((item) => (
                        <div key={item.id} className="rounded-xl border bg-secondary/20 p-2">
                          <div className="relative overflow-hidden rounded-lg">
                            <img src={item.preview} alt={item.file.name} className="aspect-[2/3] w-full object-cover" />
                            <Button
                              variant="secondary"
                              size="icon"
                              className="absolute right-2 top-2 h-7 w-7"
                              onClick={() => removePendingFile(item.id, 'img2img')}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                          <div className="mt-2 truncate text-xs text-muted-foreground">{item.file.name}</div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
                <div className="flex justify-end">
                  <Button onClick={handleGenerateFromImage} disabled={imgGenerating || !imgPrompt.trim()}>
                    {imgGenerating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
                    根据参考图生成
                  </Button>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{activeVersion.label} 版本图库</CardTitle>
            <CardDescription>
              右侧展示当前版本的三视图与角色素材图，也可以复用其他版本的图片加入当前版本图库。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-medium">当前版本三视图</div>
                  <div className="text-xs text-muted-foreground">三视图会作为角色形象锚点，也可直接参与图生图参考。</div>
                </div>
                {activeVersion.three_view_url ? (
                  <Button variant="ghost" size="sm" onClick={handleDeleteThreeView} disabled={deletingThreeView}>
                    {deletingThreeView ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Trash2 className="mr-2 h-4 w-4" />}
                    删除三视图
                  </Button>
                ) : null}
              </div>

              {activeVersion.three_view_url ? (
                <div className="overflow-hidden rounded-xl border bg-card">
                  <img src={activeVersion.three_view_url} alt="三视图" className="aspect-[2/3] w-full object-cover" />
                  <div className="flex items-center justify-between gap-2 p-3">
                    <div className="text-xs text-muted-foreground">三视图</div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant={selectedReferenceUrls.includes(activeVersion.three_view_url) ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => toggleReferenceSelection(activeVersion.three_view_url!)}
                      >
                        {selectedReferenceUrls.includes(activeVersion.three_view_url) ? '已选中' : '设为参考图'}
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => setPreviewUrl(activeVersion.three_view_url)}>
                        <Eye className="mr-1 h-3 w-3" />
                        预览
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                <FileDropZone
                  onSelect={handleUploadThreeView}
                  disabled={uploadingThreeView}
                  title="上传三视图"
                  description="支持点击选择和拖拽上传，用于固定当前版本角色形象"
                />
              )}
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-medium">上传到当前版本图库</div>
                  <div className="text-xs text-muted-foreground">点击或拖拽上传角色参考图，保存后会归档到当前版本。</div>
                </div>
                {uploadFiles.length > 0 ? (
                  <Button onClick={handleUploadReferenceImages} disabled={uploadingReferenceImages}>
                    {uploadingReferenceImages ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ImagePlus className="mr-2 h-4 w-4" />}
                    保存到当前版本
                  </Button>
                ) : null}
              </div>

              <FileDropZone
                onSelect={(files) => addPendingFiles(files, 'upload')}
                disabled={uploadingReferenceImages}
                title="上传角色参考图"
                description="支持点击选择和拖拽上传，JPG / PNG / WebP / GIF，单张不超过 10MB"
              />

              {uploadFiles.length > 0 ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  {uploadFiles.map((item) => (
                    <div key={item.id} className="rounded-xl border bg-secondary/20 p-2">
                      <div className="relative overflow-hidden rounded-lg">
                        <img src={item.preview} alt={item.file.name} className="aspect-[2/3] w-full object-cover" />
                        <Button
                          variant="secondary"
                          size="icon"
                          className="absolute right-2 top-2 h-7 w-7"
                          onClick={() => removePendingFile(item.id, 'upload')}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                      <div className="mt-2 truncate text-xs text-muted-foreground">{item.file.name}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>

            {activeVersion.reference_image_urls?.length === 0 ? (
              <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
                还没有角色参考图。你可以先输入提示词生成一张，或者上传本地图片。
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                {activeVersion.reference_image_urls?.map((url, index) => (
                  <div key={`${url}-${index}`} className="overflow-hidden rounded-xl border bg-card">
                    <img src={url} alt={`角色参考图 ${index + 1}`} className="aspect-[2/3] w-full object-cover" />
                    <div className="flex items-center justify-between gap-2 p-3">
                      <div className="text-xs text-muted-foreground">参考图 #{index + 1}</div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant={selectedReferenceUrls.includes(url) ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => toggleReferenceSelection(url)}
                        >
                          {selectedReferenceUrls.includes(url) ? '已选中' : '设为参考图'}
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => setPreviewUrl(url)}>
                          <Eye className="mr-1 h-3 w-3" />
                          预览
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeleteReferenceImage(index)}
                          disabled={deletingReferenceIndex === index}
                        >
                          {deletingReferenceIndex === index ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                          )}
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {reusableVersionImages.length > 0 ? (
              <div className="space-y-3">
                <div>
                  <div className="text-sm font-medium">其他版本可复用角色图</div>
                  <div className="text-xs text-muted-foreground">可直接加入当前版本图库，复用同一角色的其他版本素材。</div>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  {reusableVersionImages.map((item) => (
                    <div key={item.key} className="overflow-hidden rounded-xl border bg-card">
                      <img src={item.url} alt={item.versionLabel} className="aspect-[2/3] w-full object-cover" />
                      <div className="flex items-center justify-between gap-2 p-3">
                        <div>
                          <div className="text-xs text-muted-foreground">{item.versionLabel}</div>
                          <div className="text-xs text-muted-foreground">{item.imageLabel}</div>
                        </div>
                        <Button size="sm" variant="outline" onClick={() => handleAddReusableImage(item.url)}>
                          加入当前图库
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <FullscreenPreview url={previewUrl} open={!!previewUrl} onOpenChange={() => setPreviewUrl(null)} />
    </div>
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
}: {
  version: CharacterVersionResponse;
  onDelete: () => void;
  onOpenStudio: (versionId: number) => void;
}) {
  const previewImages = [version.three_view_url, ...(version.reference_image_urls || [])].filter(Boolean) as string[];
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
                <img src={url} alt="" className="aspect-[2/3] w-full object-cover" />
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

// 创建版本对话框
function CreateVersionDialog({ open, onOpenChange, onCreate, creating }: { open: boolean; onOpenChange: (open: boolean) => void; onCreate: (data: { version_code: string; label: string }) => void; creating: boolean }) {
  const [versionCode, setVersionCode] = useState('');
  const [label, setLabel] = useState('');

  useEffect(() => {
    if (!open) { setVersionCode(''); setLabel(''); }
  }, [open]);

  const handleCreate = () => {
    if (!versionCode.trim() || !label.trim()) return;
    onCreate({ version_code: versionCode.trim(), label: label.trim() });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>创建角色版本</DialogTitle>
          <DialogDescription>为角色创建一个新的版本，用于管理不同阶段的形象</DialogDescription>
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
          <Button onClick={handleCreate} disabled={!versionCode.trim() || !label.trim() || creating}>
            {creating && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}创建
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// 主页面
export default function CharactersPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = use(params);
  const projectIdNum = Number(projectId);

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [characters, setCharacters] = useState<CharacterResponse[]>([]);
  const [selectedCharId, setSelectedCharId] = useState<number | null>(null);
  const [charDetail, setCharDetail] = useState<CharacterDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newCharName, setNewCharName] = useState('');
  const [newCharCode, setNewCharCode] = useState('');
  const [newCharDesc, setNewCharDesc] = useState('');
  const [creating, setCreating] = useState(false);
  const [isCreateVersionOpen, setIsCreateVersionOpen] = useState(false);
  const [creatingVersion, setCreatingVersion] = useState(false);
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState<'studio' | 'versions' | 'details'>('studio');
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);

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

  const handleCreateCharacter = useCallback(async () => {
    if (!newCharName.trim() || !newCharCode.trim()) return;
    setCreating(true);
    try {
      const char = await charactersApi.create(projectIdNum, { char_code: newCharCode.trim(), name: newCharName.trim(), role_description: newCharDesc.trim() || undefined });
      setCharacters(prev => [char, ...prev]);
      setSelectedCharId(char.id);
      setIsCreateDialogOpen(false);
      setNewCharName(''); setNewCharCode(''); setNewCharDesc('');
      toast.success('角色创建成功');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '创建失败');
    } finally {
      setCreating(false);
    }
  }, [projectIdNum, newCharName, newCharCode, newCharDesc]);

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

  const handleCreateVersion = useCallback(async (data: { version_code: string; label: string }) => {
    if (!selectedCharId) return;
    setCreatingVersion(true);
    try {
      await charactersApi.createVersion(projectIdNum, selectedCharId, data);
      toast.success('版本创建成功');
      setIsCreateVersionOpen(false);
      loadCharDetail();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '创建失败');
    } finally {
      setCreatingVersion(false);
    }
  }, [projectIdNum, selectedCharId, loadCharDetail]);

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
                  <div className="space-y-2"><label className="text-sm font-medium">角色编号 *</label><Input placeholder="如 CHAR_XIAO_YAN" value={newCharCode} onChange={(e) => setNewCharCode(e.target.value)} /></div>
                  <div className="space-y-2"><label className="text-sm font-medium">角色描述</label><Textarea placeholder="描述角色的背景..." rows={3} value={newCharDesc} onChange={(e) => setNewCharDesc(e.target.value)} /></div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>取消</Button>
                  <Button onClick={handleCreateCharacter} disabled={!newCharName.trim() || !newCharCode.trim() || creating}>{creating && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}创建</Button>
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
                      <p className="text-sm">在“角色版本”标签页创建版本后再生成图片</p>
                    </div>
                  ) : (
                    <CharacterStudioWorkspace
                      projectId={projectIdNum}
                      characterId={charDetail.id}
                      characterName={charDetail.name}
                      versions={charDetail.versions}
                      selectedVersionId={selectedVersionId}
                      onSelectVersionId={setSelectedVersionId}
                      onRefresh={loadCharDetail}
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
                      <Button size="sm" onClick={() => setIsCreateVersionOpen(true)}>
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
      <CreateVersionDialog open={isCreateVersionOpen} onOpenChange={setIsCreateVersionOpen} onCreate={handleCreateVersion} creating={creatingVersion} />
    </AppLayout>
  );
}
