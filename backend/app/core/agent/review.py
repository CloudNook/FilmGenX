"""Review harness for Agent candidate outputs."""

from __future__ import annotations

from dataclasses import dataclass
import inspect
import json
from typing import Any, Optional

from app.core.agent.base import (
    AgentConfig,
    AgentResult,
    ReviewError,
    Reviewer,
    ReviewRequest,
    ReviewResult,
)
from app.core.agent.persist.base import PersistStrategy


@dataclass(frozen=True)
class ReviewFeedbackMessage:
    """Synthetic user message produced when review fails."""

    content: str
    metadata: dict[str, Any]


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

    @property
    def enabled(self) -> bool:
        policy = self.config.review_policy
        return bool(policy and policy.enabled)

    def can_revise(self, result: AgentResult) -> bool:
        policy = self.config.review_policy
        if policy is None:
            return False
        failed_reviews = sum(1 for review in result.review_history if not review.passed)
        return failed_reviews <= policy.max_revision_rounds

    async def review_candidate(
        self,
        *,
        candidate_output: str,
        result: AgentResult,
        ctx: Optional[Any],
        messages: list[dict[str, Any]],
        loop_count: int,
    ) -> ReviewResult | None:
        if not self.enabled:
            return None

        policy = self.config.review_policy
        request = ReviewRequest(
            agent_name=self.config.agent_name,
            session_id=self.session_id,
            request_id=self.request_id,
            user_input=self._resolve_user_input(ctx, messages),
            candidate_output=candidate_output,
            loop_count=loop_count,
            review_round=len(result.review_history) + 1,
            criteria=list(policy.criteria if policy is not None else []),
        )

        if self.reviewer is not None:
            review_value = self.reviewer(request)
            if inspect.isawaitable(review_value):
                review_value = await review_value
            review_result = self._coerce_review_result(review_value)
        else:
            review_result = await self._run_default_reviewer(request)

        if policy is not None and review_result.score < policy.min_score:
            review_result.passed = False
        result.review_history.append(review_result)
        return review_result

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

    def _build_review_prompt(self, request: ReviewRequest) -> str:
        criteria = (
            "\n".join(f"- {item}" for item in request.criteria)
            or "- 整体质量、完整性、可执行性"
        )
        return (
            "你是一个严格的 Review Agent。请客观评估候选输出是否满足用户请求。\n"
            "只返回 JSON，不要输出 JSON 之外的文本。\n\n"
            f"## 用户请求\n{request.user_input}\n\n"
            f"## 候选输出\n{request.candidate_output}\n\n"
            f"## 评审维度\n{criteria}\n\n"
            "JSON 格式：\n"
            "{\n"
            '  "score": 8.5,\n'
            '  "passed": true,\n'
            '  "feedback": "具体反馈",\n'
            '  "suggestions": ["建议1", "建议2"]\n'
            "}"
        )

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

    async def _run_default_reviewer(self, request: ReviewRequest) -> ReviewResult:
        policy = self.config.review_policy
        if policy is None:
            return ReviewResult(passed=True, score=10.0)

        from app.core.agent.factory import create_agent

        prompt = policy.review_prompt or self._build_review_prompt(request)
        review_agent = create_agent(
            agent_name=policy.reviewer_agent_name,
            session_id=f"review-{self.session_id}-{self.request_id}-{request.review_round}",
            prompt=prompt,
            model=policy.reviewer_model,
            max_loop=1,
            persist=self.persist,
            review_policy=None,
        )
        review_result = await review_agent.run("请评审候选输出并返回 JSON。")
        return self._parse_reviewer_output(review_agent, review_result.raw_output or "{}")

    def _parse_reviewer_output(self, review_agent: Any, raw_output: str) -> ReviewResult:
        parsed = None
        if getattr(review_agent._llm, "parse_json", None):
            parsed = review_agent._llm.parse_json(raw_output)
        if parsed is None:
            try:
                parsed = json.loads(raw_output)
            except json.JSONDecodeError:
                parsed = {
                    "score": 0.0,
                    "passed": False,
                    "feedback": raw_output,
                    "suggestions": [],
                }

        policy = self.config.review_policy
        min_score = policy.min_score if policy is not None else 0.0
        score = float(parsed.get("score", 0.0))
        passed = bool(parsed.get("passed", score >= min_score)) and score >= min_score
        return ReviewResult(
            score=score,
            passed=passed,
            feedback=str(parsed.get("feedback", "")),
            suggestions=list(parsed.get("suggestions") or []),
        )
