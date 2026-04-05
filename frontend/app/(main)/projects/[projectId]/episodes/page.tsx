'use client';

import { use, useEffect, useState, type ComponentType } from 'react';
import Link from 'next/link';
import { AppLayout } from '@/components/layout';
import {
  projectsApi,
  scenesApi,
  type ProjectResponse,
  type SceneResponse,
} from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Search,
  MoreVertical,
  Play,
  Edit,
  Trash2,
  Copy,
  Clock,
  Film,
  FileText,
  ChevronRight,
  Loader2,
  MapPin,
  Sparkles,
  Users,
} from 'lucide-react';

const statusLabels: Record<string, string> = {
  draft: '草稿',
  scored: '已评分',
  in_production: '制作中',
  completed: '完成',
};

const statusColors: Record<string, string> = {
  draft: 'bg-muted text-muted-foreground',
  scored: 'bg-info/20 text-info',
  in_production: 'bg-primary/20 text-primary',
  completed: 'bg-success/20 text-success',
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

export default function EpisodesPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const projectIdNum = Number(projectId);

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [scenes, setScenes] = useState<SceneResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    if (isNaN(projectIdNum)) return;

    Promise.all([
      projectsApi.get(projectIdNum).catch(() => null),
      scenesApi.list(projectIdNum, 1, 100).then(r => r.items).catch(() => []),
    ]).then(([p, s]) => {
      setProject(p);
      setScenes(s);
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

  const filteredScenes = scenes.filter((scene) => {
    const query = searchQuery.trim().toLowerCase();
    const searchCorpus = [
      scene.scene_code,
      scene.title,
      scene.synopsis || '',
      scene.theme || '',
      scene.story_arc || '',
      scene.novel_excerpt || '',
      scene.primary_location || '',
      scene.previous_episode_hint || '',
      scene.next_episode_hint || '',
      scene.characters.join(' '),
      scene.scene_types.join(' '),
    ]
      .join(' ')
      .toLowerCase();
    const matchesSearch = !query || searchCorpus.includes(query);
    const matchesStatus = statusFilter === 'all' || scene.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '--:--';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <AppLayout
      projectId={projectId}
      breadcrumbs={[
        { label: '项目', href: '/projects' },
        { label: project.name, href: `/projects/${projectId}` },
        { label: '分集管理' },
      ]}
    >
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div className="flex flex-1 gap-3 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-80">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="搜索分集..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 bg-card border-border"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-32 bg-card border-border">
                <SelectValue placeholder="状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="draft">草稿</SelectItem>
                <SelectItem value="scored">已评分</SelectItem>
                <SelectItem value="in_production">制作中</SelectItem>
                <SelectItem value="completed">完成</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Scenes Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {filteredScenes.map((scene) => (
            <SceneCard
              key={scene.id}
              scene={scene}
              projectId={projectId}
              formatDuration={formatDuration}
            />
          ))}
        </div>

        {/* Empty State */}
        {filteredScenes.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted mb-4">
              <FileText className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">
              {scenes.length === 0 ? '暂无分集' : '没有找到匹配的分集'}
            </h3>
            <p className="text-muted-foreground mb-6">
              {scenes.length === 0
                ? '通过 AI 对话创建分集后，会自动出现在这里'
                : '尝试调整搜索条件或筛选器'}
            </p>
            {scenes.length === 0 && (
              <Link href={`/projects/${projectId}/chat`}>
                <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
                  <Film className="h-4 w-4 mr-2" />
                  开始 AI 对话
                </Button>
              </Link>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
}

function SceneCard({
  scene,
  projectId,
  formatDuration,
}: {
  scene: SceneResponse;
  projectId: string;
  formatDuration: (seconds: number | null) => string;
}) {
  const priorityColors: Record<string, string> = {
    S: 'bg-destructive/20 text-destructive',
    A: 'bg-primary/20 text-primary',
    B: 'bg-info/20 text-info',
    C: 'bg-muted text-muted-foreground',
  };

  const chapterRange = formatChapterRange(scene.novel_chapter_start, scene.novel_chapter_end);
  const keyEvents = scene.key_events;
  const hasContextHints = Boolean(scene.previous_episode_hint || scene.next_episode_hint);

  return (
    <Card className="border-border bg-card transition-all duration-200 hover:border-primary/50 hover:shadow-sm">
      <CardContent className="p-5 space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline" className="border-border font-mono text-[11px] tracking-wide">
                {scene.scene_code}
              </Badge>
              <Badge className={`text-xs ${priorityColors[scene.priority] || 'bg-muted text-muted-foreground'}`}>
                优先级 {scene.priority}
              </Badge>
              <Badge className={`text-xs ${statusColors[scene.status] || 'bg-muted text-muted-foreground'}`}>
                {statusLabels[scene.status] || scene.status}
              </Badge>
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-semibold leading-tight text-foreground">{scene.title}</h3>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
                {chapterRange && (
                  <span className="flex items-center gap-1.5">
                    <Film className="h-3.5 w-3.5" />
                    {chapterRange}
                  </span>
                )}
                {scene.estimated_duration_sec && (
                  <span className="flex items-center gap-1.5">
                    <Clock className="h-3.5 w-3.5" />
                    {formatDuration(scene.estimated_duration_sec)}
                  </span>
                )}
                {scene.primary_location && (
                  <span className="flex items-center gap-1.5">
                    <MapPin className="h-3.5 w-3.5" />
                    {scene.primary_location}
                  </span>
                )}
              </div>
            </div>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <Play className="h-4 w-4 mr-2" />
                预览
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Edit className="h-4 w-4 mr-2" />
                编辑
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Copy className="h-4 w-4 mr-2" />
                复制
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-destructive">
                <Trash2 className="h-4 w-4 mr-2" />
                删除
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <p className="text-sm leading-6 text-muted-foreground line-clamp-4">
          {scene.synopsis || '暂无剧情简介'}
        </p>

        <div className="grid gap-3 md:grid-cols-2">
          <InfoBlock
            icon={Sparkles}
            label="核心主题"
            value={scene.theme || '暂无主题描述'}
          />
          <InfoBlock
            icon={MapPin}
            label="剧情节奏"
            value={scene.story_arc || scene.emotional_arc || '暂无节奏描述'}
          />
          <InfoBlock
            icon={Users}
            label="角色焦点"
            value={scene.character_focus || (scene.characters.length > 0 ? scene.characters.join('、') : '暂无角色信息')}
          />
          <InfoBlock
            icon={Film}
            label="视觉亮点"
            value={
              scene.visual_highlights.length > 0
                ? scene.visual_highlights
                    .slice(0, 2)
                    .map((highlight) => highlight.name)
                    .join(' / ')
                : scene.color_palette || '暂无视觉描述'
            }
          />
        </div>

        <div className="flex flex-wrap gap-2">
          {scene.scene_types.slice(0, 3).map((type) => (
            <Badge key={type} variant="outline" className="border-border text-xs">
              {formatSceneTypeLabel(type)}
            </Badge>
          ))}
          {scene.characters.slice(0, 4).map((character) => (
            <Badge key={character} className="bg-secondary text-secondary-foreground text-xs">
              {character}
            </Badge>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
          <span>{keyEvents.length} 个关键事件</span>
          <span>{scene.visual_highlights.length} 个视觉亮点</span>
          <span>{scene.characters.length} 位主要角色</span>
          {keyEvents[0]?.emotional_beat && <span>首个情绪点：{keyEvents[0].emotional_beat}</span>}
        </div>

        {hasContextHints && (
          <div className="grid gap-3 md:grid-cols-2">
            <HintBlock
              label="上集承接"
              value={scene.previous_episode_hint || '暂无'}
            />
            <HintBlock
              label="下集铺垫"
              value={scene.next_episode_hint || '暂无'}
            />
          </div>
        )}

        <div className="flex items-center gap-2 pt-1">
          <Link href={`/projects/${projectId}/episodes/${scene.id}`} className="flex-1">
            <Button
              variant="outline"
              size="sm"
              className="w-full border-border hover:border-primary/50"
            >
              查看详情
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </Link>
          <Link href={`/projects/${projectId}/storyboard?scene=${scene.id}`}>
            <Button size="sm" className="bg-primary text-primary-foreground hover:bg-primary/90">
              分镜工作台
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

function InfoBlock({
  icon: Icon,
  label,
  value,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-border/70 bg-muted/30 p-3">
      <div className="mb-1.5 flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <p className="text-sm leading-6 text-foreground line-clamp-2">{value}</p>
    </div>
  );
}

function HintBlock({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-border/70 bg-secondary/30 p-3">
      <p className="mb-1 text-xs font-medium text-muted-foreground">{label}</p>
      <p className="text-sm leading-6 text-foreground line-clamp-2">{value}</p>
    </div>
  );
}
