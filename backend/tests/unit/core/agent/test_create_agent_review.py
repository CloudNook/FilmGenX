"""
端到端集成测试：真实 LLM + 真实 ReviewerAgent。

通过 create_reviewer_agent 起一个真实评审 Agent，挂到 writer Agent，全部使用真实 Gemini API。
验证完整的「写 → 评 → 修订 → 通过」链路。

环境要求：backend/.env 中已配置 GOOGLE_API_KEY。
该测试会真实调用 Gemini API，会消耗少量 quota。
"""

from __future__ import annotations

import os

import pytest

from app.core.agent import (
    ReviewerAgent,
    create_agent,
    create_reviewer_agent,
)


def _google_api_key_available() -> bool:
    """Settings 启动时会从 backend/.env 自动读取 GOOGLE_API_KEY。"""
    if os.environ.get("GOOGLE_API_KEY"):
        return True
    try:
        from app.core.config import settings
        return bool(settings.GOOGLE_API_KEY)
    except Exception:
        return False


# 没有 GOOGLE_API_KEY 时跳过，避免在 CI 无密钥环境失败
pytestmark = pytest.mark.skipif(
    not _google_api_key_available(),
    reason="GOOGLE_API_KEY not configured; skipping real-LLM end-to-end test",
)


# ----------------------------------------------------------------------
# Prompts
# ----------------------------------------------------------------------

WRITER_SYSTEM_PROMPT = """\
你是一位资深动作戏编剧。要求：

1. 直接输出场景内容，不要写"好的我来帮你"这类应答语。
2. 每次输出长度 80-200 字，结构包含：场景 / 人物动作 / 情绪转折。
3. 如果收到 [REVIEW_FAILED] 反馈，必须严格按建议修订，重新输出完整新版本，不要解释你做了什么。
"""

REVIEWER_SYSTEM_PROMPT = """\
你是严格的影视剧本评审 Agent。客观评估候选场景文本是否满足专业动作戏剧本要求。

评分标准（0-10 分）：
- 8.5-10：节奏紧凑、动作明确、情绪推进清晰、画面感强
- 7-8.5：基本合格，有少量改进空间
- 5-7：明显问题（节奏松散、动作含糊、情绪平淡），需要较大修改
- 0-5：不合格，缺核心要素

要求：
- 严格、诚实、不溢美
- feedback 指出具体问题，避免空话
- suggestions 给出可执行的修改建议（每条不超过 20 字）

只返回符合 JSON Schema 的 JSON，不要输出 JSON 之外的文本。
"""


@pytest.mark.asyncio
async def test_create_agent_with_real_reviewer_agent_real_llm():
    """
    端到端真实 LLM 测试：

    1. 通过 create_reviewer_agent 起一个真实 reviewer Agent（带专业评审 prompt + JSON Schema）
    2. 通过 create_agent 起 writer，挂载 reviewer
    3. writer 输出动作戏 → reviewer 评审 → 不通过则进入修订循环 → 最终通过或耗尽
    4. 验证：评审历史完整、评分单调收敛、最终输出存在
    """
    reviewer: ReviewerAgent = create_reviewer_agent(
        prompt=REVIEWER_SYSTEM_PROMPT,
        criteria=[
            "节奏紧凑度",
            "动作描写具体",
            "情绪推进清晰",
            "画面感与镜头调度暗示",
        ],
        min_score=8.0,
        max_revision_rounds=2,
        on_exhausted="accept_last",
        # max_loop=1 默认，即一轮 LLM 调用产 JSON 即返回
    )

    writer = create_agent(
        agent_name="writer",
        session_id="real-llm-review-e2e",
        prompt=WRITER_SYSTEM_PROMPT,
        reviewer=reviewer,
    )

    user_request = (
        "写一场动作戏：雨夜，独狼侦探追捕街头逃犯，巷弄中三招制服。"
        "要求节奏紧凑，体现侦探的专业克制。"
    )

    result = await writer.run(user_request)

    # ── 链路完整性 ────────────────────────────────────────────────────
    # 至少跑过一轮评审
    assert len(result.review_history) >= 1, "reviewer 应该至少被调用一次"

    for review in result.review_history:
        assert 0.0 <= review.score <= 10.0, f"评分越界: {review.score}"
        assert isinstance(review.passed, bool)
        assert isinstance(review.feedback, str)
        assert isinstance(review.suggestions, list)

    # ── 最终输出 ──────────────────────────────────────────────────────
    # 由于 on_exhausted=accept_last，无论是否通过，最终都应该 finished=True
    assert result.finished is True
    assert result.raw_output, "最终输出不应为空"
    assert len(result.raw_output) >= 30, "动作戏场景输出应有合理长度"

    # ── 行为契约 ──────────────────────────────────────────────────────
    last = result.review_history[-1]
    if last.passed:
        # 通过：review_exhausted 一定是 False
        assert result.review_exhausted is False
        assert result.error is None
    else:
        # 未通过且最终走到这一步，说明耗尽修订次数后被 accept_last 接住
        assert result.review_exhausted is True
        assert result.error is None
        assert len(result.review_history) >= 2, "耗尽前至少要经过 max_revision_rounds+1 轮"

    print(f"\n=== Final output ({len(result.raw_output)} chars) ===")
    print(result.raw_output)
    print(f"\n=== Review history ({len(result.review_history)} rounds) ===")
    for i, r in enumerate(result.review_history, 1):
        print(f"  Round {i}: score={r.score} passed={r.passed}")
        print(f"    feedback: {r.feedback}")
        if r.suggestions:
            print(f"    suggestions: {r.suggestions}")
