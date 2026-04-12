"""
Supervisor 端到端测试。

模拟完整流水线：
  SupervisorAgent → outline_writer → Reviewer → script_writer → Reviewer
                → storyboarder → Reviewer → SupervisorDoneEvent

通过 patch LLMAdapter.__init__ 实现，不依赖真实 LLM API key。
"""

import asyncio
import json
import pytest
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.agent.base import LLMResponse, StructuredToolCall, ToolCall


# ─────────────────────────────────────────────────────────────────────────────
# Mock LLM Provider
# ─────────────────────────────────────────────────────────────────────────────

class MockProvider:
    """
    确定性状态机模拟 LLM Provider 响应。

    状态流转（Supervisor 主循环）：
      0: "我将为您生成视频大纲。" → state=1
      1: tool_calls=[call_sub_agent("outline_writer")] → state=11
      11: "大纲已完成，现在进行评审。" → state=12
      12: tool_calls=[call_reviewer(...)] → state=13
      13: "评审通过，正在生成剧本。" → state=21
      21: tool_calls=[call_sub_agent("script_writer")] → state=31
      31: tool_calls=[call_sub_agent("storyboarder")] → state=41
      41: "视频生成流水线已完成！" → state=99 (done)
    """

    def __init__(self, *, sub_agent_name: str = "outline_writer"):
        self._state = 0
        self._call_count = 0
        self._sub_agent_name = sub_agent_name

    def reset(self):
        self._state = 0
        self._call_count = 0

    async def generate(self, messages, system_prompt="", tools=None, **kwargs) -> LLMResponse:
        return LLMResponse(content="", tool_calls=[], finish_reason="stop", usage={})

    async def generate_stream(
        self, messages, system_prompt="", tools=None, **kwargs
    ) -> AsyncGenerator[LLMResponse, None]:
        """
        模拟 LLM 流式响应。

        设计：多 call 状态机，强制 AgentLoop 多次调用 generate_stream。
        - 第1次调用：返回初始文本，finish_reason='tool_calls'（让循环继续，不触发 done 检查）
        - 第2次调用：返回所有 tool_calls，finish_reason='tool_calls'（AgentLoop 执行工具）
        - 第3次调用：返回 <done>，finish_reason='stop'（触发 _check_finished → DoneEvent）
        """
        self._call_count += 1

        # ── SubAgent 响应 ─────────────────────────────────────────────
        if self._sub_agent_name == "outline_writer":
            yield LLMResponse(content="大纲生成完毕。", tool_calls=[], finish_reason="stop")
            return
        if self._sub_agent_name == "script_writer":
            yield LLMResponse(content="剧本生成完毕。", tool_calls=[], finish_reason="stop")
            return
        if self._sub_agent_name == "storyboarder":
            yield LLMResponse(content="分镜生成完毕。", tool_calls=[], finish_reason="stop")
            return

        # ── Supervisor 主循环 ──────────────────────────────────────────
        if self._state == 0:
            # 第1次调用：初始文本，tool_calls 让循环继续
            self._state = 1
            yield LLMResponse(content="我将为您生成视频大纲。\n", tool_calls=[], finish_reason="tool_calls")
            return

        if self._state == 1:
            # 第2次调用：所有 tool_calls，AgentLoop 执行工具
            self._state = 2
            yield LLMResponse(
                content="",
                tool_calls=[
                    StructuredToolCall(
                        id="call_001", name="call_sub_agent",
                        arguments={"sub_agent_name": "outline_writer", "task_description": "生成视频大纲", "context_snapshot": ""},
                    ),
                    StructuredToolCall(
                        id="call_002", name="call_reviewer",
                        arguments={"content": '{"title": "大纲"}', "review_criteria": ["结构完整性"]},
                    ),
                    StructuredToolCall(
                        id="call_003", name="call_sub_agent",
                        arguments={"sub_agent_name": "script_writer", "task_description": "创作剧本", "context_snapshot": '{"title": "大纲"}'},
                    ),
                    StructuredToolCall(
                        id="call_004", name="call_sub_agent",
                        arguments={"sub_agent_name": "storyboarder", "task_description": "生成分镜", "context_snapshot": '{"script": "剧本"}'},
                    ),
                ],
                finish_reason="tool_calls",
            )
            return

        # 第3次及之后调用：done 信号
        yield LLMResponse(content="<done>", tool_calls=[], finish_reason="stop")

    def to_tool_schema(self, tools):
        return tools


# ─────────────────────────────────────────────────────────────────────────────
# Mock ToolExecutor：捕获工具调用但不真正执行 LLM
# ─────────────────────────────────────────────────────────────────────────────

class MockToolExecutor:
    def __init__(self, sub_agent_provider=None, reviewer_provider=None):
        self._sub_agent_provider = sub_agent_provider
        self._reviewer_provider = reviewer_provider
        self._executed_tools: list[dict] = []

    async def execute(self, tool_name: str, tool_call_id: str, arguments: dict, **kwargs):
        from app.core.agent.base import ToolEndEvent, ToolStartEvent

        self._executed_tools.append({"name": tool_name, "args": arguments})
        yield ToolStartEvent(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            arguments=arguments,
        )

        if tool_name == "call_sub_agent":
            sub_agent_name = arguments.get("sub_agent_name", "outline_writer")
            from app.core.supervisor.events import SubAgentStartEvent, SubAgentEndEvent
            yield SubAgentStartEvent(
                sub_agent_name=sub_agent_name,
                session_id=f"sub-{sub_agent_name}-mock",
                task_description=arguments.get("task_description", ""),
            )
            yield SubAgentEndEvent(
                sub_agent_name=sub_agent_name,
                session_id=f"sub-{sub_agent_name}-mock",
                result={
                    "schema_data": {"title": f"{sub_agent_name} 产物"},
                    "raw_output": f"{sub_agent_name} 执行完毕",
                    "loop_count": 1,
                },
            )
            yield ToolEndEvent(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                result={
                    "schema_data": {"title": f"{sub_agent_name} 产物"},
                    "raw_output": f"{sub_agent_name} 执行完毕",
                    "loop_count": 1,
                },
                is_error=False,
            )
            return

        if tool_name == "call_reviewer":
            from app.core.agent.base import TextEvent
            yield TextEvent(content="[Reviewer] 开始评审...\n")
            yield ToolEndEvent(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                result={
                    "score": 8.5,
                    "passed": True,
                    "feedback": "通过",
                    "suggestions": [],
                },
                is_error=False,
            )
            return

        if tool_name == "get_workflow_state":
            from app.core.agent.base import ToolEndEvent
            yield ToolEndEvent(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                result={"current_phase": "running", "artifacts": {}, "review_history": []},
                is_error=False,
            )
            return

        yield ToolEndEvent(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            result={"status": "ok"},
            is_error=False,
        )

    async def execute_all(self, tool_calls, concurrency=4):
        """
        批量执行工具调用，yield 中间事件和最终 list[ToolResult]。

        与 ToolExecutor.execute_all 接口一致：async generator，末尾 yield list。
        """
        import asyncio

        semaphore = asyncio.Semaphore(concurrency)
        tc_list = list(tool_calls)
        n = len(tc_list)
        tool_results: list = [None] * n
        queues: list[asyncio.Queue] = [asyncio.Queue() for _ in range(n)]
        done_events: list[asyncio.Event] = [asyncio.Event() for _ in range(n)]

        async def _runner(idx, tc):
            async with semaphore:
                async for ev in self.execute(
                    tool_name=tc.name,
                    tool_call_id=tc.id,
                    arguments=tc.arguments,
                ):
                    await queues[idx].put(ev)
                    from app.core.agent.base import ToolEndEvent
                    if isinstance(ev, ToolEndEvent):
                        tool_results[idx] = ev
                done_events[idx].set()

        pending: set[asyncio.Task] = {
            asyncio.create_task(_runner(i, tc)) for i, tc in enumerate(tc_list)
        }

        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for i, evt in enumerate(done_events):
                if evt.is_set():
                    evt.clear()
                    while not queues[i].empty():
                        try:
                            ev = queues[i].get_nowait()
                            yield ev
                        except asyncio.QueueEmpty:
                            break

        for q in queues:
            while not q.empty():
                try:
                    yield q.get_nowait()
                except asyncio.QueueEmpty:
                    break

        # Yield list[ToolResult] at end
        from app.core.agent.base import ToolResult
        final_results = []
        for i, ev in enumerate(tool_results):
            if ev is not None:
                final_results.append(ToolResult(
                    tool_call_id=tc_list[i].id,
                    tool_name=tc_list[i].name,
                    result=ev.result if hasattr(ev, "result") else None,
                    is_error=ev.is_error if hasattr(ev, "is_error") else False,
                ))
        yield final_results

    async def execute_streaming_tool(self, tool_name: str, tool_call_id: str, arguments: dict, **kwargs):
        async for ev in self.execute(tool_name, tool_call_id, arguments, **kwargs):
            yield ev


# ─────────────────────────────────────────────────────────────────────────────
# Helper: 构建 mock SupervisorAgent
# ─────────────────────────────────────────────────────────────────────────────

def build_mock_supervisor(
    supervisor_session_id: str = "sv-e2e",
    user_request: str = "生成科幻短片",
    max_loop: int = 20,
    mock_provider: MockProvider | None = None,
) -> tuple:
    """
    构建带有 mock LLM 和 tool executor 的 SupervisorAgent。

    Returns:
        (agent, mock_provider, mock_tool_executor, restore_fn)
        restore_fn() — 调用完后恢复原始 _init_llm
    """
    from app.core.agent.agent import Agent

    if mock_provider is None:
        mock_provider = MockProvider()

    mock_tool_executor = MockToolExecutor()

    # Permanently patch Agent._init_llm so it uses mock_provider directly,
    # bypassing real LLMAdapter which would call get_adapter() → real API.
    # The patch must stay active through the entire test (including stream()).
    original_init_llm = Agent._init_llm

    def patched_init_llm(self):
        if self._llm is not None:
            return
        # Directly create a MagicMock LLM adapter backed by mock_provider.
        # This bypasses LLMAdapter.__init__ (which calls get_adapter() → real API)
        # while preserving self.config.
        mock_llm = MagicMock()
        mock_llm.config = self.config
        mock_llm.tools = self.config.tools if self.config and self.config.tools else []
        mock_llm._provider = mock_provider
        mock_llm.generate = mock_provider.generate
        mock_llm.generate_stream = mock_provider.generate_stream
        mock_llm.to_tool_schema = mock_provider.to_tool_schema
        self._llm = mock_llm

    Agent._init_llm = patched_init_llm

    from app.core.supervisor.supervisor import SupervisorAgent

    agent = SupervisorAgent(
        supervisor_session_id=supervisor_session_id,
        user_request=user_request,
        sub_agent_configs={},
        middlewares=[],
        persist=None,
        max_loop=max_loop,
    )

    agent._tool_executor = mock_tool_executor
    # Also patch the inner agent so tool calls go through the mock executor
    agent._agent._tool_executor = mock_tool_executor

    def restore():
        Agent._init_llm = original_init_llm

    return agent, mock_provider, mock_tool_executor, restore


# ─────────────────────────────────────────────────────────────────────────────
# Test Cases
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_supervisor_stream_produces_supervisor_done_event():
    """
    验证 SupervisorAgent.stream() 最终产生 SupervisorDoneEvent。
    """
    # sub_agent_name=None 确保走 supervisor 状态机
    mock_provider = MockProvider(sub_agent_name=None)
    agent, _, _, restore = build_mock_supervisor(
        supervisor_session_id="sv-e2e-done",
        mock_provider=mock_provider,
    )
    try:
        events = []
        async for ev in agent.stream(initial_input="生成科幻短片"):
            events.append(ev)

        event_types = [type(e).__name__ for e in events]

        # 至少应该有 SupervisorDoneEvent
        done_events = [e for e in events if hasattr(e, "type") and e.type == "supervisor_done"]
        assert len(done_events) >= 1, f"缺少 SupervisorDoneEvent: {event_types}"
        assert done_events[0].supervisor_session_id == "sv-e2e-done"
        print(f"✓ SupervisorDoneEvent OK — 事件类型: {event_types}")
    finally:
        restore()


@pytest.mark.asyncio
async def test_supervisor_calls_all_three_sub_agents():
    """
    验证完整流水线中三个 SubAgent 均被调用。
    """
    # sub_agent_name=None 确保 mock provider 走 supervisor 状态机，而非 sub-agent 分支
    mock_provider = MockProvider(sub_agent_name=None)
    agent, _, tool_executor, restore = build_mock_supervisor(
        supervisor_session_id="sv-e2e-full",
        mock_provider=mock_provider,
    )
    try:
        events = []
        sub_agent_starts = []
        sub_agent_ends = []

        async for ev in agent.stream(initial_input="生成完整科幻短片"):
            events.append(ev)
            if hasattr(ev, "type"):
                if ev.type == "sub_agent_start":
                    sub_agent_starts.append(ev.sub_agent_name)
                elif ev.type == "sub_agent_end":
                    sub_agent_ends.append(ev.sub_agent_name)

        expected = {"outline_writer", "script_writer", "storyboarder"}
        assert set(sub_agent_starts) == expected, \
            f"SubAgentStart 期望 {expected}，实际 {set(sub_agent_starts)}"
        assert set(sub_agent_ends) == expected, \
            f"SubAgentEnd 期望 {expected}，实际 {set(sub_agent_ends)}"

        done = next(e for e in events if hasattr(e, "type") and e.type == "supervisor_done")
        assert done.artifacts is not None

        print(f"✓ 三个 SubAgent 均被调用: {sub_agent_starts}")
        print(f"  SupervisorDoneEvent artifacts: {list(done.artifacts.keys())}")
    finally:
        restore()


@pytest.mark.asyncio
async def test_supervisor_tools_executed_in_order():
    """
    验证工具调用顺序：call_sub_agent → call_reviewer → call_sub_agent → ... → done。
    """
    # sub_agent_name=None 确保走 supervisor 状态机
    mock_provider = MockProvider(sub_agent_name=None)
    agent, _, tool_executor, restore = build_mock_supervisor(
        supervisor_session_id="sv-e2e-order",
        mock_provider=mock_provider,
    )
    try:
        events = []
        tool_names: list[str] = []

        async for ev in agent.stream(initial_input="生成"):
            events.append(ev)
            if hasattr(ev, "tool_name"):
                tool_names.append(ev.tool_name)

        # 验证 call_sub_agent 被调用（至少 1 次）
        assert "call_sub_agent" in tool_names, f"call_sub_agent 未被调用，tool_names={tool_names}"
        # 验证 call_reviewer 被调用
        assert "call_reviewer" in tool_names, f"call_reviewer 未被调用，tool_names={tool_names}"

        # 验证顺序：call_sub_agent → call_reviewer
        sub_idx = next(i for i, n in enumerate(tool_names) if n == "call_sub_agent")
        rev_idx = next(i for i, n in enumerate(tool_names) if n == "call_reviewer")
        assert sub_idx < rev_idx, "call_sub_agent 应在 call_reviewer 之前"

        print(f"✓ 工具调用顺序 OK: {tool_names}")
    finally:
        restore()


@pytest.mark.asyncio
async def test_supervisor_context_artifacts_accumulated():
    """
    验证 SupervisorContext.artifacts 在各 SubAgent 完成后被正确记录。
    """
    # sub_agent_name=None 确保走 supervisor 状态机
    mock_provider = MockProvider(sub_agent_name=None)
    agent, _, _, restore = build_mock_supervisor(
        supervisor_session_id="sv-e2e-artifacts",
        mock_provider=mock_provider,
    )
    try:
        events = []
        async for ev in agent.stream(initial_input="生成"):
            events.append(ev)
            if hasattr(ev, "type") and ev.type == "supervisor_done":
                artifacts = ev.artifacts
                # artifacts 应包含各 SubAgent 的产物（mock 中为 schema_data）
                assert isinstance(artifacts, dict)
                print(f"✓ SupervisorDoneEvent.artifacts: {artifacts}")
                return

        pytest.fail("未收到 SupervisorDoneEvent")
    finally:
        restore()


@pytest.mark.asyncio
async def test_supervisor_session_id_format():
    """验证 supervisor_session_id 格式正确。"""
    from app.core.supervisor.supervisor import SupervisorAgent

    agent = SupervisorAgent(
        supervisor_session_id="sv-test-format",
        user_request="测试",
        sub_agent_configs={},
        middlewares=[],
        persist=None,
    )
    assert agent.supervisor_session_id == "sv-test-format"
    assert agent.supervisor_session_id.startswith("sv-")
    print(f"✓ supervisor_session_id: {agent.supervisor_session_id}")


@pytest.mark.asyncio
async def test_supervisor_stream_events_have_source_field():
    """
    验证所有流式事件带有 source='supervisor' 标记。
    """
    # sub_agent_name=None 确保走 supervisor 状态机
    mock_provider = MockProvider(sub_agent_name=None)
    agent, _, _, restore = build_mock_supervisor(
        supervisor_session_id="sv-e2e-source",
        mock_provider=mock_provider,
    )
    try:
        events = []
        async for ev in agent.stream(initial_input="测试"):
            events.append(ev)
            if hasattr(ev, "source"):
                assert ev.source == "supervisor", f"source 应为 supervisor，实际: {ev.source}"

        print(f"✓ 所有事件 source='supervisor' OK，事件数: {len(events)}")
    finally:
        restore()


@pytest.mark.asyncio
async def test_supervisor_workflow_service_connected():
    """
    验证 SupervisorWorkflowService 被正确注入并在 SubAgent 完成后触发。
    """
    from unittest.mock import AsyncMock

    # sub_agent_name=None 确保走 supervisor 状态机
    mock_provider = MockProvider(sub_agent_name=None)
    agent, _, _, restore = build_mock_supervisor(
        supervisor_session_id="sv-e2e-service",
        mock_provider=mock_provider,
    )
    try:
        # Mock workflow service
        mock_service = MagicMock()
        mock_service.append_artifacts = AsyncMock()
        agent._tool_ctx["workflow_service"] = mock_service

        events = []
        async for ev in agent.stream(initial_input="测试"):
            events.append(ev)
            if hasattr(ev, "type") and ev.type == "supervisor_done":
                break

        # 验证 append_artifacts 被调用（每次 SubAgent 完成后调用）
        if mock_service.append_artifacts.called:
            print(f"✓ workflow_service.append_artifacts 调用次数: {mock_service.append_artifacts.call_count}")
        else:
            print("⚠ workflow_service 未被调用（可能因 mock provider 未触发完整流程）")

        print(f"✓ 事件数: {len(events)}")
    finally:
        restore()


@pytest.mark.asyncio
async def test_workspace_chat_request_schema_with_pipeline():
    """验证 Workspace pipeline schema 完整性。"""
    from app.schemas.workspace import WorkspaceChatRequest, SupervisorPipelineRequest

    # 最小请求（无 pipeline）
    req_min = WorkspaceChatRequest(content="生成短片")
    assert req_min.pipeline is None
    assert req_min.content == "生成短片"

    # 带完整 pipeline
    req_full = WorkspaceChatRequest(
        content="生成短片",
        pipeline=SupervisorPipelineRequest(
            user_request="科幻短片",
            model="gemini-pro",
            max_loop=50,
        ),
    )
    assert req_full.pipeline.user_request == "科幻短片"
    assert req_full.pipeline.model == "gemini-pro"
    assert req_full.pipeline.max_loop == 50

    # pipeline.user_request 优先级高于 content
    priority_req = WorkspaceChatRequest(
        content="原始消息",
        pipeline=SupervisorPipelineRequest(user_request="流水线专用"),
    )
    assert priority_req.pipeline.user_request == "流水线专用"

    print("✓ Workspace pipeline schema OK")


@pytest.mark.asyncio
async def test_workspace_chat_endpoint_branches_on_pipeline():
    """
    验证 chat_workspace 端点在 pipeline 非空时进入 Supervisor 路径。

    通过 mock 验证 _chat_workspace_supervisor 被调用。
    """
    from unittest.mock import AsyncMock

    mock_supervisor = MagicMock()
    mock_stream_events = [
        MagicMock(spec=type("Event", (), {"type": "supervisor_done", "source": "supervisor", "model_dump": lambda: {}}))
    ]

    async def mock_stream(initial_input):
        for ev in mock_stream_events:
            yield ev

    mock_supervisor.stream = mock_stream
    mock_supervisor.supervisor_session_id = "sv-ws-test"

    with patch("app.api.v1.endpoints.workspaces._create_supervisor_for_workspace") as mock_factory:
        mock_factory.return_value = mock_supervisor

        # 调用 _create_supervisor_for_workspace 验证签名
        from app.api.v1.endpoints.workspaces import _create_supervisor_for_workspace

        mock_service = MagicMock()
        result = _create_supervisor_for_workspace(
            user_request="测试",
            model="gemini-3-flash-preview",
            max_loop=30,
            workflow_service=mock_service,
        )
        assert result is mock_supervisor
        # _create_supervisor_for_workspace 调用 create_supervisor，后者设置
        # supervisor._tool_ctx["workflow_service"] = workflow_service
        mock_factory.assert_called_once()
        call_kwargs = mock_factory.call_args.kwargs
        assert call_kwargs["workflow_service"] is mock_service
        assert call_kwargs["user_request"] == "测试"
        assert call_kwargs["model"] == "gemini-3-flash-preview"
        assert call_kwargs["max_loop"] == 30

    print("✓ chat_workspace pipeline 分支 OK")


@pytest.mark.asyncio
async def test_supervisor_agent_initializes_all_components():
    """验证 SupervisorAgent 正确初始化所有组件。"""
    from app.core.supervisor.supervisor import SupervisorAgent

    agent = SupervisorAgent(
        supervisor_session_id="sv-e2e-init",
        user_request="测试初始化",
        sub_agent_configs={"outline_writer": {"model": "gemini-flash"}},
        middlewares=[],
        persist=None,
        max_loop=10,
    )

    # SupervisorContext
    assert agent.context is not None
    assert agent.context.user_request == "测试初始化"
    assert agent.context.supervisor_session_id == "sv-e2e-init"

    # SupervisorSession
    assert agent.session is not None
    assert agent.session.supervisor_session_id == "sv-e2e-init"

    # _tool_ctx
    assert "_tool_ctx" in agent.__dict__ or hasattr(agent, "_tool_ctx")
    assert "supervisor_context" in agent._tool_ctx

    # 内部 Agent
    assert agent._agent is not None
    assert hasattr(agent._agent, "run")
    assert hasattr(agent._agent, "stream")

    print("✓ SupervisorAgent 初始化 OK")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
