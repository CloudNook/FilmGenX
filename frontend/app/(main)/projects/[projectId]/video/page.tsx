'use client';

import { use, useState, useEffect, useCallback, useRef } from 'react';
import { AppLayout } from '@/components/layout';
import {
  projectsApi,
  scenesApi,
  storyboardsApi,
  shotsApi,
  tasksApi,
  type ProjectResponse,
  type SceneResponse,
  type ShotResponse,
  type TaskResponse,
} from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
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
  Film,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RefreshCw,
  Plus,
  Eye,
  EyeOff,
  Lock,
  Unlock,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Local types for the timeline editor (purely UI)
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export default function VideoPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const projectIdNum = Number(projectId);

  // ---- data state ----
  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [scenes, setScenes] = useState<SceneResponse[]>([]);
  const [shots, setShots] = useState<ShotResponse[]>([]);
  const [selectedSceneId, setSelectedSceneId] = useState<string>('');
  const [storyboardId, setStoryboardId] = useState<number | null>(null);
  const [tasks, setTasks] = useState<TaskResponse[]>([]);

  // ---- UI state ----
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(80);
  const [isMuted, setIsMuted] = useState(false);
  const [zoom, setZoom] = useState(100);
  const [tracks, setTracks] = useState<TimelineTrack[]>([]);
  const [rendering, setRendering] = useState(false);

  // refs for polling
  const pollingRef = useRef<Map<number, ReturnType<typeof setInterval>>>(
    new Map(),
  );

  // ---- helpers ----

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const frames = Math.floor((seconds % 1) * 24);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}:${frames.toString().padStart(2, '0')}`;
  };

  const getTrackIcon = (type: TimelineTrack['type']) => {
    switch (type) {
      case 'video':
        return Film;
      case 'audio':
        return Music;
      case 'text':
        return Type;
      case 'effect':
        return Layers;
    }
  };

  const toggleTrackVisibility = (trackId: string) => {
    setTracks((prev) =>
      prev.map((t) => (t.id === trackId ? { ...t, visible: !t.visible } : t)),
    );
  };

  const toggleTrackLock = (trackId: string) => {
    setTracks((prev) =>
      prev.map((t) => (t.id === trackId ? { ...t, locked: !t.locked } : t)),
    );
  };

  // ---- build timeline tracks from shots ----

  const buildTracks = useCallback((shotList: ShotResponse[]): TimelineTrack[] => {
    if (shotList.length === 0) return [];

    const videoItems: TimelineItem[] = shotList.map((s, i) => {
      const offset = shotList.slice(0, i).reduce((acc, prev) => acc + prev.duration_sec, 0);
      const statusColor =
        s.status === 'approved'
          ? 'bg-primary'
          : s.status === 'generating'
            ? 'bg-warning'
            : s.status === 'review'
              ? 'bg-info'
              : s.status === 'rejected'
                ? 'bg-destructive'
                : 'bg-muted-foreground';
      return {
        id: `v-${s.id}`,
        name: s.shot_code || `镜头 ${s.sequence}`,
        startTime: offset,
        duration: s.duration_sec,
        color: statusColor,
      };
    });

    const totalDur = shotList.reduce((acc, s) => acc + s.duration_sec, 0);

    const audioItems: TimelineItem[] = shotList
      .filter((s) => s.dialogue_text)
      .map((s) => {
        const idx = shotList.indexOf(s);
        const offset = shotList
          .slice(0, idx)
          .reduce((acc, prev) => acc + prev.duration_sec, 0);
        return {
          id: `a-${s.id}`,
          name: s.dialogue_character || '台词',
          startTime: offset,
          duration: s.duration_sec,
          color: 'bg-info',
        };
      });

    const bgmItems: TimelineItem[] = totalDur > 0
      ? [{ id: 'bgm-1', name: 'BGM', startTime: 0, duration: totalDur, color: 'bg-success' }]
      : [];

    const subtitleItems: TimelineItem[] = shotList
      .filter((s) => s.dialogue_text)
      .map((s) => {
        const idx = shotList.indexOf(s);
        const offset = shotList
          .slice(0, idx)
          .reduce((acc, prev) => acc + prev.duration_sec, 0);
        return {
          id: `t-${s.id}`,
          name: s.dialogue_text!.slice(0, 10) + '...',
          startTime: offset,
          duration: s.duration_sec,
          color: 'bg-muted-foreground',
        };
      });

    return [
      { id: 'video-1', name: '视频轨道', type: 'video' as const, items: videoItems, visible: true, locked: false },
      { id: 'audio-1', name: '对话音轨', type: 'audio' as const, items: audioItems, visible: true, locked: false },
      { id: 'audio-2', name: '背景音乐', type: 'audio' as const, items: bgmItems, visible: true, locked: true },
      { id: 'text-1', name: '字幕', type: 'text' as const, items: subtitleItems, visible: true, locked: false },
    ];
  }, []);

  // ---- polling helpers ----

  const stopPolling = useCallback((taskId: number) => {
    const timer = pollingRef.current.get(taskId);
    if (timer) {
      clearInterval(timer);
      pollingRef.current.delete(taskId);
    }
  }, []);

  const startPolling = useCallback(
    (taskId: number) => {
      if (pollingRef.current.has(taskId)) return;
      const timer = setInterval(async () => {
        try {
          const t = await tasksApi.get(taskId);
          setTasks((prev) => prev.map((x) => (x.id === taskId ? t : x)));
          if (t.status === 'completed' || t.status === 'failed') {
            stopPolling(taskId);
            // After task completes, reload shots to get updated status
            if (storyboardId) {
              const freshShots = await shotsApi.list(storyboardId);
              setShots(freshShots);
              setTracks(buildTracks(freshShots));
            }
          }
        } catch {
          stopPolling(taskId);
        }
      }, 3000);
      pollingRef.current.set(taskId, timer);
    },
    [stopPolling, storyboardId, buildTracks],
  );

  // ---- data fetching ----

  // Initial load: project + scenes
  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const proj = await projectsApi.get(projectIdNum);
        if (cancelled) return;
        setProject(proj);

        const page = await scenesApi.list(projectIdNum);
        if (cancelled) return;
        setScenes(page.items);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '加载失败');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [projectIdNum]);

  // When scene changes, load storyboard then shots
  useEffect(() => {
    if (!selectedSceneId) {
      setShots([]);
      setTracks([]);
      setStoryboardId(null);
      setTasks([]);
      return;
    }

    let cancelled = false;

    async function loadSceneData() {
      const sceneIdNum = Number(selectedSceneId);
      try {
        const storyboard = await storyboardsApi.get(sceneIdNum);
        if (cancelled) return;
        setStoryboardId(storyboard.id);

        const shotList = await shotsApi.list(storyboard.id);
        if (cancelled) return;
        setShots(shotList);
        setTracks(buildTracks(shotList));
      } catch {
        if (!cancelled) {
          // storyboard may not exist yet
          setShots([]);
          setTracks([]);
          setStoryboardId(null);
        }
      }
    }

    // clear old polling timers
    pollingRef.current.forEach((_, id) => stopPolling(id));
    setTasks([]);
    loadSceneData();

    return () => {
      cancelled = true;
    };
  }, [selectedSceneId, buildTracks, stopPolling]);

  // Cleanup all polling on unmount
  useEffect(() => {
    return () => {
      pollingRef.current.forEach((_, id) => stopPolling(id));
    };
  }, [stopPolling]);

  // ---- actions ----

  const handleTriggerRender = async () => {
    if (!shots.length) return;
    setRendering(true);
    try {
      // Trigger video generation for every shot that is not already generating/completed
      const shotsToRender = shots.filter(
        (s) => s.status !== 'generating' && s.status !== 'approved',
      );
      const newTasks: TaskResponse[] = [];
      for (const shot of shotsToRender) {
        const task = await tasksApi.triggerVideo({ shot_id: shot.id });
        newTasks.push(task);
        startPolling(task.id);
      }
      setTasks((prev) => [...prev, ...newTasks]);

      // Refresh shots to reflect generating status
      if (storyboardId) {
        const freshShots = await shotsApi.list(storyboardId);
        setShots(freshShots);
        setTracks(buildTracks(freshShots));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '触发渲染失败');
    } finally {
      setRendering(false);
    }
  };

  // ---- derived values ----

  const totalDuration = tracks[0]
    ? tracks[0].items.reduce((sum, item) => sum + item.duration, 0)
    : 0;

  // ---- render ----

  if (loading) {
    return (
      <AppLayout
        projectId={projectId}
        showSearch={false}
        breadcrumbs={[
          { label: '项目', href: '/projects' },
          { label: '视频制作' },
        ]}
      >
        <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppLayout>
    );
  }

  if (error && !project) {
    return (
      <AppLayout
        projectId={projectId}
        showSearch={false}
        breadcrumbs={[
          { label: '项目', href: '/projects' },
          { label: '视频制作' },
        ]}
      >
        <div className="flex flex-col items-center justify-center h-[calc(100vh-4rem)] gap-4">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <p className="text-muted-foreground">{error}</p>
          <Button variant="outline" onClick={() => window.location.reload()}>
            重试
          </Button>
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

  const taskStatusLabel = (status: string) => {
    switch (status) {
      case 'completed':
        return '已完成';
      case 'processing':
      case 'running':
        return '处理中...';
      case 'pending':
      case 'queued':
        return '排队中';
      case 'failed':
        return '失败';
      default:
        return status;
    }
  };

  const taskStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'processing':
      case 'running':
        return <Loader2 className="h-4 w-4 text-yellow-500 animate-spin" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-destructive" />;
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />;
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
                  <p className="text-sm">
                    {selectedSceneId ? '选择分镜后将显示合成预览' : '请选择场景以开始'}
                  </p>
                </div>
              </div>

              {/* Playhead Time */}
              <div className="absolute top-4 left-4 bg-black/80 rounded px-3 py-1">
                <span className="text-white font-mono text-sm">
                  {formatTime(currentTime)}
                </span>
              </div>

              {/* Controls Overlay */}
              <div className="absolute top-4 right-4 flex items-center gap-2">
                <Select
                  value={selectedSceneId}
                  onValueChange={setSelectedSceneId}
                >
                  <SelectTrigger className="w-48 bg-black/80 border-white/20 text-white text-sm">
                    <SelectValue placeholder="选择场景" />
                  </SelectTrigger>
                  <SelectContent>
                    {scenes.map((scene) => (
                      <SelectItem key={scene.id} value={String(scene.id)}>
                        {scene.scene_code} - {scene.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  variant="secondary"
                  size="icon"
                  className="h-8 w-8 bg-black/80 hover:bg-black/90"
                >
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
                  {isPlaying ? (
                    <Pause className="h-5 w-5" />
                  ) : (
                    <Play className="h-5 w-5" />
                  )}
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
                    {isMuted ? (
                      <VolumeX className="h-4 w-4" />
                    ) : (
                      <Volume2 className="h-4 w-4" />
                    )}
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
                {tasks.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    暂无渲染任务
                  </p>
                )}
                {tasks.map((task) => (
                  <Card key={task.id} className="bg-secondary border-border">
                    <CardContent className="p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-foreground">
                          Shot #{task.shot_id}
                        </span>
                        {taskStatusIcon(task.status)}
                      </div>
                      <Progress value={task.progress} className="h-1.5" />
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-xs text-muted-foreground">
                          {taskStatusLabel(task.status)}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {task.progress}%
                        </span>
                      </div>
                      {task.error_message && (
                        <p className="text-xs text-destructive mt-1 truncate">
                          {task.error_message}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
            <div className="p-4 border-t border-border">
              <Button
                className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
                onClick={handleTriggerRender}
                disabled={rendering || !selectedSceneId || shots.length === 0}
              >
                {rendering ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-2" />
                )}
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
              <span className="text-xs text-muted-foreground w-8">
                {zoom}%
              </span>
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
                {Array.from({
                  length: totalDuration > 0 ? Math.ceil(totalDuration / 5) + 1 : 1,
                }).map((_, i) => (
                  <div
                    key={i}
                    className="flex-shrink-0"
                    style={{ width: `${5 * (zoom / 100) * 20}px` }}
                  >
                    <span className="text-[10px] text-muted-foreground">
                      {i * 5}s
                    </span>
                  </div>
                ))}
              </div>

              {/* Tracks */}
              <div className="relative">
                {/* Playhead */}
                {totalDuration > 0 && (
                  <div
                    className="absolute top-0 bottom-0 w-0.5 bg-primary z-10"
                    style={{
                      left: `${currentTime * (zoom / 100) * 20 + 8}px`,
                    }}
                  >
                    <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-3 h-3 bg-primary rotate-45" />
                  </div>
                )}

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
