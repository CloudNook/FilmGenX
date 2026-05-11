"""
``memory_save`` 工具——supervisor agent 主动写项目级 memory。

**双字段并存设计**：一个工具同时暴露 KV 写入和向量写入两组字段，可单写、可同写。

- KV 字段（taxonomy 严格）：``kind`` / ``key`` / ``value``
  - 用于 character / scene / style / preference / outline / script
  - 写入 ``memory_profile`` 表，UPDATE-in-place（同 key 直接覆盖 value）
- 向量字段（free-form 语义召回）：``content`` / ``entry_kind``
  - 用于 decision / user_feedback / fact / episode_outcome / 任何不在 taxonomy 的事实
  - 写入 ``memory_entries`` 表，append-only，自动算 embedding

调用者根据需要传一组或两组字段：

- 只写 KV：传 ``kind`` + ``key`` + ``value``
- 只写向量：传 ``content``（``entry_kind`` 可选）
- 同时写两边：两组都传——一次工具调用产生两条记录

工具实例由 Agent 通过 ``ToolExecutor.extra_kwargs`` 注入 ``memory_harness``，本工具
通过 harness 调到 provider 完成实际写入。
"""

from __future__ import annotations

from typing import Any, Optional

from app.core.tools.registry import register_tool


def build_memory_save_tool_schema() -> dict[str, Any]:
    """构造 memory_save 的 LLM 工具 schema，taxonomy 注入到 description。"""
    # 延迟 import：framework 不应在 import 时依赖业务 taxonomy
    from app.memory.taxonomy import ALLOWED_KINDS, taxonomy_prompt_block

    return {
        "name": "memory_save",
        "description": (
            "Persist memory to the project. Two storage paths share one tool—you may "
            "write KV, write a free-form vector entry, or both in one call.\n\n"
            "## KV path (taxonomy-bound, exact recall)\n"
            "Pass ``kind`` + ``key`` + ``value``. UPSERT semantics—same key just "
            "updates the value. Used for character / scene / style / preference / "
            "outline / script.\n\n"
            + taxonomy_prompt_block()
            + "\n\n"
            "## Vector entry path (free-form, semantic recall later)\n"
            "Pass ``content`` (and optional ``entry_kind`` tag). Append-only; each "
            "call creates a new vector-indexed row. Use for things that don't fit "
            "the taxonomy: decisions you made and want to remember, user feedback, "
            "cross-session episode outcomes, foreshadowing notes.\n\n"
            "Suggested ``entry_kind`` tags: ``decision`` (大方向决策), "
            "``user_feedback`` (用户明确表达), ``fact`` (杂项客观事实), "
            "``episode_outcome`` (集级结尾态 / 伏笔)。也可自定义。\n\n"
            "## Examples\n"
            "- 只写 KV：``kind='character'``, ``key='萧炎'``, ``value={...}``\n"
            "- 只写向量：``content='用户希望 60s 短剧前 10s 必须建立悬念'``, ``entry_kind='user_feedback'``\n"
            "- 两个同时：调用一次写两条（同一事件想精确 KV 也想语义可召回）"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                # ---- KV path ----
                "kind": {
                    "type": "string",
                    "enum": ALLOWED_KINDS,
                    "description": (
                        "KV path: taxonomy enum. 必须和 key、value 一起传。"
                    ),
                },
                "key": {
                    "type": "string",
                    "description": (
                        "KV path: entity key. character/scene 用 canonical 名；"
                        "style/preference 用 enum；outline/script 用 'main'。"
                    ),
                },
                "value": {
                    "type": "object",
                    "description": (
                        "KV path: 结构化 value，必须符合该 kind 的 schema 必填字段。"
                    ),
                },
                # ---- Vector entry path ----
                "content": {
                    "type": "string",
                    "description": (
                        "Vector path: 自然语言内容。1-3 句话，可直接读、可被语义召回。"
                    ),
                },
                "entry_kind": {
                    "type": "string",
                    "description": (
                        "Vector path: free-form tag。建议 decision / user_feedback / "
                        "fact / episode_outcome。仅在传 content 时使用。"
                    ),
                },
                # ---- Shared ----
                "confidence": {
                    "type": "number",
                    "description": "How sure (0-1). Default 1.0.",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 1.0,
                },
            },
            # 不强制 required —— handler 会校验"至少一组完整"
            "required": [],
        },
    }


@register_tool(
    name="memory_save",
    description=(
        "Persist project memory. KV fields (kind/key/value) write taxonomy-bound "
        "exact KV; content/entry_kind write a free-form vector entry. Pass either "
        "or both."
    ),
)
async def memory_save_handler(
    kind: Optional[str] = None,
    key: Optional[str] = None,
    value: Optional[dict[str, Any]] = None,
    content: Optional[str] = None,
    entry_kind: Optional[str] = None,
    confidence: float = 1.0,
    *,
    memory_harness: Optional[Any] = None,
) -> dict[str, Any]:
    """工具处理器。``memory_harness`` 由 Agent 通过 ``ToolExecutor.extra_kwargs`` 注入。

    至少要走一条路径（KV 或 vector entry）。返回结构里分别报告两边的写入结果，
    任意一边失败不影响另一边——caller 看到字段值就知道哪个成了哪个没成。
    """
    if memory_harness is None:
        return {
            "ok": False,
            "error": "memory not configured for this agent",
        }

    has_kv = (kind is not None) and (key is not None) and (value is not None)
    has_entry = bool(content)

    if not has_kv and not has_entry:
        return {
            "ok": False,
            "error": (
                "must provide either KV fields (kind+key+value), "
                "or a vector entry (content), or both"
            ),
        }

    result: dict[str, Any] = {"ok": True}

    # ---- KV ----
    if has_kv:
        try:
            kv_id = await memory_harness.set_kv(
                kind=kind,
                key=key,
                value=value,
                confidence=confidence,
                extra_metadata={"source": "memory_save_tool"},
            )
            result["kv_id"] = kv_id
        except ValueError as exc:
            from app.memory.taxonomy import KIND_REGISTRY

            schema_hint = ""
            spec = KIND_REGISTRY.get(kind)
            if spec is not None:
                required = [
                    f for f, info in spec.value_schema.model_fields.items()
                    if info.is_required()
                ]
                optional = [
                    f for f, info in spec.value_schema.model_fields.items()
                    if not info.is_required()
                ]
                schema_hint = (
                    f" | kind={kind!r} 的 value 必填字段: {required}"
                    + (f"，可选字段: {optional}" if optional else "")
                    + f"。你传的 value={value!r}，请补齐必填字段后用同样的 (kind, key) 重调。"
                )
            result["ok"] = False
            result["kv_error"] = f"invalid kind/key/value: {exc}{schema_hint}"
        except Exception as exc:  # pragma: no cover
            result["ok"] = False
            result["kv_error"] = f"unexpected kv write error: {type(exc).__name__}: {exc}"

    # ---- Vector entry ----
    if has_entry:
        try:
            entry_id = await memory_harness.add_entry(
                content=content,
                kind=entry_kind or "fact",
                confidence=confidence,
                extra_metadata={"source": "memory_save_tool"},
            )
            result["entry_id"] = entry_id
        except Exception as exc:  # pragma: no cover
            result["ok"] = False
            result["entry_error"] = (
                f"unexpected entry write error: {type(exc).__name__}: {exc}"
            )

    if not has_kv and not has_entry:
        result["ok"] = False
        result["error"] = "nothing was written"

    return result
