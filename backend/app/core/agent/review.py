"""Review harness for Agent candidate outputs.

ReviewHarness 只负责把 reviewer 嵌入 AgentLoop 的候选评审控制点：
- 触发评审、累计 review_history、构造 synthetic feedback、发出 ReviewStart/EndEvent、持久化评审记录。
- 不再自己起 reviewer Agent；reviewer 必须由调用方显式构造（推荐 `create_reviewer_agent`）并通过
  `create_agent(..., reviewer=...)` 注入。
- 重试与耗尽控制（max_revision_rounds / on_exhausted / min_score）从 reviewer 上读取，
  reviewer 不携带这些字段时使用 ReviewerAgent 的默认值。
"""

from __future__ import annotations

from dataclasses import dataclass
import inspect
from typing import Any, List, Optional

from app.core.agent.base import (
    AgentConfig,
    AgentResult,
    ReviewEndEvent,
    ReviewError,
    Reviewer,
    ReviewRequest,
    ReviewResult,
    ReviewStartEvent,
)
from app.core.agent.persist.base import PersistStrategy


# Reviewer 未提供 loop 配置时的回落默认值。
# 与 ReviewerAgent 的字段默认保持同步，避免出现两套默认值。
_DEFAULT_MAX_REVISION_ROUNDS = 1
_DEFAULT_ON_EXHAUSTED = "fail"
_DEFAULT_MIN_SCORE = 8.0


@dataclass(frozen=True)
class ReviewFeedbackMessage:
    """Synthetic user message produced when review fails."""

    content: str
    metadata: dict[str, Any]


@dataclass
class ReviewOutcome:
    """Result of running review_candidate, including events and the review result."""

    review: Optional[ReviewResult]
    events: List[Any]


class ReviewHarness:
    """Owns candidate review and feedback construction for an AgentLoop."""

    def __init__(
        self,
        *,
        config: AgentConfig,
        session_id: str,
        request_id: str,
        persist: Optional[PersistStrategy],
        reviewer: Optional[Reviewer] = None,
    ) -> None:
        self.config = config
        self.session_id = session_id
        self.request_id = request_id
        self.persist = persist
        self.reviewer = reviewer

    # ------------------------------------------------------------------
    # Reviewer-driven configuration
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self.reviewer is not None

    @property
    def max_revision_rounds(self) -> int:
        return int(
            getattr(self.reviewer, "max_revision_rounds", _DEFAULT_MAX_REVISION_ROUNDS)
        )

    @property
    def on_exhausted(self) -> str:
        return str(getattr(self.reviewer, "on_exhausted", _DEFAULT_ON_EXHAUSTED))

    @property
    def min_score(self) -> float:
        return float(getattr(self.reviewer, "min_score", _DEFAULT_MIN_SCORE))

    def can_revise(self, result: AgentResult) -> bool:
        if self.reviewer is None:
            return False
        failed_reviews = sum(1 for review in result.review_history if not review.passed)
        return failed_reviews <= self.max_revision_rounds

    # ------------------------------------------------------------------
    # Review lifecycle
    # ------------------------------------------------------------------

    async def review_candidate(
        self,
        *,
        candidate_output: str,
        result: AgentResult,
        ctx: Optional[Any],
        messages: list[dict[str, Any]],
        loop_count: int,
        candidate_seq: int = 0,
    ) -> ReviewOutcome:
        if not self.enabled:
            return ReviewOutcome(review=None, events=[])

        review_round = len(result.review_history) + 1
        events: List[Any] = []

        events.append(
            ReviewStartEvent(
                agent_name=self.config.agent_name,
                session_id=self.session_id,
                request_id=self.request_id,
                review_round=review_round,
                loop_count=loop_count,
                candidate_preview=(candidate_output or "")[:200],
            )
        )

        request = ReviewRequest(
            agent_name=self.config.agent_name,
            session_id=self.session_id,
            request_id=self.request_id,
            user_input=self._resolve_user_input(ctx, messages),
            candidate_output=candidate_output,
            loop_count=loop_count,
            review_round=review_round,
            criteria=list(getattr(self.reviewer, "criteria", []) or []),
        )

        review_value = self.reviewer(request)
        if inspect.isawaitable(review_value):
            review_value = await review_value
        review_result = self._coerce_review_result(review_value)

        if review_result.score < self.min_score:
            review_result.passed = False
        result.review_history.append(review_result)

        will_revise = (not review_result.passed) and self.can_revise(result)
        exhausted = (not review_result.passed) and not will_revise

        events.append(
            ReviewEndEvent(
                agent_name=self.config.agent_name,
                session_id=self.session_id,
                request_id=self.request_id,
                review_round=review_round,
                loop_count=loop_count,
                review=review_result,
                will_revise=will_revise,
                exhausted=exhausted,
            )
        )

        await self._persist_review_record(
            review=review_result,
            review_round=review_round,
            loop_count=loop_count,
            candidate_seq=candidate_seq,
        )

        return ReviewOutcome(review=review_result, events=events)

    def build_feedback_message(self, review: ReviewResult) -> ReviewFeedbackMessage:
        suggestions = (
            "\n".join(f"- {item}" for item in review.suggestions)
            or "- 请根据反馈修订上一版输出"
        )
        content = (
            "[REVIEW_FAILED]\n\n"
            "你的上一版输出未通过 Review Agent 审核。\n\n"
            f"评分: {review.score}/10\n"
            f"反馈: {review.feedback or '未提供'}\n\n"
            "修订建议:\n"
            f"{suggestions}\n\n"
            "请重新思考并修订上一版输出。必要时可以继续调用工具。"
        )
        return ReviewFeedbackMessage(
            content=content,
            metadata={
                "synthetic": True,
                "source": "reviewer",
                "event_type": "review_feedback",
                "score": review.score,
                "passed": review.passed,
            },
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_user_input(
        self,
        ctx: Optional[Any],
        messages: list[dict[str, Any]],
    ) -> str:
        user_input = getattr(ctx, "initial_input", "") if ctx is not None else ""
        if user_input:
            return str(user_input)

        for message in messages:
            if message.get("role") == "user":
                return str(message.get("content") or "")
        return ""

    @staticmethod
    def _coerce_review_result(value: Any) -> ReviewResult:
        if isinstance(value, ReviewResult):
            return value
        if isinstance(value, dict):
            try:
                return ReviewResult(**value)
            except Exception as exc:
                raise ReviewError(
                    "Reviewer must return ReviewResult or dict compatible with ReviewResult"
                ) from exc
        raise ReviewError(
            "Reviewer must return ReviewResult or dict compatible with ReviewResult"
        )

    async def _persist_review_record(
        self,
        *,
        review: ReviewResult,
        review_round: int,
        loop_count: int,
        candidate_seq: int,
    ) -> None:
        if self.persist is None:
            return
        await self.persist.append_review_record(
            session_id=self.session_id,
            request_id=self.request_id,
            agent_name=self.config.agent_name,
            review_round=review_round,
            loop_count=loop_count,
            candidate_seq=candidate_seq,
            review=review.model_dump(),
        )
