"""端到端真实 LLM + 真实 DB 持久化：think → tool → HITL → resume → final 链路。

通过 ``create_agent`` + ``HumanInTheLoopMiddleware`` + ``DBPersistStrategy`` 真实
调用 Gemini API 并把消息 / interrupt checkpoint 落到 PostgreSQL ``agent_messages``
表。测试结束后**不清理**数据，方便直接查表确认。

环境要求：
- ``backend/.env`` 配置了 ``GOOGLE_API_KEY``
- PostgreSQL 可达（``DATABASE_URL`` 默认 ``postgresql+asyncpg://postgres:postgres@localhost:5432/filmgenx``）
- ``alembic upgrade head`` 已执行（``agent_messages`` 表存在）

任一条件不满足 → 整个文件 skip。

跑测试：

    cd backend
    uv run pytest tests/unit/core/agent/test_agent_loop_real_llm.py -v -s

跑完后 ``-s`` 会打印出本次使用的 ``session_id``，例如 ``hitl-e2e-1714987654``。
查表确认数据：

    uv run python -c "
    import asyncio
    from sqlalchemy import text
    from app.db.session import AsyncSessionFactory

    async def main():
        async with AsyncSessionFactory() as db:
            r = await db.execute(text('''
                SELECT seq, role, tool_name, is_checkpoint, left(content, 60) AS content
                FROM agent_messages WHERE session_id = :sid ORDER BY seq
            '''), {'sid': 'hitl-e2e-XXX'})
            for row in r:
                print(row)
    asyncio.run(main())
    "
"""

from __future__ import annotations

import os
import time

import pytest

from app.core.agent import ResumeDecision, create_agent
from app.core.agent.persist.db_strategy import DBPersistStrategy
from app.core.middleware.builtin import HumanInTheLoopMiddleware
from app.core.tools.registry import ToolRegistry, register_tool
from app.db.session import AsyncSessionFactory


def _google_api_key_available() -> bool:
    if os.environ.get("GOOGLE_API_KEY"):
        return True
    try:
        from app.core.config import settings
        return bool(settings.GOOGLE_API_KEY)
    except Exception:
        return False


async def _db_reachable() -> bool:
    from sqlalchemy import text
    try:
        async with AsyncSessionFactory() as db:
            await db.execute(text("SELECT 1 FROM agent_messages LIMIT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _google_api_key_available(),
    reason="GOOGLE_API_KEY not configured; skipping real-LLM end-to-end test",
)


@register_tool(
    name="calculate",
    description="执行简单算术表达式并返回字符串结果。仅支持数字和 + - * / ( ) 空格。",
)
def calculate(expression: str) -> str:
    allowed = set("0123456789+-*/(). ")
    if any(ch not in allowed for ch in expression):
        return f"error: 非法字符: {expression!r}"
    return str(eval(expression, {"__builtins__": {}}, {}))


async def test_agent_loop_hitl_interrupt_then_resume_with_db_persist():
    if not await _db_reachable():
        pytest.skip("PostgreSQL not reachable (DATABASE_URL / agent_messages 表)；skipping DB e2e")

    # 用时间戳隔离每次跑的 session，保证第二次 run() 看到的历史只来自当前 session
    session_id = f"hitl-e2e-{int(time.time())}"
    print(f"\n[real-llm-db-test] session_id = {session_id}")

    persist = DBPersistStrategy(session_factory=AsyncSessionFactory)

    def _build():
        return create_agent(
            agent_name="math_writer",
            session_id=session_id,
            prompt=(
                "你是严谨助手。涉及算术问题必须调用 `calculate` 工具，不要心算。"
                "拿到结果后用一句话告诉用户答案。"
            ),
            tools=[ToolRegistry.get("calculate").get_schema()],
            middlewares=[HumanInTheLoopMiddleware(auto_tool_list=[])],  # 任何工具都触发 HITL
            persist=persist,
            max_loop=5,
        )

    # ── 1. 首次 run：HITL 拦截，落 checkpoint 到 DB ──────────────────────────
    first = await _build().run("帮我算一下 1234 * 5678 是多少？")

    assert first.finished is False
    assert first.error == "interrupted"

    pending = await persist.load_interrupt_state(session_id)
    assert pending is not None
    assert pending.tool_name == "calculate"

    # 校验 DB 里有 user + 一条 is_checkpoint=True 的 assistant，且 tool_calls metadata 含 pending tool_call_id
    history = await persist.load_messages(session_id)
    roles_after_first = [m.role for m in history]
    assert "user" in roles_after_first
    assert "assistant" in roles_after_first
    ck_msg = next(m for m in history if m.is_checkpoint)
    tool_calls = (ck_msg.extra_metadata or {}).get("tool_calls") or []
    assert any(tc.get("id") == pending.tool_call_id for tc in tool_calls)

    # ── 2. resume(approve)：从 DB load checkpoint → 执行 pending tool → 拿到 final ──
    second = await _build().run("", resume=ResumeDecision(action="approve"))

    assert second.finished is True, second.error
    assert second.error is None
    # checkpoint 已被清理：load_interrupt_state 不再返回快照
    assert await persist.load_interrupt_state(session_id) is None

    # tool 在 resume 路径真正被执行
    tool_msgs = [m for m in second.messages if m.role == "tool"]
    assert any(m.tool_name == "calculate" for m in tool_msgs), second.messages
    expected = str(1234 * 5678)
    assert expected in " ".join(m.content for m in tool_msgs)
    assert (expected in second.raw_output) or (f"{1234 * 5678:,}" in second.raw_output)

    # 最终 DB 里至少有 user / assistant(checkpoint cleared) / tool / assistant(final) 四类
    final_history = await persist.load_messages(session_id)
    final_roles = [m.role for m in final_history]
    assert final_roles.count("user") >= 1
    assert final_roles.count("assistant") >= 2  # 中断的 + final
    assert final_roles.count("tool") >= 1

    print(f"[real-llm-db-test] DB rows for session={session_id}: {len(final_history)}")
    for m in final_history:
        snippet = (m.content or "").replace("\n", " ")[:60]
        print(f"  seq={m.seq} role={m.role} tool={m.tool_name} ckpt={m.is_checkpoint} | {snippet}")
