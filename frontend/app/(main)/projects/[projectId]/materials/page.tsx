'use client';

import { use, useEffect, useState } from 'react';
import Link from 'next/link';
import { AppLayout } from '@/components/layout';
import {
  projectsApi,
  charactersApi,
  locationsApi,
  assetsApi,
  type ProjectResponse,
  type CharacterResponse,
  type CharacterDetailResponse,
  type LocationResponse,
  type LocationDetailResponse,
  type AssetResponse,
} from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  Users,
  MapPin,
  Image,
  Video,
  Music,
  FileImage,
  ArrowRight,
  Loader2,
  Plus,
  Sparkles,
  Layers,
} from 'lucide-react';
import { ImageUploadDialog } from '@/components/assets/ImageUploadDialog';

export default function MaterialsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const projectIdNum = Number(projectId);

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Stats
  const [characterCount, setCharacterCount] = useState(0);
  const [characterVersionCount, setCharacterVersionCount] = useState(0);
  const [characterImageCount, setCharacterImageCount] = useState(0);
  const [locationCount, setLocationCount] = useState(0);
  const [locationVersionCount, setLocationVersionCount] = useState(0);
  const [locationImageCount, setLocationImageCount] = useState(0);
  const [assetStats, setAssetStats] = useState<Record<string, number>>({});

  // Preview lists
  const [recentCharacters, setRecentCharacters] = useState<CharacterResponse[]>([]);
  const [recentLocations, setRecentLocations] = useState<LocationResponse[]>([]);
  const [recentAssets, setRecentAssets] = useState<AssetResponse[]>([]);

  // Upload dialog
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);

  useEffect(() => {
    if (isNaN(projectIdNum)) return;

    async function loadData() {
      const [p, charsRes, locsRes, stats, assets] = await Promise.all([
        projectsApi.get(projectIdNum).catch(() => null),
        charactersApi.list(projectIdNum, 1, 100).catch(() => ({ items: [], total: 0 })),
        locationsApi.list(projectIdNum, 1, 100).catch(() => ({ items: [], total: 0 })),
        assetsApi.stats(projectIdNum).catch(() => ({})),
        assetsApi.list(projectIdNum, 1, 6).then(r => r.items).catch(() => []),
      ]);

      setProject(p);
      setCharacterCount(charsRes.total);
      setLocationCount(locsRes.total);
      setAssetStats(stats);
      setRecentCharacters(charsRes.items.slice(0, 5));
      setRecentLocations(locsRes.items.slice(0, 5));
      setRecentAssets(assets);

      // 统计角色版本和图片数量
      let charVersions = 0;
      let charImages = 0;
      for (const char of charsRes.items) {
        try {
          const detail = await charactersApi.get(projectIdNum, char.id);
          charVersions += detail.versions?.length || 0;
          for (const version of detail.versions || []) {
            if (version.three_view_url) charImages++;
            charImages += version.reference_image_urls?.length || 0;
          }
        } catch {
          // ignore
        }
      }
      setCharacterVersionCount(charVersions);
      setCharacterImageCount(charImages);

      // 统计场景版本和图片数量
      let locVersions = 0;
      let locImages = 0;
      for (const loc of locsRes.items) {
        try {
          const detail = await locationsApi.get(projectIdNum, loc.id);
          locImages += detail.reference_image_urls?.length || 0;
          locVersions += detail.versions?.length || 0;
          for (const version of detail.versions || []) {
            locImages += version.reference_image_urls?.length || 0;
          }
        } catch {
          // ignore
        }
      }
      setLocationVersionCount(locVersions);
      setLocationImageCount(locImages);

      setLoading(false);
    }

    loadData();
  }, [projectIdNum]);

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

  const materialCategories = [
    {
      icon: Users,
      title: '角色管理',
      description: '管理项目中的角色档案、版本和特征设定',
      href: `/projects/${projectId}/materials/characters`,
      count: characterCount,
      versionCount: characterVersionCount,
      imageCount: characterImageCount,
      color: 'text-primary',
      bgColor: 'bg-primary/10',
    },
    {
      icon: MapPin,
      title: '场景管理',
      description: '管理项目中的场景地点、环境设定和变体',
      href: `/projects/${projectId}/materials/locations`,
      count: locationCount,
      versionCount: locationVersionCount,
      imageCount: locationImageCount,
      color: 'text-info',
      bgColor: 'bg-info/10',
    },
    {
      icon: Image,
      title: '素材库',
      description: '管理所有图片、视频、音频素材',
      href: `/projects/${projectId}/materials/assets`,
      count: Object.values(assetStats).reduce((a, b) => a + b, 0),
      color: 'text-success',
      bgColor: 'bg-success/10',
    },
  ];

  const getAssetIcon = (type: string) => {
    switch (type) {
      case 'image': return Image;
      case 'video': return Video;
      case 'audio': return Music;
      default: return FileImage;
    }
  };

  const getAssetTypeLabel = (type: string) => {
    switch (type) {
      case 'image': return '图片';
      case 'video': return '视频';
      case 'audio': return '音频';
      case 'reference': return '参考图';
      default: return type;
    }
  };

  return (
    <AppLayout
      projectId={projectId}
      breadcrumbs={[
        { label: '项目', href: '/projects' },
        { label: project.name, href: `/projects/${projectId}` },
        { label: '素材库' },
      ]}
    >
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">素材库</h1>
            <p className="text-muted-foreground mt-1">
              管理项目中的角色、场景和素材资源
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setUploadDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              上传素材
            </Button>
            <Button onClick={() => setUploadDialogOpen(true)}>
              <Sparkles className="h-4 w-4 mr-2" />
              AI 生成
            </Button>
          </div>
        </div>

        {/* Category Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {materialCategories.map((category) => (
            <Link key={category.title} href={category.href}>
              <Card className="bg-card border-border hover:border-primary/50 transition-all cursor-pointer h-full">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className={`h-12 w-12 rounded-lg ${category.bgColor} flex items-center justify-center`}>
                      <category.icon className={`h-6 w-6 ${category.color}`} />
                    </div>
                    <Badge variant="outline" className="border-border">
                      {category.count} 项
                    </Badge>
                  </div>
                  <CardTitle className="text-lg mt-3">{category.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{category.description}</p>
                  {'versionCount' in category && (
                    <div className="flex gap-4 mt-3 text-sm">
                      <div className="flex items-center gap-1 text-muted-foreground">
                        <Layers className="h-3.5 w-3.5" />
                        <span>{category.versionCount} 版本</span>
                      </div>
                      <div className="flex items-center gap-1 text-muted-foreground">
                        <Image className="h-3.5 w-3.5" />
                        <span>{category.imageCount} 图片</span>
                      </div>
                    </div>
                  )}
                  <div className="flex items-center text-primary text-sm mt-4">
                    <span>进入管理</span>
                    <ArrowRight className="h-4 w-4 ml-1" />
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        {/* Quick Stats - 与上方卡片对齐 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* 角色统计 */}
          <Card className="bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/10">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2 text-primary">
                <Users className="h-5 w-5" />
                角色统计
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <p className="text-3xl font-bold text-foreground">{characterCount}</p>
                  <p className="text-xs text-muted-foreground mt-1">角色</p>
                </div>
                <div className="text-center border-x border-primary/20">
                  <p className="text-3xl font-bold text-foreground">{characterVersionCount}</p>
                  <p className="text-xs text-muted-foreground mt-1">版本</p>
                </div>
                <div className="text-center">
                  <p className="text-3xl font-bold text-foreground">{characterImageCount}</p>
                  <p className="text-xs text-muted-foreground mt-1">图片</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 场景统计 */}
          <Card className="bg-gradient-to-br from-info/10 to-info/5 border border-info/10">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2 text-info">
                <MapPin className="h-5 w-5" />
                场景统计
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <p className="text-3xl font-bold text-foreground">{locationCount}</p>
                  <p className="text-xs text-muted-foreground mt-1">场景</p>
                </div>
                <div className="text-center border-x border-info/20">
                  <p className="text-3xl font-bold text-foreground">{locationVersionCount}</p>
                  <p className="text-xs text-muted-foreground mt-1">版本</p>
                </div>
                <div className="text-center">
                  <p className="text-3xl font-bold text-foreground">{locationImageCount}</p>
                  <p className="text-xs text-muted-foreground mt-1">图片</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 素材库统计 */}
          <Card className="bg-gradient-to-br from-success/10 to-success/5 border border-success/10">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2 text-success">
                <Image className="h-5 w-5" />
                素材统计
              </CardTitle>
            </CardHeader>
            <CardContent>
              {Object.entries(assetStats).length > 0 ? (
                <div className="grid grid-cols-3 gap-4">
                  {Object.entries(assetStats).slice(0, 3).map(([type, count]) => (
                    <div key={type} className="text-center">
                      <p className="text-3xl font-bold text-foreground">{count}</p>
                      <p className="text-xs text-muted-foreground mt-1">{getAssetTypeLabel(type)}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 text-muted-foreground text-sm">暂无素材</div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Recent Items */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Characters */}
          <Card className="bg-card border-border">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-lg">最近角色</CardTitle>
              <Link href={`/projects/${projectId}/materials/characters`}>
                <Button variant="ghost" size="sm" className="text-primary">
                  查看全部
                  <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {recentCharacters.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground">
                  <Users className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">暂无角色</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {recentCharacters.slice(0, 5).map((char) => (
                    <Link
                      key={char.id}
                      href={`/projects/${projectId}/materials/characters`}
                      className="flex items-center gap-3 p-2 rounded-lg hover:bg-secondary/50 transition-colors"
                    >
                      <Avatar className="h-8 w-8">
                        <AvatarFallback className="text-xs bg-primary/20 text-primary">
                          {char.name.slice(0, 1)}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">{char.name}</p>
                        <p className="text-xs text-muted-foreground truncate">
                          {char.role_description || char.char_code}
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent Locations */}
          <Card className="bg-card border-border">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-lg">最近场景</CardTitle>
              <Link href={`/projects/${projectId}/materials/locations`}>
                <Button variant="ghost" size="sm" className="text-primary">
                  查看全部
                  <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {recentLocations.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground">
                  <MapPin className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">暂无场景</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {recentLocations.slice(0, 5).map((loc) => (
                    <Link
                      key={loc.id}
                      href={`/projects/${projectId}/materials/locations`}
                      className="flex items-center gap-3 p-2 rounded-lg hover:bg-secondary/50 transition-colors"
                    >
                      <div className="h-8 w-8 rounded-lg bg-info/10 flex items-center justify-center">
                        <MapPin className="h-4 w-4 text-info" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">{loc.name}</p>
                        <p className="text-xs text-muted-foreground truncate">
                          {loc.domain || loc.location_type}
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent Assets */}
          <Card className="bg-card border-border">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-lg">最近素材</CardTitle>
              <Link href={`/projects/${projectId}/materials/assets`}>
                <Button variant="ghost" size="sm" className="text-primary">
                  查看全部
                  <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {recentAssets.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground">
                  <Image className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">暂无素材</p>
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-2">
                  {recentAssets.slice(0, 6).map((asset) => (
                    <Link
                      key={asset.id}
                      href={`/projects/${projectId}/materials/assets`}
                      className="group relative aspect-square rounded-lg overflow-hidden bg-secondary/50 hover:ring-2 ring-primary/50 transition-all"
                    >
                      {asset.asset_type === 'image' ? (
                        <img
                          src={asset.file_url}
                          alt={asset.asset_code}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          {(() => {
                            const Icon = getAssetIcon(asset.asset_type);
                            return <Icon className="h-5 w-5 text-muted-foreground" />;
                          })()}
                        </div>
                      )}
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Upload Dialog */}
        <ImageUploadDialog
          open={uploadDialogOpen}
          onOpenChange={setUploadDialogOpen}
          projectId={projectIdNum}
          onAssetCreated={() => {
            // Refresh data
            assetsApi.list(projectIdNum, 1, 6).then(r => setRecentAssets(r.items));
            assetsApi.stats(projectIdNum).then(setAssetStats);
          }}
        />
      </div>
    </AppLayout>
  );
}
