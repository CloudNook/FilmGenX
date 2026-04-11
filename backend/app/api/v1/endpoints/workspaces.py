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
    ErrorEvent,
)
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
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# 默认 System Prompt
# ---------------------------------------------------------------------------

DEFAULT_SYSTEM_PROMPT = """你是 FilmGenX AI 视频制作助手。你具备专业的影视制作知识，能够帮助用户完成从剧本创作到视频生成的全流程。

你的能力包括：
- 剧本创作与分析
- 角色设计与形象生成
- 场景设计与氛围营造
- 分镜脚本规划
- 运镜设计
- 图片生成提示词编写
- 视频制作指导

当你需要专业领域知识时，使用 load_skill 工具获取对应知识库。
始终用中文回复，保持专业且友好的语气。"""


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
    elif isinstance(event, ErrorEvent):
        return {"type": "error", "error": event.error}
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

@router.post("/{workspace_id}/chat", summary="Agent 流式对话（SSE）")
async def chat_workspace(
    project_id: int,
    workspace_id: int,
    body: WorkspaceChatRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    通过 Agent 框架的 stream() 实现多轮流式对话。

    SSE 事件类型：
      - thinking: Agent 思考过程片段
      - text: Agent 回复文本片段
      - tool_start: 工具开始执行
      - tool_end: 工具执行完毕
      - done: 对话结束（含 usage 统计）
      - error: 执行出错
    """
    await _require_project(project_id, user_id, db)
    ws = await _require_workspace(workspace_id, project_id, db)

    # 确定使用的 prompt
    prompt = ws.system_prompt or DEFAULT_SYSTEM_PROMPT

    # 获取工具 schema
    tools = ToolRegistry.get_all_schemas()

    # 构建 Agent（skill_names 由 Agent 定义绑定，run/stream 时懒加载注入 prompt）
    persist = DBPersistStrategy(db=db)
    tool_executor = ToolExecutor(db=db)

    agent = create_agent(
        agent_name=ws.agent_name,
        session_id=ws.session_id,
        prompt=prompt,
        model=body.model or "gemini-3-flash-preview",
        temperature=body.temperature,
        tools=tools,
        skill_names=ws.skill_names if hasattr(ws, "skill_names") else [],
        persist=persist,
    )
    # 注入 db 到 tool_executor（工具可能需要数据库会话）
    agent._tool_executor = tool_executor

    async def stream_agent() -> AsyncGenerator[str, None]:
        total_tokens_delta = 0

        try:
            async for event in agent.stream(body.content):
                data = _serialize_agent_event(event)
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

                # 累计 token
                if isinstance(event, DoneEvent) and event.result.usage:
                    usage = event.result.usage
                    total_tokens_delta = usage.get("total_tokens") or 0

        except Exception as e:
            logger.exception(f"[Workspace:{workspace_id}] Agent stream error: {e}")
            error_data = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            await db.rollback()

        # 更新 token 统计
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
