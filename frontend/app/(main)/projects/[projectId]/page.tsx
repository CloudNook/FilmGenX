'use client';

import { useEffect, use, useState } from 'react';
import Link from 'next/link';
import { AppLayout } from '@/components/layout';
import { projectsApi, scenesApi, charactersApi, type ProjectResponse, type SceneResponse, type CharacterResponse } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  Clapperboard,
  Film,
  Users,
  MessageSquare,
  TrendingUp,
  Clock,
  CheckCircle2,
  AlertCircle,
  PlayCircle,
  ArrowRight,
  Sparkles,
  Video,
  Loader2,
  FolderOpen,
} from 'lucide-react';

const sceneStatusLabels: Record<string, string> = {
  draft: '草稿',
  scored: '已评分',
  in_production: '制作中',
  completed: '完成',
};

const sceneStatusColors: Record<string, string> = {
  draft: 'bg-muted text-muted-foreground',
  scored: 'bg-info/20 text-info',
  in_production: 'bg-primary/20 text-primary',
  completed: 'bg-success/20 text-success',
};

export default function ProjectWorkspacePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const projectIdNum = Number(projectId);

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [scenes, setScenes] = useState<SceneResponse[]>([]);
  const [characters, setCharacters] = useState<CharacterResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isNaN(projectIdNum)) return;

    Promise.all([
      projectsApi.get(projectIdNum).catch(() => null),
      scenesApi.list(projectIdNum, 1, 50).then(r => r.items).catch(() => []),
      charactersApi.list(projectIdNum, 1, 50).then(r => r.items).catch(() => []),
    ])
      .then(([p, s, c]) => {
        setProject(p);
        setScenes(s);
        setCharacters(c);
      })
      .finally(() => setLoading(false));
  }, [projectIdNum]);

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-full">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppLayout>
    );
  }

  if (!project) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-full">
          <p className="text-muted-foreground">项目不存在</p>
        </div>
      </AppLayout>
    );
  }

  const completedScenes = scenes.filter(s => s.status === 'completed').length;
  const inProgressScenes = scenes.filter(s => s.status === 'in_production').length;

  const quickActions = [
    { icon: MessageSquare, label: 'AI 对话', href: `/projects/${projectId}/chat`, color: 'text-primary' },
    { icon: FolderOpen, label: '素材库', href: `/projects/${projectId}/materials`, color: 'text-warning' },
    { icon: Clapperboard, label: '分集管理', href: `/projects/${projectId}/episodes`, color: 'text-info' },
    { icon: Video, label: '视频制作', href: `/projects/${projectId}/video`, color: 'text-success' },
  ];

  return (
    <AppLayout
      projectId={projectId}
      breadcrumbs={[
        { label: '项目', href: '/projects' },
        { label: project.name },
      ]}
    >
      <div className="p-6 space-y-6">
        {/* Project Header */}
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl font-bold text-foreground">{project.name}</h1>
            <p className="text-muted-foreground max-w-2xl">{project.description || project.novel_title}</p>
            <div className="flex items-center gap-2 pt-2">
              <Badge variant="outline" className="border-border">
                {project.novel_title}
              </Badge>
            </div>
          </div>
          <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
            <PlayCircle className="h-4 w-4 mr-2" />
            预览项目
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="bg-card border-border">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">状态</p>
                  <p className="text-2xl font-bold text-foreground">
                    {project.status === 'active' ? '制作中' : project.status === 'archived' ? '已归档' : '草稿'}
                  </p>
                </div>
                <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <TrendingUp className="h-6 w-6 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">片段/分集</p>
                  <p className="text-2xl font-bold text-foreground">
                    {completedScenes}/{scenes.length}
                  </p>
                </div>
                <div className="h-12 w-12 rounded-full bg-info/10 flex items-center justify-center">
                  <Clapperboard className="h-6 w-6 text-info" />
                </div>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                {inProgressScenes} 个制作中
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">总片段数</p>
                  <p className="text-2xl font-bold text-foreground">
                    {scenes.length}
                  </p>
                </div>
                <div className="h-12 w-12 rounded-full bg-warning/10 flex items-center justify-center">
                  <Film className="h-6 w-6 text-warning" />
                </div>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">已创建的片段</p>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">角色</p>
                  <p className="text-2xl font-bold text-foreground">{characters.length}</p>
                </div>
                <div className="h-12 w-12 rounded-full bg-success/10 flex items-center justify-center">
                  <Users className="h-6 w-6 text-success" />
                </div>
              </div>
              <div className="flex -space-x-2 mt-3">
                {characters.slice(0, 4).map((char) => (
                  <Avatar key={char.id} className="h-6 w-6 border-2 border-card">
                    <AvatarFallback className="text-xs bg-secondary text-secondary-foreground">
                      {char.name.slice(0, 1)}
                    </AvatarFallback>
                  </Avatar>
                ))}
                {characters.length > 4 && (
                  <div className="h-6 w-6 rounded-full bg-muted flex items-center justify-center text-xs text-muted-foreground border-2 border-card">
                    +{characters.length - 4}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">快速操作</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {quickActions.map((action) => (
                <Link key={action.label} href={action.href}>
                  <Button
                    variant="outline"
                    className="w-full h-auto py-4 flex flex-col items-center gap-2 border-border hover:border-primary/50 hover:bg-secondary/50"
                  >
                    <action.icon className={`h-6 w-6 ${action.color}`} />
                    <span className="text-sm font-medium">{action.label}</span>
                  </Button>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Scene List */}
          <Card className="lg:col-span-2 bg-card border-border">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-lg">片段概览</CardTitle>
              <Link href={`/projects/${projectId}/episodes`}>
                <Button variant="ghost" size="sm" className="text-primary">
                  查看全部
                  <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent className="space-y-3">
              {scenes.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <Clapperboard className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">暂无片段，通过 AI 对话创建</p>
                </div>
              )}
              {scenes.slice(0, 5).map((scene) => (
                <Link
                  key={scene.id}
                  href={`/projects/${projectId}/episodes/${scene.id}`}
                  className="block"
                >
                  <div className="flex items-center gap-4 p-3 rounded-lg hover:bg-secondary/50 transition-colors">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary font-semibold">
                      {scene.scene_code.replace(/^[A-Z]+_/, '')}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground truncate">
                          {scene.title}
                        </span>
                        <Badge className={`text-xs ${sceneStatusColors[scene.status] || 'bg-muted'}`}>
                          {sceneStatusLabels[scene.status] || scene.status}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground truncate">
                        {scene.novel_chapter_start && scene.novel_chapter_end
                          ? `第 ${scene.novel_chapter_start} - ${scene.novel_chapter_end} 章`
                          : scene.scene_types.join(', ')}
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-sm font-medium text-foreground">
                        {scene.status}
                      </p>
                      <p className="text-xs text-muted-foreground">状态</p>
                    </div>
                  </div>
                </Link>
              ))}
            </CardContent>
          </Card>

          {/* Characters */}
          <Card className="bg-card border-border">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-lg">角色</CardTitle>
              <Link href={`/projects/${projectId}/characters`}>
                <Button variant="ghost" size="sm" className="text-primary">
                  全部
                  <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              {characters.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <Users className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">暂无角色</p>
                </div>
              )}
              <div className="space-y-3">
                {characters.slice(0, 6).map((char) => (
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
                      <p className="text-xs text-muted-foreground">{char.role_description || char.char_code}</p>
                    </div>
                  </Link>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </AppLayout>
  );
}
