import pytest
from app.core.supervisor.reviewer import build_reviewer_prompt, DEFAULT_REVIEWER_SYSTEM_PROMPT


def test_build_reviewer_prompt_includes_content():
    prompt = build_reviewer_prompt(
        content="这是一个测试剧本",
        review_criteria=["情感张力", "结构完整性"],
    )
    assert "这是一个测试剧本" in prompt
    assert "情感张力" in prompt
    assert "结构完整性" in prompt


def test_build_reviewer_prompt_contains_scoring_instruction():
    prompt = build_reviewer_prompt(
        content="测试内容",
        review_criteria=["创意性"],
    )
    assert "score" in prompt.lower()
    assert "passed" in prompt.lower()


def test_default_reviewer_prompt_not_empty():
    assert len(DEFAULT_REVIEWER_SYSTEM_PROMPT) > 0
