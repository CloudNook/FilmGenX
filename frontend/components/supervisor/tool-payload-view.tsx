'use client';

/**
 * 通用工具调用载荷渲染。
 *
 * 替代 supervisor 流里 ``<pre>{JSON.stringify(args, null, 2)}</pre>`` 的裸倾倒——
 * 这种倾倒在 args 包含"字符串字段值本身又是 JSON 字符串"的情况下（典型例子：
 * call_sub_agent 的 context_snapshot）会满屏 ``\"`` 转义，几乎不可读。
 *
 * 渲染规则：
 * - null / undefined / boolean / number → 单行 badge
 * - string 且看起来是 JSON（trim 后 ``{...}`` / ``[...]`` 且 parse 成功）→ 自动 unwrap，
 *   按解析后的值递归渲染（解开嵌套转义）
 * - string 单行短文本 → 单行 inline
 * - string 多行 / 长文本 → ``<pre>`` 块，保留换行
 * - array → 每项一行，前面带 ``[i]`` 索引，递归渲染 item
 * - object → 每个键值对一行，左列 mono key，右列递归渲染 value
 */

import type { ReactNode } from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface ToolPayloadViewProps {
  value: unknown;
  className?: string;
  /** 递归深度，防御循环引用（虽然 JSON 来源理论上不会循环） */
  depth?: number;
}

const MAX_DEPTH = 8;

function tryUnwrapJsonString(s: string): unknown | null {
  const trimmed = s.trim();
  const looksLikeJson =
    (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
    (trimmed.startsWith('[') && trimmed.endsWith(']'));
  if (!looksLikeJson) return null;
  try {
    return JSON.parse(trimmed);
  } catch {
    return null;
  }
}

function ScalarBadge({ children }: { children: ReactNode }) {
  return (
    <Badge variant="outline" className="font-mono text-[10px]">
      {children}
    </Badge>
  );
}

export function ToolPayloadView({
  value,
  className,
  depth = 0,
}: ToolPayloadViewProps) {
  if (depth > MAX_DEPTH) {
    return (
      <span className="text-xs text-muted-foreground">
        … (depth limit)
      </span>
    );
  }

  if (value === null) return <ScalarBadge>null</ScalarBadge>;
  if (value === undefined) return <ScalarBadge>undefined</ScalarBadge>;

  if (typeof value === 'boolean') {
    return <ScalarBadge>{String(value)}</ScalarBadge>;
  }
  if (typeof value === 'number') {
    return <ScalarBadge>{String(value)}</ScalarBadge>;
  }

  if (typeof value === 'string') {
    const unwrapped = tryUnwrapJsonString(value);
    if (unwrapped !== null && typeof unwrapped === 'object') {
      return (
        <div className={cn('space-y-1', className)}>
          <p className="text-[10px] text-muted-foreground italic">
            （从 JSON 字符串自动解析）
          </p>
          <ToolPayloadView value={unwrapped} depth={depth + 1} />
        </div>
      );
    }
    if (!value) {
      return (
        <span className="text-xs text-muted-foreground italic">
          (空字符串)
        </span>
      );
    }
    // 长 / 多行文本：用 pre，保留换行；不需要 mono（task_description 是中文叙述）
    if (value.length > 80 || value.includes('\n')) {
      return (
        <pre
          className={cn(
            'whitespace-pre-wrap break-words rounded bg-background/60 px-3 py-2 text-xs leading-6 text-foreground',
            className,
          )}
        >
          {value}
        </pre>
      );
    }
    return (
      <span className={cn('text-xs text-foreground break-words', className)}>
        {value}
      </span>
    );
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return (
        <span className="text-xs text-muted-foreground italic">
          (空数组)
        </span>
      );
    }
    return (
      <div className={cn('space-y-1', className)}>
        {value.map((item, i) => (
          <div key={i} className="flex gap-2">
            <span className="shrink-0 pt-0.5 font-mono text-[10px] text-muted-foreground">
              [{i}]
            </span>
            <div className="min-w-0 flex-1">
              <ToolPayloadView value={item} depth={depth + 1} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 0) {
      return (
        <span className="text-xs text-muted-foreground italic">
          (空对象)
        </span>
      );
    }
    return (
      <div className={cn('space-y-1.5', className)}>
        {entries.map(([k, v]) => (
          <div
            key={k}
            className="flex flex-col gap-0.5 sm:flex-row sm:items-start sm:gap-3"
          >
            <span className="shrink-0 pt-1 font-mono text-[11px] text-muted-foreground sm:w-32 sm:text-right">
              {k}
            </span>
            <div className="min-w-0 flex-1">
              <ToolPayloadView value={v} depth={depth + 1} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  // 兜底：其它类型 stringify
  return (
    <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded bg-background/60 px-3 py-2 text-xs text-muted-foreground">
      {String(value)}
    </pre>
  );
}
