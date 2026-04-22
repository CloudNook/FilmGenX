"""Supervisor API endpoints."""

import inspect
import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.core.supervisor.errors import (
    SupervisorInterruptNotFoundError,
    SupervisorInvalidStateError,
    SupervisorSessionNotFoundError,
)
from app.core.supervisor.query import SupervisorQuery
from app.models.project import Project
from app.schemas.base import PageResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_sse_data(payload: Dict[str, Any]) -> str:
    return json.dumps(jsonable_encoder(payload), ensure_ascii=False)


def _to_event_payload(event: Any) -> Dict[str, Any]:
    if hasattr(event, "model_dump"):
        payload = event.model_dump()
    else:
        payload = {"type": "unknown", "repr": str(event)}

    for extra_field in ("source", "session_id"):
        extra_value = getattr(event, extra_field, None)
        if extra_value is not None:
            payload[extra_field] = extra_value

    if payload.get("type") in {
        "thinking",
        "text",
        "tool_start",
        "tool_end",
        "interrupt",
        "error",
    }:
        payload.setdefault("source", "supervisor")

    return payload


def _resolve_user_request(body: "SupervisorStartRequest") -> str:
    return (body.content or body.user_request or "").strip()


async def _ensure_project_access(
    db: AsyncSession,
    project_id: int,
    user_id: int,
) -> None:
    result = db.execute(
        select(Project.id).where(
            Project.id == project_id,
            Project.owner_id == user_id,
            Project.is_deleted.is_(False),
        )
    )
    if inspect.isawaitable(result):
        result = await result

    scalar = result.scalar_one_or_none()
    if inspect.isawaitable(scalar):
        scalar = await scalar

    if scalar is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="项目不存在或无权访问",
        )


class SupervisorResumePayload(BaseModel):
    """Resume payload for a paused supervisor run."""

    action: Literal["approve", "reject"] = Field(
        ...,
        description="approve | reject",
    )
    feedback: Optional[str] = Field(
        None,
        description="Feedback text for a rejected review",
    )


class SupervisorStartRequest(BaseModel):
    """Request body for creating or resuming a supervisor chat stream."""

    project_id: Optional[int] = Field(
        None,
        description="Project id. Required when starting a new run.",
    )
    content: str = Field(
        default="",
        description="Supervisor chat input. Mirrors workspace /chat semantics.",
    )
    user_request: Optional[str] = Field(
        None,
        description="Legacy alias for content.",
    )
    model: str = Field("gemini-3-flash-preview", description="LLM model")
    max_loop: int = Field(30, ge=1, le=100, description="Maximum loop count")
    persist: Optional[str] = Field(
        "db",
        description="Legacy field. Supervisor chat uses database persistence.",
    )
    sub_agent_configs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Sub-agent runtime configuration",
    )
    workflow_profile: str = Field(
        "default",
        description="Workflow profile name",
    )
    auto_run: bool = Field(
        False,
        description="Whether supervisor can continue automatically based on suggestions",
    )
    human_review: bool = Field(False, description="Enable human-in-the-loop")
    review_nodes: Optional[List[str]] = Field(
        None,
        description="Nodes to review. Empty means all reviewable nodes.",
    )
    session_id: Optional[str] = Field(
        None,
        description="Existing supervisor session id when resuming a paused run",
    )
    resume: Optional[SupervisorResumePayload] = Field(
        None,
        description="Resume decision for a paused run",
    )


SupervisorChatRequest = SupervisorStartRequest


class SupervisorInterruptState(BaseModel):
    """Interrupt state response."""

    status: str
    interrupt: Optional[Dict[str, Any]] = None
    workflow: Optional[Dict[str, Any]] = None


class SupervisorWorkflowSummary(BaseModel):
    """Supervisor workflow summary for sidebar lists."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    owner_id: int
    supervisor_session_id: str
    user_request: str
    model: str
    status: str
    workflow_profile: str
    auto_run: bool
    active_node_key: Optional[str] = None
    loop_count: int
    total_tokens: int
    final_result: Optional[str] = None
    error_message: Optional[str] = None
    hitl_enabled: bool
    review_nodes: Optional[List[str]] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SupervisorWorkflowDetail(SupervisorWorkflowSummary):
    """Supervisor workflow detail response."""

    workflow_snapshot: Optional[Dict[str, Any]] = None
    event_history: List[Dict[str, Any]] = Field(default_factory=list)


@router.post(
    "/projects/{project_id}/chat",
    summary="Supervisor chat stream",
    description=(
        "Create a new supervisor run or resume a paused run. "
        "Events are streamed back as SSE, aligned with workspace /chat semantics."
    ),
)
async def chat_supervisor(
    project_id: int,
    body: SupervisorChatRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    request = body.model_copy(update={"project_id": project_id})
    return await _stream_supervisor(request, user_id=user_id, db=db)


async def _stream_supervisor(
    body: SupervisorStartRequest,
    user_id: int,
    db: AsyncSession,
):
    from app.core.agent.base import ResumeDecision
    from app.core.supervisor.factory import create_supervisor

    user_request = _resolve_user_request(body)

    if body.resume is not None and not body.session_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="session_id is required when resume is provided",
        )
    if body.project_id is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="project_id is required when starting a new supervisor run",
        )
    if body.session_id is None and not user_request:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="content is required when starting a new supervisor run",
        )

    await _ensure_project_access(db, body.project_id, user_id)
    supervisor = create_supervisor(
        supervisor_session_id=body.session_id,
        user_request=user_request,
        model=body.model,
        max_loop=body.max_loop,
        persist=None,
        sub_agent_configs=body.sub_agent_configs,
        workflow_profile=body.workflow_profile,
        auto_run=body.auto_run,
        hitl_enabled=body.human_review,
        review_nodes=body.review_nodes,
        db=db,
    )
    supervisor_session_id = getattr(supervisor, "supervisor_session_id", body.session_id)
    resume_decision = (
        ResumeDecision(
            action=body.resume.action,
            feedback=body.resume.feedback,
        )
        if body.resume is not None
        else None
    )
    logger.info(
        "[supervisor/chat] user_id=%s, project_id=%s, user_request=%s..., supervisor_session=%s",
        user_id,
        body.project_id,
        user_request[:50],
        supervisor_session_id,
    )

    try:
        stream_result = supervisor.stream(
            initial_input=user_request,
            project_id=body.project_id,
            owner_id=user_id,
            resume=resume_decision,
            require_existing=body.session_id is not None,
        )
        if inspect.isawaitable(stream_result):
            stream_result = await stream_result
    except (SupervisorInterruptNotFoundError, SupervisorSessionNotFoundError) as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SupervisorInvalidStateError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for event in stream_result:
                payload = _to_event_payload(event)
                yield f"data: {_to_sse_data(payload)}\n\n"

            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.exception("[supervisor/chat] stream error")
            yield f"data: {_to_sse_data({'type': 'error', 'error': str(exc)})}\n\n"
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


@router.get(
    "/projects/{project_id}/workflows",
    response_model=PageResponse[SupervisorWorkflowSummary],
    summary="List supervisor workflow runs",
)
async def list_supervisor_workflows(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _ensure_project_access(db, project_id, user_id)
    items, total = await SupervisorQuery(db).list_workflows(
        project_id=project_id,
        owner_id=user_id,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        items=[SupervisorWorkflowSummary.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/projects/{project_id}/workflows/{workflow_id}",
    response_model=SupervisorWorkflowDetail,
    summary="Get supervisor workflow detail",
)
async def get_supervisor_workflow(
    project_id: int,
    workflow_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _ensure_project_access(db, project_id, user_id)
    detail_record = await SupervisorQuery(db).get_workflow_detail(
        workflow_id=workflow_id,
        project_id=project_id,
        owner_id=user_id,
    )
    if detail_record is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    detail = SupervisorWorkflowDetail.model_validate(detail_record.workflow)
    detail.workflow_snapshot = detail_record.workflow_snapshot
    detail.event_history = detail_record.event_history
    return detail

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
    try:
        state = await SupervisorQuery(db).get_interrupt_state(
            session_id=session_id,
            owner_id=user_id,
        )
    except SupervisorSessionNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except SupervisorInvalidStateError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return SupervisorInterruptState(
        status=state.status,
        interrupt=state.interrupt,
        workflow=state.workflow,
    )
