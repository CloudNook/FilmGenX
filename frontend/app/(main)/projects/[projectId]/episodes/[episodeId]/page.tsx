'use client';

import { use, useEffect, useState, type ComponentType, type ReactNode } from 'react';
import Link from 'next/link';
import { AppLayout } from '@/components/layout';
import {
  projectsApi,
  scenesApi,
  storyboardsApi,
  shotsApi,
  shotGroupsApi,
  charactersApi,
  type ProjectResponse,
  type SceneResponse,
  type ShotResponse,
  type ShotGroupResponse,
  type CharacterResponse,
} from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
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
  MapPin,
  Layers,
  ChevronDown,
  ChevronUp,
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

const sceneTypeLabels: Record<string, string> = {
  battle: '战斗',
  climax: '高潮',
  visual_spectacle: '视觉奇观',
  dialogue: '对白',
  emotional: '情感',
  transition: '转场',
};

function formatSceneTypeLabel(type: string) {
  return sceneTypeLabels[type] || type.replace(/_/g, ' ');
}

function formatChapterRange(start: string | null, end: string | null) {
  if (start && end) return `${start} - ${end}`;
  return start || end || '';
}

function getRecordText(
  record: Record<string, unknown> | null,
  key: string,
): string | null {
  if (!record) return null;
  const value = record[key];
  return typeof value === 'string' && value.trim() ? value : null;
}

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
  const [shotGroups, setShotGroups] = useState<ShotGroupResponse[]>([]);
  const [expandedGroups, setExpandedGroups] = useState<Set<number>>(new Set());
  const [characters, setCharacters] = useState<CharacterResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isNaN(projectIdNum) || isNaN(episodeIdNum)) return;

    Promise.all([
      projectsApi.get(projectIdNum).catch(() => null),
      scenesApi.get(projectIdNum, episodeIdNum).catch(() => null),
      charactersApi.list(projectIdNum).then((r) => r.items).catch(() => []),
    ]).then(async ([p, s, chars]) => {
      setProject(p);
      setScene(s);
      setCharacters(chars);

      if (s) {
        try {
          const storyboard = await storyboardsApi.get(s.id);
          const [shotList, groupList] = await Promise.all([
            shotsApi.list(storyboard.id),
            shotGroupsApi.list(storyboard.id),
          ]);
          setShots(shotList);
          setShotGroups(groupList);
          // 默认展开所有组
          setExpandedGroups(new Set(groupList.map((g) => g.id)));
        } catch {
          // storyboard not created yet
        }
      }

      setLoading(false);
    });
  }, [projectIdNum, episodeIdNum]);

  if (loading) {
    return (
      <AppLayout projectId={projectId}>
        <div className="flex h-full items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppLayout>
    );
  }

  if (!project || !scene) {
    return (
      <AppLayout projectId={projectId}>
        <div className="flex h-full items-center justify-center">
          <p className="text-muted-foreground">片段不存在</p>
        </div>
      </AppLayout>
    );
  }

  const completedShots = shots.filter((shot) => shot.status === 'approved').length;
  const generatingShots = shots.filter((shot) => shot.status === 'generating').length;
  const reviewShots = shots.filter((shot) => shot.status === 'review').length;
  const progress = shots.length > 0 ? Math.round((completedShots / shots.length) * 100) : 0;
  const chapterRange = formatChapterRange(scene.novel_chapter_start, scene.novel_chapter_end);

  const toggleGroup = (groupId: number) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) next.delete(groupId);
      else next.add(groupId);
      return next;
    });
  };

  // 构建分组映射：groupId → shots
  const groupedShotMap = new Map<number, ShotResponse[]>();
  const groupedShotIds = new Set<number>();
  for (const group of shotGroups) {
    const memberIds = new Set((group.shots || []).map((s) => s.id));
    const groupShots = shots.filter((s) => memberIds.has(s.id));
    groupedShotMap.set(group.id, groupShots);
    groupShots.forEach((s) => groupedShotIds.add(s.id));
  }
  const ungroupedShots = shots.filter((s) => !groupedShotIds.has(s.id));

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const sceneCharIds = new Set(scene.character_ids);
  const linkedCharacters = characters.filter((character) => sceneCharIds.has(character.id));
  const linkedCharacterNames = new Set(linkedCharacters.map((character) => character.name));
  const plainCharacterNames = scene.characters.filter((name) => !linkedCharacterNames.has(name));

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
      <div className="space-y-6 p-6">
        <section className="relative overflow-hidden rounded-[28px] border border-border bg-gradient-to-br from-primary/10 via-background to-secondary/30 p-6 sm:p-7">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.2),transparent_30%),radial-gradient(circle_at_bottom_left,rgba(59,130,246,0.12),transparent_35%)]" />
          <div className="relative space-y-6">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0 space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className="border-border/80 bg-background/70 font-mono text-[11px] tracking-[0.18em]">
                    {scene.scene_code}
                  </Badge>
                  <Badge className={sceneStatusColors[scene.status] || 'bg-muted text-muted-foreground'}>
                    {sceneStatusLabels[scene.status] || scene.status}
                  </Badge>
                  <Badge variant="outline" className="border-border/80 bg-background/70">
                    优先级 {scene.priority}
                  </Badge>
                </div>

                <div className="space-y-3">
                  <h1 className="text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
                    {scene.title}
                  </h1>
                  <p className="max-w-4xl text-sm leading-7 text-muted-foreground sm:text-base">
                    {scene.synopsis || '暂无剧情概述'}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-muted-foreground">
                  {chapterRange && (
                    <span className="flex items-center gap-1.5">
                      <Film className="h-4 w-4" />
                      {chapterRange}
                    </span>
                  )}
                  {scene.estimated_duration_sec && (
                    <span className="flex items-center gap-1.5">
                      <Clock className="h-4 w-4" />
                      预估 {formatDuration(scene.estimated_duration_sec)}
                    </span>
                  )}
                  {scene.primary_location && (
                    <span className="flex items-center gap-1.5">
                      <MapPin className="h-4 w-4" />
                      {scene.primary_location}
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap gap-2">
                  {scene.theme && (
                    <Badge className="bg-primary/15 text-primary hover:bg-primary/15">
                      主题: {scene.theme}
                    </Badge>
                  )}
                  {scene.scene_types.map((type) => (
                    <Badge key={type} variant="outline" className="border-border/70 bg-background/60">
                      {formatSceneTypeLabel(type)}
                    </Badge>
                  ))}
                  {scene.characters.slice(0, 5).map((character) => (
                    <Badge key={character} className="bg-secondary/80 text-secondary-foreground hover:bg-secondary/80">
                      {character}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="flex shrink-0 flex-col gap-2 sm:flex-row lg:flex-col">
                <Button variant="outline" className="border-border/80 bg-background/70">
                  <Edit className="mr-2 h-4 w-4" />
                  编辑信息
                </Button>
                <Link href={`/projects/${projectId}/storyboard?scene=${episodeId}`}>
                  <Button className="w-full bg-primary text-primary-foreground hover:bg-primary/90 lg:w-auto">
                    <Sparkles className="mr-2 h-4 w-4" />
                    分镜工作台
                  </Button>
                </Link>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <OverviewMetric
                icon={Film}
                label="镜头完成"
                value={`${completedShots}/${shots.length || 0}`}
                hint={shots.length > 0 ? '已通过镜头数' : '尚未生成分镜'}
                tone="primary"
              />
              <OverviewMetric
                icon={Sparkles}
                label="制作进度"
                value={`${progress}%`}
                hint={generatingShots > 0 ? `${generatingShots} 个镜头生成中` : '当前无生成任务'}
                tone="warning"
              />
              <OverviewMetric
                icon={Users}
                label="角色规模"
                value={`${scene.characters.length || linkedCharacters.length}`}
                hint={scene.character_focus || '人物冲突与成长信息待补充'}
                tone="info"
              />
              <OverviewMetric
                icon={CheckCircle2}
                label="审核状态"
                value={`${reviewShots}`}
                hint={reviewShots > 0 ? '镜头待审核确认' : '暂无待审核镜头'}
                tone="success"
              />
            </div>

            <div className="rounded-2xl border border-border/70 bg-background/70 p-4">
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="text-muted-foreground">分镜完成度</span>
                <span className="font-medium text-foreground">{progress}%</span>
              </div>
              <Progress value={progress} className="h-2.5" />
            </div>
          </div>
        </section>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.55fr)_360px]">
          <div className="min-w-0">
            <Tabs defaultValue="shots" className="space-y-5">
              <TabsList className="h-auto flex-wrap justify-start gap-2 rounded-2xl border border-border bg-card p-1">
                <TabsTrigger value="shots" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                  <Film className="mr-2 h-4 w-4" />
                  镜头列表 ({shots.length})
                </TabsTrigger>
                <TabsTrigger value="script" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                  <FileText className="mr-2 h-4 w-4" />
                  剧情文本
                </TabsTrigger>
                <TabsTrigger value="characters" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                  <Users className="mr-2 h-4 w-4" />
                  角色 ({linkedCharacters.length + plainCharacterNames.length})
                </TabsTrigger>
                <TabsTrigger value="settings" className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                  <Settings className="mr-2 h-4 w-4" />
                  制作设定
                </TabsTrigger>
              </TabsList>

              <TabsContent value="shots" className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <MiniStat label="总镜头数" value={String(shots.length)} />
                  <MiniStat label="分镜组" value={String(shotGroups.length)} />
                  <MiniStat label="已通过" value={String(completedShots)} />
                  <MiniStat
                    label="总时长"
                    value={formatDuration(shots.reduce((sum, shot) => sum + shot.duration_sec, 0))}
                  />
                </div>

                {shots.length > 0 ? (
                  <div className="space-y-4">
                    {/* 分镜组展示 */}
                    {shotGroups.map((group) => {
                      const groupShots = groupedShotMap.get(group.id) || [];
                      const isExpanded = expandedGroups.has(group.id);
                      return (
                        <div
                          key={group.id}
                          className="overflow-hidden rounded-2xl border border-border bg-card"
                        >
                          {/* 分镜组头部 */}
                          <button
                            onClick={() => toggleGroup(group.id)}
                            className="flex w-full items-center justify-between gap-4 bg-muted/40 px-5 py-3.5 text-left transition-colors hover:bg-muted/60"
                          >
                            <div className="flex items-center gap-3">
                              <Layers className="h-4 w-4 text-primary" />
                              <span className="font-mono text-sm font-semibold text-foreground">
                                {group.group_code}
                              </span>
                              {group.name && (
                                <span className="text-sm text-foreground">{group.name}</span>
                              )}
                            </div>
                            <div className="flex items-center gap-3">
                              {group.plan_intent && (
                                <span className="hidden max-w-xs truncate text-xs text-muted-foreground sm:inline">
                                  {group.plan_intent.slice(0, 60)}{group.plan_intent.length > 60 ? '...' : ''}
                                </span>
                              )}
                              <Badge variant="outline" className="border-border text-xs">
                                {groupShots.length} 镜头
                              </Badge>
                              <Badge variant="outline" className="border-border text-xs">
                                {formatDuration(group.total_duration_sec || 0)}
                              </Badge>
                              <Badge className={`text-xs ${shotStatusColors[group.status] || 'bg-muted text-muted-foreground'}`}>
                                {shotStatusLabels[group.status] || group.status}
                              </Badge>
                              {isExpanded ? (
                                <ChevronUp className="h-4 w-4 text-muted-foreground" />
                              ) : (
                                <ChevronDown className="h-4 w-4 text-muted-foreground" />
                              )}
                            </div>
                          </button>

                          {/* 分镜组内的镜头 */}
                          {isExpanded && (
                            <div className="grid grid-cols-1 gap-3 p-4 lg:grid-cols-2 2xl:grid-cols-3">
                              {groupShots.map((shot) => (
                                <ShotCard
                                  key={shot.id}
                                  shot={shot}
                                  projectId={projectId}
                                  episodeId={episodeId}
                                  formatDuration={formatDuration}
                                />
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}

                    {/* 未分组的独立镜头 */}
                    {ungroupedShots.length > 0 && (
                      <div>
                        {shotGroups.length > 0 && (
                          <div className="mb-3 flex items-center gap-2 text-sm text-muted-foreground">
                            <Film className="h-4 w-4" />
                            独立镜头（未分组）
                          </div>
                        )}
                        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 2xl:grid-cols-3">
                          {ungroupedShots.map((shot) => (
                            <ShotCard
                              key={shot.id}
                              shot={shot}
                              projectId={projectId}
                              episodeId={episodeId}
                              formatDuration={formatDuration}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <Card className="border-border bg-card">
                    <CardContent className="py-14 text-center">
                      <Film className="mx-auto mb-4 h-12 w-12 text-muted-foreground/70" />
                      <h3 className="mb-2 text-lg font-semibold text-foreground">暂无镜头</h3>
                      <p className="mb-5 text-muted-foreground">
                        当前分集还没有生成分镜，前往分镜工作台开始拆镜。
                      </p>
                      <Link href={`/projects/${projectId}/storyboard?scene=${episodeId}`}>
                        <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
                          <Sparkles className="mr-2 h-4 w-4" />
                          打开分镜工作台
                        </Button>
                      </Link>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="script" className="space-y-4">
                <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_320px]">
                  <Card className="border-border bg-card">
                    <CardHeader>
                      <CardTitle>原著摘录</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {chapterRange && (
                        <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
                          <Badge variant="outline" className="border-border">{chapterRange}</Badge>
                        </div>
                      )}
                      {scene.novel_excerpt ? (
                        <p className="whitespace-pre-wrap text-sm leading-7 text-foreground">
                          {scene.novel_excerpt}
                        </p>
                      ) : (
                        <p className="text-sm text-muted-foreground">暂无原著摘录</p>
                      )}
                    </CardContent>
                  </Card>

                  <Card className="border-border bg-card">
                    <CardHeader>
                      <CardTitle>剧情摘要</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4 text-sm leading-7">
                      <InfoLine label="核心主题" value={scene.theme || '暂无'} />
                      <InfoLine label="剧情弧线" value={scene.story_arc || '暂无'} />
                      <InfoLine label="情绪曲线" value={scene.emotional_arc || '暂无'} />
                      <InfoLine label="角色焦点" value={scene.character_focus || '暂无'} />
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              <TabsContent value="characters" className="space-y-4">
                {linkedCharacters.length > 0 && (
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    {linkedCharacters.map((character) => (
                      <Card key={character.id} className="border-border bg-card">
                        <CardContent className="p-5">
                          <div className="flex items-start gap-4">
                            <Avatar className="h-14 w-14 border border-border/70">
                              <AvatarFallback className="bg-primary/10 text-lg text-primary">
                                {character.name.slice(0, 1)}
                              </AvatarFallback>
                            </Avatar>
                            <div className="min-w-0 flex-1 space-y-2">
                              <div className="flex flex-wrap items-center gap-2">
                                <h3 className="font-semibold text-foreground">{character.name}</h3>
                                <Badge variant="outline" className="border-border text-xs">
                                  {character.char_code}
                                </Badge>
                              </div>
                              <p className="text-sm leading-6 text-muted-foreground">
                                {character.role_description || '暂无角色描述'}
                              </p>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}

                {plainCharacterNames.length > 0 && (
                  <Card className="border-border bg-card">
                    <CardHeader>
                      <CardTitle>待关联角色</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <p className="text-sm text-muted-foreground">
                        这些角色已经出现在分集设定里，但还没有和素材库角色建立关联。
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {plainCharacterNames.map((name) => (
                          <Badge key={name} className="bg-secondary text-secondary-foreground">
                            {name}
                          </Badge>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {linkedCharacters.length === 0 && plainCharacterNames.length === 0 && (
                  <Card className="border-border bg-card">
                    <CardContent className="py-14 text-center">
                      <Users className="mx-auto mb-4 h-12 w-12 text-muted-foreground/70" />
                      <h3 className="mb-2 text-lg font-semibold text-foreground">暂无角色信息</h3>
                      <p className="text-muted-foreground">
                        为分集补充角色后，这里会展示角色卡和角色关联情况。
                      </p>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="settings" className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <DetailPanel title="基础信息">
                    <InfoLine label="分集编号" value={scene.scene_code} />
                    <InfoLine label="状态" value={sceneStatusLabels[scene.status] || scene.status} />
                    <InfoLine label="优先级" value={scene.priority} />
                    <InfoLine
                      label="场景类型"
                      value={scene.scene_types.map(formatSceneTypeLabel).join(' / ') || '暂无'}
                    />
                  </DetailPanel>

                  <DetailPanel title="空间与氛围">
                    <InfoLine label="主要地点" value={scene.primary_location || '暂无'} />
                    <InfoLine label="环境气质" value={scene.location_atmosphere || '暂无'} />
                    <InfoLine label="色彩方向" value={scene.color_palette || '暂无'} />
                    <InfoLine label="音乐方向" value={scene.bgm_direction || '暂无'} />
                  </DetailPanel>

                  <DetailPanel title="叙事衔接">
                    <InfoLine label="上集承接" value={scene.previous_episode_hint || '暂无'} />
                    <InfoLine label="下集铺垫" value={scene.next_episode_hint || '暂无'} />
                  </DetailPanel>

                  <DetailPanel title="分镜备注">
                    <p className="text-sm leading-7 text-muted-foreground">
                      {scene.storyboard_style_notes || '暂无分镜风格备注'}
                    </p>
                  </DetailPanel>
                </div>
              </TabsContent>
            </Tabs>
          </div>

          <aside className="space-y-4">
            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle>本集速览</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <InfoLine label="核心主题" value={scene.theme || '暂无'} />
                <InfoLine label="剧情节奏" value={scene.story_arc || '暂无'} />
                <InfoLine label="情绪曲线" value={scene.emotional_arc || '暂无'} />
                <InfoLine label="角色焦点" value={scene.character_focus || '暂无'} />
                <InfoLine label="场景氛围" value={scene.location_atmosphere || '暂无'} />
              </CardContent>
            </Card>

            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle>关键事件</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {scene.key_events.length > 0 ? (
                  scene.key_events.map((event) => (
                    <div key={`${event.order}-${event.description}`} className="rounded-2xl border border-border/70 bg-muted/30 p-3">
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <span className="text-sm font-medium text-foreground">事件 {event.order}</span>
                        <Badge variant="outline" className="border-border text-[11px]">
                          {event.emotional_beat}
                        </Badge>
                      </div>
                      <p className="text-sm leading-6 text-muted-foreground">{event.description}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">暂无关键事件拆解</p>
                )}
              </CardContent>
            </Card>

            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle>视觉与分镜</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {scene.visual_highlights.length > 0 ? (
                  <div className="space-y-3">
                    {scene.visual_highlights.slice(0, 4).map((highlight) => (
                      <div key={highlight.name} className="rounded-2xl border border-border/70 bg-muted/30 p-3">
                        <p className="mb-1 text-sm font-medium text-foreground">{highlight.name}</p>
                        <p className="text-sm leading-6 text-muted-foreground">{highlight.description}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">暂无视觉亮点描述</p>
                )}

                <div className="rounded-2xl border border-border/70 bg-secondary/30 p-3">
                  <p className="mb-1 text-sm font-medium text-foreground">分镜风格提示</p>
                  <p className="text-sm leading-6 text-muted-foreground">
                    {scene.storyboard_style_notes || '暂无分镜风格提示'}
                  </p>
                </div>
              </CardContent>
            </Card>
          </aside>
        </div>
      </div>
    </AppLayout>
  );
}

function OverviewMetric({
  icon: Icon,
  label,
  value,
  hint,
  tone,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
  hint: string;
  tone: 'primary' | 'warning' | 'info' | 'success';
}) {
  const toneClasses: Record<typeof tone, string> = {
    primary: 'bg-primary/10 text-primary',
    warning: 'bg-warning/10 text-warning',
    info: 'bg-info/10 text-info',
    success: 'bg-success/10 text-success',
  };

  return (
    <div className="rounded-2xl border border-border/70 bg-background/70 p-4">
      <div className="mb-3 flex items-center gap-3">
        <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${toneClasses[tone]}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-xl font-semibold text-foreground">{value}</p>
        </div>
      </div>
      <p className="line-clamp-2 text-xs leading-5 text-muted-foreground">{hint}</p>
    </div>
  );
}

function MiniStat({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-card px-4 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold text-foreground">{value}</p>
    </div>
  );
}

function DetailPanel({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <Card className="border-border bg-card">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">{children}</CardContent>
    </Card>
  );
}

function InfoLine({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </p>
      <p className="text-sm leading-6 text-foreground">{value}</p>
    </div>
  );
}

function ShotCard({
  shot,
  projectId,
  episodeId,
  formatDuration,
}: {
  shot: ShotResponse;
  projectId: string;
  episodeId: string;
  formatDuration: (seconds: number) => string;
}) {
  const shotType = getRecordText(shot.camera, 'shot_type');
  const movement = getRecordText(shot.camera, 'movement');
  const atmosphere = getRecordText(shot.environment, 'atmosphere');

  return (
    <Link href={`/projects/${projectId}/storyboard?scene=${episodeId}&shot=${shot.id}`}>
      <Card className="cursor-pointer overflow-hidden border-border bg-card transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/50 hover:shadow-md">
        <div className="relative aspect-video overflow-hidden bg-muted">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/15 via-secondary/20 to-muted" />
          <div className="absolute inset-0 flex items-center justify-center">
            <Camera className="h-10 w-10 text-muted-foreground/70" />
          </div>
          <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/15 to-transparent" />

          <Badge className="absolute left-3 top-3 border-0 bg-black/60 text-white">
            {shot.shot_code}
          </Badge>

          <div className="absolute bottom-0 left-0 right-0 p-3">
            <div className="mb-2 flex items-center justify-between gap-3">
              <Badge className={`text-xs ${shotStatusColors[shot.status] || 'bg-muted text-muted-foreground'}`}>
                {shot.status === 'generating' && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                {shotStatusLabels[shot.status] || shot.status}
              </Badge>
              <span className="flex items-center gap-1 text-xs text-white/80">
                <Clock className="h-3 w-3" />
                {formatDuration(shot.duration_sec)}
              </span>
            </div>
            <p className="line-clamp-2 text-sm text-white/90">
              {shot.image_prompt || '暂无镜头描述'}
            </p>
          </div>
        </div>

        <CardContent className="space-y-3 p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-foreground">镜头 {shot.sequence}</p>
              <p className="text-xs text-muted-foreground">
                {shotType || movement || atmosphere || '等待补充分镜语言'}
              </p>
            </div>
            {shot.qc_approved && (
              <span className="inline-flex items-center gap-1 rounded-full bg-success/10 px-2 py-1 text-xs text-success">
                <CheckCircle2 className="h-3.5 w-3.5" />
                QC通过
              </span>
            )}
          </div>

          {(shotType || movement || atmosphere) && (
            <div className="flex flex-wrap gap-2">
              {shotType && (
                <Badge variant="outline" className="border-border text-xs">
                  {shotType}
                </Badge>
              )}
              {movement && (
                <Badge variant="outline" className="border-border text-xs">
                  {movement}
                </Badge>
              )}
              {atmosphere && (
                <Badge variant="outline" className="border-border text-xs">
                  {atmosphere}
                </Badge>
              )}
            </div>
          )}

          {shot.dialogue_text && (
            <div className="rounded-xl border border-border/70 bg-secondary/40 p-3">
              <div className="mb-1 flex items-center gap-1 text-xs text-muted-foreground">
                <Volume2 className="h-3 w-3" />
                {shot.dialogue_character || '台词'}
              </div>
              <p className="line-clamp-2 text-sm text-foreground">{shot.dialogue_text}</p>
            </div>
          )}

          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">
              {shot.transition_in || shot.transition_out
                ? `${shot.transition_in || '切入'} / ${shot.transition_out || '切出'}`
                : '查看分镜详情与镜头参数'}
            </span>
            <span className="flex items-center text-primary">
              查看详情
              <ChevronRight className="ml-0.5 h-3 w-3" />
            </span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
