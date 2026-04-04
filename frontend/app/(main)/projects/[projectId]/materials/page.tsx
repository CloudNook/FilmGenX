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
  type LocationResponse,
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
} from 'lucide-react';

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
  const [locationCount, setLocationCount] = useState(0);
  const [assetStats, setAssetStats] = useState<Record<string, number>>({});

  // Preview lists
  const [recentCharacters, setRecentCharacters] = useState<CharacterResponse[]>([]);
  const [recentLocations, setRecentLocations] = useState<LocationResponse[]>([]);
  const [recentAssets, setRecentAssets] = useState<AssetResponse[]>([]);

  useEffect(() => {
    if (isNaN(projectIdNum)) return;

    Promise.all([
      projectsApi.get(projectIdNum).catch(() => null),
      charactersApi.list(projectIdNum, 1, 5).then(r => { setCharacterCount(r.total); return r.items; }).catch(() => []),
      locationsApi.list(projectIdNum, 1, 5).then(r => { setLocationCount(r.total); return r.items; }).catch(() => []),
      assetsApi.stats(projectIdNum).catch(() => ({})),
      assetsApi.list(projectIdNum, 1, 6).then(r => r.items).catch(() => []),
    ]).then(([p, chars, locs, stats, assets]) => {
      setProject(p);
      setRecentCharacters(chars);
      setRecentLocations(locs);
      setAssetStats(stats);
      setRecentAssets(assets);
      setLoading(false);
    });
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
      href: `/projects/${projectId}/characters`,
      count: characterCount,
      color: 'text-primary',
      bgColor: 'bg-primary/10',
    },
    {
      icon: MapPin,
      title: '场景管理',
      description: '管理项目中的场景地点、环境设定和变体',
      href: `/projects/${projectId}/locations`,
      count: locationCount,
      color: 'text-info',
      bgColor: 'bg-info/10',
    },
    {
      icon: Image,
      title: '素材库',
      description: '管理所有图片、视频、音频素材',
      href: `/projects/${projectId}/assets`,
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
        <div>
          <h1 className="text-2xl font-bold text-foreground">素材库</h1>
          <p className="text-muted-foreground mt-1">
            管理项目中的角色、场景和素材资源
          </p>
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
                  <div className="flex items-center text-primary text-sm mt-4">
                    <span>进入管理</span>
                    <ArrowRight className="h-4 w-4 ml-1" />
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        {/* Quick Stats */}
        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="text-lg">素材统计</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(assetStats).length > 0 ? (
                Object.entries(assetStats).map(([type, count]) => {
                  const Icon = getAssetIcon(type);
                  return (
                    <div key={type} className="flex items-center gap-3 p-3 rounded-lg bg-secondary/50">
                      <Icon className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="text-sm font-medium text-foreground">{getAssetTypeLabel(type)}</p>
                        <p className="text-lg font-bold text-foreground">{count}</p>
                      </div>
                    </div>
                  );
                })
              ) : (
                <p className="text-muted-foreground col-span-4 text-center py-4">
                  暂无素材数据
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Recent Items */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Characters */}
          <Card className="bg-card border-border">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-base">最近角色</CardTitle>
              <Link href={`/projects/${projectId}/characters`}>
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
                <div className="space-y-3">
                  {recentCharacters.map((char) => (
                    <Link
                      key={char.id}
                      href={`/projects/${projectId}/characters`}
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
              <CardTitle className="text-base">最近场景</CardTitle>
              <Link href={`/projects/${projectId}/locations`}>
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
                <div className="space-y-3">
                  {recentLocations.map((loc) => (
                    <Link
                      key={loc.id}
                      href={`/projects/${projectId}/locations`}
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
              <CardTitle className="text-base">最近素材</CardTitle>
              <Link href={`/projects/${projectId}/assets`}>
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
                <div className="grid grid-cols-2 gap-2">
                  {recentAssets.map((asset) => (
                    <Link
                      key={asset.id}
                      href={`/projects/${projectId}/assets`}
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
                            return <Icon className="h-8 w-8 text-muted-foreground" />;
                          })()}
                        </div>
                      )}
                      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-2">
                        <p className="text-xs text-white truncate">{asset.asset_code}</p>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </AppLayout>
  );
}
