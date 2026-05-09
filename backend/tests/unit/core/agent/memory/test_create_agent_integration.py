"""create_agent 集成：memory 注入 → AgentConfig.tools / Agent.memory / ToolExecutor.extra_kwargs。

测试用 inline fakes（不依赖框架内任何具体实现）。
"""

from __future__ import annotations

import pytest

from app.core.agent.factory import create_agent
from app.core.agent.memory import (
    CandidateMemory,
    MemoryConfig,
    MemoryHarness,
)

from tests.unit.core.agent.memory._fakes import (
    FakeProvider,
    FixedCandidatesExtractor,
    PassthroughRanker,
)


def _basic_memory_config(**overrides) -> MemoryConfig:
    return MemoryConfig(
        provider=overrides.pop("provider", FakeProvider()),
        extractor=overrides.pop(
            "extractor",
            FixedCandidatesExtractor(
                [CandidateMemory(content="x", kind="fact", confidence=1.0)]
            ),
        ),
        ranker=overrides.pop("ranker", PassthroughRanker()),
        scope_metadata=overrides.pop("scope_metadata", {"project_id": 1}),
        **overrides,
    )


def test_create_agent_without_memory_no_harness_no_save_tool():
    agent = create_agent(agent_name="a", session_id="s", prompt="hi")
    assert agent.memory is None
    assert all(t.get("name") != "memory_save" for t in agent.config.tools)


def test_create_agent_with_memory_attaches_harness():
    agent = create_agent(
        agent_name="a",
        session_id="s",
        prompt="hi",
        memory=_basic_memory_config(),
    )
    assert isinstance(agent.memory, MemoryHarness)
    assert agent.memory.agent_name == "a"
    assert agent.memory.session_id == "s"


def test_create_agent_memory_injects_save_tool():
    agent = create_agent(
        agent_name="a",
        session_id="s",
        prompt="hi",
        memory=_basic_memory_config(),
    )
    names = [t.get("name") for t in agent.config.tools]
    assert names.count("memory_save") == 1


def test_create_agent_save_tool_disabled_skips_injection():
    cfg = _basic_memory_config(save_tool_enabled=False)
    agent = create_agent(
        agent_name="a",
        session_id="s",
        prompt="hi",
        memory=cfg,
    )
    names = [t.get("name") for t in agent.config.tools]
    assert "memory_save" not in names
    # 但 harness 仍挂载（fallback compact / external write 仍可用）
    assert isinstance(agent.memory, MemoryHarness)


def test_create_agent_does_not_double_inject_save_tool():
    # 调用方已经手动塞了一个同名 tool → 不应再塞第二份
    pre_tool = {"name": "memory_save", "description": "manual"}
    agent = create_agent(
        agent_name="a",
        session_id="s",
        prompt="hi",
        tools=[pre_tool],
        memory=_basic_memory_config(),
    )
    names = [t.get("name") for t in agent.config.tools]
    assert names.count("memory_save") == 1


@pytest.mark.asyncio
async def test_tool_executor_carries_memory_harness_extra_kwarg():
    """memory_save 工具能拿到 harness 实例（通过 extra_kwargs 注入）。"""
    agent = create_agent(
        agent_name="a",
        session_id="s",
        prompt="hi",
        memory=_basic_memory_config(),
    )
    # _init_tool_executor 是 lazy 的，run/stream 时才触发；这里直接调
    agent._init_tool_executor()
    assert agent._tool_executor is not None
    extra = agent._tool_executor.extra_kwargs
    assert "memory_harness" in extra
    assert extra["memory_harness"] is agent.memory


def test_memory_config_rejects_invalid_provider():
    """Protocol 校验：传一个不满足 Protocol 的对象应当报错。

    Pydantic v2 自身会做 isinstance(val, MemoryProvider) 校验（@runtime_checkable
    Protocol 走 isinstance 路径）→ 抛 ValidationError。
    """
    class _NotAProvider:
        pass

    with pytest.raises(Exception) as excinfo:
        MemoryConfig(
            provider=_NotAProvider(),  # type: ignore[arg-type]
            extractor=FixedCandidatesExtractor([]),
            ranker=PassthroughRanker(),
        )
    assert "MemoryProvider" in str(excinfo.value) or "provider" in str(excinfo.value).lower()


def test_memory_config_rejects_invalid_ranker():
    class _NotARanker:
        pass

    with pytest.raises(Exception) as excinfo:
        MemoryConfig(
            provider=FakeProvider(),
            extractor=FixedCandidatesExtractor([]),
            ranker=_NotARanker(),  # type: ignore[arg-type]
        )
    assert "MemoryRanker" in str(excinfo.value) or "ranker" in str(excinfo.value).lower()
