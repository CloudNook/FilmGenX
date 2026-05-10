"""
``memory_save`` 工具——LLM 主动写入项目级 KV memory。

设计原则（FilmGenX 业务约定）：
- ``kind`` 是闭集：character / scene / style / preference / outline / script
- ``key`` 按 kind 不同有不同规则（详见 ``app/memory/taxonomy.py``）
- ``value`` 是结构化 dict，由 taxonomy 的 Pydantic schema 校验

确定性写入路径，不走 extractor。失败（kind/key/value 不合规）会把错误抛回给
LLM，让 LLM 看到 tool_result 后自行纠正。

业务定义在 ``app/memory/taxonomy.py``，框架不感知具体 kind / key。这个工具的
schema 也是按 taxonomy 动态构造，业务改 taxonomy 时无需改 framework。
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
            "Persist a structured KV entry into the project's long-term memory. "
            "All subsequent agents in this project will see it. "
            "kind / key / value must conform to the FilmGenX taxonomy:\n\n"
            + taxonomy_prompt_block()
            + "\n\nUSE ONLY when you have concrete information matching the taxonomy. "
              "Do NOT invent new kinds or keys. Tool returns an error you can read "
              "and correct from."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ALLOWED_KINDS,
                    "description": "Memory kind (taxonomy enum).",
                },
                "key": {
                    "type": "string",
                    "description": (
                        "Entity key. For 'character' / 'scene' use the canonical name. "
                        "For 'style' use one of palette/lighting/composition/mood/camera. "
                        "For 'preference' use one of genre/duration/pacing/format/structure. "
                        "For 'outline' / 'script' use 'main'."
                    ),
                },
                "value": {
                    "type": "object",
                    "description": (
                        "Structured value matching the kind's schema. See description "
                        "above for fields per kind."
                    ),
                },
                "confidence": {
                    "type": "number",
                    "description": "How sure you are (0-1). Default 1.0.",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 1.0,
                },
            },
            "required": ["kind", "key", "value"],
        },
    }


@register_tool(
    name="memory_save",
    description=(
        "Persist a structured KV entry (kind, key, value) into the project's "
        "long-term memory. Schema is enforced by the FilmGenX taxonomy."
    ),
)
async def memory_save_handler(
    kind: str,
    key: str,
    value: dict[str, Any],
    confidence: float = 1.0,
    *,
    memory_harness: Optional[Any] = None,
) -> dict[str, Any]:
    """工具处理器。``memory_harness`` 由 Agent 通过 ``ToolExecutor.extra_kwargs`` 注入。"""
    if memory_harness is None:
        return {
            "ok": False,
            "error": "memory not configured for this agent",
        }

    try:
        new_id = await memory_harness.set_kv(
            kind=kind,
            key=key,
            value=value,
            confidence=confidence,
            extra_metadata={"source": "memory_save_tool"},
        )
    except ValueError as exc:
        # taxonomy 校验失败 —— 把详细错误抛回 LLM，它能从 tool_result 里看到
        return {
            "ok": False,
            "error": f"invalid kind/key/value: {exc}",
        }
    except Exception as exc:  # pragma: no cover - 容灾
        return {
            "ok": False,
            "error": f"unexpected memory error: {type(exc).__name__}: {exc}",
        }

    if new_id is None:
        return {
            "ok": False,
            "error": "memory provider does not support set_kv",
        }

    return {
        "ok": True,
        "id": new_id,
        "kind": kind,
        "key": key,
    }
