'use client';

import { use, useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { AppLayout } from '@/components/layout';
import {
  projectsApi,
  scenesApi,
  storyboardsApi,
  shotsApi,
  tasksApi,
  type ProjectResponse,
  type SceneResponse,
  type StoryboardResponse,
  type ShotResponse,
  type TaskResponse,
} from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Slider } from '@/components/ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable';
import {
  Plus,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Maximize2,
  ZoomIn,
  ZoomOut,
  Grid3X3,
  List,
  Camera,
  Sparkles,
  Wand2,
  RefreshCw,
  Download,
  Upload,
  Trash2,
  Copy,
  Clock,
  Volume2,
  Eye,
  Edit,
  Check,
  X,
  ChevronLeft,
  ChevronRight,
  GripVertical,
  Film,
  Loader2,
} from 'lucide-react';

const shotStatusColors: Record<string, string> = {
  draft: 'bg-muted text-muted-foreground',
  approved: 'bg-info/20 text-info',
  rendering: 'bg-warning/20 text-warning',
  completed: 'bg-success/20 text-success',
};

export default function StoryboardPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const projectIdNum = Number(projectId);
  const searchParams = useSearchParams();
  const urlSceneId = searchParams.get('scene');
  const urlShotId = searchParams.get('shot');

  // Data state
  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [scenes, setScenes] = useState<SceneResponse[]>([]);
  const [storyboard, setStoryboard] = useState<StoryboardResponse | null>(null);
  const [shots, setShots] = useState<ShotResponse[]>([]);

  // Loading state
  const [loadingProject, setLoadingProject] = useState(true);
  const [loadingScenes, setLoadingScenes] = useState(false);
  const [loadingStoryboard, setLoadingStoryboard] = useState(false);
  const [loadingShots, setLoadingShots] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // UI state
  const [selectedScene, setSelectedScene] = useState<string>('');
  const [selectedShot, setSelectedShot] = useState<ShotResponse | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [isPlaying, setIsPlaying] = useState(false);

  // Video generation state
  const [generatingVideo, setGeneratingVideo] = useState(false);
  const [videoTask, setVideoTask] = useState<TaskResponse | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [zoom, setZoom] = useState(100);

  // ---- Data fetching ----

  // Load project
  useEffect(() => {
    let cancelled = false;
    setLoadingProject(true);
    setError(null);
    projectsApi
      .get(projectIdNum)
      .then((p) => {
        if (!cancelled) setProject(p);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || '加载项目失败');
      })
      .finally(() => {
        if (!cancelled) setLoadingProject(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectIdNum]);

  // Load scenes for this project
  useEffect(() => {
    let cancelled = false;
    setLoadingScenes(true);
    scenesApi
      .list(projectIdNum)
      .then((res) => {
        if (!cancelled) {
          setScenes(res.items);
          // Auto-select scene from URL or first available
          if (res.items.length > 0) {
            const target = urlSceneId
              ? String(res.items.find(s => s.id === Number(urlSceneId))?.id || res.items[0].id)
              : String(res.items[0].id);
            setSelectedScene(target);
          }
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || '加载场景失败');
      })
      .finally(() => {
        if (!cancelled) setLoadingScenes(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectIdNum]);

  // Load storyboard when a scene is selected
  useEffect(() => {
    if (!selectedScene) {
      setStoryboard(null);
      setShots([]);
      return;
    }

    let cancelled = false;
    const sceneIdNum = Number(selectedScene);
    setLoadingStoryboard(true);
    storyboardsApi
      .get(sceneIdNum)
      .then((sb) => {
        if (!cancelled) setStoryboard(sb);
      })
      .catch(() => {
        // No storyboard exists yet for this scene
        if (!cancelled) setStoryboard(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingStoryboard(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedScene]);

  // Load shots when storyboard loads
  useEffect(() => {
    if (!storyboard) {
      setShots([]);
      return;
    }

    let cancelled = false;
    setLoadingShots(true);
    shotsApi
      .list(storyboard.id)
      .then((list) => {
        if (!cancelled) setShots(list);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || '加载镜头失败');
      })
      .finally(() => {
        if (!cancelled) setLoadingShots(false);
      });

    return () => {
      cancelled = true;
    };
  }, [storyboard]);

  // Auto-select and fetch shot detail from URL
  useEffect(() => {
    if (!urlShotId || !storyboard || shots.length === 0) return;
    const shotIdNum = Number(urlShotId);
    const found = shots.find((s) => s.id === shotIdNum);
    if (found) {
      // Fetch full detail via API
      shotsApi.get(storyboard.id, shotIdNum).then((detail) => {
        setSelectedShot(detail);
      }).catch(() => {
        setSelectedShot(found);
      });
    }
  }, [urlShotId, storyboard, shots]);

  // ---- Handlers ----

  const handleGenerateVideo = useCallback(async () => {
    if (!selectedShot || !storyboard) return;
    setGeneratingVideo(true);
    setVideoUrl(null);
    setError(null);
    try {
      const task = await tasksApi.triggerVideo({
        shot_id: selectedShot.id,
        quality: '1080p',
        sound: 'on',
        use_image_start: false,
      });
      setVideoTask(task);
      // Poll for completion
      const pollInterval = setInterval(async () => {
        try {
          const updated = await tasksApi.get(task.id);
          setVideoTask(updated);
          if (updated.status === 'success') {
            clearInterval(pollInterval);
            setGeneratingVideo(false);
            // Fetch the shot's assets to get the video URL
            if (updated.result_asset_id) {
              const refreshedShot = await shotsApi.get(storyboard.id, selectedShot.id);
              setSelectedShot(refreshedShot);
            }
          } else if (updated.status === 'failed') {
            clearInterval(pollInterval);
            setGeneratingVideo(false);
            setError(updated.error_message || '视频生成失败');
          }
        } catch {
          clearInterval(pollInterval);
          setGeneratingVideo(false);
        }
      }, 5000);
    } catch (err: unknown) {
      setGeneratingVideo(false);
      setError(err instanceof Error ? err.message : '视频生成请求失败');
    }
  }, [selectedShot, storyboard]);

  const handleAddShot = useCallback(async () => {
    if (!storyboard) return;
    try {
      const newShot = await shotsApi.create(storyboard.id, {
        shot_code: `SH${String(shots.length + 1).padStart(3, '0')}`,
        sequence: shots.length + 1,
        duration_sec: 3,
        status: 'draft',
      });
      setShots((prev) => [...prev, newShot]);
      setSelectedShot(newShot);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '创建镜头失败');
    }
  }, [storyboard, shots.length]);

  const handleUpdateShot = useCallback(
    async (shotId: number, data: Record<string, unknown>) => {
      if (!storyboard) return;
      try {
        const updated = await shotsApi.update(storyboard.id, shotId, data);
        setShots((prev) => prev.map((s) => (s.id === shotId ? updated : s)));
        if (selectedShot?.id === shotId) {
          setSelectedShot(updated);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : '更新镜头失败');
      }
    },
    [storyboard, selectedShot],
  );

  const handleDeleteShot = useCallback(
    async (shotId: number) => {
      if (!storyboard) return;
      try {
        await shotsApi.delete(storyboard.id, shotId);
        setShots((prev) => prev.filter((s) => s.id !== shotId));
        if (selectedShot?.id === shotId) {
          setSelectedShot(null);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : '删除镜头失败');
      }
    },
    [storyboard, selectedShot],
  );

  // ---- Derived data ----

  const currentScene = scenes.find((s) => String(s.id) === selectedScene);
  const totalDuration = shots.reduce((sum, shot) => sum + (shot.duration_sec || 0), 0);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Helper: extract camera fields from ShotResponse
  const getShotType = (shot: ShotResponse): string => {
    const comp = shot.composition as Record<string, string> | null;
    return comp?.shot_type || 'medium';
  };

  const getCameraAngle = (shot: ShotResponse): string => {
    const cam = shot.camera as Record<string, string> | null;
    return cam?.angle || 'eye_level';
  };

  const getShotDescription = (shot: ShotResponse): string => {
    return shot.image_prompt || shot.shot_code;
  };

  const getShotDialogue = (shot: ShotResponse): string | null => {
    return shot.dialogue_text || null;
  };

  const getShotLocation = (shot: ShotResponse): string => {
    const env = shot.environment as Record<string, string> | null;
    return env?.location || env?.location_id || '';
  };

  const getShotMood = (shot: ShotResponse): string => {
    const env = shot.environment as Record<string, string> | null;
    return env?.mood || '';
  };

  // ---- Loading / error guards ----

  if (loadingProject) {
    return (
      <AppLayout projectId={projectId} showSearch={false}>
        <div className="flex items-center justify-center h-full">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppLayout>
    );
  }

  if (error && !project) {
    return (
      <AppLayout projectId={projectId} showSearch={false}>
        <div className="flex flex-col items-center justify-center h-full gap-2">
          <p className="text-destructive">{error}</p>
          <Button
            variant="outline"
            onClick={() => window.location.reload()}
          >
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

  // ---- Main render ----

  return (
    <AppLayout
      projectId={projectId}
      showSearch={false}
      breadcrumbs={[
        { label: '项目', href: '/projects' },
        { label: project.name, href: `/projects/${projectId}` },
        { label: '分镜工作台' },
      ]}
    >
      {error && (
        <div className="bg-destructive/10 text-destructive px-4 py-2 text-sm">
          {error}
        </div>
      )}
      <ResizablePanelGroup direction="horizontal" className="h-[calc(100vh-4rem)]">
        {/* Left Panel - Shot List */}
        <ResizablePanel defaultSize={25} minSize={20} maxSize={35}>
          <div className="h-full flex flex-col bg-card border-r border-border">
            {/* Header */}
            <div className="p-4 border-b border-border space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-foreground">镜头列表</h2>
                <div className="flex items-center gap-1">
                  <Button
                    variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => setViewMode('grid')}
                  >
                    <Grid3X3 className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => setViewMode('list')}
                  >
                    <List className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>

              <Select value={selectedScene} onValueChange={setSelectedScene}>
                <SelectTrigger className="bg-secondary border-border">
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
                className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
                onClick={handleAddShot}
                disabled={!storyboard}
              >
                <Plus className="h-4 w-4 mr-2" />
                添加镜头
              </Button>
            </div>

            {/* Shot List */}
            <ScrollArea className="flex-1 min-h-0">
              {loadingShots ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className={`p-3 ${viewMode === 'grid' ? 'grid grid-cols-2 gap-2' : 'space-y-2'}`}>
                  {shots.map((shot) => (
                    <div
                      key={shot.id}
                      onClick={() => {
                        setSelectedShot(shot);
                        if (storyboard) {
                          shotsApi.get(storyboard.id, shot.id).then(setSelectedShot).catch(() => {});
                        }
                      }}
                      className={`group cursor-pointer rounded-lg border transition-all ${
                        selectedShot?.id === shot.id
                          ? 'border-primary bg-primary/5'
                          : 'border-border hover:border-primary/50 bg-secondary/30'
                      }`}
                    >
                      {viewMode === 'grid' ? (
                        <div className="p-2">
                          <div className="relative aspect-video rounded bg-muted mb-2">
                            <div className="absolute inset-0 flex items-center justify-center">
                              <Camera className="h-6 w-6 text-muted-foreground" />
                            </div>
                            <Badge className="absolute top-1 left-1 text-[10px] h-5 bg-black/60 border-0">
                              {shot.shot_code}
                            </Badge>
                          </div>
                          <p className="text-xs text-foreground truncate">{getShotDescription(shot)}</p>
                          <p className="text-[10px] text-muted-foreground">{shot.duration_sec}s</p>
                        </div>
                      ) : (
                        <div className="flex items-center gap-3 p-2">
                          <div className="flex items-center gap-2 shrink-0">
                            <GripVertical className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100" />
                            <div className="h-12 w-20 rounded bg-muted relative">
                              <div className="absolute inset-0 flex items-center justify-center">
                                <Camera className="h-4 w-4 text-muted-foreground" />
                              </div>
                            </div>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1 mb-0.5">
                              <span className="text-xs font-medium text-foreground">#{shot.sequence}</span>
                              <Badge className={`text-[10px] h-4 ${shotStatusColors[shot.status] || 'bg-muted text-muted-foreground'}`}>
                                {shot.status}
                              </Badge>
                            </div>
                            <p className="text-xs text-muted-foreground truncate">{getShotDescription(shot)}</p>
                          </div>
                          <span className="text-xs text-muted-foreground shrink-0">{shot.duration_sec}s</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>

            {/* Stats */}
            <div className="p-3 border-t border-border bg-secondary/30">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{shots.length} 个镜头</span>
                <span>总时长 {formatTime(totalDuration)}</span>
              </div>
            </div>
          </div>
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Center Panel - Preview & Timeline */}
        <ResizablePanel defaultSize={50}>
          <div className="h-full flex flex-col bg-background">
            {/* Preview Area */}
            <div className="flex-1 relative bg-black flex items-center justify-center">
              {selectedShot ? (
                <>
                  {selectedShot.video_url ? (
                    <video
                      src={selectedShot.video_url}
                      controls
                      className="max-w-full max-h-full object-contain"
                    />
                  ) : (
                    <div className="flex flex-col items-center justify-center text-white/60">
                      <Camera className="h-16 w-16 mb-4" />
                      <p>暂无预览</p>
                    </div>
                  )}

                  {/* Overlay Controls */}
                  <div className="absolute top-4 right-4 flex items-center gap-2">
                    <Button
                      variant="secondary"
                      size="icon"
                      className="h-8 w-8 bg-black/60 hover:bg-black/80"
                      onClick={() => setZoom(Math.max(50, zoom - 10))}
                    >
                      <ZoomOut className="h-4 w-4" />
                    </Button>
                    <span className="text-xs text-white bg-black/60 px-2 py-1 rounded">{zoom}%</span>
                    <Button
                      variant="secondary"
                      size="icon"
                      className="h-8 w-8 bg-black/60 hover:bg-black/80"
                      onClick={() => setZoom(Math.min(200, zoom + 10))}
                    >
                      <ZoomIn className="h-4 w-4" />
                    </Button>
                    <Button variant="secondary" size="icon" className="h-8 w-8 bg-black/60 hover:bg-black/80">
                      <Maximize2 className="h-4 w-4" />
                    </Button>
                  </div>

                  {/* Shot Info Overlay */}
                  <div className="absolute bottom-4 left-4 right-4">
                    <div className="bg-black/80 rounded-lg p-3 backdrop-blur-sm">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Badge className="bg-primary text-primary-foreground">
                            镜头 {selectedShot.shot_code}
                          </Badge>
                          <Badge variant="outline" className="border-white/30 text-white">
                            序列 {selectedShot.sequence}
                          </Badge>
                        </div>
                        <span className="text-xs text-white/80">{selectedShot.duration_sec}s</span>
                      </div>
                      <p className="text-sm text-white/80">{getShotDescription(selectedShot)}</p>
                    </div>
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center text-white/40">
                  <Film className="h-16 w-16 mb-4" />
                  <p>选择一个镜头进行预览</p>
                </div>
              )}
            </div>

            {/* Timeline */}
            <div className="h-32 border-t border-border bg-card">
              {/* Playback Controls */}
              <div className="flex items-center justify-between px-4 py-2 border-b border-border">
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
                  <Separator orientation="vertical" className="h-6 mx-2" />
                  <span className="text-sm text-muted-foreground font-mono">
                    {formatTime(currentTime)} / {formatTime(totalDuration)}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 border-border"
                    onClick={handleGenerateVideo}
                    disabled={!selectedShot || generatingVideo}
                  >
                    {generatingVideo ? (
                      <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                    ) : (
                      <Sparkles className="h-3.5 w-3.5 mr-1" />
                    )}
                    {generatingVideo
                      ? videoTask?.status === 'running'
                        ? `生成中 ${videoTask.progress}%`
                        : '排队中...'
                      : 'AI 生成'}
                  </Button>
                  <Button variant="outline" size="sm" className="h-7 border-border">
                    <Download className="h-3.5 w-3.5 mr-1" />
                    导出
                  </Button>
                </div>
              </div>

              {/* Timeline Track */}
              <div className="flex-1 px-4 py-2 overflow-x-auto">
                <div className="flex items-center gap-1 min-w-max">
                  {shots.map((shot) => {
                    const width = Math.max(80, (shot.duration_sec || 3) * 20);
                    const desc = getShotDescription(shot);
                    return (
                      <div
                        key={shot.id}
                        onClick={() => {
                          setSelectedShot(shot);
                          if (storyboard) {
                            shotsApi.get(storyboard.id, shot.id).then(setSelectedShot).catch(() => {});
                          }
                        }}
                        className={`h-16 rounded cursor-pointer transition-all relative group ${
                          selectedShot?.id === shot.id
                            ? 'ring-2 ring-primary'
                            : 'hover:ring-1 hover:ring-primary/50'
                        }`}
                        style={{ width: `${width}px` }}
                      >
                        <div className="absolute inset-0 bg-secondary rounded overflow-hidden">
                          <div className="absolute inset-0 flex items-center justify-center">
                            <Camera className="h-4 w-4 text-muted-foreground" />
                          </div>
                        </div>
                        <div className="absolute inset-0 flex flex-col justify-between p-1.5">
                          <div className="flex items-center justify-between">
                            <Badge className="text-[10px] h-4 bg-black/60 border-0 px-1">
                              {shot.shot_code}
                            </Badge>
                            <span className="text-[10px] text-white bg-black/60 px-1 rounded">
                              {shot.duration_sec}s
                            </span>
                          </div>
                          <p className="text-[10px] text-white truncate bg-black/40 px-1 rounded">
                            {desc.slice(0, 20)}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                  <Button
                    variant="outline"
                    className="h-16 w-20 border-dashed border-border hover:border-primary/50"
                    onClick={handleAddShot}
                    disabled={!storyboard}
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Right Panel - Properties */}
        <ResizablePanel defaultSize={25} minSize={20} maxSize={35}>
          <div className="h-full flex flex-col bg-card border-l border-border">
            <div className="p-4 border-b border-border">
              <h2 className="font-semibold text-foreground">属性面板</h2>
            </div>

            {selectedShot ? (
              <ShotDetailPanel
                key={selectedShot.id}
                shot={selectedShot}
                storyboardId={storyboard?.id}
                onSave={handleUpdateShot}
                onDelete={handleDeleteShot}
              />
            ) : (
              <div className="flex-1 flex items-center justify-center text-center p-6">
                <div>
                  <Eye className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">选择一个镜头查看属性</p>
                </div>
              </div>
            )}
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </AppLayout>
  );
}

// ---------------------------------------------------------------------------
// ShotDetailPanel — 属性面板（本地编辑 + 手动保存）
// ---------------------------------------------------------------------------

function ShotDetailPanel({
  shot,
  storyboardId,
  onSave,
  onDelete,
}: {
  shot: ShotResponse;
  storyboardId?: number;
  onSave: (shotId: number, data: Record<string, unknown>) => Promise<void>;
  onDelete: (shotId: number) => Promise<void>;
}) {
  // Local editing state (initialized from shot prop)
  const [form, setForm] = useState<Record<string, unknown>>({});
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  const initForm = (s: ShotResponse) => ({
    shot_code: s.shot_code,
    sequence: s.sequence,
    status: s.status || 'draft',
    image_prompt: s.image_prompt || '',
    negative_prompt: s.negative_prompt || '',
    style_preset: s.style_preset || '',
    dialogue_text: s.dialogue_text || '',
    dialogue_character: s.dialogue_character || '',
    dialogue_delivery: s.dialogue_delivery ? { ...s.dialogue_delivery } : {},
    duration_sec: s.duration_sec,
    camera: s.camera ? { ...s.camera } : {},
    composition: s.composition ? { ...s.composition } : {},
    environment: s.environment ? { ...s.environment } : {},
    characters_config: s.characters_config ? [...s.characters_config] : [],
    char_version_ids: s.char_version_ids ? [...s.char_version_ids] : [],
    sound_design: s.sound_design ? { ...s.sound_design } : {},
    transition_in: s.transition_in || 'cut',
    transition_out: s.transition_out || 'cut',
    transition_notes: s.transition_notes || '',
    dependencies: s.dependencies ? [...s.dependencies] : [],
  });

  // Sync from prop when shot changes
  useEffect(() => {
    setForm(initForm(shot));
    setDirty(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shot]);

  // Fetch full detail on mount
  useEffect(() => {
    if (!storyboardId || !shot.id) return;
    shotsApi.get(storyboardId, shot.id).then((detail) => {
      setForm(initForm(detail));
      setDirty(false);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storyboardId, shot.id]);

  const updateField = (key: string, value: unknown) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setDirty(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(shot.id, form);
      setDirty(false);
    } finally {
      setSaving(false);
    }
  };

  const camera = (form.camera as Record<string, string>) || {};
  const composition = (form.composition as Record<string, string>) || {};
  const environment = (form.environment as Record<string, string>) || {};
  const charactersConfig = (form.characters_config as Array<Record<string, string>>) || [];
  const soundDesign = (form.sound_design as Record<string, string | string[]>) || {};
  const dialogueDelivery = (form.dialogue_delivery as Record<string, string>) || {};

  return (
    <ScrollArea className="flex-1 min-h-0">
      <div className="p-4 space-y-6">
        {/* Basic Info */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">基本信息</h3>
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-muted-foreground">镜头编号</label>
                <Input
                  value={String(form.shot_code || '')}
                  onChange={(e) => updateField('shot_code', e.target.value)}
                  className="mt-1 bg-secondary border-border text-sm h-8"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">序列号</label>
                <Input
                  value={String(form.sequence || '')}
                  onChange={(e) => updateField('sequence', Number(e.target.value))}
                  className="mt-1 bg-secondary border-border text-sm h-8"
                  type="number"
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">状态</label>
              <Select
                value={String(form.status || 'draft')}
                onValueChange={(value) => updateField('status', value)}
              >
                <SelectTrigger className="mt-1 bg-secondary border-border text-xs h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="draft">草稿</SelectItem>
                  <SelectItem value="approved">已批准</SelectItem>
                  <SelectItem value="rendering">渲染中</SelectItem>
                  <SelectItem value="completed">已完成</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">风格预设</label>
              <Input
                value={String(form.style_preset || '')}
                onChange={(e) => updateField('style_preset', e.target.value)}
                className="mt-1 bg-secondary border-border text-sm h-8"
                placeholder="cinematic/dramatic/ethereal..."
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* Image Prompts */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">图像提示词</h3>
          <div className="space-y-2">
            <div>
              <label className="text-xs text-muted-foreground">图像提示词（英文）</label>
              <Textarea
                value={String(form.image_prompt || '')}
                onChange={(e) => updateField('image_prompt', e.target.value)}
                className="mt-1 bg-secondary border-border text-sm resize-none"
                rows={4}
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">负面提示词（英文）</label>
              <Input
                value={String(form.negative_prompt || '')}
                onChange={(e) => updateField('negative_prompt', e.target.value)}
                className="mt-1 bg-secondary border-border text-sm h-8"
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* Camera Settings */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">镜头设置</h3>
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-muted-foreground">景别</label>
                <Input
                  value={camera.shot_type || ''}
                  onChange={(e) =>
                    updateField('camera', { ...camera, shot_type: e.target.value })
                  }
                  className="mt-1 bg-secondary border-border text-xs h-8"
                  placeholder="MS/WS/CU..."
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">机位角度</label>
                <Input
                  value={camera.angle || ''}
                  onChange={(e) =>
                    updateField('camera', { ...camera, angle: e.target.value })
                  }
                  className="mt-1 bg-secondary border-border text-xs h-8"
                  placeholder="dutch/eye_level..."
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">镜头运动</label>
              <Input
                value={camera.movement || ''}
                onChange={(e) =>
                  updateField('camera', { ...camera, movement: e.target.value })
                }
                className="mt-1 bg-secondary border-border text-sm h-8"
                placeholder="handheld/pan/tilt..."
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">主体位置</label>
              <Input
                value={composition.subject_position || ''}
                onChange={(e) =>
                  updateField('composition', { ...composition, subject_position: e.target.value })
                }
                className="mt-1 bg-secondary border-border text-sm h-8"
                placeholder="right_third/center..."
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">时长 ({Number(form.duration_sec || 3)}s)</label>
              <Slider
                value={[Number(form.duration_sec || 3)]}
                max={30}
                min={1}
                step={0.5}
                className="mt-2"
                onValueChange={([val]) => updateField('duration_sec', val)}
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* Characters Config */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">角色配置</h3>
          <div className="space-y-2">
            {charactersConfig.length > 0 ? (
              charactersConfig.map((char, idx) => (
                <div key={idx} className="p-2 bg-secondary/50 rounded-lg space-y-2">
                  <div>
                    <label className="text-xs text-muted-foreground">动作</label>
                    <Textarea
                      value={char.action || ''}
                      onChange={(e) => {
                        const updated = [...charactersConfig];
                        updated[idx] = { ...updated[idx], action: e.target.value };
                        updateField('characters_config', updated);
                      }}
                      className="mt-1 bg-secondary border-border text-xs resize-none"
                      rows={2}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground">表情</label>
                    <Input
                      value={char.expression || ''}
                      onChange={(e) => {
                        const updated = [...charactersConfig];
                        updated[idx] = { ...updated[idx], expression: e.target.value };
                        updateField('characters_config', updated);
                      }}
                      className="mt-1 bg-secondary border-border text-xs h-8"
                    />
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-muted-foreground">无角色配置</p>
            )}
          </div>
        </div>

        <Separator />

        {/* Environment */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">场景环境</h3>
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-muted-foreground">时间</label>
                <Input
                  value={environment.time_of_day || ''}
                  onChange={(e) =>
                    updateField('environment', { ...environment, time_of_day: e.target.value })
                  }
                  className="mt-1 bg-secondary border-border text-xs h-8"
                  placeholder="morning/night..."
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">氛围</label>
                <Input
                  value={environment.atmosphere || environment.mood || ''}
                  onChange={(e) =>
                    updateField('environment', { ...environment, atmosphere: e.target.value })
                  }
                  className="mt-1 bg-secondary border-border text-xs h-8"
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">光照</label>
              <Input
                value={environment.lighting || ''}
                onChange={(e) =>
                  updateField('environment', { ...environment, lighting: e.target.value })
                }
                className="mt-1 bg-secondary border-border text-sm h-8"
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* Dialogue */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">对白</h3>
          <div className="space-y-2">
            <div>
              <label className="text-xs text-muted-foreground">说话角色</label>
              <Input
                value={String(form.dialogue_character || '')}
                onChange={(e) => updateField('dialogue_character', e.target.value)}
                className="mt-1 bg-secondary border-border text-sm h-8"
                placeholder="说话角色名"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">台词内容</label>
              <Textarea
                value={String(form.dialogue_text || '')}
                onChange={(e) => updateField('dialogue_text', e.target.value)}
                className="mt-1 bg-secondary border-border text-sm resize-none"
                rows={2}
                placeholder="台词内容"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">台词演绎</label>
              <Input
                value={dialogueDelivery.tone || dialogueDelivery.style || ''}
                onChange={(e) =>
                  updateField('dialogue_delivery', { ...dialogueDelivery, tone: e.target.value })
                }
                className="mt-1 bg-secondary border-border text-sm h-8"
                placeholder="语气/风格..."
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* Sound Design */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">音效设计</h3>
          <div className="space-y-2">
            <div>
              <label className="text-xs text-muted-foreground">环境音</label>
              <Input
                value={String(soundDesign.ambient || '')}
                onChange={(e) =>
                  updateField('sound_design', { ...soundDesign, ambient: e.target.value })
                }
                className="mt-1 bg-secondary border-border text-sm h-8"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">音效列表</label>
              <Textarea
                value={Array.isArray(soundDesign.sfx_list) ? soundDesign.sfx_list.join(', ') : ''}
                onChange={(e) =>
                  updateField('sound_design', { ...soundDesign, sfx_list: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })
                }
                className="mt-1 bg-secondary border-border text-sm resize-none"
                rows={2}
                placeholder="用逗号分隔多个音效"
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* Transitions */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">转场</h3>
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-muted-foreground">入画转场</label>
                <Input
                  value={String(form.transition_in || 'cut')}
                  onChange={(e) => updateField('transition_in', e.target.value)}
                  className="mt-1 bg-secondary border-border text-xs h-8"
                  placeholder="cut/fade/dissolve..."
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">出画转场</label>
                <Input
                  value={String(form.transition_out || 'cut')}
                  onChange={(e) => updateField('transition_out', e.target.value)}
                  className="mt-1 bg-secondary border-border text-xs h-8"
                  placeholder="cut/fade/dissolve..."
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">转场备注</label>
              <Input
                value={String(form.transition_notes || '')}
                onChange={(e) => updateField('transition_notes', e.target.value)}
                className="mt-1 bg-secondary border-border text-sm h-8"
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* Dependencies */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">依赖关系</h3>
          <div className="space-y-2">
            <div>
              <label className="text-xs text-muted-foreground">依赖的镜头ID</label>
              <Input
                value={Array.isArray(form.dependencies) ? form.dependencies.join(', ') : ''}
                onChange={(e) =>
                  updateField('dependencies', e.target.value.split(',').map(s => s.trim()).filter(Boolean))
                }
                className="mt-1 bg-secondary border-border text-sm h-8"
                placeholder="用逗号分隔镜头ID"
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* QC Info */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">质量检查</h3>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">角色一致性</span>
              <Badge variant={shot.qc_character_consistency ? 'default' : 'outline'} className="text-[10px] h-5">
                {shot.qc_character_consistency ? '通过' : '待检'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">光照匹配</span>
              <Badge variant={shot.qc_lighting_match ? 'default' : 'outline'} className="text-[10px] h-5">
                {shot.qc_lighting_match ? '通过' : '待检'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">动作连贯性</span>
              <Badge variant={shot.qc_action_continuity ? 'default' : 'outline'} className="text-[10px] h-5">
                {shot.qc_action_continuity ? '通过' : '待检'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">已批准</span>
              <Badge variant={shot.qc_approved ? 'default' : 'outline'} className="text-[10px] h-5">
                {shot.qc_approved ? '是' : '否'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">整体评分</span>
              <span className="text-foreground">{shot.qc_score ?? '-'}</span>
            </div>
          </div>
        </div>

        <Separator />

        {/* Timestamps */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">时间戳</h3>
          <div className="space-y-1 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">创建时间</span>
              <span className="text-foreground">{shot.created_at ? new Date(shot.created_at).toLocaleString('zh-CN') : '-'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">更新时间</span>
              <span className="text-foreground">{shot.updated_at ? new Date(shot.updated_at).toLocaleString('zh-CN') : '-'}</span>
            </div>
          </div>
        </div>

        <Separator />

        {/* Actions */}
        <div className="space-y-2">
          <Button
            className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
            disabled={!dirty}
            onClick={handleSave}
          >
            {saving ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Check className="h-4 w-4 mr-2" />
            )}
            {saving ? '保存中...' : '保存修改'}
          </Button>
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="outline"
              className="border-border"
              onClick={() => {
                if (storyboardId) {
                  shotsApi.get(storyboardId, shot.id).then((detail) => {
                    setForm(initForm(detail));
                    setDirty(false);
                  });
                }
              }}
            >
              <RefreshCw className="h-4 w-4 mr-1" />
              刷新
            </Button>
            <Button
              variant="outline"
              className="border-border text-destructive hover:text-destructive"
              onClick={() => onDelete(shot.id)}
            >
              <Trash2 className="h-4 w-4 mr-1" />
              删除
            </Button>
          </div>
        </div>
      </div>
    </ScrollArea>
  );
}
