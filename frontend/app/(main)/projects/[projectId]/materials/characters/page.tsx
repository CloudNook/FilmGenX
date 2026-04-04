'use client';

import { use, useEffect, useState, useCallback } from 'react';
import { AppLayout } from '@/components/layout';
import {
  projectsApi,
  charactersApi,
  type ProjectResponse,
  type CharacterResponse,
  type CharacterDetailResponse,
} from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
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
  MoreVertical,
  Edit,
  Trash2,
  Sparkles,
  Users,
  Loader2,
} from 'lucide-react';

export default function CharactersPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const projectIdNum = Number(projectId);

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [characters, setCharacters] = useState<CharacterResponse[]>([]);
  const [selectedCharId, setSelectedCharId] = useState<number | null>(null);
  const [charDetail, setCharDetail] = useState<CharacterDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newCharName, setNewCharName] = useState('');
  const [newCharCode, setNewCharCode] = useState('');
  const [newCharDesc, setNewCharDesc] = useState('');
  const [creating, setCreating] = useState(false);

  // Load project + characters
  useEffect(() => {
    if (isNaN(projectIdNum)) return;

    Promise.all([
      projectsApi.get(projectIdNum).catch(() => null),
      charactersApi.list(projectIdNum).then(r => r.items).catch(() => []),
    ]).then(([p, chars]) => {
      setProject(p);
      setCharacters(chars);
      if (chars.length > 0 && !selectedCharId) {
        setSelectedCharId(chars[0].id);
      }
      setLoading(false);
    });
  }, [projectIdNum]);

  // Load character detail when selected
  useEffect(() => {
    if (!selectedCharId || isNaN(projectIdNum)) return;
    charactersApi
      .get(projectIdNum, selectedCharId)
      .then(setCharDetail)
      .catch(() => setCharDetail(null));
  }, [selectedCharId, projectIdNum]);

  const handleCreateCharacter = useCallback(async () => {
    if (!newCharName.trim() || !newCharCode.trim()) return;
    setCreating(true);
    try {
      const char = await charactersApi.create(projectIdNum, {
        char_code: newCharCode.trim(),
        name: newCharName.trim(),
        role_description: newCharDesc.trim() || undefined,
      });
      setCharacters(prev => [char, ...prev]);
      setSelectedCharId(char.id);
      setIsCreateDialogOpen(false);
      setNewCharName('');
      setNewCharCode('');
      setNewCharDesc('');
    } catch (err) {
      console.error('Failed to create character:', err);
    } finally {
      setCreating(false);
    }
  }, [projectIdNum, newCharName, newCharCode, newCharDesc]);

  const handleDeleteCharacter = useCallback(async (charId: number) => {
    try {
      await charactersApi.delete(projectIdNum, charId);
      setCharacters(prev => prev.filter(c => c.id !== charId));
      if (selectedCharId === charId) {
        setSelectedCharId(null);
        setCharDetail(null);
      }
    } catch (err) {
      console.error('Failed to delete character:', err);
    }
  }, [projectIdNum, selectedCharId]);

  const filteredCharacters = characters.filter((char) => {
    return (
      char.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (char.role_description || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      char.char_code.toLowerCase().includes(searchQuery.toLowerCase())
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
        { label: '素材库', href: `/projects/${projectId}/materials` },
        { label: '角色管理' },
      ]}
    >
      <div className="flex h-[calc(100vh-4rem)]">
        {/* Left Panel - Character List */}
        <div className="w-80 border-r border-border bg-card flex flex-col">
          <div className="p-4 border-b border-border space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-foreground">角色列表</h2>
              <Badge variant="outline" className="border-border">
                {characters.length} 个角色
              </Badge>
            </div>

            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="搜索角色..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 bg-secondary border-border"
              />
            </div>

            <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button className="w-full bg-primary text-primary-foreground hover:bg-primary/90">
                  <Plus className="h-4 w-4 mr-2" />
                  创建角色
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>创建新角色</DialogTitle>
                  <DialogDescription>
                    填写角色的基本信息
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">角色名称</label>
                    <Input
                      placeholder="输入角色名称"
                      className="bg-secondary border-border"
                      value={newCharName}
                      onChange={(e) => setNewCharName(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">角色编号</label>
                    <Input
                      placeholder="如 CHAR_XIAO_YAN"
                      className="bg-secondary border-border"
                      value={newCharCode}
                      onChange={(e) => setNewCharCode(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">角色描述</label>
                    <Textarea
                      placeholder="描述角色的背景、身份等信息..."
                      className="bg-secondary border-border resize-none"
                      rows={3}
                      value={newCharDesc}
                      onChange={(e) => setNewCharDesc(e.target.value)}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                    取消
                  </Button>
                  <Button
                    className="bg-primary text-primary-foreground hover:bg-primary/90"
                    onClick={handleCreateCharacter}
                    disabled={!newCharName.trim() || !newCharCode.trim() || creating}
                  >
                    {creating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                    创建角色
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <ScrollArea className="flex-1">
            <div className="p-3 space-y-2">
              {filteredCharacters.map((char) => (
                <div key={char.id} className="group relative">
                  <div
                    onClick={() => setSelectedCharId(char.id)}
                    className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all ${
                      selectedCharId === char.id
                        ? 'bg-primary/10 border border-primary/30'
                        : 'hover:bg-secondary/50 border border-transparent'
                    }`}
                  >
                    <Avatar className="h-10 w-10 shrink-0">
                      <AvatarFallback className="bg-primary/10 text-primary text-lg">
                        {char.name.slice(0, 1)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <span className="font-medium text-foreground text-sm truncate block">
                        {char.name}
                      </span>
                      <p className="text-xs text-muted-foreground truncate">
                        {char.role_description || char.char_code}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 opacity-0 group-hover:opacity-100 shrink-0 text-muted-foreground hover:text-destructive"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteCharacter(char.id);
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}

              {filteredCharacters.length === 0 && (
                <div className="py-8 text-center text-muted-foreground">
                  <Users className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>没有找到角色</p>
                </div>
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Right Panel - Character Details */}
        <div className="flex-1 bg-background overflow-y-auto">
          {charDetail ? (
            <div className="p-6 space-y-6">
              {/* Header */}
              <div className="flex items-start gap-6">
                <Avatar className="h-24 w-24">
                  <AvatarFallback className="bg-primary/10 text-primary text-3xl">
                    {charDetail.name.slice(0, 1)}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h1 className="text-2xl font-bold text-foreground">{charDetail.name}</h1>
                    <Badge variant="outline" className="border-border">
                      {charDetail.char_code}
                    </Badge>
                  </div>
                  <p className="text-muted-foreground mb-2">
                    {charDetail.role_description || '暂无描述'}
                  </p>
                  {charDetail.name_aliases.length > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">别名：</span>
                      {charDetail.name_aliases.map((alias) => (
                        <Badge key={alias} variant="outline" className="text-xs border-border">
                          {alias}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Tabs */}
              <Tabs defaultValue="versions" className="space-y-4">
                <TabsList className="bg-card border border-border">
                  <TabsTrigger value="versions">
                    角色版本 ({charDetail.versions.length})
                  </TabsTrigger>
                  <TabsTrigger value="features">
                    特征设定
                  </TabsTrigger>
                  <TabsTrigger value="relationships">
                    关系设定
                  </TabsTrigger>
                </TabsList>

                {/* Versions Tab */}
                <TabsContent value="versions" className="space-y-4">
                  {charDetail.versions.length === 0 && (
                    <div className="text-center py-12">
                      <Users className="h-12 w-12 mx-auto text-muted-foreground mb-3 opacity-50" />
                      <p className="text-muted-foreground">暂无角色版本</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        为角色创建不同时期的版本（如少年期、成年期等）
                      </p>
                    </div>
                  )}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {charDetail.versions.map((version) => (
                      <Card key={version.id} className="bg-card border-border">
                        <CardHeader className="pb-3">
                          <CardTitle className="text-base flex items-center justify-between">
                            <span>{version.label}</span>
                            <Badge variant="outline" className="text-xs border-border">
                              {version.version_code}
                            </Badge>
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          {version.age_description && (
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-muted-foreground">年龄</span>
                              <span className="text-foreground">{version.age_description}</span>
                            </div>
                          )}
                          {version.height_cm && (
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-muted-foreground">身高</span>
                              <span className="text-foreground">{version.height_cm}cm</span>
                            </div>
                          )}
                          {version.face_description && (
                            <>
                              <Separator />
                              <div>
                                <span className="text-sm text-muted-foreground">面容</span>
                                <p className="text-sm text-foreground mt-1">{version.face_description}</p>
                              </div>
                            </>
                          )}
                          {version.hair_description && (
                            <div>
                              <span className="text-sm text-muted-foreground">发型</span>
                              <p className="text-sm text-foreground mt-1">{version.hair_description}</p>
                            </div>
                          )}
                          {version.dou_qi_level && (
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-muted-foreground">境界</span>
                              <span className="text-foreground">{version.dou_qi_level}</span>
                            </div>
                          )}
                          {version.dou_qi_color && (
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-muted-foreground">斗气颜色</span>
                              <span className="flex items-center gap-2">
                                <span
                                  className="h-4 w-4 rounded-full border"
                                  style={{ backgroundColor: version.dou_qi_color }}
                                />
                                {version.dou_qi_color}
                              </span>
                            </div>
                          )}
                          {version.base_image_prompt && (
                            <>
                              <Separator />
                              <div>
                                <span className="text-sm text-muted-foreground">图像提示词</span>
                                <p className="text-xs text-foreground mt-1 font-mono bg-secondary p-2 rounded">
                                  {version.base_image_prompt}
                                </p>
                              </div>
                            </>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </TabsContent>

                {/* Features Tab */}
                <TabsContent value="features" className="space-y-4">
                  <Card className="bg-card border-border">
                    <CardHeader>
                      <CardTitle className="text-base">跨版本固定特征</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {charDetail.consistent_features ? (
                        <pre className="text-sm text-foreground whitespace-pre-wrap bg-secondary p-3 rounded">
                          {JSON.stringify(charDetail.consistent_features, null, 2)}
                        </pre>
                      ) : (
                        <p className="text-sm text-muted-foreground">暂未设置</p>
                      )}
                    </CardContent>
                  </Card>

                  <Card className="bg-card border-border">
                    <CardHeader>
                      <CardTitle className="text-base">表情指南</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {charDetail.expression_guide ? (
                        <pre className="text-sm text-foreground whitespace-pre-wrap bg-secondary p-3 rounded">
                          {JSON.stringify(charDetail.expression_guide, null, 2)}
                        </pre>
                      ) : (
                        <p className="text-sm text-muted-foreground">暂未设置</p>
                      )}
                    </CardContent>
                  </Card>

                  <Card className="bg-card border-border">
                    <CardHeader>
                      <CardTitle className="text-base">动作指南</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {charDetail.action_guide ? (
                        <pre className="text-sm text-foreground whitespace-pre-wrap bg-secondary p-3 rounded">
                          {JSON.stringify(charDetail.action_guide, null, 2)}
                        </pre>
                      ) : (
                        <p className="text-sm text-muted-foreground">暂未设置</p>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Relationships Tab */}
                <TabsContent value="relationships" className="space-y-4">
                  <Card className="bg-card border-border">
                    <CardHeader>
                      <CardTitle className="text-base">角色关系</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {charDetail.relationships ? (
                        <pre className="text-sm text-foreground whitespace-pre-wrap bg-secondary p-3 rounded">
                          {JSON.stringify(charDetail.relationships, null, 2)}
                        </pre>
                      ) : (
                        <p className="text-sm text-muted-foreground">暂未设置角色关系</p>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-center">
              <div>
                <Users className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold text-foreground mb-2">选择一个角色</h3>
                <p className="text-muted-foreground">从左侧列表选择角色查看详情</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
