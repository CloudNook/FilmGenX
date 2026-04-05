'use client';

import { use, useEffect, useState, useCallback, useRef } from 'react';
import { AppLayout } from '@/components/layout';
import {
  projectsApi,
  charactersApi,
  tasksApi,
  type ProjectResponse,
  type CharacterResponse,
  type CharacterDetailResponse,
  type CharacterVersionResponse,
} from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
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
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  Plus,
  Search,
  MoreVertical,
  Edit,
  Trash2,
  Sparkles,
  Users,
  Loader2,
  Upload,
  Image as ImageIcon,
  X,
  RefreshCw,
  Eye,
  Wand2,
  ChevronDown,
  Check,
  Clock,
} from 'lucide-react';
import { toast } from 'sonner';

// 预定义状态类型
const CHARACTER_STATE_TYPES: Record<string, string> = {
  anger: '愤怒',
  happy: '开心',
  sad: '悲伤',
  surprise: '惊讶',
  fear: '恐惧',
  determination: '坚定',
  skill_release: '释放技能',
  battle_stance: '战斗姿态',
  injured: '受伤',
  exhausted: '精疲力尽',
  meditation: '冥想',
  triumph: '胜利',
};

const VIEW_TYPES: Record<string, string> = {
  front: '正面',
  side: '侧面',
  back: '背面',
};

// 图片上传组件
function ImageUploader({
  onUpload,
  accept = 'image/*',
  disabled = false,
  className = '',
}: {
  onUpload: (file: File) => Promise<void>;
  accept?: string;
  disabled?: boolean;
  className?: string;
}) {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (file: File) => {
    if (disabled || uploading) return;
    setUploading(true);
    try {
      await onUpload(file);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      handleUpload(file);
    }
  };

  return (
    <div
      className={`relative border-2 border-dashed rounded-lg transition-colors ${
        dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
      } ${className}`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
        disabled={disabled || uploading}
      />
      <div
        className="flex flex-col items-center justify-center p-4 cursor-pointer"
        onClick={() => inputRef.current?.click()}
      >
        {uploading ? (
          <Loader2 className="h-8 w-8 animate-spin text-primary mb-2" />
        ) : (
          <Upload className="h-8 w-8 text-muted-foreground mb-2" />
        )}
        <span className="text-sm text-muted-foreground">
          {uploading ? '上传中...' : '拖拽或点击上传'}
        </span>
      </div>
    </div>
  );
}

// 图片预览卡片
function ImageCard({
  url,
  label,
  onDelete,
  onGenerate,
  isGenerating = false,
}: {
  url: string | null;
  label: string;
  onDelete?: () => void;
  onGenerate?: () => void;
  isGenerating?: boolean;
}) {
  const [showFull, setShowFull] = useState(false);

  return (
    <>
      <div className="group relative aspect-[2/3] bg-secondary rounded-lg overflow-hidden border border-border">
        {url ? (
          <>
            <img
              src={url}
              alt={label}
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
              <Button
                size="icon"
                variant="secondary"
                onClick={() => setShowFull(true)}
              >
                <Eye className="h-4 w-4" />
              </Button>
              {onDelete && (
                <Button
                  size="icon"
                  variant="destructive"
                  onClick={onDelete}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          </>
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center text-muted-foreground">
            {isGenerating ? (
              <>
                <Loader2 className="h-8 w-8 animate-spin mb-2" />
                <span className="text-xs">生成中...</span>
              </>
            ) : (
              <>
                <ImageIcon className="h-8 w-8 mb-2 opacity-50" />
                <span className="text-xs">{label}</span>
                {onGenerate && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="mt-2"
                    onClick={onGenerate}
                  >
                    <Wand2 className="h-3 w-3 mr-1" />
                    AI生成
                  </Button>
                )}
              </>
            )}
          </div>
        )}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-2">
          <span className="text-xs text-white font-medium">{label}</span>
        </div>
      </div>

      {/* 全屏预览 */}
      <Dialog open={showFull} onOpenChange={setShowFull}>
        <DialogContent className="max-w-4xl">
          <img src={url!} alt={label} className="w-full h-auto" />
        </DialogContent>
      </Dialog>
    </>
  );
}

// 三视图组件
function ThreeViewSection({
  projectId,
  characterId,
  version,
  onRefresh,
}: {
  projectId: number;
  characterId: number;
  version: CharacterVersionResponse;
  onRefresh: () => void;
}) {
  const [generating, setGenerating] = useState<string | null>(null);

  const handleUpload = async (viewType: 'front' | 'side' | 'back', file: File) => {
    try {
      await charactersApi.uploadViewImage(projectId, characterId, version.id, viewType, file);
      toast.success(`${VIEW_TYPES[viewType]}视图上传成功`);
      onRefresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '上传失败');
    }
  };

  const handleGenerate = async (viewType: 'front' | 'side' | 'back') => {
    setGenerating(viewType);
    try {
      const result = await charactersApi.generateViewImage(projectId, characterId, version.id, viewType);
      toast.success(result.message || '生成任务已提交');
      // 轮询任务状态
      pollTaskStatus(result.task_id, onRefresh);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '生成失败');
      setGenerating(null);
    }
  };

  const handleDelete = async (viewType: 'front' | 'side' | 'back') => {
    try {
      await charactersApi.deleteViewImage(projectId, characterId, version.id, viewType);
      toast.success('删除成功');
      onRefresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    }
  };

  const views: Array<{ key: 'front' | 'side' | 'back'; url: string | null }> = [
    { key: 'front', url: version.view_front_url },
    { key: 'side', url: version.view_side_url },
    { key: 'back', url: version.view_back_url },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">三视图</h3>
        <Badge variant="outline">
          {views.filter(v => v.url).length}/3 已完成
        </Badge>
      </div>
      <div className="grid grid-cols-3 gap-4">
        {views.map(({ key, url }) => (
          <div key={key} className="space-y-2">
            <ImageCard
              url={url}
              label={VIEW_TYPES[key]}
              onDelete={url ? () => handleDelete(key) : undefined}
              onGenerate={!url ? () => handleGenerate(key) : undefined}
              isGenerating={generating === key}
            />
            {!url && (
              <ImageUploader
                onUpload={(file) => handleUpload(key, file)}
                className="h-16"
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// 状态图片组件
function StateImagesSection({
  projectId,
  characterId,
  version,
  onRefresh,
}: {
  projectId: number;
  characterId: number;
  version: CharacterVersionResponse;
  onRefresh: () => void;
}) {
  const [selectedState, setSelectedState] = useState<string>('anger');
  const [stateDesc, setStateDesc] = useState('');
  const [generating, setGenerating] = useState<string | null>(null);
  const [showGenerateDialog, setShowGenerateDialog] = useState(false);

  const stateImages = version.state_images || {};

  const handleUpload = async (stateType: string, file: File) => {
    try {
      await charactersApi.uploadStateImage(projectId, characterId, version.id, stateType, file);
      toast.success(`${CHARACTER_STATE_TYPES[stateType] || stateType}图片上传成功`);
      onRefresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '上传失败');
    }
  };

  const handleGenerate = async () => {
    setGenerating(selectedState);
    setShowGenerateDialog(false);
    try {
      const result = await charactersApi.generateStateImage(
        projectId,
        characterId,
        version.id,
        selectedState,
        stateDesc || undefined
      );
      toast.success(result.message || '生成任务已提交');
      pollTaskStatus(result.task_id, onRefresh);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '生成失败');
      setGenerating(null);
    }
  };

  const handleDelete = async (stateType: string) => {
    try {
      await charactersApi.deleteStateImage(projectId, characterId, version.id, stateType);
      toast.success('删除成功');
      onRefresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">状态图片</h3>
        <Dialog open={showGenerateDialog} onOpenChange={setShowGenerateDialog}>
          <DialogTrigger asChild>
            <Button size="sm" variant="outline">
              <Wand2 className="h-4 w-4 mr-2" />
              生成新状态
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>生成状态图片</DialogTitle>
              <DialogDescription>选择要生成的状态类型</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">状态类型</label>
                <Select value={selectedState} onValueChange={setSelectedState}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(CHARACTER_STATE_TYPES).map(([key, label]) => (
                      <SelectItem key={key} value={key}>
                        {label}
                        {stateImages[key] && <Check className="inline ml-2 h-3 w-3" />}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">详细描述（可选）</label>
                <Textarea
                  value={stateDesc}
                  onChange={(e) => setStateDesc(e.target.value)}
                  placeholder="描述该状态的具体表现..."
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowGenerateDialog(false)}>
                取消
              </Button>
              <Button onClick={handleGenerate} disabled={generating === selectedState}>
                {generating === selectedState && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                开始生成
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* 已有状态图片网格 */}
      <div className="grid grid-cols-4 gap-4">
        {Object.entries(CHARACTER_STATE_TYPES).map(([key, label]) => {
          const url = stateImages[key];
          const isGenerating = generating === key;
          return (
            <div key={key} className="space-y-2">
              <ImageCard
                url={url || null}
                label={label}
                onDelete={url ? () => handleDelete(key) : undefined}
                onGenerate={!url ? () => { setSelectedState(key); setShowGenerateDialog(true); } : undefined}
                isGenerating={isGenerating}
              />
              {!url && (
                <ImageUploader
                  onUpload={(file) => handleUpload(key, file)}
                  className="h-12"
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// 参考图组件
function ReferenceImagesSection({
  projectId,
  characterId,
  version,
  onRefresh,
}: {
  projectId: number;
  characterId: number;
  version: CharacterVersionResponse;
  onRefresh: () => void;
}) {
  const handleUpload = async (file: File) => {
    try {
      await charactersApi.uploadReferenceImage(projectId, characterId, version.id, file);
      toast.success('参考图上传成功');
      onRefresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '上传失败');
    }
  };

  const handleDelete = async (index: number) => {
    try {
      await charactersApi.deleteReferenceImage(projectId, characterId, version.id, index);
      toast.success('删除成功');
      onRefresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    }
  };

  const urls = version.reference_image_urls || [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">参考图</h3>
        <Badge variant="outline">{urls.length} 张</Badge>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {urls.map((url, idx) => (
          <ImageCard
            key={idx}
            url={url}
            label={`参考图 ${idx + 1}`}
            onDelete={() => handleDelete(idx)}
          />
        ))}
        {urls.length < 8 && (
          <div className="space-y-2">
            <div className="aspect-[2/3]">
              <ImageUploader
                onUpload={handleUpload}
                className="h-full"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// 版本详情组件
function VersionDetailCard({
  projectId,
  characterId,
  version,
  onRefresh,
  onEdit,
}: {
  projectId: number;
  characterId: number;
  version: CharacterVersionResponse;
  onRefresh: () => void;
  onEdit: () => void;
}) {
  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">{version.label}</CardTitle>
            <CardDescription className="text-sm">{version.version_code}</CardDescription>
          </div>
          <Button size="sm" variant="ghost" onClick={onEdit}>
            <Edit className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* 基本信息 */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          {version.age_description && (
            <div>
              <span className="text-muted-foreground">年龄</span>
              <p className="text-foreground">{version.age_description}</p>
            </div>
          )}
          {version.height_cm && (
            <div>
              <span className="text-muted-foreground">身高</span>
              <p className="text-foreground">{version.height_cm}cm</p>
            </div>
          )}
          {version.dou_qi_level && (
            <div>
              <span className="text-muted-foreground">境界</span>
              <p className="text-foreground">{version.dou_qi_level}</p>
            </div>
          )}
          {version.dou_qi_color && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">斗气颜色</span>
              <span
                className="h-4 w-4 rounded-full border"
                style={{ backgroundColor: version.dou_qi_color }}
              />
            </div>
          )}
        </div>

        <Separator />

        {/* 三视图 */}
        <ThreeViewSection
          projectId={projectId}
          characterId={characterId}
          version={version}
          onRefresh={onRefresh}
        />

        <Separator />

        {/* 状态图片 */}
        <StateImagesSection
          projectId={projectId}
          characterId={characterId}
          version={version}
          onRefresh={onRefresh}
        />

        <Separator />

        {/* 参考图 */}
        <ReferenceImagesSection
          projectId={projectId}
          characterId={characterId}
          version={version}
          onRefresh={onRefresh}
        />

        {/* 提示词 */}
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
  );
}

// 轮询任务状态
async function pollTaskStatus(taskId: number, onComplete: () => void) {
  const maxAttempts = 60; // 最多轮询60次（5分钟）
  let attempts = 0;

  const poll = async () => {
    try {
      const task = await tasksApi.get(taskId);
      if (task.status === 'success') {
        toast.success('生成完成');
        onComplete();
        return;
      }
      if (task.status === 'failed') {
        toast.error(task.error_message || '生成失败');
        onComplete();
        return;
      }
      attempts++;
      if (attempts < maxAttempts) {
        setTimeout(poll, 5000);
      } else {
        toast.warning('生成时间较长，请稍后刷新查看');
        onComplete();
      }
    } catch {
      attempts++;
      if (attempts < maxAttempts) {
        setTimeout(poll, 5000);
      }
    }
  };

  poll();
}

// 主页面
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
  const loadCharDetail = useCallback(() => {
    if (!selectedCharId || isNaN(projectIdNum)) return;
    charactersApi
      .get(projectIdNum, selectedCharId)
      .then(setCharDetail)
      .catch(() => setCharDetail(null));
  }, [selectedCharId, projectIdNum]);

  useEffect(() => {
    loadCharDetail();
  }, [loadCharDetail]);

  const handleCreateCharacter = useCallback(async () => {
    if (!newCharName.trim()) return;
    setCreating(true);
    try {
      const char = await charactersApi.create(projectIdNum, {
        name: newCharName.trim(),
        role_description: newCharDesc.trim() || undefined,
      });
      setCharacters(prev => [char, ...prev]);
      setSelectedCharId(char.id);
      setIsCreateDialogOpen(false);
      setNewCharName('');
      setNewCharDesc('');
      toast.success('角色创建成功');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '创建失败');
    } finally {
      setCreating(false);
    }
  }, [projectIdNum, newCharName, newCharDesc]);

  const handleDeleteCharacter = useCallback(async (charId: number) => {
    if (!confirm('确定要删除这个角色吗？')) return;
    try {
      await charactersApi.delete(projectIdNum, charId);
      setCharacters(prev => prev.filter(c => c.id !== charId));
      if (selectedCharId === charId) {
        setSelectedCharId(null);
        setCharDetail(null);
      }
      toast.success('角色已删除');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
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
      <AppLayout>
        <div className="h-full flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="h-[calc(100vh-4rem)] flex">
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
                  <DialogDescription>填写角色的基本信息</DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">角色名称 *</label>
                    <Input
                      placeholder="输入角色名称"
                      className="bg-secondary border-border"
                      value={newCharName}
                      onChange={(e) => setNewCharName(e.target.value)}
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
                    disabled={!newCharName.trim() || creating}
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
                    <div className="flex items-center gap-2 flex-wrap">
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
                  <TabsTrigger value="features">特征设定</TabsTrigger>
                  <TabsTrigger value="relationships">关系设定</TabsTrigger>
                </TabsList>

                {/* Versions Tab */}
                <TabsContent value="versions" className="space-y-4">
                  {charDetail.versions.length === 0 ? (
                    <div className="text-center py-12">
                      <Users className="h-12 w-12 mx-auto text-muted-foreground mb-3 opacity-50" />
                      <p className="text-muted-foreground">暂无角色版本</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        为角色创建不同时期的版本（如少年期、成年期等）
                      </p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      {charDetail.versions.map((version) => (
                        <VersionDetailCard
                          key={version.id}
                          projectId={projectIdNum}
                          characterId={charDetail.id}
                          version={version}
                          onRefresh={loadCharDetail}
                          onEdit={() => {}}
                        />
                      ))}
                    </div>
                  )}
                </TabsContent>

                {/* Features Tab */}
                <TabsContent value="features" className="space-y-4">
                  <Card className="bg-card border-border">
                    <CardHeader>
                      <CardTitle className="text-base">跨版本固定特征</CardTitle>
                      <CardDescription>在不同版本中保持不变的形象特征</CardDescription>
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
                      <CardDescription>角色常见表情的绘制参考</CardDescription>
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
                      <CardDescription>角色典型动作的绘制参考</CardDescription>
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
                      <CardDescription>与其他角色的关系设定</CardDescription>
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
