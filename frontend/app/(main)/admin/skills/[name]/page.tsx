'use client';

import { use, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AppLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  ArrowLeft,
  Save,
  Loader2,
  FileText,
  Trash2,
  Brain,
  Plus,
  AtSign,
  AlertTriangle,
  CheckCircle,
} from 'lucide-react';
import {
  skillsApi,
  type LintIssue,
  type SkillReferenceItem,
  type SkillResponse,
  type SkillUpdate,
  type SkillMetaResponse,
} from '@/lib/api';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';

// ===========================================================================
// @ 引用 picker：在 body / reference body 编辑时插入 @ref / @skill / @skill#ref token
// ===========================================================================

function ReferencePickerDialog({
  open,
  onOpenChange,
  selfReferences,
  allSkills,
  currentSkillName,
  onPick,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selfReferences: SkillReferenceItem[];
  allSkills: SkillMetaResponse[];
  currentSkillName: string;
  onPick: (token: string) => void;
}) {
  const [tab, setTab] = useState<'self' | 'cross'>('self');
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const [crossRefs, setCrossRefs] = useState<SkillReferenceItem[]>([]);
  const [loadingCross, setLoadingCross] = useState(false);

  useEffect(() => {
    if (!open) {
      setSelectedSkill(null);
      setCrossRefs([]);
    }
  }, [open]);

  useEffect(() => {
    if (!selectedSkill) return;
    setLoadingCross(true);
    skillsApi
      .get(selectedSkill)
      .then((res) => setCrossRefs(res.references))
      .catch(() => setCrossRefs([]))
      .finally(() => setLoadingCross(false));
  }, [selectedSkill]);

  const otherSkills = allSkills.filter((s) => s.name !== currentSkillName);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>插入 @ 引用</DialogTitle>
          <DialogDescription>
            选中后会在光标处插入纯文本 token；DB 始终存原始字符串，前端再叠加样式。
          </DialogDescription>
        </DialogHeader>

        <div className="flex gap-1 border-b border-border/70">
          <button
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === 'self'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setTab('self')}
          >
            本 Skill 引用 (@ref:&lt;key&gt;)
          </button>
          <button
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === 'cross'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setTab('cross')}
          >
            跨 Skill 引用 (@skill:...)
          </button>
        </div>

        {tab === 'self' ? (
          <ScrollArea className="max-h-96">
            {selfReferences.length === 0 ? (
              <p className="px-4 py-6 text-sm text-muted-foreground">
                当前 Skill 还没有 reference 子文档。先在下方"引用"区添加 reference，再回来插入 @ref 标记。
              </p>
            ) : (
              <ul className="space-y-2 py-2">
                {selfReferences.map((ref) => {
                  const token = `@ref:${ref.key}`;
                  return (
                    <li key={ref.key}>
                      <button
                        className="w-full rounded-lg border border-border/60 bg-background px-4 py-3 text-left hover:border-primary/50"
                        onClick={() => {
                          onPick(token);
                          onOpenChange(false);
                        }}
                      >
                        <div className="font-mono text-sm text-primary">{token}</div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {ref.title || ref.key}
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </ScrollArea>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            <ScrollArea className="max-h-96 rounded-lg border border-border/60">
              <ul className="space-y-1 p-2">
                {otherSkills.length === 0 && (
                  <li className="px-3 py-2 text-sm text-muted-foreground">无其他 Skill</li>
                )}
                {otherSkills.map((s) => (
                  <li key={s.name}>
                    <button
                      className={`w-full rounded-md px-3 py-2 text-left text-sm transition-colors ${
                        selectedSkill === s.name
                          ? 'bg-primary/10 text-primary'
                          : 'hover:bg-muted'
                      }`}
                      onClick={() => setSelectedSkill(s.name)}
                    >
                      <div className="font-mono">{s.name}</div>
                      <div className="text-xs text-muted-foreground line-clamp-1">
                        {s.description}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </ScrollArea>
            <ScrollArea className="max-h-96 rounded-lg border border-border/60">
              <div className="p-2 space-y-2">
                {!selectedSkill && (
                  <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                    选择左侧 Skill 查看可用 reference
                  </p>
                )}
                {selectedSkill && (
                  <>
                    <button
                      className="w-full rounded-md border border-border/60 px-3 py-2 text-left hover:border-primary/50"
                      onClick={() => {
                        onPick(`@skill:${selectedSkill}`);
                        onOpenChange(false);
                      }}
                    >
                      <div className="font-mono text-sm text-primary">
                        @skill:{selectedSkill}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        引用整个 Skill（LLM 决策是否 load_skill）
                      </div>
                    </button>
                    {loadingCross && (
                      <div className="px-3 py-2 text-sm text-muted-foreground">
                        加载中...
                      </div>
                    )}
                    {!loadingCross &&
                      crossRefs.map((ref) => {
                        const token = `@skill:${selectedSkill}#${ref.key}`;
                        return (
                          <button
                            key={ref.key}
                            className="w-full rounded-md border border-border/60 px-3 py-2 text-left hover:border-primary/50"
                            onClick={() => {
                              onPick(token);
                              onOpenChange(false);
                            }}
                          >
                            <div className="font-mono text-sm text-primary">{token}</div>
                            <div className="text-xs text-muted-foreground mt-1">
                              {ref.title || ref.key}
                            </div>
                          </button>
                        );
                      })}
                    {!loadingCross && crossRefs.length === 0 && (
                      <p className="px-3 py-2 text-xs text-muted-foreground">
                        该 Skill 没有 reference 子文档
                      </p>
                    )}
                  </>
                )}
              </div>
            </ScrollArea>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ===========================================================================
// 文本输入 + @ picker 触发器
// ===========================================================================

function TextareaWithRefPicker({
  value,
  onChange,
  rows,
  placeholder,
  selfReferences,
  allSkills,
  currentSkillName,
}: {
  value: string;
  onChange: (v: string) => void;
  rows?: number;
  placeholder?: string;
  selfReferences: SkillReferenceItem[];
  allSkills: SkillMetaResponse[];
  currentSkillName: string;
}) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);

  const insertAtCursor = useCallback(
    (token: string) => {
      const el = ref.current;
      if (!el) {
        onChange(`${value}${value && !value.endsWith(' ') ? ' ' : ''}${token}`);
        return;
      }
      const start = el.selectionStart;
      const end = el.selectionEnd;
      const before = value.slice(0, start);
      const after = value.slice(end);
      const insert = (start > 0 && before[before.length - 1] !== ' ' && before[before.length - 1] !== '\n')
        ? ` ${token}`
        : token;
      const next = `${before}${insert}${after}`;
      onChange(next);
      // 把光标放在插入内容之后
      requestAnimationFrame(() => {
        const pos = before.length + insert.length;
        el.focus();
        el.setSelectionRange(pos, pos);
      });
    },
    [onChange, value],
  );

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          支持 @ref:&lt;key&gt; / @skill:&lt;name&gt; / @skill:&lt;name&gt;#&lt;key&gt; 引用
        </span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setPickerOpen(true)}
        >
          <AtSign className="mr-1.5 h-3.5 w-3.5" />
          插入引用
        </Button>
      </div>
      <Textarea
        ref={ref}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={rows}
        placeholder={placeholder}
        className="font-mono text-sm"
      />
      <ReferencePickerDialog
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        selfReferences={selfReferences}
        allSkills={allSkills}
        currentSkillName={currentSkillName}
        onPick={insertAtCursor}
      />
    </div>
  );
}

// ===========================================================================
// 主页面
// ===========================================================================

export default function SkillDetailPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name: skillName } = use(params);
  const router = useRouter();

  const [skill, setSkill] = useState<SkillResponse | null>(null);
  const [allMeta, setAllMeta] = useState<SkillMetaResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [linting, setLinting] = useState(false);
  const [lintIssues, setLintIssues] = useState<LintIssue[] | null>(null);

  // 编辑表单状态
  const [description, setDescription] = useState('');
  const [body, setBody] = useState('');
  const [targetAgents, setTargetAgents] = useState<string[]>([]);
  const [agentInput, setAgentInput] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [references, setReferences] = useState<SkillReferenceItem[]>([]);
  const [author, setAuthor] = useState('');
  const [isActive, setIsActive] = useState(true);

  const fetchSkill = useCallback(async () => {
    setLoading(true);
    try {
      const [skillRes, metaRes] = await Promise.all([
        skillsApi.get(skillName),
        skillsApi.meta(),
      ]);
      setSkill(skillRes);
      setAllMeta(metaRes);
      setEditMode(false);

      setDescription(skillRes.description || '');
      setBody(skillRes.body || '');
      setTargetAgents(skillRes.target_agents || []);
      setTags(skillRes.tags || []);
      setReferences(skillRes.references || []);
      setAuthor(skillRes.author || '');
      setIsActive(skillRes.is_active);
      setLintIssues(null);
    } catch (e) {
      toast.error(`加载失败: ${(e as Error).message}`);
      router.back();
    } finally {
      setLoading(false);
    }
  }, [skillName, router]);

  useEffect(() => {
    fetchSkill();
  }, [fetchSkill]);

  const handleSave = async () => {
    if (!skill) return;
    setSaving(true);
    try {
      const update: SkillUpdate = {
        description,
        target_agents: targetAgents,
        body,
        references,
        tags,
        author: author || undefined,
        is_active: isActive,
      };
      await skillsApi.update(skill.name, update);
      toast.success('保存成功');
      setEditMode(false);
      await fetchSkill();
    } catch (e) {
      toast.error(`保存失败: ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (skill) {
      setDescription(skill.description || '');
      setBody(skill.body || '');
      setTargetAgents(skill.target_agents || []);
      setTags(skill.tags || []);
      setReferences(skill.references || []);
      setAuthor(skill.author || '');
      setIsActive(skill.is_active);
    }
    setEditMode(false);
  };

  const handleLint = async () => {
    if (!skill) return;
    setLinting(true);
    try {
      const res = await skillsApi.lint(skill.name);
      setLintIssues(res.issues);
      if (res.issues.length === 0) {
        toast.success('Lint 通过，无 issue');
      } else {
        const errors = res.issues.filter((i) => i.level === 'error').length;
        toast(
          errors > 0
            ? `Lint：${errors} 个 error / ${res.issues.length - errors} 个 warning`
            : `Lint：${res.issues.length} 个 warning`,
        );
      }
    } catch (e) {
      toast.error(`Lint 失败: ${(e as Error).message}`);
    } finally {
      setLinting(false);
    }
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

  const handleAddTag = () => {
    const v = tagInput.trim();
    if (v && !tags.includes(v)) setTags([...tags, v]);
    setTagInput('');
  };
  const handleRemoveTag = (t: string) =>
    setTags(tags.filter((x) => x !== t));

  const handleAddAgent = () => {
    const v = agentInput.trim();
    if (v && !targetAgents.includes(v)) setTargetAgents([...targetAgents, v]);
    setAgentInput('');
  };
  const handleRemoveAgent = (a: string) =>
    setTargetAgents(targetAgents.filter((x) => x !== a));

  const handleAddReference = () => {
    const usedKeys = new Set(references.map((r) => r.key));
    let i = 1;
    let key = `ref-${i}`;
    while (usedKeys.has(key)) {
      i += 1;
      key = `ref-${i}`;
    }
    setReferences([...references, { key, title: '', body: '' }]);
  };
  const handleRemoveReference = (key: string) =>
    setReferences(references.filter((r) => r.key !== key));
  const handleUpdateReference = (
    key: string,
    field: keyof SkillReferenceItem,
    value: string,
  ) => {
    setReferences(
      references.map((r) => (r.key === key ? { ...r, [field]: value } : r)),
    );
  };

  const lintErrors = useMemo(
    () => (lintIssues || []).filter((i) => i.level === 'error'),
    [lintIssues],
  );
  const lintWarnings = useMemo(
    () => (lintIssues || []).filter((i) => i.level === 'warning'),
    [lintIssues],
  );

  if (loading) {
    return (
      <AppLayout title={`Skill: ${skillName}`} description="加载中...">
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppLayout>
    );
  }

  if (!skill) {
    return (
      <AppLayout title={`Skill: ${skillName}`} description="未找到">
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
      title={skill.name}
      description={`v${skill.version}${skill.author ? ` · ${skill.author}` : ''}`}
    >
      <div className="p-6 space-y-6">
        {/* 顶部操作栏 */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <Button variant="outline" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            返回
          </Button>
          <div className="flex items-center gap-2 flex-wrap">
            <Button variant="outline" onClick={handleDownloadMarkdown}>
              <FileText className="mr-2 h-4 w-4" />
              下载 SKILL.md
            </Button>
            <Button variant="outline" onClick={handleLint} disabled={linting}>
              {linting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle className="mr-2 h-4 w-4" />
              )}
              引用 Lint
            </Button>
            {!editMode ? (
              <Button onClick={() => setEditMode(true)}>
                <Brain className="mr-2 h-4 w-4" />
                编辑
              </Button>
            ) : (
              <>
                <Button variant="outline" onClick={handleCancel} disabled={saving}>
                  取消
                </Button>
                <Button onClick={handleSave} disabled={saving}>
                  {saving ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="mr-2 h-4 w-4" />
                  )}
                  保存
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Lint 结果 */}
        {lintIssues !== null && lintIssues.length > 0 && (
          <div className="rounded-2xl border border-yellow-200 bg-yellow-50 p-5 text-yellow-900">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <AlertTriangle className="h-4 w-4" />
              Lint 结果：{lintErrors.length} 个 error · {lintWarnings.length} 个 warning
            </div>
            <ul className="mt-3 space-y-2 text-sm leading-6">
              {lintIssues.map((issue, idx) => (
                <li
                  key={idx}
                  className="rounded-xl border border-yellow-200/80 bg-background/70 px-3 py-2"
                >
                  <span
                    className={`mr-2 rounded-md px-2 py-0.5 text-xs font-medium ${
                      issue.level === 'error'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-yellow-100 text-yellow-700'
                    }`}
                  >
                    {issue.level} · {issue.code}
                  </span>
                  <span className="font-mono text-xs text-muted-foreground">
                    {issue.field}
                  </span>
                  <span className="ml-2">{issue.message}</span>
                  {issue.token && (
                    <span className="ml-2 font-mono text-xs text-blue-700">
                      {issue.token}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
        {lintIssues !== null && lintIssues.length === 0 && (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-3 text-sm text-emerald-800">
            <CheckCircle className="mr-1 inline h-4 w-4" />
            Lint 通过，无 issue。
          </div>
        )}

        {/* 编辑模式 */}
        {editMode ? (
          <div className="space-y-6 rounded-lg border p-6 bg-card">
            <div>
              <Label htmlFor="description">
                激活描述 (description) <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder='建议 "Use when ... to ..." 句式，agent 据此判断是否加载本 Skill 主体'
                rows={2}
                className="mt-1"
              />
            </div>

            <div>
              <Label>适用 Sub-Agent (target_agents)</Label>
              <p className="mt-1 text-xs text-muted-foreground">
                列在这里的 sub-agent 启动时会自动看到本 Skill 的 L1 元信息。
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {targetAgents.map((agent) => (
                  <Badge
                    key={agent}
                    variant="secondary"
                    className="flex items-center gap-1 pr-2"
                  >
                    {agent}
                    <button
                      type="button"
                      className="ml-1 hover:bg-destructive/20 rounded-sm p-0.5"
                      onClick={() => handleRemoveAgent(agent)}
                    >
                      ×
                    </button>
                  </Badge>
                ))}
              </div>
              <div className="mt-2 flex gap-2">
                <Input
                  value={agentInput}
                  onChange={(e) => setAgentInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddAgent();
                    }
                  }}
                  placeholder="例如 outline_agent / script_agent"
                  className="flex-1"
                />
                <Button type="button" size="sm" variant="outline" onClick={handleAddAgent}>
                  添加
                </Button>
              </div>
            </div>

            <div>
              <Label>主体 body (L2)</Label>
              <p className="mt-1 text-xs text-muted-foreground">
                LLM 调 load_skill 时返回此内容。建议使用 @ref / @skill 引用而不是把所有内容塞在这里。
              </p>
              <div className="mt-2">
                <TextareaWithRefPicker
                  value={body}
                  onChange={setBody}
                  rows={12}
                  placeholder="SKILL.md 主体 markdown..."
                  selfReferences={references}
                  allSkills={allMeta}
                  currentSkillName={skill.name}
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between">
                <Label>引用 references (L3)</Label>
                <Button type="button" size="sm" variant="outline" onClick={handleAddReference}>
                  <Plus className="mr-1.5 h-3.5 w-3.5" />
                  添加 reference
                </Button>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                每个 reference 是一个独立子文档；LLM 调 load_skill_reference(name, key) 加载。
                body 里需要用 @ref:&lt;key&gt; 显式引用，否则会被 lint 标为孤立。
              </p>
              <div className="mt-3 space-y-3">
                {references.length === 0 && (
                  <p className="rounded-lg border border-dashed border-muted-foreground/30 px-4 py-6 text-center text-sm text-muted-foreground">
                    没有 reference 子文档
                  </p>
                )}
                {references.map((ref) => (
                  <div
                    key={ref.key}
                    className="rounded-lg border border-border/60 bg-background p-4 space-y-3"
                  >
                    <div className="flex gap-2">
                      <div className="flex-1">
                        <Label className="text-xs">key</Label>
                        <Input
                          value={ref.key}
                          onChange={(e) =>
                            handleUpdateReference(ref.key, 'key', e.target.value)
                          }
                          placeholder="例如 act-templates"
                          className="font-mono text-sm mt-1"
                        />
                      </div>
                      <div className="flex-1">
                        <Label className="text-xs">title（前端展示用）</Label>
                        <Input
                          value={ref.title}
                          onChange={(e) =>
                            handleUpdateReference(ref.key, 'title', e.target.value)
                          }
                          placeholder="可选，前端展示用"
                          className="text-sm mt-1"
                        />
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRemoveReference(ref.key)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                    <div>
                      <Label className="text-xs">body</Label>
                      <div className="mt-1">
                        <TextareaWithRefPicker
                          value={ref.body}
                          onChange={(v) =>
                            handleUpdateReference(ref.key, 'body', v)
                          }
                          rows={6}
                          placeholder="reference 子文档 markdown..."
                          selfReferences={references}
                          allSkills={allMeta}
                          currentSkillName={skill.name}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <Label>标签 (tags)</Label>
              <div className="mt-2 flex flex-wrap gap-2">
                {tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="flex items-center gap-1 pr-2">
                    {tag}
                    <button
                      type="button"
                      className="ml-1 hover:bg-destructive/20 rounded-sm p-0.5"
                      onClick={() => handleRemoveTag(tag)}
                    >
                      ×
                    </button>
                  </Badge>
                ))}
              </div>
              <div className="mt-2 flex gap-2">
                <Input
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddTag();
                    }
                  }}
                  placeholder="输入标签后回车添加"
                  className="flex-1"
                />
                <Button type="button" size="sm" variant="outline" onClick={handleAddTag}>
                  添加
                </Button>
              </div>
            </div>

            <div>
              <Label htmlFor="author">作者 (author)</Label>
              <Input
                id="author"
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
                placeholder="可选"
                className="mt-1"
              />
            </div>

            <div className="flex items-center gap-3 border-t pt-4">
              <Switch id="is_active" checked={isActive} onCheckedChange={setIsActive} />
              <Label htmlFor="is_active" className="cursor-pointer">
                启用此 Skill（agent 可加载）
              </Label>
            </div>
          </div>
        ) : (
          /* 预览模式 */
          <div className="space-y-6">
            <div className="rounded-lg border p-6 bg-card">
              <h3 className="text-lg font-semibold mb-4">基本信息</h3>
              <div className="space-y-3 text-sm">
                <div>
                  <span className="text-muted-foreground">name：</span>
                  <span className="font-mono">{skill.name}</span>
                  {!skill.is_active && (
                    <Badge variant="destructive" className="ml-2">
                      已禁用
                    </Badge>
                  )}
                </div>
                <div>
                  <span className="text-muted-foreground">description：</span>
                  <p>{skill.description}</p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-muted-foreground">target_agents：</span>
                  {skill.target_agents.length > 0 ? (
                    skill.target_agents.map((a) => (
                      <Badge key={a} variant="outline">
                        {a}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-muted-foreground">未指定</span>
                  )}
                </div>
                {skill.tags.length > 0 && (
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-muted-foreground">tags：</span>
                    {skill.tags.map((t) => (
                      <Badge key={t} variant="secondary">
                        {t}
                      </Badge>
                    ))}
                  </div>
                )}
                <div className="text-xs text-muted-foreground">
                  v{skill.version} · 创建{' '}
                  {new Date(skill.created_at).toLocaleDateString('zh-CN')} · 更新{' '}
                  {new Date(skill.updated_at).toLocaleDateString('zh-CN')}
                  {skill.author ? ` · 作者 ${skill.author}` : ''}
                </div>
              </div>
            </div>

            {skill.body && (
              <div className="rounded-lg border p-6 bg-card">
                <h3 className="text-lg font-semibold mb-3">主体 body (L2)</h3>
                <pre className="rounded-md bg-muted p-4 whitespace-pre-wrap text-sm font-mono">
                  {skill.body}
                </pre>
              </div>
            )}

            {skill.references.length > 0 && (
              <div className="rounded-lg border p-6 bg-card">
                <h3 className="text-lg font-semibold mb-3">
                  引用 references (L3) · {skill.references.length}
                </h3>
                <div className="space-y-3">
                  {skill.references.map((ref) => (
                    <div
                      key={ref.key}
                      className="rounded-lg border border-border/60 bg-background p-4"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="outline" className="font-mono">
                          @ref:{ref.key}
                        </Badge>
                        {ref.title && (
                          <span className="text-sm text-muted-foreground">
                            {ref.title}
                          </span>
                        )}
                      </div>
                      <pre className="rounded-md bg-muted p-3 whitespace-pre-wrap text-xs font-mono">
                        {ref.body}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {skill.raw_markdown && (
              <div className="rounded-lg border p-6 bg-card">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold">原始 Markdown</h3>
                  <Button variant="outline" size="sm" onClick={handleDownloadMarkdown}>
                    <FileText className="mr-2 h-4 w-4" />
                    下载
                  </Button>
                </div>
                <pre className="rounded-md bg-muted p-4 text-xs overflow-auto max-h-60 font-mono whitespace-pre-wrap">
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
