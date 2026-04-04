'use client';

import { use } from 'react';
import Link from 'next/link';
import { AppLayout } from '@/components/layout';
import {
  getProjectById,
  getEpisodesByProjectId,
  getCharactersByProjectId,
  emotionCurveData,
} from '@/lib/mock-data';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
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
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
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

export default function ProjectWorkspacePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const project = getProjectById(projectId);
  const episodes = getEpisodesByProjectId(projectId);
  const characters = getCharactersByProjectId(projectId);

  if (!project) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-full">
          <p className="text-muted-foreground">项目不存在</p>
        </div>
      </AppLayout>
    );
  }

  const completedEpisodes = episodes.filter(e => e.status === 'completed').length;
  const inProgressEpisodes = episodes.filter(e => e.status === 'production' || e.status === 'storyboarding').length;
  const totalShots = episodes.reduce((sum, e) => sum + e.shotCount, 0);
  const completedShots = episodes.reduce((sum, e) => sum + e.completedShots, 0);

  const quickActions = [
    { icon: MessageSquare, label: 'AI 对话', href: `/projects/${projectId}/chat`, color: 'text-primary' },
    { icon: Clapperboard, label: '分集管理', href: `/projects/${projectId}/episodes`, color: 'text-info' },
    { icon: Sparkles, label: '分镜工作台', href: `/projects/${projectId}/storyboard`, color: 'text-warning' },
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
            <p className="text-muted-foreground max-w-2xl">{project.description}</p>
            <div className="flex items-center gap-2 pt-2">
              {project.tags.map((tag) => (
                <Badge key={tag} variant="outline" className="border-border">
                  {tag}
                </Badge>
              ))}
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
                  <p className="text-sm text-muted-foreground">总进度</p>
                  <p className="text-2xl font-bold text-foreground">{project.progress}%</p>
                </div>
                <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <TrendingUp className="h-6 w-6 text-primary" />
                </div>
              </div>
              <Progress value={project.progress} className="mt-3 h-2" />
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">分集</p>
                  <p className="text-2xl font-bold text-foreground">
                    {completedEpisodes}/{project.episodeCount}
                  </p>
                </div>
                <div className="h-12 w-12 rounded-full bg-info/10 flex items-center justify-center">
                  <Clapperboard className="h-6 w-6 text-info" />
                </div>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                {inProgressEpisodes} 集制作中
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">镜头</p>
                  <p className="text-2xl font-bold text-foreground">
                    {completedShots}/{totalShots}
                  </p>
                </div>
                <div className="h-12 w-12 rounded-full bg-warning/10 flex items-center justify-center">
                  <Film className="h-6 w-6 text-warning" />
                </div>
              </div>
              <Progress value={(completedShots / totalShots) * 100} className="mt-3 h-2" />
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
                    <AvatarImage src={char.avatarUrl} />
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
          {/* Episode List */}
          <Card className="lg:col-span-2 bg-card border-border">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-lg">分集概览</CardTitle>
              <Link href={`/projects/${projectId}/episodes`}>
                <Button variant="ghost" size="sm" className="text-primary">
                  查看全部
                  <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent className="space-y-3">
              {episodes.slice(0, 5).map((episode) => (
                <Link
                  key={episode.id}
                  href={`/projects/${projectId}/episodes/${episode.id}`}
                  className="block"
                >
                  <div className="flex items-center gap-4 p-3 rounded-lg hover:bg-secondary/50 transition-colors">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary font-semibold">
                      {episode.number}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground truncate">
                          {episode.title}
                        </span>
                        <Badge className={`text-xs ${statusColors[episode.status]}`}>
                          {statusLabels[episode.status]}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground truncate">
                        {episode.synopsis}
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-sm font-medium text-foreground">
                        {episode.completedShots}/{episode.shotCount}
                      </p>
                      <p className="text-xs text-muted-foreground">镜头</p>
                    </div>
                  </div>
                </Link>
              ))}
            </CardContent>
          </Card>

          {/* Emotion Curve */}
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">情感曲线</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={emotionCurveData}>
                    <defs>
                      <linearGradient id="tensionGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis
                      dataKey="time"
                      tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
                      tickFormatter={(value) => `${Math.floor(value / 60)}m`}
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
                      domain={[0, 100]}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                      }}
                      labelFormatter={(value) => `时间: ${Math.floor(Number(value) / 60)}分${Number(value) % 60}秒`}
                      formatter={(value: number, name: string) => [value, name === 'tension' ? '张力' : name]}
                    />
                    <Area
                      type="monotone"
                      dataKey="tension"
                      stroke="hsl(var(--primary))"
                      fill="url(#tensionGradient)"
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 space-y-2">
                {emotionCurveData
                  .filter((point) => point.label)
                  .slice(0, 4)
                  .map((point, index) => (
                    <div key={index} className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">{point.label}</span>
                      <Badge variant="outline" className="border-border">
                        {point.tension}%
                      </Badge>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Activity */}
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">最近活动</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[
                { icon: CheckCircle2, color: 'text-success', text: '第三集镜头 1-3 渲染完成', time: '10 分钟前' },
                { icon: MessageSquare, color: 'text-primary', text: 'AI 优化了第四集的台词', time: '25 分钟前' },
                { icon: Film, color: 'text-warning', text: '新增 5 个分镜到第三集', time: '1 小时前' },
                { icon: AlertCircle, color: 'text-destructive', text: '镜头 4 渲染失败，需要重试', time: '2 小时前' },
                { icon: Users, color: 'text-info', text: '更新了角色「陈明」的外观设定', time: '3 小时前' },
              ].map((activity, index) => (
                <div key={index} className="flex items-center gap-3">
                  <div className={`h-8 w-8 rounded-full bg-secondary flex items-center justify-center ${activity.color}`}>
                    <activity.icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-foreground">{activity.text}</p>
                  </div>
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {activity.time}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
