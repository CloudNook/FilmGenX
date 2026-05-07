"""
保证 build_default_registry 把业务层的 prompt + response_schema + reviewer prompt
正确装到 sub-agent 上，并通过 call_sub_agent 透传到 create_agent。

这是 sub-agent 输出质量的第一道护栏：sub-agent prompt 不能再是空字符串。
"""

import pytest

from app.agents import (
    REVIEWER_PROMPT,
    SUB_AGENT_PROMPT,
    SUB_AGENT_RESPONSE_SCHEMA,
)
from app.core.agent.base import AgentResult, DoneEvent
from app.core.supervisor.context import SupervisorContext
from app.core.supervisor.registry import (
    RegisteredAgent,
    SupervisorAgentRegistry,
    build_default_registry,
)
from app.core.supervisor.tools import call_sub_agent
from app.core.supervisor.workflow import WorkflowNodeDefinition


SUB_AGENT_NAMES = ["outline_agent", "script_agent", "storyboard_agent"]


# ---------------------------------------------------------------------- #
# RegisteredAgent shape：prompt / response_schema / reviewer 三件齐全
# ---------------------------------------------------------------------- #


def test_default_registry_assigns_domain_prompt_to_each_sub_agent():
    """每个 sub-agent 必须挂载 app.agents 里对应的 domain prompt。"""
    registry = build_default_registry()
    for name in SUB_AGENT_NAMES:
        agent = registry.get(name)
        assert agent is not None, f"missing sub-agent {name}"
        assert agent.prompt, f"{name} prompt is empty"
        assert agent.prompt == SUB_AGENT_PROMPT[name]
        # 长度兜底：不允许悄悄回到一句话占位
        assert len(agent.prompt) > 200


def test_default_registry_assigns_response_schema_to_each_sub_agent():
    """每个 sub-agent 必须挂载从 Pydantic 类导出的 JSON Schema。"""
    registry = build_default_registry()
    for name in SUB_AGENT_NAMES:
        agent = registry.get(name)
        assert agent.response_schema is not None
        # 与 app.agents 暴露的同源
        assert agent.response_schema is SUB_AGENT_RESPONSE_SCHEMA[name] or (
            agent.response_schema == SUB_AGENT_RESPONSE_SCHEMA[name]
        )
        # JSON Schema 必备字段
        assert "properties" in agent.response_schema
        assert "type" in agent.response_schema


def test_default_registry_reviewer_uses_domain_prompt():
    """每个 sub-agent 的 reviewer 必须用 domain reviewer prompt（不是默认 prompt）。"""
    from app.core.agent.reviewer import DEFAULT_REVIEWER_PROMPT

    registry = build_default_registry()
    for name in SUB_AGENT_NAMES:
        agent = registry.get(name)
        assert agent.reviewer is not None
        rev_prompt = agent.reviewer.agent.config.prompt
        assert rev_prompt == REVIEWER_PROMPT[name]
        assert rev_prompt != DEFAULT_REVIEWER_PROMPT


def test_default_registry_reviewer_loop_settings():
    """reviewer 的修订轮次和通过门槛对三个 sub-agent 当前一致。"""
    registry = build_default_registry()
    for name in SUB_AGENT_NAMES:
        agent = registry.get(name)
        assert agent.reviewer.max_revision_rounds == 2
        assert agent.reviewer.min_score == 7.5
        assert agent.reviewer.on_exhausted == "accept_last"


# ---------------------------------------------------------------------- #
# call_sub_agent 透传：prompt 和 response_schema 必须出现在 create_agent kwargs
# ---------------------------------------------------------------------- #


class _FakeAgent:
    async def stream(self, initial_input: str):
        yield DoneEvent(
            result=AgentResult(
                agent_name="outline_agent",
                raw_output="ok",
                finished=True,
            )
        )


@pytest.mark.asyncio
async def test_call_sub_agent_passes_domain_prompt_and_schema_to_create_agent(monkeypatch):
    """
    确保 call_sub_agent 把 registered.prompt 和 registered.response_schema 透传给 create_agent。
    这是回归用：之前 prompt 被 hardcode 成 ""，本测试钉死它必须来自 registry。
    """
    captured: dict = {}

    def _fake_create_agent(**kwargs):
        captured.update(kwargs)
        return _FakeAgent()

    monkeypatch.setattr(
        "app.core.supervisor.tools.create_agent",
        _fake_create_agent,
    )

    ctx = SupervisorContext(
        supervisor_session_id="sv-wiring-001",
        user_request="start",
        workflow_definitions=[
            WorkflowNodeDefinition(
                key="outline",
                label="Outline",
                node_type="text",
                depends_on=[],
            ),
        ],
    )

    # 用 default registry 而不是构造一个空的 RegisteredAgent，让 prompt 走真链路
    async for _event in call_sub_agent(
        sub_agent_name="outline_agent",
        task_description="generate outline",
        supervisor_context=ctx,
        registry=build_default_registry(),
    ):
        pass

    assert captured["prompt"] == SUB_AGENT_PROMPT["outline_agent"]
    assert captured["response_schema"] == SUB_AGENT_RESPONSE_SCHEMA["outline_agent"]
    assert captured["agent_name"] == "outline_agent"


@pytest.mark.asyncio
async def test_call_sub_agent_uses_empty_prompt_when_registered_is_empty(monkeypatch):
    """
    如果上层传一个 prompt='' 的 RegisteredAgent，call_sub_agent 不再硬编码空串而是按字段透传。
    保证业务 registry 里 prompt 字段是唯一来源。
    """
    captured: dict = {}

    def _fake_create_agent(**kwargs):
        captured.update(kwargs)
        return _FakeAgent()

    monkeypatch.setattr(
        "app.core.supervisor.tools.create_agent",
        _fake_create_agent,
    )

    ctx = SupervisorContext(
        supervisor_session_id="sv-wiring-002",
        user_request="start",
        workflow_definitions=[
            WorkflowNodeDefinition(
                key="outline",
                label="Outline",
                node_type="text",
                depends_on=[],
            ),
        ],
    )
    custom_registry = SupervisorAgentRegistry(
        agents=[
            RegisteredAgent(
                name="outline_agent",
                label="Outline",
                description="empty",
                node_keys=["outline"],
                # 不传 prompt / response_schema → 走 default
            )
        ]
    )

    async for _event in call_sub_agent(
        sub_agent_name="outline_agent",
        task_description="x",
        supervisor_context=ctx,
        registry=custom_registry,
    ):
        pass

    assert captured["prompt"] == ""
    assert captured["response_schema"] is None
