"""
Supervisor 工具：call_sub_agent / call_reviewer / get_workflow_state。
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import uuid4

from app.core.agent.agent import Agent
from app.core.agent.base import AgentConfig, ToolCall
from app.core.agent.factory import create_agent
from app.core.agent.tool import ToolExecutor
from app.core.agent.base import (
    ToolStartEvent,
    ToolEndEvent,
    ThinkingEvent,
    TextEvent,
    DoneEvent,
    ErrorEvent,
)
from app.core.supervisor.context import SupervisorContext
from app.core.supervisor.reviewer import build_reviewer_prompt

logger = logging.getLogger(__name__)

SUB_AGENT_NAMES = {"outline_writer", "script_writer", "storyboarder"}


def _build_call_sub_agent_schema() -> Dict[str, Any]:
    return {
        "name": "call_sub_agent",
        "description": (
            "调用指定的 SubAgent 执行任务，实时返回流式事件。\n"
            "Args:\n"
            "  sub_agent_name: SubAgent 名称，可选值：outline_writer | script_writer | storyboarder\n"
            "  task_description: 给 SubAgent 的具体任务描述（包含角色定义 + 任务 + 参考产物）\n"
            "  context_snapshot: 前序 SubAgent 产物的 JSON 字符串（选择性注入上下文）\n"
            "Returns: 流式事件（SubAgentStart → Thinking/Text/ToolStart/ToolEnd → SubAgentEnd）\n"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sub_agent_name": {
                    "type": "string",
                    "description": "SubAgent 名称：outline_writer | script_writer | storyboarder",
                    "enum": list(SUB_AGENT_NAMES),
                },
                "task_description": {
                    "type": "string",
                    "description": "Supervisor 构造的 prompt：角色 + 具体任务 + 参考产物",
                },
                "context_snapshot": {
                    "type": "string",
                    "description": "前序产物 JSON，供 SubAgent 参考（如大纲 JSON）",
                },
            },
            "required": ["sub_agent_name", "task_description"],
        },
    }


async def call_sub_agent(
    sub_agent_name: str,
    task_description: str,
    context_snapshot: str = "",
    supervisor_context: Optional[SupervisorContext] = None,
    db=None,
) -> AsyncGenerator:
    """
    调用指定的 SubAgent 执行任务，实时 yield 所有流式事件。

    设计要点：
    - SubAgent 不访问 supervisor_context，只通过 task_description 接收必要数据
    - session_id 格式：sub-{agent_name}-{uuid4()[:8]}
    - 流式事件实时透传到 SSE
    """
    from app.core.supervisor.events import SubAgentStartEvent, SubAgentEndEvent

    if sub_agent_name not in SUB_AGENT_NAMES:
        yield SubAgentEndEvent(
            sub_agent_name=sub_agent_name,
            session_id="",
            result={"error": f"Unknown sub_agent_name: {sub_agent_name}"},
        )
        return

    sub_session_id = f"sub-{sub_agent_name}-{str(uuid4())[:8]}"

    sub_prompt = task_description
    if context_snapshot:
        sub_prompt = f"{task_description}\n\n## 参考上下文\n{context_snapshot}"

    sub_agent = create_agent(
        agent_name=sub_agent_name,
        session_id=sub_session_id,
        prompt=sub_prompt,
        model="gemini-3-flash-preview",
        max_loop=20,
        persist="redis",
    )

    if supervisor_context is not None:
        supervisor_context.sub_agent_sessions[sub_agent_name] = sub_session_id

    logger.info(
        f"[call_sub_agent] starting sub_agent={sub_agent_name}, "
        f"session={sub_session_id}"
    )

    yield SubAgentStartEvent(
        sub_agent_name=sub_agent_name,
        session_id=sub_session_id,
        task_description=task_description,
    )

    try:
        accumulated_result = {}

        async for event in sub_agent.stream(initial_input=""):
            if isinstance(event, ThinkingEvent):
                yield ThinkingEvent(content=event.content, source=sub_agent_name)
            elif isinstance(event, TextEvent):
                yield TextEvent(content=event.content, source=sub_agent_name)
            elif isinstance(event, ToolStartEvent):
                yield ToolStartEvent(
                    tool_call_id=event.tool_call_id,
                    tool_name=event.tool_name,
                    arguments=event.arguments,
                    source=sub_agent_name,
                )
            elif isinstance(event, ToolEndEvent):
                yield ToolEndEvent(
                    tool_call_id=event.tool_call_id,
                    tool_name=event.tool_name,
                    result=event.result,
                    is_error=event.is_error,
                    source=sub_agent_name,
                )
            elif isinstance(event, DoneEvent):
                accumulated_result = {
                    "schema_data": event.result.schema_data,
                    "raw_output": event.result.raw_output,
                    "loop_count": event.result.loop_count,
                }
                if supervisor_context is not None:
                    supervisor_context.artifacts[sub_agent_name] = (
                        event.result.schema_data or event.result.raw_output
                    )
                logger.info(
                    f"[call_sub_agent] completed sub_agent={sub_agent_name}, "
                    f"loop_count={event.result.loop_count}"
                )
    except Exception as e:
        logger.exception(f"[call_sub_agent] error in sub_agent={sub_agent_name}: {e}")
        yield ErrorEvent(error=str(e), source=sub_agent_name)
        accumulated_result = {"error": str(e)}

    yield SubAgentEndEvent(
        sub_agent_name=sub_agent_name,
        session_id=sub_session_id,
        result=accumulated_result,
    )


def _build_call_reviewer_schema() -> Dict[str, Any]:
    return {
        "name": "call_reviewer",
        "description": (
            "调用 Reviewer Agent 评估内容质量。\n"
            "Args:\n"
            "  content: 需要评估的内容（文本或 JSON）\n"
            "  review_criteria: 评估维度列表，如：情感张力 | 结构完整性 | 分镜合理性\n"
            "Returns: {score: 0-10, passed: bool, feedback: str, suggestions: []}\n"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "待评估内容"},
                "review_criteria": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "评估维度列表",
                },
            },
            "required": ["content", "review_criteria"],
        },
    }


async def call_reviewer(
    content: str,
    review_criteria: List[str],
    supervisor_context: Optional[SupervisorContext] = None,
    db=None,
) -> Dict[str, Any]:
    """
    调用 Reviewer Agent 评估内容质量。

    Reviewer 是一个标准 Agent，封装在此函数中。
    返回 {score, passed, feedback, suggestions}。
    """
    reviewer_session_id = f"reviewer-{str(uuid4())[:8]}"
    reviewer_prompt = build_reviewer_prompt(content, review_criteria)

    reviewer_agent = create_agent(
        agent_name="reviewer",
        session_id=reviewer_session_id,
        prompt=reviewer_prompt,
        model="gemini-3-flash-preview",
        max_loop=10,
        persist="redis",
    )

    try:
        result = await reviewer_agent.run(initial_input="")
        raw = result.raw_output or ""

        import re

        json_match = re.search(r"\{[\s\S]+\}", raw)
        if json_match:
            review_data = json.loads(json_match.group())
        else:
            review_data = {
                "score": 7.0,
                "passed": True,
                "feedback": raw,
                "suggestions": [],
            }

        score = float(review_data.get("score", 7.0))
        passed = review_data.get("passed", score >= 7.0)

        if supervisor_context is not None:
            from app.core.supervisor.context import ReviewEntry
            supervisor_context.review_history.append(ReviewEntry(
                agent=review_data.get("agent", "unknown"),
                score=score,
                passed=passed,
                feedback=review_data.get("feedback", ""),
                suggestions=review_data.get("suggestions", []),
            ))

        return {
            "score": score,
            "passed": passed,
            "feedback": review_data.get("feedback", ""),
            "suggestions": review_data.get("suggestions", []),
        }
    except Exception as e:
        logger.exception(f"[call_reviewer] error: {e}")
        return {
            "score": 0.0,
            "passed": False,
            "feedback": f"Reviewer 执行失败：{str(e)}",
            "suggestions": [],
        }


def _build_get_workflow_state_schema() -> Dict[str, Any]:
    return {
        "name": "get_workflow_state",
        "description": (
            "查询当前流水线状态和已有产物。\n"
            "Returns: {current_phase, artifacts, review_history}\n"
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }


async def get_workflow_state(
    supervisor_context: SupervisorContext,
) -> Dict[str, Any]:
    """
    查询当前流水线状态。

    供 Supervisor Agent（LLM）做决策参考。
    注意：此工具是给 Supervisor 用的，不是给 SubAgent 用的。
    """
    return {
        "current_phase": supervisor_context.current_phase,
        "artifacts": supervisor_context.artifacts,
        "review_history": [
            r.model_dump() for r in supervisor_context.review_history
        ],
        "sub_agent_sessions": supervisor_context.sub_agent_sessions,
    }


def get_supervisor_tool_schemas() -> List[Dict[str, Any]]:
    """返回所有 Supervisor 工具的 schema 列表。"""
    return [
        _build_call_sub_agent_schema(),
        _build_call_reviewer_schema(),
        _build_get_workflow_state_schema(),
    ]
