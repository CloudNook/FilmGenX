'use client';

import { use, useEffect, useState } from 'react';
import Link from 'next/link';
import { AppLayout } from '@/components/layout';
import {
  projectsApi,
  scenesApi,
  storyboardsApi,
  shotsApi,
  charactersApi,
  type ProjectResponse,
  type SceneResponse,
  type ShotResponse,
  type CharacterResponse,
} from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Play,
  Edit,
  Clock,
  Film,
  Users,
  FileText,
  Sparkles,
  ChevronRight,
  Camera,
  Volume2,
  Settings,
  CheckCircle2,
  Loader2,
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

const shotStatusLabels: Record<string, string> = {
  draft: '草稿',
  generating: '生成中',
  review: '审核中',
  approved: '已通过',
  rejected: '已拒绝',
};

const shotStatusColors: Record<string, string> = {
  draft: 'bg-muted text-muted-foreground',
  generating: 'bg-warning/20 text-warning',
  review: 'bg-info/20 text-info',
  approved: 'bg-success/20 text-success',
  rejected: 'bg-destructive/20 text-destructive',
};

export default function EpisodeDetailPage({
  params,
}: {
  params: Promise<{ projectId: string; episodeId: string }>;
}) {
  const { projectId, episodeId } = use(params);
  const projectIdNum = Number(projectId);
  const episodeIdNum = Number(episodeId);

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [scene, setScene] = useState<SceneResponse | null>(null);
  const [shots, setShots] = useState<ShotResponse[]>([]);
  const [characters, setCharacters] = useState<CharacterResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isNaN(projectIdNum) || isNaN(episodeIdNum)) return;

    Promise.all([
      projectsApi.get(projectIdNum).catch(() => null),
      scenesApi.get(projectIdNum, episodeIdNum).catch(() => null),
      charactersApi.list(projectIdNum).then(r => r.items).catch(() => []),
    ]).then(async ([p, s, chars]) => {
      setProject(p);
      setScene(s);
      setCharacters(chars);

      // Load storyboard + shots if scene exists
      if (s) {
        try {
          const sb = await storyboardsApi.get(s.id);
          const shotList = await shotsApi.list(sb.id);
          setShots(shotList);
        } catch {
          // no storyboard yet
        }
      }
      setLoading(false);
    });
  }, [projectIdNum, episodeIdNum]);

  if (loading) {
    return (
      <AppLayout projectId={projectId}>
        <div className="flex items-center justify-center h-full">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppLayout>
    );
  }

  if (!project || !scene) {
    return (
      <AppLayout projectId={projectId}>
        <div className="flex items-center justify-center h-full">
          <p className="text-muted-foreground">片段不存在</p>
        </div>
      </AppLayout>
    );
  }

  const completedShots = shots.filter(s => s.status === 'approved').length;
  const progress = shots.length > 0 ? Math.round((completedShots / shots.length) * 100) : 0;

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Characters in this scene
  const sceneCharIds = new Set(scene.character_ids);
  const episodeCharacters = characters.filter(c => sceneCharIds.has(c.id));

  return (
    <AppLayout
      projectId={projectId}
      breadcrumbs={[
        { label: '项目', href: '/projects' },
        { label: project.name, href: `/projects/${projectId}` },
        { label: '分集管理', href: `/projects/${projectId}/episodes` },
        { label: scene.title },
      ]}
    >
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                <span className="text-xl font-bold text-primary">
                  {scene.scene_code.replace(/^[A-Z]+_/, '')}
                </span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-2xl font-bold text-foreground">{scene.title}</h1>
                  <Badge className={sceneStatusColors[scene.status] || 'bg-muted'}>
                    {sceneStatusLabels[scene.status] || scene.status}
                  </Badge>
                  <Badge variant="outline" className="border-border">
                    优先级 {scene.priority}
                  </Badge>
                </div>
                <p className="text-muted-foreground">
                  {scene.novel_chapter_start && scene.novel_chapter_end
                    ? `第 ${scene.novel_chapter_start} - ${scene.novel_chapter_end} 章`
                    : ''}
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" className="border-border">
              <Edit className="h-4 w-4 mr-2" />
              编辑信息
            </Button>
            <Link href={`/projects/${projectId}/storyboard?scene=${episodeId}`}>
              <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
                <Sparkles className="h-4 w-4 mr-2" />
                分镜工作台
              </Button>
            </Link>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-card border-border">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Film className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">镜头数</p>
                <p className="text-xl font-bold text-foreground">
                  {completedShots}/{shots.length}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="h-10 w-10 rounded-lg bg-info/10 flex items-center justify-center">
                <Clock className="h-5 w-5 text-info" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">预估时长</p>
                <p className="text-xl font-bold text-foreground">
                  {scene.estimated_duration_sec ? formatDuration(scene.estimated_duration_sec) : '--:--'}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="h-10 w-10 rounded-lg bg-warning/10 flex items-center justify-center">
                <Users className="h-5 w-5 text-warning" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">评分</p>
                <p className="text-xl font-bold text-foreground">
                  {scene.score_total ?? '-'}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">完成进度</span>
                <span className="text-sm font-medium text-foreground">{progress}%</span>
              </div>
              <Progress value={progress} className="h-2" />
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="shots" className="space-y-4">
          <TabsList className="bg-card border border-border">
            <TabsTrigger value="shots" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              <Film className="h-4 w-4 mr-2" />
              镜头列表 ({shots.length})
            </TabsTrigger>
            <TabsTrigger value="script" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              <FileText className="h-4 w-4 mr-2" />
              原著摘录
            </TabsTrigger>
            <TabsTrigger value="characters" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              <Users className="h-4 w-4 mr-2" />
              角色 ({episodeCharacters.length})
            </TabsTrigger>
            <TabsTrigger value="settings" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              <Settings className="h-4 w-4 mr-2" />
              设置
            </TabsTrigger>
          </TabsList>

          {/* Shots Tab */}
          <TabsContent value="shots" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
              {shots.map((shot) => (
                <ShotCard key={shot.id} shot={shot} formatDuration={formatDuration} />
              ))}
            </div>
            {shots.length === 0 && (
              <Card className="bg-card border-border">
                <CardContent className="py-12 text-center">
                  <Film className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-semibold text-foreground mb-2">暂无镜头</h3>
                  <p className="text-muted-foreground mb-4">
                    前往分镜工作台创建第一个镜头
                  </p>
                  <Link href={`/projects/${projectId}/storyboard?scene=${episodeId}`}>
                    <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
                      <Sparkles className="h-4 w-4 mr-2" />
                      打开分镜工作台
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Script / Novel Excerpt Tab */}
          <TabsContent value="script">
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>原著摘录</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {scene.novel_excerpt ? (
                  <div className="prose prose-invert max-w-none">
                    <p className="text-foreground whitespace-pre-wrap leading-relaxed">
                      {scene.novel_excerpt}
                    </p>
                  </div>
                ) : (
                  <p className="text-muted-foreground">暂无原著摘录</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Characters Tab */}
          <TabsContent value="characters">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {episodeCharacters.map((character) => (
                <Card key={character.id} className="bg-card border-border">
                  <CardContent className="p-4">
                    <div className="flex items-start gap-4">
                      <Avatar className="h-16 w-16">
                        <AvatarFallback className="bg-primary/10 text-primary text-xl">
                          {character.name.slice(0, 1)}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold text-foreground">{character.name}</h3>
                          <Badge variant="outline" className="border-border text-xs">
                            {character.char_code}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {character.role_description || '暂无描述'}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {episodeCharacters.length === 0 && (
                <Card className="bg-card border-border col-span-full">
                  <CardContent className="py-12 text-center">
                    <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <h3 className="text-lg font-semibold text-foreground mb-2">暂无角色</h3>
                    <p className="text-muted-foreground">
                      在片段设置中添加角色后会在此显示
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings">
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle>片段设置</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">片段编号</label>
                    <p className="text-sm text-muted-foreground">{scene.scene_code}</p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">状态</label>
                    <Badge className={sceneStatusColors[scene.status] || 'bg-muted'}>
                      {sceneStatusLabels[scene.status] || scene.status}
                    </Badge>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">优先级</label>
                    <p className="text-sm text-muted-foreground">{scene.priority}</p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">类型</label>
                    <div className="flex gap-2">
                      {scene.scene_types.map(t => (
                        <Badge key={t} variant="outline" className="border-border">{t}</Badge>
                      ))}
                    </div>
                  </div>
                  {scene.novel_chapter_start && (
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-foreground">起始章节</label>
                      <p className="text-sm text-muted-foreground">{scene.novel_chapter_start}</p>
                    </div>
                  )}
                  {scene.novel_chapter_end && (
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-foreground">结束章节</label>
                      <p className="text-sm text-muted-foreground">{scene.novel_chapter_end}</p>
                    </div>
                  )}
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">评分明细</label>
                    <div className="text-sm text-muted-foreground space-y-1">
                      <p>戏剧张力: {scene.score_dramatic_tension ?? '-'}</p>
                      <p>视觉化潜力: {scene.score_visual_potential ?? '-'}</p>
                      <p>情感共鸣: {scene.score_emotional_resonance ?? '-'}</p>
                      <p>叙事重要性: {scene.score_narrative_importance ?? '-'}</p>
                      <p>粉丝熟知度: {scene.score_audience_familiarity ?? '-'}</p>
                      <p className="font-medium text-foreground">总分: {scene.score_total ?? '-'}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppLayout>
  );
}

function ShotCard({
  shot,
  formatDuration,
}: {
  shot: ShotResponse;
  formatDuration: (seconds: number) => string;
}) {
  return (
    <Card className="bg-card border-border hover:border-primary/50 transition-all duration-200 overflow-hidden">
      {/* Thumbnail */}
      <div className="relative aspect-video bg-muted">
        <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-secondary to-muted">
          <Camera className="h-8 w-8 text-muted-foreground" />
        </div>

        {/* Overlay Info */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-3">
          <div className="flex items-center justify-between">
            <Badge className={`text-xs ${shotStatusColors[shot.status] || 'bg-muted'}`}>
              {shot.status === 'generating' && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
              {shotStatusLabels[shot.status] || shot.status}
            </Badge>
            <span className="text-xs text-white/80 flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatDuration(shot.duration_sec)}
            </span>
          </div>
        </div>

        <Badge className="absolute top-2 left-2 bg-black/60 text-white border-0">
          {shot.shot_code}
        </Badge>
      </div>

      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm font-medium text-foreground">镜头 {shot.sequence}</span>
          {shot.camera?.shot_type && (
            <>
              <span className="text-xs text-muted-foreground">|</span>
              <span className="text-xs text-muted-foreground">{shot.camera.shot_type}</span>
            </>
          )}
        </div>
        <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
          {shot.image_prompt || shot.character_action || '暂无描述'}
        </p>

        {shot.dialogue_text && (
          <div className="bg-secondary/50 rounded-lg p-2 mb-3">
            <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
              <Volume2 className="h-3 w-3" />
              {shot.dialogue_character || '台词'}
            </div>
            <p className="text-xs text-foreground line-clamp-2">{shot.dialogue_text}</p>
          </div>
        )}

        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            {shot.camera?.movement || shot.environment?.atmosphere || ''}
          </span>
          <Button variant="ghost" size="sm" className="h-7 text-primary">
            编辑
            <ChevronRight className="h-3 w-3 ml-1" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
