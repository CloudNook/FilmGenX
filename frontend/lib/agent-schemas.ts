/**
 * Agent 输出 schema 客户端缓存。
 *
 * Backend ``GET /api/v1/agent-schemas`` 返回 ``{sub_agent_name: <JSON Schema>}``。
 * 这一层做：
 *  - 单例 promise 缓存（防多组件并发触发多次 fetch）
 *  - sessionStorage 持久化（页面刷新后秒返结果，跨标签页也能复用）
 *  - 字段元数据查找辅助函数：``getFieldTitle``、``resolveRef``
 *
 * 渲染器消费方式：先 ``ensureAgentSchemas()``，拿到字典后用 ``getFieldTitle(schema, ['characters', 'name'])``
 * 之类的访问字段标签——schema 里没找到时回退到 field key 原文。
 */

import { useEffect, useState } from 'react';

import { agentSchemasApi } from '@/lib/api';

export type JsonSchema = {
  type?: string;
  title?: string;
  description?: string;
  properties?: Record<string, JsonSchema>;
  items?: JsonSchema;
  required?: string[];
  enum?: unknown[];
  $ref?: string;
  anyOf?: JsonSchema[];
  $defs?: Record<string, JsonSchema>;
  // 允许任意扩展字段
  [k: string]: unknown;
};

export type AgentSchemasMap = Record<string, JsonSchema>;

const SESSION_STORAGE_KEY = 'filmgenx:agent-schemas:v1';

let inFlight: Promise<AgentSchemasMap> | null = null;
let memoryCache: AgentSchemasMap | null = null;

function readSessionCache(): AgentSchemasMap | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === 'object') return parsed as AgentSchemasMap;
  } catch {
    // ignore
  }
  return null;
}

function writeSessionCache(value: AgentSchemasMap) {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(value));
  } catch {
    // 限额或私密模式：忽略
  }
}

/**
 * 取所有 sub-agent 的输出 schema。多组件并发调用复用一份 promise 与
 * sessionStorage 缓存；页面级生命周期内只会真实 fetch 一次。
 */
export async function ensureAgentSchemas(): Promise<AgentSchemasMap> {
  if (memoryCache) return memoryCache;
  if (inFlight) return inFlight;

  const cached = readSessionCache();
  if (cached) {
    memoryCache = cached;
    return cached;
  }

  inFlight = agentSchemasApi
    .list()
    .then((map) => {
      const typed = map as AgentSchemasMap;
      memoryCache = typed;
      writeSessionCache(typed);
      return typed;
    })
    .catch((err) => {
      // fetch 失败时下次仍然可以重试
      inFlight = null;
      throw err;
    });

  return inFlight;
}

/** 同步访问：用于 useSyncExternalStore-free 的简单场景。已 ensure 过则可用。 */
export function getCachedAgentSchemas(): AgentSchemasMap | null {
  return memoryCache;
}

// -------------------------------------------------------------------- //
// 字段元数据辅助
// -------------------------------------------------------------------- //

/**
 * 解开 ``$ref`` 指向的子 schema。
 *
 * Pydantic 把嵌套类型放在 ``$defs`` 下，property 用 ``{"$ref": "#/$defs/Foo"}`` 引用。
 * 此函数假设 ref 形如 ``#/$defs/<name>``，最多解一层（不递归 ref-to-ref）。
 */
export function resolveRef(schema: JsonSchema, root: JsonSchema): JsonSchema {
  if (!schema.$ref || typeof schema.$ref !== 'string') return schema;
  const m = schema.$ref.match(/^#\/\$defs\/(.+)$/);
  if (!m) return schema;
  const name = m[1];
  const defs = root.$defs;
  if (!defs) return schema;
  return defs[name] || schema;
}

/**
 * 沿对象路径取出字段 schema。
 *
 * 例：``getFieldSchema(outlineSchema, ['characters'])`` 返回 characters 这个数组字段的 schema；
 * ``getFieldSchema(outlineSchema, ['characters', 'name'])`` 自动跳过数组的 ``items`` 拿到
 * CharacterArc.name 的 schema（先解开 ref）。
 *
 * 找不到返回 null。
 */
export function getFieldSchema(
  root: JsonSchema | undefined,
  path: string[],
): JsonSchema | null {
  if (!root) return null;
  let current: JsonSchema | null = root;
  for (const key of path) {
    if (!current) return null;
    let resolved = resolveRef(current, root);
    // 如果当前是 array，下一段路径属于其 items
    if (resolved.type === 'array' && resolved.items) {
      resolved = resolveRef(resolved.items, root);
    }
    const next = resolved.properties?.[key];
    if (!next) return null;
    current = next;
  }
  return current ? resolveRef(current, root) : null;
}

/** 拿字段 ``title``。找不到返回 null（让调用方决定 fallback）。 */
export function getFieldTitle(
  root: JsonSchema | undefined,
  path: string[],
): string | null {
  const s = getFieldSchema(root, path);
  if (!s) return null;
  return typeof s.title === 'string' && s.title.length > 0 ? s.title : null;
}

/** 拿字段 ``description``。找不到返回 null。 */
export function getFieldDescription(
  root: JsonSchema | undefined,
  path: string[],
): string | null {
  const s = getFieldSchema(root, path);
  if (!s) return null;
  return typeof s.description === 'string' && s.description.length > 0
    ? s.description
    : null;
}

// -------------------------------------------------------------------- //
// React hook
// -------------------------------------------------------------------- //

/**
 * 取指定 sub-agent 的输出 schema。
 *
 * - 首次调用时若内存未缓存则触发 fetch；多个组件并发挂载会复用同一个 promise
 * - 命中内存或 sessionStorage 时同步返回 schema（不闪空）
 * - fetch 失败时返回 null（renderer 走"无 schema 兜底用 field key 做 label"路径）
 */
export function useAgentSchema(name: string): JsonSchema | null {
  const [schema, setSchema] = useState<JsonSchema | null>(() => {
    if (memoryCache) return memoryCache[name] ?? null;
    const session = readSessionCache();
    if (session) {
      memoryCache = session;
      return session[name] ?? null;
    }
    return null;
  });

  useEffect(() => {
    let cancelled = false;
    ensureAgentSchemas()
      .then((map) => {
        if (cancelled) return;
        setSchema(map[name] ?? null);
      })
      .catch(() => {
        if (cancelled) return;
        setSchema(null);
      });
    return () => {
      cancelled = true;
    };
  }, [name]);

  return schema;
}
