'use client';

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from 'react';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import {
  skillsApi,
  type SkillMetaResponse,
  type SkillReferenceItem,
} from '@/lib/api';

/**
 * 带 @ 触发自动补全的 textarea。
 *
 * 输入 ``@`` 后弹出下拉框，列出可插入的 token：
 * - ``@ref:<key>`` —— 当前 skill 的 references
 * - ``@skill:<name>`` —— 其它 active skill
 * - ``@skill:<name>#<key>`` —— 选中某个 skill 后会按需 fetch 它的 references 并展开
 *
 * 触发要求：``@`` 必须出现在行首或紧跟空白字符之后，避免误识别"@everyone"等正常文本。
 * 已经插入的 token 再次定位光标也会触发补全（方便替换）；不想要补全可以 Esc 或点外面。
 */

type CandidateKind = 'self_ref' | 'skill' | 'skill_ref';

interface Candidate {
  kind: CandidateKind;
  token: string;
  label: string;
  hint?: string;
}

export interface MentionTextareaHandle {
  focus: () => void;
  insertToken: (token: string) => void;
}

interface MentionTextareaProps {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  rows?: number;
  className?: string;
  /** 当前 skill 自身的 references（用于 @ref 补全） */
  selfReferences: SkillReferenceItem[];
  /** 当前所有 active skill 元信息（用于 @skill 补全） */
  allSkills: SkillMetaResponse[];
  /** 当前 skill 的 name；从 @skill 列表里排除自己 */
  currentSkillName?: string;
}

const VALID_QUERY = /^[a-zA-Z0-9:_#-]*$/;

export const MentionTextarea = forwardRef<MentionTextareaHandle, MentionTextareaProps>(
  function MentionTextarea(
    {
      value,
      onChange,
      placeholder,
      rows = 6,
      className,
      selfReferences,
      allSkills,
      currentSkillName,
    },
    ref,
  ) {
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const [mention, setMention] = useState<{
      triggerStart: number;
      query: string;
      selectedIndex: number;
    } | null>(null);
    // 跨 skill #ref 补全：选中某个 skill 后按需 fetch 它的 references 并缓存
    const [crossRefCache, setCrossRefCache] = useState<
      Record<string, SkillReferenceItem[]>
    >({});
    const fetchingRef = useRef<Set<string>>(new Set());

    useImperativeHandle(ref, () => ({
      focus: () => textareaRef.current?.focus(),
      insertToken: (token: string) => {
        const el = textareaRef.current;
        if (!el) {
          onChange(`${value}${value && !value.endsWith(' ') ? ' ' : ''}${token}`);
          return;
        }
        const start = el.selectionStart;
        const end = el.selectionEnd;
        const before = value.slice(0, start);
        const after = value.slice(end);
        const needsLeadingSpace =
          before.length > 0 && !/[\s]$/.test(before);
        const insert = (needsLeadingSpace ? ' ' : '') + token;
        const next = `${before}${insert}${after}`;
        onChange(next);
        requestAnimationFrame(() => {
          const pos = before.length + insert.length;
          el.focus();
          el.setSelectionRange(pos, pos);
        });
      },
    }));

    /** 从光标向左走，找到 ``@`` 触发点，返回 query 字符串。 */
    const detectMention = useCallback(() => {
      const el = textareaRef.current;
      if (!el) {
        setMention(null);
        return;
      }
      const cursor = el.selectionStart;
      const text = value;

      let i = cursor - 1;
      while (i >= 0) {
        const ch = text[i];
        if (ch === '@') {
          const before = i > 0 ? text[i - 1] : '';
          if (i === 0 || /\s/.test(before)) {
            const query = text.slice(i + 1, cursor);
            if (VALID_QUERY.test(query)) {
              setMention((prev) => ({
                triggerStart: i,
                query,
                selectedIndex:
                  prev && prev.triggerStart === i ? prev.selectedIndex : 0,
              }));
              return;
            }
          }
          break;
        }
        if (/\s/.test(ch)) break;
        i -= 1;
      }
      setMention(null);
    }, [value]);

    /** 当 query = "skill:foo#" 时，按需 fetch foo 的 references。 */
    useEffect(() => {
      if (!mention) return;
      const q = mention.query.toLowerCase();
      if (!q.startsWith('skill:')) return;
      const sub = q.slice(6);
      const hashIdx = sub.indexOf('#');
      if (hashIdx < 0) return;
      const skillName = sub.slice(0, hashIdx);
      if (!skillName) return;
      if (skillName in crossRefCache) return;
      if (fetchingRef.current.has(skillName)) return;
      fetchingRef.current.add(skillName);
      skillsApi
        .get(skillName)
        .then((skill) => {
          setCrossRefCache((prev) => ({
            ...prev,
            [skillName]: skill.references || [],
          }));
        })
        .catch(() => {
          // skill 不存在或获取失败：写入空数组避免反复重试
          setCrossRefCache((prev) => ({ ...prev, [skillName]: [] }));
        })
        .finally(() => {
          fetchingRef.current.delete(skillName);
        });
    }, [mention, crossRefCache]);

    const candidates: Candidate[] = useMemo(() => {
      if (!mention) return [];
      const q = mention.query.toLowerCase();
      const out: Candidate[] = [];

      if (q.startsWith('ref:')) {
        const sub = q.slice(4);
        for (const r of selfReferences) {
          if (r.key.toLowerCase().includes(sub)) {
            out.push({
              kind: 'self_ref',
              token: `@ref:${r.key}`,
              label: `@ref:${r.key}`,
              hint: r.title || '本 Skill 引用',
            });
          }
        }
      } else if (q.startsWith('skill:')) {
        const sub = q.slice(6);
        const hashIdx = sub.indexOf('#');
        if (hashIdx >= 0) {
          const skillName = sub.slice(0, hashIdx);
          const refQuery = sub.slice(hashIdx + 1);
          // 提供"不带子节"的快捷选项
          if (skillName) {
            out.push({
              kind: 'skill',
              token: `@skill:${skillName}`,
              label: `@skill:${skillName}`,
              hint: '引用整个 Skill（不带子节）',
            });
          }
          const cached = crossRefCache[skillName];
          if (cached) {
            for (const r of cached) {
              if (r.key.toLowerCase().includes(refQuery)) {
                out.push({
                  kind: 'skill_ref',
                  token: `@skill:${skillName}#${r.key}`,
                  label: `@skill:${skillName}#${r.key}`,
                  hint: r.title || `${skillName} 的 reference`,
                });
              }
            }
          } else {
            out.push({
              kind: 'skill_ref',
              token: '',
              label: '加载子节...',
              hint: '',
            });
          }
        } else {
          for (const s of allSkills) {
            if (s.name === currentSkillName) continue;
            if (!sub || s.name.toLowerCase().includes(sub)) {
              out.push({
                kind: 'skill',
                token: `@skill:${s.name}`,
                label: `@skill:${s.name}`,
                hint: s.description.slice(0, 80),
              });
            }
          }
        }
      } else {
        // 没有前缀：混合展示，self_ref 优先
        for (const r of selfReferences) {
          if (!q || r.key.toLowerCase().includes(q)) {
            out.push({
              kind: 'self_ref',
              token: `@ref:${r.key}`,
              label: `@ref:${r.key}`,
              hint: r.title || '本 Skill 引用',
            });
          }
        }
        for (const s of allSkills) {
          if (s.name === currentSkillName) continue;
          if (!q || s.name.toLowerCase().includes(q)) {
            out.push({
              kind: 'skill',
              token: `@skill:${s.name}`,
              label: `@skill:${s.name}`,
              hint: s.description.slice(0, 80),
            });
          }
        }
      }

      return out.slice(0, 12);
    }, [mention, selfReferences, allSkills, currentSkillName, crossRefCache]);

    /** candidates 变化后保证 selectedIndex 不越界 */
    useEffect(() => {
      if (mention && mention.selectedIndex >= candidates.length) {
        setMention((prev) =>
          prev ? { ...prev, selectedIndex: 0 } : null,
        );
      }
    }, [candidates.length, mention]);

    const applyCandidate = useCallback(
      (candidate: Candidate) => {
        if (!candidate.token) return; // "加载中" 占位项不可选
        const el = textareaRef.current;
        if (!el || !mention) return;
        const cursor = el.selectionStart;
        const before = value.slice(0, mention.triggerStart);
        const after = value.slice(cursor);
        const next = `${before}${candidate.token}${after}`;
        onChange(next);
        setMention(null);
        requestAnimationFrame(() => {
          const pos = before.length + candidate.token.length;
          el.focus();
          el.setSelectionRange(pos, pos);
        });
      },
      [mention, value, onChange],
    );

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (!mention || candidates.length === 0) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setMention({
          ...mention,
          selectedIndex: (mention.selectedIndex + 1) % candidates.length,
        });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setMention({
          ...mention,
          selectedIndex:
            (mention.selectedIndex - 1 + candidates.length) % candidates.length,
        });
      } else if (e.key === 'Enter' || e.key === 'Tab') {
        const c = candidates[mention.selectedIndex];
        if (c?.token) {
          e.preventDefault();
          applyCandidate(c);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        setMention(null);
      }
    };

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onChange(e.target.value);
      requestAnimationFrame(detectMention);
    };

    return (
      <div className="relative">
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onClick={() => requestAnimationFrame(detectMention)}
          onSelect={() => requestAnimationFrame(detectMention)}
          onBlur={() => {
            // 给 dropdown 的 onMouseDown 留时间触发后再关闭
            setTimeout(() => setMention(null), 150);
          }}
          placeholder={placeholder}
          rows={rows}
          className={cn('font-mono text-sm', className)}
        />
        {mention && candidates.length > 0 && (
          <div className="absolute z-50 mt-1 left-0 right-0 max-h-72 overflow-auto rounded-lg border border-border/70 bg-popover shadow-lg">
            <div className="flex items-center justify-between border-b border-border/60 bg-muted/50 px-3 py-1.5 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              <span>{mention.query ? `匹配 "${mention.query}"` : 'Skill 引用'}</span>
              <span className="text-muted-foreground/70 normal-case tracking-normal">
                ↑↓ 选 · ↵/Tab 插入 · Esc 关
              </span>
            </div>
            {candidates.map((c, i) => (
              <button
                key={`${c.token}-${i}`}
                type="button"
                disabled={!c.token}
                onMouseDown={(e) => {
                  // 阻止默认 focus 转移，让 onClick 之前 textarea 别先 blur
                  e.preventDefault();
                  applyCandidate(c);
                }}
                className={cn(
                  'block w-full px-3 py-2 text-left text-sm transition-colors',
                  i === mention.selectedIndex
                    ? 'bg-primary/10 text-primary'
                    : 'hover:bg-muted',
                  !c.token && 'cursor-not-allowed opacity-60',
                )}
              >
                <div className="font-mono">{c.label}</div>
                {c.hint && (
                  <div className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                    {c.hint}
                  </div>
                )}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  },
);
