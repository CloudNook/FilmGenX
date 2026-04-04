'use client';

import { use, useState } from 'react';
import { AppLayout } from '@/components/layout';
import { getProjectById, getCharactersByProjectId, shots } from '@/lib/mock-data';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
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
  Copy,
  Upload,
  Image,
  Sparkles,
  Users,
  Film,
  Mic,
  Palette,
  User,
  Heart,
  X,
  Check,
  RefreshCw,
} from 'lucide-react';
import type { Character } from '@/lib/types';

const roleLabels: Record<Character['role'], string> = {
  protagonist: '主角',
  antagonist: '反派',
  supporting: '配角',
  background: '背景角色',
};

const roleColors: Record<Character['role'], string> = {
  protagonist: 'bg-primary/20 text-primary',
  antagonist: 'bg-destructive/20 text-destructive',
  supporting: 'bg-info/20 text-info',
  background: 'bg-muted text-muted-foreground',
};

export default function CharactersPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const project = getProjectById(projectId);
  const characters = getCharactersByProjectId(projectId);

  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(
    characters[0] || null
  );
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);

  if (!project) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-full">
          <p className="text-muted-foreground">项目不存在</p>
        </div>
      </AppLayout>
    );
  }

  const filteredCharacters = characters.filter((char) => {
    const matchesSearch =
      char.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      char.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRole = roleFilter === 'all' || char.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const getCharacterShots = (characterId: string) => {
    return shots.filter((shot) => shot.characters.includes(characterId));
  };

  return (
    <AppLayout
      projectId={projectId}
      breadcrumbs={[
        { label: '项目', href: '/projects' },
        { label: project.name, href: `/projects/${projectId}` },
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

            <div className="flex items-center gap-2">
              <Select value={roleFilter} onValueChange={setRoleFilter}>
                <SelectTrigger className="flex-1 bg-secondary border-border">
                  <SelectValue placeholder="筛选角色类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部类型</SelectItem>
                  <SelectItem value="protagonist">主角</SelectItem>
                  <SelectItem value="antagonist">反派</SelectItem>
                  <SelectItem value="supporting">配角</SelectItem>
                  <SelectItem value="background">背景角色</SelectItem>
                </SelectContent>
              </Select>
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
                    填写角色的基本信息，AI 将帮助您生成角色的视觉形象
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">角色名称</label>
                    <Input placeholder="输入角色名称" className="bg-secondary border-border" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">角色类型</label>
                    <Select>
                      <SelectTrigger className="bg-secondary border-border">
                        <SelectValue placeholder="选择角色类型" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="protagonist">主角</SelectItem>
                        <SelectItem value="antagonist">反派</SelectItem>
                        <SelectItem value="supporting">配角</SelectItem>
                        <SelectItem value="background">背景角色</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">角色描述</label>
                    <Textarea
                      placeholder="描述角色的背景、身份等信息..."
                      className="bg-secondary border-border resize-none"
                      rows={3}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">外观特征</label>
                    <Textarea
                      placeholder="描述角色的外貌特征，用于 AI 生成角色形象..."
                      className="bg-secondary border-border resize-none"
                      rows={3}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                    取消
                  </Button>
                  <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
                    <Sparkles className="h-4 w-4 mr-2" />
                    AI 生成角色
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <ScrollArea className="flex-1">
            <div className="p-3 space-y-2">
              {filteredCharacters.map((character) => (
                <div
                  key={character.id}
                  onClick={() => setSelectedCharacter(character)}
                  className={`group flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all ${
                    selectedCharacter?.id === character.id
                      ? 'bg-primary/10 border border-primary/30'
                      : 'hover:bg-secondary/50 border border-transparent'
                  }`}
                >
                  <Avatar className="h-12 w-12 shrink-0">
                    <AvatarImage src={character.avatarUrl} />
                    <AvatarFallback className="bg-primary/10 text-primary text-lg">
                      {character.name.slice(0, 1)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-foreground truncate">
                        {character.name}
                      </span>
                      <Badge className={`text-xs ${roleColors[character.role]}`}>
                        {roleLabels[character.role]}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground truncate">
                      {character.description}
                    </p>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 opacity-0 group-hover:opacity-100 shrink-0"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
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
          {selectedCharacter ? (
            <div className="p-6 space-y-6">
              {/* Header */}
              <div className="flex items-start gap-6">
                <div className="relative group">
                  <Avatar className="h-32 w-32">
                    <AvatarImage src={selectedCharacter.avatarUrl} />
                    <AvatarFallback className="bg-primary/10 text-primary text-4xl">
                      {selectedCharacter.name.slice(0, 1)}
                    </AvatarFallback>
                  </Avatar>
                  <Button
                    size="icon"
                    className="absolute bottom-0 right-0 h-8 w-8 rounded-full bg-primary text-primary-foreground hover:bg-primary/90"
                  >
                    <Upload className="h-4 w-4" />
                  </Button>
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h1 className="text-2xl font-bold text-foreground">{selectedCharacter.name}</h1>
                    <Badge className={roleColors[selectedCharacter.role]}>
                      {roleLabels[selectedCharacter.role]}
                    </Badge>
                  </div>
                  <p className="text-muted-foreground mb-4">{selectedCharacter.description}</p>
                  <div className="flex items-center gap-3">
                    <Button variant="outline" className="border-border">
                      <Edit className="h-4 w-4 mr-2" />
                      编辑信息
                    </Button>
                    <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
                      <Sparkles className="h-4 w-4 mr-2" />
                      AI 优化
                    </Button>
                  </div>
                </div>
              </div>

              {/* Tabs */}
              <Tabs defaultValue="profile" className="space-y-4">
                <TabsList className="bg-card border border-border">
                  <TabsTrigger value="profile" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                    <User className="h-4 w-4 mr-2" />
                    人物档案
                  </TabsTrigger>
                  <TabsTrigger value="appearance" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                    <Palette className="h-4 w-4 mr-2" />
                    外观设定
                  </TabsTrigger>
                  <TabsTrigger value="references" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                    <Image className="h-4 w-4 mr-2" />
                    参考图
                  </TabsTrigger>
                  <TabsTrigger value="appearances" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                    <Film className="h-4 w-4 mr-2" />
                    出场镜头
                  </TabsTrigger>
                </TabsList>

                {/* Profile Tab */}
                <TabsContent value="profile" className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <Card className="bg-card border-border">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                          <User className="h-4 w-4 text-primary" />
                          基本信息
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-muted-foreground">年龄</span>
                          <span className="text-sm text-foreground">
                            {selectedCharacter.age || '未设置'}
                          </span>
                        </div>
                        <Separator />
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-muted-foreground">角色类型</span>
                          <Badge className={roleColors[selectedCharacter.role]}>
                            {roleLabels[selectedCharacter.role]}
                          </Badge>
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="bg-card border-border">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                          <Mic className="h-4 w-4 text-info" />
                          配音设置
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-muted-foreground">声线风格</span>
                          <span className="text-sm text-foreground">
                            {selectedCharacter.voiceStyle || '未设置'}
                          </span>
                        </div>
                        <Button variant="outline" size="sm" className="w-full border-border">
                          <Sparkles className="h-3.5 w-3.5 mr-2" />
                          AI 生成配音
                        </Button>
                      </CardContent>
                    </Card>
                  </div>

                  <Card className="bg-card border-border">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base flex items-center gap-2">
                        <Heart className="h-4 w-4 text-destructive" />
                        性格特征
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-foreground leading-relaxed">
                        {selectedCharacter.personality}
                      </p>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Appearance Tab */}
                <TabsContent value="appearance" className="space-y-4">
                  <Card className="bg-card border-border">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base">外观描述</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-foreground leading-relaxed">
                        {selectedCharacter.appearance}
                      </p>
                    </CardContent>
                  </Card>

                  <Card className="bg-card border-border">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base">AI 形象生成</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <p className="text-sm text-muted-foreground">
                        根据外观描述，AI 可以自动生成角色的不同姿态和表情
                      </p>
                      <div className="grid grid-cols-4 gap-3">
                        {['正面', '侧面', '表情1', '表情2'].map((pose, index) => (
                          <div
                            key={index}
                            className="aspect-square rounded-lg bg-secondary border-2 border-dashed border-border flex items-center justify-center cursor-pointer hover:border-primary/50 transition-colors"
                          >
                            <div className="text-center">
                              <Plus className="h-6 w-6 mx-auto text-muted-foreground mb-1" />
                              <span className="text-xs text-muted-foreground">{pose}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                      <Button className="w-full bg-primary text-primary-foreground hover:bg-primary/90">
                        <Sparkles className="h-4 w-4 mr-2" />
                        批量生成角色姿态
                      </Button>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* References Tab */}
                <TabsContent value="references" className="space-y-4">
                  <Card className="bg-card border-border">
                    <CardHeader className="flex flex-row items-center justify-between pb-3">
                      <CardTitle className="text-base">参考图片</CardTitle>
                      <Button size="sm" variant="outline" className="border-border">
                        <Upload className="h-4 w-4 mr-2" />
                        上传图片
                      </Button>
                    </CardHeader>
                    <CardContent>
                      {selectedCharacter.referenceImages.length > 0 ? (
                        <div className="grid grid-cols-3 gap-4">
                          {selectedCharacter.referenceImages.map((img, index) => (
                            <div
                              key={index}
                              className="relative aspect-square rounded-lg bg-muted overflow-hidden group"
                            >
                              <div
                                className="absolute inset-0 bg-cover bg-center"
                                style={{ backgroundImage: `url(${img})` }}
                              />
                              <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                                <Button size="icon" variant="secondary" className="h-8 w-8">
                                  <RefreshCw className="h-4 w-4" />
                                </Button>
                                <Button size="icon" variant="destructive" className="h-8 w-8">
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="py-8 text-center">
                          <Image className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                          <p className="text-muted-foreground mb-4">暂无参考图片</p>
                          <Button variant="outline" className="border-border">
                            <Upload className="h-4 w-4 mr-2" />
                            上传参考图
                          </Button>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Appearances Tab */}
                <TabsContent value="appearances" className="space-y-4">
                  <Card className="bg-card border-border">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-base">出场镜头</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {getCharacterShots(selectedCharacter.id).length > 0 ? (
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                          {getCharacterShots(selectedCharacter.id).map((shot) => (
                            <div
                              key={shot.id}
                              className="group cursor-pointer"
                            >
                              <div className="relative aspect-video rounded-lg bg-muted overflow-hidden mb-2">
                                {shot.thumbnailUrl ? (
                                  <div
                                    className="absolute inset-0 bg-cover bg-center transition-transform group-hover:scale-105"
                                    style={{ backgroundImage: `url(${shot.thumbnailUrl})` }}
                                  />
                                ) : (
                                  <div className="absolute inset-0 flex items-center justify-center">
                                    <Film className="h-8 w-8 text-muted-foreground" />
                                  </div>
                                )}
                                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                                <Badge className="absolute bottom-2 left-2 bg-black/60 border-0">
                                  镜头 {shot.number}
                                </Badge>
                              </div>
                              <p className="text-sm text-foreground line-clamp-1">
                                {shot.description}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {shot.duration}秒 | {shot.location}
                              </p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="py-8 text-center">
                          <Film className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                          <p className="text-muted-foreground">该角色暂未出现在任何镜头中</p>
                        </div>
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
