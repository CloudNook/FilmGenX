'use client';

import { use, useCallback, useEffect, useRef, useState } from 'react';
import { AppLayout } from '@/components/layout';
import {
  assetsApi,
  locationsApi,
  projectsApi,
  type AssetResponse,
  type LocationResponse,
  type ProjectResponse,
} from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import {
  Building,
  Camera,
  Eye,
  Image as ImageIcon,
  Loader2,
  MapPin,
  Plus,
  Search,
  Trash2,
  Trees,
  Upload,
  X,
  Layers,
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
  fantasy: Layers,
  mixed: Layers,
};

interface PendingImageFile {
  id: string;
  file: File;
  preview: string;
}

function createPendingImageFiles(files: FileList | null, limit: number): PendingImageFile[] {
  if (!files || files.length === 0) return [];
  const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
  const nextFiles: PendingImageFile[] = [];
  Array.from(files).slice(0, limit).forEach((file) => {
    if (!validTypes.includes(file.type)) {
      toast.error(`${file.name} 不是支持的图片格式`);
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error(`${file.name} 超过 10MB 限制`);
      return;
    }
    nextFiles.push({ id: `${Date.now()}-${Math.random()}`, file, preview: URL.createObjectURL(file) });
  });
  return nextFiles;
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
      onDragOver={(event) => { if (disabled) return; event.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => { if (disabled) return; event.preventDefault(); setDragging(false); onSelect(event.dataTransfer.files); }}
    >
      <input className="hidden" type="file" accept="image/*" multiple disabled={disabled} onChange={(event) => { onSelect(event.target.files); event.target.value = ''; }} />
      <div className="flex flex-col items-center justify-center gap-3 text-center">
        <div className="rounded-full bg-secondary p-3 text-muted-foreground"><Upload className="h-6 w-6" /></div>
        <div><p className="font-medium text-foreground">{title}</p><p className="text-sm text-muted-foreground">{description}</p></div>
      </div>
    </label>
  );
}

function FullscreenPreview({ url, open, onOpenChange }: { url: string | null; open: boolean; onOpenChange: (open: boolean) => void }) {
  if (!url) return null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl overflow-hidden p-0">
        <img src={url} alt="Preview" className="max-h-[85vh] w-full object-contain bg-black/95" />
      </DialogContent>
    </Dialog>
  );
}

function AssetLibraryPickerDialog({
  open, onOpenChange, projectId, onSelect, title, description, selectLabel,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: number;
  onSelect: (url: string) => Promise<void>;
  title: string;
  description: string;
  selectLabel: string;
}) {
  const pageSize = 12;
  const [assets, setAssets] = useState<AssetResponse[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [submittingUrl, setSubmittingUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setPage(1);
    assetsApi.list(projectId, 1, pageSize, { assetType: 'image', isCurrent: true })
      .then((response) => { setAssets(response.items); setTotal(response.total); })
      .catch(() => { setAssets([]); setTotal(0); })
      .finally(() => setLoading(false));
  }, [open, projectId]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const loadPage = useCallback((p: number) => {
    setLoading(true);
    assetsApi.list(projectId, p, pageSize, { assetType: 'image', isCurrent: true })
      .then((response) => { setAssets(response.items); setTotal(response.total); setPage(p); })
      .catch(() => { setAssets([]); })
      .finally(() => setLoading(false));
  }, [projectId]);

  const handleSelect = useCallback(async (url: string) => {
    setSubmittingUrl(url);
    try { await onSelect(url); } finally { setSubmittingUrl(null); }
  }, [onSelect]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl">
        <DialogHeader><DialogTitle>{title}</DialogTitle></DialogHeader>
        <p className="text-sm text-muted-foreground">{description}</p>
        <div className="max-h-[60vh] overflow-hidden flex flex-col">
          <ScrollArea className="flex-1">
            {loading ? (
              <div className="flex items-center justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>
            ) : assets.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground">素材库中暂无图片</div>
            ) : (
              <div className="grid grid-cols-2 gap-4 p-1 sm:grid-cols-3">
                {assets.map((asset) => {
                  const assetLabel = asset.description || asset.tags.join(', ') || `素材 #${asset.id}`;
                  const isSubmitting = submittingUrl === asset.file_url;
                  return (
                    <div key={asset.id} className="group overflow-hidden rounded-xl border bg-card transition hover:shadow-md">
                      <div className="relative aspect-[4/3] overflow-hidden">
                        <img src={asset.file_url} alt={assetLabel} className="aspect-[4/3] w-full object-cover transition duration-300 group-hover:scale-[1.02]" />
                      </div>
                      <div className="space-y-3 p-4">
                        <div className="line-clamp-1 text-sm font-semibold text-foreground" title={assetLabel}>{assetLabel}</div>
                        <div className="text-xs text-muted-foreground">{`素材 #${asset.id}`}</div>
                        <Button className="w-full" size="sm" variant="outline" disabled={Boolean(submittingUrl)} onClick={() => handleSelect(asset.file_url)}>
                          {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                          {selectLabel}
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
              <Pagination>
                <PaginationContent>
                  <PaginationItem><PaginationPrevious href="#" onClick={(event) => { event.preventDefault(); if (page > 1 && !loading) loadPage(page - 1); }} className={page <= 1 || loading ? 'pointer-events-none opacity-50' : ''} /></PaginationItem>
                  <PaginationItem><span className="px-3 text-sm font-medium text-muted-foreground">{`第 ${page} / ${totalPages} 页`}</span></PaginationItem>
                  <PaginationItem><PaginationNext href="#" onClick={(event) => { event.preventDefault(); if (page < totalPages && !loading) loadPage(page + 1); }} className={page >= totalPages || loading ? 'pointer-events-none opacity-50' : ''} /></PaginationItem>
                </PaginationContent>
              </Pagination>
            </div>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function LocationsPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = use(params);
  const projectIdNum = Number(projectId);

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [locations, setLocations] = useState<LocationResponse[]>([]);
  const [selectedLocId, setSelectedLocId] = useState<number | null>(null);
  const [locDetail, setLocDetail] = useState<LocationResponse | null>(null);
  const [locationAssets, setLocationAssets] = useState<AssetResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newLocName, setNewLocName] = useState('');
  const [newLocType, setNewLocType] = useState('outdoor');

  const [uploadFiles, setUploadFiles] = useState<PendingImageFile[]>([]);
  const [uploadingSceneImage, setUploadingSceneImage] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [uploadingPic, setUploadingPic] = useState(false);
  const [deletingPic, setDeletingPic] = useState(false);
  const picFileInputRef = useRef<HTMLInputElement>(null);
  const uploadFilesRef = useRef<PendingImageFile[]>([]);

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
    setLocationAssets(items);
    return items;
  }, [projectIdNum]);

  const loadLocationDetail = useCallback(async (locationId: number) => {
    const detail = await locationsApi.get(projectIdNum, locationId);
    setLocDetail(detail);
    return detail;
  }, [projectIdNum]);

  useEffect(() => {
    if (isNaN(projectIdNum)) return;
    Promise.all([
      projectsApi.get(projectIdNum).catch(() => null),
      loadLocations(),
    ]).then(([projectRes, locs]) => {
      setProject(projectRes);
      if (locs.length > 0) setSelectedLocId(locs[0].id);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [projectIdNum, loadLocations]);

  useEffect(() => {
    if (!selectedLocId) { setLocDetail(null); setLocationAssets([]); return; }
    loadLocationDetail(selectedLocId);
    loadLocationAssets(selectedLocId);
  }, [selectedLocId, loadLocationDetail, loadLocationAssets]);

  const uploadFilesToLocation = useCallback(async (files: PendingImageFile[]) => {
    return Promise.all(
      files.map((item) => assetsApi.upload(projectIdNum, item.file, undefined, locDetail!.id)),
    );
  }, [locDetail, projectIdNum]);

  // Handle upload cover pic
  const handleUploadPic = useCallback(async (file: File) => {
    if (!locDetail) return;
    setUploadingPic(true);
    try {
      const updated = await locationsApi.uploadPic(projectIdNum, locDetail.id, file);
      setLocDetail(updated);
      setLocations(prev => prev.map(l => l.id === updated.id ? updated : l));
      toast.success('封面图上传成功');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '上传失败');
    } finally {
      setUploadingPic(false);
    }
  }, [locDetail, projectIdNum]);

  // Handle delete cover pic
  const handleDeletePic = useCallback(async () => {
    if (!locDetail) return;
    setDeletingPic(true);
    try {
      const updated = await locationsApi.deletePic(projectIdNum, locDetail.id);
      setLocDetail(updated);
      setLocations(prev => prev.map(l => l.id === updated.id ? updated : l));
      toast.success('封面图已删除');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    } finally {
      setDeletingPic(false);
    }
  }, [locDetail, projectIdNum]);

  // Handle upload files to asset library
  const handleUploadFiles = useCallback(async () => {
    if (!locDetail || uploadFiles.length === 0) return;
    setUploadingSceneImage(true);
    try {
      await uploadFilesToLocation(uploadFiles);
      resetPreviewFiles(uploadFiles);
      setUploadFiles([]);
      await loadLocationAssets(locDetail.id);
      toast.success('上传成功');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '上传失败');
    } finally {
      setUploadingSceneImage(false);
    }
  }, [locDetail, uploadFiles, uploadFilesToLocation, resetPreviewFiles, loadLocationAssets]);

  // Create location
  const handleCreateLocation = useCallback(async () => {
    if (!newLocName.trim()) return;
    setCreating(true);
    try {
      const loc = await locationsApi.create(projectIdNum, {
        name: newLocName.trim(),
        location_type: newLocType,
      });
      setLocations(prev => [loc, ...prev]);
      setSelectedLocId(loc.id);
      setIsCreateDialogOpen(false);
      setNewLocName('');
      toast.success('场景创建成功');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '创建失败');
    } finally {
      setCreating(false);
    }
  }, [projectIdNum, newLocName, newLocType]);

  // Delete location
  const handleDeleteLocation = useCallback(async (locId: number) => {
    if (!confirm('确定要删除这个场景吗？')) return;
    try {
      await locationsApi.delete(projectIdNum, locId);
      setLocations(prev => prev.filter(l => l.id !== locId));
      if (selectedLocId === locId) { setSelectedLocId(null); setLocDetail(null); }
      toast.success('场景已删除');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    }
  }, [projectIdNum, selectedLocId]);

  const filteredLocations = locations.filter(loc =>
    loc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    loc.loc_code.toLowerCase().includes(searchQuery.toLowerCase())
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
        { label: '场景管理' },
      ]}
    >
      <div className="h-[calc(100vh-4rem)] flex">
        {/* 左侧：场景列表 */}
        <div className="w-80 border-r border-border bg-card flex flex-col">
          <div className="p-4 border-b border-border space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">场景列表</h2>
              <Badge variant="outline">{locations.length}</Badge>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input placeholder="搜索场景..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-9" />
            </div>
            <Button className="w-full" onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />创建场景
            </Button>
            <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
              <DialogContent>
                <DialogHeader><DialogTitle>创建新场景</DialogTitle></DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">场景名称 *</label>
                    <Input placeholder="输入场景名称" value={newLocName} onChange={(e) => setNewLocName(e.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">场景类型</label>
                    <Select value={newLocType} onValueChange={setNewLocType}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {Object.entries(locationTypeLabels).map(([value, label]) => (
                          <SelectItem key={value} value={value}>{label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>取消</Button>
                  <Button onClick={handleCreateLocation} disabled={!newLocName.trim() || creating}>{creating && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}创建</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
          <ScrollArea className="flex-1">
            <div className="p-3 space-y-2">
              {filteredLocations.map(loc => {
                const Icon = locationTypeIcons[loc.location_type] || Building;
                return (
                  <div key={loc.id} className="group relative">
                    <div onClick={() => setSelectedLocId(loc.id)} className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all ${selectedLocId === loc.id ? 'bg-primary/10 border border-primary/30' : 'hover:bg-secondary/50 border border-transparent'}`}>
                      {loc.pic_url ? (
                        <img src={loc.pic_url} alt={loc.name} className="h-10 w-10 rounded-lg object-cover shrink-0" />
                      ) : (
                        <div className="h-10 w-10 shrink-0 rounded-lg bg-secondary flex items-center justify-center"><Icon className="h-5 w-5 text-muted-foreground" /></div>
                      )}
                      <div className="flex-1 min-w-0">
                        <span className="font-medium text-sm truncate block">{loc.name}</span>
                        <p className="text-xs text-muted-foreground truncate">{locationTypeLabels[loc.location_type] || loc.loc_code}</p>
                      </div>
                      <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100 shrink-0 text-muted-foreground hover:text-destructive" onClick={(e) => { e.stopPropagation(); handleDeleteLocation(loc.id); }}><Trash2 className="h-4 w-4" /></Button>
                    </div>
                  </div>
                );
              })}
              {filteredLocations.length === 0 && <div className="py-8 text-center text-muted-foreground"><MapPin className="h-12 w-12 mx-auto mb-3 opacity-50" /><p>没有找到场景</p></div>}
            </div>
          </ScrollArea>
        </div>

        {/* 右侧：场景详情 */}
        <div className="flex-1 bg-background overflow-y-auto">
          {locDetail ? (
            <div className="p-6 space-y-6">
              {/* 场景头部 */}
              <div className="flex flex-col gap-4 rounded-2xl border bg-card p-6 lg:flex-row lg:items-start lg:justify-between">
                <div className="flex items-start gap-4">
                  <div className="relative h-16 w-16 rounded-xl bg-secondary shrink-0 overflow-hidden">
                    {locDetail.pic_url ? (
                      <img src={locDetail.pic_url} alt={locDetail.name} className="h-full w-full object-cover" />
                    ) : (
                      <div className="h-full w-full flex items-center justify-center">
                        {(() => { const Icon = locationTypeIcons[locDetail.location_type] || Building; return <Icon className="h-8 w-8 text-muted-foreground" />; })()}
                      </div>
                    )}
                    <input
                      ref={picFileInputRef}
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) handleUploadPic(file);
                        e.target.value = '';
                      }}
                    />
                    <button
                      type="button"
                      className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 hover:opacity-100 transition-opacity rounded-xl"
                      onClick={() => picFileInputRef.current?.click()}
                      disabled={uploadingPic}
                    >
                      {uploadingPic ? <Loader2 className="h-5 w-5 text-white animate-spin" /> : <Camera className="h-5 w-5 text-white" />}
                    </button>
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h1 className="text-2xl font-bold text-foreground">{locDetail.name}</h1>
                      <Badge variant="outline">{locDetail.loc_code}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {[locationTypeLabels[locDetail.location_type], locDetail.domain].filter(Boolean).join(' · ') || '暂无信息'}
                    </p>
                  </div>
                </div>
                {locDetail.pic_url && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-muted-foreground shrink-0"
                    disabled={deletingPic}
                    onClick={handleDeletePic}
                  >
                    {deletingPic ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Trash2 className="h-4 w-4 mr-1" />}
                    删除封面
                  </Button>
                )}
              </div>

              {/* 上传图片到素材库 */}
              <Card>
                <CardHeader><CardTitle>上传场景图片</CardTitle></CardHeader>
                <CardContent className="space-y-4">
                  <FileDropZone
                    title="拖拽或点击上传"
                    description="支持 JPG/PNG/WEBP，最多 5 张，单张不超过 10MB"
                    onSelect={(files) => {
                      resetPreviewFiles(uploadFiles);
                      const next = createPendingImageFiles(files, 5);
                      setUploadFiles(next);
                      uploadFilesRef.current = next;
                    }}
                    disabled={uploadingSceneImage}
                  />
                  {uploadFiles.length > 0 && (
                    <div className="space-y-3">
                      <div className="flex flex-wrap gap-3">
                        {uploadFiles.map((item) => (
                          <div key={item.id} className="relative group">
                            <img src={item.preview} alt="" className="h-24 w-24 object-cover rounded-lg border" />
                            <button type="button" className="absolute -top-2 -right-2 h-5 w-5 rounded-full bg-destructive text-destructive-foreground flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity" onClick={() => {
                              setUploadFiles((prev) => { const next = prev.filter((f) => f.id !== item.id); URL.revokeObjectURL(item.preview); return next; });
                            }}><X className="h-3 w-3" /></button>
                          </div>
                        ))}
                      </div>
                      <div className="flex gap-2">
                        <Button onClick={handleUploadFiles} disabled={uploadingSceneImage}>
                          {uploadingSceneImage ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
                          上传到素材库
                        </Button>
                        <Button variant="outline" onClick={() => { resetPreviewFiles(uploadFiles); setUploadFiles([]); }} disabled={uploadingSceneImage}>清除</Button>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* 场景图片库 */}
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>场景图片</CardTitle>
                  <span className="text-sm text-muted-foreground">{locationAssets.length} 张</span>
                </CardHeader>
                <CardContent>
                  {locationAssets.length === 0 ? (
                    <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
                      暂无场景图片，可通过上方上传
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                      {locationAssets.map((asset) => (
                        <div key={asset.id} className="group relative aspect-[4/3] bg-secondary rounded-lg overflow-hidden border">
                          <img src={asset.file_url} alt="" className="w-full h-full object-cover" />
                          <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                            <Button size="icon" variant="secondary" onClick={() => setPreviewUrl(asset.file_url)}><Eye className="h-4 w-4" /></Button>
                          </div>
                          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-2">
                            <Badge variant="secondary" className="text-[10px]">{asset.source === 'generated' ? 'AI生成' : '上传'}</Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          ) : (
            <EmptyState title="选择一个场景" description="从左侧列表选择场景查看详情" />
          )}
        </div>
      </div>

      <FullscreenPreview url={previewUrl} open={!!previewUrl} onOpenChange={() => setPreviewUrl(null)} />
    </AppLayout>
  );
}
