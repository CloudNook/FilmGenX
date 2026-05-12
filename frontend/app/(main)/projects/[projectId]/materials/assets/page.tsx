'use client';

import { use, useEffect, useState, useCallback } from 'react';
import { AppLayout } from '@/components/layout';
import {
  projectsApi,
  assetsApi,
  type ProjectResponse,
  type AssetResponse,
} from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Image as ImageIcon,
  Video,
  Music,
  FileImage,
  Upload,
  Sparkles,
  Search,
  Grid3X3,
  List,
  Loader2,
  Trash2,
  ExternalLink,
} from 'lucide-react';
import { toast } from 'sonner';
import { ImageUploadDialog } from '@/components/assets/ImageUploadDialog';

type ViewMode = 'grid' | 'list';

// 顶部 Tab 顺序：全部在第一位，其余按"图 → 视频 → 音频 → 参考图"语义顺序。
// value 跟 Asset.asset_type 列对齐，filter 直接 ===。
const ASSET_TYPE_TABS = [
  { value: 'all', label: '全部' },
  { value: 'image', label: '图片' },
  { value: 'video', label: '视频' },
  { value: 'audio', label: '音频' },
  { value: 'reference', label: '参考图' },
] as const;

const SOURCE_OPTIONS = [
  { value: 'all', label: '全部来源' },
  { value: 'uploaded', label: '本地上传' },
  { value: 'generated', label: 'AI 生成' },
];

export default function AssetsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const projectIdNum = Number(projectId);

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [assets, setAssets] = useState<AssetResponse[]>([]);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<AssetResponse | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);

  // Load project and assets
  const loadData = useCallback(async () => {
    if (isNaN(projectIdNum)) return;

    setLoading(true);
    try {
      const [p, assetsRes, statsRes] = await Promise.all([
        projectsApi.get(projectIdNum).catch(() => null),
        assetsApi.list(projectIdNum, 1, 100).catch(() => ({ items: [], total: 0 })),
        assetsApi.stats(projectIdNum).catch(() => ({})),
      ]);
      setProject(p);
      setAssets(assetsRes.items);
      setStats(statsRes);
    } finally {
      setLoading(false);
    }
  }, [projectIdNum]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Filter assets
  const filteredAssets = assets.filter((asset) => {
    const matchesType = typeFilter === 'all' || asset.asset_type === typeFilter;
    const matchesSource = sourceFilter === 'all' || asset.source === sourceFilter;
    const matchesSearch =
      !searchQuery ||
      asset.asset_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (asset.description?.toLowerCase().includes(searchQuery.toLowerCase()) ?? false);
    return matchesType && matchesSource && matchesSearch;
  });

  // Get icon for asset type
  const getAssetIcon = (type: string) => {
    switch (type) {
      case 'image':
        return ImageIcon;
      case 'video':
        return Video;
      case 'audio':
        return Music;
      default:
        return FileImage;
    }
  };

  // Get label for asset type
  const getAssetTypeLabel = (type: string) => {
    switch (type) {
      case 'image':
        return '图片';
      case 'video':
        return '视频';
      case 'audio':
        return '音频';
      case 'reference':
        return '参考图';
      default:
        return type;
    }
  };

  // Get badge color for source
  const getSourceBadgeVariant = (source: string) => {
    return source === 'generated' ? 'default' : 'secondary';
  };

  // Delete asset
  const handleDelete = async (assetId: number) => {
    if (!confirm('确定要删除这个素材吗？')) return;

    setDeleting(assetId);
    try {
      await assetsApi.delete(projectIdNum, assetId);
      toast.success('删除成功');
      setAssets((prev) => prev.filter((a) => a.id !== assetId));
      if (selectedAsset?.id === assetId) {
        setSelectedAsset(null);
      }
      // Refresh stats
      const newStats = await assetsApi.stats(projectIdNum);
      setStats(newStats);
    } catch (error) {
      toast.error('删除失败', {
        description: error instanceof Error ? error.message : '未知错误',
      });
    } finally {
      setDeleting(null);
    }
  };

  // Format file size
  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return '-';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  // mm:ss 风格的时长展示，给视频缩略图角标用
  const formatDuration = (sec: number | null): string | null => {
    if (sec == null || sec <= 0) return null;
    const total = Math.round(sec);
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <AppLayout projectId={projectId}>
        <div className="flex items-center justify-center h-full">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppLayout>
    );
  }

  if (!project) {
    return (
      <AppLayout projectId={projectId}>
        <div className="flex items-center justify-center h-full">
          <p className="text-muted-foreground">项目不存在</p>
        </div>
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
        { label: '素材管理' },
      ]}
    >
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">素材管理</h1>
            <p className="text-muted-foreground mt-1">
              管理项目中的图片、视频、音频素材
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setUploadDialogOpen(true)}>
              <Upload className="h-4 w-4 mr-2" />
              上传素材
            </Button>
            <Button onClick={() => setUploadDialogOpen(true)}>
              <Sparkles className="h-4 w-4 mr-2" />
              AI 生成
            </Button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(stats).length > 0 ? (
            Object.entries(stats).map(([type, count]) => {
              const Icon = getAssetIcon(type);
              return (
                <Card key={type} className="bg-card border-border">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                        <Icon className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">
                          {getAssetTypeLabel(type)}
                        </p>
                        <p className="text-xl font-bold text-foreground">{count}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })
          ) : (
            <Card className="col-span-4 bg-card border-border">
              <CardContent className="p-4 text-center text-muted-foreground">
                暂无素材数据
              </CardContent>
            </Card>
          )}
        </div>

        {/* 类型分类 Tabs。比起隐式下拉，tab 把分类做成第一视觉层级 +
            每个 tab 携带数量，让用户对素材构成一眼有数。
            'all' 的数量是 assets 全集；其余取 stats[type] || 0。 */}
        <Tabs value={typeFilter} onValueChange={setTypeFilter}>
          <TabsList>
            {ASSET_TYPE_TABS.map((tab) => {
              const count =
                tab.value === 'all'
                  ? assets.length
                  : stats[tab.value] || 0;
              return (
                <TabsTrigger key={tab.value} value={tab.value}>
                  {tab.label}
                  <Badge variant="outline" className="ml-2 text-[10px] font-normal">
                    {count}
                  </Badge>
                </TabsTrigger>
              );
            })}
          </TabsList>
        </Tabs>

        {/* 搜索 + 来源 + 视图切换 */}
        <div className="flex flex-wrap items-center gap-4">
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索素材..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>

          <Select value={sourceFilter} onValueChange={setSourceFilter}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SOURCE_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="flex items-center border rounded-lg p-1">
            <Button
              variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
              size="icon"
              onClick={() => setViewMode('grid')}
            >
              <Grid3X3 className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="icon"
              onClick={() => setViewMode('list')}
            >
              <List className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Assets Grid/List */}
        {filteredAssets.length === 0 ? (
          <Card className="bg-card border-border">
            <CardContent className="p-12 text-center">
              <ImageIcon className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
              <p className="text-muted-foreground mb-4">暂无素材</p>
              <Button onClick={() => setUploadDialogOpen(true)}>
                <Upload className="h-4 w-4 mr-2" />
                上传第一个素材
              </Button>
            </CardContent>
          </Card>
        ) : viewMode === 'grid' ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {filteredAssets.map((asset) => {
              const Icon = getAssetIcon(asset.asset_type);
              return (
                <Card
                  key={asset.id}
                  className="bg-card border-border overflow-hidden cursor-pointer hover:border-primary/50 hover:shadow-md transition-all group"
                  onClick={() => setSelectedAsset(asset)}
                >
                  <div className="aspect-[4/3] relative bg-secondary/30 overflow-hidden">
                    {asset.asset_type === 'image' || asset.asset_type === 'reference' ? (
                      <img
                        src={asset.file_url}
                        alt={asset.asset_code}
                        className="w-full h-full object-cover transition-transform group-hover:scale-105"
                      />
                    ) : asset.asset_type === 'video' ? (
                      // preload="metadata" 让浏览器只拉首帧作为缩略图，不下载整个视频。
                      // muted + playsInline 是为移动端默认行为友好；要播放走详情弹窗。
                      <video
                        src={asset.file_url}
                        preload="metadata"
                        muted
                        playsInline
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Icon className="h-12 w-12 text-muted-foreground" />
                      </div>
                    )}
                    {asset.asset_type === 'video' && (
                      // 视频缩略图右下角加一个时长 badge（如果有 duration_sec），
                      // 同时叠一个播放图标提示这是可播放素材。
                      <div className="absolute bottom-2 right-2 flex items-center gap-1 rounded bg-black/70 px-1.5 py-0.5 text-[10px] text-white">
                        <Video className="h-3 w-3" />
                        {formatDuration(asset.duration_sec) && (
                          <span>{formatDuration(asset.duration_sec)}</span>
                        )}
                      </div>
                    )}
                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                      <Button
                        variant="secondary"
                        size="icon"
                        onClick={(e) => {
                          e.stopPropagation();
                          window.open(asset.file_url, '_blank');
                        }}
                      >
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="destructive"
                        size="icon"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(asset.id);
                        }}
                        disabled={deleting === asset.id}
                      >
                        {deleting === asset.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                    <div className="absolute top-2 left-2">
                      <Badge variant={getSourceBadgeVariant(asset.source)} className="text-xs bg-black/60 border-0">
                        {asset.source === 'generated' ? 'AI' : '上传'}
                      </Badge>
                    </div>
                  </div>
                  <CardContent className="p-3">
                    <p className="text-sm font-medium text-foreground truncate" title={asset.asset_code}>
                      {asset.asset_code}
                    </p>
                    <div className="flex items-center justify-between mt-1">
                      <Badge variant="outline" className="text-xs">
                        {getAssetTypeLabel(asset.asset_type)}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatFileSize(asset.file_size_bytes)}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        ) : (
          <Card className="bg-card border-border">
            <CardContent className="p-0">
              <ScrollArea className="h-[600px]">
                <table className="w-full">
                  <thead className="sticky top-0 bg-card border-b">
                    <tr>
                      <th className="text-left p-3 text-sm font-medium text-muted-foreground">
                        预览
                      </th>
                      <th className="text-left p-3 text-sm font-medium text-muted-foreground">
                        名称
                      </th>
                      <th className="text-left p-3 text-sm font-medium text-muted-foreground">
                        类型
                      </th>
                      <th className="text-left p-3 text-sm font-medium text-muted-foreground">
                        来源
                      </th>
                      <th className="text-left p-3 text-sm font-medium text-muted-foreground">
                        大小
                      </th>
                      <th className="text-left p-3 text-sm font-medium text-muted-foreground">
                        创建时间
                      </th>
                      <th className="text-right p-3 text-sm font-medium text-muted-foreground">
                        操作
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAssets.map((asset) => {
                      const Icon = getAssetIcon(asset.asset_type);
                      return (
                        <tr
                          key={asset.id}
                          className="border-b hover:bg-secondary/30 cursor-pointer"
                          onClick={() => setSelectedAsset(asset)}
                        >
                          <td className="p-3">
                            <div className="h-12 w-12 rounded bg-secondary/50 flex items-center justify-center overflow-hidden">
                              {asset.asset_type === 'image' || asset.asset_type === 'reference' ? (
                                <img
                                  src={asset.file_url}
                                  alt=""
                                  className="w-full h-full object-cover"
                                />
                              ) : asset.asset_type === 'video' ? (
                                <video
                                  src={asset.file_url}
                                  preload="metadata"
                                  muted
                                  playsInline
                                  className="w-full h-full object-cover"
                                />
                              ) : (
                                <Icon className="h-6 w-6 text-muted-foreground" />
                              )}
                            </div>
                          </td>
                          <td className="p-3">
                            <p className="text-sm font-medium text-foreground">
                              {asset.asset_code}
                            </p>
                          </td>
                          <td className="p-3">
                            <Badge variant="outline">{getAssetTypeLabel(asset.asset_type)}</Badge>
                          </td>
                          <td className="p-3">
                            <Badge variant={getSourceBadgeVariant(asset.source)}>
                              {asset.source === 'generated' ? 'AI 生成' : '上传'}
                            </Badge>
                          </td>
                          <td className="p-3 text-sm text-muted-foreground">
                            {formatFileSize(asset.file_size_bytes)}
                          </td>
                          <td className="p-3 text-sm text-muted-foreground">
                            {new Date(asset.created_at).toLocaleDateString()}
                          </td>
                          <td className="p-3 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  window.open(asset.file_url, '_blank');
                                }}
                              >
                                <ExternalLink className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDelete(asset.id);
                                }}
                                disabled={deleting === asset.id}
                              >
                                {deleting === asset.id ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <Trash2 className="h-4 w-4" />
                                )}
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </ScrollArea>
            </CardContent>
          </Card>
        )}

        {/* Asset Detail Dialog */}
        {selectedAsset && (
          <div
            className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedAsset(null)}
          >
            <Card
              className="bg-card border-border max-w-2xl w-full max-h-[90vh] overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>素材详情</CardTitle>
                <Button variant="ghost" size="icon" onClick={() => setSelectedAsset(null)}>
                  ×
                </Button>
              </CardHeader>
              <CardContent className="space-y-4">
                {(selectedAsset.asset_type === 'image' ||
                  selectedAsset.asset_type === 'reference') && (
                  <div className="aspect-video relative bg-secondary/30 rounded-lg overflow-hidden">
                    <img
                      src={selectedAsset.file_url}
                      alt={selectedAsset.asset_code}
                      className="w-full h-full object-contain"
                    />
                  </div>
                )}
                {selectedAsset.asset_type === 'video' && (
                  // controls + 不 autoPlay：让用户主动播。aspect-video 容器配合
                  // object-contain 保留视频原始比例，不裁切。
                  <div className="aspect-video relative bg-black rounded-lg overflow-hidden">
                    <video
                      src={selectedAsset.file_url}
                      controls
                      preload="metadata"
                      playsInline
                      className="w-full h-full object-contain"
                    >
                      您的浏览器不支持视频播放。
                    </video>
                  </div>
                )}
                {selectedAsset.asset_type === 'audio' && (
                  <div className="rounded-lg bg-secondary/30 p-4">
                    <audio
                      src={selectedAsset.file_url}
                      controls
                      preload="metadata"
                      className="w-full"
                    >
                      您的浏览器不支持音频播放。
                    </audio>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">名称</p>
                    <p className="font-medium">{selectedAsset.asset_code}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">类型</p>
                    <p className="font-medium">{getAssetTypeLabel(selectedAsset.asset_type)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">来源</p>
                    <Badge variant={getSourceBadgeVariant(selectedAsset.source)}>
                      {selectedAsset.source === 'generated' ? 'AI 生成' : '上传'}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-muted-foreground">文件大小</p>
                    <p className="font-medium">{formatFileSize(selectedAsset.file_size_bytes)}</p>
                  </div>
                  {selectedAsset.width && selectedAsset.height && (
                    <div>
                      <p className="text-muted-foreground">尺寸</p>
                      <p className="font-medium">
                        {selectedAsset.width} × {selectedAsset.height}
                      </p>
                    </div>
                  )}
                  <div>
                    <p className="text-muted-foreground">创建时间</p>
                    <p className="font-medium">
                      {new Date(selectedAsset.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                {selectedAsset.tags.length > 0 && (
                  <div>
                    <p className="text-muted-foreground text-sm mb-2">标签</p>
                    <div className="flex flex-wrap gap-1">
                      {selectedAsset.tags.map((tag, i) => (
                        <Badge key={i} variant="outline">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                <div className="flex gap-2 pt-4">
                  <Button
                    variant="outline"
                    className="flex-1"
                    onClick={() => window.open(selectedAsset.file_url, '_blank')}
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    在新窗口打开
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={() => {
                      handleDelete(selectedAsset.id);
                      setSelectedAsset(null);
                    }}
                    disabled={deleting === selectedAsset.id}
                  >
                    {deleting === selectedAsset.id ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4 mr-2" />
                    )}
                    删除
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Upload Dialog */}
        <ImageUploadDialog
          open={uploadDialogOpen}
          onOpenChange={setUploadDialogOpen}
          projectId={projectIdNum}
          onAssetCreated={() => {
            loadData();
          }}
        />
      </div>
    </AppLayout>
  );
}
