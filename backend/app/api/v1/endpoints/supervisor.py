"""
Supervisor 流式 API 端点。

路由前缀：/api/v1/supervisor
权限：需登录用户
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# 请求 / 响应 Schema
# ---------------------------------------------------------------------------

class SupervisorStartRequest(BaseModel):
    """启动 Supervisor 流水线请求。"""
    project_id: int = Field(..., description="所属项目 ID（用于流水线记录）")
    user_request: str = Field(..., description="用户原始需求描述")
    model: str = Field("gemini-3-flash-preview", description="LLM 模型")
    max_loop: int = Field(30, ge=1, le=100, description="最大循环次数")
    persist: Optional[str] = Field(
        "redis",
        description="持久化策略：'redis' | None",
    )
    sub_agent_configs: Dict[str, Any] = Field(
        default_factory=dict,
        description="SubAgent 配置映射（预留）",
    )
    human_review: bool = Field(False, description="Enable human-in-the-loop")
    review_nodes: Optional[List[str]] = Field(None, description="Nodes to review (empty = all)")


class SupervisorResumeRequest(BaseModel):
    """Resume Supervisor pipeline after human review."""
    action: Literal["approve", "reject", "skip"] = Field(
        ...,
        description="approve | reject | skip",
    )
    feedback: Optional[str] = Field(None, description="Feedback text (for reject)")


class SupervisorInterruptState(BaseModel):
    """Interrupt state response."""
    status: str
    interrupt: Optional[Dict[str, Any]] = None
    artifacts: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# 流式端点
# ---------------------------------------------------------------------------

@router.post(
    "/stream",
    summary="启动 Supervisor 流水线（流式 SSE）",
    description="""
创建 SupervisorAgent，流式返回所有事件（Thinking/Text/SubAgent/Review/Done）。

前端按 `event.type` 渲染对应 UI 区块。
    """,
)
async def start_supervisor_pipeline(
    body: SupervisorStartRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    启动 Supervisor 视频生成流水线，流式返回 SSE 事件。

    权限：任何已登录用户均可调用。
    """
    from app.services.supervisor_workflow_service import SupervisorWorkflowService

    service = SupervisorWorkflowService(db)
    workflow_service = service  # SupervisorWorkflowService 实例，供 call_sub_agent 持久化

    supervisor = _create_supervisor(body, user_id, workflow_service)

    # 在流式开始前创建 DB 记录（使用与 supervisor 相同的 session_id）
    try:
        await service.create_workflow(
            project_id=body.project_id,
            owner_id=user_id,
            supervisor_session_id=supervisor.supervisor_session_id,
            user_request=body.user_request,
            model=body.model,
        )
        await db.commit()
        logger.info(
            f"[supervisor/stream] workflow created: session={supervisor.supervisor_session_id}"
        )
    except Exception as e:
        logger.warning(f"[supervisor/stream] failed to create workflow record: {e}")
        # 不阻断流式，workflow 记录是可选的

    logger.info(
        f"[supervisor/stream] user_id={user_id}, project_id={body.project_id}, "
        f"user_request={body.user_request[:50]}..., supervisor_session={supervisor.supervisor_session_id}"
    )

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for event in supervisor.stream(initial_input=body.user_request):
                # 所有事件统一转为 JSON 行
                if hasattr(event, "model_dump"):
                    payload = event.model_dump()
                else:
                    # 兜底：未知事件类型直接转 str
                    payload = {"type": "unknown", "repr": str(event)}

                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                # Mark workflow as waiting_review on interrupt
                if payload.get("type") == "interrupt":
                    try:
                        await service.update_status(
                            supervisor.supervisor_session_id, "waiting_review"
                        )
                        await db.commit()
                    except Exception as e:
                        logger.warning(f"[supervisor/stream] failed to update status: {e}")

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.exception("[supervisor/stream] stream error")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


def _create_supervisor(body: SupervisorStartRequest, user_id: int, workflow_service):
    """
    创建 SupervisorAgent 实例。

    延迟导入以避免循环依赖。
    """
    from app.core.supervisor.factory import create_supervisor
    from app.core.middleware import HumanInTheLoopMiddleware

    persist: Any = None
    if body.persist and body.persist != "none":
        persist = body.persist  # "redis" → factory 内部解析

    middlewares = []

    # HITL：需要审阅时，传入 HumanInTheLoopMiddleware
    if body.human_review:
        middlewares.append(
            HumanInTheLoopMiddleware(
                white_tool_list=["call_sub_agent"],
                context={"review_sub_agents": body.review_nodes or []},
            )
        )

    return create_supervisor(
        user_request=body.user_request,
        model=body.model,
        max_loop=body.max_loop,
        persist=persist,
        sub_agent_configs=body.sub_agent_configs,
        workflow_service=workflow_service,
        middlewares=middlewares,
    )


# ---------------------------------------------------------------------------
# HITL endpoints: state query + resume
# ---------------------------------------------------------------------------

@router.get(
    "/{session_id}/state",
    summary="Query interrupt state",
)
async def get_interrupt_state(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return current interrupt state for a paused pipeline."""
    from app.services.supervisor_workflow_service import SupervisorWorkflowService
    from fastapi import HTTPException, status as http_status

    service = SupervisorWorkflowService(db)
    workflow = await service.get_workflow_by_session(session_id)
    if not workflow:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Session not found")
    if workflow.status != "waiting_review":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Session status is '{workflow.status}', not 'waiting_review'",
        )

    from app.core.agent.persist.redis_strategy import RedisPersistStrategy
    persist = RedisPersistStrategy()
    interrupt_state = await persist.load_interrupt_state(session_id)

    return SupervisorInterruptState(
        status=workflow.status,
        interrupt={
            "tool_name": interrupt_state.tool_name if interrupt_state else None,
            "arguments": interrupt_state.arguments if interrupt_state else {},
            "context": interrupt_state.context if interrupt_state else {},
        },
        artifacts=workflow.artifacts,
    )


@router.post(
    "/{session_id}/resume",
    summary="Resume pipeline after human review",
)
async def resume_supervisor_pipeline(
    session_id: str,
    body: SupervisorResumeRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused Supervisor pipeline with human review decision."""
    from app.services.supervisor_workflow_service import SupervisorWorkflowService
    from fastapi import HTTPException, status as http_status

    service = SupervisorWorkflowService(db)
    workflow = await service.get_workflow_by_session(session_id)
    if not workflow:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Session not found")
    if workflow.status != "waiting_review":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Session status is '{workflow.status}', expected 'waiting_review'",
        )

    await service.update_status(session_id, "running")
    await db.commit()

    from app.core.agent.persist.redis_strategy import RedisPersistStrategy
    from app.core.supervisor.factory import create_supervisor

    persist = RedisPersistStrategy()
    interrupt_state = await persist.load_interrupt_state(session_id)
    if not interrupt_state:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="No interrupt state found for session",
        )

    supervisor = create_supervisor(
        user_request=workflow.user_request,
        model=workflow.model,
        persist="redis",
    )

    if workflow.artifacts:
        supervisor.context.artifacts.update(workflow.artifacts)

    async def event_stream():
        try:
            async for event in supervisor.resume(
                action=body.action,
                feedback=body.feedback,
            ):
                if hasattr(event, "model_dump"):
                    payload = event.model_dump()
                else:
                    payload = {"type": "unknown", "repr": str(event)}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                # Update workflow status on next interrupt or completion
                if payload.get("type") == "interrupt":
                    try:
                        await service.update_status(session_id, "waiting_review")
                        await db.commit()
                    except Exception as e:
                        logger.warning(f"[supervisor/resume] failed to update status: {e}")

            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.exception("[supervisor/resume] stream error")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
