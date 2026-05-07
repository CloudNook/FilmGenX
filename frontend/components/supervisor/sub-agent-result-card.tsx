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
  result,
}: SubAgentResultCardProps) {
  if (result == null) return null;

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
            return <OutlineRenderer data={parsed as OutlineOutput} />;
          }
          break;
        case 'script_agent':
          if (looksLikeScript(parsed)) {
            return <ScriptRenderer data={parsed as ScriptOutput} />;
          }
          break;
        case 'storyboard_agent':
          if (looksLikeStoryboard(parsed)) {
            return <StoryboardRenderer data={parsed as StoryboardOutput} />;
          }
          break;
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

function OutlineRenderer({ data }: { data: OutlineOutput }) {
  return (
    <div className="space-y-4">
      <StructuredShell
        title={data.title || '剧情大纲'}
        subtitle={`outline · ${data.acts?.length ?? 0} 幕`}
      >
        {data.logline && (
          <Field label="logline">
            <p className="italic">"{data.logline}"</p>
          </Field>
        )}
        {data.synopsis && (
          <Field label="synopsis">
            <p className="text-sm leading-6 whitespace-pre-wrap break-words">
              {data.synopsis}
            </p>
          </Field>
        )}
        {data.themes && data.themes.length > 0 && (
          <Field label="themes">
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
          <SectionHeading>角色弧线</SectionHeading>
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
                      <span className="text-foreground">想要：</span>
                      {c.want}
                    </p>
                  )}
                  {c.need && (
                    <p>
                      <span className="text-foreground">需要：</span>
                      {c.need}
                    </p>
                  )}
                  {c.arc_summary && (
                    <p>
                      <span className="text-foreground">弧线：</span>
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
          <SectionHeading>三幕结构</SectionHeading>
          <div className="space-y-2">
            {data.acts.map((act) => (
              <div
                key={act.act_number}
                className="rounded-md border border-border/60 bg-background/80 px-3 py-2.5"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className="text-[10px]">
                    Act {act.act_number}
                  </Badge>
                  <span className="text-sm font-semibold">{act.title}</span>
                </div>
                {act.goal && (
                  <p className="mt-1.5 text-xs text-muted-foreground">
                    <span className="text-foreground">目标：</span>
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
                    <span className="text-foreground">转折点：</span>
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
          <SectionHeading>关键节拍</SectionHeading>
          <div className="space-y-1.5">
            {data.beats.map((b, i) => (
              <div
                key={`${b.beat_name}-${i}`}
                className="rounded border border-border/50 bg-background/60 px-3 py-1.5 text-xs"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className="text-[10px]">
                    Act {b.act_ref}
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

function ScriptRenderer({ data }: { data: ScriptOutput }) {
  return (
    <div className="space-y-4">
      <StructuredShell
        title={data.title || '剧本'}
        subtitle={`script · ${data.scenes?.length ?? 0} 场`}
      >
        {data.based_on_outline && (
          <Field label="based on">
            <p className="text-xs">{data.based_on_outline}</p>
          </Field>
        )}
      </StructuredShell>

      {data.scenes && data.scenes.length > 0 && (
        <div className="space-y-2">
          <SectionHeading>场景序列</SectionHeading>
          <div className="space-y-3">
            {data.scenes.map((scene, idx) => (
              <SceneCard key={`${scene.scene_number}-${idx}`} scene={scene} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SceneCard({ scene }: { scene: Scene }) {
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
          <span className="text-foreground">本场目的：</span>
          {scene.summary}
        </p>
      )}
      {scene.emotional_beat && (
        <p className="mt-0.5 text-xs text-muted-foreground">
          <span className="text-foreground">情绪节拍：</span>
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

function StoryboardRenderer({ data }: { data: StoryboardOutput }) {
  return (
    <div className="space-y-4">
      <StructuredShell
        title={data.title || '分镜'}
        subtitle={`storyboard · ${data.shots?.length ?? 0} 镜`}
      >
        {data.based_on_script && (
          <Field label="based on">
            <p className="text-xs">{data.based_on_script}</p>
          </Field>
        )}
      </StructuredShell>

      {data.shots && data.shots.length > 0 && (
        <div className="space-y-2">
          <SectionHeading>镜头序列</SectionHeading>
          <div className="space-y-2">
            {data.shots.map((shot, i) => (
              <ShotCard key={`${shot.shot_number}-${i}`} shot={shot} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ShotCard({ shot }: { shot: Shot }) {
  return (
    <div className="rounded-md border border-border/60 bg-background/80 px-3 py-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline" className="font-mono text-[10px]">
          Shot {shot.shot_number}
        </Badge>
        <Badge variant="secondary" className="font-mono text-[10px]">
          Scene {shot.scene_number}
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
          <span className="text-foreground">构图：</span>
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
              <span className="text-foreground">音：</span>
              {shot.audio_notes}
            </span>
          )}
          {shot.transition_to_next && (
            <span>
              <span className="text-foreground">转场：</span>
              {shot.transition_to_next}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
