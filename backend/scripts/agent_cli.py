"""
交互式 Agent CLI — 用于测试 HITL / 中间件 / 持久化。

运行方式：
    cd backend
    python scripts/agent_cli.py

测试场景：
    - HITL: HumanInTheLoopMiddleware 拦截指定工具调用，等待人工确认后继续
    - 中间件: 自定义 before/after/on_loop_start/on_loop_end/finalize_result 钩子
    - 持久化: 消息写入 PostgreSQL（DB），支持 resume 恢复中断会话
    - 全量事件: thinking / text / tool_start / tool_end / interrupt / done / error
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# 将 backend 目录加入 Python 路径（支持 python scripts/agent_cli.py 直接运行）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.agent import DoneEvent, ErrorEvent, TextEvent, ThinkingEvent
from app.core.agent import ToolEndEvent, ToolStartEvent
from app.core.agent.base import AgentResult, InterruptEvent, ResumeDecision
from app.core.agent.persist.db_strategy import DBPersistStrategy
from app.core.middleware import LoggingMiddleware
from app.core.middleware.builtin import HumanInTheLoopMiddleware
from app.core.middleware.chain import AgentMiddleware, MiddlewareContext
from app.core.tools import ToolRegistry
from app.core.tools.examples import *  # noqa: F401, F403

DEFAULT_PROMPT = (
    "你是一个可观测的多轮助手。"
    "当用户的问题需要计算、天气、时间或搜索时，请优先使用工具。"
    "你可以进行内部思考，但面向用户的最终自然语言回答应当简洁、清楚。"
)


# ---------------------------------------------------------------------------
# 自定义中间件：演示所有钩子
# ---------------------------------------------------------------------------

class DebugMiddleware(AgentMiddleware):
    """
    演示中间件所有钩子的调试中间件。

    每个钩子触发时打印一行日志，便于观察中间件在 Agent 循环中的执行时机。
    """

    name = "debug"

    async def before(self, ctx: MiddlewareContext) -> None:
        print(f"\n[MIDDLEWARE:before]  session={ctx.session_id}  input={ctx.initial_input[:50]}...")

    async def after(self, ctx: MiddlewareContext) -> None:
        finished = ctx.result.finished if ctx.result else False
        error = ctx.result.error if ctx.result else None
        print(f"\n[MIDDLEWARE:after]  finished={finished}  error={error}")

    async def on_loop_start(self, ctx: MiddlewareContext) -> None:
        print(f"  [MIDDLEWARE:on_loop_start]  loop={ctx.loop_count}")

    async def on_loop_end(self, ctx: MiddlewareContext) -> None:
        added = len(ctx.loop_messages)
        print(f"  [MIDDLEWARE:on_loop_end]  loop={ctx.loop_count}  added={added}")

    async def before_tool_calls(
        self,
        ctx: MiddlewareContext,
        tool_calls: list,
    ) -> MiddlewareContext:
        for tc in tool_calls:
            print(f"  [MIDDLEWARE:before_tool_calls]  tool={tc.name}  id={tc.id}")
        return ctx

    async def after_tool_calls(
        self,
        ctx: MiddlewareContext,
        tool_calls: list,
        tool_results: list,
    ) -> MiddlewareContext:
        for tr in tool_results:
            print(f"  [MIDDLEWARE:after_tool_calls]  tool={tr.tool_name}  result={str(tr.result)[:60]}")
        return ctx

    async def finalize_result(self, ctx: MiddlewareContext, result: AgentResult) -> AgentResult:
        print(f"\n[MIDDLEWARE:finalize_result]  finished={result.finished}  loop_count={result.loop_count}")
        return result


# ---------------------------------------------------------------------------
# 事件渲染器
# ---------------------------------------------------------------------------

class TurnPrinter:
    """将流式事件打印为适合命令行观察的格式，完整展示所有事件类型。"""

    def __init__(self, show_thinking: bool = True) -> None:
        self._thinking_open = False
        self._text_open = False
        self.saw_thinking = False
        self.saw_interrupt = False
        self.show_thinking = show_thinking

    def _close_open_blocks(self) -> None:
        if self._thinking_open or self._text_open:
            print()
        self._thinking_open = False
        self._text_open = False

    def handle(self, event) -> None:
        # --- 中断事件（最高优先级，打印在最前面）---
        if isinstance(event, InterruptEvent):
            self.saw_interrupt = True
            print(f"\n{'='*60}")
            print(f"[!! INTERRUPT !!]  tool={event.tool_name}  id={event.tool_call_id}")
            print(f"  arguments : {json.dumps(event.arguments, ensure_ascii=False)}")
            print(f"  context   : {json.dumps(event.context, ensure_ascii=False)}")
            print(f"  actions   : {event.available_actions}")
            print(f"  session   : {event.session_id}")
            print(f"{'='*60}")
            return

        # --- LLM 思考过程 ---
        if isinstance(event, ThinkingEvent):
            self.saw_thinking = True
            if not self.show_thinking:
                return
            if self._text_open:
                print()
                self._text_open = False
            if not self._thinking_open:
                print("\n[Thinking] ", end="", flush=True)
                self._thinking_open = True
            print(event.content, end="", flush=True)
            return

        # --- LLM 文本输出 ---
        if isinstance(event, TextEvent):
            if self._thinking_open:
                print()
                self._thinking_open = False
            if not self._text_open:
                print("\n[Assistant] ", end="", flush=True)
                self._text_open = True
            print(event.content, end="", flush=True)
            return

        # --- 其他事件类型 ---
        self._close_open_blocks()

        if isinstance(event, ToolStartEvent):
            args_text = json.dumps(dict(event.arguments), ensure_ascii=False)
            print(f"\n[ToolStart] {event.tool_name}({args_text})")
        elif isinstance(event, ToolEndEvent):
            result_str = (
                json.dumps(event.result, ensure_ascii=False)
                if isinstance(event.result, (dict, list))
                else str(event.result)
            )
            tag = "[ToolEnd] " if not event.is_error else "[ToolEnd:ERROR] "
            print(f"{tag}{event.tool_name} -> {result_str[:120]}")
        elif isinstance(event, ErrorEvent):
            print(f"\n[Error] {event.error}")
        elif isinstance(event, DoneEvent):
            print(f"\n[Done] finished={event.result.finished}  loop={event.result.loop_count}  error={event.result.error}")
        else:
            print(f"\n[Event] {event}")

    def finish(self) -> None:
        self._close_open_blocks()
        if not self.saw_thinking and self.show_thinking:
            print("\n[System] 本轮未收到 ThinkingEvent（模型本轮无思考片段）")
        if not self.saw_interrupt:
            print("[System] 本轮未发生中断")


# ---------------------------------------------------------------------------
# HITL 交互
# ---------------------------------------------------------------------------

class HITLInteraction:
    """
    人工审阅交互器。

    在 interrupt 发生时暂停流式接收，等待用户在 CLI 输入决策，
    然后将决策通过 resume 接口继续执行。
    """

    def __init__(self, printer: TurnPrinter) -> None:
        self.printer = printer
        self.pending_session_id: Optional[str] = None
        self.pending_tool_name: Optional[str] = None

    def on_interrupt(self, event: InterruptEvent) -> bool:
        """返回 True 表示已处理（用户 abort 了），无需 resume。"""
        self.pending_session_id = event.session_id
        self.pending_tool_name = event.tool_name
        return False

    def choose_action(self) -> ResumeDecision:
        """
        引导用户在 CLI 输入决策。

        Returns:
            ResumeDecision
        """
        print()
        print("=" * 60)
        print(f"人工审阅：{self.pending_tool_name}")
        print("=" * 60)
        print("可选操作：")
        print("  1. approve  — 直接通过，继续执行")
        print("  2. reject   — 拒绝此次工具调用")
        print("  3. abort    — 放弃本次请求")
        print()
        while True:
            choice = input("请选择 [1/2/3] (默认 1=approve): ").strip()
            if choice == "" or choice == "1":
                return ResumeDecision(action="approve")
            if choice == "2":
                return ResumeDecision(action="reject")
            if choice == "3":
                return ResumeDecision(action="abort")
            print("无效选择，请重新输入。")


# ---------------------------------------------------------------------------
# Agent 构造
# ---------------------------------------------------------------------------

def build_agent(
    *,
    session_id: str,
    model: str,
    max_loop: int,
    hitl_enabled: bool,
    db_session,
    hitl_tools: Optional[list[str]] = None,
):
    ToolRegistry.discover("app.core.tools.examples")
    tools = [
        tool
        for tool in ToolRegistry.get_all_schemas()
        if tool["name"] not in ("load_skill", "load_skill_lite")
    ]

    middlewares: list[AgentMiddleware] = [
        DebugMiddleware(),
        LoggingMiddleware(),
    ]

    if hitl_enabled:
        middlewares.append(
            HumanInTheLoopMiddleware(
                # auto_tool_list 内的工具直接执行，不在列表内的工具触发人工审阅
                auto_tool_list=hitl_tools,
                context={"note": "测试 HITL，请人工审阅"},
            )
        )

    persist = DBPersistStrategy(db=db_session)

    from app.core.agent import create_agent
    return create_agent(
        agent_name="assistant",
        session_id=session_id,
        prompt=DEFAULT_PROMPT,
        model=model,
        tools=tools,
        max_loop=max_loop,
        persist=persist,
        middlewares=middlewares,
    )


# ---------------------------------------------------------------------------
# DB 工具
# ---------------------------------------------------------------------------

async def clear_session(session_id: str, db) -> None:
    from sqlalchemy import delete
    from app.core.agent.persist.models import AgentMessageRecord

    await db.execute(delete(AgentMessageRecord).where(AgentMessageRecord.session_id == session_id))
    await db.commit()
    print(f"[System] Session cleared: {session_id}")


async def show_session_state(session_id: str, db) -> None:
    from sqlalchemy import select
    from app.core.agent.persist.models import AgentMessageRecord

    rows = (await db.execute(
        select(AgentMessageRecord)
        .where(AgentMessageRecord.session_id == session_id)
        .order_by(AgentMessageRecord.seq)
    )).scalars().all()

    interrupt = (await db.execute(
        select(AgentMessageRecord.extra_metadata)
        .where(
            AgentMessageRecord.session_id == session_id,
            AgentMessageRecord.role == "assistant",
            AgentMessageRecord.is_checkpoint == True,
        )
        .order_by(AgentMessageRecord.seq.desc())
        .limit(1)
    )).scalar_one_or_none()

    print(f"\n--- Session: {session_id} ---")
    print(f"[DB] agent_messages  ->  {len(rows)} 条消息")
    for i, r in enumerate(rows):
        tag = "[CHECKPOINT] " if r.is_checkpoint else ""
        if r.role == "tool":
            status = (r.extra_metadata or {}).get("status")
            if status == "pending_call":
                print(f"  [{i:03d}] {tag}role=tool       status=pending_call  tool={r.tool_name}  arguments={r.content[:80]}")
            else:
                print(f"  [{i:03d}] {tag}role=tool       tool={r.tool_name}  content={r.content[:80]}")
        elif r.role == "assistant":
            tc_names = [tc.get("name") for tc in (r.extra_metadata or {}).get("tool_calls", [])]
            print(f"  [{i:03d}] {tag}role=assistant  content={r.content[:60]}  tools={tc_names}")
        else:
            print(f"  [{i:03d}] {tag}role={r.role}  content={r.content[:80]}")

    if interrupt and interrupt.get("interrupt"):
        intr = interrupt["interrupt"]
        print(f"[DB] interrupt  ->  tool={intr.get('tool_name')}  tool_call_id={intr.get('tool_call_id')}")
    else:
        print("[DB] interrupt  ->  (无中断状态)")


# ---------------------------------------------------------------------------
# 主循环
# ---------------------------------------------------------------------------

async def chat_once(agent, user_input: str, printer: TurnPrinter) -> tuple[AgentResult, bool]:
    """
    执行一轮对话。

    Returns:
        (result, was_interrupted)
    """
    was_interrupted = False
    final_result: Optional[AgentResult] = None

    async for event in agent.stream(user_input):
        printer.handle(event)
        if isinstance(event, InterruptEvent):
            was_interrupted = True
            # interrupt 已打印，调用方负责 resume
        elif isinstance(event, DoneEvent):
            final_result = event.result

    printer.finish()
    return final_result, was_interrupted


async def chat_once_with_resume(agent, hitl: HITLInteraction, user_input: str, printer: TurnPrinter) -> AgentResult:
    """
    完整的一轮：可能发生中断 → 用户决策 → resume → DoneEvent。
    """
    was_interrupted = False

    async for event in agent.stream(user_input):
        printer.handle(event)
        if isinstance(event, InterruptEvent):
            was_interrupted = True
            hitl.on_interrupt(event)
        elif isinstance(event, DoneEvent):
            return event.result

    printer.finish()

    # --- 处理中断 ---
    if was_interrupted:
        decision = hitl.choose_action()

        if decision.action == "abort":
            print("\n[System] 用户放弃本次请求")
            return AgentResult(
                agent_name=agent.config.agent_name,
                error="Aborted by user",
                finished=False,
            )

        # 通过 stream(resume=...) 继续执行
        print(f"\n[System] 执行 resume: action={decision.action}")
        printer2 = TurnPrinter()
        resume_stream = agent.stream("", resume=decision)
        async for event in resume_stream:
            printer2.handle(event)
            if isinstance(event, InterruptEvent):
                # resume 过程中又触发了新中断（少见，但需要支持）
                printer2.finish()
                print("\n[System] resume 过程中又发生中断，递归处理")
                return await chat_once_with_resume(agent, hitl, "", printer2)
            elif isinstance(event, DoneEvent):
                printer2.finish()
                return event.result
        printer2.finish()

    raise RuntimeError("chat_once_with_resume: 未收到 DoneEvent")


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="交互式 Agent CLI — 测试 HITL / 中间件 / 持久化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
    # 普通对话（无 HITL）
    python scripts/agent_cli.py

    # 启用 HITL，仅 get_weather 自动执行，其他工具全部拦截
    python scripts/agent_cli.py --hitl

    # 自动放行 get_weather 和 get_time，其他工具拦截
    python scripts/agent_cli.py --hitl --hitl-tools get_weather get_time

    # 拦截所有工具（慎用）
    python scripts/agent_cli.py --hitl --hitl-tools

    # 保留历史，启动时不清空 DB
    python scripts/agent_cli.py --resume

    # 查看 DB 中的消息状态
    python scripts/agent_cli.py --show-state
""",
    )
    parser.add_argument("--model", default="gemini-3.1-pro-preview", help="LLM 模型")
    parser.add_argument("--max-loop", type=int, default=10, help="Agent 最大循环次数")
    parser.add_argument("--session-id", default=f"cli_{uuid4().hex[:8]}", help="会话 ID")
    parser.add_argument("--resume", action="store_true", help="保留已有 session 历史，不在启动时清空")
    parser.add_argument("--hitl", action="store_true", help="启用 Human-In-The-Loop 中间件")
    parser.add_argument(
        "--hitl-tools",
        nargs="+",
        default=["get_weather"],
        metavar="TOOL",
        help="自动放行的工具名（默认: get_weather）；其他工具均触发人工审阅",
    )
    parser.add_argument("--show-state", action="store_true", help="打印 DB 消息状态后退出")
    parser.add_argument(
        "--no-thinking",
        action="store_true",
        help="不显示 ThinkingEvent 内容（减少噪音）",
    )
    return parser


async def async_main() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    args = build_arg_parser().parse_args()

    from app.db.session import AsyncSessionFactory
    async with AsyncSessionFactory() as db:
        if args.show_state:
            await show_session_state(args.session_id, db)
            return

        agent = build_agent(
            session_id=args.session_id,
            model=args.model,
            max_loop=args.max_loop,
            hitl_enabled=args.hitl,
            hitl_tools=args.hitl_tools,
            db_session=db,
        )

        hitl = HITLInteraction(TurnPrinter(show_thinking=not args.no_thinking))

        print("=" * 72)
        print("Agent CLI")
        print("=" * 72)
        print(f"session-id  : {args.session_id}")
        print(f"model       : {args.model}")
        print(f"max-loop    : {args.max_loop}")
        print(f"HITL        : {'启用（自动放行: ' + ', '.join(args.hitl_tools) + ')' if args.hitl else '关闭'}")
        print(f"persist     : DB")
        print("commands    : /clear 清空会话 | /state 查看 DB 状态 | /exit 退出")
        print()

        if not args.resume:
            await clear_session(args.session_id, db)

        while True:
            try:
                user_input = input("\nYou > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[System] Bye")
                return

            if not user_input:
                continue

            # --- 内置命令 ---
            if user_input.lower() in {"exit", "quit", "/exit", "/quit"}:
                print("[System] Bye")
                return
            if user_input.lower() in {"clear", "/clear"}:
                await clear_session(args.session_id, db)
                continue
            if user_input.lower() in {"state", "/state"}:
                await show_session_state(args.session_id, db)
                continue

            # --- 对话 ---
            printer = TurnPrinter(show_thinking=not args.no_thinking)

            try:
                if args.hitl:
                    result = await chat_once_with_resume(agent, hitl, user_input, printer)
                else:
                    result, _ = await chat_once(agent, user_input, printer)
            except Exception as e:
                print(f"\n[Exception] {e}")
                continue

            if result is None:
                print("\n[System] 未收到 DoneEvent")
                continue

            # --- 打印最终结果 ---
            print("\n" + "=" * 72)
            print("[Final Result]")
            print(f"  finished   : {result.finished}")
            print(f"  loop_count  : {result.loop_count}")
            print(f"  error       : {result.error}")
            print(f"  raw_output  : {result.raw_output}")
            print(f"  schema_data : {json.dumps(result.schema_data, ensure_ascii=False, indent=4) if result.schema_data else 'null'}")
            print(f"  messages    : {len(result.messages)} 条")
            for i, msg in enumerate(result.messages):
                tag = f"[{i:03d}] {msg.role:10s}"
                if msg.tool_name:
                    print(f"  {tag}  tool={msg.tool_name}  {msg.content[:80]}")
                elif msg.thinking:
                    print(f"  {tag}  {msg.content[:80]}  (thinking={msg.thinking[:40]}...)")
                else:
                    print(f"  {tag}  {msg.content[:80]}")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
