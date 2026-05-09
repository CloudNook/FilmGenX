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
- **增量抽取**：write 入口先查 Provider 上次的 extract cursor，把 messages 截到
  "新增量"再喂给 extractor。极大节省 LLM 抽取成本，避免重复落库相似条目
"""

from __future__ import annotations

import asyncio
import hashlib
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
        """raw messages → cutoff by cursor → pre_filter → extract → post_filter → provider.write。

        ``explicit_kind`` / ``explicit_confidence`` 给 explicit_save 用：让 LLM
        指定的 kind / confidence 覆盖 extractor 的默认值。

        **增量抽取**：先从 Provider 查这个 (session_id, agent_name) 上次抽到的
        marker，把 ``messages`` 截到 marker 之后的新增量再走管道。如果上次没抽过、
        marker 失效（messages 里找不到），自动 fallback 到全量。explicit_save
        触发时不做截取（用户/LLM 主动指定要存什么，整个 messages 视为有意义）。
        """
        # 增量截取：explicit_save 不增量（caller 已经精确控制内容）；其它触发都按
        # cursor 截取，节省 extractor LLM 成本 + 防重复落库
        sliced_messages, marker_advances_to = await self._slice_unextracted(
            messages, trigger
        )

        now = datetime.now(timezone.utc)
        pre_ctx = PreExtractionContext(
            messages=sliced_messages,
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
                sliced_messages,
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

        # 跑 post_filter，分出"通过的候选"和"被砍的"
        passed_candidates: list[CandidateMemory] = []
        post_decisions: list[FilterDecision] = []
        for candidate in candidates:
            post_ctx = PostExtractionContext(
                **pre_ctx.model_dump(),
                candidate=candidate,
            )
            post_decision = await self.config.post_extraction_filters.evaluate(post_ctx)
            post_decisions.append(post_decision)
            if post_decision.passed:
                passed_candidates.append(candidate)
            else:
                logger.info(
                    "[memory:%s] post-extraction rejected trigger=%s score=%.2f rejected_by=%s",
                    self.agent_name,
                    trigger.value,
                    post_decision.aggregate_score,
                    post_decision.rejected_by,
                )

        # 原子提交：候选写入 + 推进游标在 provider 端单事务完成。
        # 即便 candidates 为空（extractor 返回空 / post filter 全砍），只要走完了
        # extractor（pre filter 通过），仍应推进 cursor —— 表示"这段对话已被评估，
        # 没有可记的内容"，下次不必重抽。
        # explicit_save 触发时 marker_advances_to=None，不动 cursor。
        written_ids: list[str] = []
        try:
            written_ids = await self.config.provider.commit_extraction(
                candidates=passed_candidates,
                scope_metadata=dict(self.config.scope_metadata),
                cursor_key=self._cursor_key() if marker_advances_to is not None else None,
                cursor_marker=marker_advances_to,
            )
        except Exception:
            logger.exception(
                "[memory:%s] commit_extraction failed (atomic); "
                "neither writes nor cursor advanced",
                self.agent_name,
            )

        if written_ids:
            logger.info(
                "[memory:%s] committed %d entrie(s) trigger=%s cursor=%s",
                self.agent_name,
                len(written_ids),
                trigger.value,
                marker_advances_to,
            )

        return WriteOutcome(
            pre_decision=pre_decision,
            candidates_total=len(candidates),
            candidates_written=len(written_ids),
            written_ids=written_ids,
            post_decisions=post_decisions,
        )

    # ------------------------------------------------------------------ #
    # 增量截取
    # ------------------------------------------------------------------ #

    async def _slice_unextracted(
        self,
        messages: list[dict[str, Any]],
        trigger: WriteTrigger,
    ) -> tuple[list[dict[str, Any]], Optional[str]]:
        """根据 Provider 的 cursor 把 messages 截到"未抽部分"。

        Returns:
            (sliced_messages, marker_advances_to)
            - sliced_messages：传给 extractor 的实际消息列表
            - marker_advances_to：写入成功后 cursor 应该推进到的 marker（None 表示不推进）
        """
        # explicit_save 触发时，caller 已经精确控制内容（一般就是 LLM 给的一句话），
        # 不应当 cursor 化处理 —— 直接全量进 extractor，且不动游标
        if trigger == WriteTrigger.EXPLICIT_SAVE:
            return messages, None

        if not messages:
            return messages, None

        try:
            last_marker = await self.config.provider.get_extract_cursor(
                self._cursor_key()
            )
        except Exception:
            logger.exception(
                "[memory:%s] get_extract_cursor failed; falling back to full messages",
                self.agent_name,
            )
            last_marker = None

        sliced = messages
        if last_marker:
            cutoff_idx = self._find_marker_index(messages, last_marker)
            if cutoff_idx is not None:
                sliced = messages[cutoff_idx + 1:]
                logger.info(
                    "[memory:%s] incremental: cursor=%s sliced %d -> %d messages",
                    self.agent_name,
                    last_marker,
                    len(messages),
                    len(sliced),
                )
            else:
                # marker 在当前 messages 列表里找不到（caller 可能传了截断的子序列）
                # → fallback 到全量；保守一点保证不丢内容
                logger.warning(
                    "[memory:%s] last cursor marker %s not found in current messages; "
                    "falling back to full extraction",
                    self.agent_name,
                    last_marker,
                )

        # 写入成功后 cursor 推到本次最后一条 message
        marker_advances_to = self._make_marker(messages[-1]) if messages else None
        return sliced, marker_advances_to

    def _cursor_key(self) -> str:
        """同一 (session_id, agent_name) 共享一个 cursor。"""
        return f"{self.session_id}:{self.agent_name}"

    @staticmethod
    def _make_marker(message: dict[str, Any]) -> str:
        """计算一条 message 的稳定 marker，用作增量抽取的"截止点"标识。

        优先级：
        1. ``message["seq"]`` 是整数 → ``"seq:<n>"``。AgentLoop 在 ``_load_history``
           等场景下从 DB 表 ``agent_messages.seq`` 还原历史时，**caller 应该把 seq
           回填到 dict**，让 marker 直接绑 DB 序号——稳定、唯一、可比较。
        2. 否则退回 ``"hash:<sha256(role+content)[:16]>"``。In-memory 新构造的
           message dict（system / user_input / assistant turn）通常没 seq 字段，
           只能基于内容做 hash。

        hash 路径的局限：
        - 如果某条历史消息的 content 被改写（比如 system prompt 调整、上下文 block
          注入到原有消息中），hash 变了，下次就找不到游标对应的 message → fallback
          到全量抽取（保守安全，但浪费 LLM 调用）。
        - 业务想避免这个 fallback，应在 _load_history / 持久化层把 seq 字段穿透到
          in-memory messages dict。

        framework 当前默认走 hash 路径——它对 caller 没要求，开箱即用；性能上
        最坏退化到"重抽过去内容"，不会丢数据。
        """
        if "seq" in message and isinstance(message["seq"], int):
            return f"seq:{message['seq']}"
        role = str(message.get("role", ""))
        content = str(message.get("content", ""))
        digest = hashlib.sha256(f"{role}|{content}".encode("utf-8")).hexdigest()
        return f"hash:{digest[:16]}"

    @classmethod
    def _find_marker_index(
        cls,
        messages: list[dict[str, Any]],
        marker: str,
    ) -> Optional[int]:
        """从尾向头找 marker 对应的 message 下标。找不到返回 None。"""
        for i in range(len(messages) - 1, -1, -1):
            if cls._make_marker(messages[i]) == marker:
                return i
        return None

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
