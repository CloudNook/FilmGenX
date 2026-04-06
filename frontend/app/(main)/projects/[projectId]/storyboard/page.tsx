'use client';

import { use, useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import { AppLayout } from '@/components/layout';
import {
  projectsApi,
  scenesApi,
  storyboardsApi,
  shotsApi,
  shotGroupsApi,
  tasksApi,
  charactersApi,
  locationsApi,
  type ProjectResponse,
  type SceneResponse,
  type StoryboardResponse,
  type ShotResponse,
  type ShotGroupResponse,
  type CharacterResponse,
  type LocationResponse,
  type ImageRef,
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
  Group,
} from 'lucide-react';
import { ImagePickerDialog } from '@/components/shots/ImagePickerDialog';

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
  const [shotGroups, setShotGroups] = useState<ShotGroupResponse[]>([]);
  const [selectedShotIds, setSelectedShotIds] = useState<Set<number>>(new Set());
  const [selectedGroup, setSelectedGroup] = useState<ShotGroupResponse | null>(null);
  const [generatingGroupVideo, setGeneratingGroupVideo] = useState(false);
  const [imagePickerOpen, setImagePickerOpen] = useState(false);

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
  const [currentTime, setCurrentTime] = useState(0);
  const [zoom, setZoom] = useState(100);
  const resolvedUrlShotKeyRef = useRef<string | null>(null);
  const selectedShotRequestIdRef = useRef(0);

  const getGroupForShot = useCallback(
    (shot: Pick<ShotResponse, 'id' | 'shot_group_id'> | null) => {
      if (!shot) return null;
      return (
        shotGroups.find((group) =>
          (shot.shot_group_id != null && group.id === shot.shot_group_id) ||
          group.shots?.some((member) => member.id === shot.id),
        ) || null
      );
    },
    [shotGroups],
  );

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
      setSelectedShot(null);
      resolvedUrlShotKeyRef.current = null;
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
      setSelectedShot(null);
      resolvedUrlShotKeyRef.current = null;
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

  useEffect(() => {
    if (selectedShot) {
      const relatedGroup = getGroupForShot(selectedShot);
      setSelectedGroup((prev) => (prev?.id === relatedGroup?.id ? prev : relatedGroup));
      return;
    }

    if (selectedGroup) {
      const refreshedGroup = shotGroups.find((group) => group.id === selectedGroup.id) || null;
      setSelectedGroup((prev) => (prev?.id === refreshedGroup?.id ? prev : refreshedGroup));
    }
  }, [selectedShot, selectedGroup, shotGroups, getGroupForShot]);

  // Load shot groups when storyboard loads
  useEffect(() => {
    if (!storyboard) {
      setShotGroups([]);
      setSelectedGroup(null);
      return;
    }
    let cancelled = false;
    shotGroupsApi
      .list(storyboard.id)
      .then((groups) => {
        if (!cancelled) setShotGroups(groups);
      })
      .catch(() => {
        if (!cancelled) setShotGroups([]);
      });
    return () => {
      cancelled = true;
    };
  }, [storyboard]);

  // Auto-select and fetch shot detail from URL
  useEffect(() => {
    if (!urlShotId || !storyboard || shots.length === 0) return;
    const resolveKey = `${storyboard.id}:${urlShotId}`;
    if (resolvedUrlShotKeyRef.current === resolveKey) return;
    const shotIdNum = Number(urlShotId);
    const found = shots.find((s) => s.id === shotIdNum);
    if (found) {
      const requestId = selectedShotRequestIdRef.current + 1;
      selectedShotRequestIdRef.current = requestId;
      // Fetch full detail via API
      shotsApi
        .get(storyboard.id, shotIdNum)
        .then((detail) => {
          if (selectedShotRequestIdRef.current !== requestId) return;
          setSelectedShot(detail);
          setShots((prev) => prev.map((item) => (item.id === detail.id ? detail : item)));
          resolvedUrlShotKeyRef.current = resolveKey;
        })
        .catch(() => {
          if (selectedShotRequestIdRef.current !== requestId) return;
          setSelectedShot(found);
          resolvedUrlShotKeyRef.current = resolveKey;
        });
    }
  }, [urlShotId, storyboard, shots]);

  const selectShotWithDetail = useCallback(
    (baseShot: ShotResponse, onResolved?: (detail: ShotResponse) => void, onFallback?: () => void) => {
      setSelectedShot(baseShot);
      if (!storyboard) {
        onFallback?.();
        return;
      }

      const requestId = selectedShotRequestIdRef.current + 1;
      selectedShotRequestIdRef.current = requestId;

      shotsApi
        .get(storyboard.id, baseShot.id)
        .then((detail) => {
          if (selectedShotRequestIdRef.current !== requestId) return;
          setSelectedShot(detail);
          setShots((prev) => prev.map((item) => (item.id === detail.id ? detail : item)));
          onResolved?.(detail);
        })
        .catch(() => {
          if (selectedShotRequestIdRef.current !== requestId) return;
          setSelectedShot(baseShot);
          onFallback?.();
        });
    },
    [storyboard],
  );

  // ---- Handlers ----

  const runMultiShotGeneration = useCallback(
    async (group: ShotGroupResponse, focusShotId?: number) => {
      if (!storyboard) return;

      setGeneratingGroupVideo(true);
      setError(null);

      try {
        await tasksApi.triggerMultiShotVideo({
          shot_group_id: group.id,
          quality: '1080p',
          sound: 'on',
        });
        // Immediately refresh group & shots to get 'generating' status
        const [refreshedGroup, refreshedShots] = await Promise.all([
          shotGroupsApi.get(storyboard.id, group.id),
          shotsApi.list(storyboard.id),
        ]);
        setShotGroups((prev) => prev.map((g) => (g.id === refreshedGroup.id ? refreshedGroup : g)));
        setSelectedGroup(refreshedGroup);
        setShots(refreshedShots);
        if (focusShotId) {
          const refreshedShot = refreshedShots.find((s) => s.id === focusShotId);
          if (refreshedShot) {
            setSelectedShot(refreshedShot);
          }
        }
      } catch (err: unknown) {
        setGeneratingGroupVideo(false);
        setError(err instanceof Error ? err.message : '组视频生成请求失败');
      }
    },
    [storyboard],
  );

  const handleGenerateVideo = useCallback(async () => {
    if (!selectedShot || !storyboard) return;

    const shotGroup = getGroupForShot(selectedShot);
    if (shotGroup) {
      await runMultiShotGeneration(shotGroup, selectedShot.id);
      return;
    }

    setGeneratingVideo(true);
    setError(null);
    try {
      await tasksApi.triggerVideo({
        shot_id: selectedShot.id,
        quality: '1080p',
        sound: 'on',
        use_image_start: false,
      });
      // Immediately refresh shot to get 'generating' status
      const refreshedShot = await shotsApi.get(storyboard.id, selectedShot.id);
      setSelectedShot(refreshedShot);
      setShots((prev) => prev.map((s) => (s.id === refreshedShot.id ? refreshedShot : s)));
    } catch (err: unknown) {
      setGeneratingVideo(false);
      setError(err instanceof Error ? err.message : '视频生成请求失败');
    }
  }, [getGroupForShot, runMultiShotGeneration, selectedShot, storyboard]);

  // Poll shot detail while status is 'generating'
  useEffect(() => {
    if (!selectedShot || !storyboard || selectedShot.status !== 'generating') {
      return;
    }
    const interval = setInterval(async () => {
      try {
        const detail = await shotsApi.get(storyboard.id, selectedShot.id);
        setSelectedShot((prev) => (prev?.id === detail.id ? detail : prev));
        setShots((prev) => prev.map((s) => (s.id === detail.id ? detail : s)));
        if (detail.status !== 'generating') {
          setGeneratingVideo(false);
          if (detail.status === 'draft') {
            setError('视频生成失败');
          }
        }
      } catch {
        // ignore poll errors
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [selectedShot?.id, selectedShot?.status, storyboard]);

  // Toggle shot selection for grouping
  const toggleShotSelection = useCallback((shotId: number) => {
    setSelectedShotIds((prev) => {
      const next = new Set(prev);
      if (next.has(shotId)) {
        next.delete(shotId);
      } else {
        next.add(shotId);
      }
      return next;
    });
  }, []);

  // Create group from selected shots
  const handleCreateGroup = useCallback(async () => {
    if (!storyboard || selectedShotIds.size < 2) return;
    const selectedShots = shots.filter((s) => selectedShotIds.has(s.id));
    const totalDuration = selectedShots.reduce((sum, s) => sum + (s.duration_sec || 3), 0);

    if (selectedShots.length > 6) {
      setError('每组最多 6 个分镜');
      return;
    }
    if (totalDuration > 15) {
      setError(`总时长 ${totalDuration.toFixed(1)}s 超过 15 秒限制`);
      return;
    }

    try {
      const groupCode = `G${String(shotGroups.length + 1).padStart(3, '0')}`;
      const group = await shotGroupsApi.create(storyboard.id, {
        group_code: groupCode,
        shot_ids: Array.from(selectedShotIds),
      });
      setShotGroups((prev) => [...prev, group]);
      setSelectedShotIds(new Set());
      // Refresh shots to get updated shot_group_id
      const refreshed = await shotsApi.list(storyboard.id);
      setShots(refreshed);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '创建分镜组失败');
    }
  }, [storyboard, shots, selectedShotIds, shotGroups.length]);

  // Generate video for a shot group
  const handleGenerateGroupVideo = useCallback(async () => {
    if (!selectedGroup || !storyboard) return;
    await runMultiShotGeneration(selectedGroup, selectedShot?.id);
  }, [runMultiShotGeneration, selectedGroup, selectedShot?.id, storyboard]);

  // Delete a shot group
  const handleDeleteGroup = useCallback(async (groupId: number) => {
    if (!storyboard) return;
    try {
      await shotGroupsApi.delete(storyboard.id, groupId);
      setShotGroups((prev) => prev.filter((g) => g.id !== groupId));
      if (selectedGroup?.id === groupId) {
        setSelectedGroup(null);
      }
      // Refresh shots
      const refreshed = await shotsApi.list(storyboard.id);
      setShots(refreshed);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '删除分镜组失败');
    }
  }, [storyboard, selectedGroup]);

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

  const selectedShotGroup = selectedShot ? getGroupForShot(selectedShot) : null;
  const activeGroup = selectedGroup || selectedShotGroup;

  // Save image picker selections to shot group
  const handleImagePickerConfirm = useCallback(
    async (refs: ImageRef[], imgStartUrl: string | null) => {
      if (!storyboard || !selectedShot) return;
      try {
        let group = activeGroup;

        // If no group exists, auto-create a single-shot group
        if (!group) {
          const groupCode = `G${String(shotGroups.length + 1).padStart(3, '0')}`;
          group = await shotGroupsApi.create(storyboard.id, {
            group_code: groupCode,
            shot_ids: [selectedShot.id],
          });
          setShotGroups((prev) => [...prev, group!]);
          setSelectedGroup(group);
          const refreshed = await shotsApi.list(storyboard.id);
          setShots(refreshed);
        }

        const updatedGroup = await shotGroupsApi.update(
          storyboard.id,
          group.id,
          {
            image_references: refs,
            image_start_url: imgStartUrl,
          },
        );
        setShotGroups((prev) =>
          prev.map((g) => (g.id === updatedGroup.id ? updatedGroup : g)),
        );
        setSelectedGroup(updatedGroup);
        setImagePickerOpen(false);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : '保存图片关联失败');
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [storyboard, selectedShot?.id, activeGroup, shotGroups.length],
  );

  // Derive generating state from API status (not simulated)
  const isShotGenerating = selectedShot?.status === 'generating';
  const isGroupGenerating = activeGroup?.status === 'generating';
  const isAnyGenerating = isShotGenerating || isGroupGenerating;

  // Poll group detail while status is 'generating'
  useEffect(() => {
    if (!activeGroup || !storyboard || activeGroup.status !== 'generating') {
      return;
    }
    const interval = setInterval(async () => {
      try {
        const [refreshedGroup, refreshedShots] = await Promise.all([
          shotGroupsApi.get(storyboard.id, activeGroup.id),
          shotsApi.list(storyboard.id),
        ]);
        setShotGroups((prev) => prev.map((g) => (g.id === refreshedGroup.id ? refreshedGroup : g)));
        setSelectedGroup((prev) => (prev?.id === refreshedGroup.id ? refreshedGroup : prev));
        setShots(refreshedShots);
        if (refreshedGroup.status !== 'generating') {
          setGeneratingGroupVideo(false);
          if (refreshedGroup.status === 'draft') {
            setError('组视频生成失败');
          }
        }
      } catch {
        // ignore poll errors
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [activeGroup?.id, activeGroup?.status, storyboard]);

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

              <div className="flex gap-2">
                  <Button
                    className="flex-1 bg-primary text-primary-foreground hover:bg-primary/90"
                    onClick={handleAddShot}
                    disabled={!storyboard}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    添加镜头
                  </Button>
                  {selectedShotIds.size >= 2 && selectedShotIds.size <= 6 && (
                    <Button
                      variant="outline"
                      className="shrink-0"
                      onClick={handleCreateGroup}
                    >
                      <Group className="h-4 w-4 mr-1" />
                      创建组
                    </Button>
                  )}
                </div>
            </div>

            {/* Shot List */}
            <div className="flex-1 min-h-0 overflow-y-auto">
              {loadingShots ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className={`p-3 ${viewMode === 'grid' ? 'grid grid-cols-2 gap-2' : 'space-y-2'}`}>
                  {/* Group indicators */}
                  {shotGroups.map((group) => (
                    <div
                      key={`group-${group.id}`}
                      className={`col-span-2 flex items-center gap-2 px-2 py-1 rounded-md cursor-pointer transition-all ${
                        selectedGroup?.id === group.id
                          ? 'bg-primary/10 border border-primary/30'
                          : 'bg-muted/50 border border-border hover:border-primary/20'
                      }`}
                      onClick={() => {
                        setSelectedGroup(group);
                        setSelectedShot(null);
                      }}
                    >
                      <Group className="h-3.5 w-3.5 text-primary shrink-0" />
                      <span className="text-xs font-medium text-foreground truncate">
                        {group.name || group.group_code}
                      </span>
                      {(group.image_references?.length || 0) > 0 && (
                        <Badge variant="outline" className="text-[9px] h-4 px-1 shrink-0">
                          <Camera className="h-2.5 w-2.5 mr-0.5" />
                          {group.image_references.length}
                        </Badge>
                      )}
                      <span className="text-[10px] text-muted-foreground ml-auto shrink-0">
                        {group.shots?.length || 0}镜头 · {(group.total_duration_sec || 0).toFixed(1)}s
                      </span>
                      <Badge className={`text-[9px] h-4 px-1 ${
                        group.status === 'review' ? 'bg-success/20 text-success' :
                        group.status === 'generating' ? 'bg-warning/20 text-warning' :
                        'bg-muted text-muted-foreground'
                      }`}>
                        {group.status}
                      </Badge>
                    </div>
                  ))}

                  {shots.map((shot) => {
                    // Find group this shot belongs to
                    const shotGroup = shotGroups.find((g) =>
                      g.shots?.some((s) => s.id === shot.id)
                    );
                    const groupColor = shotGroup
                      ? ['bg-blue-500/10 border-blue-500/30', 'bg-emerald-500/10 border-emerald-500/30', 'bg-amber-500/10 border-amber-500/30', 'bg-purple-500/10 border-purple-500/30'][
                          shotGroups.indexOf(shotGroup) % 4
                        ]
                      : '';

                    return (
                    <div
                      key={shot.id}
                      onClick={(e) => {
                        if (e.shiftKey) {
                          toggleShotSelection(shot.id);
                        } else {
                          selectShotWithDetail(shot);
                          setSelectedShotIds(new Set());
                        }
                      }}
                      className={`group cursor-pointer rounded-lg border transition-all ${
                        selectedShotIds.has(shot.id)
                          ? 'border-primary bg-primary/10 ring-1 ring-primary/30'
                          : selectedShot?.id === shot.id
                          ? 'border-primary bg-primary/5'
                          : groupColor
                          ? groupColor
                          : 'border-border hover:border-primary/50 bg-secondary/30'
                      }`}
                    >
                      {viewMode === 'grid' ? (
                        <div className="flex h-[172px] flex-col p-2">
                          <div className="mb-2 flex items-center justify-between gap-2">
                            <Badge variant="outline" className="text-[10px] h-5">
                              {shot.shot_code}
                            </Badge>
                            <span className="text-[10px] text-muted-foreground">{shot.duration_sec}s</span>
                          </div>
                          <div className="relative mb-2 aspect-video overflow-hidden rounded bg-muted/60">
                            {shot.video_url ? (
                              <video
                                src={shot.video_url}
                                className="h-full w-full object-cover"
                                muted
                                playsInline
                                preload="metadata"
                              />
                            ) : null}
                          </div>
                          <p className="line-clamp-2 text-xs text-foreground">{getShotDescription(shot)}</p>
                        </div>
                      ) : (
                        <div className="flex h-[72px] items-center gap-3 p-2">
                          <div className="flex items-center gap-2 shrink-0">
                            <GripVertical className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100" />
                            <div className="h-12 w-20 overflow-hidden rounded bg-muted/60">
                              {shot.video_url ? (
                                <video
                                  src={shot.video_url}
                                  className="h-full w-full object-cover"
                                  muted
                                  playsInline
                                  preload="metadata"
                                />
                              ) : null}
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
                    );
                  })}
                </div>
              )}
            </div>

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
                      key={selectedShot.id}
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
                  {activeGroup && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 border-border"
                        onClick={() => setImagePickerOpen(true)}
                      >
                        <Camera className="h-3.5 w-3.5 mr-1" />
                        参考图
                        {(activeGroup.image_references?.length || 0) > 0
                          ? ` (${activeGroup.image_references.length})`
                          : ''}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 border-primary/50 text-primary hover:bg-primary/10"
                        onClick={handleGenerateGroupVideo}
                        disabled={isAnyGenerating}
                      >
                        {isGroupGenerating ? (
                          <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                        ) : (
                          <Group className="h-3.5 w-3.5 mr-1" />
                        )}
                        {isGroupGenerating
                          ? '生成中...'
                          : activeGroup.status === 'review'
                            ? `重新生成 (${activeGroup.shots?.length || 0}镜头)`
                            : `Kling Multi-Shot (${activeGroup.shots?.length || 0}镜头)`}
                      </Button>
                    </>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 border-border"
                    onClick={handleGenerateVideo}
                    disabled={!selectedShot || isAnyGenerating}
                  >
                    {isShotGenerating ? (
                      <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                    ) : (
                      <>
                        {selectedShotGroup ? (
                          <Group className="h-3.5 w-3.5 mr-1" />
                        ) : (
                          <Sparkles className="h-3.5 w-3.5 mr-1" />
                        )}
                      </>
                    )}
                    {selectedShotGroup
                      ? isGroupGenerating
                        ? '组生成中...'
                        : selectedShotGroup.status === 'review'
                          ? `重新生成 ${selectedShotGroup.group_code}`
                          : `按组生成 ${selectedShotGroup.group_code}`
                      : isShotGenerating
                        ? '生成中...'
                        : selectedShot?.status === 'review'
                          ? '重新生成'
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
                          selectShotWithDetail(shot);
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
                projectId={projectIdNum}
                storyboardId={storyboard?.id}
                activeGroup={activeGroup}
                onOpenImagePicker={() => setImagePickerOpen(true)}
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

      {/* Image Picker Dialog for ShotGroup */}
      <ImagePickerDialog
        open={imagePickerOpen}
        onOpenChange={setImagePickerOpen}
        projectId={projectIdNum}
        existingRefs={activeGroup?.image_references || []}
        existingImageStartUrl={activeGroup?.image_start_url || null}
        onConfirm={handleImagePickerConfirm}
      />
    </AppLayout>
  );
}

// ---------------------------------------------------------------------------
// ShotDetailPanel — 属性面板（本地编辑 + 手动保存）
// ---------------------------------------------------------------------------

function ShotDetailPanel({
  shot,
  projectId,
  storyboardId,
  activeGroup,
  onOpenImagePicker,
  onSave,
  onDelete,
}: {
  shot: ShotResponse;
  projectId: number;
  storyboardId?: number;
  activeGroup?: ShotGroupResponse | null;
  onOpenImagePicker?: () => void;
  onSave: (shotId: number, data: Record<string, unknown>) => Promise<void>;
  onDelete: (shotId: number) => Promise<void>;
}) {
  // Local editing state (initialized from shot prop)
  const [form, setForm] = useState<Record<string, unknown>>({});
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  // Character & location data for pickers
  const [characters, setCharacters] = useState<CharacterResponse[]>([]);
  const [locations, setLocations] = useState<LocationResponse[]>([]);
  const [loadingChars, setLoadingChars] = useState(false);
  const [loadingLocs, setLoadingLocs] = useState(false);
  const [locationVersionMap, setLocationVersionMap] = useState<Record<number, { locationId: number; locationName: string; versionLabel: string }>>({});

  // Map: charVersionId → { charId, charName, versionLabel }
  type CharVersionInfo = { charId: number; charName: string; versionLabel: string };
  const [charVersionMap, setCharVersionMap] = useState<Record<number, CharVersionInfo>>({});

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

  // Fetch characters for picker
  useEffect(() => {
    if (!projectId) return;
    setLoadingChars(true);
    charactersApi.list(projectId, 1, 100).then(async (page) => {
      setCharacters(page.items);
      // Fetch details for each character to get versions
      const versionMap: Record<number, CharVersionInfo> = {};
      await Promise.allSettled(
        page.items.map((char) =>
          charactersApi.get(projectId, char.id).then((detail) => {
            detail.versions.forEach((v) => {
              versionMap[v.id] = {
                charId: char.id,
                charName: char.name,
                versionLabel: v.label || v.version_code,
              };
            });
          }),
        ),
      );
      setCharVersionMap(versionMap);
    }).catch(() => {
      // ignore errors silently
    }).finally(() => setLoadingChars(false));
  }, [projectId]);

  // Fetch locations for picker
  useEffect(() => {
    if (!projectId) return;
    setLoadingLocs(true);
    locationsApi.listBrief(projectId).then((locs) => {
      setLocations(locs);
    }).catch(() => {
      // ignore errors silently
    }).finally(() => setLoadingLocs(false));
  }, [projectId]);

  // Add a character version to the shot
  const handleAddCharacter = (charVersionId: number, charName: string, versionLabel: string) => {
    const currentIds = (form.char_version_ids as number[]) || [];
    if (currentIds.includes(charVersionId)) return; // already added

    const newIds = [...currentIds, charVersionId];
    const newConfig = [
      ...((form.characters_config as Array<Record<string, unknown>>) || []),
      { char_version_id: charVersionId, action: '', expression: '' },
    ];
    updateField('char_version_ids', newIds);
    updateField('characters_config', newConfig);
  };

  // Remove a character version from the shot
  const handleRemoveCharacter = (charVersionId: number) => {
    const newIds = ((form.char_version_ids as number[]) || []).filter((id) => id !== charVersionId);
    const newConfig = ((form.characters_config as Array<Record<string, unknown>>) || []).filter(
      (c) => c.char_version_id !== charVersionId,
    );
    updateField('char_version_ids', newIds);
    updateField('characters_config', newConfig);
  };

  // Change location
  const handleLocationChange = async (locationId: number | null) => {
    const env = (form.environment as Record<string, unknown>) || {};

    if (locationId == null) {
      updateField('environment', { ...env, location_id: null, location_version_id: null });
      return;
    }

    // Fetch location details to get versions
    try {
      const detail = await locationsApi.get(projectId, locationId);
      const newMap = { ...locationVersionMap };

      // Build version map for this location
      const defaultVersionId = detail.default_version?.id ?? detail.versions?.[0]?.id ?? null;
      for (const v of detail.versions || []) {
        newMap[v.id] = {
          locationId: detail.id,
          locationName: detail.name,
          versionLabel: v.label || v.version_code,
        };
      }
      setLocationVersionMap(newMap);

      updateField('environment', {
        ...env,
        location_id: locationId,
        // Auto-select default version
        location_version_id: defaultVersionId,
      });
    } catch {
      updateField('environment', { ...env, location_id: locationId, location_version_id: null });
    }
  };

  // Change location version
  const handleLocationVersionChange = (versionId: number | null) => {
    const env = (form.environment as Record<string, unknown>) || {};
    updateField('environment', { ...env, location_version_id: versionId });
  };

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
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-foreground">角色关联</h3>
            {loadingChars ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
            ) : (
              <Select
                onValueChange={(val) => {
                  const [charId, versionId] = val.split(':');
                  handleAddCharacter(Number(versionId), '', '');
                }}
              >
                <SelectTrigger className="h-7 text-xs w-auto min-w-[80px]">
                  <Plus className="h-3 w-3 mr-1" />
                  <SelectValue placeholder="添加角色" />
                </SelectTrigger>
                <SelectContent>
                  {/* Grouped by character — show one version per character as option */}
                  {(() => {
                    const seen = new Set<number>();
                    return characters
                      .filter((char) => {
                        if (seen.has(char.id)) return false;
                        seen.add(char.id);
                        return true;
                      })
                      .map((char) => {
                        const versionId = Object.keys(charVersionMap).find(
                          (k) => charVersionMap[Number(k)]?.charId === char.id,
                        );
                        const info = versionId ? charVersionMap[Number(versionId)] : undefined;
                        return (
                          <SelectItem
                            key={`char-${char.id}`}
                            value={`${char.id}:${versionId ?? 0}`}
                            disabled={!versionId}
                          >
                            {char.name}
                            {info ? ` — ${info.versionLabel}` : ''}
                          </SelectItem>
                        );
                      });
                  })()}
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Selected character badges */}
          {(form.char_version_ids as number[])?.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {(form.char_version_ids as number[]).map((versionId) => {
                const info = charVersionMap[versionId];
                return (
                  <Badge
                    key={versionId}
                    variant="outline"
                    className="flex items-center gap-1 pr-1 pl-2 py-0.5 text-xs cursor-pointer hover:bg-destructive/10"
                    onClick={() => handleRemoveCharacter(versionId)}
                    title="点击移除"
                  >
                    {info ? `${info.charName} — ${info.versionLabel}` : `版本 #${versionId}`}
                    <X className="h-3 w-3 text-muted-foreground hover:text-destructive" />
                  </Badge>
                );
              })}
            </div>
          )}

          {/* Action/expression fields per character */}
          <div className="space-y-2">
            {charactersConfig.length > 0 ? (
              charactersConfig.map((char, idx) => {
                const info = charVersionMap[char.char_version_id as unknown as number];
                return (
                  <div key={idx} className="p-2 bg-secondary/50 rounded-lg space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-foreground">
                        {info ? `${info.charName} — ${info.versionLabel}` : `角色版本 #${char.char_version_id}`}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleRemoveCharacter(char.char_version_id as unknown as number)}
                        className="text-xs text-muted-foreground hover:text-destructive"
                      >
                        移除
                      </button>
                    </div>
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
                );
              })
            ) : (
              <p className="text-xs text-muted-foreground">点击右上角「+」添加角色关联</p>
            )}
          </div>
        </div>

        <Separator />

        {/* Reference Images (for image-to-video) */}
        {onOpenImagePicker && (
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-foreground">参考图</h3>
            <div className="space-y-2">
              {activeGroup ? (
                <>
                  <p className="text-xs text-muted-foreground">
                    为所属分镜组「{activeGroup.name || activeGroup.group_code}」选择角色图和场景图，用于 image-to-video 生成。
                  </p>
                  {(activeGroup.image_references?.length || 0) > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {activeGroup.image_references.map((ref, i) => (
                        <div key={`ref-${i}`} className="relative w-10 h-10 rounded overflow-hidden border border-border">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img src={ref.url} alt={ref.label} className="w-full h-full object-cover" />
                          <div className={`absolute bottom-0 left-0 right-0 text-[8px] text-center ${
                            ref.char_version_id ? 'bg-primary/80 text-primary-foreground' : 'bg-emerald-500/80 text-white'
                          }`}>
                            {ref.char_version_id ? '角色' : '场景'}
                          </div>
                        </div>
                      ))}
                      {activeGroup.image_start_url && (
                        <div className="relative w-10 h-10 rounded overflow-hidden border border-amber-500/50">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img src={activeGroup.image_start_url} alt="首帧" className="w-full h-full object-cover" />
                          <div className="absolute bottom-0 left-0 right-0 bg-amber-500/80 text-[8px] text-white text-center">首帧</div>
                        </div>
                      )}
                    </div>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full h-7 border-border"
                    onClick={onOpenImagePicker}
                  >
                    <Camera className="h-3.5 w-3.5 mr-1" />
                    {activeGroup.image_references?.length
                      ? '修改参考图'
                      : '选择参考图'}
                  </Button>
                </>
              ) : (
                <>
                  <p className="text-xs text-muted-foreground">
                    选择角色图和场景图作为参考，用于 image-to-video 生成。
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full h-7 border-border"
                    onClick={onOpenImagePicker}
                  >
                    <Camera className="h-3.5 w-3.5 mr-1" />
                    选择参考图
                  </Button>
                </>
              )}
            </div>
          </div>
        )}

        <Separator />

        {/* Environment */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">场景环境</h3>
          <div className="space-y-2">
            {/* Location picker */}
            <div>
              <label className="text-xs text-muted-foreground">场景地点</label>
              <Select
                value={String(environment.location_id || '')}
                onValueChange={(val) => handleLocationChange(val === '__none__' ? null : Number(val))}
              >
                <SelectTrigger className="mt-1 bg-secondary border-border text-xs h-8">
                  <SelectValue placeholder="选择场景地点（可选）" />
                </SelectTrigger>
                <SelectContent>
                  {loadingLocs ? (
                    <div className="flex items-center justify-center py-2">
                      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                    </div>
                  ) : (
                    <>
                      <SelectItem value="__none__">（无）</SelectItem>
                      {locations.map((loc) => (
                        <SelectItem key={loc.id} value={String(loc.id)}>
                          {loc.name}
                        </SelectItem>
                      ))}
                    </>
                  )}
                </SelectContent>
              </Select>
            </div>

            {/* Location version picker — shown when a location is selected */}
            {environment.location_id && (
              <div>
                <label className="text-xs text-muted-foreground">场景版本</label>
                <Select
                  value={String(environment.location_version_id || '')}
                  onValueChange={(val) => handleLocationVersionChange(val ? Number(val) : null)}
                >
                  <SelectTrigger className="mt-1 bg-secondary border-border text-xs h-8">
                    <SelectValue placeholder="选择场景版本（可选）" />
                  </SelectTrigger>
                  <SelectContent>
                    {/* Dynamically show versions for selected location */}
                    {(() => {
                      const selectedLocId = environment.location_id as unknown as number;
                      const relevantVersions = Object.entries(locationVersionMap)
                        .filter(([, info]) => info.locationId === selectedLocId)
                        .map(([vid, info]) => ({ id: Number(vid), ...info }));

                      if (relevantVersions.length === 0) {
                        return <SelectItem value="__none__" disabled>加载中...</SelectItem>;
                      }
                      return (
                        <>
                          <SelectItem value="__none__">（无）</SelectItem>
                          {relevantVersions.map((v) => (
                            <SelectItem key={v.id} value={String(v.id)}>
                              {v.versionLabel}
                            </SelectItem>
                          ))}
                        </>
                      );
                    })()}
                  </SelectContent>
                </Select>
                {environment.location_version_id && (() => {
                  const info = locationVersionMap[environment.location_version_id as unknown as number];
                  return info ? (
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                      已关联：{info.locationName} · {info.versionLabel}
                    </p>
                  ) : null;
                })()}
              </div>
            )}
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
