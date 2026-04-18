'use client';

import { use, useCallback, useEffect, useState } from 'react';
import {
  charactersApi,
  projectsApi,
  tasksApi,
  type CharacterResponse,
  type ProjectResponse,
  type TaskResponse,
} from '@/lib/api';
import { AppLayout } from '@/components/layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Image as ImageIcon,
  Loader2,
  Plus,
  Search,
  Sparkles,
  Trash2,
  Upload,
  Users,
} from 'lucide-react';
import { toast } from 'sonner';

const FINAL_TASK_STATES = new Set(['success', 'completed', 'failed', 'cancelled']);
const SUCCESS_TASK_STATES = new Set(['success', 'completed']);

const STYLE_PRESETS = [
  { value: 'anime', label: 'Anime' },
  { value: 'cinematic', label: 'Cinematic' },
  { value: 'realistic', label: 'Realistic' },
  { value: 'sketch', label: 'Sketch' },
];

function sleep(ms: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

// 主页面
export default function CharactersPage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId } = use(params);
  const projectIdNum = Number(projectId);

  const [project, setProject] = useState<ProjectResponse | null>(null);
  const [characters, setCharacters] = useState<CharacterResponse[]>([]);
  const [selectedCharId, setSelectedCharId] = useState<number | null>(null);
  const [charDetail, setCharDetail] = useState<CharacterResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newCharName, setNewCharName] = useState('');
  const [creating, setCreating] = useState(false);
  const [uploadingPic, setUploadingPic] = useState(false);

  const [genPrompt, setGenPrompt] = useState('');
  const [genNegativePrompt, setGenNegativePrompt] = useState('');
  const [genAspectRatio, setGenAspectRatio] = useState('16:9');
  const [genResolution, setGenResolution] = useState('1K');
  const [genStylePreset, setGenStylePreset] = useState('cinematic');
  const [useCurrentPicAsRef, setUseCurrentPicAsRef] = useState(true);
  const [manualRefUrl, setManualRefUrl] = useState('');
  const [generatingAsset, setGeneratingAsset] = useState(false);

  useEffect(() => {
    if (isNaN(projectIdNum)) return;

    Promise.all([
      projectsApi.get(projectIdNum).catch(() => null),
      charactersApi.list(projectIdNum),
    ])
      .then(([projectRes, charsRes]) => {
        setProject(projectRes);
        setCharacters(charsRes.items);
        if (charsRes.items.length > 0) setSelectedCharId(charsRes.items[0].id);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load data:', err);
        setLoading(false);
      });
  }, [projectIdNum]);

  const loadCharDetail = useCallback(async () => {
    if (!selectedCharId || isNaN(projectIdNum)) {
      setCharDetail(null);
      return null;
    }
    try {
      const detail = await charactersApi.get(projectIdNum, selectedCharId);
      setCharDetail(detail);
      return detail;
    } catch {
      setCharDetail(null);
      return null;
    }
  }, [selectedCharId, projectIdNum]);

  useEffect(() => {
    loadCharDetail();
  }, [loadCharDetail]);

  const handleCreateCharacter = useCallback(async () => {
    if (!newCharName.trim()) return;
    setCreating(true);
    try {
      const char = await charactersApi.create(projectIdNum, { name: newCharName.trim() });
      setCharacters((prev) => [char, ...prev]);
      setSelectedCharId(char.id);
      setIsCreateDialogOpen(false);
      setNewCharName('');
      toast.success('角色创建成功');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '创建失败');
    } finally {
      setCreating(false);
    }
  }, [projectIdNum, newCharName]);

  const handleDeleteCharacter = useCallback(async (charId: number) => {
    if (!confirm('确定要删除这个角色吗？')) return;
    try {
      await charactersApi.delete(projectIdNum, charId);
      setCharacters((prev) => prev.filter((c) => c.id !== charId));
      if (selectedCharId === charId) {
        setSelectedCharId(null);
        setCharDetail(null);
      }
      toast.success('角色已删除');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    }
  }, [projectIdNum, selectedCharId]);

  const handleUploadPic = useCallback(async (file: File) => {
    if (!selectedCharId) return;
    setUploadingPic(true);
    try {
      const updated = await charactersApi.uploadPic(projectIdNum, selectedCharId, file);
      setCharDetail(updated);
      setCharacters((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      toast.success('角色图片上传成功');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '上传失败');
    } finally {
      setUploadingPic(false);
    }
  }, [projectIdNum, selectedCharId]);

  const handleDeletePic = useCallback(async () => {
    if (!selectedCharId || !confirm('确定要删除角色图片吗？')) return;
    try {
      await charactersApi.deletePic(projectIdNum, selectedCharId);
      if (charDetail) {
        const updated = { ...charDetail, pic_url: null, pic_name: null };
        setCharDetail(updated);
        setCharacters((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      }
      toast.success('角色图片已删除');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除失败');
    }
  }, [projectIdNum, selectedCharId, charDetail]);

  const handleGenerateCharacterAsset = useCallback(async () => {
    if (!selectedCharId) {
      toast.error('请先选择角色');
      return;
    }
    if (!genPrompt.trim()) {
      toast.error('请输入提示词');
      return;
    }

    const refUrls = Array.from(
      new Set(
        [
          useCurrentPicAsRef ? charDetail?.pic_url : null,
          manualRefUrl.trim() || null,
        ].filter((item): item is string => Boolean(item)),
      ),
    );

    setGeneratingAsset(true);
    try {
      const task = await tasksApi.triggerImage({
        project_id: projectIdNum,
        character_id: selectedCharId,
        prompt: genPrompt.trim(),
        negative_prompt: genNegativePrompt.trim() || undefined,
        aspect_ratio: genAspectRatio,
        resolution: genResolution,
        style_preset: genStylePreset || undefined,
        reference_image_urls: refUrls.length > 0 ? refUrls : undefined,
        save_to_shot: true,
      });

      let latestTask: TaskResponse | null = null;
      for (let i = 0; i < 120; i += 1) {
        await sleep(2000);
        const currentTask = await tasksApi.get(task.id);
        if (FINAL_TASK_STATES.has(currentTask.status)) {
          latestTask = currentTask;
          break;
        }
      }

      if (!latestTask) {
        throw new Error('任务执行超时，请稍后在素材库查看结果');
      }
      if (!SUCCESS_TASK_STATES.has(latestTask.status)) {
        throw new Error(latestTask.error_message || '生成失败');
      }

      const updated = await charactersApi.get(projectIdNum, selectedCharId);
      setCharDetail(updated);
      setCharacters((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      toast.success(refUrls.length > 0 ? '图生图生成成功' : '文生图生成成功');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '生成失败');
    } finally {
      setGeneratingAsset(false);
    }
  }, [
    charDetail?.pic_url,
    genAspectRatio,
    genNegativePrompt,
    genPrompt,
    genResolution,
    genStylePreset,
    manualRefUrl,
    projectIdNum,
    selectedCharId,
    useCurrentPicAsRef,
  ]);

  const filteredCharacters = characters.filter((char) =>
    char.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    char.char_code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <AppLayout projectId={projectId}>
        <div className="h-full flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout
      projectId={projectId}
      breadcrumbs={[
        { label: '项目', href: '/projects' },
        { label: project?.name || '加载中...', href: `/projects/${projectId}` },
        { label: '素材库', href: `/projects/${projectId}/materials` },
        { label: '角色管理' },
      ]}
    >
      <div className="h-[calc(100vh-4rem)] flex">
        <div className="w-80 border-r border-border bg-card flex flex-col">
          <div className="p-4 border-b border-border space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">角色列表</h2>
              <Badge variant="outline">{characters.length}</Badge>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="搜索角色..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Button className="w-full" onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              创建角色
            </Button>
            <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>创建新角色</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">角色名称 *</label>
                    <Input
                      placeholder="输入角色名称"
                      value={newCharName}
                      onChange={(e) => setNewCharName(e.target.value)}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                    取消
                  </Button>
                  <Button onClick={handleCreateCharacter} disabled={!newCharName.trim() || creating}>
                    {creating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                    创建
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
                      {char.pic_url ? <AvatarImage src={char.pic_url} alt={char.name} /> : null}
                      <AvatarFallback className="bg-primary/10 text-primary text-lg">
                        {char.name.slice(0, 1)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <span className="font-medium text-sm truncate block">{char.name}</span>
                      <p className="text-xs text-muted-foreground truncate">{char.char_code}</p>
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
              {filteredCharacters.length === 0 ? (
                <div className="py-8 text-center text-muted-foreground">
                  <Users className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>没有找到角色</p>
                </div>
              ) : null}
            </div>
          </ScrollArea>
        </div>

        <div className="flex-1 bg-background overflow-y-auto">
          {charDetail ? (
            <div className="p-6 space-y-6">
              <div className="flex flex-col gap-4 rounded-2xl border bg-card p-6 lg:flex-row lg:items-start lg:justify-between">
                <div className="flex items-start gap-4">
                  <Avatar className="h-20 w-20">
                    {charDetail.pic_url ? <AvatarImage src={charDetail.pic_url} alt={charDetail.name} /> : null}
                    <AvatarFallback className="bg-primary/10 text-primary text-3xl">
                      {charDetail.name.slice(0, 1)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <h1 className="text-2xl font-bold text-foreground">{charDetail.name}</h1>
                      <Badge variant="outline">{charDetail.char_code}</Badge>
                    </div>
                  </div>
                </div>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>角色图片</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {charDetail.pic_url ? (
                      <div className="relative inline-block group">
                        <img
                          src={charDetail.pic_url}
                          alt={charDetail.name}
                          className="w-48 h-64 object-cover rounded-lg border"
                        />
                        <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2 rounded-lg">
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={handleDeletePic}
                            disabled={uploadingPic}
                          >
                            <Trash2 className="h-4 w-4 mr-1" />
                            删除
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div
                        className="w-48 h-64 border-2 border-dashed rounded-lg flex flex-col items-center justify-center gap-3 cursor-pointer hover:border-primary/50 transition-colors"
                        onClick={() => document.getElementById('char-pic-input')?.click()}
                      >
                        {uploadingPic ? (
                          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                        ) : (
                          <>
                            <ImageIcon className="h-8 w-8 text-muted-foreground" />
                            <span className="text-sm text-muted-foreground">上传角色图片</span>
                          </>
                        )}
                      </div>
                    )}
                    <input
                      id="char-pic-input"
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => e.target.files?.[0] && handleUploadPic(e.target.files[0])}
                      disabled={uploadingPic}
                    />
                    {charDetail.pic_url ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => document.getElementById('char-pic-input')?.click()}
                        disabled={uploadingPic}
                      >
                        {uploadingPic ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
                        更换图片
                      </Button>
                    ) : null}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>AI 生成素材</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">提示词 *</label>
                    <Textarea
                      value={genPrompt}
                      onChange={(e) => setGenPrompt(e.target.value)}
                      placeholder="输入角色生成提示词，如：国风动漫少女，银发，红色战甲，正面半身像..."
                      rows={4}
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">负向提示词（可选）</label>
                    <Input
                      value={genNegativePrompt}
                      onChange={(e) => setGenNegativePrompt(e.target.value)}
                      placeholder="如：模糊、低清晰度、畸形手"
                    />
                  </div>

                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">画幅</label>
                      <select
                        className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                        value={genAspectRatio}
                        onChange={(e) => setGenAspectRatio(e.target.value)}
                        disabled={generatingAsset}
                      >
                        <option value="1:1">1:1</option>
                        <option value="16:9">16:9</option>
                        <option value="9:16">9:16</option>
                        <option value="4:3">4:3</option>
                        <option value="3:4">3:4</option>
                      </select>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">分辨率</label>
                      <select
                        className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                        value={genResolution}
                        onChange={(e) => setGenResolution(e.target.value)}
                        disabled={generatingAsset}
                      >
                        <option value="512">512</option>
                        <option value="1K">1K</option>
                        <option value="2K">2K</option>
                        <option value="4K">4K</option>
                      </select>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">风格</label>
                      <select
                        className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                        value={genStylePreset}
                        onChange={(e) => setGenStylePreset(e.target.value)}
                        disabled={generatingAsset}
                      >
                        {STYLE_PRESETS.map((item) => (
                          <option key={item.value} value={item.value}>
                            {item.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="space-y-2 rounded-lg border bg-muted/20 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium">图生图参考</span>
                      {charDetail.pic_url ? (
                        <Button
                          type="button"
                          size="sm"
                          variant={useCurrentPicAsRef ? 'default' : 'outline'}
                          onClick={() => setUseCurrentPicAsRef((prev) => !prev)}
                          disabled={generatingAsset}
                        >
                          {useCurrentPicAsRef ? '已使用当前角色图' : '使用当前角色图'}
                        </Button>
                      ) : (
                        <span className="text-xs text-muted-foreground">当前角色没有封面图，可仅使用下方 URL</span>
                      )}
                    </div>
                    <Input
                      value={manualRefUrl}
                      onChange={(e) => setManualRefUrl(e.target.value)}
                      placeholder="可选：输入参考图 URL（支持图生图）"
                      disabled={generatingAsset}
                    />
                    <p className="text-xs text-muted-foreground">
                      不填参考图时会走文生图；填写任一参考图后会自动走图生图。
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      onClick={handleGenerateCharacterAsset}
                      disabled={generatingAsset || !genPrompt.trim()}
                    >
                      {generatingAsset ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                      {generatingAsset ? '生成中...' : '生成并保存到角色'}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-center">
              <div>
                <Users className="h-16 w-16 mx-auto text-muted-foreground mb-4 opacity-50" />
                <h3 className="text-lg font-semibold mb-2">选择一个角色</h3>
                <p className="text-muted-foreground">从左侧列表选择角色</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
