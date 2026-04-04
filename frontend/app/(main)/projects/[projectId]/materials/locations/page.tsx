'use client';

import { use, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AppLayout } from '@/components/layout';
import {
  assetsApi,
  locationsApi,
  projectsApi,
  tasksApi,
  type LocationDetailResponse,
  type LocationResponse,
  type LocationVersionResponse,
  type ProjectResponse,
} from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import {
  Building,
  Cloud,
  CloudRain,
  ImagePlus,
  Layers,
  Loader2,
  MapPin,
  Moon,
  Plus,
  Search,
  Sparkles,
  Sun,
  Trash2,
  Trees,
  Upload,
  Wand2,
  X,
} from 'lucide-react';

const locationTypeLabels: Record<string, string> = {
  indoor: '室内',
  outdoor: '室外',
  fantasy: '奇幻',
  mixed: '混合',
};

const locationTypeIcons: Record<string, typeof Building> = {
  indoor: Building,
  outdoor: Trees,
  fantasy: Sparkles,
  mixed: Layers,
};

const timeOfDayLabels: Record<string, string> = {
  dawn: '黎明',
  day: '白天',
  dusk: '黄昏',
  night: '夜晚',
};

const weatherLabels: Record<string, string> = {
  clear: '晴朗',
  cloudy: '多云',
  rain: '下雨',
  snow: '下雪',
  fog: '大雾',
  storm: '暴风雨',
};

const aspectRatios = [
  { value: '16:9', label: '16:9 横屏' },
  { value: '9:16', label: '9:16 竖屏' },
  { value: '1:1', label: '1:1 方图' },
  { value: '4:3', label: '4:3' },
  { value: '3:4', label: '3:4' },
  { value: '21:9', label: '21:9 超宽' },
];

const resolutions = [
  { value: '512', label: '512' },
  { value: '1K', label: '1K' },
  { value: '2K', label: '2K' },
  { value: '4K', label: '4K' },
];

interface PendingImageFile {
  id: string;
  file: File;
  preview: string;
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-center">
        <MapPin className="mx-auto mb-4 h-14 w-14 text-muted-foreground/60" />
        <h3 className="mb-2 text-lg font-semibold text-foreground">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
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

export default function LocationsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const projectIdNum = Number(projectId);

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [locations, setLocations] = useState<LocationResponse[]>([]);
  const [selectedLocId, setSelectedLocId] = useState<number | null>(null);
  const [locDetail, setLocDetail] = useState<LocationDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newLocName, setNewLocName] = useState('');
  const [newLocCode, setNewLocCode] = useState('');
  const [newLocType, setNewLocType] = useState('outdoor');
  const [newLocDomain, setNewLocDomain] = useState('');
  const [newLocDesc, setNewLocDesc] = useState('');

  const [textPrompt, setTextPrompt] = useState('');
  const [textNegativePrompt, setTextNegativePrompt] = useState('');
  const [textStylePreset, setTextStylePreset] = useState('');
  const [textAspectRatio, setTextAspectRatio] = useState('16:9');
  const [textResolution, setTextResolution] = useState('1K');
  const [textGenerating, setTextGenerating] = useState(false);

  const [uploadFiles, setUploadFiles] = useState<PendingImageFile[]>([]);
  const [uploadingSceneImage, setUploadingSceneImage] = useState(false);

  const [imgPrompt, setImgPrompt] = useState('');
  const [imgNegativePrompt, setImgNegativePrompt] = useState('');
  const [imgStylePreset, setImgStylePreset] = useState('');
  const [imgAspectRatio, setImgAspectRatio] = useState('16:9');
  const [imgResolution, setImgResolution] = useState('1K');
  const [img2imgFiles, setImg2imgFiles] = useState<PendingImageFile[]>([]);
  const [selectedReferenceUrls, setSelectedReferenceUrls] = useState<string[]>([]);
  const [imgGenerating, setImgGenerating] = useState(false);
  const uploadFilesRef = useRef<PendingImageFile[]>([]);
  const img2imgFilesRef = useRef<PendingImageFile[]>([]);

  const resetPreviewFiles = useCallback((files: PendingImageFile[]) => {
    files.forEach((item) => URL.revokeObjectURL(item.preview));
  }, []);

  const loadLocations = useCallback(async () => {
    const items = await locationsApi.list(projectIdNum, 1, 50).then((response) => response.items);
    setLocations(items);
    return items;
  }, [projectIdNum]);

  const loadLocationDetail = useCallback(async (locationId: number) => {
    const detail = await locationsApi.get(projectIdNum, locationId);
    setLocDetail(detail);
    setSelectedReferenceUrls((prev) => {
      if (prev.length === 0) {
        return detail.reference_image_urls.slice(0, 5);
      }
      return prev.filter((url) => detail.reference_image_urls.includes(url));
    });
    return detail;
  }, [projectIdNum]);

  useEffect(() => {
    if (Number.isNaN(projectIdNum)) return;

    Promise.all([
      projectsApi.get(projectIdNum).catch(() => null),
      loadLocations().catch(() => []),
    ]).then(([projectResponse, locationItems]) => {
      setProject(projectResponse);
      if (locationItems.length > 0) {
        setSelectedLocId((current) => current ?? locationItems[0].id);
      }
      setLoading(false);
    });
  }, [loadLocations, projectIdNum]);

  useEffect(() => {
    if (!selectedLocId || Number.isNaN(projectIdNum)) return;
    loadLocationDetail(selectedLocId).catch(() => setLocDetail(null));
  }, [loadLocationDetail, projectIdNum, selectedLocId]);

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

  const filteredLocations = useMemo(() => {
    const keyword = searchQuery.trim().toLowerCase();
    if (!keyword) return locations;
    return locations.filter((location) => (
      location.name.toLowerCase().includes(keyword)
      || location.loc_code.toLowerCase().includes(keyword)
      || (location.domain || '').toLowerCase().includes(keyword)
    ));
  }, [locations, searchQuery]);

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

  const updateLocationReferenceUrls = useCallback(async (urls: string[]) => {
    if (!locDetail) return null;
    await locationsApi.update(projectIdNum, locDetail.id, {
      reference_image_urls: Array.from(new Set(urls)),
    });
    return loadLocationDetail(locDetail.id);
  }, [loadLocationDetail, locDetail, projectIdNum]);

  const uploadFilesToLocation = useCallback(async (files: PendingImageFile[]) => {
    if (!locDetail) return [];
    const uploadedAssets = await Promise.all(
      files.map((item) => assetsApi.upload(projectIdNum, item.file, undefined, locDetail.id)),
    );
    return uploadedAssets.map((asset) => asset.file_url);
  }, [locDetail, projectIdNum]);

  const waitForTask = useCallback(async (taskId: number) => {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      const task = await tasksApi.get(taskId);
      if (task.status === 'success') return task;
      if (task.status === 'failed') {
        throw new Error(task.error_message || '图像生成失败');
      }
      await new Promise((resolve) => setTimeout(resolve, 5000));
    }
    throw new Error('生成时间较长，请稍后刷新查看结果');
  }, []);

  const handleCreateLocation = useCallback(async () => {
    if (!newLocName.trim() || !newLocCode.trim()) return;
    setCreating(true);
    try {
      // 自动格式化 loc_code：大写 + 下划线
      let formattedCode = newLocCode.trim().toUpperCase().replace(/\s+/g, '_').replace(/[^A-Z0-9_]/g, '');
      if (!formattedCode.startsWith('LOC_')) {
        formattedCode = 'LOC_' + formattedCode;
      }

      const location = await locationsApi.create(projectIdNum, {
        loc_code: formattedCode,
        name: newLocName.trim(),
        location_type: newLocType,
        domain: newLocDomain.trim() || undefined,
        description: newLocDesc.trim() || undefined,
      });
      setLocations((prev) => [location, ...prev]);
      setSelectedLocId(location.id);
      setIsCreateDialogOpen(false);
      setNewLocName('');
      setNewLocCode('');
      setNewLocType('outdoor');
      setNewLocDomain('');
      setNewLocDesc('');
      toast.success('场景创建成功');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '场景创建失败');
    } finally {
      setCreating(false);
    }
  }, [newLocCode, newLocDesc, newLocDomain, newLocName, newLocType, projectIdNum]);

  const handleDeleteLocation = useCallback(async (locationId: number) => {
    if (!window.confirm('确定删除这个场景吗？')) return;
    try {
      await locationsApi.delete(projectIdNum, locationId);
      const nextLocations = locations.filter((item) => item.id !== locationId);
      setLocations(nextLocations);
      if (selectedLocId === locationId) {
        setSelectedLocId(nextLocations[0]?.id ?? null);
        if (nextLocations.length === 0) setLocDetail(null);
      }
      toast.success('场景已删除');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '删除失败');
    }
  }, [locations, projectIdNum, selectedLocId]);

  const handleUploadSceneImages = useCallback(async () => {
    if (!locDetail || uploadFiles.length === 0) return;
    setUploadingSceneImage(true);
    try {
      const urls = await uploadFilesToLocation(uploadFiles);
      await updateLocationReferenceUrls([...(locDetail.reference_image_urls || []), ...urls]);
      toast.success('场景图上传成功');
      resetPreviewFiles(uploadFiles);
      setUploadFiles([]);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '上传失败');
    } finally {
      setUploadingSceneImage(false);
    }
  }, [locDetail, resetPreviewFiles, updateLocationReferenceUrls, uploadFiles, uploadFilesToLocation]);

  const handleGenerateFromPrompt = useCallback(async () => {
    if (!locDetail || !textPrompt.trim()) {
      toast.error('请先输入提示词');
      return;
    }

    setTextGenerating(true);
    try {
      const task = await tasksApi.triggerImage({
        project_id: projectIdNum,
        location_id: locDetail.id,
        prompt: textPrompt.trim(),
        negative_prompt: textNegativePrompt.trim() || undefined,
        aspect_ratio: textAspectRatio,
        resolution: textResolution,
        style_preset: textStylePreset.trim() || undefined,
        save_to_shot: true,
      });
      toast.success('场景图生成任务已提交');
      await waitForTask(task.id);
      await loadLocationDetail(locDetail.id);
      toast.success('场景图生成完成');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '生成失败');
    } finally {
      setTextGenerating(false);
    }
  }, [
    loadLocationDetail,
    locDetail,
    projectIdNum,
    textAspectRatio,
    textNegativePrompt,
    textPrompt,
    textResolution,
    textStylePreset,
    waitForTask,
  ]);

  const handleGenerateFromImage = useCallback(async () => {
    if (!locDetail || !imgPrompt.trim()) {
      toast.error('请先输入图生图提示词');
      return;
    }
    if (selectedReferenceUrls.length === 0 && img2imgFiles.length === 0) {
      toast.error('请至少选择或上传一张参考图');
      return;
    }

    setImgGenerating(true);
    try {
      const uploadedUrls = img2imgFiles.length > 0 ? await uploadFilesToLocation(img2imgFiles) : [];
      if (uploadedUrls.length > 0) {
        await updateLocationReferenceUrls([...(locDetail.reference_image_urls || []), ...uploadedUrls]);
      }

      const referenceUrls = Array.from(new Set([...selectedReferenceUrls, ...uploadedUrls])).slice(0, 5);
      const task = await tasksApi.triggerImage({
        project_id: projectIdNum,
        location_id: locDetail.id,
        prompt: imgPrompt.trim(),
        negative_prompt: imgNegativePrompt.trim() || undefined,
        aspect_ratio: imgAspectRatio,
        resolution: imgResolution,
        style_preset: imgStylePreset.trim() || undefined,
        reference_image_urls: referenceUrls,
        save_to_shot: true,
      });
      toast.success('图生图任务已提交');
      await waitForTask(task.id);
      await loadLocationDetail(locDetail.id);
      resetPreviewFiles(img2imgFiles);
      setImg2imgFiles([]);
      toast.success('图生图生成完成');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '图生图失败');
    } finally {
      setImgGenerating(false);
    }
  }, [
    img2imgFiles,
    imgAspectRatio,
    imgNegativePrompt,
    imgPrompt,
    imgResolution,
    imgStylePreset,
    loadLocationDetail,
    locDetail,
    projectIdNum,
    resetPreviewFiles,
    selectedReferenceUrls,
    updateLocationReferenceUrls,
    uploadFilesToLocation,
    waitForTask,
  ]);

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

  const handleRemoveReferenceImage = useCallback(async (url: string) => {
    if (!locDetail) return;
    try {
      await updateLocationReferenceUrls(locDetail.reference_image_urls.filter((item) => item !== url));
      toast.success('已从当前场景移除参考图');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '移除失败');
    }
  }, [locDetail, updateLocationReferenceUrls]);

  if (loading) {
    return (
      <AppLayout projectId={projectId}>
        <div className="flex h-full items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppLayout>
    );
  }

  if (!project) {
    return (
      <AppLayout projectId={projectId}>
        <EmptyState title="项目不存在" description="请返回项目列表重新选择。" />
      </AppLayout>
    );
  }

  return (
    <AppLayout
      projectId={projectId}
      breadcrumbs={[
        { label: '项目', href: '/projects' },
        { label: project.name, href: `/projects/${projectId}` },
        { label: '素材库', href: `/projects/${projectId}/materials` },
        { label: '场景管理' },
      ]}
    >
      <div className="flex h-[calc(100vh-4rem)]">
        <div className="flex w-80 flex-col border-r border-border bg-card">
          <div className="space-y-3 border-b border-border p-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-foreground">场景列表</h2>
              <Badge variant="outline">{locations.length} 个</Badge>
            </div>

            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="搜索场景..."
                className="pl-9"
              />
            </div>

            <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button className="w-full">
                  <Plus className="mr-2 h-4 w-4" />
                  创建场景
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>创建新场景</DialogTitle>
                  <DialogDescription>先录入基础信息，后续再补充提示词和场景图。</DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">场景名称</label>
                    <Input value={newLocName} onChange={(event) => setNewLocName(event.target.value)} placeholder="例如：云岚宗广场" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">场景编号</label>
                    <Input value={newLocCode} onChange={(event) => setNewLocCode(event.target.value)} placeholder="例如：LOC_YUNLAN_SQUARE" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">场景类型</label>
                    <Select value={newLocType} onValueChange={setNewLocType}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="indoor">室内</SelectItem>
                        <SelectItem value="outdoor">室外</SelectItem>
                        <SelectItem value="fantasy">奇幻</SelectItem>
                        <SelectItem value="mixed">混合</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">所属领域</label>
                    <Input value={newLocDomain} onChange={(event) => setNewLocDomain(event.target.value)} placeholder="例如：云岚宗" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">场景描述</label>
                    <Textarea value={newLocDesc} onChange={(event) => setNewLocDesc(event.target.value)} rows={4} placeholder="描述场景的核心视觉特征..." />
                  </div>
                </div>

                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>取消</Button>
                  <Button onClick={handleCreateLocation} disabled={creating || !newLocName.trim() || !newLocCode.trim()}>
                    {creating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    创建
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <ScrollArea className="flex-1">
            <div className="space-y-2 p-3">
              {filteredLocations.map((location) => {
                const Icon = locationTypeIcons[location.location_type] || MapPin;
                const isActive = selectedLocId === location.id;
                return (
                  <div
                    key={location.id}
                    className={`group rounded-lg border p-3 transition ${isActive ? 'border-primary bg-primary/5' : 'border-transparent hover:border-border hover:bg-secondary/40'}`}
                    onClick={() => setSelectedLocId(location.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        setSelectedLocId(location.id);
                      }
                    }}
                  >
                    <div className="flex items-start gap-3">
                      <div className="rounded-lg bg-info/10 p-2 text-info">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="truncate font-medium text-foreground">{location.name}</div>
                        <div className="truncate text-xs text-muted-foreground">
                          {location.domain || locationTypeLabels[location.location_type] || location.location_type}
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="opacity-0 transition group-hover:opacity-100"
                        onClick={(event) => {
                          event.stopPropagation();
                          handleDeleteLocation(location.id);
                        }}
                      >
                        <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                      </Button>
                    </div>
                  </div>
                );
              })}

              {filteredLocations.length === 0 ? (
                <div className="py-10 text-center text-sm text-muted-foreground">
                  没有找到匹配的场景
                </div>
              ) : null}
            </div>
          </ScrollArea>
        </div>

        <div className="flex-1 overflow-y-auto bg-background">
          {!locDetail ? (
            <EmptyState title="选择一个场景" description="从左侧列表选择场景后，就可以上传或生成场景图。" />
          ) : (
            <div className="space-y-6 p-6">
              <div className="flex flex-col gap-4 rounded-2xl border bg-card p-6 lg:flex-row lg:items-start lg:justify-between">
                <div className="flex items-start gap-4">
                  <div className="rounded-2xl bg-info/10 p-4 text-info">
                    {(() => {
                      const Icon = locationTypeIcons[locDetail.location_type] || MapPin;
                      return <Icon className="h-10 w-10" />;
                    })()}
                  </div>
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <h1 className="text-2xl font-bold text-foreground">{locDetail.name}</h1>
                      <Badge variant="outline">{locDetail.loc_code}</Badge>
                      <Badge variant={locDetail.is_active ? 'default' : 'secondary'}>
                        {locDetail.is_active ? '启用中' : '已停用'}
                      </Badge>
                    </div>
                    <p className="max-w-3xl text-sm text-muted-foreground">
                      {locDetail.description || '暂未填写场景描述。'}
                    </p>
                    <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                      <span>类型：<span className="text-foreground">{locationTypeLabels[locDetail.location_type] || locDetail.location_type}</span></span>
                      <span>领域：<span className="text-foreground">{locDetail.domain || '未设置'}</span></span>
                      <span>参考图：<span className="text-foreground">{locDetail.reference_image_urls.length} 张</span></span>
                      <span>版本：<span className="text-foreground">{locDetail.version_count} 个</span></span>
                    </div>
                  </div>
                </div>
              </div>

              <Tabs defaultValue="studio" className="space-y-4">
                <TabsList>
                  <TabsTrigger value="studio">场景出图工作区</TabsTrigger>
                  <TabsTrigger value="versions">场景版本</TabsTrigger>
                  <TabsTrigger value="details">场景信息</TabsTrigger>
                </TabsList>

                <TabsContent value="studio" className="space-y-6">
                  <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
                    <Card>
                      <CardHeader>
                        <CardTitle>生成与上传</CardTitle>
                        <CardDescription>支持文生图、本地上传、图生图三种方式维护当前场景图。</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <Tabs defaultValue="prompt" className="space-y-4">
                          <TabsList className="grid w-full grid-cols-3">
                            <TabsTrigger value="prompt">提示词生图</TabsTrigger>
                            <TabsTrigger value="upload">本地上传</TabsTrigger>
                            <TabsTrigger value="img2img">图生图</TabsTrigger>
                          </TabsList>

                          <TabsContent value="prompt" className="space-y-4">
                            <div className="space-y-2">
                              <label className="text-sm font-medium">正向提示词</label>
                              <Textarea
                                value={textPrompt}
                                onChange={(event) => setTextPrompt(event.target.value)}
                                rows={5}
                                placeholder="描述你想要的场景，例如：古风宗门广场，石阶层叠，晨雾缭绕，远处山门高耸，动漫电影感..."
                              />
                            </div>
                            <div className="space-y-2">
                              <label className="text-sm font-medium">负面提示词</label>
                              <Input
                                value={textNegativePrompt}
                                onChange={(event) => setTextNegativePrompt(event.target.value)}
                                placeholder="例如：blurry, low quality, watermark"
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
                                    {aspectRatios.map((item) => (
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
                                    {resolutions.map((item) => (
                                      <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              </div>
                              <div className="space-y-2">
                                <label className="text-sm font-medium">风格预设</label>
                                <Input value={textStylePreset} onChange={(event) => setTextStylePreset(event.target.value)} placeholder="例如：anime cinematic" />
                              </div>
                            </div>
                            <div className="flex justify-end">
                              <Button onClick={handleGenerateFromPrompt} disabled={textGenerating || !textPrompt.trim()}>
                                {textGenerating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Wand2 className="mr-2 h-4 w-4" />}
                                生成场景图
                              </Button>
                            </div>
                          </TabsContent>

                          <TabsContent value="upload" className="space-y-4">
                            <FileDropZone
                              onSelect={(files) => addPendingFiles(files, 'upload')}
                              disabled={uploadingSceneImage}
                              title="上传本地场景图"
                              description="支持 JPG、PNG、WebP、GIF，单张不超过 10MB"
                            />

                            {uploadFiles.length > 0 ? (
                              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                                {uploadFiles.map((item) => (
                                  <div key={item.id} className="rounded-xl border bg-secondary/20 p-2">
                                    <div className="relative overflow-hidden rounded-lg">
                                      <img src={item.preview} alt={item.file.name} className="aspect-video w-full object-cover" />
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

                            <div className="flex justify-end">
                              <Button onClick={handleUploadSceneImages} disabled={uploadingSceneImage || uploadFiles.length === 0}>
                                {uploadingSceneImage ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ImagePlus className="mr-2 h-4 w-4" />}
                                保存到当前场景
                              </Button>
                            </div>
                          </TabsContent>

                          <TabsContent value="img2img" className="space-y-4">
                            <div className="space-y-2">
                              <label className="text-sm font-medium">图生图提示词</label>
                              <Textarea
                                value={imgPrompt}
                                onChange={(event) => setImgPrompt(event.target.value)}
                                rows={4}
                                placeholder="在已有场景基础上继续细化，例如：保留建筑结构和空间布局，加入夜色、灯火和薄雾..."
                              />
                            </div>
                            <div className="space-y-2">
                              <label className="text-sm font-medium">负面提示词</label>
                              <Input
                                value={imgNegativePrompt}
                                onChange={(event) => setImgNegativePrompt(event.target.value)}
                                placeholder="例如：deformed, extra objects, watermark"
                              />
                            </div>
                            <div className="grid gap-4 md:grid-cols-3">
                              <div className="space-y-2">
                                <label className="text-sm font-medium">画幅比例</label>
                                <Select value={imgAspectRatio} onValueChange={setImgAspectRatio}>
                                  <SelectTrigger>
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {aspectRatios.map((item) => (
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
                                    {resolutions.map((item) => (
                                      <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              </div>
                              <div className="space-y-2">
                                <label className="text-sm font-medium">风格预设</label>
                                <Input value={imgStylePreset} onChange={(event) => setImgStylePreset(event.target.value)} placeholder="例如：anime matte painting" />
                              </div>
                            </div>

                            <Separator />

                            <div className="space-y-3">
                              <div className="flex items-center justify-between">
                                <div>
                                  <div className="text-sm font-medium">选择已有参考图</div>
                                  <div className="text-xs text-muted-foreground">可多选，最多 5 张</div>
                                </div>
                                <Badge variant="secondary">{selectedReferenceUrls.length}/5</Badge>
                              </div>

                              {locDetail.reference_image_urls.length > 0 ? (
                                <div className="grid gap-3 sm:grid-cols-2">
                                  {locDetail.reference_image_urls.map((url) => {
                                    const selected = selectedReferenceUrls.includes(url);
                                    return (
                                      <button
                                        key={url}
                                        type="button"
                                        onClick={() => toggleReferenceSelection(url)}
                                        className={`overflow-hidden rounded-xl border text-left transition ${selected ? 'border-primary ring-2 ring-primary/20' : 'border-border hover:border-primary/40'}`}
                                      >
                                        <img src={url} alt="" className="aspect-video w-full object-cover" />
                                      </button>
                                    );
                                  })}
                                </div>
                              ) : (
                                <div className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
                                  当前场景还没有参考图，可以先在“本地上传”里上传一张，或者直接在下面补充图生图参考图。
                                </div>
                              )}
                            </div>

                            <div className="space-y-3">
                              <div>
                                <div className="text-sm font-medium">补充新的图生图参考图</div>
                                <div className="text-xs text-muted-foreground">上传后会自动保存到当前场景参考图库。</div>
                              </div>

                              <FileDropZone
                                onSelect={(files) => addPendingFiles(files, 'img2img')}
                                disabled={imgGenerating}
                                title="添加参考图"
                                description="可以补充新的底图或角度参考"
                              />

                              {img2imgFiles.length > 0 ? (
                                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                                  {img2imgFiles.map((item) => (
                                    <div key={item.id} className="rounded-xl border bg-secondary/20 p-2">
                                      <div className="relative overflow-hidden rounded-lg">
                                        <img src={item.preview} alt={item.file.name} className="aspect-video w-full object-cover" />
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
                        <CardTitle>当前场景图库</CardTitle>
                        <CardDescription>这里展示已经绑定到当前场景的参考图，图生图会优先复用它们。</CardDescription>
                      </CardHeader>
                      <CardContent>
                        {locDetail.reference_image_urls.length === 0 ? (
                          <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
                            还没有场景图。你可以先输入提示词生成一张，或者上传本地图片。
                          </div>
                        ) : (
                          <div className="grid gap-4 sm:grid-cols-2">
                            {locDetail.reference_image_urls.map((url, index) => (
                              <div key={url} className="overflow-hidden rounded-xl border bg-card">
                                <img src={url} alt={`场景图 ${index + 1}`} className="aspect-video w-full object-cover" />
                                <div className="flex items-center justify-between gap-2 p-3">
                                  <div className="text-xs text-muted-foreground">场景图 #{index + 1}</div>
                                  <div className="flex items-center gap-2">
                                    <Button
                                      variant={selectedReferenceUrls.includes(url) ? 'default' : 'outline'}
                                      size="sm"
                                      onClick={() => toggleReferenceSelection(url)}
                                    >
                                      {selectedReferenceUrls.includes(url) ? '已选中' : '设为参考图'}
                                    </Button>
                                    <Button variant="ghost" size="icon" onClick={() => handleRemoveReferenceImage(url)}>
                                      <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                                    </Button>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </div>
                </TabsContent>

                <TabsContent value="versions" className="space-y-4">
                  {locDetail.versions.length === 0 ? (
                    <Card>
                      <CardContent className="py-12 text-center text-sm text-muted-foreground">
                        当前场景还没有版本。后续可以通过版本区分白天、夜晚、战损等状态。
                      </CardContent>
                    </Card>
                  ) : (
                    <div className="grid gap-4 lg:grid-cols-2">
                      {locDetail.versions.map((version: LocationVersionResponse) => (
                        <Card key={version.id}>
                          <CardHeader>
                            <div className="flex items-center justify-between gap-3">
                              <div>
                                <CardTitle className="text-base">{version.label}</CardTitle>
                                <CardDescription>{version.version_code}</CardDescription>
                              </div>
                              <div className="flex items-center gap-2">
                                {version.is_default ? <Badge>默认</Badge> : null}
                                {version.time_of_day ? (
                                  <Badge variant="outline">
                                    {version.time_of_day === 'night' ? <Moon className="mr-1 h-3 w-3" /> : <Sun className="mr-1 h-3 w-3" />}
                                    {timeOfDayLabels[version.time_of_day] || version.time_of_day}
                                  </Badge>
                                ) : null}
                                {version.weather ? (
                                  <Badge variant="outline">
                                    {version.weather === 'rain' ? <CloudRain className="mr-1 h-3 w-3" /> : <Cloud className="mr-1 h-3 w-3" />}
                                    {weatherLabels[version.weather] || version.weather}
                                  </Badge>
                                ) : null}
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent className="space-y-4">
                            <p className="text-sm text-muted-foreground">
                              {version.description || '暂无版本描述。'}
                            </p>

                            {version.additional_elements.length > 0 ? (
                              <div className="space-y-2">
                                <div className="text-xs font-medium text-muted-foreground">新增元素</div>
                                <div className="flex flex-wrap gap-2">
                                  {version.additional_elements.map((item) => (
                                    <Badge key={item} variant="secondary">{item}</Badge>
                                  ))}
                                </div>
                              </div>
                            ) : null}

                            {version.removed_elements.length > 0 ? (
                              <div className="space-y-2">
                                <div className="text-xs font-medium text-muted-foreground">移除元素</div>
                                <div className="flex flex-wrap gap-2">
                                  {version.removed_elements.map((item) => (
                                    <Badge key={item} variant="outline">{item}</Badge>
                                  ))}
                                </div>
                              </div>
                            ) : null}

                            {version.reference_image_urls.length > 0 ? (
                              <div className="grid gap-3 sm:grid-cols-2">
                                {version.reference_image_urls.slice(0, 4).map((url) => (
                                  <img key={url} src={url} alt="" className="aspect-video rounded-lg object-cover" />
                                ))}
                              </div>
                            ) : null}
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="details" className="space-y-4">
                  <div className="grid gap-4 lg:grid-cols-2">
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">标志性元素</CardTitle>
                      </CardHeader>
                      <CardContent>
                        {locDetail.key_elements.length > 0 ? (
                          <div className="flex flex-wrap gap-2">
                            {locDetail.key_elements.map((item) => (
                              <Badge key={item} variant="secondary">{item}</Badge>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-muted-foreground">暂未设置标志性元素。</p>
                        )}
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">建筑风格</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-foreground">{locDetail.architectural_style || '暂未设置'}</p>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">默认氛围</CardTitle>
                      </CardHeader>
                      <CardContent>
                        {locDetail.default_atmosphere ? (
                          <pre className="overflow-x-auto rounded-xl bg-secondary p-3 text-xs text-foreground">
                            {JSON.stringify(locDetail.default_atmosphere, null, 2)}
                          </pre>
                        ) : (
                          <p className="text-sm text-muted-foreground">暂未设置默认氛围。</p>
                        )}
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">时间变体描述</CardTitle>
                      </CardHeader>
                      <CardContent>
                        {locDetail.time_variants ? (
                          <div className="grid gap-3 sm:grid-cols-2">
                            {Object.entries(locDetail.time_variants).map(([timeKey, description]) => (
                              <div key={timeKey} className="rounded-xl bg-secondary/50 p-3">
                                <div className="mb-1 text-xs font-medium text-muted-foreground">
                                  {timeOfDayLabels[timeKey] || timeKey}
                                </div>
                                <div className="text-sm text-foreground">{description}</div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-muted-foreground">暂未设置时间变体。</p>
                        )}
                      </CardContent>
                    </Card>

                    <Card className="lg:col-span-2">
                      <CardHeader>
                        <CardTitle className="text-base">生成提示词</CardTitle>
                        <CardDescription>这些字段会直接影响文生图和图生图的基础效果。</CardDescription>
                      </CardHeader>
                      <CardContent className="grid gap-4 lg:grid-cols-3">
                        <div className="space-y-2">
                          <div className="text-xs font-medium text-muted-foreground">基础背景提示词</div>
                          <div className="rounded-xl bg-secondary p-3 text-sm text-foreground">
                            {locDetail.base_background_prompt || '暂未设置'}
                          </div>
                        </div>
                        <div className="space-y-2">
                          <div className="text-xs font-medium text-muted-foreground">负面提示词</div>
                          <div className="rounded-xl bg-secondary p-3 text-sm text-foreground">
                            {locDetail.negative_prompt || '暂未设置'}
                          </div>
                        </div>
                        <div className="space-y-2">
                          <div className="text-xs font-medium text-muted-foreground">风格预设</div>
                          <div className="rounded-xl bg-secondary p-3 text-sm text-foreground">
                            {locDetail.style_preset || '暂未设置'}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
