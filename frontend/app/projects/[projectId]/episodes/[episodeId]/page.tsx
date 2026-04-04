'use client';

import { use } from 'react';
import Link from 'next/link';
import { AppLayout } from '@/components/layout';
import {
  getProjectById,
  getEpisodeById,
  getShotsByEpisodeId,
  getCharactersByProjectId,
} from '@/lib/mock-data';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
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
  AlertCircle,
  Loader2,
} from 'lucide-react';
import type { Shot, Episode } from '@/lib/types';

const statusLabels: Record<Episode['status'], string> = {
  draft: '草稿',
  scripting: '剧本',
  storyboarding: '分镜',
  production: '制作',
  completed: '完成',
};

const statusColors: Record<Episode['status'], string> = {
  draft: 'bg-muted text-muted-foreground',
  scripting: 'bg-info/20 text-info',
  storyboarding: 'bg-warning/20 text-warning',
  production: 'bg-primary/20 text-primary',
  completed: 'bg-success/20 text-success',
};

const shotStatusLabels: Record<Shot['status'], string> = {
  draft: '草稿',
  approved: '已批准',
  rendering: '渲染中',
  completed: '完成',
};

const shotStatusColors: Record<Shot['status'], string> = {
  draft: 'bg-muted text-muted-foreground',
  approved: 'bg-info/20 text-info',
  rendering: 'bg-warning/20 text-warning',
  completed: 'bg-success/20 text-success',
};

const shotStatusIcons: Record<Shot['status'], React.ComponentType<{ className?: string }>> = {
  draft: Edit,
  approved: CheckCircle2,
  rendering: Loader2,
  completed: CheckCircle2,
};

export default function EpisodeDetailPage({
  params,
}: {
  params: Promise<{ projectId: string; episodeId: string }>;
}) {
  const { projectId, episodeId } = use(params);
  const project = getProjectById(projectId);
  const episode = getEpisodeById(episodeId);
  const shots = getShotsByEpisodeId(episodeId);
  const characters = getCharactersByProjectId(projectId);

  if (!project || !episode) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-full">
          <p className="text-muted-foreground">分集不存在</p>
        </div>
      </AppLayout>
    );
  }

  const progress = episode.shotCount > 0
    ? Math.round((episode.completedShots / episode.shotCount) * 100)
    : 0;

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // 获取该分集涉及的角色
  const episodeCharacterIds = new Set(shots.flatMap((shot) => shot.characters));
  const episodeCharacters = characters.filter((char) => episodeCharacterIds.has(char.id));

  return (
    <AppLayout
      projectId={projectId}
      breadcrumbs={[
        { label: '项目', href: '/projects' },
        { label: project.name, href: `/projects/${projectId}` },
        { label: '分集管理', href: `/projects/${projectId}/episodes` },
        { label: `第 ${episode.number} 集` },
      ]}
    >
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                <span className="text-xl font-bold text-primary">{episode.number}</span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-2xl font-bold text-foreground">{episode.title}</h1>
                  <Badge className={statusColors[episode.status]}>
                    {statusLabels[episode.status]}
                  </Badge>
                </div>
                <p className="text-muted-foreground">{episode.synopsis}</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" className="border-border">
              <Edit className="h-4 w-4 mr-2" />
              编辑信息
            </Button>
            <Link href={`/projects/${projectId}/storyboard?episode=${episodeId}`}>
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
                  {episode.completedShots}/{episode.shotCount}
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
                <p className="text-sm text-muted-foreground">时长</p>
                <p className="text-xl font-bold text-foreground">
                  {episode.duration > 0 ? formatDuration(episode.duration) : '--:--'}
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
                <p className="text-sm text-muted-foreground">出场角色</p>
                <p className="text-xl font-bold text-foreground">{episodeCharacters.length}</p>
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
              镜头列表
            </TabsTrigger>
            <TabsTrigger value="script" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              <FileText className="h-4 w-4 mr-2" />
              剧本
            </TabsTrigger>
            <TabsTrigger value="characters" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              <Users className="h-4 w-4 mr-2" />
              角色
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
                  <Link href={`/projects/${projectId}/storyboard?episode=${episodeId}`}>
                    <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
                      <Sparkles className="h-4 w-4 mr-2" />
                      打开分镜工作台
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Script Tab */}
          <TabsContent value="script">
            <Card className="bg-card border-border">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>剧本内容</span>
                  <Button variant="outline" size="sm" className="border-border">
                    <Edit className="h-4 w-4 mr-2" />
                    编辑剧本
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose prose-invert max-w-none">
                  <h3>第 {episode.number} 集 - {episode.title}</h3>
                  <p className="text-muted-foreground">{episode.synopsis}</p>
                  
                  <h4>场景一：飞船驾驶舱</h4>
                  <p>
                    【内景 - 曙光号驾驶舱 - 日】
                    <br />
                    飞船缓缓接近神秘行星，驾驶舱内警报灯闪烁。船长陈明站在指挥台前，
                    凝视着窗外的星球表面。
                  </p>
                  <p className="text-primary">
                    <strong>陈明</strong>：这就是我们要寻找的答案吗？
                  </p>
                  <p className="text-muted-foreground italic">
                    （陈明转身，看向科学官李薇）
                  </p>
                  <p className="text-info">
                    <strong>李薇</strong>：大气成分显示这颗行星适合人类居住，但是...
                  </p>
                  <p className="text-primary">
                    <strong>陈明</strong>：但是什么？
                  </p>
                  <p className="text-info">
                    <strong>李薇</strong>：我检测到了一些异常的能量波动，来源不明。
                  </p>
                </div>
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
                        <AvatarImage src={character.avatarUrl} />
                        <AvatarFallback className="bg-primary/10 text-primary text-xl">
                          {character.name.slice(0, 1)}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold text-foreground">{character.name}</h3>
                          <Badge variant="outline" className="border-border text-xs">
                            {character.role === 'protagonist' ? '主角' : 
                             character.role === 'antagonist' ? '反派' : '配角'}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {character.description}
                        </p>
                        <p className="text-xs text-muted-foreground mt-2">
                          出现在 {shots.filter(s => s.characters.includes(character.id)).length} 个镜头
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
                      在镜头中添加角色后会在此显示
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
                <CardTitle>分集设置</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">分辨率</label>
                    <p className="text-sm text-muted-foreground">1920 x 1080 (1080p)</p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">帧率</label>
                    <p className="text-sm text-muted-foreground">24 FPS</p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">宽高比</label>
                    <p className="text-sm text-muted-foreground">16:9</p>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">AI 模型</label>
                    <p className="text-sm text-muted-foreground">FilmGenX-v2</p>
                  </div>
                </div>
                <Button variant="outline" className="border-border">
                  <Settings className="h-4 w-4 mr-2" />
                  修改设置
                </Button>
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
  shot: Shot;
  formatDuration: (seconds: number) => string;
}) {
  const StatusIcon = shotStatusIcons[shot.status];

  return (
    <Card className="bg-card border-border hover:border-primary/50 transition-all duration-200 overflow-hidden">
      {/* Thumbnail */}
      <div className="relative aspect-video bg-muted">
        {shot.thumbnailUrl ? (
          <div
            className="absolute inset-0 bg-cover bg-center"
            style={{ backgroundImage: `url(${shot.thumbnailUrl})` }}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-secondary to-muted">
            <Camera className="h-8 w-8 text-muted-foreground" />
          </div>
        )}
        
        {/* Overlay Info */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-3">
          <div className="flex items-center justify-between">
            <Badge className={`text-xs ${shotStatusColors[shot.status]}`}>
              <StatusIcon className={`h-3 w-3 mr-1 ${shot.status === 'rendering' ? 'animate-spin' : ''}`} />
              {shotStatusLabels[shot.status]}
            </Badge>
            <span className="text-xs text-white/80 flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatDuration(shot.duration)}
            </span>
          </div>
        </div>

        {/* Version Badge */}
        <Badge className="absolute top-2 left-2 bg-black/60 text-white border-0">
          v{shot.version}
        </Badge>

        {/* Play Button */}
        {shot.videoUrl && (
          <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
            <Button size="icon" className="h-12 w-12 rounded-full bg-primary/90 hover:bg-primary">
              <Play className="h-6 w-6 text-primary-foreground" />
            </Button>
          </div>
        )}
      </div>

      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm font-medium text-foreground">镜头 {shot.number}</span>
          <span className="text-xs text-muted-foreground">|</span>
          <span className="text-xs text-muted-foreground">{shot.shotType.replace('_', ' ')}</span>
        </div>
        <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
          {shot.description}
        </p>
        
        {shot.dialogue && (
          <div className="bg-secondary/50 rounded-lg p-2 mb-3">
            <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
              <Volume2 className="h-3 w-3" />
              台词
            </div>
            <p className="text-xs text-foreground line-clamp-2">{shot.dialogue}</p>
          </div>
        )}

        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">{shot.mood}</span>
          <Button variant="ghost" size="sm" className="h-7 text-primary">
            编辑
            <ChevronRight className="h-3 w-3 ml-1" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
