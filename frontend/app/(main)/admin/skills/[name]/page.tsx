'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { AppLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ArrowLeft, Save, Loader2, RefreshCw, FileText, Trash2, Brain, CheckCircle } from 'lucide-react';
import { skillsApi, type SkillResponse, type SkillParseResult, type SkillUploadResponse } from '@/lib/api';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';

const FIELD_LABELS: Record<string, string> = {
  name: '名称 (name)',
  title: '标题 (title)',
  description: '描述 (description)',
  content: '核心指令 (content)',
  parameters: '参数定义 (parameters)',
  examples: '使用示例 (examples)',
  constraints: '约束条件 (constraints)',
  category: '领域分类 (category)',
  difficulty: '难度 (difficulty)',
  tags: '标签 (tags)',
  author: '作者 (author)',
  metadata: '元数据 (metadata)',
};

const CATEGORIES = ['剧本', '灯光', '运镜', '调色', '音效', '特效', '服装', '道具', '合成', '其他'];
const DIFFICULTIES = [
  { value: 'beginner', label: '入门' },
  { value: 'intermediate', label: '进阶' },
  { value: 'advanced', label: '专家' },
];

// ===========================================================================
// 主页面
// ===========================================================================
export default function SkillDetailPage({ params }: { params: { name: string } }) {
  const router = useRouter();
  const [skill, setSkill] = useState<SkillResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [form, setForm] = useState<Partial<SkillResponse>>({});

  // 编辑表单状态
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [content, setContent] = useState('');
  const [category, setCategory] = useState<string>('');
  const [difficulty, setDifficulty] = useState<string>('');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [examples, setExamples] = useState<string[]>(['']);
  const [constraints, setConstraints] = useState<string[]>(['']);
  const [exampleInputs, setExampleInputs] = useState<string[]>([]);
  const [constraintInputs, setConstraintInputs] = useState<string[]>([]);
  const [is_active, setIsActive] = useState(true);
  const [author, setAuthor] = useState('');

  const initialLoad = useRef(false);

  const fetchSkill = useCallback(async () => {
    if (initialLoad.current) return;
    initialLoad.current = true;
    setLoading(true);
    try {
      const res = await skillsApi.get(params.name);
      setSkill(res);
      setEditMode(false);
      // 初始化表单
      setTitle(res.title || '');
      setDescription(res.description || '');
      setContent(res.content || '');
      setCategory(res.category || '');
      setDifficulty(res.difficulty || '');
      setTags(res.tags || []);
      setExamples(res.examples || ['']);
      setConstraints(res.constraints || ['']);
      setIsActive(res.is_active);
      setAuthor(res.author || '');
    } catch (e) {
      toast.error(`加载失败: ${(e as Error).message}`);
      router.back();
    } finally {
      setLoading(false);
    }
  }, [params.name]);

  useEffect(() => {
    fetchSkill();
  }, [fetchSkill]);

  const handleSave = async () => {
    if (!skill) return;
    setSaving(true);
    try {
      const updateData: Parameters<typeof skillsApi.update>[1] = {
        title: title || undefined,
        description: description || undefined,
        content: content || undefined,
        category: category || undefined,
        difficulty: difficulty || undefined,
        tags,
        examples,
        constraints,
        is_active,
        author: author || undefined,
      };
      await skillsApi.update(skill.name, updateData);
      toast.success('保存成功');
      setEditMode(false);
      fetchSkill();
    } catch (e) {
      toast.error(`保存失败: ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (skill) {
      setTitle(skill.title || '');
      setDescription(skill.description || '');
      setContent(skill.content || '');
      setCategory(skill.category || '');
      setDifficulty(skill.difficulty || '');
      setTags(skill.tags || []);
      setExamples(skill.examples || ['']);
      setConstraints(skill.constraints || ['']);
      setIsActive(skill.is_active);
      setAuthor(skill.author || '');
    }
    setEditMode(false);
  };

  const handleAddTag = () => {
    if (tagInput.trim()) {
      setTags([...tags, tagInput.trim()]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (index: number) => {
    setTags(tags.filter((_, i) => i !== index));
  };

  const handleAddExample = () => {
    setExamples([...examples, '']);
    setExampleInputs([...exampleInputs, '']);
  };

  const handleRemoveExample = (index: number) => {
    setExamples(examples.filter((_, i) => i !== index));
    setExampleInputs(exampleInputs.filter((_, i) => i !== index));
  };

  const handleAddConstraint = () => {
    setConstraints([...constraints, '']);
    setConstraintInputs([...constraintInputs, '']);
  };

  const handleRemoveConstraint = (index: number) => {
    setConstraints(constraints.filter((_, i) => i !== index));
    setConstraintInputs(constraintInputs.filter((_, i) => i !== index));
  };

  const handleDownloadMarkdown = async () => {
    if (!skill) return;
    try {
      const markdown = await skillsApi.downloadMarkdown(skill.name);
      const blob = new Blob([markdown], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${skill.name}.md`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('下载成功');
    } catch (e) {
      toast.error(`下载失败: ${(e as Error).message}`);
    }
  };

  const handleReparse = async () => {
    if (!skill?.raw_markdown) {
      toast.error('Skill 没有原始 Markdown');
      return;
    }
    try {
      const res = await skillsApi.preview(skill.raw_markdown);
      // 如果解析出更多字段，提示用户保存
      if (res.missing_fields.length === 0 && Object.keys(res.fields).length > Object.keys(skill.raw_markdown || '').length) {
        toast.success('Markdown 已解析，没有缺失字段');
      } else if (res.missing_fields.length > 0) {
        toast.success(`解析完成，发现 ${res.missing_fields.length} 个缺失字段`);
        // 进入编辑模式
        setEditMode(true);
      } else {
        toast.success('Markdown 解析完成');
      }
    } catch (e) {
      toast.error(`解析失败: ${(e as Error).message}`);
    }
  };

  if (loading) {
    return (
      <AppLayout title={`Skill: ${params.name}`} description={loading ? '加载中...' : 'Skill 详情'}>
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppLayout>
    );
  }

  if (!skill) {
    return (
      <AppLayout title={`Skill: ${params.name}`} description="未找到">
        <div className="p-6">
          <p className="text-muted-foreground">Skill 不存在或已被删除。</p>
          <Button variant="outline" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            返回
          </Button>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout
      title={skill.title || skill.name}
      description={`Skill 管理 - ${skill.category || '通用'} · ${skill.difficulty || '未设置难度'}`}
    >
      <div className="p-6 space-y-6">
        {/* 顶部操作栏 */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <Button variant="outline" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            返回
          </Button>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={handleDownloadMarkdown}>
              <FileText className="mr-2 h-4 w-4" />
              下载 SKILL.md
            </Button>
            {skill.raw_markdown && (
              <Button variant="outline" onClick={handleReparse}>
                <RefreshCw className="mr-2 h-4 w-4" />
                重新解析 Markdown
              </Button>
            )}
            {!editMode ? (
              <Button onClick={() => setEditMode(true)}>
                <Brain className="mr-2 h-4 w-4" />
                编辑
              </Button>
            ) : (
              <>
                <Button
                  variant="outline"
                  onClick={handleCancel}
                  disabled={saving}
                >
                  取消
                </Button>
                <Button onClick={handleSave} disabled={saving}>
                  {saving ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      保存中...
                    </>
                  ) : (
                    <>
                      <Save className="mr-2 h-4 w-4" />
                      保存
                    </>
                  )}
                </Button>
              </>
            )}
          </div>
        </div>

        {/* 编辑模式 */}
        {editMode ? (
          <div className="space-y-6 rounded-lg border p-6 bg-card">
            {/* 基本信息 */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">基本信息</h3>
              <div className="space-y-3">
                {/* 标题 */}
                <div>
                  <Label htmlFor="title">{FIELD_LABELS.title}</Label>
                  <Input
                    id="title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="人类可读标题（可选）"
                  />
                </div>

                {/* 描述 */}
                <div>
                  <Label htmlFor="description">{FIELD_LABELS.description} <span className="text-destructive">*</span></Label>
                  <Textarea
                    id="description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="一句话描述，用于 Agent 判断何时激活"
                    rows={2}
                  />
                </div>

                {/* 领域分类 */}
                <div>
                  <Label htmlFor="category">{FIELD_LABELS.category}</Label>
                  <Select value={category} onValueChange={setCategory}>
                    <SelectTrigger id="category">
                      <SelectValue placeholder="选择领域分类" />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORIES.map((c) => (
                        <SelectItem key={c} value={c}>
                          {c}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* 难度 */}
                <div>
                  <Label htmlFor="difficulty">{FIELD_LABELS.difficulty}</Label>
                  <Select value={difficulty} onValueChange={setDifficulty}>
                    <SelectTrigger id="difficulty">
                      <SelectValue placeholder="选择难度" />
                    </SelectTrigger>
                    <SelectContent>
                      {DIFFICULTIES.map((d) => (
                        <SelectItem key={d.value} value={d.value}>
                          {d.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* 标签 */}
                <div>
                  <Label>{FIELD_LABELS.tags}</Label>
                  <div className="flex flex-wrap gap-2 mb-2">
                    {tags.map((tag, i) => (
                      <Badge key={i} variant="secondary" className="flex items-center gap-1 pr-2">
                        {tag}
                        <button
                          type="button"
                          className="ml-1 hover:bg-destructive/20 rounded-sm p-0.5"
                          onClick={() => handleRemoveTag(i)}
                        >
                          ×
                        </button>
                      </Badge>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Input
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                      placeholder="输入标签后回车添加"
                      className="flex-1"
                    />
                    <Button type="button" size="sm" variant="outline" onClick={handleAddTag}>
                      添加
                    </Button>
                  </div>
                </div>

                {/* 作者 */}
                <div>
                  <Label htmlFor="author">{FIELD_LABELS.author}</Label>
                  <Input
                    id="author"
                    value={author}
                    onChange={(e) => setAuthor(e.target.value)}
                    placeholder="作者（可选）"
                  />
                </div>
              </div>
            </div>

            {/* 核心指令 */}
            <div>
              <h3 className="text-lg font-semibold mb-3">{FIELD_LABELS.content}</h3>
              <Textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="你是一个专业的...当用户请求...时激活此技能"
                rows={10}
                className="font-mono text-sm"
              />
            </div>

            {/* 使用示例 */}
            <div>
              <h3 className="text-lg font-semibold mb-3">{FIELD_LABELS.examples}</h3>
              <div className="space-y-2">
                {examples.map((ex, i) => (
                  <div key={i} className="flex gap-2">
                    <Textarea
                      value={ex}
                      onChange={(e) => {
                        const newExamples = [...examples];
                        newExamples[i] = e.target.value;
                        setExamples(newExamples);
                      }}
                      placeholder={`示例 ${i + 1}`}
                      rows={2}
                      className="flex-1 font-mono text-sm"
                    />
                    {i > 0 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRemoveExample(i)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddExample}
                >
                  + 添加示例
                </Button>
              </div>
            </div>

            {/* 约束条件 */}
            <div>
              <h3 className="text-lg font-semibold mb-3">{FIELD_LABELS.constraints}</h3>
              <div className="space-y-2">
                {constraints.map((con, i) => (
                  <div key={i} className="flex gap-2">
                    <Textarea
                      value={con}
                      onChange={(e) => {
                        const newConstraints = [...constraints];
                        newConstraints[i] = e.target.value;
                        setConstraints(newConstraints);
                      }}
                      placeholder={`约束条件 ${i + 1}`}
                      rows={1}
                      className="flex-1 text-sm"
                    />
                    {i > 0 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRemoveConstraint(i)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddConstraint}
                >
                  + 添加约束
                </Button>
              </div>
            </div>

            {/* 启用状态 */}
            <div className="flex items-center gap-3 border-t pt-4">
              <Switch
                id="is_active"
                checked={is_active}
                onCheckedChange={setIsActive}
              />
              <Label htmlFor="is_active" className="cursor-pointer">
                启用此 Skill（Agent 可调用）
              </Label>
            </div>
          </div>
        ) : (
          /* 预览模式 */
          <div className="space-y-6">
            {/* 基本信息 */}
            <div className="rounded-lg border p-6 bg-card">
              <h3 className="text-lg font-semibold mb-4">基本信息</h3>
              <div className="space-y-3">
                <div className="flex items-center gap-4 flex-wrap">
                  <span className="text-sm text-muted-foreground">名称：</span>
                  <span className="font-mono text-sm">{skill.name}</span>
                  {!skill.is_active && (
                    <Badge variant="destructive">已禁用</Badge>
                  )}
                </div>
                {skill.title && (
                  <div>
                    <span className="text-sm text-muted-foreground">标题：</span>
                    <p className="text-sm font-medium">{skill.title}</p>
                  </div>
                )}
                <div>
                  <span className="text-sm text-muted-foreground">描述：</span>
                  <p className="text-sm">{skill.description}</p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  {skill.category && (
                    <Badge variant="outline">{skill.category}</Badge>
                  )}
                  {skill.difficulty && (
                    <Badge variant="outline">
                      {DIFFICULTIES.find((d) => d.value === skill.difficulty)?.label}
                    </Badge>
                  )}
                  {skill.author && (
                    <span className="text-xs text-muted-foreground">
                      作者: {skill.author}
                    </span>
                  )}
                </div>
                {skill.tags?.length > 0 && (
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm text-muted-foreground">标签：</span>
                    {skill.tags.map((tag) => (
                      <Badge key={tag} variant="secondary">{tag}</Badge>
                    ))}
                  </div>
                )}
                <div className="text-xs text-muted-foreground">
                  版本: v{skill.version} · 创建: {new Date(skill.created_at).toLocaleDateString('zh-CN')} ·
                  更新: {new Date(skill.updated_at).toLocaleDateString('zh-CN')}
                </div>
              </div>
            </div>

            {/* 核心指令 */}
            {skill.content && (
              <div className="rounded-lg border p-6 bg-card">
                <h3 className="text-lg font-semibold mb-3">{FIELD_LABELS.content}</h3>
                <div className="rounded-md bg-muted p-4 whitespace-pre-wrap text-sm">
                  {skill.content}
                </div>
              </div>
            )}

            {/* 参数定义 */}
            {Object.keys(skill.parameters || {}).length > 0 && (
              <div className="rounded-lg border p-6 bg-card">
                <h3 className="text-lg font-semibold mb-3">{FIELD_LABELS.parameters}</h3>
                <pre className="rounded-md bg-muted p-4 text-xs overflow-auto">
                  {JSON.stringify(skill.parameters, null, 2)}
                </pre>
              </div>
            )}

            {/* 使用示例 */}
            {skill.examples?.length > 0 && skill.examples.some((e) => e) && (
              <div className="rounded-lg border p-6 bg-card">
                <h3 className="text-lg font-semibold mb-3">{FIELD_LABELS.examples}</h3>
                <div className="space-y-2">
                  {skill.examples.map((ex, i) => (
                    ex && (
                      <div key={i} className="rounded-md border p-3 text-sm">
                        {ex}
                      </div>
                    )
                  ))}
                </div>
              </div>
            )}

            {/* 约束条件 */}
            {skill.constraints?.length > 0 && skill.constraints.some((c) => c) && (
              <div className="rounded-lg border p-6 bg-card">
                <h3 className="text-lg font-semibold mb-3">{FIELD_LABELS.constraints}</h3>
                <ul className="space-y-1">
                  {skill.constraints.map((con, i) => (
                    con && (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <CheckCircle className="h-4 w-4 text-green-600 shrink-0 mt-0.5" />
                        <span>{con}</span>
                      </li>
                    )
                  ))}
                </ul>
              </div>
            )}

            {/* 原始 Markdown */}
            {skill.raw_markdown && (
              <div className="rounded-lg border p-6 bg-card">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold">原始 Markdown</h3>
                  <Button variant="outline" size="sm" onClick={handleDownloadMarkdown}>
                    <FileText className="mr-2 h-4 w-4" />
                    下载
                  </Button>
                </div>
                <pre className="rounded-md bg-muted p-4 text-xs overflow-auto max-h-60 font-mono">
                  {skill.raw_markdown}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
