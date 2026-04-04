'use client';

import { use, useState } from 'react';
import { AppLayout } from '@/components/layout';
import {
  getProjectById,
  getEpisodesByProjectId,
  getShotsByEpisodeId,
  shots as allShots,
} from '@/lib/mock-data';
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
} from 'lucide-react';
import type { Shot, Episode } from '@/lib/types';

const shotStatusColors: Record<Shot['status'], string> = {
  draft: 'bg-muted text-muted-foreground',
  approved: 'bg-info/20 text-info',
  rendering: 'bg-warning/20 text-warning',
  completed: 'bg-success/20 text-success',
};

const shotTypes = [
  { value: 'extreme_wide', label: '大远景' },
  { value: 'wide', label: '远景' },
  { value: 'medium_wide', label: '中远景' },
  { value: 'medium', label: '中景' },
  { value: 'medium_close', label: '中近景' },
  { value: 'close_up', label: '特写' },
  { value: 'extreme_close_up', label: '大特写' },
];

const cameraAngles = [
  { value: 'eye_level', label: '平视' },
  { value: 'high_angle', label: '俯视' },
  { value: 'low_angle', label: '仰视' },
  { value: 'birds_eye', label: '鸟瞰' },
  { value: 'dutch_angle', label: '倾斜' },
  { value: 'over_shoulder', label: '过肩' },
];

export default function StoryboardPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const project = getProjectById(projectId);
  const episodes = getEpisodesByProjectId(projectId);

  const [selectedEpisode, setSelectedEpisode] = useState<string>(episodes[2]?.id || '');
  const [selectedShot, setSelectedShot] = useState<Shot | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [zoom, setZoom] = useState(100);

  const shots = selectedEpisode ? getShotsByEpisodeId(selectedEpisode) : allShots.slice(0, 6);
  const currentEpisode = episodes.find((e) => e.id === selectedEpisode);

  if (!project) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-full">
          <p className="text-muted-foreground">项目不存在</p>
        </div>
      </AppLayout>
    );
  }

  const totalDuration = shots.reduce((sum, shot) => sum + shot.duration, 0);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

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

              <Select value={selectedEpisode} onValueChange={setSelectedEpisode}>
                <SelectTrigger className="bg-secondary border-border">
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

              <Button className="w-full bg-primary text-primary-foreground hover:bg-primary/90">
                <Plus className="h-4 w-4 mr-2" />
                添加镜头
              </Button>
            </div>

            {/* Shot List */}
            <ScrollArea className="flex-1">
              <div className={`p-3 ${viewMode === 'grid' ? 'grid grid-cols-2 gap-2' : 'space-y-2'}`}>
                {shots.map((shot, index) => (
                  <div
                    key={shot.id}
                    onClick={() => setSelectedShot(shot)}
                    className={`group cursor-pointer rounded-lg border transition-all ${
                      selectedShot?.id === shot.id
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50 bg-secondary/30'
                    }`}
                  >
                    {viewMode === 'grid' ? (
                      <div className="p-2">
                        <div className="relative aspect-video rounded bg-muted mb-2">
                          {shot.thumbnailUrl ? (
                            <div
                              className="absolute inset-0 rounded bg-cover bg-center"
                              style={{ backgroundImage: `url(${shot.thumbnailUrl})` }}
                            />
                          ) : (
                            <div className="absolute inset-0 flex items-center justify-center">
                              <Camera className="h-6 w-6 text-muted-foreground" />
                            </div>
                          )}
                          <Badge className="absolute top-1 left-1 text-[10px] h-5 bg-black/60 border-0">
                            {shot.number}
                          </Badge>
                        </div>
                        <p className="text-xs text-foreground truncate">{shot.description}</p>
                        <p className="text-[10px] text-muted-foreground">{shot.duration}s</p>
                      </div>
                    ) : (
                      <div className="flex items-center gap-3 p-2">
                        <div className="flex items-center gap-2 shrink-0">
                          <GripVertical className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100" />
                          <div className="h-12 w-20 rounded bg-muted relative">
                            {shot.thumbnailUrl ? (
                              <div
                                className="absolute inset-0 rounded bg-cover bg-center"
                                style={{ backgroundImage: `url(${shot.thumbnailUrl})` }}
                              />
                            ) : (
                              <div className="absolute inset-0 flex items-center justify-center">
                                <Camera className="h-4 w-4 text-muted-foreground" />
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1 mb-0.5">
                            <span className="text-xs font-medium text-foreground">#{shot.number}</span>
                            <Badge className={`text-[10px] h-4 ${shotStatusColors[shot.status]}`}>
                              {shot.status}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground truncate">{shot.description}</p>
                        </div>
                        <span className="text-xs text-muted-foreground shrink-0">{shot.duration}s</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
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
                  {selectedShot.thumbnailUrl ? (
                    <div
                      className="w-full h-full bg-contain bg-center bg-no-repeat"
                      style={{
                        backgroundImage: `url(${selectedShot.thumbnailUrl})`,
                        transform: `scale(${zoom / 100})`,
                      }}
                    />
                  ) : (
                    <div className="flex flex-col items-center justify-center text-white/60">
                      <Camera className="h-16 w-16 mb-4" />
                      <p>暂无预览</p>
                    </div>
                  )}
                  
                  {/* Overlay Controls */}
                  <div className="absolute top-4 right-4 flex items-center gap-2">
                    <Button variant="secondary" size="icon" className="h-8 w-8 bg-black/60 hover:bg-black/80">
                      <ZoomOut className="h-4 w-4" onClick={() => setZoom(Math.max(50, zoom - 10))} />
                    </Button>
                    <span className="text-xs text-white bg-black/60 px-2 py-1 rounded">{zoom}%</span>
                    <Button variant="secondary" size="icon" className="h-8 w-8 bg-black/60 hover:bg-black/80">
                      <ZoomIn className="h-4 w-4" onClick={() => setZoom(Math.min(200, zoom + 10))} />
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
                            镜头 {selectedShot.number}
                          </Badge>
                          <Badge variant="outline" className="border-white/30 text-white">
                            v{selectedShot.version}
                          </Badge>
                        </div>
                        <span className="text-xs text-white/80">{selectedShot.duration}s</span>
                      </div>
                      <p className="text-sm text-white/80">{selectedShot.description}</p>
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
                  <Button variant="outline" size="sm" className="h-7 border-border">
                    <Sparkles className="h-3.5 w-3.5 mr-1" />
                    AI 生成
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
                  {shots.map((shot, index) => {
                    const width = Math.max(80, shot.duration * 20);
                    return (
                      <div
                        key={shot.id}
                        onClick={() => setSelectedShot(shot)}
                        className={`h-16 rounded cursor-pointer transition-all relative group ${
                          selectedShot?.id === shot.id
                            ? 'ring-2 ring-primary'
                            : 'hover:ring-1 hover:ring-primary/50'
                        }`}
                        style={{ width: `${width}px` }}
                      >
                        <div className="absolute inset-0 bg-secondary rounded overflow-hidden">
                          {shot.thumbnailUrl ? (
                            <div
                              className="absolute inset-0 bg-cover bg-center opacity-60"
                              style={{ backgroundImage: `url(${shot.thumbnailUrl})` }}
                            />
                          ) : (
                            <div className="absolute inset-0 flex items-center justify-center">
                              <Camera className="h-4 w-4 text-muted-foreground" />
                            </div>
                          )}
                        </div>
                        <div className="absolute inset-0 flex flex-col justify-between p-1.5">
                          <div className="flex items-center justify-between">
                            <Badge className="text-[10px] h-4 bg-black/60 border-0 px-1">
                              {shot.number}
                            </Badge>
                            <span className="text-[10px] text-white bg-black/60 px-1 rounded">
                              {shot.duration}s
                            </span>
                          </div>
                          <p className="text-[10px] text-white truncate bg-black/40 px-1 rounded">
                            {shot.description.slice(0, 20)}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                  <Button
                    variant="dashed"
                    className="h-16 w-20 border-dashed border-border hover:border-primary/50"
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
              <ScrollArea className="flex-1">
                <div className="p-4 space-y-6">
                  {/* Basic Info */}
                  <div className="space-y-3">
                    <h3 className="text-sm font-medium text-foreground">基本信息</h3>
                    <div className="space-y-2">
                      <div>
                        <label className="text-xs text-muted-foreground">描述</label>
                        <Textarea
                          defaultValue={selectedShot.description}
                          className="mt-1 bg-secondary border-border text-sm resize-none"
                          rows={3}
                        />
                      </div>
                      {selectedShot.dialogue && (
                        <div>
                          <label className="text-xs text-muted-foreground">台词</label>
                          <Textarea
                            defaultValue={selectedShot.dialogue}
                            className="mt-1 bg-secondary border-border text-sm resize-none"
                            rows={2}
                          />
                        </div>
                      )}
                    </div>
                  </div>

                  <Separator />

                  {/* Camera Settings */}
                  <div className="space-y-3">
                    <h3 className="text-sm font-medium text-foreground">镜头设置</h3>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs text-muted-foreground">景别</label>
                        <Select defaultValue={selectedShot.shotType}>
                          <SelectTrigger className="mt-1 bg-secondary border-border text-xs h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {shotTypes.map((type) => (
                              <SelectItem key={type.value} value={type.value}>
                                {type.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <label className="text-xs text-muted-foreground">机位</label>
                        <Select defaultValue={selectedShot.cameraAngle}>
                          <SelectTrigger className="mt-1 bg-secondary border-border text-xs h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {cameraAngles.map((angle) => (
                              <SelectItem key={angle.value} value={angle.value}>
                                {angle.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">时长 ({selectedShot.duration}s)</label>
                      <Slider
                        defaultValue={[selectedShot.duration]}
                        max={30}
                        min={1}
                        step={1}
                        className="mt-2"
                      />
                    </div>
                  </div>

                  <Separator />

                  {/* Scene Info */}
                  <div className="space-y-3">
                    <h3 className="text-sm font-medium text-foreground">场景信息</h3>
                    <div className="space-y-2">
                      <div>
                        <label className="text-xs text-muted-foreground">场景</label>
                        <Input
                          defaultValue={selectedShot.location}
                          className="mt-1 bg-secondary border-border text-sm h-8"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-muted-foreground">氛围</label>
                        <Input
                          defaultValue={selectedShot.mood}
                          className="mt-1 bg-secondary border-border text-sm h-8"
                        />
                      </div>
                    </div>
                  </div>

                  <Separator />

                  {/* Versions */}
                  {selectedShot.versions.length > 0 && (
                    <div className="space-y-3">
                      <h3 className="text-sm font-medium text-foreground">历史版本</h3>
                      <div className="space-y-2">
                        {selectedShot.versions.map((version) => (
                          <div
                            key={version.id}
                            className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors ${
                              version.version === selectedShot.version
                                ? 'bg-primary/10 border border-primary/30'
                                : 'bg-secondary/50 hover:bg-secondary'
                            }`}
                          >
                            <div className="h-10 w-16 rounded bg-muted shrink-0">
                              {version.thumbnailUrl && (
                                <div
                                  className="h-full w-full rounded bg-cover bg-center"
                                  style={{ backgroundImage: `url(${version.thumbnailUrl})` }}
                                />
                              )}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-1">
                                <span className="text-xs font-medium text-foreground">
                                  v{version.version}
                                </span>
                                {version.version === selectedShot.version && (
                                  <Badge className="text-[10px] h-4 bg-primary text-primary-foreground">
                                    当前
                                  </Badge>
                                )}
                              </div>
                              <p className="text-[10px] text-muted-foreground truncate">
                                {version.note || '无备注'}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="space-y-2">
                    <Button className="w-full bg-primary text-primary-foreground hover:bg-primary/90">
                      <Wand2 className="h-4 w-4 mr-2" />
                      AI 重新生成
                    </Button>
                    <div className="grid grid-cols-2 gap-2">
                      <Button variant="outline" className="border-border">
                        <RefreshCw className="h-4 w-4 mr-1" />
                        刷新
                      </Button>
                      <Button variant="outline" className="border-border text-destructive hover:text-destructive">
                        <Trash2 className="h-4 w-4 mr-1" />
                        删除
                      </Button>
                    </div>
                  </div>
                </div>
              </ScrollArea>
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
