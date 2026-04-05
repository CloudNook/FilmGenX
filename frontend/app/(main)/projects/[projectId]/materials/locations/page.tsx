'use client';

import { use, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AppLayout } from '@/components/layout';
import {
  assetsApi,
  locationsApi,
  projectsApi,
  tasksApi,
  type AssetResponse,
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

interface SceneImageItem {
  url: string;
  assetId: number | null;
  source: 'uploaded' | 'generated' | 'reference';
  createdAt?: string;
  isReferenced: boolean;
}

function splitMultilineValue(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildSceneImageItems(referenceUrls: string[], assets: AssetResponse[]): SceneImageItem[] {
  const assetMap = new Map<string, AssetResponse>();
  assets.forEach((asset) => {
    if (!assetMap.has(asset.file_url)) {
      assetMap.set(asset.file_url, asset);
    }
  });

  const referencedSet = new Set(referenceUrls);
  const orderedUrls = [
    ...referenceUrls,
    ...assets.map((asset) => asset.file_url).filter((url) => !referencedSet.has(url)),
  ];

  return Array.from(new Set(orderedUrls)).map((url) => {
    const asset = assetMap.get(url);
    return {
      url,
      assetId: asset?.id ?? null,
      source: asset ? (asset.source as 'uploaded' | 'generated') : 'reference',
      createdAt: asset?.created_at,
      isReferenced: referencedSet.has(url),
    };
  });
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
  const [dragging, setDragging] = useState(false);

  return (
    <label
      className={`block rounded-xl border-2 border-dashed p-6 transition ${disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer hover:border-primary/50 hover:bg-secondary/30'} ${dragging ? 'border-primary bg-secondary/40' : ''}`}
      onDragOver={(event) => {
        if (disabled) return;
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        if (disabled) return;
        event.preventDefault();
        setDragging(false);
        onSelect(event.dataTransfer.files);
      }}
    >
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
  const [locationAssets, setLocationAssets] = useState<AssetResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newLocName, setNewLocName] = useState('');
  const [newLocType, setNewLocType] = useState('outdoor');
  const [newLocDomain, setNewLocDomain] = useState('');
  const [newLocDesc, setNewLocDesc] = useState('');
  const [versionDialogOpen, setVersionDialogOpen] = useState(false);
  const [editingVersion, setEditingVersion] = useState<LocationVersionResponse | null>(null);
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState<'studio' | 'versions' | 'details'>('studio');
  const [selectedStudioVersionId, setSelectedStudioVersionId] = useState<number | null | undefined>(undefined);
  const [studioVersionAssets, setStudioVersionAssets] = useState<AssetResponse[]>([]);
  const [selectedSourceLocationId, setSelectedSourceLocationId] = useState<number | null>(null);
  const [selectedSourceVersionId, setSelectedSourceVersionId] = useState<number | null>(null);
  const [sourceLocationDetail, setSourceLocationDetail] = useState<LocationDetailResponse | null>(null);
  const [sourceLocationAssets, setSourceLocationAssets] = useState<AssetResponse[]>([]);
  const [sourceVersionAssets, setSourceVersionAssets] = useState<AssetResponse[]>([]);
  const [loadingSourceLibrary, setLoadingSourceLibrary] = useState(false);

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

  const loadLocationAssets = useCallback(async (locationId: number) => {
    const items = await assetsApi.list(projectIdNum, 1, 100, {
      assetType: 'image',
      locationId,
      isCurrent: true,
    }).then((response) => response.items);
    setLocationAssets(items.filter((asset) => asset.location_version_id == null));
    return items;
  }, [projectIdNum]);

  const loadStudioVersionAssets = useCallback(async (locationId: number, versionId: number) => {
    const items = await assetsApi.list(projectIdNum, 1, 100, {
      assetType: 'image',
      locationId,
      locationVersionId: versionId,
      isCurrent: true,
    }).then((response) => response.items);
    setStudioVersionAssets(items);
    return items;
  }, [projectIdNum]);

  const loadLocationDetail = useCallback(async (locationId: number) => {
    const detail = await locationsApi.get(projectIdNum, locationId);
    setLocDetail(detail);
    await loadLocationAssets(locationId);
    return detail;
  }, [loadLocationAssets, projectIdNum]);

  const activeStudioVersion = useMemo(
    () => locDetail?.versions.find((version) => version.id === selectedStudioVersionId) ?? null,
    [locDetail?.versions, selectedStudioVersionId],
  );

  const studioReferenceUrls = activeStudioVersion?.reference_image_urls || locDetail?.reference_image_urls || [];

  const sourceLocationOptions = useMemo(() => {
    if (!locDetail) return locations;
    const currentLocation = locations.find((location) => location.id === locDetail.id);
    const otherLocations = locations.filter((location) => location.id !== locDetail.id);
    return currentLocation ? [currentLocation, ...otherLocations] : locations;
  }, [locDetail, locations]);

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
    if (!locDetail) {
      setSelectedStudioVersionId(undefined);
      setStudioVersionAssets([]);
      return;
    }

    if (selectedStudioVersionId === null) {
      return;
    }

    if (selectedStudioVersionId !== undefined && locDetail.versions.some((version) => version.id === selectedStudioVersionId)) {
      return;
    }

    setSelectedStudioVersionId(locDetail.default_version?.id ?? locDetail.versions[0]?.id ?? null);
  }, [locDetail, selectedStudioVersionId]);

  useEffect(() => {
    if (!locDetail || sourceLocationOptions.length === 0) {
      setSelectedSourceLocationId(null);
      setSelectedSourceVersionId(null);
      setSourceLocationDetail(null);
      setSourceLocationAssets([]);
      setSourceVersionAssets([]);
      return;
    }

    setSelectedSourceLocationId((current) => {
      if (current && sourceLocationOptions.some((location) => location.id === current)) {
        return current;
      }
      return locDetail.id;
    });
  }, [locDetail, sourceLocationOptions]);

  useEffect(() => {
    if (!locDetail) return;

    const nextReferenceUrls = activeStudioVersion?.reference_image_urls || locDetail.reference_image_urls || [];
    setSelectedReferenceUrls((prev) => {
      if (prev.length === 0) {
        return nextReferenceUrls.slice(0, 5);
      }
      return prev.filter((url) => nextReferenceUrls.includes(url));
    });

    if (activeStudioVersion) {
      loadStudioVersionAssets(locDetail.id, activeStudioVersion.id).catch(() => setStudioVersionAssets([]));
    } else {
      setStudioVersionAssets([]);
    }
  }, [activeStudioVersion, loadStudioVersionAssets, locDetail]);

  useEffect(() => {
    if (!selectedSourceLocationId || Number.isNaN(projectIdNum)) {
      setSourceLocationDetail(null);
      setSourceLocationAssets([]);
      setSourceVersionAssets([]);
      setLoadingSourceLibrary(false);
      return;
    }

    let cancelled = false;
    setLoadingSourceLibrary(true);

    Promise.all([
      locationsApi.get(projectIdNum, selectedSourceLocationId),
      assetsApi.list(projectIdNum, 1, 100, {
        assetType: 'image',
        locationId: selectedSourceLocationId,
        isCurrent: true,
      }).then((response) => response.items),
    ]).then(([detail, items]) => {
      if (cancelled) return;
      setSourceLocationDetail(detail);
      setSourceLocationAssets(items.filter((asset) => asset.location_version_id == null));
      setSelectedSourceVersionId((current) => (
        current && detail.versions.some((version) => version.id === current) ? current : null
      ));
    }).catch(() => {
      if (cancelled) return;
      setSourceLocationDetail(null);
      setSourceLocationAssets([]);
      setSourceVersionAssets([]);
    }).finally(() => {
      if (!cancelled) {
        setLoadingSourceLibrary(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [projectIdNum, selectedSourceLocationId]);

  useEffect(() => {
    if (!selectedSourceLocationId || !selectedSourceVersionId || Number.isNaN(projectIdNum)) {
      setSourceVersionAssets([]);
      return;
    }

    let cancelled = false;

    assetsApi.list(projectIdNum, 1, 100, {
      assetType: 'image',
      locationId: selectedSourceLocationId,
      locationVersionId: selectedSourceVersionId,
      isCurrent: true,
    }).then((response) => {
      if (cancelled) return;
      setSourceVersionAssets(response.items);
    }).catch(() => {
      if (cancelled) return;
      setSourceVersionAssets([]);
    });

    return () => {
      cancelled = true;
    };
  }, [projectIdNum, selectedSourceLocationId, selectedSourceVersionId]);

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

  const locationImageItems = useMemo(
    () => buildSceneImageItems(locDetail?.reference_image_urls || [], locationAssets),
    [locDetail?.reference_image_urls, locationAssets],
  );

  const studioImageItems = useMemo(
    () => buildSceneImageItems(studioReferenceUrls, activeStudioVersion ? studioVersionAssets : locationAssets),
    [activeStudioVersion, locationAssets, studioReferenceUrls, studioVersionAssets],
  );

  const reusableVersionImages = useMemo(() => {
    if (!locDetail) return [];

    return locDetail.versions
      .filter((version) => version.id !== activeStudioVersion?.id)
      .flatMap((version) => version.reference_image_urls.map((url) => ({
        key: `${version.id}-${url}`,
        url,
        versionId: version.id,
        versionLabel: version.label,
      })))
      .filter((item, index, arr) => arr.findIndex((candidate) => candidate.url === item.url) === index)
      .filter((item) => !studioReferenceUrls.includes(item.url));
  }, [activeStudioVersion?.id, locDetail, studioReferenceUrls]);

  const selectedSourceVersion = useMemo(
    () => sourceLocationDetail?.versions.find((version) => version.id === selectedSourceVersionId) ?? null,
    [sourceLocationDetail?.versions, selectedSourceVersionId],
  );

  const sourceLibraryMatchesCurrentTarget = useMemo(
    () => selectedSourceLocationId === locDetail?.id && (selectedSourceVersionId ?? null) === (activeStudioVersion?.id ?? null),
    [activeStudioVersion?.id, locDetail?.id, selectedSourceLocationId, selectedSourceVersionId],
  );

  const externalSourceImageItems = useMemo(() => {
    if (sourceLibraryMatchesCurrentTarget) return [];
    const sourceReferenceUrls = selectedSourceVersion?.reference_image_urls || sourceLocationDetail?.reference_image_urls || [];
    const sourceAssets = selectedSourceVersion ? sourceVersionAssets : sourceLocationAssets;
    return buildSceneImageItems(sourceReferenceUrls, sourceAssets)
      .filter((item) => !studioReferenceUrls.includes(item.url));
  }, [selectedSourceVersion, sourceLibraryMatchesCurrentTarget, sourceLocationAssets, sourceLocationDetail?.reference_image_urls, sourceVersionAssets, studioReferenceUrls]);

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

  const updateStudioReferenceUrls = useCallback(async (urls: string[]) => {
    if (!locDetail) return null;

    if (activeStudioVersion) {
      await locationsApi.updateVersion(projectIdNum, locDetail.id, activeStudioVersion.id, {
        reference_image_urls: Array.from(new Set(urls)),
      });
    } else {
      await locationsApi.update(projectIdNum, locDetail.id, {
        reference_image_urls: Array.from(new Set(urls)),
      });
    }

    return loadLocationDetail(locDetail.id);
  }, [activeStudioVersion, loadLocationDetail, locDetail, projectIdNum]);

  const uploadFilesToLocation = useCallback(async (files: PendingImageFile[]) => {
    if (!locDetail) return [];
    const uploadedAssets = await Promise.all(
      files.map((item) => assetsApi.upload(projectIdNum, item.file, undefined, locDetail.id)),
    );
    return uploadedAssets.map((asset) => asset.file_url);
  }, [locDetail, projectIdNum]);

  const uploadFilesToStudio = useCallback(async (files: PendingImageFile[]) => {
    if (!locDetail) return [];
    const uploadedAssets = await Promise.all(
      files.map((item) => assetsApi.upload(projectIdNum, item.file, undefined, locDetail.id, activeStudioVersion?.id)),
    );
    return uploadedAssets.map((asset) => asset.file_url);
  }, [activeStudioVersion?.id, locDetail, projectIdNum]);

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
    if (!newLocName.trim()) return;
    setCreating(true);
    try {
      const location = await locationsApi.create(projectIdNum, {
        name: newLocName.trim(),
        location_type: newLocType,
        domain: newLocDomain.trim() || undefined,
        description: newLocDesc.trim() || undefined,
      });
      setLocations((prev) => [location, ...prev]);
      setSelectedLocId(location.id);
      setIsCreateDialogOpen(false);
      setNewLocName('');
      setNewLocType('outdoor');
      setNewLocDomain('');
      setNewLocDesc('');
      toast.success('场景创建成功');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '场景创建失败');
    } finally {
      setCreating(false);
    }
  }, [newLocDesc, newLocDomain, newLocName, newLocType, projectIdNum]);

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

  const openCreateVersionDialog = useCallback(() => {
    setEditingVersion(null);
    setVersionDialogOpen(true);
  }, []);

  const openEditVersionDialog = useCallback((version: LocationVersionResponse) => {
    setEditingVersion(version);
    setVersionDialogOpen(true);
  }, []);

  const handleDeleteVersion = useCallback(async (versionId: number) => {
    if (!locDetail || !window.confirm('确定删除这个场景版本吗？')) return;
    try {
      await locationsApi.deleteVersion(projectIdNum, locDetail.id, versionId);
      if (selectedStudioVersionId === versionId) {
        setSelectedStudioVersionId(locDetail.default_version?.id ?? null);
      }
      await loadLocationDetail(locDetail.id);
      toast.success('场景版本已删除');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '删除版本失败');
    }
  }, [loadLocationDetail, locDetail, projectIdNum, selectedStudioVersionId]);

  const handleSetDefaultVersion = useCallback(async (versionId: number) => {
    if (!locDetail) return;
    try {
      await locationsApi.updateVersion(projectIdNum, locDetail.id, versionId, { is_default: true });
      await loadLocationDetail(locDetail.id);
      toast.success('默认版本已更新');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '设置默认版本失败');
    }
  }, [loadLocationDetail, locDetail, projectIdNum]);

  const handleUploadSceneImages = useCallback(async () => {
    if (!locDetail || uploadFiles.length === 0) return;
    setUploadingSceneImage(true);
    try {
      const urls = await uploadFilesToStudio(uploadFiles);
      await updateStudioReferenceUrls([...(studioReferenceUrls || []), ...urls]);
      if (activeStudioVersion) {
        await loadStudioVersionAssets(locDetail.id, activeStudioVersion.id);
      }
      toast.success('场景图上传成功');
      resetPreviewFiles(uploadFiles);
      setUploadFiles([]);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '上传失败');
    } finally {
      setUploadingSceneImage(false);
    }
  }, [activeStudioVersion, loadStudioVersionAssets, locDetail, resetPreviewFiles, studioReferenceUrls, updateStudioReferenceUrls, uploadFiles, uploadFilesToStudio]);

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
        location_version_id: activeStudioVersion?.id,
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
      if (activeStudioVersion) {
        await loadStudioVersionAssets(locDetail.id, activeStudioVersion.id);
      }
      toast.success('场景图生成完成');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '生成失败');
    } finally {
      setTextGenerating(false);
    }
  }, [
    activeStudioVersion,
    loadLocationDetail,
    loadStudioVersionAssets,
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
      const uploadedUrls = img2imgFiles.length > 0 ? await uploadFilesToStudio(img2imgFiles) : [];
      if (uploadedUrls.length > 0) {
        await updateStudioReferenceUrls([...(studioReferenceUrls || []), ...uploadedUrls]);
      }

      const referenceUrls = Array.from(new Set([...selectedReferenceUrls, ...uploadedUrls])).slice(0, 5);
      const task = await tasksApi.triggerImage({
        project_id: projectIdNum,
        location_id: locDetail.id,
        location_version_id: activeStudioVersion?.id,
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
      if (activeStudioVersion) {
        await loadStudioVersionAssets(locDetail.id, activeStudioVersion.id);
      }
      resetPreviewFiles(img2imgFiles);
      setImg2imgFiles([]);
      toast.success('图生图生成完成');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '图生图失败');
    } finally {
      setImgGenerating(false);
    }
  }, [
    activeStudioVersion,
    img2imgFiles,
    imgAspectRatio,
    imgNegativePrompt,
    imgPrompt,
    imgResolution,
    imgStylePreset,
    loadLocationDetail,
    loadStudioVersionAssets,
    locDetail,
    projectIdNum,
    resetPreviewFiles,
    selectedReferenceUrls,
    studioReferenceUrls,
    updateStudioReferenceUrls,
    uploadFilesToStudio,
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

  const handleDeleteLocationImage = useCallback(async (item: SceneImageItem) => {
    if (!locDetail) return;
    try {
      if (item.assetId) {
        await assetsApi.delete(projectIdNum, item.assetId);
        await loadLocationDetail(locDetail.id);
        if (activeStudioVersion) {
          await loadStudioVersionAssets(locDetail.id, activeStudioVersion.id);
        }
        setSelectedReferenceUrls((prev) => prev.filter((url) => url !== item.url));
        toast.success('场景图片已删除');
        return;
      }

      await updateStudioReferenceUrls(studioReferenceUrls.filter((url) => url !== item.url));
      setSelectedReferenceUrls((prev) => prev.filter((url) => url !== item.url));
      toast.success('场景参考图已移除');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '删除失败');
    }
  }, [activeStudioVersion, loadLocationDetail, loadStudioVersionAssets, locDetail, projectIdNum, studioReferenceUrls, updateStudioReferenceUrls]);

  const handleAddReusableStudioImage = useCallback(async (url: string) => {
    try {
      await updateStudioReferenceUrls([...studioReferenceUrls, url]);
      toast.success('已加入当前场景图库');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '加入图库失败');
    }
  }, [studioReferenceUrls, updateStudioReferenceUrls]);

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
                  <Button onClick={handleCreateLocation} disabled={creating || !newLocName.trim()}>
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

              <Tabs value={activeWorkspaceTab} onValueChange={(value) => setActiveWorkspaceTab(value as 'studio' | 'versions' | 'details')} className="space-y-4">
                <TabsList>
                  <TabsTrigger value="studio">场景出图工作区</TabsTrigger>
                  <TabsTrigger value="versions">场景版本</TabsTrigger>
                  <TabsTrigger value="details">场景信息</TabsTrigger>
                </TabsList>

                <TabsContent value="studio" className="space-y-6">
                  <Card>
                    <CardContent className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between">
                      <div>
                        <div className="font-medium text-foreground">当前出图目标</div>
                        <div className="text-sm text-muted-foreground">
                          选择主场景或某个版本后，上传、生成、图库展示和落库都会自动切换到对应目标。
                        </div>
                      </div>
                      <div className="w-full md:w-72">
                        <Select
                          value={selectedStudioVersionId === null ? '__base__' : String(selectedStudioVersionId)}
                          onValueChange={(value) => {
                            setSelectedStudioVersionId(value === '__base__' ? null : Number(value));
                            setSelectedReferenceUrls([]);
                          }}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="__base__">主场景图库</SelectItem>
                            {locDetail.versions.map((version) => (
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
                        <CardTitle>{activeStudioVersion ? `${activeStudioVersion.label} 生成与上传` : '主场景生成与上传'}</CardTitle>
                        <CardDescription>
                          {activeStudioVersion
                            ? '当前上传、文生图和图生图结果会同步保存到该版本。'
                            : '当前上传、文生图和图生图结果会保存到主场景图库。'}
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

                            {selectedReferenceUrls.length > 0 ? (
                              <div className="space-y-3">
                                <div className="flex items-center justify-between">
                                  <div>
                                    <div className="text-sm font-medium">选择已有参考图</div>
                                    <div className="text-xs text-muted-foreground">可多选，最多 5 张</div>
                                  </div>
                                  <Badge variant="secondary">{selectedReferenceUrls.length}/5</Badge>
                                </div>

                                <div className="grid gap-3 sm:grid-cols-2">
                                  {selectedReferenceUrls.map((url) => {
                                    return (
                                      <button
                                        key={url}
                                        type="button"
                                        onClick={() => toggleReferenceSelection(url)}
                                        className="overflow-hidden rounded-xl border border-primary ring-2 ring-primary/20 text-left transition"
                                      >
                                        <img src={url} alt="" className="aspect-video w-full object-cover" />
                                      </button>
                                    );
                                  })}
                                </div>
                              </div>
                            ) : null}

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
                        <CardTitle>{activeStudioVersion ? `${activeStudioVersion.label} 版本图库` : '主场景图库'}</CardTitle>
                        <CardDescription>
                          {activeStudioVersion
                            ? '右侧只展示当前版本的场景素材图；也可以把其他版本的图片加入当前版本图库。'
                            : '这里展示主场景图库，也可以复用其他版本的场景图加入当前主场景。'}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="space-y-3">
                          <div className="flex items-center justify-between gap-3">
                            <div>
                              <div className="text-sm font-medium">
                                {activeStudioVersion ? '上传到当前版本图库' : '上传到主场景图库'}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                点击或拖拽图片到这里，上传后会保存到当前选中的出图目标。
                              </div>
                            </div>
                            {uploadFiles.length > 0 ? (
                              <Button onClick={handleUploadSceneImages} disabled={uploadingSceneImage}>
                                {uploadingSceneImage ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ImagePlus className="mr-2 h-4 w-4" />}
                                {activeStudioVersion ? '保存到当前版本' : '保存到主场景'}
                              </Button>
                            ) : null}
                          </div>

                          <FileDropZone
                            onSelect={(files) => addPendingFiles(files, 'upload')}
                            disabled={uploadingSceneImage}
                            title={activeStudioVersion ? '上传版本场景图' : '上传主场景图'}
                            description="支持点击选择和拖拽上传，JPG / PNG / WebP / GIF，单张不超过 10MB"
                          />

                          {uploadFiles.length > 0 ? (
                            <div className="grid gap-3 sm:grid-cols-2">
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
                        </div>

                        <div className="space-y-3 rounded-xl border bg-secondary/10 p-4">
                            <div>
                              <div className="text-sm font-medium">引用已有图片</div>
                              <div className="text-xs text-muted-foreground">
                                可从当前场景的其他版本，或项目内其他场景/版本图库中选择图片，直接加入当前图库。
                              </div>
                            </div>

                          <div className="grid gap-3 md:grid-cols-2">
                            <div className="space-y-2">
                              <label className="text-xs font-medium text-muted-foreground">来源场景</label>
                              <Select
                                value={selectedSourceLocationId ? String(selectedSourceLocationId) : undefined}
                                onValueChange={(value) => {
                                  setSelectedSourceLocationId(Number(value));
                                  setSelectedSourceVersionId(null);
                                  setSourceVersionAssets([]);
                                }}
                                disabled={sourceLocationOptions.length === 0}
                              >
                                <SelectTrigger>
                                  <SelectValue placeholder="选择来源场景" />
                                </SelectTrigger>
                                <SelectContent>
                                  {sourceLocationOptions.map((location) => (
                                    <SelectItem key={location.id} value={String(location.id)}>
                                      {location.id === locDetail?.id ? `${location.name}（当前场景）` : `${location.name} (${location.loc_code})`}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>

                            <div className="space-y-2">
                              <label className="text-xs font-medium text-muted-foreground">来源图库</label>
                              <Select
                                value={selectedSourceVersionId === null ? '__base__' : String(selectedSourceVersionId)}
                                onValueChange={(value) => {
                                  setSelectedSourceVersionId(value === '__base__' ? null : Number(value));
                                  setSourceVersionAssets([]);
                                }}
                                disabled={!sourceLocationDetail || sourceLocationOptions.length === 0}
                              >
                                <SelectTrigger>
                                  <SelectValue placeholder="选择主图库或版本图库" />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="__base__">主场景图库</SelectItem>
                                  {sourceLocationDetail?.versions.map((version) => (
                                    <SelectItem key={version.id} value={String(version.id)}>
                                      {version.label} ({version.version_code})
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                          </div>

                          {sourceLocationOptions.length === 0 ? (
                            <div className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
                              当前项目还没有可引用的场景或版本图库。
                            </div>
                          ) : sourceLibraryMatchesCurrentTarget ? (
                            <div className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
                              当前选中的来源就是正在编辑的图库本身，请切换到当前场景的其他版本，或选择其他场景/版本进行引用。
                            </div>
                          ) : loadingSourceLibrary ? (
                            <div className="flex items-center justify-center rounded-xl border border-dashed p-6 text-sm text-muted-foreground">
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              正在加载来源图库...
                            </div>
                          ) : externalSourceImageItems.length > 0 ? (
                            <div className="grid gap-3 sm:grid-cols-2">
                              {externalSourceImageItems.map((item, index) => (
                                <div key={`${item.url}-${index}`} className="overflow-hidden rounded-xl border bg-card">
                                  <img src={item.url} alt="" className="aspect-video w-full object-cover" />
                                  <div className="flex items-center justify-between gap-2 p-3">
                                    <div className="text-xs text-muted-foreground">
                                      {selectedSourceVersion ? `${sourceLocationDetail?.name} / ${selectedSourceVersion.label}` : sourceLocationDetail?.name}
                                    </div>
                                    <Button size="sm" variant="outline" onClick={() => handleAddReusableStudioImage(item.url)}>
                                      引用到当前图库
                                    </Button>
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
                              当前来源图库暂无可引用图片，或者这些图片已经在当前图库中了。
                            </div>
                          )}
                        </div>

                        {studioImageItems.length === 0 ? (
                          <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
                            还没有场景图。你可以先输入提示词生成一张，或者上传本地图片。
                          </div>
                        ) : (
                          <div className="grid gap-4 sm:grid-cols-2">
                            {studioImageItems.map((item, index) => {
                              const url = item.url;
                              return (
                              <div key={item.url} className="overflow-hidden rounded-xl border bg-card">
                                <img src={item.url} alt={`场景图 ${index + 1}`} className="aspect-video w-full object-cover" />
                                <div className="flex items-center justify-between gap-2 p-3">
                                  <div className="text-xs text-muted-foreground">场景图 #{index + 1}</div>
                                  <div className="flex items-center gap-2">
                                    <Button
                                      variant={selectedReferenceUrls.includes(item.url) ? 'default' : 'outline'}
                                      size="sm"
                                      onClick={() => toggleReferenceSelection(item.url)}
                                    >
                                      {selectedReferenceUrls.includes(url) ? '已选中' : '设为参考图'}
                                    </Button>
                                    <Button variant="ghost" size="icon" onClick={() => handleDeleteLocationImage(item)}>
                                      <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                                    </Button>
                                  </div>
                                </div>
                              </div>
                              );
                            })}
                          </div>
                        )}
                        {reusableVersionImages.length > 0 ? (
                          <div className="space-y-3">
                            <div>
                              <div className="text-sm font-medium">其他版本可复用场景图</div>
                              <div className="text-xs text-muted-foreground">可直接加入当前选中目标的场景图库。</div>
                            </div>
                            <div className="grid gap-4 sm:grid-cols-2">
                              {reusableVersionImages.map((item) => (
                                <div key={item.key} className="overflow-hidden rounded-xl border bg-card">
                                  <img src={item.url} alt={item.versionLabel} className="aspect-video w-full object-cover" />
                                  <div className="flex items-center justify-between gap-2 p-3">
                                    <div>
                                      <div className="text-xs text-muted-foreground">{item.versionLabel}</div>
                                      <div className="text-xs text-muted-foreground">来自其他版本</div>
                                    </div>
                                    <Button size="sm" variant="outline" onClick={() => handleAddReusableStudioImage(item.url)}>
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
                </TabsContent>

                <TabsContent value="versions" className="space-y-4">
                  <Card>
                    <CardContent className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between">
                      <div>
                        <div className="font-medium text-foreground">场景版本管理</div>
                        <div className="text-sm text-muted-foreground">
                          为同一个场景维护白天、夜景、战损等多套版本，并分别管理版本场景图。
                        </div>
                      </div>
                      <Button onClick={openCreateVersionDialog}>
                        <Plus className="mr-2 h-4 w-4" />
                        新增版本
                      </Button>
                    </CardContent>
                  </Card>

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

                            <div className="flex flex-wrap gap-2">
                              {!version.is_default ? (
                                <Button variant="outline" size="sm" onClick={() => handleSetDefaultVersion(version.id)}>
                                  设为默认
                                </Button>
                              ) : null}
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                  setSelectedStudioVersionId(version.id);
                                  setActiveWorkspaceTab('studio');
                                }}
                              >
                                <Sparkles className="mr-2 h-4 w-4" />
                                图片工作台
                              </Button>
                              <Button variant="outline" size="sm" onClick={() => openEditVersionDialog(version)}>
                                编辑版本
                              </Button>
                              <Button variant="ghost" size="sm" onClick={() => handleDeleteVersion(version.id)}>
                                <Trash2 className="mr-2 h-4 w-4 text-muted-foreground" />
                                删除
                              </Button>
                            </div>

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

              <LocationVersionDialog
                open={versionDialogOpen}
                onOpenChange={setVersionDialogOpen}
                projectId={projectIdNum}
                locationId={locDetail.id}
                version={editingVersion}
                onSuccess={async () => {
                  await loadLocationDetail(locDetail.id);
                }}
              />

            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}

function LocationVersionDialog({
  open,
  onOpenChange,
  projectId,
  locationId,
  version,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: number;
  locationId: number;
  version: LocationVersionResponse | null;
  onSuccess: () => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);
  const [versionCode, setVersionCode] = useState('');
  const [label, setLabel] = useState('');
  const [description, setDescription] = useState('');
  const [timeOfDay, setTimeOfDay] = useState('');
  const [weather, setWeather] = useState('');
  const [additionalElements, setAdditionalElements] = useState('');
  const [removedElements, setRemovedElements] = useState('');
  const [promptSuffix, setPromptSuffix] = useState('');
  const [fullPrompt, setFullPrompt] = useState('');
  const [applicableSceneCodes, setApplicableSceneCodes] = useState('');
  const [isDefault, setIsDefault] = useState(false);

  useEffect(() => {
    if (!open) return;
    setVersionCode(version?.version_code ?? '');
    setLabel(version?.label ?? '');
    setDescription(version?.description ?? '');
    setTimeOfDay(version?.time_of_day ?? '');
    setWeather(version?.weather ?? '');
    setAdditionalElements((version?.additional_elements ?? []).join('\n'));
    setRemovedElements((version?.removed_elements ?? []).join('\n'));
    setPromptSuffix(version?.prompt_suffix ?? '');
    setFullPrompt(version?.full_prompt ?? '');
    setApplicableSceneCodes((version?.applicable_scene_codes ?? []).join('\n'));
    setIsDefault(version?.is_default ?? false);
  }, [open, version]);

  const handleSave = useCallback(async () => {
    const normalizedVersionCode = versionCode.trim().toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
    if (!label.trim()) {
      toast.error('请输入版本名称');
      return;
    }
    if (!version && !normalizedVersionCode) {
      toast.error('请输入版本编码');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        label: label.trim(),
        description: description.trim() || undefined,
        time_of_day: timeOfDay || undefined,
        weather: weather || undefined,
        additional_elements: splitMultilineValue(additionalElements),
        removed_elements: splitMultilineValue(removedElements),
        prompt_suffix: promptSuffix.trim() || undefined,
        full_prompt: fullPrompt.trim() || undefined,
        applicable_scene_codes: splitMultilineValue(applicableSceneCodes),
        is_default: isDefault,
      };

      if (version) {
        await locationsApi.updateVersion(projectId, locationId, version.id, payload);
        toast.success('场景版本已更新');
      } else {
        await locationsApi.createVersion(projectId, locationId, {
          version_code: normalizedVersionCode,
          ...payload,
        });
        toast.success('场景版本已创建');
      }

      await onSuccess();
      onOpenChange(false);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '保存版本失败');
    } finally {
      setSaving(false);
    }
  }, [
    additionalElements,
    applicableSceneCodes,
    description,
    fullPrompt,
    isDefault,
    label,
    locationId,
    onOpenChange,
    onSuccess,
    projectId,
    promptSuffix,
    removedElements,
    timeOfDay,
    version,
    versionCode,
    weather,
  ]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{version ? '编辑场景版本' : '新增场景版本'}</DialogTitle>
          <DialogDescription>
            版本可用于区分白天、夜景、战损、雨天等不同场景状态，并拥有独立场景图。
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium">版本名称</label>
            <Input value={label} onChange={(event) => setLabel(event.target.value)} placeholder="例如：夜景" />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">版本编码</label>
            <Input
              value={versionCode}
              onChange={(event) => setVersionCode(event.target.value)}
              placeholder="例如：night"
              disabled={Boolean(version)}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">时间</label>
            <Select value={timeOfDay || '__none__'} onValueChange={(value) => setTimeOfDay(value === '__none__' ? '' : value)}>
              <SelectTrigger>
                <SelectValue placeholder="未设置" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">未设置</SelectItem>
                {Object.entries(timeOfDayLabels).map(([value, text]) => (
                  <SelectItem key={value} value={value}>{text}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">天气</label>
            <Select value={weather || '__none__'} onValueChange={(value) => setWeather(value === '__none__' ? '' : value)}>
              <SelectTrigger>
                <SelectValue placeholder="未设置" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">未设置</SelectItem>
                {Object.entries(weatherLabels).map(([value, text]) => (
                  <SelectItem key={value} value={value}>{text}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">版本描述</label>
          <Textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={3} />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium">新增元素</label>
            <Textarea value={additionalElements} onChange={(event) => setAdditionalElements(event.target.value)} rows={4} placeholder="每行一个，或用逗号分隔" />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">移除元素</label>
            <Textarea value={removedElements} onChange={(event) => setRemovedElements(event.target.value)} rows={4} placeholder="每行一个，或用逗号分隔" />
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium">追加提示词</label>
            <Textarea value={promptSuffix} onChange={(event) => setPromptSuffix(event.target.value)} rows={3} />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">完整提示词覆盖</label>
            <Textarea value={fullPrompt} onChange={(event) => setFullPrompt(event.target.value)} rows={3} />
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">适用场景编码</label>
          <Textarea value={applicableSceneCodes} onChange={(event) => setApplicableSceneCodes(event.target.value)} rows={3} placeholder="每行一个 scene code" />
        </div>

        <label className="flex items-center gap-2 text-sm text-foreground">
          <input type="checkbox" checked={isDefault} onChange={(event) => setIsDefault(event.target.checked)} />
          设为默认版本
        </label>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            保存版本
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function LocationVersionStudioDialog({
  open,
  onOpenChange,
  projectId,
  locationId,
  version,
  onRefresh,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: number;
  locationId: number;
  version: LocationVersionResponse | null;
  onRefresh: () => Promise<void>;
}) {
  const [uploadFiles, setUploadFiles] = useState<PendingImageFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [stylePreset, setStylePreset] = useState('');
  const [aspectRatio, setAspectRatio] = useState('16:9');
  const [resolution, setResolution] = useState('1K');
  const [generating, setGenerating] = useState(false);
  const [imgPrompt, setImgPrompt] = useState('');
  const [imgNegativePrompt, setImgNegativePrompt] = useState('');
  const [imgStylePreset, setImgStylePreset] = useState('');
  const [imgAspectRatio, setImgAspectRatio] = useState('16:9');
  const [imgResolution, setImgResolution] = useState('1K');
  const [img2imgFiles, setImg2imgFiles] = useState<PendingImageFile[]>([]);
  const [versionAssets, setVersionAssets] = useState<AssetResponse[]>([]);
  const [selectedReferenceUrls, setSelectedReferenceUrls] = useState<string[]>([]);
  const [imgGenerating, setImgGenerating] = useState(false);

  const resetPreviewFiles = useCallback((files: PendingImageFile[]) => {
    files.forEach((item) => URL.revokeObjectURL(item.preview));
  }, []);

  useEffect(() => {
    if (!open || !version) return;
    setSelectedReferenceUrls(version.reference_image_urls.slice(0, 5));
  }, [open, version]);

  const loadVersionAssets = useCallback(async () => {
    if (!version) {
      setVersionAssets([]);
      return [];
    }
    const items = await assetsApi.list(projectId, 1, 100, {
      assetType: 'image',
      locationId,
      locationVersionId: version.id,
      isCurrent: true,
    }).then((response) => response.items);
    setVersionAssets(items);
    return items;
  }, [locationId, projectId, version]);

  useEffect(() => {
    if (open) {
      loadVersionAssets().catch(() => setVersionAssets([]));
      return;
    }
    resetPreviewFiles(uploadFiles);
    resetPreviewFiles(img2imgFiles);
    setUploadFiles([]);
    setImg2imgFiles([]);
    setPrompt('');
    setNegativePrompt('');
    setStylePreset('');
    setImgPrompt('');
    setImgNegativePrompt('');
    setImgStylePreset('');
    setAspectRatio('16:9');
    setResolution('1K');
    setImgAspectRatio('16:9');
    setImgResolution('1K');
    setSelectedReferenceUrls([]);
    setVersionAssets([]);
  }, [img2imgFiles, loadVersionAssets, open, resetPreviewFiles, uploadFiles]);

  const versionImageItems = useMemo(
    () => buildSceneImageItems(version?.reference_image_urls || [], versionAssets),
    [version?.reference_image_urls, versionAssets],
  );

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
      if (removed) {
        URL.revokeObjectURL(removed.preview);
      }
      return prev.filter((item) => item.id !== id);
    });
  }, []);

  const syncReferenceUrls = useCallback(async (urls: string[]) => {
    if (!version) return;
    await locationsApi.updateVersion(projectId, locationId, version.id, {
      reference_image_urls: Array.from(new Set(urls)),
    });
    await onRefresh();
  }, [locationId, onRefresh, projectId, version]);

  const uploadFilesToVersion = useCallback(async (files: PendingImageFile[]) => {
    const assets = await Promise.all(
      files.map((item) => assetsApi.upload(projectId, item.file, undefined, locationId, version?.id)),
    );
    return assets.map((asset) => asset.file_url);
  }, [locationId, projectId, version?.id]);

  const waitForTask = useCallback(async (taskId: number) => {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      const task = await tasksApi.get(taskId);
      if (task.status === 'success') return task;
      if (task.status === 'failed') {
        throw new Error(task.error_message || '图片生成失败');
      }
      await new Promise((resolve) => setTimeout(resolve, 5000));
    }
    throw new Error('生成耗时较长，请稍后刷新查看结果');
  }, []);

  const handleUpload = useCallback(async () => {
    if (!version || uploadFiles.length === 0) return;
    setUploading(true);
    try {
      const urls = await uploadFilesToVersion(uploadFiles);
      await syncReferenceUrls([...(version.reference_image_urls || []), ...urls]);
      await loadVersionAssets();
      toast.success('版本场景图已上传');
      resetPreviewFiles(uploadFiles);
      setUploadFiles([]);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '上传失败');
    } finally {
      setUploading(false);
    }
  }, [loadVersionAssets, resetPreviewFiles, syncReferenceUrls, uploadFiles, uploadFilesToVersion, version]);

  const handlePromptGenerate = useCallback(async () => {
    if (!version || !prompt.trim()) {
      toast.error('请输入提示词');
      return;
    }
    setGenerating(true);
    try {
      const task = await tasksApi.triggerImage({
        project_id: projectId,
        location_id: locationId,
        location_version_id: version.id,
        prompt: prompt.trim(),
        negative_prompt: negativePrompt.trim() || undefined,
        aspect_ratio: aspectRatio,
        resolution,
        style_preset: stylePreset.trim() || undefined,
      });
      await waitForTask(task.id);
      await onRefresh();
      await loadVersionAssets();
      toast.success('版本场景图生成完成');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '生成失败');
    } finally {
      setGenerating(false);
    }
  }, [aspectRatio, loadVersionAssets, locationId, negativePrompt, onRefresh, projectId, prompt, resolution, stylePreset, version, waitForTask]);

  const handleImageGenerate = useCallback(async () => {
    if (!version || !imgPrompt.trim()) {
      toast.error('请输入图生图提示词');
      return;
    }
    if (selectedReferenceUrls.length === 0 && img2imgFiles.length === 0) {
      toast.error('请至少准备一张参考图');
      return;
    }

    setImgGenerating(true);
    try {
      const uploadedUrls = img2imgFiles.length > 0 ? await uploadFilesToVersion(img2imgFiles) : [];
      if (uploadedUrls.length > 0) {
        await syncReferenceUrls([...(version.reference_image_urls || []), ...uploadedUrls]);
      }

      const task = await tasksApi.triggerImage({
        project_id: projectId,
        location_id: locationId,
        location_version_id: version.id,
        prompt: imgPrompt.trim(),
        negative_prompt: imgNegativePrompt.trim() || undefined,
        aspect_ratio: imgAspectRatio,
        resolution: imgResolution,
        style_preset: imgStylePreset.trim() || undefined,
        reference_image_urls: Array.from(new Set([...selectedReferenceUrls, ...uploadedUrls])).slice(0, 5),
      });
      await waitForTask(task.id);
      await onRefresh();
      await loadVersionAssets();
      resetPreviewFiles(img2imgFiles);
      setImg2imgFiles([]);
      toast.success('版本图生图完成');
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
    locationId,
    onRefresh,
    projectId,
    resetPreviewFiles,
    selectedReferenceUrls,
    syncReferenceUrls,
    uploadFilesToVersion,
    version,
    waitForTask,
    loadVersionAssets,
  ]);

  const handleRemoveReferenceImage = useCallback(async (url: string) => {
    if (!version) return;
    try {
      await syncReferenceUrls(version.reference_image_urls.filter((item) => item !== url));
      setSelectedReferenceUrls((prev) => prev.filter((item) => item !== url));
      toast.success('已移除版本场景图');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '移除失败');
    }
  }, [syncReferenceUrls, version]);

  const handleDeleteVersionImage = useCallback(async (item: SceneImageItem) => {
    if (!version) return;
    try {
      if (item.assetId) {
        await assetsApi.delete(projectId, item.assetId);
        await onRefresh();
        await loadVersionAssets();
        setSelectedReferenceUrls((prev) => prev.filter((url) => url !== item.url));
        toast.success('版本场景图已删除');
        return;
      }

      await syncReferenceUrls(version.reference_image_urls.filter((url) => url !== item.url));
      setSelectedReferenceUrls((prev) => prev.filter((url) => url !== item.url));
      toast.success('版本参考图已移除');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '删除失败');
    }
  }, [loadVersionAssets, onRefresh, projectId, syncReferenceUrls, version]);

  const toggleReferenceSelection = useCallback((url: string) => {
    setSelectedReferenceUrls((prev) => {
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

  if (!version) {
    return null;
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl">
        <DialogHeader>
          <DialogTitle>{version.label} 图片工作台</DialogTitle>
          <DialogDescription>
            这里管理当前版本的独立场景图，支持手动上传、文生图和图生图。
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">生成与上传</CardTitle>
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
                    <Textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} rows={5} />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">负向提示词</label>
                    <Input value={negativePrompt} onChange={(event) => setNegativePrompt(event.target.value)} />
                  </div>
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">画幅比例</label>
                      <Select value={aspectRatio} onValueChange={setAspectRatio}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {aspectRatios.map((item) => (
                            <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">分辨率</label>
                      <Select value={resolution} onValueChange={setResolution}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {resolutions.map((item) => (
                            <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">风格预设</label>
                      <Input value={stylePreset} onChange={(event) => setStylePreset(event.target.value)} />
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <Button onClick={handlePromptGenerate} disabled={generating || !prompt.trim()}>
                      {generating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Wand2 className="mr-2 h-4 w-4" />}
                      生成版本场景图
                    </Button>
                  </div>
                </TabsContent>

                <TabsContent value="upload" className="space-y-4">
                  <FileDropZone
                    onSelect={(files) => addPendingFiles(files, 'upload')}
                    disabled={uploading}
                    title="上传版本场景图"
                    description="支持 JPG、PNG、WebP、GIF，单张不超过 10MB"
                  />
                  {uploadFiles.length > 0 ? (
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {uploadFiles.map((item) => (
                        <div key={item.id} className="rounded-xl border bg-secondary/20 p-2">
                          <div className="relative overflow-hidden rounded-lg">
                            <img src={item.preview} alt={item.file.name} className="aspect-video w-full object-cover" />
                            <Button variant="secondary" size="icon" className="absolute right-2 top-2 h-7 w-7" onClick={() => removePendingFile(item.id, 'upload')}>
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                          <div className="mt-2 truncate text-xs text-muted-foreground">{item.file.name}</div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                  <div className="flex justify-end">
                    <Button onClick={handleUpload} disabled={uploading || uploadFiles.length === 0}>
                      {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ImagePlus className="mr-2 h-4 w-4" />}
                      保存到当前版本
                    </Button>
                  </div>
                </TabsContent>

                <TabsContent value="img2img" className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">图生图提示词</label>
                    <Textarea value={imgPrompt} onChange={(event) => setImgPrompt(event.target.value)} rows={4} />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">负向提示词</label>
                    <Input value={imgNegativePrompt} onChange={(event) => setImgNegativePrompt(event.target.value)} />
                  </div>
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">画幅比例</label>
                      <Select value={imgAspectRatio} onValueChange={setImgAspectRatio}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
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
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {resolutions.map((item) => (
                            <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">风格预设</label>
                      <Input value={imgStylePreset} onChange={(event) => setImgStylePreset(event.target.value)} />
                    </div>
                  </div>

                  <Separator />

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="text-sm font-medium">选择已有版本参考图</div>
                      <Badge variant="secondary">{selectedReferenceUrls.length}/5</Badge>
                    </div>
                    {selectedReferenceUrls.length > 0 ? (
                      <div className="grid gap-3 sm:grid-cols-2">
                        {selectedReferenceUrls.map((url) => {
                          return (
                            <button
                              key={url}
                              type="button"
                              onClick={() => toggleReferenceSelection(url)}
                              className="overflow-hidden rounded-xl border border-primary ring-2 ring-primary/20 text-left transition"
                            >
                              <img src={url} alt="" className="aspect-video w-full object-cover" />
                            </button>
                          );
                        })}
                      </div>
                    ) : version.reference_image_urls.length > 0 ? (
                      <div className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">
                        暂未选中参考图，请在右侧版本图库中点击“设为参考图”。
                      </div>
                    ) : (
                      <div className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">
                        当前版本还没有参考图，可先上传再进行图生图。
                      </div>
                    )}
                  </div>

                  <div className="space-y-3">
                    <div>
                      <div className="text-sm font-medium">补充新的参考图</div>
                      <div className="text-xs text-muted-foreground">上传后会自动并入当前版本的场景图库。</div>
                    </div>
                    <FileDropZone
                      onSelect={(files) => addPendingFiles(files, 'img2img')}
                      disabled={imgGenerating}
                      title="添加参考图"
                      description="支持上传 1-5 张图作为图生图参考"
                    />
                    {img2imgFiles.length > 0 ? (
                      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        {img2imgFiles.map((item) => (
                          <div key={item.id} className="rounded-xl border bg-secondary/20 p-2">
                            <div className="relative overflow-hidden rounded-lg">
                              <img src={item.preview} alt={item.file.name} className="aspect-video w-full object-cover" />
                              <Button variant="secondary" size="icon" className="absolute right-2 top-2 h-7 w-7" onClick={() => removePendingFile(item.id, 'img2img')}>
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
                    <Button onClick={handleImageGenerate} disabled={imgGenerating || !imgPrompt.trim()}>
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
              <CardTitle className="text-base">当前版本图库</CardTitle>
              <CardDescription>每张图都只属于当前版本，可独立删除和复用。</CardDescription>
            </CardHeader>
            <CardContent>
              {versionImageItems.length === 0 ? (
                <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
                  当前版本还没有场景图。
                </div>
              ) : (
                <div className="grid gap-4">
                  {versionImageItems.map((item, index) => {
                    const url = item.url;
                    return (
                    <div key={url} className="overflow-hidden rounded-xl border bg-card">
                      <img src={url} alt={`版本场景图 ${index + 1}`} className="aspect-video w-full object-cover" />
                      <div className="flex items-center justify-between gap-2 p-3">
                        <div className="text-xs text-muted-foreground">版本场景图 #{index + 1}</div>
                        <div className="flex items-center gap-2">
                          <Button
                            variant={selectedReferenceUrls.includes(url) ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => toggleReferenceSelection(url)}
                          >
                            {selectedReferenceUrls.includes(url) ? '已选中' : '设为参考图'}
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => handleDeleteVersionImage(item)}>
                            <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
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
        </div>
      </DialogContent>
    </Dialog>
  );
}
