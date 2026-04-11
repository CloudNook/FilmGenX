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
  Loader2,
  AlertTriangle,
  CheckCircle,
  Save,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { skillsApi, type SkillResponse, type SkillUploadResponse } from '@/lib/api';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

// ===========================================================================
// 常量
// ===========================================================================
const FIELD_LABELS: Record<string, string> = {
  name: '名称',
  title: '标题',
  description: '描述',
  content: '核心指令',
  parameters: '参数定义',
  examples: '使用示例',
  constraints: '约束条件',
  category: '领域分类',
  difficulty: '难度',
  tags: '标签',
  author: '作者',
  metadata: '元数据',
};

const CATEGORIES = ['剧本', '灯光', '运镜', '调色', '音效', '特效', '服装', '道具', '合成', '其他'];
const DIFFICULTIES = [
  { value: 'beginner', label: '入门' },
  { value: 'intermediate', label: '进阶' },
  { value: 'advanced', label: '专家' },
];

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

const LONG_TEXT_FIELDS = new Set(['content', 'description']);
const JSON_FIELDS = new Set(['parameters', 'metadata']);

function isEmptyFieldValue(value: unknown): boolean {
  if (value === null || value === undefined || value === '') return true;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === 'object') return Object.keys(value as object).length === 0;
  return false;
}

// ===========================================================================
// Markdown 编辑器（源码 / 渲染 切换 + 可编辑 + 可保存）
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
      {/* 头部 */}
      <div className="flex items-center justify-between border-b border-border/70 px-5 py-3">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold">原始 Markdown</p>
          <div className="flex rounded-lg border border-border/70 bg-muted/30 p-0.5">
            <button
              className={cn(
                'rounded-md px-3 py-1 text-xs font-medium transition-colors',
                mode === 'preview' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground',
              )}
              onClick={() => setMode('preview')}
            >
              渲染
            </button>
            <button
              className={cn(
                'rounded-md px-3 py-1 text-xs font-medium transition-colors',
                mode === 'source' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground',
              )}
              onClick={() => setMode('source')}
            >
              源码
            </button>
          </div>
        </div>
        {!editing ? (
          <Button variant="outline" size="sm" onClick={() => { setEditing(true); setMode('source'); }}>
            <Pencil className="mr-1.5 h-3.5 w-3.5" />
            编辑
          </Button>
        ) : (
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => setEditing(false)}>
              取消编辑
            </Button>
          </div>
        )}
      </div>

      {/* 内容 */}
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

function renderFieldStateBadge(fieldKey: string, value: unknown, missingFields: string[]): ReactNode {
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
          'rounded-xl border border-border/60 bg-white px-4 py-3 text-sm leading-6 whitespace-pre-wrap',
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
                {String(item)}
              </div>
            ))}
          </div>
      </div>
    );
  }

  return (
    <div className={cn('overflow-auto rounded-xl border border-border/60 bg-white text-black', className, JSON_FIELDS.has(fieldKey) ? 'max-h-[24rem]' : 'max-h-72')}>
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
          <p className="text-sm font-semibold text-foreground">{FIELD_LABELS[fieldKey] || fieldKey}</p>
          <p className="mt-1 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{fieldKey}</p>
        </div>
        {showStatusBadge ? renderFieldStateBadge(fieldKey, value, missingFields) : null}
      </div>

      <div className="mt-4">
        <FieldValuePreview fieldKey={fieldKey} value={value} />
      </div>
    </article>
  );
}

// 只读 Markdown 查看器（渲染 / 源码 切换）
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
              mode === 'preview' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground',
            )}
            onClick={() => setMode('preview')}
          >
            渲染
          </button>
          <button
            className={cn(
              'rounded-md px-3 py-1 text-xs font-medium transition-colors',
              mode === 'source' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground',
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
          <pre className="px-5 py-4 text-sm leading-7 whitespace-pre-wrap text-foreground">{content}</pre>
        )}
      </ScrollArea>
    </>
  );
}

// ===========================================================================
// 上传对话框（宽弹窗 + 自动解析 + name 去重）
// ===========================================================================
function UploadDialog({ onUploaded }: { onUploaded: () => void }) {
  const [open, setOpen] = useState(false);
  const [markdown, setMarkdown] = useState('');
  const [fileName, setFileName] = useState('');
  const [preview, setPreview] = useState<SkillUploadResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    const text = await file.text();
    setMarkdown(text);
    await doParse(text);
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
      const fields = { ...preview.skill.fields };
      for (const mf of preview.skill.missing_fields) {
        if (mf === 'examples' || mf === 'constraints' || mf === 'tags') {
          fields[mf] = [];
        } else if (mf === 'parameters' || mf === 'metadata') {
          fields[mf] = {};
        } else {
          fields[mf] = '';
        }
      }

      await skillsApi.create({
        ...fields,
        raw_markdown: markdown,
      } as Parameters<typeof skillsApi.create>[0]);

      toast.success('Skill 已创建');
      handleClose();
      onUploaded();
    } catch (e) {
      toast.error(`保存失败: ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    setOpen(false);
    setMarkdown('');
    setFileName('');
    setPreview(null);
  };

  const skillName = preview?.skill.fields.name as string | undefined;
  const hasMissing = (preview?.skill.missing_fields.length ?? 0) > 0;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button onClick={() => setOpen(true)}>
        <Upload className="mr-2 h-4 w-4" />
        上传 SKILL.md
      </Button>

      <DialogContent className={cn(LARGE_DIALOG_CLASSNAME, 'flex flex-col')}>
        <DialogHeader className="shrink-0 border-b border-border/70 px-6 py-5 text-left sm:px-8">
          <DialogTitle>上传 SKILL.md</DialogTitle>
          <DialogDescription>
            选择 .md 文件上传，系统会自动解析字段并在保存前展示完整预览。
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 min-h-0 overflow-hidden px-6 py-6 sm:px-8">
          {!preview && !loading && (
            <label className="flex h-full min-h-[26rem] cursor-pointer flex-col items-center justify-center rounded-[28px] border-2 border-dashed border-border/70 bg-muted/20 px-8 py-12 text-center transition-colors hover:border-primary/45 hover:bg-muted/35">
              <div className="rounded-full border border-border/70 bg-background p-4 shadow-sm">
                <Upload className="h-10 w-10 text-primary" />
              </div>
              <span className="mt-6 text-lg font-semibold">点击选择 SKILL.md 文件</span>
              <span className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
                支持 `.md` / `.markdown`，上传后会自动解析字段、提示缺失项，并在保存前展示完整内容预览。
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

          {loading && (
            <div className="flex h-full min-h-[26rem] flex-col items-center justify-center rounded-[28px] border border-border/70 bg-muted/15 text-center">
              <Loader2 className="h-10 w-10 animate-spin text-muted-foreground" />
              <span className="mt-4 text-base font-medium">正在解析 Skill 文件</span>
              <span className="mt-2 text-sm text-muted-foreground">系统会自动抽取字段并生成保存预览</span>
            </div>
          )}

          {preview && !loading && (
            <div className="flex h-full min-h-0 gap-5 xl:flex-row flex-col">
              <div className="xl:w-[40%] shrink-0 flex min-h-0 flex-col gap-5 overflow-auto">
                <section className="rounded-2xl border border-border/70 bg-background/95 p-5 shadow-sm">
                  <div className="flex flex-wrap items-center gap-3">
                    {preview.is_update ? (
                      <Badge className="border-yellow-300 bg-yellow-100 text-yellow-800">
                        更新模式：Skill &quot;{skillName}&quot;
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
                        {preview.skill.missing_fields.length} 个字段缺失
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
                      <p className="mt-2 truncate text-sm font-medium text-foreground">{fileName || '未命名文件'}</p>
                    </div>
                  </div>
                  <Button variant="outline" size="sm" className="mt-4 w-full sm:w-auto" onClick={() => setPreview(null)}>
                    重新上传
                  </Button>
                </section>

                {preview.skill.warnings.length > 0 ? (
                  <section className="rounded-2xl border border-yellow-200 bg-yellow-50 p-5 text-yellow-900 shadow-sm dark:border-yellow-900/60 dark:bg-yellow-950/40 dark:text-yellow-100">
                    <div className="flex items-center gap-2 text-sm font-semibold">
                      <AlertTriangle className="h-4 w-4" />
                      解析提醒
                    </div>
                    <ul className="mt-3 space-y-2 text-sm leading-6">
                      {preview.skill.warnings.map((warning, index) => (
                        <li key={`${warning.field}-${index}`} className="rounded-xl border border-yellow-200/80 bg-background/70 px-3 py-2 dark:border-yellow-900/50 dark:bg-background/20">
                          <span className="font-medium">{FIELD_LABELS[warning.field] || warning.field}:</span> {warning.message}
                        </li>
                      ))}
                    </ul>
                  </section>
                ) : null}

                {hasMissing ? (
                  <section className="rounded-2xl border border-blue-200 bg-blue-50 p-5 text-blue-900 shadow-sm dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-100">
                    <div className="text-sm font-semibold">待补全字段</div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {preview.skill.missing_fields.map((field) => (
                        <Badge key={field} variant="secondary" className="rounded-full px-3 py-1 text-xs">
                          {FIELD_LABELS[field] || field}
                        </Badge>
                      ))}
                    </div>
                  </section>
                ) : null}

                <MarkdownEditor
                  value={markdown}
                  onChange={setMarkdown}
                />
              </div>

              <section className="flex-1 min-h-0 flex flex-col overflow-hidden rounded-2xl border border-border/70 bg-white shadow-sm">
                <div className="shrink-0 border-b border-border/70 px-5 py-4">
                  <p className="text-sm font-semibold">字段预览</p>
                  <p className="mt-1 text-xs text-muted-foreground">每个字段都以可滚动卡片展示，长文本和 JSON 不再被压缩到小窗口。</p>
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
            <Button onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
              {preview.is_update ? '确认更新' : '创建 Skill'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ===========================================================================
// Skill 查看对话框（展示原始 Markdown + 解析字段）
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
    ['title', skill.title],
    ['description', skill.description],
    ['content', skill.content],
    ['parameters', skill.parameters],
    ['examples', skill.examples],
    ['constraints', skill.constraints],
    ['metadata', skill.metadata],
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={cn(LARGE_DIALOG_CLASSNAME, 'flex flex-col')}>
        <DialogHeader className="shrink-0 border-b border-border/70 px-6 py-5 text-left sm:px-8">
          <div className="flex items-center gap-3">
            <DialogTitle>{skill.title || skill.name}</DialogTitle>
            {!skill.is_active && <Badge variant="secondary">已禁用</Badge>}
          </div>
          <DialogDescription>
            {skill.description}
            <span className="ml-2 text-muted-foreground">
              v{skill.version} · {skill.category || '未分类'}
            </span>
          </DialogDescription>
        </DialogHeader>

        {/* Tab 切换 */}
        <div className="shrink-0 flex gap-1 border-b border-border/70 px-6 sm:px-8">
          <button
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === 'parsed'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setTab('parsed')}
          >
            解析字段
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
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">category</p>
                      <p className="mt-2 text-sm text-foreground">{skill.category || '—'}</p>
                    </div>
                    <div className="rounded-xl border border-border/60 bg-muted/20 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">difficulty</p>
                      <p className="mt-2 text-sm text-foreground">
                        {DIFFICULTIES.find((item) => item.value === skill.difficulty)?.label || '—'}
                      </p>
                    </div>
                    <div className="rounded-xl border border-border/60 bg-muted/20 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">author</p>
                      <p className="mt-2 text-sm text-foreground">{skill.author || '—'}</p>
                    </div>
                    <div className="rounded-xl border border-border/60 bg-muted/20 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">version</p>
                      <p className="mt-2 text-sm text-foreground">v{skill.version}</p>
                    </div>
                    <div className="rounded-xl border border-border/60 bg-muted/20 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">status</p>
                      <p className="mt-2 text-sm text-foreground">{skill.is_active ? '启用中' : '已禁用'}</p>
                    </div>
                  </div>
                </div>

                <div className="rounded-2xl border border-border/70 bg-background/95 p-5 shadow-sm">
                  <p className="text-sm font-semibold">标签</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {skill.tags?.length > 0 ? (
                      skill.tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="rounded-full px-3 py-1 text-xs">
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
                  <p className="text-sm font-semibold">解析字段</p>
                  <p className="mt-1 text-xs text-muted-foreground">长文本、数组和 JSON 都支持更舒适的阅读与滚动。</p>
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
// Skill 卡片（点击 = 查看，整个卡片可点击）
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
              {skill.title && <h3 className="font-semibold text-sm truncate">{skill.title}</h3>}
              <span className="font-mono text-xs text-muted-foreground shrink-0">{skill.name}</span>
              {!skill.is_active && <Badge variant="secondary" className="text-xs">已禁用</Badge>}
            </div>
            <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{skill.description || '无描述'}</p>
            <div className="mt-2 flex flex-wrap gap-1">
              {skill.category && <Badge variant="outline" className="text-xs">{skill.category}</Badge>}
              {skill.difficulty && (
                <Badge variant="outline" className="text-xs">
                  {DIFFICULTIES.find(d => d.value === skill.difficulty)?.label}
                </Badge>
              )}
              {skill.tags?.slice(0, 3).map(tag => <Badge key={tag} variant="secondary" className="text-xs">{tag}</Badge>)}
            </div>
            <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
              {skill.content && <span className="flex items-center gap-1"><FileText className="h-3 w-3" />content</span>}
              {skill.examples?.length > 0 && <span>示例 {skill.examples.length}</span>}
              {skill.constraints?.length > 0 && <span>约束 {skill.constraints.length}</span>}
              <span>v{skill.version}</span>
            </div>
          </div>

          {/* 操作按钮（阻止冒泡，不触发卡片点击） */}
          <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => onToggle(!skill.is_active)}
              title={skill.is_active ? '禁用' : '启用'}
            >
              {skill.is_active ? <EyeOff className="h-4 w-4 text-muted-foreground" /> : <Eye className="h-4 w-4 text-green-600" />}
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={onClick}>
                  <Eye className="mr-2 h-4 w-4" />查看
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href={`/admin/skills/${skill.name}`}>
                    <Pencil className="mr-2 h-4 w-4" />编辑
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="text-destructive focus:text-destructive" onSelect={() => onDelete()}>
                  <Trash2 className="mr-2 h-4 w-4" />删除
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
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [activeFilter, setActiveFilter] = useState<string>('');
  const [viewSkill, setViewSkill] = useState<SkillResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchSkills = useCallback(async () => {
    setLoading(true);
    try {
      const res = await skillsApi.list(
        page,
        pageSize,
        categoryFilter || undefined,
        activeFilter === '' ? undefined : activeFilter === 'true',
      );
      setSkills(res.items);
      setTotal(res.total);
    } catch (e) {
      toast.error(`加载失败: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, categoryFilter, activeFilter]);

  useEffect(() => { fetchSkills(); }, [fetchSkills]);

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

  const filtered = search
    ? skills.filter(s =>
        s.name.includes(search.toLowerCase()) ||
        s.title?.includes(search) ||
        s.description?.includes(search) ||
        s.category?.includes(search),
      )
    : skills;

  const totalPages = Math.ceil(total / pageSize);

  return (
    <AppLayout title="AI 技能库">
      <div className="p-6 space-y-6">
        {/* 顶部操作栏 */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3 flex-wrap flex-1">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索 name / title / 描述..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={categoryFilter || 'all'} onValueChange={(v) => { setCategoryFilter(v === 'all' ? '' : v); setPage(1); }}>
              <SelectTrigger className="w-40"><SelectValue placeholder="全部分类" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部分类</SelectItem>
                {CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={activeFilter || 'all'} onValueChange={(v) => { setActiveFilter(v === 'all' ? '' : v); setPage(1); }}>
              <SelectTrigger className="w-28"><SelectValue placeholder="全部状态" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="true">已启用</SelectItem>
                <SelectItem value="false">已禁用</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">共 {total} 个 Skill</span>
            <UploadDialog onUploaded={fetchSkills} />
          </div>
        </div>

        {/* 列表 */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Brain className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium">暂无 Skill</h3>
            <p className="text-sm text-muted-foreground mt-1">上传第一个 SKILL.md 文件开始构建 AI 专业知识库</p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map(skill => (
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

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>上一页</Button>
            <span className="text-sm text-muted-foreground">第 {page} / {totalPages} 页</span>
            <Button variant="outline" size="sm" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>下一页</Button>
          </div>
        )}

        {/* 查看 Skill 弹窗 */}
        <SkillViewDialog skill={viewSkill} open={!!viewSkill} onOpenChange={(v) => !v && setViewSkill(null)} />

        {/* 删除确认 */}
        <Dialog open={!!deleteTarget} onOpenChange={(v) => !v && setDeleteTarget(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>确认删除</DialogTitle>
              <DialogDescription>确定删除 Skill <strong>{deleteTarget}</strong>？此操作不可撤销。</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteTarget(null)}>取消</Button>
              <Button variant="destructive" onClick={() => deleteTarget && handleDelete(deleteTarget)} disabled={deleting}>
                {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}删除
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
}
