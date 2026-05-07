'use client';

import { useCallback, useEffect, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { AppLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
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
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Search,
  MoreVertical,
  Upload,
  Pencil,
  Trash2,
  Eye,
  EyeOff,
  Brain,
  FileText,
  FileEdit,
  Loader2,
  AlertTriangle,
  CheckCircle,
  Save,
  Sparkles,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  skillsApi,
  type SkillCreate,
  type SkillResponse,
  type SkillUploadResponse,
} from '@/lib/api';
import { SKILL_SAMPLES } from '@/lib/skill-samples';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

// ===========================================================================
// 常量
// ===========================================================================

// 新模型的字段标签（Claude SKILL.md 风格）
const FIELD_LABELS: Record<string, string> = {
  name: '名称',
  description: '激活描述',
  target_agents: '适用 Sub-Agent',
  body: '主体 (L2)',
  references: '引用 (L3)',
  tags: '标签',
  author: '作者',
  metadata: '元数据',
};

const LARGE_DIALOG_CLASSNAME = [
  'h-[min(94vh,1080px)]',
  'w-[calc(100vw-1rem)]',
  'max-w-none',
  'gap-0',
  'overflow-hidden',
  'border-border/60',
  'p-0',
  'sm:w-[min(96vw,1600px)]',
  'sm:max-w-[min(96vw,1600px)]',
  'sm:rounded-2xl',
].join(' ');

const LONG_TEXT_FIELDS = new Set(['body', 'description']);
const JSON_FIELDS = new Set(['metadata', 'references']);

function isEmptyFieldValue(value: unknown): boolean {
  if (value === null || value === undefined || value === '') return true;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === 'object') return Object.keys(value as object).length === 0;
  return false;
}

// ===========================================================================
// Markdown 编辑器（源码 / 渲染 切换）
// ===========================================================================
function MarkdownEditor({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const [mode, setMode] = useState<'source' | 'preview'>('preview');
  const [editing, setEditing] = useState(false);

  return (
    <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-border/70 bg-background shadow-sm">
      <div className="flex items-center justify-between border-b border-border/70 px-5 py-3">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold">原始 Markdown</p>
          <div className="flex rounded-lg border border-border/70 bg-muted/30 p-0.5">
            <button
              className={cn(
                'rounded-md px-3 py-1 text-xs font-medium transition-colors',
                mode === 'preview'
                  ? 'bg-background shadow-sm text-foreground'
                  : 'text-muted-foreground hover:text-foreground',
              )}
              onClick={() => setMode('preview')}
            >
              渲染
            </button>
            <button
              className={cn(
                'rounded-md px-3 py-1 text-xs font-medium transition-colors',
                mode === 'source'
                  ? 'bg-background shadow-sm text-foreground'
                  : 'text-muted-foreground hover:text-foreground',
              )}
              onClick={() => setMode('source')}
            >
              源码
            </button>
          </div>
        </div>
        {!editing ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setEditing(true);
              setMode('source');
            }}
          >
            <Pencil className="mr-1.5 h-3.5 w-3.5" />
            编辑
          </Button>
        ) : (
          <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
            取消编辑
          </Button>
        )}
      </div>

      <ScrollArea className="min-h-0 flex-1">
        {mode === 'preview' && !editing ? (
          <div className="prose prose-sm max-w-none bg-white text-black px-6 py-4 [&_h1]:text-black [&_h2]:text-black [&_h3]:text-black [&_h4]:text-black [&_h5]:text-black [&_h6]:text-black [&_p]:text-black [&_li]:text-black [&_strong]:text-black [&_a]:text-blue-600 [&_blockquote]:text-gray-700 [&_pre]:bg-gray-100 [&_pre>_code]:bg-gray-100 [&_code]:bg-gray-100 [&_code]:text-black">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{value}</ReactMarkdown>
          </div>
        ) : (
          <textarea
            className="h-full min-h-[20rem] w-full resize-none bg-background px-5 py-4 font-mono text-xs leading-6 text-foreground focus:outline-none"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            readOnly={!editing}
          />
        )}
      </ScrollArea>
    </section>
  );
}

function renderFieldStateBadge(
  fieldKey: string,
  value: unknown,
  missingFields: string[],
): ReactNode {
  const isMissing = missingFields.includes(fieldKey);
  const isEmpty = isEmptyFieldValue(value);

  if (isMissing || isEmpty) {
    return (
      <Badge variant="outline" className="text-xs text-yellow-700 border-yellow-300 bg-yellow-50">
        缺失
      </Badge>
    );
  }

  return (
    <Badge variant="outline" className="text-xs text-emerald-700 border-emerald-300 bg-emerald-50">
      <CheckCircle className="mr-1 h-3.5 w-3.5" />
      已解析
    </Badge>
  );
}

function FieldValuePreview({
  fieldKey,
  value,
  className,
}: {
  fieldKey: string;
  value: unknown;
  className?: string;
}) {
  if (isEmptyFieldValue(value)) {
    return (
      <div className="rounded-xl border border-dashed border-muted-foreground/25 bg-muted/20 px-4 py-3 text-sm text-muted-foreground">
        暂无内容
      </div>
    );
  }

  if (typeof value === 'string') {
    const isLongText = LONG_TEXT_FIELDS.has(fieldKey) || value.length > 180 || value.includes('\n');
    return (
      <div
        className={cn(
          'rounded-xl border border-border/60 bg-white px-4 py-3 text-sm leading-6 whitespace-pre-wrap text-black',
          isLongText && 'max-h-[28rem] overflow-auto',
          className,
        )}
      >
        {value}
      </div>
    );
  }

  if (Array.isArray(value)) {
    const shouldClampHeight = value.length > 4;
    return (
      <div
        className={cn(
          'overflow-auto rounded-xl border border-border/60 bg-white',
          shouldClampHeight && 'max-h-72',
          className,
        )}
      >
        <div className="space-y-2 px-4 py-3">
          {value.map((item, index) => (
            <div
              key={`${fieldKey}-${index}`}
              className="rounded-lg border bg-white px-3 py-2 text-sm text-black break-words"
            >
              {typeof item === 'object'
                ? JSON.stringify(item, null, 2)
                : String(item)}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'overflow-auto rounded-xl border border-border/60 bg-white text-black',
        className,
        JSON_FIELDS.has(fieldKey) ? 'max-h-[24rem]' : 'max-h-72',
      )}
    >
      <pre className="px-4 py-3 text-xs leading-6 whitespace-pre-wrap">
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}

function UploadFieldCard({
  fieldKey,
  value,
  missingFields,
  showStatusBadge = true,
}: {
  fieldKey: string;
  value: unknown;
  missingFields: string[];
  showStatusBadge?: boolean;
}) {
  return (
    <article className="rounded-2xl border border-border/70 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground">
            {FIELD_LABELS[fieldKey] || fieldKey}
          </p>
          <p className="mt-1 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            {fieldKey}
          </p>
        </div>
        {showStatusBadge ? renderFieldStateBadge(fieldKey, value, missingFields) : null}
      </div>

      <div className="mt-4">
        <FieldValuePreview fieldKey={fieldKey} value={value} />
      </div>
    </article>
  );
}

function ViewMarkdownContent({ content }: { content: string }) {
  const [mode, setMode] = useState<'preview' | 'source'>('preview');

  if (!content) {
    return (
      <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
        （无原始 Markdown）
      </div>
    );
  }

  return (
    <>
      <div className="flex items-center border-b border-border/70 px-5 py-3">
        <div className="flex rounded-lg border border-border/70 bg-muted/30 p-0.5">
          <button
            className={cn(
              'rounded-md px-3 py-1 text-xs font-medium transition-colors',
              mode === 'preview'
                ? 'bg-background shadow-sm text-foreground'
                : 'text-muted-foreground hover:text-foreground',
            )}
            onClick={() => setMode('preview')}
          >
            渲染
          </button>
          <button
            className={cn(
              'rounded-md px-3 py-1 text-xs font-medium transition-colors',
              mode === 'source'
                ? 'bg-background shadow-sm text-foreground'
                : 'text-muted-foreground hover:text-foreground',
            )}
            onClick={() => setMode('source')}
          >
            源码
          </button>
        </div>
      </div>
      <ScrollArea className="min-h-0 flex-1">
        {mode === 'preview' ? (
          <div className="prose prose-sm max-w-none bg-white text-black px-6 py-4 [&_h1]:text-black [&_h2]:text-black [&_h3]:text-black [&_h4]:text-black [&_h5]:text-black [&_h6]:text-black [&_p]:text-black [&_li]:text-black [&_strong]:text-black [&_a]:text-blue-600 [&_blockquote]:text-gray-700 [&_pre]:bg-gray-100 [&_pre>_code]:bg-gray-100 [&_code]:bg-gray-100 [&_code]:text-black">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        ) : (
          <pre className="px-5 py-4 text-sm leading-7 whitespace-pre-wrap text-foreground">
            {content}
          </pre>
        )}
      </ScrollArea>
    </>
  );
}

// ===========================================================================
// 创建 / 上传对话框
// 同时支持"上传 .md 文件"与"直接在浏览器写 markdown"两种入口；
// 解析、预览、保存逻辑两路共用。
// ===========================================================================

type SourceMode = 'upload' | 'write';

interface SkillSourceDialogProps {
  defaultMode: SourceMode;
  triggerLabel: string;
  triggerIcon: 'upload' | 'edit';
  triggerVariant?: 'default' | 'outline';
  onSaved: () => void;
}

function SkillSourceDialog({
  defaultMode,
  triggerLabel,
  triggerIcon,
  triggerVariant = 'default',
  onSaved,
}: SkillSourceDialogProps) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<SourceMode>(defaultMode);
  const [markdown, setMarkdown] = useState('');
  const [draft, setDraft] = useState('');
  const [fileName, setFileName] = useState('');
  const [preview, setPreview] = useState<SkillUploadResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // open 状态变化时重置 mode 到 defaultMode（每次打开都从指定入口开始）
  useEffect(() => {
    if (open) setMode(defaultMode);
  }, [open, defaultMode]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    const text = await file.text();
    setMarkdown(text);
    await doParse(text);
  };

  const handleWriteParse = async () => {
    if (!draft.trim()) {
      toast.error('请先编写或选择模板内容');
      return;
    }
    setMarkdown(draft);
    setFileName('（直接编写）');
    await doParse(draft);
  };

  const handleApplySample = (sampleMarkdown: string) => {
    setDraft(sampleMarkdown);
  };

  const doParse = async (text: string) => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const result = await skillsApi.upload(text);
      setPreview(result);
    } catch (e) {
      toast.error(`解析失败: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!preview) return;

    setSaving(true);
    try {
      const f = preview.skill.fields as Record<string, unknown>;
      const payload: SkillCreate = {
        name: String(f.name ?? ''),
        description: String(f.description ?? ''),
        target_agents: Array.isArray(f.target_agents) ? (f.target_agents as string[]) : [],
        body: typeof f.body === 'string' ? f.body : undefined,
        references: Array.isArray(f.references)
          ? (f.references as Array<{ key: string; title?: string; body?: string }>).map(
              (r) => ({
                key: r.key,
                title: r.title ?? '',
                body: r.body ?? '',
              }),
            )
          : [],
        tags: Array.isArray(f.tags) ? (f.tags as string[]) : [],
        author: typeof f.author === 'string' ? f.author : undefined,
        raw_markdown: markdown,
        metadata: typeof f.metadata === 'object' && f.metadata
          ? (f.metadata as Record<string, unknown>)
          : undefined,
      };

      if (preview.is_update) {
        await skillsApi.update(payload.name, {
          description: payload.description,
          target_agents: payload.target_agents,
          body: payload.body,
          references: payload.references,
          tags: payload.tags,
          author: payload.author,
          raw_markdown: payload.raw_markdown,
          skill_metadata: payload.metadata,
        });
        toast.success('Skill 已更新');
      } else {
        await skillsApi.create(payload);
        toast.success('Skill 已创建');
      }
      handleClose();
      onSaved();
    } catch (e) {
      toast.error(`保存失败: ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    setOpen(false);
    setMarkdown('');
    setDraft('');
    setFileName('');
    setPreview(null);
  };

  const skillName = preview?.skill.fields.name as string | undefined;
  const hasMissing = (preview?.skill.missing_fields.length ?? 0) > 0;

  const TriggerIcon = triggerIcon === 'upload' ? Upload : FileEdit;
  const dialogTitle = mode === 'upload' ? '上传 SKILL.md' : '直接编写 SKILL';
  const dialogDescription =
    mode === 'upload'
      ? '上传 .md 文件，系统会按 Claude SKILL.md 风格解析 frontmatter / body / references，并在保存前展示完整预览。'
      : '直接在编辑器里写 SKILL.md 或从内置示例模板开始；点 "解析并预览" 后进入字段预览，再保存。';

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button variant={triggerVariant} onClick={() => setOpen(true)}>
        <TriggerIcon className="mr-2 h-4 w-4" />
        {triggerLabel}
      </Button>

      <DialogContent className={cn(LARGE_DIALOG_CLASSNAME, 'flex flex-col')}>
        <DialogHeader className="shrink-0 border-b border-border/70 px-6 py-5 text-left sm:px-8">
          <DialogTitle>{dialogTitle}</DialogTitle>
          <DialogDescription>{dialogDescription}</DialogDescription>
        </DialogHeader>

        {!preview && !loading && (
          <div className="shrink-0 flex gap-1 border-b border-border/70 px-6 sm:px-8">
            <button
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                mode === 'upload'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
              onClick={() => setMode('upload')}
            >
              <Upload className="mr-2 inline h-3.5 w-3.5" />
              上传文件
            </button>
            <button
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                mode === 'write'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
              onClick={() => setMode('write')}
            >
              <FileEdit className="mr-2 inline h-3.5 w-3.5" />
              直接编写
            </button>
          </div>
        )}

        <div className="flex-1 min-h-0 overflow-hidden px-6 py-6 sm:px-8">
          {!preview && !loading && mode === 'upload' && (
            <label className="flex h-full min-h-[26rem] cursor-pointer flex-col items-center justify-center rounded-[28px] border-2 border-dashed border-border/70 bg-muted/20 px-8 py-12 text-center transition-colors hover:border-primary/45 hover:bg-muted/35">
              <div className="rounded-full border border-border/70 bg-background p-4 shadow-sm">
                <Upload className="h-10 w-10 text-primary" />
              </div>
              <span className="mt-6 text-lg font-semibold">点击选择 SKILL.md 文件</span>
              <span className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
                支持 .md / .markdown。frontmatter 至少需要 name + description；body 内可用 ## reference: &lt;key&gt; 拆分子文档。
              </span>
              {fileName ? (
                <span className="mt-4 rounded-full border border-primary/20 bg-primary/10 px-4 py-1.5 text-sm font-medium text-primary">
                  {fileName}
                </span>
              ) : null}
              <input
                type="file"
                accept=".md,.markdown,text/markdown"
                className="hidden"
                onChange={handleFileSelect}
              />
            </label>
          )}

          {!preview && !loading && mode === 'write' && (
            <div className="flex h-full min-h-0 flex-col gap-4">
              <div className="shrink-0 flex flex-wrap items-center gap-2 rounded-2xl border border-border/70 bg-muted/20 px-4 py-3">
                <Sparkles className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium">从模板开始：</span>
                {SKILL_SAMPLES.map((sample) => (
                  <Button
                    key={sample.label}
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => handleApplySample(sample.markdown)}
                  >
                    {sample.label}
                    {sample.targetAgent !== '通用' && (
                      <span className="ml-1.5 text-[10px] text-muted-foreground">
                        → {sample.targetAgent}
                      </span>
                    )}
                  </Button>
                ))}
                <span className="ml-auto text-xs text-muted-foreground">
                  选中后会覆盖当前编辑内容
                </span>
              </div>
              <textarea
                className="min-h-[28rem] flex-1 resize-none rounded-2xl border border-border/70 bg-background px-5 py-4 font-mono text-xs leading-6 text-foreground focus:border-primary/50 focus:outline-none"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder={`---\nname: my-skill\ndescription: Use when ... to ...\ntarget_agents: [outline_agent]\ntags: []\n---\n\n# 标题\n\n主体内容...\n\n## reference: example-key\n\nreference 子文档内容\n`}
              />
              <div className="shrink-0 flex items-center justify-between gap-3">
                <span className="text-xs text-muted-foreground">
                  {draft.length} 字 · 保存前会按 SKILL.md 规则解析
                </span>
                <Button onClick={handleWriteParse} disabled={!draft.trim()}>
                  <Brain className="mr-2 h-4 w-4" />
                  解析并预览
                </Button>
              </div>
            </div>
          )}

          {loading && (
            <div className="flex h-full min-h-[26rem] flex-col items-center justify-center rounded-[28px] border border-border/70 bg-muted/15 text-center">
              <Loader2 className="h-10 w-10 animate-spin text-muted-foreground" />
              <span className="mt-4 text-base font-medium">正在解析 Skill 文件</span>
            </div>
          )}

          {preview && !loading && (
            <div className="flex h-full min-h-0 gap-5 xl:flex-row flex-col">
              <div className="xl:w-[40%] shrink-0 flex min-h-0 flex-col gap-5 overflow-auto">
                <section className="rounded-2xl border border-border/70 bg-background/95 p-5 shadow-sm">
                  <div className="flex flex-wrap items-center gap-3">
                    {preview.is_update ? (
                      <Badge className="border-yellow-300 bg-yellow-100 text-yellow-800">
                        更新模式：{skillName}
                      </Badge>
                    ) : (
                      <Badge className="border-emerald-300 bg-emerald-100 text-emerald-800">
                        <CheckCircle className="mr-1 h-3.5 w-3.5" />
                        新建：{skillName}
                      </Badge>
                    )}
                    {hasMissing ? (
                      <Badge variant="outline" className="border-blue-300 text-blue-700">
                        <AlertTriangle className="mr-1 h-3.5 w-3.5" />
                        {preview.skill.missing_fields.length} 个必填字段缺失
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="border-emerald-300 text-emerald-700">
                        字段完整
                      </Badge>
                    )}
                  </div>
                  <div className="mt-4 grid gap-3 text-sm text-muted-foreground sm:grid-cols-2">
                    <div className="rounded-xl border border-border/60 bg-muted/20 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.18em]">保存方式</p>
                      <p className="mt-2 text-sm font-medium text-foreground">
                        {preview.is_update ? '覆盖已有 Skill' : '创建新 Skill'}
                      </p>
                    </div>
                    <div className="rounded-xl border border-border/60 bg-muted/20 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.18em]">文件名</p>
                      <p className="mt-2 truncate text-sm font-medium text-foreground">
                        {fileName || '未命名文件'}
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-4 w-full sm:w-auto"
                    onClick={() => setPreview(null)}
                  >
                    重新上传
                  </Button>
                </section>

                {preview.skill.warnings.length > 0 ? (
                  <section className="rounded-2xl border border-yellow-200 bg-yellow-50 p-5 text-yellow-900 shadow-sm">
                    <div className="flex items-center gap-2 text-sm font-semibold">
                      <AlertTriangle className="h-4 w-4" />
                      解析提醒
                    </div>
                    <ul className="mt-3 space-y-2 text-sm leading-6">
                      {preview.skill.warnings.map((warning, index) => (
                        <li
                          key={`${warning.field}-${index}`}
                          className="rounded-xl border border-yellow-200/80 bg-background/70 px-3 py-2"
                        >
                          <span className="font-medium">
                            {FIELD_LABELS[warning.field] || warning.field}:
                          </span>{' '}
                          {warning.message}
                        </li>
                      ))}
                    </ul>
                  </section>
                ) : null}

                {hasMissing ? (
                  <section className="rounded-2xl border border-blue-200 bg-blue-50 p-5 text-blue-900 shadow-sm">
                    <div className="text-sm font-semibold">必填字段缺失</div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {preview.skill.missing_fields.map((field) => (
                        <Badge
                          key={field}
                          variant="secondary"
                          className="rounded-full px-3 py-1 text-xs"
                        >
                          {FIELD_LABELS[field] || field}
                        </Badge>
                      ))}
                    </div>
                    <p className="mt-3 text-xs leading-5 text-muted-foreground">
                      解析未识别到这些字段。请检查 frontmatter 是否包含 name 和 description。
                    </p>
                  </section>
                ) : null}

                <MarkdownEditor value={markdown} onChange={setMarkdown} />
              </div>

              <section className="flex-1 min-h-0 flex flex-col overflow-hidden rounded-2xl border border-border/70 bg-white shadow-sm">
                <div className="shrink-0 border-b border-border/70 px-5 py-4">
                  <p className="text-sm font-semibold">解析字段预览</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    name / description / target_agents / tags 来自 frontmatter；body 与 references 从 markdown 主体抽取。
                  </p>
                </div>
                <div className="flex-1 min-h-0 overflow-auto">
                  <div className="grid gap-4 p-5 2xl:grid-cols-2">
                    {Object.entries(preview.skill.fields).map(([key, value]) => (
                      <UploadFieldCard
                        key={key}
                        fieldKey={key}
                        value={value}
                        missingFields={preview.skill.missing_fields}
                      />
                    ))}
                  </div>
                </div>
              </section>
            </div>
          )}
        </div>

        <DialogFooter className="shrink-0 border-t border-border/70 px-6 py-4 sm:px-8">
          <Button variant="outline" onClick={handleClose}>
            取消
          </Button>
          {preview && (
            <Button onClick={handleSave} disabled={saving || hasMissing}>
              {saving ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              {preview.is_update ? '确认更新' : '创建 Skill'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ===========================================================================
// Skill 查看对话框
// ===========================================================================
function SkillViewDialog({
  skill,
  open,
  onOpenChange,
}: {
  skill: SkillResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [tab, setTab] = useState<'parsed' | 'markdown'>('parsed');

  useEffect(() => {
    if (open) setTab('parsed');
  }, [open]);

  if (!skill) return null;

  const parsedFields: Array<[string, unknown]> = [
    ['description', skill.description],
    ['target_agents', skill.target_agents],
    ['body', skill.body],
    ['references', skill.references],
    ['tags', skill.tags],
    ['author', skill.author],
    ['metadata', skill.skill_metadata],
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={cn(LARGE_DIALOG_CLASSNAME, 'flex flex-col')}>
        <DialogHeader className="shrink-0 border-b border-border/70 px-6 py-5 text-left sm:px-8">
          <div className="flex items-center gap-3">
            <DialogTitle className="font-mono">{skill.name}</DialogTitle>
            {!skill.is_active && <Badge variant="secondary">已禁用</Badge>}
          </div>
          <DialogDescription>
            {skill.description}
            <span className="ml-2 text-muted-foreground">
              v{skill.version}
              {skill.author ? ` · ${skill.author}` : ''}
            </span>
          </DialogDescription>
        </DialogHeader>

        <div className="shrink-0 flex gap-1 border-b border-border/70 px-6 sm:px-8">
          <button
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === 'parsed'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setTab('parsed')}
          >
            字段
          </button>
          <button
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === 'markdown'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setTab('markdown')}
          >
            原始 Markdown
          </button>
        </div>

        <div className="flex-1 min-h-0 flex flex-col overflow-hidden px-6 py-6 sm:px-8">
          {tab === 'parsed' ? (
            <div className="flex-1 min-h-0 flex gap-5 xl:flex-row flex-col">
              <section className="xl:w-[30%] shrink-0 flex flex-col gap-5 overflow-auto">
                <div className="rounded-2xl border border-border/70 bg-background/95 p-5 shadow-sm">
                  <p className="text-sm font-semibold">基本信息</p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                    <div className="rounded-xl border border-border/60 bg-muted/20 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">name</p>
                      <p className="mt-2 break-all font-mono text-sm text-foreground">{skill.name}</p>
                    </div>
                    <div className="rounded-xl border border-border/60 bg-muted/20 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">version</p>
                      <p className="mt-2 text-sm text-foreground">v{skill.version}</p>
                    </div>
                    <div className="rounded-xl border border-border/60 bg-muted/20 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">status</p>
                      <p className="mt-2 text-sm text-foreground">
                        {skill.is_active ? '启用中' : '已禁用'}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="rounded-2xl border border-border/70 bg-background/95 p-5 shadow-sm">
                  <p className="text-sm font-semibold">适用 Sub-Agent</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {skill.target_agents.length > 0 ? (
                      skill.target_agents.map((agent) => (
                        <Badge
                          key={agent}
                          variant="outline"
                          className="rounded-full px-3 py-1 text-xs"
                        >
                          {agent}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-sm text-muted-foreground">未指定（不会被任何 sub-agent 自动加载）</span>
                    )}
                  </div>
                </div>

                <div className="rounded-2xl border border-border/70 bg-background/95 p-5 shadow-sm">
                  <p className="text-sm font-semibold">标签</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {skill.tags.length > 0 ? (
                      skill.tags.map((tag) => (
                        <Badge
                          key={tag}
                          variant="secondary"
                          className="rounded-full px-3 py-1 text-xs"
                        >
                          {tag}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-sm text-muted-foreground">暂无标签</span>
                    )}
                  </div>
                </div>
              </section>

              <section className="flex-1 min-h-0 flex flex-col overflow-hidden rounded-2xl border border-border/70 bg-white shadow-sm">
                <div className="shrink-0 border-b border-border/70 px-5 py-4">
                  <p className="text-sm font-semibold">字段</p>
                </div>
                <div className="flex-1 min-h-0 overflow-auto">
                  <div className="grid gap-4 p-5 2xl:grid-cols-2">
                    {parsedFields.map(([fieldKey, value]) => (
                      <UploadFieldCard
                        key={fieldKey}
                        fieldKey={fieldKey}
                        value={value}
                        missingFields={[]}
                        showStatusBadge={false}
                      />
                    ))}
                  </div>
                </div>
              </section>
            </div>
          ) : (
            <section className="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-border/70 bg-background shadow-sm">
              <ViewMarkdownContent content={skill.raw_markdown || ''} />
            </section>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ===========================================================================
// Skill 卡片
// ===========================================================================
function SkillCard({
  skill,
  onClick,
  onDelete,
  onToggle,
}: {
  skill: SkillResponse;
  onClick: () => void;
  onDelete: () => void;
  onToggle: (active: boolean) => void;
}) {
  return (
    <Card
      className="group relative cursor-pointer hover:border-primary/50 transition-colors"
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-mono text-sm truncate">{skill.name}</h3>
              {!skill.is_active && (
                <Badge variant="secondary" className="text-xs">
                  已禁用
                </Badge>
              )}
            </div>
            <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
              {skill.description || '无描述'}
            </p>
            <div className="mt-2 flex flex-wrap gap-1">
              {skill.target_agents.slice(0, 3).map((agent) => (
                <Badge key={agent} variant="outline" className="text-xs">
                  {agent}
                </Badge>
              ))}
              {skill.tags.slice(0, 3).map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
            <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
              {skill.body && (
                <span className="flex items-center gap-1">
                  <FileText className="h-3 w-3" />
                  body
                </span>
              )}
              {skill.references.length > 0 && (
                <span>引用 {skill.references.length}</span>
              )}
              <span>v{skill.version}</span>
            </div>
          </div>

          <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => onToggle(!skill.is_active)}
              title={skill.is_active ? '禁用' : '启用'}
            >
              {skill.is_active ? (
                <EyeOff className="h-4 w-4 text-muted-foreground" />
              ) : (
                <Eye className="h-4 w-4 text-green-600" />
              )}
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={onClick}>
                  <Eye className="mr-2 h-4 w-4" />
                  查看
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href={`/admin/skills/${skill.name}`}>
                    <Pencil className="mr-2 h-4 w-4" />
                    编辑
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onSelect={() => onDelete()}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  删除
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ===========================================================================
// 主页面
// ===========================================================================
export default function AdminSkillsPage() {
  const [skills, setSkills] = useState<SkillResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState<string>('');
  const [agentFilter, setAgentFilter] = useState<string>('');
  const [viewSkill, setViewSkill] = useState<SkillResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchSkills = useCallback(async () => {
    setLoading(true);
    try {
      const res = await skillsApi.list(
        page,
        pageSize,
        activeFilter === '' ? undefined : activeFilter === 'true',
      );
      setSkills(res.items);
      setTotal(res.total);
    } catch (e) {
      toast.error(`加载失败: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, activeFilter]);

  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  const handleDelete = async (name: string) => {
    setDeleting(true);
    try {
      await skillsApi.delete(name);
      toast.success('删除成功');
      setDeleteTarget(null);
      fetchSkills();
    } catch (e) {
      toast.error(`删除失败: ${(e as Error).message}`);
    } finally {
      setDeleting(false);
    }
  };

  const handleToggle = async (name: string, isActive: boolean) => {
    try {
      await skillsApi.update(name, { is_active: isActive });
      toast.success(isActive ? '已启用' : '已禁用');
      fetchSkills();
    } catch (e) {
      toast.error(`操作失败: ${(e as Error).message}`);
    }
  };

  const filtered = skills.filter((s) => {
    if (search) {
      const q = search.toLowerCase();
      const matches =
        s.name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.tags.some((t) => t.toLowerCase().includes(q));
      if (!matches) return false;
    }
    if (agentFilter && !s.target_agents.includes(agentFilter)) {
      return false;
    }
    return true;
  });

  // 简单聚合所有 skill 中出现过的 target_agents 作为 filter 选项
  const knownAgents = Array.from(
    new Set(skills.flatMap((s) => s.target_agents)),
  ).sort();

  const totalPages = Math.ceil(total / pageSize);

  return (
    <AppLayout title="AI 技能库">
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3 flex-wrap flex-1">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索 name / description / tag..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select
              value={agentFilter || 'all'}
              onValueChange={(v) => {
                setAgentFilter(v === 'all' ? '' : v);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-44">
                <SelectValue placeholder="全部 Sub-Agent" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部 Sub-Agent</SelectItem>
                {knownAgents.map((a) => (
                  <SelectItem key={a} value={a}>
                    {a}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={activeFilter || 'all'}
              onValueChange={(v) => {
                setActiveFilter(v === 'all' ? '' : v);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-28">
                <SelectValue placeholder="全部状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="true">已启用</SelectItem>
                <SelectItem value="false">已禁用</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">共 {total} 个 Skill</span>
            <SkillSourceDialog
              defaultMode="write"
              triggerLabel="新建 Skill"
              triggerIcon="edit"
              triggerVariant="outline"
              onSaved={fetchSkills}
            />
            <SkillSourceDialog
              defaultMode="upload"
              triggerLabel="上传 SKILL.md"
              triggerIcon="upload"
              onSaved={fetchSkills}
            />
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Brain className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">暂无 Skill</h3>
            <p className="text-sm text-muted-foreground mt-1">
              上传第一个 SKILL.md 文件开始构建领域知识库
            </p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((skill) => (
              <SkillCard
                key={skill.name}
                skill={skill}
                onClick={() => setViewSkill(skill)}
                onDelete={() => setDeleteTarget(skill.name)}
                onToggle={(active) => handleToggle(skill.name, active)}
              />
            ))}
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              上一页
            </Button>
            <span className="text-sm text-muted-foreground">
              第 {page} / {totalPages} 页
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
            >
              下一页
            </Button>
          </div>
        )}

        <SkillViewDialog
          skill={viewSkill}
          open={!!viewSkill}
          onOpenChange={(v) => !v && setViewSkill(null)}
        />

        <Dialog
          open={!!deleteTarget}
          onOpenChange={(v) => !v && setDeleteTarget(null)}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>确认删除</DialogTitle>
              <DialogDescription>
                确定删除 Skill <strong>{deleteTarget}</strong>？此操作不可撤销。
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteTarget(null)}>
                取消
              </Button>
              <Button
                variant="destructive"
                onClick={() => deleteTarget && handleDelete(deleteTarget)}
                disabled={deleting}
              >
                {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                删除
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
}
