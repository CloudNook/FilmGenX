"""
MemoryHarness ——内部协调器。

把 ``MemoryConfig`` 编织到 AgentLoop / Agent 的实际调用点：
- ``recall(...)`` 由 AgentLoop 在 stream_run 主路径上**显式调用**
- ``write(...)`` 由 ``memory_save`` 工具 / fallback 兜底 / 业务直接注入
- ``format_recalled_for_prompt(...)`` 把召回结果格式化成 prompt 注入块
- ``tick_loop()`` AgentLoop 在 on_loop_end 调，返回 True 表示该触发兜底 compact

设计要点：
- recall 同步带 timeout；超时 / 异常 → 静默返回空（不阻塞主流）
- write 同步阻塞；失败抛异常给 caller。但 caller（AgentLoop on_loop_end /
  memory_save 工具）自己 try-except 防止主流被拖垮
- 不直接调用 LLM；extractor 是 caller-injected Protocol
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.agent.memory.config import MemoryConfig
from app.core.agent.memory.types import (
    CandidateMemory,
    FilterDecision,
    PostExtractionContext,
    PreExtractionContext,
    RecallQuery,
    ScoredMemory,
    ToolCallSummary,
    WriteOutcome,
    WriteTrigger,
)

logger = logging.getLogger(__name__)


class MemoryHarness:
    """每个 Agent 实例对应一个 harness。"""

    def __init__(
        self,
        config: MemoryConfig,
        *,
        agent_name: str,
        session_id: str,
    ) -> None:
        self.config = config
        self.agent_name = agent_name
        self.session_id = session_id
        self.session_started_at = datetime.now(timezone.utc)
        # 兜底 compact 触发计数器
        self._loops_since_compact = 0

    # ------------------------------------------------------------------ #
    # Recall：AgentLoop 显式调
    # ------------------------------------------------------------------ #

    async def recall(
        self,
        *,
        initial_input: str | None,
        recent_messages: list[dict[str, Any]] | None = None,
    ) -> list[ScoredMemory]:
        """召回 + 排序 + 阈值过滤 + topK。失败静默返回空。"""
        query = RecallQuery(
            agent_name=self.agent_name,
            session_id=self.session_id,
            initial_input=initial_input,
            recent_messages=recent_messages or [],
            metadata=dict(self.config.scope_metadata),
        )

        try:
            candidates = await asyncio.wait_for(
                self.config.provider.recall(query),
                timeout=self.config.recall_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "[memory:%s] recall timed out after %ss",
                self.agent_name,
                self.config.recall_timeout_seconds,
            )
            return []
        except Exception:
            logger.exception("[memory:%s] recall failed; skipping injection", self.agent_name)
            return []

        if not candidates:
            return []

        try:
            scored = await self.config.ranker.rank(candidates, query)
        except Exception:
            logger.exception("[memory:%s] rank failed; skipping injection", self.agent_name)
            return []

        kept = [s for s in scored if s.score >= self.config.recall_threshold]
        return kept[: self.config.recall_max_items]

    def format_recalled_for_prompt(self, scored: list[ScoredMemory]) -> str:
        """根据 ``inject_strategy`` 把召回结果格式化成 prompt 块。"""
        if not scored:
            return ""

        title = self.config.inject_section_title
        lines: list[str] = []
        if self.config.inject_strategy == "structured_block":
            lines.append(title)
            lines.append("")
            for s in scored:
                m = s.memory
                lines.append(f"- [{m.kind}] {m.content}")
            return "\n".join(lines)

        if self.config.inject_strategy == "system_message":
            # 紧凑版，给 system 角色读
            body = "\n".join(f"[{s.memory.kind}] {s.memory.content}" for s in scored)
            return f"{title}\n{body}"

        # user_preamble
        body = "\n".join(f"- [{s.memory.kind}] {s.memory.content}" for s in scored)
        return f"{title}\n{body}\n---"

    # ------------------------------------------------------------------ #
    # Write：三个触发路径的统一管道
    # ------------------------------------------------------------------ #

    async def write(
        self,
        *,
        messages: list[dict[str, Any]],
        trigger: WriteTrigger,
        loop_count: int = 0,
        tool_calls_made: list[ToolCallSummary] | None = None,
        user_id: str | None = None,
        explicit_kind: str | None = None,
        explicit_confidence: float | None = None,
    ) -> WriteOutcome:
        """raw messages → pre_filter → extract → post_filter → provider.write。

        ``explicit_kind`` / ``explicit_confidence`` 给 explicit_save 用：让 LLM
        指定的 kind / confidence 覆盖 extractor 的默认值。
        """
        now = datetime.now(timezone.utc)
        pre_ctx = PreExtractionContext(
            messages=messages,
            loop_count=loop_count,
            tool_calls_made=tool_calls_made or [],
            session_started_at=self.session_started_at,
            session_duration_seconds=(now - self.session_started_at).total_seconds(),
            session_id=self.session_id,
            agent_name=self.agent_name,
            user_id=user_id,
            scope_metadata=dict(self.config.scope_metadata),
            trigger=trigger,
        )

        pre_decision = await self.config.pre_extraction_filters.evaluate(pre_ctx)
        if not pre_decision.passed:
            logger.info(
                "[memory:%s] pre-extraction rejected trigger=%s score=%.2f rejected_by=%s",
                self.agent_name,
                trigger.value,
                pre_decision.aggregate_score,
                pre_decision.rejected_by,
            )
            return WriteOutcome(
                pre_decision=pre_decision,
                candidates_total=0,
                candidates_written=0,
            )

        try:
            candidates = await self.config.extractor.extract(
                messages,
                dict(self.config.scope_metadata),
            )
        except Exception:
            logger.exception("[memory:%s] extractor failed", self.agent_name)
            candidates = []

        # explicit_save 时让 LLM 给的 kind / confidence 接管
        if trigger == WriteTrigger.EXPLICIT_SAVE and candidates:
            for c in candidates:
                if explicit_kind is not None:
                    c.kind = explicit_kind
                if explicit_confidence is not None:
                    c.confidence = max(0.0, min(1.0, explicit_confidence))

        written_ids: list[str] = []
        post_decisions: list[FilterDecision] = []

        for candidate in candidates:
            post_ctx = PostExtractionContext(
                **pre_ctx.model_dump(),
                candidate=candidate,
            )
            post_decision = await self.config.post_extraction_filters.evaluate(post_ctx)
            post_decisions.append(post_decision)
            if not post_decision.passed:
                logger.info(
                    "[memory:%s] post-extraction rejected trigger=%s score=%.2f rejected_by=%s",
                    self.agent_name,
                    trigger.value,
                    post_decision.aggregate_score,
                    post_decision.rejected_by,
                )
                continue

            try:
                new_id = await self.config.provider.write(
                    candidate,
                    dict(self.config.scope_metadata),
                )
                written_ids.append(new_id)
                logger.info(
                    "[memory:%s] wrote id=%s kind=%s trigger=%s",
                    self.agent_name,
                    new_id,
                    candidate.kind,
                    trigger.value,
                )
            except Exception:
                logger.exception("[memory:%s] provider.write failed", self.agent_name)

        return WriteOutcome(
            pre_decision=pre_decision,
            candidates_total=len(candidates),
            candidates_written=len(written_ids),
            written_ids=written_ids,
            post_decisions=post_decisions,
        )

    # ------------------------------------------------------------------ #
    # 兜底 compact 触发器
    # ------------------------------------------------------------------ #

    def tick_loop(self) -> bool:
        """AgentLoop on_loop_end 调用一次。返回 True 表示该触发 fallback compact。"""
        self._loops_since_compact += 1
        if self._loops_since_compact >= self.config.fallback_compact_every_n_loops:
            self._loops_since_compact = 0
            return True
        return False

    def reset_compact_counter(self) -> None:
        """业务可显式 reset（比如刚做完 explicit_save 不想紧接着兜底）。"""
        self._loops_since_compact = 0

    @property
    def fallback_message_window(self) -> int:
        return self.config.fallback_compact_message_window
