#!/usr/bin/env python
# coding: utf-8
"""
Supervisor Human-in-the-Loop E2E 测试脚本。

完整流程：用户输入 → Supervisor 调度 → SubAgent 依次执行
  outline_writer → [用户审阅] → script_writer → [用户审阅] → storyboarder → 最终产物

每个 SubAgent 完成后暂停，用户可以：
  - 直接回车 → 通过，继续下一阶段
  - 输入修改意见 → 反馈注入 system prompt，Supervisor 根据反馈调整

前置条件：
  - .env 中配置 GOOGLE_API_KEY（Gemini API）
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ── 路径 & 环境变量 ─────────────────────────────────────────────
BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
_env_path = BACKEND_ROOT / ".env"
if not _env_path.exists():
    _main_backend = BACKEND_ROOT.parent.parent.parent / "backend"
    _env_path = _main_backend / ".env"
load_dotenv(_env_path)

import os
_key = os.environ.get("GOOGLE_API_KEY", "")
if not _key:
    print(f"ERROR: GOOGLE_API_KEY not found. Tried: {_env_path}")
    sys.exit(1)
print(f"GOOGLE_API_KEY loaded: {_key[:8]}...")

# ── 导入 ────────────────────────────────────────────────────────
from app.core.supervisor.factory import create_supervisor
from app.core.supervisor.events import (
    SubAgentStartEvent,
    SubAgentEndEvent,
    SupervisorDoneEvent,
)
from app.core.agent.base import (
    ThinkingEvent,
    TextEvent,
    ToolStartEvent,
    ToolEndEvent,
    ErrorEvent,
    DoneEvent,
    InterruptEvent,
    InterruptConfig,
)

import app.core.tools.supervisor_tools  # noqa: F401


# ── 颜色输出 ────────────────────────────────────────────────────
class C:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    RED = "\033[31m"
    RESET = "\033[0m"


def _tag(color: str, label: str) -> str:
    return f"{color}{C.BOLD}[{label}]{C.RESET}"


# ── 同步 input → 异步桥接 ─────────────────────────────────────
async def ainput(prompt: str) -> str:
    """在 async 上下文中安全读取 stdin。"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: input(prompt))


# ── 事件处理器 ──────────────────────────────────────────────────
async def run_supervisor_pipeline(user_request: str) -> None:
    """执行 Supervisor 流水线，每个 SubAgent 完成后暂停等待用户审阅。"""

    print(f"\n{'='*70}")
    print(f"{C.CYAN}{C.BOLD}  Supervisor Human-in-the-Loop E2E 测试{C.RESET}")
    print(f"{'='*70}")
    print(f"{C.DIM}用户需求: {user_request}{C.RESET}")
    print(f"{C.YELLOW}模式: 每个 SubAgent 完成后暂停等待用户审阅{C.RESET}\n")

    supervisor = create_supervisor(
        user_request=user_request,
        model="gemini-3-flash-preview",
        max_loop=30,
        persist=None,
        interrupt_config=InterruptConfig(
            enabled=True,
            tool_names=["call_sub_agent"],
        ),
    )

    print(f"{_tag(C.BLUE, 'INIT')} session = {supervisor.supervisor_session_id}")
    print()

    t0 = time.perf_counter()
    phase_times: dict[str, float] = {}
    event_counts: dict[str, int] = {}

    def _count(etype: str):
        event_counts[etype] = event_counts.get(etype, 0) + 1

    try:
        async for ev in supervisor.stream(initial_input=user_request):
            ev_type = getattr(ev, "type", type(ev).__name__)
            _count(ev_type)

            # ── 思考 ──
            if isinstance(ev, ThinkingEvent):
                source = getattr(ev, "source", "supervisor")
                print(f"  {_tag(C.DIM, f'THINK:{source}')} {ev.content}")

            # ── 文本 ──
            elif isinstance(ev, TextEvent):
                source = getattr(ev, "source", "supervisor")
                if source == "supervisor":
                    print(f"  {_tag(C.CYAN, 'TEXT')} {ev.content}", end="")
                else:
                    print(f"  {_tag(C.MAGENTA, f'TEXT:{source}')} {ev.content}", end="")

            # ── SubAgent 开始 ──
            elif isinstance(ev, SubAgentStartEvent):
                phase_times[ev.sub_agent_name] = time.perf_counter()
                print(f"\n{_tag(C.GREEN, 'SUB_START')} {C.GREEN}{ev.sub_agent_name}{C.RESET}"
                      f" session={ev.session_id}")
                print(f"  {C.DIM}task: {ev.task_description}{C.RESET}")

            # ── SubAgent 结束 ──
            elif isinstance(ev, SubAgentEndEvent):
                name = ev.sub_agent_name
                elapsed = time.perf_counter() - phase_times.get(name, t0)
                print(f"\n{_tag(C.GREEN, 'SUB_END')}   {C.GREEN}{name}{C.RESET} ({elapsed:.1f}s)")
                if isinstance(ev.result, dict) and "output" in ev.result:
                    print(f"  {C.DIM}output:{C.RESET}\n{ev.result['output']}")

            # ── 中断事件（用户审阅） ──
            elif isinstance(ev, InterruptEvent):
                tool_label = ev.tool_name
                sub_name = ev.context.get("sub_agent_name", tool_label)
                print(f"\n{'─'*70}")
                print(f"{C.YELLOW}{C.BOLD}  审阅: {sub_name} 输出{C.RESET}")
                print(f"{'─'*70}")
                if ev.tool_result and isinstance(ev.tool_result, dict):
                    print(ev.tool_result.get("output", ev.tool_result))
                else:
                    print(ev.tool_result or "(无输出)")
                print(f"{'─'*70}")

                feedback = await ainput(
                    f"{C.YELLOW}请审阅 [{sub_name}]: "
                    f"(回车=通过 / 输入修改意见): {C.RESET}"
                )

                if feedback.strip():
                    print(f"{_tag(C.RED, 'FEEDBACK')} 注入反馈: {feedback}")
                    async for resume_ev in supervisor.resume(
                        action="reject",
                        feedback=feedback.strip(),
                    ):
                        _count(getattr(resume_ev, "type", type(resume_ev).__name__))
                        # Print resumed-stream events for visibility
                        if isinstance(resume_ev, TextEvent):
                            source = getattr(resume_ev, "source", "supervisor")
                            print(f"  {_tag(C.CYAN, f'TEXT:{source}')} {resume_ev.content}", end="")
                        elif isinstance(resume_ev, ThinkingEvent):
                            source = getattr(resume_ev, "source", "supervisor")
                            print(f"  {_tag(C.DIM, f'THINK:{source}')} {resume_ev.content}")
                        elif isinstance(resume_ev, ErrorEvent):
                            print(f"  {_tag(C.RED, 'ERROR')} {resume_ev.error}")
                else:
                    print(f"{_tag(C.GREEN, 'APPROVED')} 通过，继续下一阶段")
                    async for resume_ev in supervisor.resume(action="approve"):
                        _count(getattr(resume_ev, "type", type(resume_ev).__name__))

                print(f"{_tag(C.BLUE, 'RESUMING')} Supervisor 正在接收反馈并继续决策，请稍候...")
                print()

            # ── 工具调用 ──
            elif isinstance(ev, ToolStartEvent):
                source = getattr(ev, "source", "supervisor")
                args_str = json.dumps(ev.arguments, ensure_ascii=False)
                print(f"  {_tag(C.YELLOW, f'TOOL:{source}')} {ev.tool_name}({args_str})")

            elif isinstance(ev, ToolEndEvent):
                source = getattr(ev, "source", "supervisor")
                result_str = json.dumps(ev.result, ensure_ascii=False, default=str) \
                    if isinstance(ev.result, (dict, list)) else str(ev.result)
                print(f"  {_tag(C.YELLOW, f'TOOL_END:{source}')} {ev.tool_name} -> {result_str}")

            # ── Supervisor 完成 ──
            elif isinstance(ev, SupervisorDoneEvent):
                elapsed = time.perf_counter() - t0
                print(f"\n{'='*70}")
                print(f"{C.GREEN}{C.BOLD}  SUPERVISOR DONE{C.RESET}")
                print(f"{'='*70}")
                print(f"  session_id : {ev.supervisor_session_id}")
                print(f"  duration   : {elapsed:.1f}s")
                print(f"  artifacts  : {list(ev.artifacts.keys())}")
                for name, artifact in ev.artifacts.items():
                    artifact_str = json.dumps(artifact, ensure_ascii=False, default=str)
                    print(f"    {C.CYAN}{name}{C.RESET}:")
                    print(f"    {artifact_str}")
                print(f"\n  final_result:")
                print(f"  {ev.final_result}")

            # ── 错误 ──
            elif isinstance(ev, ErrorEvent):
                print(f"\n  {_tag(C.RED, 'ERROR')} {ev.error}")

            # ── Done 事件 ──
            elif isinstance(ev, DoneEvent):
                pass  # 静默处理

            else:
                print(f"  {_tag(C.DIM, ev_type)} {type(ev).__name__}")

    except Exception as e:
        print(f"\n  {_tag(C.RED, 'EXCEPTION')} {e}")
        logger.exception("Pipeline failed")

    # ── 汇总 ──
    elapsed = time.perf_counter() - t0
    print(f"\n{'─'*70}")
    print(f"{C.BOLD}  汇总{C.RESET}")
    print(f"{'─'*70}")
    print(f"  总耗时: {elapsed:.1f}s")
    print(f"  事件统计: {json.dumps(event_counts, ensure_ascii=False)}")
    if supervisor.context.artifacts:
        print(f"  artifacts: {list(supervisor.context.artifacts.keys())}")
    if supervisor.context.metadata:
        print(f"  用户反馈记录: {list(supervisor.context.metadata.keys())}")
    print()


# ── main ────────────────────────────────────────────────────────
async def main():
    user_request = (
        "生成一个 60 秒的科幻短片视频："
        "一位宇航员在火星基地发现一个神秘信号源，"
        "跟随信号来到一座古老的外星遗迹，"
        "在遗迹中找到一块发光的水晶。"
        "风格：电影级画质，暖色调与冷蓝色对比，紧张氛围。"
    )
    await run_supervisor_pipeline(user_request)


if __name__ == "__main__":
    asyncio.run(main())
