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
  Download,
  ExternalLink,
  Filter,
} from 'lucide-react';
import { toast } from 'sonner';
import { ImageUploadDialog } from '@/components/assets/ImageUploadDialog';

type AssetType = 'image' | 'video' | 'audio' | 'reference';
type ViewMode = 'grid' | 'list';

const ASSET_TYPE_OPTIONS = [
  { value: 'all', label: '全部类型' },
  { value: 'image', label: '图片' },
  { value: 'video', label: '视频' },
  { value: 'audio', label: '音频' },
  { value: 'reference', label: '参考图' },
];

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

        {/* Filters */}
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

          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-[140px]">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ASSET_TYPE_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

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
                    {asset.asset_type === 'image' ? (
                      <img
                        src={asset.file_url}
                        alt={asset.asset_code}
                        className="w-full h-full object-cover transition-transform group-hover:scale-105"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Icon className="h-12 w-12 text-muted-foreground" />
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
                              {asset.asset_type === 'image' ? (
                                <img
                                  src={asset.file_url}
                                  alt=""
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
                {selectedAsset.asset_type === 'image' && (
                  <div className="aspect-video relative bg-secondary/30 rounded-lg overflow-hidden">
                    <img
                      src={selectedAsset.file_url}
                      alt={selectedAsset.asset_code}
                      className="w-full h-full object-contain"
                    />
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
                    查看原图
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
