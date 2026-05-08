'use client';

/**
 * Sub-agent 结果渲染卡片。
 *
 * 替代 supervisor 流里直接 dump JSON 的 ``<pre>`` 块——按 sub-agent 名分派到
 * 对应 schema 的渲染器：
 * - outline_agent  → OutlineRenderer
 * - script_agent   → ScriptRenderer
 * - storyboard_agent → StoryboardRenderer
 *
 * TS 接口与 backend ``app/schemas/agent_outputs/*.py`` 的 Pydantic 类一一对应；
 * Pydantic spec 改了之后这里手工同步即可（业务层 spec 演化比框架慢，没必要做代码生成）。
 *
 * Result 形态分支：
 * - ``{ok: false, error_code, message, hint, context}``     → ToolErrorCard
 * - ``{error: string, sub_agent_name?: string}``            → ErrorCard
 * - ``{output: string-of-json, sub_agent_name?: string}``   → 结构化渲染（按名匹配）
 * - 其它                                                     → 兜底 JSON pre
 */

import type { ReactNode } from 'react';
import { AlertTriangle, Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import {
  getFieldTitle,
  useAgentSchema,
  type JsonSchema,
} from '@/lib/agent-schemas';
// 没有专用 renderer 的 sub-agent（visual_style / character_ref / scene_ref /
// frame_prompt / video_prompt 等）走 schema-aware 通用渲染：用 schema.title 当卡片标题，
// 内容交给 ToolPayloadView 递归展开。等积累足够 prompt 调通的 fixture 再回头写专用
// renderer，避免在字段还在调整时重复造样式。
const GENERIC_AGENT_NAMES = new Set([
  'visual_style_agent',
  'character_ref_agent',
  'scene_ref_agent',
  'frame_prompt_agent',
  'video_prompt_agent',
]);

/**
 * 字段标签：优先用 schema 的 title，缺失时退到 fallback；都没有就用 field key 原文。
 * renderer 内部各处的 ``"目标："`` / ``"角色"`` 等中文 label 都走这条入口，schema
 * 改动 title → UI 自动同步；schema 还没加载完成 → 显示 fallback / key 原文。
 */
function fieldLabel(
  schema: JsonSchema | null,
  path: string[],
  fallback?: string,
): string {
  if (schema) {
    const t = getFieldTitle(schema, path);
    if (t) return t;
  }
  if (fallback) return fallback;
  return path[path.length - 1] ?? '';
}

// ---------------------------------------------------------------------- //
// schema TS interfaces（与 backend Pydantic 类对齐）
// ---------------------------------------------------------------------- //

interface CharacterArc {
  name: string;
  role: string;
  want: string;
  need: string;
  arc_summary: string;
}

interface Act {
  act_number: number;
  title: string;
  goal: string;
  key_events: string[];
  turning_point: string;
}

interface Beat {
  beat_name: string;
  description: string;
  act_ref: number;
}

interface OutlineOutput {
  title: string;
  logline: string;
  synopsis: string;
  themes: string[];
  characters: CharacterArc[];
  acts: Act[];
  beats?: Beat[];
}

interface DialogueLine {
  character: string;
  line: string;
  parenthetical?: string | null;
}

interface SceneAction {
  description: string;
}

interface Scene {
  scene_number: number;
  space: string;
  location: string;
  time_of_day: string;
  heading: string;
  summary: string;
  emotional_beat: string;
  actions: SceneAction[];
  dialogues: DialogueLine[];
  duration_estimate_seconds?: number | null;
}

interface ScriptOutput {
  title: string;
  based_on_outline: string;
  scenes: Scene[];
}

interface Shot {
  shot_number: number;
  scene_number: number;
  shot_size: string;
  camera_movement: string;
  camera_angle: string;
  composition_notes: string;
  visual_description: string;
  duration_seconds: number;
  audio_notes?: string | null;
  transition_to_next?: string | null;
}

interface StoryboardOutput {
  title: string;
  based_on_script: string;
  shots: Shot[];
}

// ---------------------------------------------------------------------- //
// 主入口
// ---------------------------------------------------------------------- //

interface SubAgentResultCardProps {
  subAgentName?: string;
  result: unknown;
}

export function SubAgentResultCard({
  subAgentName = '',
  result: rawResult,
}: SubAgentResultCardProps) {
  // 永远先 call hook，遵守 React rules of hooks（不能在 if/return 之后）。
  // 未知 sub-agent 名传空字符串，hook 内部找不到 schema 返回 null，不影响兜底分支。
  const schema = useAgentSchema(subAgentName);

  if (rawResult == null) return null;

  // 兼容：从持久化历史回灌时，tool_end.result 可能是 JSON 字符串（``agent_messages.content``
  // 是 string，``_record_to_history_events`` 直接传给 result）。先尝试 parse 一次让后续
  // 分支走在结构化对象上。
  let result: unknown = rawResult;
  if (typeof rawResult === 'string') {
    try {
      const parsed = JSON.parse(rawResult);
      if (parsed && typeof parsed === 'object') {
        result = parsed;
      }
    } catch {
      // 保持原 string，下面分支会按字符串兜底处理
    }
  }

  // 1) 结构化 ToolError
  if (
    typeof result === 'object' &&
    result !== null &&
    (result as Record<string, unknown>).ok === false &&
    typeof (result as Record<string, unknown>).error_code === 'string'
  ) {
    return <ToolErrorCard payload={result as ToolErrorPayload} />;
  }

  // 2) 旧格式 error
  if (
    typeof result === 'object' &&
    result !== null &&
    typeof (result as Record<string, unknown>).error === 'string'
  ) {
    return (
      <ErrorCard message={(result as Record<string, string>).error} />
    );
  }

  // 3) 结构化 output（按 sub-agent 名分派）
  const output =
    typeof result === 'object' && result !== null
      ? (result as Record<string, unknown>).output
      : undefined;
  if (typeof output === 'string' && output.trim()) {
    const parsed = tryParseJson(output);
    if (parsed) {
      switch (subAgentName) {
        case 'outline_agent':
          if (looksLikeOutline(parsed)) {
            return <OutlineRenderer data={parsed as OutlineOutput} schema={schema} />;
          }
          break;
        case 'script_agent':
          if (looksLikeScript(parsed)) {
            return <ScriptRenderer data={parsed as ScriptOutput} schema={schema} />;
          }
          break;
        case 'storyboard_agent':
          if (looksLikeStoryboard(parsed)) {
            return <StoryboardRenderer data={parsed as StoryboardOutput} schema={schema} />;
          }
          break;
      }
      // 5 个新 sub-agent（visual_style / character_ref / scene_ref / frame_prompt /
      // video_prompt）暂未实现专用 renderer，走 schema-aware 通用展示
      if (
        GENERIC_AGENT_NAMES.has(subAgentName) &&
        parsed &&
        typeof parsed === 'object'
      ) {
        return <GenericSchemaRenderer data={parsed} schema={schema} />;
      }
      // 已成功 parse 为 JSON 但 schema 不对：退回 JSON pretty print
      return <JsonFallback value={parsed} />;
    }
    // 不是 JSON：当成纯文本（LLM 偶尔不按 schema 输出）
    return <RawTextFallback text={output} />;
  }

  // 4) 兜底
  return <JsonFallback value={result} />;
}

// ---------------------------------------------------------------------- //
// helpers
// ---------------------------------------------------------------------- //

interface ToolErrorPayload {
  ok: false;
  error_code: string;
  message: string;
  hint?: string;
  context?: Record<string, unknown>;
}

function tryParseJson(text: string): unknown | null {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function looksLikeOutline(v: unknown): boolean {
  if (typeof v !== 'object' || v === null) return false;
  const o = v as Record<string, unknown>;
  return (
    typeof o.title === 'string' &&
    typeof o.logline === 'string' &&
    Array.isArray(o.acts)
  );
}

function looksLikeScript(v: unknown): boolean {
  if (typeof v !== 'object' || v === null) return false;
  const o = v as Record<string, unknown>;
  return typeof o.title === 'string' && Array.isArray(o.scenes);
}

function looksLikeStoryboard(v: unknown): boolean {
  if (typeof v !== 'object' || v === null) return false;
  const o = v as Record<string, unknown>;
  return typeof o.title === 'string' && Array.isArray(o.shots);
}

// ---------------------------------------------------------------------- //
// 通用小组件
// ---------------------------------------------------------------------- //

function SectionHeading({ children }: { children: ReactNode }) {
  return (
    <h4 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
      {children}
    </h4>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </p>
      <div className="mt-1 text-sm text-foreground">{children}</div>
    </div>
  );
}

function StructuredShell({
  title,
  subtitle,
  children,
  accent = 'primary',
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  accent?: 'primary' | 'amber' | 'rose';
}) {
  const accentStyles = {
    primary: 'border-primary/20 bg-background/80',
    amber: 'border-amber-300/40 bg-amber-50/40',
    rose: 'border-rose-300/40 bg-rose-50/40',
  } as const;
  return (
    <div
      className={cn(
        'rounded-md border px-4 py-3 space-y-3',
        accentStyles[accent],
      )}
    >
      <div className="flex items-center gap-2">
        <Sparkles className="h-3.5 w-3.5 text-primary" />
        <p className="text-sm font-semibold text-foreground">{title}</p>
        {subtitle && (
          <span className="text-xs text-muted-foreground">{subtitle}</span>
        )}
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function JsonFallback({ value }: { value: unknown }) {
  return (
    <pre className="overflow-x-auto whitespace-pre-wrap break-all rounded bg-background/60 p-2 text-xs text-muted-foreground">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

/**
 * Schema-aware 通用渲染器。
 *
 * 与 outline / script / storyboard 专用 renderer 同体系：
 * - 顶层 ``StructuredShell``（title 取 schema.title，subtitle 取 description 或数组计数）
 * - 标量字段走 ``Field`` 行（label 优先 schema.title，缺失时人化字段名）
 * - 字符串数组 → ``Badge`` 列
 * - 对象数组 → ``SectionHeading`` + 一组小卡片（每张卡片再递归渲染）
 * - 嵌套对象 → ``SectionHeading`` + 子卡片
 *
 * 字段顺序保持 LLM 输出原序；scalar 字段先渲染、复杂字段后渲染。
 */
function GenericSchemaRenderer({
  data,
  schema,
}: {
  data: unknown;
  schema: JsonSchema | null;
}) {
  if (!isPlainObject(data)) {
    return <JsonFallback value={data} />;
  }
  const title =
    (schema && typeof schema.title === 'string' && schema.title) || '结构化输出';
  const subtitle = buildSubtitle(data, schema);
  return (
    <StructuredShell title={title} subtitle={subtitle}>
      <SchemaObjectBody data={data} rootSchema={schema} path={[]} />
    </StructuredShell>
  );
}

function SchemaObjectBody({
  data,
  rootSchema,
  path,
}: {
  data: Record<string, unknown>;
  rootSchema: JsonSchema | null;
  path: string[];
}) {
  const entries = Object.entries(data).filter(([, v]) => !isEmpty(v));
  const scalarEntries = entries.filter(([, v]) => isScalar(v));
  const complexEntries = entries.filter(([, v]) => !isScalar(v));

  return (
    <div className="space-y-3">
      {scalarEntries.length > 0 && (
        <div className="space-y-2.5">
          {scalarEntries.map(([k, v]) => (
            <Field
              key={k}
              label={fieldLabel(rootSchema, [...path, k], humanizeKey(k))}
            >
              {renderScalar(v)}
            </Field>
          ))}
        </div>
      )}
      {complexEntries.map(([k, v]) => (
        <ComplexSection
          key={k}
          title={fieldLabel(rootSchema, [...path, k], humanizeKey(k))}
          value={v}
          rootSchema={rootSchema}
          path={[...path, k]}
        />
      ))}
    </div>
  );
}

function ComplexSection({
  title,
  value,
  rootSchema,
  path,
}: {
  title: string;
  value: unknown;
  rootSchema: JsonSchema | null;
  path: string[];
}) {
  if (Array.isArray(value) && value.length > 0 && value.every(isScalar)) {
    return (
      <div className="space-y-2">
        <SectionHeading>{title}</SectionHeading>
        <div className="flex flex-wrap gap-1.5">
          {value.map((v, i) => (
            <Badge key={i} variant="secondary" className="text-xs">
              {String(v)}
            </Badge>
          ))}
        </div>
      </div>
    );
  }

  if (Array.isArray(value) && value.length > 0 && value.every(isPlainObject)) {
    return (
      <div className="space-y-2">
        <SectionHeading>{`${title} · ${value.length}`}</SectionHeading>
        <div className="space-y-2">
          {value.map((item, i) => (
            <div
              key={i}
              className="rounded-md border border-border/60 bg-background/80 px-3 py-2.5"
            >
              <SchemaObjectBody
                data={item as Record<string, unknown>}
                rootSchema={rootSchema}
                path={path}
              />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (isPlainObject(value)) {
    return (
      <div className="space-y-2">
        <SectionHeading>{title}</SectionHeading>
        <div className="rounded-md border border-border/60 bg-background/80 px-3 py-2.5">
          <SchemaObjectBody
            data={value}
            rootSchema={rootSchema}
            path={path}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <SectionHeading>{title}</SectionHeading>
      <JsonFallback value={value} />
    </div>
  );
}

function isScalar(v: unknown): boolean {
  return v === null || typeof v !== 'object';
}

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return v !== null && typeof v === 'object' && !Array.isArray(v);
}

function isEmpty(v: unknown): boolean {
  if (v === null || v === undefined) return true;
  if (typeof v === 'string' && v.trim() === '') return true;
  if (Array.isArray(v) && v.length === 0) return true;
  if (isPlainObject(v) && Object.keys(v).length === 0) return true;
  return false;
}

function renderScalar(v: unknown): ReactNode {
  if (v === null || v === undefined || v === '') {
    return <span className="italic text-muted-foreground">—</span>;
  }
  if (typeof v === 'boolean' || typeof v === 'number') {
    return (
      <Badge variant="outline" className="font-mono text-[10px]">
        {String(v)}
      </Badge>
    );
  }
  const s = String(v);
  if (s.length > 80) {
    return (
      <p className="text-sm leading-6 whitespace-pre-wrap break-words">
        {s}
      </p>
    );
  }
  return <span className="text-sm">{s}</span>;
}

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function buildSubtitle(
  data: Record<string, unknown>,
  schema: JsonSchema | null,
): string | undefined {
  if (
    schema &&
    typeof schema.description === 'string' &&
    schema.description.length > 0 &&
    schema.description.length < 120
  ) {
    return schema.description;
  }
  const arrays = Object.entries(data).filter(([, v]) => Array.isArray(v));
  if (arrays.length === 1) {
    const [k, v] = arrays[0];
    return `${humanizeKey(k)} · ${(v as unknown[]).length}`;
  }
  return undefined;
}

function RawTextFallback({ text }: { text: string }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs text-amber-700">
        <AlertTriangle className="h-3.5 w-3.5" />
        <span>未识别为结构化输出，按原文展示</span>
      </div>
      <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded bg-background/60 p-2 text-xs text-muted-foreground">
        {text}
      </pre>
    </div>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-rose-300/60 bg-rose-50/60 px-4 py-3">
      <div className="flex items-center gap-2 text-sm font-medium text-rose-800">
        <AlertTriangle className="h-3.5 w-3.5" />
        Sub-agent 异常
      </div>
      <p className="mt-2 text-xs text-rose-900/80 whitespace-pre-wrap break-words">
        {message}
      </p>
    </div>
  );
}

function ToolErrorCard({ payload }: { payload: ToolErrorPayload }) {
  return (
    <div className="rounded-md border border-amber-300/60 bg-amber-50/60 px-4 py-3 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <AlertTriangle className="h-3.5 w-3.5 text-amber-700" />
        <span className="text-sm font-semibold text-amber-900">
          {payload.error_code}
        </span>
      </div>
      <p className="text-xs text-amber-900 whitespace-pre-wrap break-words">
        {payload.message}
      </p>
      {payload.hint && (
        <div className="rounded border border-amber-200/80 bg-background/70 px-3 py-2 text-xs text-amber-900/90">
          <span className="font-medium">建议：</span>
          {payload.hint}
        </div>
      )}
      {payload.context && Object.keys(payload.context).length > 0 && (
        <details className="text-xs">
          <summary className="cursor-pointer text-amber-700 hover:text-amber-900">
            查看错误上下文
          </summary>
          <JsonFallback value={payload.context} />
        </details>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------- //
// OutlineRenderer
// ---------------------------------------------------------------------- //

function OutlineRenderer({
  data,
  schema,
}: {
  data: OutlineOutput;
  schema: JsonSchema | null;
}) {
  const label = (path: string[], fallback?: string) =>
    fieldLabel(schema, path, fallback);

  return (
    <div className="space-y-4">
      <StructuredShell
        title={data.title || label([], '剧情大纲')}
        subtitle={`outline · ${data.acts?.length ?? 0} 幕`}
      >
        {data.logline && (
          <Field label={label(['logline'], 'logline')}>
            <p className="italic">"{data.logline}"</p>
          </Field>
        )}
        {data.synopsis && (
          <Field label={label(['synopsis'], 'synopsis')}>
            <p className="text-sm leading-6 whitespace-pre-wrap break-words">
              {data.synopsis}
            </p>
          </Field>
        )}
        {data.themes && data.themes.length > 0 && (
          <Field label={label(['themes'], 'themes')}>
            <div className="flex flex-wrap gap-1.5">
              {data.themes.map((t, i) => (
                <Badge key={i} variant="secondary" className="text-xs">
                  {t}
                </Badge>
              ))}
            </div>
          </Field>
        )}
      </StructuredShell>

      {data.characters && data.characters.length > 0 && (
        <div className="space-y-2">
          <SectionHeading>{label(['characters'], '角色')}</SectionHeading>
          <div className="grid gap-2 md:grid-cols-2">
            {data.characters.map((c, i) => (
              <div
                key={`${c.name}-${i}`}
                className="rounded-md border border-border/60 bg-background/80 px-3 py-2"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-foreground">
                    {c.name}
                  </span>
                  <Badge variant="outline" className="text-[10px]">
                    {c.role}
                  </Badge>
                </div>
                <div className="mt-1.5 space-y-1 text-xs text-muted-foreground">
                  {c.want && (
                    <p>
                      <span className="text-foreground">
                        {label(['characters', 'want'], 'want')}：
                      </span>
                      {c.want}
                    </p>
                  )}
                  {c.need && (
                    <p>
                      <span className="text-foreground">
                        {label(['characters', 'need'], 'need')}：
                      </span>
                      {c.need}
                    </p>
                  )}
                  {c.arc_summary && (
                    <p>
                      <span className="text-foreground">
                        {label(['characters', 'arc_summary'], 'arc')}：
                      </span>
                      {c.arc_summary}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.acts && data.acts.length > 0 && (
        <div className="space-y-2">
          <SectionHeading>{label(['acts'], '三幕')}</SectionHeading>
          <div className="space-y-2">
            {data.acts.map((act) => (
              <div
                key={act.act_number}
                className="rounded-md border border-border/60 bg-background/80 px-3 py-2.5"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className="text-[10px]">
                    {label(['acts', 'act_number'], 'Act')} {act.act_number}
                  </Badge>
                  <span className="text-sm font-semibold">{act.title}</span>
                </div>
                {act.goal && (
                  <p className="mt-1.5 text-xs text-muted-foreground">
                    <span className="text-foreground">
                      {label(['acts', 'goal'], 'goal')}：
                    </span>
                    {act.goal}
                  </p>
                )}
                {act.key_events && act.key_events.length > 0 && (
                  <ul className="mt-1.5 list-disc space-y-0.5 pl-5 text-xs text-muted-foreground">
                    {act.key_events.map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                )}
                {act.turning_point && (
                  <p className="mt-1.5 text-xs text-muted-foreground">
                    <span className="text-foreground">
                      {label(['acts', 'turning_point'], 'turning_point')}：
                    </span>
                    {act.turning_point}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {data.beats && data.beats.length > 0 && (
        <div className="space-y-2">
          <SectionHeading>{label(['beats'], '节拍')}</SectionHeading>
          <div className="space-y-1.5">
            {data.beats.map((b, i) => (
              <div
                key={`${b.beat_name}-${i}`}
                className="rounded border border-border/50 bg-background/60 px-3 py-1.5 text-xs"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className="text-[10px]">
                    {label(['beats', 'act_ref'], 'Act')} {b.act_ref}
                  </Badge>
                  <span className="font-semibold">{b.beat_name}</span>
                </div>
                {b.description && (
                  <p className="mt-0.5 text-muted-foreground">
                    {b.description}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------- //
// ScriptRenderer
// ---------------------------------------------------------------------- //

function ScriptRenderer({
  data,
  schema,
}: {
  data: ScriptOutput;
  schema: JsonSchema | null;
}) {
  const label = (path: string[], fallback?: string) =>
    fieldLabel(schema, path, fallback);

  return (
    <div className="space-y-4">
      <StructuredShell
        title={data.title || label([], '剧本')}
        subtitle={`script · ${data.scenes?.length ?? 0} 场`}
      >
        {data.based_on_outline && (
          <Field label={label(['based_on_outline'], 'based_on_outline')}>
            <p className="text-xs">{data.based_on_outline}</p>
          </Field>
        )}
      </StructuredShell>

      {data.scenes && data.scenes.length > 0 && (
        <div className="space-y-2">
          <SectionHeading>{label(['scenes'], '场景序列')}</SectionHeading>
          <div className="space-y-3">
            {data.scenes.map((scene, idx) => (
              <SceneCard
                key={`${scene.scene_number}-${idx}`}
                scene={scene}
                schema={schema}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SceneCard({
  scene,
  schema,
}: {
  scene: Scene;
  schema: JsonSchema | null;
}) {
  const label = (path: string[], fallback?: string) =>
    fieldLabel(schema, path, fallback);

  return (
    <div className="rounded-md border border-border/60 bg-background/80 px-3 py-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline" className="font-mono text-[10px]">
          #{scene.scene_number}
        </Badge>
        <span className="text-sm font-semibold font-mono">
          {scene.heading || `${scene.space}. ${scene.location} - ${scene.time_of_day}`}
        </span>
        {scene.duration_estimate_seconds != null && (
          <span className="text-[11px] text-muted-foreground">
            ~{scene.duration_estimate_seconds}s
          </span>
        )}
      </div>
      {scene.summary && (
        <p className="mt-1.5 text-xs text-muted-foreground">
          <span className="text-foreground">
            {label(['scenes', 'summary'], '本场目的')}：
          </span>
          {scene.summary}
        </p>
      )}
      {scene.emotional_beat && (
        <p className="mt-0.5 text-xs text-muted-foreground">
          <span className="text-foreground">
            {label(['scenes', 'emotional_beat'], '情绪节拍')}：
          </span>
          {scene.emotional_beat}
        </p>
      )}

      {(scene.actions?.length ?? 0) + (scene.dialogues?.length ?? 0) > 0 && (
        <div className="mt-2 space-y-2 rounded bg-muted/30 px-3 py-2">
          {scene.actions?.map((a, i) => (
            <p
              key={`act-${i}`}
              className="text-xs leading-6 text-foreground/90 whitespace-pre-wrap"
            >
              {a.description}
            </p>
          ))}
          {scene.dialogues?.map((d, i) => (
            <div key={`dlg-${i}`} className="text-xs leading-6">
              <p className="font-semibold uppercase tracking-wider text-foreground">
                {d.character}
                {d.parenthetical && (
                  <span className="ml-2 font-normal italic text-muted-foreground normal-case tracking-normal">
                    ({d.parenthetical})
                  </span>
                )}
              </p>
              <p className="text-foreground/90 whitespace-pre-wrap break-words">
                {d.line}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------- //
// StoryboardRenderer
// ---------------------------------------------------------------------- //

function StoryboardRenderer({
  data,
  schema,
}: {
  data: StoryboardOutput;
  schema: JsonSchema | null;
}) {
  const label = (path: string[], fallback?: string) =>
    fieldLabel(schema, path, fallback);

  return (
    <div className="space-y-4">
      <StructuredShell
        title={data.title || label([], '分镜')}
        subtitle={`storyboard · ${data.shots?.length ?? 0} 镜`}
      >
        {data.based_on_script && (
          <Field label={label(['based_on_script'], 'based_on_script')}>
            <p className="text-xs">{data.based_on_script}</p>
          </Field>
        )}
      </StructuredShell>

      {data.shots && data.shots.length > 0 && (
        <div className="space-y-2">
          <SectionHeading>{label(['shots'], '镜头序列')}</SectionHeading>
          <div className="space-y-2">
            {data.shots.map((shot, i) => (
              <ShotCard
                key={`${shot.shot_number}-${i}`}
                shot={shot}
                schema={schema}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ShotCard({
  shot,
  schema,
}: {
  shot: Shot;
  schema: JsonSchema | null;
}) {
  const label = (path: string[], fallback?: string) =>
    fieldLabel(schema, path, fallback);

  return (
    <div className="rounded-md border border-border/60 bg-background/80 px-3 py-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline" className="font-mono text-[10px]">
          {label(['shots', 'shot_number'], 'Shot')} {shot.shot_number}
        </Badge>
        <Badge variant="secondary" className="font-mono text-[10px]">
          {label(['shots', 'scene_number'], 'Scene')} {shot.scene_number}
        </Badge>
        <Badge variant="outline" className="text-[10px]">
          {shot.shot_size}
        </Badge>
        <Badge variant="outline" className="text-[10px]">
          {shot.camera_movement}
        </Badge>
        <Badge variant="outline" className="text-[10px]">
          {shot.camera_angle}
        </Badge>
        <span className="text-[11px] text-muted-foreground">
          {shot.duration_seconds}s
        </span>
      </div>
      {shot.composition_notes && (
        <p className="mt-1.5 text-xs text-muted-foreground">
          <span className="text-foreground">
            {label(['shots', 'composition_notes'], 'composition')}：
          </span>
          {shot.composition_notes}
        </p>
      )}
      {shot.visual_description && (
        <p className="mt-0.5 text-xs leading-5 text-foreground/90 whitespace-pre-wrap break-words">
          {shot.visual_description}
        </p>
      )}
      {(shot.audio_notes || shot.transition_to_next) && (
        <div className="mt-1.5 flex flex-wrap gap-3 text-[11px] text-muted-foreground">
          {shot.audio_notes && (
            <span>
              <span className="text-foreground">
                {label(['shots', 'audio_notes'], 'audio')}：
              </span>
              {shot.audio_notes}
            </span>
          )}
          {shot.transition_to_next && (
            <span>
              <span className="text-foreground">
                {label(['shots', 'transition_to_next'], 'transition')}：
              </span>
              {shot.transition_to_next}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
