"""
``memory_save`` 工具——LLM 主动调它把当前对话中的事实 / 偏好 / 决策固化到长期 memory。

工具走的是和 fallback_compact / user_correction 完全相同的 ``MemoryHarness.write``
管道：raw → pre_filter → extract → post_filter → provider.write。Filter 链能拦下
噪音；LLM 调了不一定真落库。

工具实例不直接走 ToolRegistry 的 @register_tool（那是全局注册），而是由 Agent
在 ``_init_tool_executor`` 时注入 ``memory_harness`` 到 ``ToolExecutor.extra_kwargs``，
让本工具 await harness.write() 即可。
"""

from __future__ import annotations

from typing import Any, Optional

from app.core.agent.memory.types import WriteOutcome, WriteTrigger
from app.core.tools.registry import register_tool


def build_memory_save_tool_schema() -> dict[str, Any]:
    """供 AgentConfig.tools 注入的 OpenAI/Gemini 兼容 tool schema。"""
    return {
        "name": "memory_save",
        "description": (
            "Persist a fact / preference / decision from the current conversation "
            "into long-term memory. Use sparingly: only for information worth "
            "remembering across sessions. Provide content as one or more concise "
            "sentences; the framework's filter chain may still drop low-quality "
            "candidates."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Concise summary of what to remember.",
                },
                "kind": {
                    "type": "string",
                    "description": (
                        "Type of memory (e.g. preference, fact, decision). "
                        "Free-form, business-defined."
                    ),
                    "default": "fact",
                },
                "confidence": {
                    "type": "number",
                    "description": "How sure you are (0-1). Default 1.0.",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 1.0,
                },
            },
            "required": ["content"],
        },
    }


@register_tool(
    name="memory_save",
    description=(
        "Persist a fact / preference / decision from the current conversation "
        "into long-term memory. Use sparingly—only for information worth "
        "remembering across sessions. The framework's filter chain may still "
        "drop low-quality candidates; check the returned ``ok`` field."
    ),
)
async def memory_save_handler(
    content: str,
    kind: str = "fact",
    confidence: float = 1.0,
    *,
    memory_harness: Optional[Any] = None,
    loop_count: int = 0,
) -> dict[str, Any]:
    """工具处理器。``memory_harness`` 由 Agent 通过 ToolExecutor.extra_kwargs 注入。

    返回结构对 LLM 友好：``{ok, written_count, written_ids, rejected_reason?}``。
    """
    if memory_harness is None:
        return {
            "ok": False,
            "error": "memory not configured for this agent",
            "written_count": 0,
        }

    # 构造一条 user 消息作为 raw payload，让管道走完整流程
    fake_messages: list[dict[str, Any]] = [
        {"role": "user", "content": content, "metadata": {"kind": kind}}
    ]

    outcome: WriteOutcome = await memory_harness.write(
        messages=fake_messages,
        trigger=WriteTrigger.EXPLICIT_SAVE,
        loop_count=loop_count,
        explicit_kind=kind,
        explicit_confidence=confidence,
    )

    if outcome.candidates_written > 0:
        return {
            "ok": True,
            "written_count": outcome.candidates_written,
            "written_ids": outcome.written_ids,
        }

    rejected_reasons = []
    if not outcome.pre_decision.passed:
        rejected_reasons.append(
            f"pre-extraction filters rejected (score={outcome.pre_decision.aggregate_score:.2f})"
        )
    for d in outcome.post_decisions:
        if not d.passed:
            rejected_reasons.append(
                f"post-extraction rejected (score={d.aggregate_score:.2f}"
                + (f", by={d.rejected_by}" if d.rejected_by else "")
                + ")"
            )

    return {
        "ok": False,
        "written_count": 0,
        "rejected_reason": "; ".join(rejected_reasons) or "no candidates extracted",
    }
