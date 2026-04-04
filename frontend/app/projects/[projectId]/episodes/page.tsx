'use client';

import { use, useState } from 'react';
import Link from 'next/link';
import { AppLayout } from '@/components/layout';
import { getProjectById, getEpisodesByProjectId } from '@/lib/mock-data';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
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
} from 'lucide-react';
import type { Episode } from '@/lib/types';

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

export default function EpisodesPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const project = getProjectById(projectId);
  const episodes = getEpisodesByProjectId(projectId);

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  if (!project) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-full">
          <p className="text-muted-foreground">项目不存在</p>
        </div>
      </AppLayout>
    );
  }

  const filteredEpisodes = episodes.filter((episode) => {
    const matchesSearch =
      episode.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      episode.synopsis.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || episode.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const formatDuration = (seconds: number) => {
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
                <SelectItem value="scripting">剧本</SelectItem>
                <SelectItem value="storyboarding">分镜</SelectItem>
                <SelectItem value="production">制作</SelectItem>
                <SelectItem value="completed">完成</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
            <Plus className="h-4 w-4 mr-2" />
            新建分集
          </Button>
        </div>

        {/* Episodes Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {filteredEpisodes.map((episode) => (
            <EpisodeCard
              key={episode.id}
              episode={episode}
              projectId={projectId}
              formatDuration={formatDuration}
            />
          ))}
        </div>

        {/* Empty State */}
        {filteredEpisodes.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted mb-4">
              <FileText className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">没有找到分集</h3>
            <p className="text-muted-foreground mb-6">
              {searchQuery || statusFilter !== 'all'
                ? '尝试调整搜索条件或筛选器'
                : '点击上方按钮创建第一个分集'}
            </p>
          </div>
        )}
      </div>
    </AppLayout>
  );
}

function EpisodeCard({
  episode,
  projectId,
  formatDuration,
}: {
  episode: Episode;
  projectId: string;
  formatDuration: (seconds: number) => string;
}) {
  const progress = episode.shotCount > 0 
    ? Math.round((episode.completedShots / episode.shotCount) * 100) 
    : 0;

  return (
    <Card className="bg-card border-border hover:border-primary/50 transition-all duration-200">
      <CardContent className="p-0">
        <div className="flex">
          {/* Episode Number */}
          <div className="flex items-center justify-center w-20 bg-primary/10 shrink-0">
            <span className="text-3xl font-bold text-primary">{episode.number}</span>
          </div>

          {/* Content */}
          <div className="flex-1 p-4">
            <div className="flex items-start justify-between mb-2">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold text-foreground">{episode.title}</h3>
                  <Badge className={`text-xs ${statusColors[episode.status]}`}>
                    {statusLabels[episode.status]}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {episode.synopsis}
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
                {episode.completedShots}/{episode.shotCount} 镜头
              </span>
              {episode.duration > 0 && (
                <span className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  {formatDuration(episode.duration)}
                </span>
              )}
            </div>

            {/* Progress */}
            {episode.shotCount > 0 && (
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">完成进度</span>
                  <span className="text-foreground font-medium">{progress}%</span>
                </div>
                <Progress value={progress} className="h-1.5" />
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-2 mt-4">
              <Link href={`/projects/${projectId}/episodes/${episode.id}`} className="flex-1">
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full border-border hover:border-primary/50"
                >
                  查看详情
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
              <Link href={`/projects/${projectId}/storyboard?episode=${episode.id}`}>
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
