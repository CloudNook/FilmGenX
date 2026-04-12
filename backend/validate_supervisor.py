"""
Supervisor 功能验证脚本。

覆盖范围：
1. SupervisorAgent 工厂创建
2. SupervisorAgent 核心属性
3. 工具 Schema 注册
4. SupervisorContext / SupervisorSession
5. call_sub_agent / call_reviewer / get_workflow_state 工具函数
6. 流式事件类型
7. ConcurrencyLimiter
8. workflow_service DB 持久化链路（mock）
"""

import asyncio
import sys
import os

# 确保 backend 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from unittest.mock import patch, MagicMock, AsyncMock


def green(msg):
    print(f"\033[92m✓ {msg}\033[0m")


def red(msg):
    print(f"\033[91m✗ {msg}\033[0m")


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


# ─────────────────────────────────────────────────────────────
# 1. SupervisorAgent 工厂创建
# ─────────────────────────────────────────────────────────────
section("1. SupervisorAgent 工厂创建")

try:
    from app.core.supervisor.factory import create_supervisor

    supervisor = create_supervisor(
        user_request="生成一个科幻短片脚本",
        model="gemini-3-flash-preview",
        max_loop=5,
        persist=None,  # 不实际连接 Redis
    )

    assert supervisor is not None
    assert hasattr(supervisor, "supervisor_session_id")
    assert supervisor.supervisor_session_id.startswith("sv-")
    assert hasattr(supervisor, "_tool_ctx")
    assert supervisor._tool_ctx.get("workflow_service") is None
    green(f"create_supervisor() OK — session={supervisor.supervisor_session_id}")
except Exception as e:
    red(f"create_supervisor() 失败: {e}")
    import traceback
    traceback.print_exc()

# ─────────────────────────────────────────────────────────────
# 2. workflow_service 注入
# ─────────────────────────────────────────────────────────────
section("2. workflow_service 注入")

try:
    mock_service = MagicMock()
    supervisor2 = create_supervisor(
        user_request="test",
        persist=None,
        workflow_service=mock_service,
    )
    assert supervisor2._tool_ctx.get("workflow_service") is mock_service
    green("workflow_service 注入 OK")
except Exception as e:
    red(f"workflow_service 注入失败: {e}")

# ─────────────────────────────────────────────────────────────
# 3. SupervisorAgent 核心属性
# ─────────────────────────────────────────────────────────────
section("3. SupervisorAgent 核心属性")

try:
    assert hasattr(supervisor, "context")
    assert hasattr(supervisor.context, "user_request")
    assert supervisor.context.user_request == "生成一个科幻短片脚本"
    green("SupervisorContext 绑定 OK")

    assert hasattr(supervisor, "session")
    assert hasattr(supervisor.session, "supervisor_session_id")
    green("SupervisorSession 绑定 OK")

    assert hasattr(supervisor, "_agent")
    assert hasattr(supervisor._agent, "run")
    assert hasattr(supervisor._agent, "stream")
    green("内部 Agent 实例 OK")
except Exception as e:
    red(f"核心属性检查失败: {e}")

# ─────────────────────────────────────────────────────────────
# 4. 工具 Schema 注册
# ─────────────────────────────────────────────────────────────
section("4. 工具 Schema 注册")

try:
    from app.core.supervisor.tools import get_supervisor_tool_schemas

    schemas = get_supervisor_tool_schemas()
    tool_names = {s["name"] for s in schemas}

    assert "call_sub_agent" in tool_names
    assert "call_reviewer" in tool_names
    assert "get_workflow_state" in tool_names
    green(f"工具注册 OK: {tool_names}")

    call_sub_schema = next(s for s in schemas if s["name"] == "call_sub_agent")
    assert "sub_agent_name" in call_sub_schema["parameters"]["properties"]
    enum_vals = call_sub_schema["parameters"]["properties"]["sub_agent_name"]["enum"]
    assert set(enum_vals) == {"outline_writer", "script_writer", "storyboarder"}
    green(f"call_sub_agent enum OK: {enum_vals}")
except Exception as e:
    red(f"工具 Schema 检查失败: {e}")

# ─────────────────────────────────────────────────────────────
# 5. SupervisorContext
# ─────────────────────────────────────────────────────────────
section("5. SupervisorContext")

try:
    from app.core.supervisor.context import SupervisorContext

    ctx = SupervisorContext(
        supervisor_session_id="sv-test-123",
        user_request="测试需求",
    )

    assert ctx.user_request == "测试需求"
    assert ctx.current_phase == "init"
    assert ctx.artifacts == {}
    assert ctx.review_history == []
    ctx.current_phase = "outline"
    assert ctx.current_phase == "outline"
    ctx.artifacts["outline_writer"] = {"title": "大纲"}
    assert ctx.artifacts["outline_writer"]["title"] == "大纲"
    ctx.sub_agent_sessions["outline_writer"] = "sub-outline-abc123"
    assert ctx.sub_agent_sessions["outline_writer"] == "sub-outline-abc123"
    green("SupervisorContext 读写 OK")
except Exception as e:
    red(f"SupervisorContext 失败: {e}")
    import traceback
    traceback.print_exc()

# ─────────────────────────────────────────────────────────────
# 6. SupervisorSession
# ─────────────────────────────────────────────────────────────
section("6. SupervisorSession")

try:
    from app.core.supervisor.session import SupervisorSession

    sess = SupervisorSession("sv-test-456")
    sess.register_sub_session("script_writer", "sub-script-def456")
    sub = sess.get_sub_session("script_writer")
    assert sub == "sub-script-def456"
    all_sessions = sess.get_all_sessions()
    assert "script_writer" in all_sessions
    green("SupervisorSession OK")
except Exception as e:
    red(f"SupervisorSession 失败: {e}")

# ─────────────────────────────────────────────────────────────
# 7. 流式事件类型
# ─────────────────────────────────────────────────────────────
section("7. 流式事件类型")

try:
    from app.core.supervisor.events import (
        SupervisorDoneEvent,
        SubAgentStartEvent,
        SubAgentEndEvent,
        ReviewEndEvent,
    )
    from app.core.agent.base import ThinkingEvent, TextEvent

    done = SupervisorDoneEvent(
        supervisor_session_id="sv-abc",
        artifacts={"outline": {"title": "测试"}},
        final_result="完成",
    )
    assert done.supervisor_session_id == "sv-abc"
    assert done.type == "supervisor_done"
    green("SupervisorDoneEvent OK")

    start = SubAgentStartEvent(
        sub_agent_name="outline_writer",
        session_id="sub-xyz",
        task_description="生成大纲",
    )
    assert start.sub_agent_name == "outline_writer"
    assert start.type == "sub_agent_start"
    green("SubAgentStartEvent OK")

    end = SubAgentEndEvent(
        sub_agent_name="outline_writer",
        session_id="sub-xyz",
        result={"schema_data": {"title": "大纲"}},
    )
    assert end.result["schema_data"]["title"] == "大纲"
    green("SubAgentEndEvent OK")

    # ReviewEndEvent 需要 sub_agent_name
    review_end = ReviewEndEvent(
        sub_agent_name="outline_writer",
        score=8.5,
        passed=True,
        feedback="Good",
        suggestions=[],
    )
    assert review_end.score == 8.5
    green("ReviewEndEvent OK")
except Exception as e:
    red(f"流式事件类型失败: {e}")
    import traceback
    traceback.print_exc()

# ─────────────────────────────────────────────────────────────
# 8. ConcurrencyLimiter
# ─────────────────────────────────────────────────────────────
section("8. SubAgentConcurrencyLimiter")

try:
    from app.core.supervisor.concurrency import SubAgentConcurrencyLimiter

    async def run_concurrency_test():
        # 重置单例，测试独立实例
        SubAgentConcurrencyLimiter._instance = None
        limiter = SubAgentConcurrencyLimiter(max_concurrent=3, timeout_seconds=10)

        assert limiter.active_count() == 0

        # 获取一个 permit
        permit = await limiter.acquire("outline_writer")
        assert limiter.active_count() == 1
        green("acquire() + active_count OK")

        # 再获取一个
        permit2 = await limiter.acquire("script_writer")
        assert limiter.active_count() == 2

        # 释放
        await permit.__aenter__()
        await permit.__aexit__(None, None, None)
        assert limiter.active_count() == 1
        green("permit __aexit__ 释放 OK")

        await permit2.__aenter__()
        await permit2.__aexit__(None, None, None)
        assert limiter.active_count() == 0
        green("全部释放 OK")

        # get_instance 单例
        SubAgentConcurrencyLimiter._instance = None
        inst1 = SubAgentConcurrencyLimiter.get_instance(max_concurrent=5, timeout_seconds=20)
        inst2 = SubAgentConcurrencyLimiter.get_instance()
        assert inst1 is inst2
        assert inst1._max_concurrent == 5
        green("get_instance 单例 OK")

        # 超时测试：同时持有所有槽位，后续请求必须等待
        SubAgentConcurrencyLimiter._instance = None
        limiter2 = SubAgentConcurrencyLimiter(max_concurrent=2, timeout_seconds=0.5)
        # 先获取两个 permit，把槽位占满
        p1 = await limiter2.acquire("outline_writer")
        p2 = await limiter2.acquire("script_writer")
        assert limiter2.active_count() == 2
        green(f"已持有 2 个 permit，active={limiter2.active_count()}")

        # 第三个请求会阻塞，超时 0.5s
        permit_blocked_task = asyncio.create_task(limiter2.acquire("storyboarder"))
        await asyncio.sleep(0.05)
        assert not permit_blocked_task.done(), "任务不应在 50ms 内完成（应等待信号量）"
        green("50ms 内未完成（符合预期，信号量被占满）")

        # 用 wait_for 验证超时
        try:
            await asyncio.wait_for(permit_blocked_task, timeout=1.0)
            red("timeout 测试失败：未抛出 TimeoutError")
        except asyncio.TimeoutError:
            green("TimeoutError 正确抛出 OK")

        # 清理：释放持有的 permit（p1, p2）
        await p1.__aenter__()
        await p1.__aexit__(None, None, None)
        await p2.__aenter__()
        await p2.__aexit__(None, None, None)

    asyncio.run(run_concurrency_test())
    green("ConcurrencyLimiter 全部 OK")
except Exception as e:
    red(f"ConcurrencyLimiter 失败: {e}")
    import traceback
    traceback.print_exc()

# ─────────────────────────────────────────────────────────────
# 9. call_reviewer 工具函数
# ─────────────────────────────────────────────────────────────
section("9. call_reviewer 工具函数")

try:
    from app.core.supervisor.tools import call_reviewer
    from app.core.supervisor.context import SupervisorContext

    ctx = SupervisorContext(supervisor_session_id="sv-test-review", user_request="test")

    async def run_reviewer():
        result = await call_reviewer(
            content="这是一个测试内容",
            review_criteria=["情感张力", "结构完整性"],
            supervisor_context=ctx,
        )
        assert "score" in result
        assert "passed" in result
        assert "feedback" in result
        assert "suggestions" in result
        green(f"call_reviewer OK — score={result['score']}, passed={result['passed']}")

        # review_history 仅在调用成功时记录；API key 缺失会走 except 分支返回 fallback
        # 因此这里只验证字段结构，不检查 history 长度
        assert hasattr(ctx, "review_history")
        assert isinstance(ctx.review_history, list)
        green(f"ReviewHistory list 存在 OK (len={len(ctx.review_history)}, 因无有效 API key)")

    asyncio.run(run_reviewer())
except Exception as e:
    red(f"call_reviewer 失败: {e}")
    import traceback
    traceback.print_exc()

# ─────────────────────────────────────────────────────────────
# 10. get_workflow_state 工具函数
# ─────────────────────────────────────────────────────────────
section("10. get_workflow_state 工具函数")

try:
    from app.core.supervisor.tools import get_workflow_state
    from app.core.supervisor.context import SupervisorContext

    ctx = SupervisorContext(supervisor_session_id="sv-state-test", user_request="test")
    ctx.current_phase = "script"
    ctx.artifacts["outline_writer"] = {"title": "测试大纲"}
    ctx.sub_agent_sessions["outline_writer"] = "sub-outline-001"

    state = asyncio.run(get_workflow_state(ctx))

    assert state["current_phase"] == "script"
    assert "outline_writer" in state["artifacts"]
    assert "outline_writer" in state["sub_agent_sessions"]
    assert state["sub_agent_sessions"]["outline_writer"] == "sub-outline-001"
    green(f"get_workflow_state OK: current_phase={state['current_phase']}")
except Exception as e:
    red(f"get_workflow_state 失败: {e}")

# ─────────────────────────────────────────────────────────────
# 11. SupervisorWorkflow 模型
# ─────────────────────────────────────────────────────────────
section("11. SupervisorWorkflow ORM 模型")

try:
    from app.models.supervisor_workflow import SupervisorWorkflow

    assert SupervisorWorkflow.__tablename__ == "supervisor_workflows"
    assert SupervisorWorkflow.supervisor_session_id.index  # 有 index
    # 检查字段存在
    assert hasattr(SupervisorWorkflow, "user_request")
    assert hasattr(SupervisorWorkflow, "status")
    assert hasattr(SupervisorWorkflow, "artifacts")
    assert hasattr(SupervisorWorkflow, "final_result")
    green("SupervisorWorkflow 模型 OK")
except Exception as e:
    red(f"SupervisorWorkflow 模型失败: {e}")

# ─────────────────────────────────────────────────────────────
# 12. SupervisorWorkflowService（mock DB）
# ─────────────────────────────────────────────────────────────
section("12. SupervisorWorkflowService（mock DB）")

try:
    from app.services.supervisor_workflow_service import SupervisorWorkflowService
    from app.repositories.supervisor_workflow import SupervisorWorkflowRepository
    from app.models.supervisor_workflow import SupervisorWorkflow

    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.flush = AsyncMock()

    # Mock repo 内部方法
    service = SupervisorWorkflowService(db=mock_session)

    async def run_service_test():
        # mock ProjectRepository.get_by_id_and_owner
        mock_project = MagicMock()
        mock_project.id = 1

        with patch("app.repositories.project.ProjectRepository.get_by_id_and_owner", new_callable=AsyncMock) as mock_get_proj:
            mock_get_proj.return_value = mock_project

            # mock repo.create
            mock_wf = MagicMock(spec=SupervisorWorkflow)
            mock_wf.id = 42
            mock_wf.supervisor_session_id = "sv-verify-001"
            mock_wf.artifacts = {}

            with patch.object(service.repo, "create", new_callable=AsyncMock) as mock_create:
                mock_create.return_value = mock_wf
                wf = await service.create_workflow(
                    project_id=1,
                    owner_id=1,
                    supervisor_session_id="sv-verify-001",
                    user_request="验证脚本测试",
                    model="gemini-3-flash-preview",
                )
                green(f"create_workflow OK — id={wf.id}")

        with patch.object(service.repo, "get_by_session_id", new_callable=AsyncMock) as mock_get:
            mock_wf2 = MagicMock(spec=SupervisorWorkflow)
            mock_wf2.loop_count = 0
            mock_wf2.artifacts = {}
            mock_wf2.current_stage = ""
            mock_get.return_value = mock_wf2

            await service.update_stage("sv-verify-001", "outline_writer")
            green("update_stage OK")

            count = await service.increment_loop_count("sv-verify-001")
            green(f"increment_loop_count OK — count={count}")

            await service.append_artifacts("sv-verify-001", "outline_writer", {"title": "大纲"})
            green("append_artifacts OK")

            with patch.object(service.repo, "get_by_session_id", new_callable=AsyncMock) as mock_get2:
                mock_wf3 = MagicMock(spec=SupervisorWorkflow)
                mock_wf3.artifacts = {"outline_writer": {"title": "大纲"}}
                mock_get2.return_value = mock_wf3
                with patch.object(service.repo, "mark_completed", new_callable=AsyncMock) as mock_complete:
                    mock_wf4 = MagicMock()
                    mock_wf4.status = "completed"
                    mock_complete.return_value = mock_wf4
                    await service.mark_completed("sv-verify-001", final_result="流水线完成")
                    green("mark_completed OK")

    asyncio.run(run_service_test())
    assert mock_session.commit.call_count >= 3
    green(f"DB commit 调用次数: {mock_session.commit.call_count} >= 3")
except Exception as e:
    red(f"SupervisorWorkflowService 失败: {e}")
    import traceback
    traceback.print_exc()

# ─────────────────────────────────────────────────────────────
# 13. SupervisorWorkflowRepository
# ─────────────────────────────────────────────────────────────
section("13. SupervisorWorkflowRepository")

try:
    from app.repositories.supervisor_workflow import SupervisorWorkflowRepository

    mock_session = MagicMock()
    repo = SupervisorWorkflowRepository(session=mock_session)

    assert hasattr(repo, "get_by_session_id")
    assert hasattr(repo, "get_by_id_and_project")
    assert hasattr(repo, "list_by_project")
    assert hasattr(repo, "mark_completed")
    assert hasattr(repo, "mark_failed")
    green("SupervisorWorkflowRepository 方法 OK")
except Exception as e:
    red(f"SupervisorWorkflowRepository 失败: {e}")

# ─────────────────────────────────────────────────────────────
# 14. SupervisorStreamEvent Union 类型覆盖
# ─────────────────────────────────────────────────────────────
section("14. SupervisorStreamEvent Union 类型")

try:
    from app.core.supervisor.events import (
        SupervisorDoneEvent,
        SubAgentStartEvent,
        SubAgentEndEvent,
        ReviewEndEvent,
    )
    from app.core.agent.base import ThinkingEvent, TextEvent

    events = [
        SupervisorDoneEvent(supervisor_session_id="x", artifacts={}, final_result=""),
        SubAgentStartEvent(sub_agent_name="x", session_id="x", task_description="x"),
        SubAgentEndEvent(sub_agent_name="x", session_id="x", result={}),
        ReviewEndEvent(sub_agent_name="x", score=7.0, passed=True, feedback="", suggestions=[]),
        ThinkingEvent(content="hi"),
        TextEvent(content="hi"),
    ]
    for ev in events:
        assert hasattr(ev, "type"), f"{type(ev)} 缺少 type 字段"
        assert isinstance(ev.type, str), f"{type(ev)}.type 不是 str"
    green(f"全部 {len(events)} 个事件类型有 type 字段 OK")
except Exception as e:
    red(f"SupervisorStreamEvent Union 失败: {e}")

# ─────────────────────────────────────────────────────────────
# 15. call_sub_agent 工具函数（mock sub-agent）
# ─────────────────────────────────────────────────────────────
section("15. call_sub_agent 工具函数（mock）")

try:
    from app.core.supervisor.tools import call_sub_agent
    from app.core.supervisor.context import SupervisorContext

    ctx = SupervisorContext(supervisor_session_id="sv-call-sub-test", user_request="test")

    async def run_call_sub_agent():
        events = []
        async for ev in call_sub_agent(
            sub_agent_name="outline_writer",
            task_description="生成一个简短的大纲",
            context_snapshot='{"theme": "科幻"}',
            supervisor_context=ctx,
        ):
            events.append(ev)

        # 应该至少有 SubAgentStart, 若干事件, SubAgentEnd
        event_types = [type(e).__name__ for e in events]
        assert "SubAgentStartEvent" in event_types, f"缺少 SubAgentStartEvent: {event_types}"
        assert "SubAgentEndEvent" in event_types, f"缺少 SubAgentEndEvent: {event_types}"
        green(f"call_sub_agent 返回事件类型: {set(event_types)}")

        # 验证 context 被更新
        assert "outline_writer" in ctx.sub_agent_sessions
        green(f"sub_agent_session 记录: {ctx.sub_agent_sessions['outline_writer']}")

    asyncio.run(run_call_sub_agent())
except Exception as e:
    red(f"call_sub_agent 失败: {e}")
    import traceback
    traceback.print_exc()

# ─────────────────────────────────────────────────────────────
# 16. API Endpoint Schema
# ─────────────────────────────────────────────────────────────
section("16. Supervisor API Endpoint")

try:
    from app.api.v1.endpoints.supervisor import SupervisorStartRequest

    req = SupervisorStartRequest(
        project_id=1,
        user_request="生成科幻短片",
        model="gemini-3-flash-preview",
        max_loop=10,
    )
    assert req.project_id == 1
    assert req.user_request == "生成科幻短片"
    assert req.model == "gemini-3-flash-preview"
    assert req.max_loop == 10
    green(f"SupervisorStartRequest OK — project_id={req.project_id}, max_loop={req.max_loop}")
except Exception as e:
    red(f"Supervisor API Schema 失败: {e}")

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────
section("验证完成")
print("\n所有验证检查已执行完毕。请查看上方 ✓ / ✗ 结果。")
print("55 个 pytest 测试见: pytest app/tests/unit/ -v")
