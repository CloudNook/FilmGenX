'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { AppLayout } from '@/components/layout';
import { Card, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import {
  Plus,
  Search,
  Grid3X3,
  List,
  MoreVertical,
  Film,
  Calendar,
  Play,
  Edit,
  Trash2,
  Copy,
  Archive,
  Loader2,
} from 'lucide-react';
import { projectsApi, type ProjectResponse } from '@/lib/api';
import { useRouter } from 'next/navigation';

const statusLabels: Record<string, string> = {
  draft: '草稿',
  active: '制作中',
  archived: '已归档',
};

const statusColors: Record<string, string> = {
  draft: 'bg-muted text-muted-foreground',
  active: 'bg-primary/20 text-primary',
  archived: 'bg-secondary text-secondary-foreground',
};

export default function ProjectsPage() {
  const router = useRouter();
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('updated');
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [loading, setLoading] = useState(true);

  // Create dialog state
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newNovelTitle, setNewNovelTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    projectsApi
      .list()
      .then((data) => setProjects(data.items))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleCreateProject = async () => {
    if (!newName.trim() || !newNovelTitle.trim()) return;
    setCreating(true);
    try {
      const project = await projectsApi.create({
        name: newName.trim(),
        novel_title: newNovelTitle.trim(),
        description: newDesc.trim() || undefined,
      });
      setCreateOpen(false);
      setNewName('');
      setNewNovelTitle('');
      setNewDesc('');
      router.push(`/projects/${project.id}`);
    } catch (err) {
      console.error('Failed to create project:', err);
    } finally {
      setCreating(false);
    }
  };

  const filteredProjects = projects
    .filter(project => {
      const matchesSearch = project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (project.description || '').toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === 'all' || project.status === statusFilter;
      return matchesSearch && matchesStatus;
    })
    .sort((a, b) => {
      if (sortBy === 'updated') {
        return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
      }
      if (sortBy === 'created') {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
      if (sortBy === 'name') {
        return a.name.localeCompare(b.name);
      }
      return 0;
    });

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <AppLayout title="项目列表">
      <div className="p-6 space-y-6">

        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-4">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              <p className="text-sm text-muted-foreground">加载项目...</p>
            </div>
          </div>
        )}

        {!loading && (
        <>

        {/* Header Actions */}
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div className="flex flex-1 gap-3 w-full sm:w-auto">
            {/* Search */}
            <div className="relative flex-1 sm:w-80">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="搜索项目..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 bg-card border-border"
              />
            </div>

            {/* Status Filter */}
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-32 bg-card border-border">
                <SelectValue placeholder="状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="draft">草稿</SelectItem>
                <SelectItem value="in_progress">制作中</SelectItem>
                <SelectItem value="completed">已完成</SelectItem>
                <SelectItem value="archived">已归档</SelectItem>
              </SelectContent>
            </Select>

            {/* Sort */}
            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-32 bg-card border-border">
                <SelectValue placeholder="排序" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="updated">最近更新</SelectItem>
                <SelectItem value="created">创建时间</SelectItem>
                <SelectItem value="name">名称</SelectItem>
                <SelectItem value="progress">进度</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            {/* View Mode Toggle */}
            <div className="flex items-center rounded-lg border border-border bg-card p-1">
              <Button
                variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setViewMode('grid')}
              >
                <Grid3X3 className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setViewMode('list')}
              >
                <List className="h-4 w-4" />
              </Button>
            </div>

            {/* Create Project Button */}
            <Dialog open={createOpen} onOpenChange={setCreateOpen}>
              <DialogTrigger asChild>
                <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
                  <Plus className="h-4 w-4 mr-2" />
                  新建项目
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>新建项目</DialogTitle>
                  <DialogDescription>创建一个新的动画制作项目</DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="project-name">项目名称 *</Label>
                    <Input
                      id="project-name"
                      placeholder="输入项目名称"
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="novel-title">原著名称 *</Label>
                    <Input
                      id="novel-title"
                      placeholder="输入原著小说名称"
                      value={newNovelTitle}
                      onChange={(e) => setNewNovelTitle(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="project-desc">项目描述</Label>
                    <Input
                      id="project-desc"
                      placeholder="简要描述项目（可选）"
                      value={newDesc}
                      onChange={(e) => setNewDesc(e.target.value)}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setCreateOpen(false)}>
                    取消
                  </Button>
                  <Button
                    className="bg-primary text-primary-foreground hover:bg-primary/90"
                    onClick={handleCreateProject}
                    disabled={!newName.trim() || !newNovelTitle.trim() || creating}
                  >
                    {creating && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                    创建
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        {/* Projects Grid/List */}
        {viewMode === 'grid' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredProjects.map((project) => (
              <ProjectCard key={project.id} project={project} formatDate={formatDate} />
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {filteredProjects.map((project) => (
              <ProjectListItem key={project.id} project={project} formatDate={formatDate} />
            ))}
          </div>
        )}

        {/* Empty State */}
        {filteredProjects.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted mb-4">
              <Film className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">没有找到项目</h3>
            <p className="text-muted-foreground mb-6">
              {searchQuery || statusFilter !== 'all'
                ? '尝试调整搜索条件或筛选器'
                : '点击上方按钮创建您的第一个项目'}
            </p>
            {!searchQuery && statusFilter === 'all' && (
              <Button
                className="bg-primary text-primary-foreground hover:bg-primary/90"
                onClick={() => setCreateOpen(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                新建项目
              </Button>
            )}
          </div>
        )}
        </>
        )}
      </div>
    </AppLayout>
  );
}

function ProjectCard({
  project,
  formatDate,
}: {
  project: ProjectResponse;
  formatDate: (date: string) => string;
}) {
  return (
    <Card className="group overflow-hidden bg-card border-border hover:border-primary/50 transition-all duration-200">
      {/* Cover Image */}
      <div className="relative aspect-video bg-muted overflow-hidden">
        {project.cover_image_url ? (
          <div
            className="absolute inset-0 bg-cover bg-center transition-transform duration-300 group-hover:scale-105"
            style={{ backgroundImage: `url(${project.cover_image_url})` }}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-secondary to-muted">
            <Film className="h-12 w-12 text-muted-foreground" />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
        
        {/* Hover Actions */}
        <div className="absolute inset-0 flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
          <Link href={`/projects/${project.id}`}>
            <Button size="sm" className="bg-primary text-primary-foreground hover:bg-primary/90">
              <Play className="h-4 w-4 mr-1" />
              打开
            </Button>
          </Link>
        </div>

        {/* Status Badge */}
        <Badge className={`absolute top-3 left-3 ${statusColors[project.status]}`}>
          {statusLabels[project.status]}
        </Badge>

        {/* Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="absolute top-2 right-2 h-8 w-8 bg-black/40 hover:bg-black/60 text-white opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>
              <Edit className="h-4 w-4 mr-2" />
              编辑信息
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Copy className="h-4 w-4 mr-2" />
              复制项目
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Archive className="h-4 w-4 mr-2" />
              归档
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive">
              <Trash2 className="h-4 w-4 mr-2" />
              删除
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <CardContent className="p-4">
        <Link href={`/projects/${project.id}`}>
          <h3 className="font-semibold text-foreground hover:text-primary transition-colors truncate">
            {project.name}
          </h3>
        </Link>
        <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
          {project.description || project.novel_title}
        </p>

        {/* Tags */}
        {project.novel_title && (
          <div className="mt-3 flex flex-wrap gap-1">
            <Badge variant="outline" className="text-xs border-border">
              {project.novel_title}
            </Badge>
          </div>
        )}
      </CardContent>

      <CardFooter className="px-4 pb-4 pt-0 flex flex-col gap-3">
        {/* Stats */}
        <div className="flex items-center justify-between w-full text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Film className="h-3.5 w-3.5" />
            {project.novel_title}
          </span>
          <span className="flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" />
            {formatDate(project.updated_at)}
          </span>
        </div>
      </CardFooter>
    </Card>
  );
}

function ProjectListItem({
  project,
  formatDate,
}: {
  project: ProjectResponse;
  formatDate: (date: string) => string;
}) {
  return (
    <Card className="bg-card border-border hover:border-primary/50 transition-all duration-200">
      <div className="flex items-center gap-4 p-4">
        {/* Thumbnail */}
        <div className="relative h-20 w-32 rounded-lg overflow-hidden bg-muted shrink-0">
          {project.cover_image_url ? (
            <div
              className="absolute inset-0 bg-cover bg-center"
              style={{ backgroundImage: `url(${project.cover_image_url})` }}
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-secondary to-muted">
              <Film className="h-8 w-8 text-muted-foreground" />
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Link href={`/projects/${project.id}`}>
              <h3 className="font-semibold text-foreground hover:text-primary transition-colors">
                {project.name}
              </h3>
            </Link>
            <Badge className={`text-xs ${statusColors[project.status]}`}>
              {statusLabels[project.status]}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground line-clamp-1 mb-2">
            {project.description || project.novel_title}
          </p>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Film className="h-3.5 w-3.5" />
              {project.novel_title}
            </span>
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              更新于 {formatDate(project.updated_at)}
            </span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 shrink-0">
          <Link href={`/projects/${project.id}`}>
            <Button size="sm" className="bg-primary text-primary-foreground hover:bg-primary/90">
              <Play className="h-4 w-4 mr-1" />
              打开
            </Button>
          </Link>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <Edit className="h-4 w-4 mr-2" />
                编辑信息
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Copy className="h-4 w-4 mr-2" />
                复制项目
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Archive className="h-4 w-4 mr-2" />
                归档
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-destructive">
                <Trash2 className="h-4 w-4 mr-2" />
                删除
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </Card>
  );
}
