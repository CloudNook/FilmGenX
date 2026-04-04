'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  assetsApi,
  type AssetResponse,
} from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Image as ImageIcon,
  Video,
  Music,
  FileImage,
  Loader2,
  Trash2,
  Download,
  ExternalLink,
  MoreVertical,
  Clock,
  Check,
  History,
  Plus,
} from 'lucide-react';

interface ShotAssetsPanelProps {
  projectId: number;
  shotId: number;
  shotCode?: string;
}

const assetTypeLabels: Record<string, string> = {
  image: '图片',
  video: '视频',
  audio: '音频',
  reference: '参考图',
};

const assetTypeIcons: Record<string, typeof ImageIcon> = {
  image: ImageIcon,
  video: Video,
  audio: Music,
  reference: FileImage,
};

const sourceLabels: Record<string, string> = {
  generated: 'AI生成',
  uploaded: '手动上传',
};

export function ShotAssetsPanel({ projectId, shotId, shotCode }: ShotAssetsPanelProps) {
  const [assets, setAssets] = useState<AssetResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [selectedAsset, setSelectedAsset] = useState<AssetResponse | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Group assets by type
  const groupedAssets = assets.reduce((acc, asset) => {
    const type = asset.asset_type;
    if (!acc[type]) acc[type] = [];
    acc[type].push(asset);
    return acc;
  }, {} as Record<string, AssetResponse[]>);

  // Load assets
  const loadAssets = useCallback(async () => {
    if (!projectId || !shotId) return;
    setLoading(true);
    try {
      const [assetsResult, statsResult] = await Promise.all([
        assetsApi.list(projectId, 1, 100, { shotId, isCurrent: false }).then(r => r.items),
        assetsApi.stats(projectId).catch(() => ({})),
      ]);
      setAssets(assetsResult);
      // Calculate shot-specific stats
      const shotStats: Record<string, number> = {};
      assetsResult.forEach(a => {
        shotStats[a.asset_type] = (shotStats[a.asset_type] || 0) + 1;
      });
      setStats(shotStats);
    } catch (err) {
      console.error('Failed to load shot assets:', err);
    } finally {
      setLoading(false);
    }
  }, [projectId, shotId]);

  useEffect(() => {
    loadAssets();
  }, [loadAssets]);

  const handleDeleteAsset = async (assetId: number) => {
    setDeleting(true);
    try {
      await assetsApi.delete(projectId, assetId);
      setAssets(prev => prev.filter(a => a.id !== assetId));
      setIsDetailOpen(false);
      setSelectedAsset(null);
    } catch (err) {
      console.error('Failed to delete asset:', err);
    } finally {
      setDeleting(false);
    }
  };

  const getAssetIcon = (type: string) => assetTypeIcons[type] || FileImage;

  if (loading) {
    return (
      <Card className="bg-card border-border">
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card className="bg-card border-border">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <ImageIcon className="h-5 w-5 text-primary" />
              镜头素材
            </CardTitle>
            <div className="flex items-center gap-2">
              {Object.entries(stats).map(([type, count]) => {
                const Icon = getAssetIcon(type);
                return (
                  <Badge key={type} variant="outline" className="border-border gap-1">
                    <Icon className="h-3 w-3" />
                    {count}
                  </Badge>
                );
              })}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {assets.length === 0 ? (
            <div className="text-center py-8">
              <ImageIcon className="h-10 w-10 mx-auto text-muted-foreground mb-3 opacity-50" />
              <p className="text-sm text-muted-foreground">暂无素材</p>
              <p className="text-xs text-muted-foreground mt-1">
                通过 AI 生成或手动上传添加素材
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {Object.entries(groupedAssets).map(([type, typeAssets]) => {
                const Icon = getAssetIcon(type);
                return (
                  <div key={type}>
                    <div className="flex items-center gap-2 mb-2">
                      <Icon className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium text-foreground">
                        {assetTypeLabels[type] || type}
                      </span>
                      <Badge variant="outline" className="text-xs border-border">
                        {typeAssets.length}
                      </Badge>
                    </div>

                    {type === 'image' || type === 'reference' ? (
                      <div className="grid grid-cols-4 gap-2">
                        {typeAssets.map((asset) => (
                          <div
                            key={asset.id}
                            className="group relative aspect-square rounded-lg overflow-hidden bg-secondary/50 cursor-pointer hover:ring-2 ring-primary/50 transition-all"
                            onClick={() => {
                              setSelectedAsset(asset);
                              setIsDetailOpen(true);
                            }}
                          >
                            <img
                              src={asset.file_url}
                              alt={asset.asset_code}
                              className="w-full h-full object-cover"
                            />
                            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                              <p className="text-xs text-white truncate">{asset.asset_code}</p>
                            </div>
                            {asset.is_current && (
                              <div className="absolute top-1 right-1">
                                <Badge className="bg-success/90 text-white text-xs px-1.5 py-0.5">
                                  <Check className="h-3 w-3 mr-1" />
                                  当前
                                </Badge>
                              </div>
                            )}
                            {asset.version > 1 && (
                              <div className="absolute top-1 left-1">
                                <Badge variant="outline" className="bg-black/50 text-white text-xs border-0 px-1.5 py-0.5">
                                  v{asset.version}
                                </Badge>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {typeAssets.map((asset) => (
                          <div
                            key={asset.id}
                            className="flex items-center gap-3 p-2 rounded-lg bg-secondary/30 hover:bg-secondary/50 cursor-pointer transition-colors"
                            onClick={() => {
                              setSelectedAsset(asset);
                              setIsDetailOpen(true);
                            }}
                          >
                            <div className="h-10 w-10 rounded bg-secondary flex items-center justify-center shrink-0">
                              <Icon className="h-5 w-5 text-muted-foreground" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-foreground truncate">
                                {asset.asset_code}
                              </p>
                              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <span>{sourceLabels[asset.source] || asset.source}</span>
                                {asset.duration_sec && (
                                  <span>· {asset.duration_sec.toFixed(1)}s</span>
                                )}
                                {asset.version > 1 && <span>· v{asset.version}</span>}
                              </div>
                            </div>
                            {asset.is_current && (
                              <Badge className="bg-success/20 text-success text-xs">
                                当前版本
                              </Badge>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Asset Detail Dialog */}
      <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedAsset && (() => {
                const Icon = getAssetIcon(selectedAsset.asset_type);
                return <Icon className="h-5 w-5 text-primary" />;
              })()}
              素材详情
            </DialogTitle>
            <DialogDescription>
              {selectedAsset?.asset_code}
            </DialogDescription>
          </DialogHeader>

          {selectedAsset && (
            <div className="space-y-4">
              {/* Preview */}
              {(selectedAsset.asset_type === 'image' || selectedAsset.asset_type === 'reference') && (
                <div className="aspect-video rounded-lg overflow-hidden bg-secondary/50">
                  <img
                    src={selectedAsset.file_url}
                    alt={selectedAsset.asset_code}
                    className="w-full h-full object-contain"
                  />
                </div>
              )}

              {selectedAsset.asset_type === 'video' && (
                <video
                  src={selectedAsset.file_url}
                  controls
                  className="w-full rounded-lg bg-secondary/50"
                />
              )}

              {selectedAsset.asset_type === 'audio' && (
                <audio src={selectedAsset.file_url} controls className="w-full" />
              )}

              {/* Info Grid */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">类型</span>
                  <p className="font-medium text-foreground">
                    {assetTypeLabels[selectedAsset.asset_type] || selectedAsset.asset_type}
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground">来源</span>
                  <p className="font-medium text-foreground">
                    {sourceLabels[selectedAsset.source] || selectedAsset.source}
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground">版本</span>
                  <p className="font-medium text-foreground">v{selectedAsset.version}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">格式</span>
                  <p className="font-medium text-foreground">
                    {selectedAsset.file_format || '-'}
                  </p>
                </div>
                {selectedAsset.width && selectedAsset.height && (
                  <div>
                    <span className="text-muted-foreground">尺寸</span>
                    <p className="font-medium text-foreground">
                      {selectedAsset.width} × {selectedAsset.height}
                    </p>
                  </div>
                )}
                {selectedAsset.duration_sec && (
                  <div>
                    <span className="text-muted-foreground">时长</span>
                    <p className="font-medium text-foreground">
                      {selectedAsset.duration_sec.toFixed(2)}s
                    </p>
                  </div>
                )}
                {selectedAsset.file_size_bytes && (
                  <div>
                    <span className="text-muted-foreground">大小</span>
                    <p className="font-medium text-foreground">
                      {(selectedAsset.file_size_bytes / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground">创建时间</span>
                  <p className="font-medium text-foreground">
                    {new Date(selectedAsset.created_at).toLocaleString('zh-CN')}
                  </p>
                </div>
              </div>

              {/* Tags */}
              {selectedAsset.tags.length > 0 && (
                <div>
                  <span className="text-sm text-muted-foreground">标签</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {selectedAsset.tags.map((tag, i) => (
                      <Badge key={i} variant="outline" className="text-xs border-border">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Description */}
              {selectedAsset.description && (
                <div>
                  <span className="text-sm text-muted-foreground">描述</span>
                  <p className="text-sm text-foreground mt-1">{selectedAsset.description}</p>
                </div>
              )}
            </div>
          )}

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="destructive"
              onClick={() => selectedAsset && handleDeleteAsset(selectedAsset.id)}
              disabled={deleting}
            >
              {deleting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Trash2 className="h-4 w-4 mr-2" />}
              删除
            </Button>
            <Button variant="outline" asChild>
              <a href={selectedAsset?.file_url} download target="_blank" rel="noopener noreferrer">
                <Download className="h-4 w-4 mr-2" />
                下载
              </a>
            </Button>
            <Button variant="outline" asChild>
              <a href={selectedAsset?.file_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4 mr-2" />
                新窗口打开
              </a>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
