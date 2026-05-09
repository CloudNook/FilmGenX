"""测试专用 fakes —— 全部 inline，不依赖框架内的具体实现（框架本身不提供）。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.agent.memory.types import (
    CandidateMemory,
    FilterScore,
    PostExtractionContext,
    PreExtractionContext,
    RecallQuery,
    RecalledMemory,
    ScoredMemory,
)


class FakeProvider:
    """dict 后端的最小 fake provider。"""

    def __init__(self) -> None:
        self.store: dict[str, dict[str, Any]] = {}
        self.recall_calls: list[RecallQuery] = []
        self.write_calls: list[CandidateMemory] = []

    async def recall(self, query: RecallQuery) -> list[RecalledMemory]:
        self.recall_calls.append(query)
        results: list[RecalledMemory] = []
        for entry in self.store.values():
            if not _scope_matches(entry["scope_metadata"], query.metadata):
                continue
            results.append(
                RecalledMemory(
                    id=entry["id"],
                    content=entry["content"],
                    kind=entry["kind"],
                    confidence=entry.get("confidence", 1.0),
                    created_at=entry.get("created_at"),
                )
            )
        return results

    async def write(
        self,
        candidate: CandidateMemory,
        scope_metadata: dict[str, Any],
    ) -> str:
        self.write_calls.append(candidate)
        new_id = str(uuid.uuid4())
        self.store[new_id] = {
            "id": new_id,
            "content": candidate.content,
            "kind": candidate.kind,
            "confidence": candidate.confidence,
            "created_at": datetime.now(timezone.utc),
            "scope_metadata": dict(scope_metadata),
        }
        return new_id


class FixedCandidatesExtractor:
    """返回预定的 candidates，不需要 LLM。"""

    def __init__(self, candidates: list[CandidateMemory]) -> None:
        self._candidates = candidates
        self.calls: list[list[dict[str, Any]]] = []

    async def extract(
        self,
        messages: list[dict[str, Any]],
        scope_metadata: dict[str, Any],
    ) -> list[CandidateMemory]:
        self.calls.append(list(messages))
        return [c.model_copy() for c in self._candidates]


class PassthroughRanker:
    """不做实际打分，每条直接 score=1.0。仅用于测试。"""

    async def rank(
        self,
        candidates: list[RecalledMemory],
        query: RecallQuery,
    ) -> list[ScoredMemory]:
        return [
            ScoredMemory(memory=c, score=1.0, breakdown={"fake": 1.0})
            for c in candidates
        ]


class ConstFilter:
    """返回固定 score 的 filter。"""

    def __init__(self, name: str, score: float) -> None:
        self.name = name
        self._score = score

    async def score(self, ctx) -> FilterScore:
        return FilterScore(score=self._score)


class RaisingFilter:
    """每次 score 都 raise，验证 chain 异常保护。"""

    name = "raises"

    async def score(self, ctx) -> FilterScore:
        raise RuntimeError("boom")


class MinLengthContentFilter:
    """业务侧 filter 示例：候选内容字符数少于阈值则丢。"""

    name = "min_length_content"

    def __init__(self, min_length: int = 5) -> None:
        self.min_length = min_length

    async def score(self, ctx) -> FilterScore:
        if isinstance(ctx, PostExtractionContext):
            content = ctx.candidate.content or ""
        else:
            content = "\n".join(str(m.get("content", "")) for m in ctx.messages)
        passed = len(content.strip()) >= self.min_length
        return FilterScore(score=1.0 if passed else 0.0)


def _scope_matches(entry_scope: dict[str, Any], query_scope: dict[str, Any]) -> bool:
    for k, v in query_scope.items():
        if entry_scope.get(k) != v:
            return False
    return True


def make_pre_ctx(messages, **kwargs) -> PreExtractionContext:
    """测试辅助：构造 PreExtractionContext。"""
    from app.core.agent.memory.types import WriteTrigger

    now = datetime.now(timezone.utc)
    return PreExtractionContext(
        messages=messages,
        loop_count=kwargs.get("loop_count", 0),
        tool_calls_made=[],
        session_started_at=now,
        session_duration_seconds=0.0,
        session_id="sess",
        agent_name="test_agent",
        scope_metadata={},
        trigger=kwargs.get("trigger", WriteTrigger.EXPLICIT_SAVE),
    )


def make_post_ctx(candidate: CandidateMemory, **kwargs) -> PostExtractionContext:
    base = make_pre_ctx(kwargs.get("messages", [{"role": "user", "content": "x"}]))
    return PostExtractionContext(**base.model_dump(), candidate=candidate)
