'use client';

import { use, useState } from 'react';
import { AppLayout } from '@/components/layout';
import {
  getProjectById,
  getEpisodesByProjectId,
  shots as allShots,
} from '@/lib/mock-data';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Slider } from '@/components/ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
  Maximize2,
  Download,
  Upload,
  Settings,
  Layers,
  Music,
  Type,
  Image,
  Film,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RefreshCw,
  Plus,
  Trash2,
  ChevronUp,
  ChevronDown,
  Eye,
  EyeOff,
  Lock,
  Unlock,
} from 'lucide-react';
import type { Shot } from '@/lib/types';

interface TimelineTrack {
  id: string;
  name: string;
  type: 'video' | 'audio' | 'text' | 'effect';
  items: TimelineItem[];
  visible: boolean;
  locked: boolean;
}

interface TimelineItem {
  id: string;
  name: string;
  startTime: number;
  duration: number;
  color: string;
}

const mockTracks: TimelineTrack[] = [
  {
    id: 'video-1',
    name: '视频轨道',
    type: 'video',
    visible: true,
    locked: false,
    items: [
      { id: 'v1', name: '镜头 1', startTime: 0, duration: 8, color: 'bg-primary' },
      { id: 'v2', name: '镜头 2', startTime: 8, duration: 5, color: 'bg-primary' },
      { id: 'v3', name: '镜头 3', startTime: 13, duration: 6, color: 'bg-primary' },
      { id: 'v4', name: '镜头 4', startTime: 19, duration: 10, color: 'bg-warning' },
    ],
  },
  {
    id: 'audio-1',
    name: '对话音轨',
    type: 'audio',
    visible: true,
    locked: false,
    items: [
      { id: 'a1', name: '陈明台词', startTime: 8, duration: 4, color: 'bg-info' },
      { id: 'a2', name: '李薇台词', startTime: 13, duration: 5, color: 'bg-info' },
    ],
  },
  {
    id: 'audio-2',
    name: '背景音乐',
    type: 'audio',
    visible: true,
    locked: true,
    items: [
      { id: 'bgm1', name: 'BGM - 紧张氛围', startTime: 0, duration: 29, color: 'bg-success' },
    ],
  },
  {
    id: 'text-1',
    name: '字幕',
    type: 'text',
    visible: true,
    locked: false,
    items: [
      { id: 't1', name: '场景介绍', startTime: 0, duration: 3, color: 'bg-muted-foreground' },
    ],
  },
];

const renderTasks = [
  { id: 'task-1', name: '镜头 1 渲染', progress: 100, status: 'completed' as const },
  { id: 'task-2', name: '镜头 2 渲染', progress: 100, status: 'completed' as const },
  { id: 'task-3', name: '镜头 3 渲染', progress: 78, status: 'processing' as const },
  { id: 'task-4', name: '镜头 4 渲染', progress: 0, status: 'queued' as const },
  { id: 'task-5', name: '音频合成', progress: 0, status: 'queued' as const },
  { id: 'task-6', name: '最终导出', progress: 0, status: 'queued' as const },
];

export default function VideoPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const project = getProjectById(projectId);
  const episodes = getEpisodesByProjectId(projectId);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(80);
  const [isMuted, setIsMuted] = useState(false);
  const [selectedEpisode, setSelectedEpisode] = useState<string>(episodes[2]?.id || '');
  const [zoom, setZoom] = useState(100);
  const [tracks, setTracks] = useState(mockTracks);

  if (!project) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-full">
          <p className="text-muted-foreground">项目不存在</p>
        </div>
      </AppLayout>
    );
  }

  const totalDuration = 29; // 秒

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const frames = Math.floor((seconds % 1) * 24);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}:${frames.toString().padStart(2, '0')}`;
  };

  const toggleTrackVisibility = (trackId: string) => {
    setTracks(tracks.map(t => 
      t.id === trackId ? { ...t, visible: !t.visible } : t
    ));
  };

  const toggleTrackLock = (trackId: string) => {
    setTracks(tracks.map(t => 
      t.id === trackId ? { ...t, locked: !t.locked } : t
    ));
  };

  const getTrackIcon = (type: TimelineTrack['type']) => {
    switch (type) {
      case 'video': return Film;
      case 'audio': return Music;
      case 'text': return Type;
      case 'effect': return Layers;
    }
  };

  return (
    <AppLayout
      projectId={projectId}
      showSearch={false}
      breadcrumbs={[
        { label: '项目', href: '/projects' },
        { label: project.name, href: `/projects/${projectId}` },
        { label: '视频制作' },
      ]}
    >
      <div className="h-[calc(100vh-4rem)] flex flex-col">
        {/* Top Section - Preview and Tasks */}
        <div className="flex-1 flex min-h-0">
          {/* Preview Area */}
          <div className="flex-1 flex flex-col bg-black">
            {/* Video Preview */}
            <div className="flex-1 relative flex items-center justify-center">
              <div className="aspect-video w-full max-w-4xl bg-gradient-to-br from-secondary to-muted rounded-lg flex items-center justify-center">
                <div className="text-center text-white/60">
                  <Film className="h-16 w-16 mx-auto mb-4" />
                  <p className="text-lg">视频预览区域</p>
                  <p className="text-sm">选择分集后将显示合成预览</p>
                </div>
              </div>

              {/* Playhead Time */}
              <div className="absolute top-4 left-4 bg-black/80 rounded px-3 py-1">
                <span className="text-white font-mono text-sm">{formatTime(currentTime)}</span>
              </div>

              {/* Controls Overlay */}
              <div className="absolute top-4 right-4 flex items-center gap-2">
                <Select value={selectedEpisode} onValueChange={setSelectedEpisode}>
                  <SelectTrigger className="w-48 bg-black/80 border-white/20 text-white text-sm">
                    <SelectValue placeholder="选择分集" />
                  </SelectTrigger>
                  <SelectContent>
                    {episodes.map((ep) => (
                      <SelectItem key={ep.id} value={ep.id}>
                        第 {ep.number} 集 - {ep.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button variant="secondary" size="icon" className="h-8 w-8 bg-black/80 hover:bg-black/90">
                  <Maximize2 className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Playback Controls */}
            <div className="h-16 bg-card border-t border-border flex items-center justify-between px-4">
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <SkipBack className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-10 w-10"
                  onClick={() => setIsPlaying(!isPlaying)}
                >
                  {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
                </Button>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <SkipForward className="h-4 w-4" />
                </Button>
                
                <div className="flex items-center gap-2 ml-4">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => setIsMuted(!isMuted)}
                  >
                    {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
                  </Button>
                  <Slider
                    value={[isMuted ? 0 : volume]}
                    onValueChange={([v]) => {
                      setVolume(v);
                      setIsMuted(v === 0);
                    }}
                    max={100}
                    className="w-24"
                  />
                </div>

                <span className="text-sm text-muted-foreground ml-4 font-mono">
                  {formatTime(currentTime)} / {formatTime(totalDuration)}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" className="border-border">
                  <Settings className="h-4 w-4 mr-2" />
                  设置
                </Button>
                <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
                  <Download className="h-4 w-4 mr-2" />
                  导出视频
                </Button>
              </div>
            </div>
          </div>

          {/* Right Panel - Render Tasks */}
          <div className="w-80 border-l border-border bg-card flex flex-col">
            <div className="p-4 border-b border-border">
              <h2 className="font-semibold text-foreground">渲染任务</h2>
            </div>
            <ScrollArea className="flex-1">
              <div className="p-4 space-y-3">
                {renderTasks.map((task) => (
                  <Card key={task.id} className="bg-secondary border-border">
                    <CardContent className="p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-foreground">{task.name}</span>
                        {task.status === 'completed' && (
                          <CheckCircle2 className="h-4 w-4 text-success" />
                        )}
                        {task.status === 'processing' && (
                          <Loader2 className="h-4 w-4 text-warning animate-spin" />
                        )}
                        {task.status === 'queued' && (
                          <Clock className="h-4 w-4 text-muted-foreground" />
                        )}
                      </div>
                      <Progress value={task.progress} className="h-1.5" />
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-xs text-muted-foreground">
                          {task.status === 'completed' && '已完成'}
                          {task.status === 'processing' && '处理中...'}
                          {task.status === 'queued' && '排队中'}
                        </span>
                        <span className="text-xs text-muted-foreground">{task.progress}%</span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
            <div className="p-4 border-t border-border">
              <Button className="w-full bg-primary text-primary-foreground hover:bg-primary/90">
                <RefreshCw className="h-4 w-4 mr-2" />
                开始渲染
              </Button>
            </div>
          </div>
        </div>

        {/* Timeline Section */}
        <div className="h-64 border-t border-border bg-card flex flex-col">
          {/* Timeline Header */}
          <div className="h-10 border-b border-border flex items-center justify-between px-4">
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" className="h-7">
                <Plus className="h-3.5 w-3.5 mr-1" />
                添加轨道
              </Button>
              <Button variant="ghost" size="sm" className="h-7">
                <Upload className="h-3.5 w-3.5 mr-1" />
                导入素材
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">缩放</span>
              <Slider
                value={[zoom]}
                onValueChange={([v]) => setZoom(v)}
                min={50}
                max={200}
                className="w-24"
              />
              <span className="text-xs text-muted-foreground w-8">{zoom}%</span>
            </div>
          </div>

          {/* Timeline Tracks */}
          <div className="flex-1 flex overflow-hidden">
            {/* Track Labels */}
            <div className="w-48 border-r border-border bg-secondary/30">
              {tracks.map((track) => {
                const Icon = getTrackIcon(track.type);
                return (
                  <div
                    key={track.id}
                    className="h-12 border-b border-border flex items-center gap-2 px-3"
                  >
                    <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
                    <span className="text-xs font-medium text-foreground flex-1 truncate">
                      {track.name}
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => toggleTrackVisibility(track.id)}
                    >
                      {track.visible ? (
                        <Eye className="h-3 w-3 text-muted-foreground" />
                      ) : (
                        <EyeOff className="h-3 w-3 text-muted-foreground" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => toggleTrackLock(track.id)}
                    >
                      {track.locked ? (
                        <Lock className="h-3 w-3 text-muted-foreground" />
                      ) : (
                        <Unlock className="h-3 w-3 text-muted-foreground" />
                      )}
                    </Button>
                  </div>
                );
              })}
            </div>

            {/* Timeline Content */}
            <div className="flex-1 overflow-x-auto">
              {/* Time Ruler */}
              <div className="h-6 border-b border-border bg-secondary/30 flex items-end px-2">
                {Array.from({ length: Math.ceil(totalDuration / 5) + 1 }).map((_, i) => (
                  <div
                    key={i}
                    className="flex-shrink-0"
                    style={{ width: `${5 * (zoom / 100) * 20}px` }}
                  >
                    <span className="text-[10px] text-muted-foreground">{i * 5}s</span>
                  </div>
                ))}
              </div>

              {/* Tracks */}
              <div className="relative">
                {/* Playhead */}
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-primary z-10"
                  style={{ left: `${currentTime * (zoom / 100) * 20 + 8}px` }}
                >
                  <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-3 h-3 bg-primary rotate-45" />
                </div>

                {tracks.map((track) => (
                  <div
                    key={track.id}
                    className={`h-12 border-b border-border relative ${
                      !track.visible ? 'opacity-50' : ''
                    }`}
                  >
                    {track.items.map((item) => (
                      <div
                        key={item.id}
                        className={`absolute top-1 bottom-1 ${item.color} rounded cursor-pointer hover:brightness-110 transition-all ${
                          track.locked ? 'cursor-not-allowed' : ''
                        }`}
                        style={{
                          left: `${item.startTime * (zoom / 100) * 20 + 8}px`,
                          width: `${item.duration * (zoom / 100) * 20 - 4}px`,
                        }}
                      >
                        <div className="px-2 py-1 h-full flex items-center overflow-hidden">
                          <span className="text-[10px] text-white truncate font-medium">
                            {item.name}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
