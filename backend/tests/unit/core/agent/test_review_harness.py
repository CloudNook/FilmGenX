from typing import Any

import pytest

from app.core.agent.base import (
    AgentConfig,
    LLMResponse,
    ReviewError,
    ReviewPolicy,
    ReviewResult,
    TextEvent,
)
from app.core.agent.loop import AgentLoop


class _SequencedLLM:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)
        self.messages_seen: list[list[dict[str, Any]]] = []

    async def generate(self, messages, system_prompt: str = ""):
        self.messages_seen.append(list(messages))
        return LLMResponse(
            content=self.outputs.pop(0),
            finish_reason="stop",
        )


class _StreamingSequencedLLM:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)

    async def generate_stream(self, messages, system_prompt: str = ""):
        yield LLMResponse(content=self.outputs.pop(0))
        yield LLMResponse(finish_reason="stop")


@pytest.mark.asyncio
async def test_review_failure_appends_synthetic_feedback_and_continues_loop():
    llm = _SequencedLLM(["rough draft", "revised draft"])
    review_results = [
        ReviewResult(
            score=5.0,
            passed=False,
            feedback="缺少镜头节奏",
            suggestions=["补充分镜节奏"],
        ),
        ReviewResult(score=9.0, passed=True, feedback="通过"),
    ]

    async def reviewer(request):
        assert request.agent_name == "writer"
        assert request.user_input == "写一场动作戏"
        return review_results.pop(0)

    loop = AgentLoop(
        config=AgentConfig(
            agent_name="writer",
            prompt="",
            review_policy=ReviewPolicy(enabled=True, max_revision_rounds=2),
        ),
        llm=llm,
        reviewer=reviewer,
    )

    result = await loop.run("写一场动作戏")

    assert result.finished is True
    assert result.raw_output == "revised draft"
    assert [review.score for review in result.review_history] == [5.0, 9.0]
    assert any(
        msg["role"] == "user"
        and msg.get("metadata", {}).get("source") == "reviewer"
        and "缺少镜头节奏" in msg["content"]
        for msg in llm.messages_seen[-1]
    )


@pytest.mark.asyncio
async def test_stream_review_buffers_failed_candidate_until_review_passes():
    llm = _StreamingSequencedLLM(["rough draft", "revised draft"])
    review_results = [
        ReviewResult(score=5.0, passed=False, feedback="不够完整"),
        ReviewResult(score=9.0, passed=True, feedback="通过"),
    ]

    async def reviewer(request):
        return review_results.pop(0)

    loop = AgentLoop(
        config=AgentConfig(
            agent_name="writer",
            prompt="",
            review_policy=ReviewPolicy(enabled=True, max_revision_rounds=2),
        ),
        llm=llm,
        reviewer=reviewer,
    )

    events = []
    async for event in loop.stream_run("写一场动作戏"):
        events.append(event)

    text_chunks = [event.content for event in events if isinstance(event, TextEvent)]
    assert text_chunks == ["revised draft"]


@pytest.mark.asyncio
async def test_reviewer_must_return_review_result_or_compatible_dict():
    llm = _SequencedLLM(["rough draft"])

    def invalid_reviewer(_request):
        return "not a review result"

    loop = AgentLoop(
        config=AgentConfig(
            agent_name="writer",
            prompt="",
            review_policy=ReviewPolicy(enabled=True),
        ),
        llm=llm,
        reviewer=invalid_reviewer,
    )

    result = await loop.run("写一场动作戏")

    assert result.finished is False
    assert isinstance(result.error, str)
    assert "Reviewer must return ReviewResult or dict compatible with ReviewResult" in result.error
