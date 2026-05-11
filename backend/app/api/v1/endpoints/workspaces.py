"""
AI 工作台（Workspace）API 端点。

路由前缀：/api/v1/projects/{project_id}/workspaces

核心：通过 Agent 框架的 stream() 实现 SSE 流式多轮对话，
复用 DBPersistStrategy 持久化，复用 agent_messages 表存储消息。
"""

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.core.agent.persist.models import AgentMessageRecord
from app.core.agent import (
    create_agent,
    ThinkingEvent,
    TextEvent,
    ToolStartEvent,
    ToolEndEvent,
    DoneEvent,
    UsageEvent,
    ErrorEvent,
    InterruptEvent,
    ReviewStartEvent,
    ReviewEndEvent,
)
from app.core.agent.reviewer import create_reviewer_agent
from app.core.agent.persist.db_strategy import DBPersistStrategy
from app.core.agent.tool import ToolExecutor
from app.core.tools import ToolRegistry
from app.models.workspace import Workspace
from app.repositories.workspace import WorkspaceRepository
from app.repositories.project import ProjectRepository
from app.schemas.base import PageResponse
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    WorkspaceDetailResponse,
    WorkspaceChatRequest,
    AgentMessageResponse,
    PendingInterrupt,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# 默认 System Prompt
# ---------------------------------------------------------------------------

DEFAULT_SYSTEM_PROMPT = """你是 FilmGenX AI 视频制作助手。你具备专业的影视制作知识，能帮用户从剧本创作走到视频生成全流程。

# 你的能力

- 剧本创作与分析（大纲 / 场景 / 对白）
- 角色设计与形象生成
- 场景设计与氛围营造
- 分镜脚本规划与运镜设计
- 图片 / 视频生成提示词编写
- 项目级长期记忆维护（character / scene / style / outline / script 等 KV）

# 工具调用协议（强约束）

每次调用工具时，必须在**同一轮回复**里完成两件事：

1. 先输出 1-2 句文字，**说清你要调哪个工具、为什么调、期望得到什么**
2. **紧接着、在同一轮里**发起 tool_call

不要把"说明"和"调用"拆成两轮——AgentLoop 看到没 tool_call 会判定循环结束、任务卡死。你要持续工作，必须每次说完意图就立即调。

涉及的工具：
- ``load_skill`` / ``load_skill_reference``：领域知识 / 参考资料
- ``memory_save``：把项目级精确知识写入 KV（character / scene / style / script）
- ``generate_image`` / ``generate_video``：图像 / 视频生成

正例：
> "你想给萧炎做三视图。我先调 ``generate_image`` 出图，模型选 pro 拿高质量。"
> 〔同一轮 immediately 调用 ``generate_image(prompt='萧炎三视图：黑发、玄重尺背身、玄铁色战袍...', model='gemini-3-pro-image-preview', aspect_ratio='9:16')``〕

工具返回 URL 后，下一轮再继续：
> "三视图已出（URL=...）。把它写回 ``character.萧炎.three_view_url``。"
> 〔同一轮 immediately 调用 ``memory_save(...)``〕

反例（禁止）：
- 只输出说明文字、不发起 tool_call —— Agent 立刻退出循环
- 直接 tool_call 没说明 —— 用户无法跟上判断
- 把意图说明留到下一轮才调 —— 同样会卡死

任何动作都要先**讲清意图 + 理由**，但说完立即执行。涉及影视 / 编剧专业知识时同样按协议——先说要 load 哪个 skill，立即调。

# 项目级 Memory（KV 仓库）

每个 project 有一份有限集合的 KV 仓库，跨会话共享：

| kind | key | 关键字段 |
| --- | --- | --- |
| character | 角色名 | appearance / key_skills / three_view_url / reference_image_urls |
| scene | 场景名 | atmosphere / lighting / reference_image_urls |
| style | palette / lighting / composition / mood / camera | description / keywords |
| preference | genre / duration / pacing / format / structure | description |
| outline | main | summary / characters / key_arcs / duration_seconds |
| script | main | summary / scene_count / total_duration_seconds / famous_quotes |

**写入路径**：
- preference / outline：自动从对话抽取，**你不需要手动写**
- character / scene / style / script：你必须按工具调用协议显式调 ``memory_save`` 写入

**召回路径**：每次对话开始前，所有 active KV 自动注入到你的上下文，按 kind 分组。直接消费字段，不要让用户反复重述。

# 风格

始终用中文回复，专业且友好。回答前先看注入的 KV，已有的信息不要让用户重复说。
"""


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

async def _require_project(project_id: int, user_id: int, db: AsyncSession):
    project = await ProjectRepository(db).get_by_id_and_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project


async def _require_workspace(
    workspace_id: int, project_id: int, db: AsyncSession
) -> Workspace:
    ws = await WorkspaceRepository(db).get_by_id_and_project(workspace_id, project_id)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作台不存在")
    return ws


def _serialize_agent_event(event) -> dict:
    """将 Agent 流式事件序列化为 SSE data dict。"""
    if isinstance(event, ThinkingEvent):
        return {"type": "thinking", "content": event.content}
    elif isinstance(event, TextEvent):
        return {"type": "text", "content": event.content}
    elif isinstance(event, ToolStartEvent):
        return {
            "type": "tool_start",
            "tool_call_id": event.tool_call_id,
            "tool_name": event.tool_name,
            "arguments": event.arguments,
        }
    elif isinstance(event, ToolEndEvent):
        return {
            "type": "tool_end",
            "tool_call_id": event.tool_call_id,
            "tool_name": event.tool_name,
            "result": event.result,
            "is_error": event.is_error,
        }
    elif isinstance(event, DoneEvent):
        return {
            "type": "done",
            "usage": event.result.usage,
            "loop_count": event.result.loop_count,
            "finished": event.result.finished,
        }
    elif isinstance(event, UsageEvent):
        return {
            "type": "usage",
            "usage": event.usage,
            "accumulated_usage": event.accumulated_usage,
            "loop_count": event.loop_count,
        }
    elif isinstance(event, ErrorEvent):
        return {"type": "error", "error": event.error}
    elif isinstance(event, InterruptEvent):
        return {
            "type": "interrupt",
            "session_id": event.session_id,
            "tool_name": event.tool_name,
            "tool_call_id": event.tool_call_id,
            "arguments": event.arguments,
            "available_actions": event.available_actions,
            "context": event.context,
        }
    elif isinstance(event, ReviewStartEvent):
        return {
            "type": "review_start",
            "review_round": event.review_round,
            "candidate_preview": event.candidate_preview,
        }
    elif isinstance(event, ReviewEndEvent):
        return {
            "type": "review_end",
            "review_round": event.review_round,
            "score": event.review.score,
            "passed": event.review.passed,
            "feedback": event.review.feedback,
            "suggestions": event.review.suggestions,
        }
    return {"type": "unknown"}


# ---------------------------------------------------------------------------
# Workspace CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=PageResponse[WorkspaceResponse], summary="获取工作台列表")
async def list_workspaces(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    items, total = await WorkspaceRepository(db).get_by_project(
        project_id, page=page, page_size=page_size
    )
    return PageResponse(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新建工作台",
)
async def create_workspace(
    project_id: int,
    body: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)

    from uuid import uuid4
    session_id = f"ws_{uuid4().hex[:16]}"

    ws = await WorkspaceRepository(db).create(
        project_id=project_id,
        title=body.title,
        session_id=session_id,
        system_prompt=body.system_prompt,
    )
    await db.commit()
    return ws


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceDetailResponse,
    summary="获取工作台详情（含历史消息）",
)
async def get_workspace(
    project_id: int,
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    ws = await _require_workspace(workspace_id, project_id, db)

    # 从 agent_messages 表加载历史消息
    stmt = (
        select(AgentMessageRecord)
        .where(AgentMessageRecord.session_id == ws.session_id)
        .order_by(AgentMessageRecord.seq)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    messages = []
    for r in records:
        messages.append(
            AgentMessageResponse(
                role=r.role,
                content=r.content,
                seq=r.seq,
                tool_call_id=r.tool_call_id,
                tool_name=r.tool_name,
                usage=r.usage,
                extra_metadata=r.extra_metadata,
                created_at=r.created_at,
            )
        )

    # 检查是否有待审阅的中断状态
    pending_interrupt = None
    try:
        checkpoint = await DBPersistStrategy(db=db).load_interrupt_state(ws.session_id)
        if checkpoint is not None:
            pending_interrupt = PendingInterrupt(
                tool_name=checkpoint.tool_name,
                tool_call_id=checkpoint.tool_call_id,
                arguments=checkpoint.arguments,
                available_actions=checkpoint.available_actions,
                context=checkpoint.context,
            )
    except Exception:
        pass

    return WorkspaceDetailResponse(
        id=ws.id,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
        project_id=ws.project_id,
        title=ws.title,
        agent_name=ws.agent_name,
        session_id=ws.session_id,
        system_prompt=ws.system_prompt,
        status=ws.status,
        total_tokens=ws.total_tokens,
        last_message_at=ws.last_message_at,
        messages=messages,
        pending_interrupt=pending_interrupt,
    )


@router.patch("/{workspace_id}", response_model=WorkspaceResponse, summary="更新工作台")
async def update_workspace(
    project_id: int,
    workspace_id: int,
    body: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    ws = await _require_workspace(workspace_id, project_id, db)

    data = body.model_dump(exclude_none=True)
    ws = await WorkspaceRepository(db).update(ws, data)
    await db.commit()
    return ws


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除工作台",
)
async def delete_workspace(
    project_id: int,
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    ws = await _require_workspace(workspace_id, project_id, db)
    # 软删除 workspace（agent_messages 通过 session_id 关联，暂不级联删除）
    await WorkspaceRepository(db).soft_delete(ws)
    await db.commit()


# ---------------------------------------------------------------------------
# 核心端点：流式对话
# ---------------------------------------------------------------------------

@router.post("/{workspace_id}/chat", summary="Agent 流式对话（SSE）/ HITL Resume")
async def chat_workspace(
    project_id: int,
    workspace_id: int,
    body: WorkspaceChatRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    通过 Agent 框架的 stream() 实现多轮流式对话，同时支持 HITL Resume。

    普通对话模式：body.resume 为 None，body.content 为用户消息。
    Resume 模式：body.resume 包含 action（approve/reject），content 可为空，
                 Agent 从持久化的中断快照恢复并继续执行。

    SSE 事件类型：
      - thinking: Agent 思考过程片段
      - text: Agent 回复文本片段
      - tool_start: 工具开始执行
      - tool_end: 工具执行完毕
      - interrupt: 工具调用等待人工审阅（HITL）
      - done: 对话结束（含 usage 统计）
      - error: 执行出错
    """
    from app.core.agent.base import ResumeDecision

    await _require_project(project_id, user_id, db)
    ws = await _require_workspace(workspace_id, project_id, db)

    # ── 普通 / Resume Agent 对话模式 ────────────────────────────────
    from app.core.middleware.builtin import HumanInTheLoopMiddleware

    prompt = ws.system_prompt or DEFAULT_SYSTEM_PROMPT
    tools = ToolRegistry.get_all_schemas()

    persist = DBPersistStrategy(db=db)
    tool_executor = ToolExecutor()

    resume = (
        ResumeDecision(action=body.resume.action)
        if body.resume is not None
        else None
    )

    middlewares = []
    hitl_auto_tools = body.hitl_auto_tools
    if hitl_auto_tools is None and ws.hitl_enabled:
        hitl_auto_tools = []
    if hitl_auto_tools is not None:
        middlewares.append(HumanInTheLoopMiddleware(auto_tool_list=hitl_auto_tools))

    enable_review = body.enable_review or ws.review_enabled
    reviewer = (
        create_reviewer_agent(
            criteria=["内容质量", "创意表达", "专业性", "可执行性"],
            min_score=7.0,
            max_revision_rounds=1,
            on_exhausted="accept_last",
        )
        if enable_review
        else None
    )

    # Project-scoped memory: ws.project_id 当 framework 的 domain_id
    memory_config = None
    if ws.memory_enabled:
        from app.memory import build_domain_memory_config

        memory_config = build_domain_memory_config(domain_id=ws.project_id)

    agent = create_agent(
        agent_name=ws.agent_name,
        session_id=ws.session_id,
        prompt=prompt,
        model=body.model or ws.model or "gemini-3-flash-preview",
        temperature=body.temperature if body.temperature is not None else ws.temperature,
        tools=tools,
        skill_names=ws.skill_names if hasattr(ws, "skill_names") else [],
        persist=persist,
        middlewares=middlewares,
        reviewer=reviewer,
        memory=memory_config,
    )
    agent._tool_executor = tool_executor

    async def stream_agent() -> AsyncGenerator[str, None]:
        total_tokens_delta = 0

        try:
            async for event in agent.stream(body.content, resume=resume):
                data = _serialize_agent_event(event)
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

                if isinstance(event, DoneEvent) and event.result.usage:
                    usage = event.result.usage
                    total_tokens_delta = usage.get("total_tokens") or 0

        except Exception as e:
            logger.exception(f"[Workspace:{workspace_id}] Agent stream error: {e}")
            error_data = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            await db.rollback()

        if total_tokens_delta > 0:
            try:
                await WorkspaceRepository(db).update_tokens(workspace_id, total_tokens_delta)
                await db.commit()
            except Exception:
                logger.exception(f"[Workspace:{workspace_id}] Failed to update tokens")

    return StreamingResponse(
        stream_agent(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
