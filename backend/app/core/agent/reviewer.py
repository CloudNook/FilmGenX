"""
ReviewerAgent: 独立可复用的 reviewer agent。

用法：
    from app.core.agent import create_agent, create_reviewer_agent

    reviewer = create_reviewer_agent(
        criteria=["镜头节奏", "情绪推进"],
        max_revision_rounds=2,
        on_exhausted="accept_last",
    )
    writer = create_agent(
        agent_name="writer",
        session_id="...",
        prompt="...",
        reviewer=reviewer,
    )

设计要点：
- ReviewerAgent 包一个通过 create_agent 构造的内部 Agent，把 review 流程做成独立可复用对象。
- 满足 Reviewer Protocol（`async __call__(request) -> ReviewResult`），可直接挂到 create_agent。
- review loop 控制（max_revision_rounds / on_exhausted / min_score）作为字段暴露在 reviewer 上，
  ReviewHarness 通过 getattr 读取。reviewer 不是 ReviewerAgent（例如纯函数）时使用框架默认值。
- json_schema 通过 AgentConfig.response_schema 透传到 LLMAdapter，走 Provider 原生结构化输出；
  解析失败时回落到 LLMAdapter.parse_json。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from app.core.agent.agent import Agent
from app.core.agent.base import (
    ReviewError,
    ReviewRequest,
    ReviewResult,
)
from app.core.agent.factory import create_agent

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 默认 prompt 模板和 JSON schema
# ----------------------------------------------------------------------

DEFAULT_REVIEWER_PROMPT = """\
你是一个严格的 Review Agent。请客观评估候选输出是否满足用户请求，并按 JSON Schema 返回评审结果。

评分标准（0-10 分）：
- 8.5-10：优秀，几乎无需修改
- 7-8.5：良好，少量改进空间
- 5-7：一般，需要较大修改
- 0-5：不合格，需要重新设计

要求：
- 严格、诚实、不溢美
- 指出具体问题，避免空话
- suggestions 必须可执行

只返回 JSON，不要输出 JSON 之外的文本。"""


# ReviewResult 的 JSON Schema（Provider structured output 的 contract）。
# 与 ReviewResult Pydantic 模型字段保持一致。
DEFAULT_REVIEWER_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "score": {
            "type": "number",
            "minimum": 0,
            "maximum": 10,
            "description": "0-10 分质量评分",
        },
        "passed": {
            "type": "boolean",
            "description": "是否通过评审",
        },
        "feedback": {
            "type": "string",
            "description": "评审反馈，不超过 200 字",
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "可执行修改建议",
        },
    },
    "required": ["score", "passed", "feedback", "suggestions"],
}


# ----------------------------------------------------------------------
# ReviewerAgent
# ----------------------------------------------------------------------


class ReviewerAgent:
    """
    独立可复用的 reviewer agent。

    Attributes:
        agent:               内部 ReAct Agent，承担一次评审的 LLM 调用
        json_schema:         Provider structured output 的 schema，校验 reviewer LLM 输出
        criteria:            评审维度列表，会拼到每次 review 的 user message 里
        min_score:           reviewer 评分的通过门槛；分数低于该值会强制 passed=False
        max_revision_rounds: 候选评审失败后允许的修订轮次（写入 Agent 看的是这个数）
        on_exhausted:        修订轮次耗尽后的策略：
                             - "fail":         返回 error="Review failed"
                             - "accept_last":  接受最后一版候选作为最终输出
    """

    def __init__(
        self,
        *,
        agent: Agent,
        json_schema: Dict[str, Any],
        criteria: List[str],
        min_score: float,
        max_revision_rounds: int,
        on_exhausted: Literal["fail", "accept_last"],
    ) -> None:
        self.agent = agent
        self.json_schema = json_schema
        self.criteria = list(criteria)
        self.min_score = float(min_score)
        self.max_revision_rounds = int(max_revision_rounds)
        self.on_exhausted = on_exhausted

    async def review(self, request: ReviewRequest) -> ReviewResult:
        """运行内部 reviewer agent，返回结构化 ReviewResult。"""

        user_message = self._render_user_message(request)
        logger.info(
            f"[ReviewerAgent:{self.agent.config.agent_name}] reviewing "
            f"round={request.review_round} agent={request.agent_name}"
        )
        agent_result = await self.agent.run(
            user_message,
            request_id=f"review-{request.request_id}-{request.review_round}-{uuid4().hex[:6]}",
        )

        if agent_result.error and not agent_result.raw_output:
            raise ReviewError(
                f"Reviewer agent failed: {agent_result.error}"
            )

        return self._parse_review_output(agent_result.raw_output or "")

    async def __call__(self, request: ReviewRequest) -> ReviewResult:
        return await self.review(request)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _render_user_message(self, request: ReviewRequest) -> str:
        criteria_block = (
            "\n".join(f"- {item}" for item in (request.criteria or self.criteria))
            or "- 整体质量、完整性、可执行性"
        )
        return (
            f"## 用户请求\n{request.user_input}\n\n"
            f"## 候选输出\n{request.candidate_output}\n\n"
            f"## 评审维度\n{criteria_block}\n\n"
            "请严格按 JSON Schema 返回评审结果。"
        )

    def _parse_review_output(self, raw_output: str) -> ReviewResult:
        if not raw_output:
            raise ReviewError("Reviewer agent produced empty output")

        # structured output 路径下 raw_output 已经是合法 JSON
        try:
            parsed = json.loads(raw_output)
        except json.JSONDecodeError:
            # fallback：reviewer LLM 没走 structured output 时尝试宽松解析
            llm = getattr(self.agent, "_llm", None)
            parser = getattr(llm, "parse_json", None)
            parsed = parser(raw_output) if callable(parser) else None
            if parsed is None:
                raise ReviewError(
                    f"Reviewer output is not valid JSON: {raw_output[:200]!r}"
                )

        try:
            return ReviewResult(**parsed)
        except Exception as exc:
            raise ReviewError(
                f"Reviewer output cannot be coerced to ReviewResult: {parsed}"
            ) from exc


# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------


def create_reviewer_agent(
    *,
    prompt: Optional[str] = None,
    json_schema: Optional[Dict[str, Any]] = None,
    model: str = "gemini-3-flash-preview",
    max_loop: int = 1,
    criteria: Optional[List[str]] = None,
    min_score: float = 8.0,
    max_revision_rounds: int = 1,
    on_exhausted: Literal["fail", "accept_last"] = "fail",
    agent_name: str = "reviewer",
    session_id: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> ReviewerAgent:
    """
    构建 reviewer agent。

    所有参数都有合理默认；不传任何参数即得通用默认 reviewer，可直接：

        reviewer = create_reviewer_agent()
        agent = create_agent(..., reviewer=reviewer)

    Args:
        prompt:              reviewer 的 system prompt；None 时使用 DEFAULT_REVIEWER_PROMPT
        json_schema:         reviewer LLM 输出的 JSON Schema；None 时使用 ReviewResult schema
        model:               reviewer 使用的 LLM 模型
        max_loop:            reviewer Agent 内部 ReAct 循环最大轮次（默认 1）
        criteria:            评审维度，会注入到每次 review 的 user message
        min_score:           评分通过门槛
        max_revision_rounds: 写入 Agent 在 review 失败后允许的修订轮次
        on_exhausted:        修订耗尽策略，"fail" 或 "accept_last"
        agent_name:          内部 Agent 的名称（持久化和日志用）
        session_id:          内部 Agent 的 session_id；None 时自动生成
        temperature:         可选温度参数
        max_tokens:          可选 max_tokens
    """
    effective_prompt = prompt if prompt is not None else DEFAULT_REVIEWER_PROMPT
    effective_schema = (
        json_schema if json_schema is not None else DEFAULT_REVIEWER_JSON_SCHEMA
    )
    effective_session_id = session_id or f"reviewer-{uuid4().hex[:8]}"

    inner_agent = create_agent(
        agent_name=agent_name,
        session_id=effective_session_id,
        prompt=effective_prompt,
        model=model,
        max_loop=max_loop,
        temperature=temperature,
        max_tokens=max_tokens,
        response_schema=effective_schema,
    )

    return ReviewerAgent(
        agent=inner_agent,
        json_schema=effective_schema,
        criteria=criteria or [],
        min_score=min_score,
        max_revision_rounds=max_revision_rounds,
        on_exhausted=on_exhausted,
    )
