'use client';

import { use, useEffect, useState, useCallback } from 'react';
import { AppLayout } from '@/components/layout';
import {
  projectsApi,
  locationsApi,
  type ProjectResponse,
  type LocationResponse,
  type LocationDetailResponse,
  type LocationVersionResponse,
} from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Plus,
  Search,
  Trash2,
  MapPin,
  Loader2,
  Building,
  Trees,
  Sparkles,
  Layers,
  Sun,
  Moon,
  Cloud,
  CloudRain,
} from 'lucide-react';

const locationTypeLabels: Record<string, string> = {
  indoor: '室内',
  outdoor: '室外',
  fantasy: '玄幻',
  mixed: '混合',
};

const locationTypeIcons: Record<string, typeof Building> = {
  indoor: Building,
  outdoor: Trees,
  fantasy: Sparkles,
  mixed: Layers,
};

const timeOfDayLabels: Record<string, string> = {
  dawn: '黎明',
  day: '白天',
  dusk: '黄昏',
  night: '夜晚',
};

const weatherLabels: Record<string, string> = {
  clear: '晴朗',
  cloudy: '多云',
  rain: '雨天',
  snow: '雪天',
  fog: '雾天',
  storm: '暴风雨',
};

export default function LocationsPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const projectIdNum = Number(projectId);

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [locations, setLocations] = useState<LocationResponse[]>([]);
  const [selectedLocId, setSelectedLocId] = useState<number | null>(null);
  const [locDetail, setLocDetail] = useState<LocationDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  // Form state
  const [newLocName, setNewLocName] = useState('');
  const [newLocCode, setNewLocCode] = useState('');
  const [newLocType, setNewLocType] = useState('outdoor');
  const [newLocDomain, setNewLocDomain] = useState('');
  const [newLocDesc, setNewLocDesc] = useState('');

  // Load project + locations
  useEffect(() => {
    if (isNaN(projectIdNum)) return;

    Promise.all([
      projectsApi.get(projectIdNum).catch(() => null),
      locationsApi.list(projectIdNum).then(r => r.items).catch(() => []),
    ]).then(([p, locs]) => {
      setProject(p);
      setLocations(locs);
      if (locs.length > 0 && !selectedLocId) {
        setSelectedLocId(locs[0].id);
      }
      setLoading(false);
    });
  }, [projectIdNum]);

  // Load location detail when selected
  useEffect(() => {
    if (!selectedLocId || isNaN(projectIdNum)) return;
    locationsApi
      .get(projectIdNum, selectedLocId)
      .then(setLocDetail)
      .catch(() => setLocDetail(null));
  }, [selectedLocId, projectIdNum]);

  const handleCreateLocation = useCallback(async () => {
    if (!newLocName.trim() || !newLocCode.trim()) return;
    setCreating(true);
    try {
      const loc = await locationsApi.create(projectIdNum, {
        loc_code: newLocCode.trim(),
        name: newLocName.trim(),
        location_type: newLocType,
        domain: newLocDomain.trim() || undefined,
        description: newLocDesc.trim() || undefined,
      });
      setLocations(prev => [loc, ...prev]);
      setSelectedLocId(loc.id);
      setIsCreateDialogOpen(false);
      setNewLocName('');
      setNewLocCode('');
      setNewLocType('outdoor');
      setNewLocDomain('');
      setNewLocDesc('');
    } catch (err) {
      console.error('Failed to create location:', err);
    } finally {
      setCreating(false);
    }
  }, [projectIdNum, newLocName, newLocCode, newLocType, newLocDomain, newLocDesc]);

  const handleDeleteLocation = useCallback(async (locId: number) => {
    try {
      await locationsApi.delete(projectIdNum, locId);
      setLocations(prev => prev.filter(l => l.id !== locId));
      if (selectedLocId === locId) {
        setSelectedLocId(null);
        setLocDetail(null);
      }
    } catch (err) {
      console.error('Failed to delete location:', err);
    }
  }, [projectIdNum, selectedLocId]);

  const filteredLocations = locations.filter((loc) => {
    return (
      loc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (loc.domain || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      loc.loc_code.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

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

  return (
    <AppLayout
      projectId={projectId}
      breadcrumbs={[
        { label: '项目', href: '/projects' },
        { label: project.name, href: `/projects/${projectId}` },
        { label: '场景管理' },
      ]}
    >
      <div className="flex h-[calc(100vh-4rem)]">
        {/* Left Panel - Location List */}
        <div className="w-80 border-r border-border bg-card flex flex-col">
          <div className="p-4 border-b border-border space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-foreground">场景列表</h2>
              <Badge variant="outline" className="border-border">
                {locations.length} 个场景
              </Badge>
            </div>

            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="搜索场景..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 bg-secondary border-border"
              />
            </div>

            <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button className="w-full bg-primary text-primary-foreground hover:bg-primary/90">
                  <Plus className="h-4 w-4 mr-2" />
                  创建场景
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>创建新场景</DialogTitle>
                  <DialogDescription>填写场景的基本信息</DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">场景名称</label>
                    <Input
                      placeholder="输入场景名称"
                      className="bg-secondary border-border"
                      value={newLocName}
                      onChange={(e) => setNewLocName(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">场景编号</label>
                    <Input
                      placeholder="如 LOC_YUNLAN_SQUARE"
                      className="bg-secondary border-border"
                      value={newLocCode}
                      onChange={(e) => setNewLocCode(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">场景类型</label>
                    <Select value={newLocType} onValueChange={setNewLocType}>
                      <SelectTrigger className="bg-secondary border-border">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="indoor">室内</SelectItem>
                        <SelectItem value="outdoor">室外</SelectItem>
                        <SelectItem value="fantasy">玄幻</SelectItem>
                        <SelectItem value="mixed">混合</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">所属势力/领域</label>
                    <Input
                      placeholder="如 云岚宗"
                      className="bg-secondary border-border"
                      value={newLocDomain}
                      onChange={(e) => setNewLocDomain(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">场景描述</label>
                    <Textarea
                      placeholder="描述场景的详细特征..."
                      className="bg-secondary border-border resize-none"
                      rows={3}
                      value={newLocDesc}
                      onChange={(e) => setNewLocDesc(e.target.value)}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                    取消
                  </Button>
                  <Button
                    className="bg-primary text-primary-foreground hover:bg-primary/90"
                    onClick={handleCreateLocation}
                    disabled={!newLocName.trim() || !newLocCode.trim() || creating}
                  >
                    {creating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                    创建场景
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <ScrollArea className="flex-1">
            <div className="p-3 space-y-2">
              {filteredLocations.map((loc) => {
                const TypeIcon = locationTypeIcons[loc.location_type] || MapPin;
                return (
                  <div key={loc.id} className="group relative">
                    <div
                      onClick={() => setSelectedLocId(loc.id)}
                      className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all ${
                        selectedLocId === loc.id
                          ? 'bg-primary/10 border border-primary/30'
                          : 'hover:bg-secondary/50 border border-transparent'
                      }`}
                    >
                      <div className="h-10 w-10 rounded-lg bg-info/10 flex items-center justify-center shrink-0">
                        <TypeIcon className="h-5 w-5 text-info" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <span className="font-medium text-foreground text-sm truncate block">
                          {loc.name}
                        </span>
                        <p className="text-xs text-muted-foreground truncate">
                          {loc.domain || locationTypeLabels[loc.location_type]}
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 opacity-0 group-hover:opacity-100 shrink-0 text-muted-foreground hover:text-destructive"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteLocation(loc.id);
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                );
              })}

              {filteredLocations.length === 0 && (
                <div className="py-8 text-center text-muted-foreground">
                  <MapPin className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>没有找到场景</p>
                </div>
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Right Panel - Location Details */}
        <div className="flex-1 bg-background overflow-y-auto">
          {locDetail ? (
            <div className="p-6 space-y-6">
              {/* Header */}
              <div className="flex items-start gap-6">
                <div className="h-24 w-24 rounded-xl bg-info/10 flex items-center justify-center">
                  {(() => {
                    const TypeIcon = locationTypeIcons[locDetail.location_type] || MapPin;
                    return <TypeIcon className="h-12 w-12 text-info" />;
                  })()}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h1 className="text-2xl font-bold text-foreground">{locDetail.name}</h1>
                    <Badge variant="outline" className="border-border">
                      {locDetail.loc_code}
                    </Badge>
                    <Badge
                      variant={locDetail.is_active ? 'default' : 'secondary'}
                      className={locDetail.is_active ? 'bg-success/20 text-success' : ''}
                    >
                      {locDetail.is_active ? '启用' : '禁用'}
                    </Badge>
                  </div>
                  <p className="text-muted-foreground mb-2">
                    {locDetail.description || '暂无描述'}
                  </p>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-muted-foreground">
                      类型: <span className="text-foreground">{locationTypeLabels[locDetail.location_type]}</span>
                    </span>
                    {locDetail.domain && (
                      <span className="text-muted-foreground">
                        领域: <span className="text-foreground">{locDetail.domain}</span>
                      </span>
                    )}
                    <span className="text-muted-foreground">
                      引用: <span className="text-foreground">{locDetail.usage_count} 次</span>
                    </span>
                  </div>
                </div>
              </div>

              {/* Tabs */}
              <Tabs defaultValue="versions" className="space-y-4">
                <TabsList className="bg-card border border-border">
                  <TabsTrigger value="versions">
                    场景版本 ({locDetail.version_count})
                  </TabsTrigger>
                  <TabsTrigger value="elements">标志性元素</TabsTrigger>
                  <TabsTrigger value="prompts">生成提示词</TabsTrigger>
                </TabsList>

                {/* Versions Tab */}
                <TabsContent value="versions" className="space-y-4">
                  {locDetail.versions.length === 0 && (
                    <div className="text-center py-12">
                      <MapPin className="h-12 w-12 mx-auto text-muted-foreground mb-3 opacity-50" />
                      <p className="text-muted-foreground">暂无场景版本</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        为场景创建不同状态或时间的变体（如夜晚、战斗损毁等）
                      </p>
                    </div>
                  )}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {locDetail.versions.map((version) => (
                      <Card key={version.id} className="bg-card border-border">
                        <CardHeader className="pb-3">
                          <CardTitle className="text-base flex items-center justify-between">
                            <span>{version.label}</span>
                            <div className="flex items-center gap-2">
                              {version.is_default && (
                                <Badge className="bg-primary/20 text-primary text-xs">默认</Badge>
                              )}
                              <Badge variant="outline" className="text-xs border-border">
                                {version.version_code}
                              </Badge>
                            </div>
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          {version.description && (
                            <p className="text-sm text-muted-foreground">{version.description}</p>
                          )}
                          <div className="flex items-center gap-4 text-sm">
                            {version.time_of_day && (
                              <span className="flex items-center gap-1 text-muted-foreground">
                                {version.time_of_day === 'night' ? (
                                  <Moon className="h-4 w-4" />
                                ) : (
                                  <Sun className="h-4 w-4" />
                                )}
                                {timeOfDayLabels[version.time_of_day]}
                              </span>
                            )}
                            {version.weather && (
                              <span className="flex items-center gap-1 text-muted-foreground">
                                {version.weather === 'rain' ? (
                                  <CloudRain className="h-4 w-4" />
                                ) : (
                                  <Cloud className="h-4 w-4" />
                                )}
                                {weatherLabels[version.weather]}
                              </span>
                            )}
                          </div>
                          {version.additional_elements.length > 0 && (
                            <div>
                              <span className="text-xs text-muted-foreground">额外元素</span>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {version.additional_elements.map((el, i) => (
                                  <Badge key={i} variant="outline" className="text-xs border-border">
                                    {el}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          )}
                          {version.reference_image_urls.length > 0 && (
                            <div className="grid grid-cols-4 gap-2 mt-2">
                              {version.reference_image_urls.slice(0, 4).map((url, i) => (
                                <div
                                  key={i}
                                  className="aspect-square rounded bg-secondary/50 overflow-hidden"
                                >
                                  <img src={url} alt="" className="w-full h-full object-cover" />
                                </div>
                              ))}
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </TabsContent>

                {/* Elements Tab */}
                <TabsContent value="elements" className="space-y-4">
                  <Card className="bg-card border-border">
                    <CardHeader>
                      <CardTitle className="text-base">标志性元素</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {locDetail.key_elements.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {locDetail.key_elements.map((el, i) => (
                            <Badge key={i} variant="outline" className="border-border">
                              {el}
                            </Badge>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">暂未设置标志性元素</p>
                      )}
                    </CardContent>
                  </Card>

                  <Card className="bg-card border-border">
                    <CardHeader>
                      <CardTitle className="text-base">建筑风格</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-foreground">
                        {locDetail.architectural_style || '暂未设置'}
                      </p>
                    </CardContent>
                  </Card>

                  <Card className="bg-card border-border">
                    <CardHeader>
                      <CardTitle className="text-base">默认氛围</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {locDetail.default_atmosphere ? (
                        <pre className="text-sm text-foreground whitespace-pre-wrap bg-secondary p-3 rounded">
                          {JSON.stringify(locDetail.default_atmosphere, null, 2)}
                        </pre>
                      ) : (
                        <p className="text-sm text-muted-foreground">暂未设置</p>
                      )}
                    </CardContent>
                  </Card>

                  <Card className="bg-card border-border">
                    <CardHeader>
                      <CardTitle className="text-base">时间变体描述</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {locDetail.time_variants ? (
                        <div className="grid grid-cols-2 gap-3">
                          {Object.entries(locDetail.time_variants).map(([time, desc]) => (
                            <div key={time} className="p-3 rounded bg-secondary/50">
                              <p className="text-xs text-muted-foreground mb-1">
                                {timeOfDayLabels[time] || time}
                              </p>
                              <p className="text-sm text-foreground">{desc}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">暂未设置</p>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Prompts Tab */}
                <TabsContent value="prompts" className="space-y-4">
                  <Card className="bg-card border-border">
                    <CardHeader>
                      <CardTitle className="text-base">背景生成提示词</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {locDetail.base_background_prompt ? (
                        <p className="text-sm text-foreground font-mono bg-secondary p-3 rounded whitespace-pre-wrap">
                          {locDetail.base_background_prompt}
                        </p>
                      ) : (
                        <p className="text-sm text-muted-foreground">暂未设置</p>
                      )}
                    </CardContent>
                  </Card>

                  <Card className="bg-card border-border">
                    <CardHeader>
                      <CardTitle className="text-base">负面提示词</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {locDetail.negative_prompt ? (
                        <p className="text-sm text-foreground font-mono bg-secondary p-3 rounded whitespace-pre-wrap">
                          {locDetail.negative_prompt}
                        </p>
                      ) : (
                        <p className="text-sm text-muted-foreground">暂未设置</p>
                      )}
                    </CardContent>
                  </Card>

                  <Card className="bg-card border-border">
                    <CardHeader>
                      <CardTitle className="text-base">风格预设</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-foreground">
                        {locDetail.style_preset || '暂未设置'}
                      </p>
                    </CardContent>
                  </Card>

                  <Card className="bg-card border-border">
                    <CardHeader>
                      <CardTitle className="text-base">参考图</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {locDetail.reference_image_urls.length > 0 ? (
                        <div className="grid grid-cols-4 gap-3">
                          {locDetail.reference_image_urls.map((url, i) => (
                            <div
                              key={i}
                              className="aspect-video rounded bg-secondary/50 overflow-hidden"
                            >
                              <img src={url} alt="" className="w-full h-full object-cover" />
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">暂无参考图</p>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-center">
              <div>
                <MapPin className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold text-foreground mb-2">选择一个场景</h3>
                <p className="text-muted-foreground">从左侧列表选择场景查看详情</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
