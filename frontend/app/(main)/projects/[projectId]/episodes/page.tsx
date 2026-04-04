'use client';

import { use, useEffect, useState } from 'react';
import Link from 'next/link';
import { AppLayout } from '@/components/layout';
import { projectsApi, scenesApi, type ProjectResponse, type SceneResponse } from '@/lib/api';
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
  Plus,
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
    const matchesSearch =
      scene.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (scene.novel_excerpt || '').toLowerCase().includes(searchQuery.toLowerCase());
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

  return (
    <Card className="bg-card border-border hover:border-primary/50 transition-all duration-200">
      <CardContent className="p-0">
        <div className="flex">
          {/* Scene Code / Priority */}
          <div className="flex items-center justify-center w-20 bg-primary/10 shrink-0">
            <div className="text-center">
              <span className="text-lg font-bold text-primary block">
                {scene.scene_code.replace(/^[A-Z]+_/, '')}
              </span>
              <Badge className={`text-xs mt-1 ${priorityColors[scene.priority] || ''}`}>
                {scene.priority}
              </Badge>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 p-4">
            <div className="flex items-start justify-between mb-2">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold text-foreground">{scene.title}</h3>
                  <Badge className={`text-xs ${statusColors[scene.status] || 'bg-muted'}`}>
                    {statusLabels[scene.status] || scene.status}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {scene.novel_chapter_start && scene.novel_chapter_end
                    ? `第 ${scene.novel_chapter_start} - ${scene.novel_chapter_end} 章`
                    : scene.scene_types.join(', ')}
                </p>
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

            {/* Stats */}
            <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3">
              <span className="flex items-center gap-1">
                <Film className="h-3.5 w-3.5" />
                评分 {scene.score_total ?? '-'}
              </span>
              {scene.estimated_duration_sec && (
                <span className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  {formatDuration(scene.estimated_duration_sec)}
                </span>
              )}
              {scene.scene_types.length > 0 && (
                <div className="flex gap-1">
                  {scene.scene_types.slice(0, 3).map((t) => (
                    <Badge key={t} variant="outline" className="text-xs border-border">
                      {t}
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 mt-4">
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
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
