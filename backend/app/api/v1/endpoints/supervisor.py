"""Supervisor API endpoints."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.core.agent.persist.db_strategy import DBPersistStrategy
from app.core.agent.persist.models import AgentMessageRecord
from app.db.session import AsyncSessionFactory
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


def _event_stream_session_id(supervisor_session_id: str) -> str:
    return f"{supervisor_session_id}:events"


def _should_persist_synthetic_event(event_type: Optional[str]) -> bool:
    return event_type in {
        "supervisor_started",
        "interrupt",
        "sub_agent_start",
        "sub_agent_end",
        "review_start",
        "review_end",
        "supervisor_done",
        "error",
    }


def _session_marker(payload: Dict[str, Any], supervisor_session_id: str) -> Optional[str]:
    session_id = payload.get("session_id")
    if isinstance(session_id, str):
        return session_id
    if payload.get("type") == "supervisor_done":
        return supervisor_session_id
    return None


def _record_source(
    record: AgentMessageRecord,
    supervisor_session_id: str,
) -> str:
    if record.agent_name:
        return record.agent_name
    if record.session_id == supervisor_session_id:
        return "supervisor"
    return "unknown"


def _record_to_history_events(
    record: AgentMessageRecord,
    supervisor_session_id: str,
) -> List[Dict[str, Any]]:
    metadata = record.extra_metadata or {}
    source = _record_source(record, supervisor_session_id)
    session_id = (
        record.session_id
        if record.session_id.startswith("sub-")
        else None
    )
    events: List[Dict[str, Any]] = []

    if record.role == "event":
        stored_event = metadata.get("event")
        if isinstance(stored_event, dict):
            events.append(stored_event)
        return events

    if record.role == "assistant":
        thinking = metadata.get("thinking")
        if isinstance(thinking, str) and thinking:
            event = {
                "type": "thinking",
                "content": thinking,
                "source": source,
            }
            if session_id:
                event["session_id"] = session_id
            events.append(event)

        if record.content:
            event = {
                "type": "text",
                "content": record.content,
                "source": source,
            }
            if session_id:
                event["session_id"] = session_id
            events.append(event)

        tool_calls = metadata.get("tool_calls")
        if isinstance(tool_calls, list):
            for tool_call in tool_calls:
                if not isinstance(tool_call, dict):
                    continue
                event = {
                    "type": "tool_start",
                    "tool_call_id": tool_call.get("id", ""),
                    "tool_name": tool_call.get("name", ""),
                    "arguments": tool_call.get("arguments", {}) or {},
                    "source": source,
                }
                if session_id:
                    event["session_id"] = session_id
                events.append(event)

        return events

    if record.role == "tool":
        event = {
            "type": "tool_end",
            "tool_call_id": record.tool_call_id or "",
            "tool_name": record.tool_name or "",
            "result": record.content,
            "is_error": False,
            "source": source,
        }
        if session_id:
            event["session_id"] = session_id
        events.append(event)

    return events


async def _append_supervisor_event(
    supervisor_session_id: str,
    payload: Dict[str, Any],
) -> None:
    async with AsyncSessionFactory() as db_session:
        encoded_payload = jsonable_encoder(payload)
        event_session_id = _event_stream_session_id(supervisor_session_id)
        result = await db_session.execute(
            select(AgentMessageRecord.seq)
            .where(AgentMessageRecord.session_id == event_session_id)
            .order_by(AgentMessageRecord.seq.desc())
            .limit(1)
        )
        latest_seq = result.scalar_one_or_none()
        next_seq = (latest_seq or 0) + 1

        record = AgentMessageRecord(
            session_id=event_session_id,
            request_id=supervisor_session_id,
            agent_name=str(encoded_payload.get("source") or "supervisor_event"),
            role="event",
            content=json.dumps(encoded_payload, ensure_ascii=False),
            seq=next_seq,
            extra_metadata={"event": encoded_payload},
            supervisor_session_id=supervisor_session_id,
        )
        db_session.add(record)
        await db_session.commit()


async def _load_supervisor_event_history(
    db: AsyncSession,
    supervisor_session_id: str,
) -> List[Dict[str, Any]]:
    stmt = (
        select(AgentMessageRecord)
        .where(
            AgentMessageRecord.is_deleted.is_(False),
            or_(
                AgentMessageRecord.session_id == supervisor_session_id,
                AgentMessageRecord.supervisor_session_id == supervisor_session_id,
            ),
        )
        .order_by(AgentMessageRecord.created_at.asc(), AgentMessageRecord.id.asc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    events: List[Dict[str, Any]] = []
    for record in records:
        events.extend(_record_to_history_events(record, supervisor_session_id))
    return events


def _extract_usage_metrics(payload: Dict[str, Any]) -> tuple[int, int]:
    if payload.get("type") != "done":
        return 0, 0

    result = payload.get("result")
    if not isinstance(result, dict):
        return 0, 0

    usage = result.get("usage")
    loop_count = result.get("loop_count")
    total_tokens = usage.get("total_tokens") if isinstance(usage, dict) else 0

    return int(loop_count or 0), int(total_tokens or 0)


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
    return await _handle_supervisor_chat(request, user_id=user_id, db=db)


async def _handle_supervisor_chat(
    body: SupervisorStartRequest,
    user_id: int,
    db: AsyncSession,
):
    if body.resume is not None:
        if not body.session_id:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="session_id is required when resume is provided",
            )
        return await _resume_supervisor_stream(
            session_id=body.session_id,
            resume=body.resume,
            user_id=user_id,
            db=db,
        )

    if body.project_id is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="project_id is required when starting a new supervisor run",
        )

    user_request = _resolve_user_request(body)
    if not user_request:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="content is required when starting a new supervisor run",
        )

    if body.session_id:
        return await _continue_supervisor_stream(
            session_id=body.session_id,
            initial_input=user_request,
            body=body,
            user_id=user_id,
            db=db,
        )

    return await _start_supervisor_stream(
        body=body,
        user_request=user_request,
        user_id=user_id,
        db=db,
    )


async def _start_supervisor_stream(
    body: SupervisorStartRequest,
    user_request: str,
    user_id: int,
    db: AsyncSession,
):
    from app.services.supervisor_workflow_service import SupervisorWorkflowService

    service = SupervisorWorkflowService(db)
    supervisor = _create_supervisor(body, user_id=user_id, workflow_service=service)
    workflow_record = None

    try:
        workflow_record = await service.create_workflow(
            project_id=body.project_id,
            owner_id=user_id,
            supervisor_session_id=supervisor.supervisor_session_id,
            user_request=user_request,
            model=body.model,
            workflow_profile=body.workflow_profile,
            auto_run=body.auto_run,
            hitl_enabled=body.human_review,
            review_nodes=body.review_nodes,
        )
        await service.save_workflow_snapshot(
            supervisor_session_id=supervisor.supervisor_session_id,
            workflow_snapshot=(
                supervisor.context.workflow.model_dump()
                if supervisor.context.workflow
                else {}
            ),
        )
    except Exception as exc:
        logger.warning("[supervisor/chat] failed to create workflow record: %s", exc)

    logger.info(
        "[supervisor/chat] user_id=%s, project_id=%s, user_request=%s..., supervisor_session=%s",
        user_id,
        body.project_id,
        user_request[:50],
        supervisor.supervisor_session_id,
    )

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            if workflow_record is not None:
                started_payload = {
                    "type": "supervisor_started",
                    "workflow_id": workflow_record.id,
                    "supervisor_session_id": supervisor.supervisor_session_id,
                    "status": workflow_record.status,
                    "workflow_profile": workflow_record.workflow_profile,
                    "auto_run": workflow_record.auto_run,
                }
                await _append_supervisor_event(
                    supervisor.supervisor_session_id,
                    started_payload,
                )
                yield f"data: {_to_sse_data(started_payload)}\n\n"

            async for event in supervisor.stream(initial_input=user_request):
                payload = _to_event_payload(event)
                yield f"data: {_to_sse_data(payload)}\n\n"

                event_type = payload.get("type")
                if _should_persist_synthetic_event(event_type):
                    await _append_supervisor_event(
                        supervisor.supervisor_session_id,
                        payload,
                    )

                if event_type == "done":
                    loop_count, total_tokens = _extract_usage_metrics(payload)
                    if loop_count > 0:
                        workflow = await service.get_workflow_by_session(
                            supervisor.supervisor_session_id
                        )
                        if workflow is not None:
                            workflow.loop_count = loop_count
                        if total_tokens > 0 and workflow is not None:
                            workflow.total_tokens = total_tokens
                        await db.commit()

                if event_type == "interrupt":
                    try:
                        await service.save_workflow_snapshot(
                            supervisor_session_id=supervisor.supervisor_session_id,
                            workflow_snapshot=(
                                supervisor.context.workflow.model_dump()
                                if supervisor.context.workflow
                                else {}
                            ),
                        )
                        await service.update_status(
                            supervisor.supervisor_session_id,
                            "waiting_review",
                        )
                    except Exception as exc:
                        logger.warning(
                            "[supervisor/chat] failed to update status: %s",
                            exc,
                        )
                elif event_type == "supervisor_done":
                    try:
                        await service.save_workflow_snapshot(
                            supervisor_session_id=supervisor.supervisor_session_id,
                            workflow_snapshot=(
                                supervisor.context.workflow.model_dump()
                                if supervisor.context.workflow
                                else {}
                            ),
                        )
                        await service.mark_completed(
                            supervisor.supervisor_session_id,
                            final_result=payload.get("final_result"),
                        )
                    except Exception as exc:
                        logger.warning(
                            "[supervisor/chat] failed to mark completed: %s",
                            exc,
                        )

            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.exception("[supervisor/chat] stream error")
            try:
                await service.mark_failed(supervisor.supervisor_session_id, str(exc))
                error_payload = {"type": "error", "error": str(exc), "source": "supervisor"}
                await _append_supervisor_event(
                    supervisor.supervisor_session_id,
                    error_payload,
                )
            except Exception as inner_exc:
                logger.warning(
                    "[supervisor/chat] failed to mark failed: %s",
                    inner_exc,
                )
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


async def _continue_supervisor_stream(
    session_id: str,
    initial_input: str,
    body: SupervisorStartRequest,
    user_id: int,
    db: AsyncSession,
):
    from app.services.supervisor_workflow_service import SupervisorWorkflowService

    service = SupervisorWorkflowService(db)
    workflow = await service.get_workflow_by_session(session_id)
    if (
        workflow is None
        or workflow.owner_id != user_id
        or workflow.project_id != body.project_id
    ):
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if workflow.status == "waiting_review":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Session is waiting for review; use resume instead of a new message",
        )

    workflow.status = "running"
    workflow.completed_at = None
    workflow.error_message = None
    workflow.final_result = None
    await db.commit()
    await db.refresh(workflow)

    supervisor = _create_supervisor(
        SupervisorStartRequest(
            project_id=workflow.project_id,
            session_id=session_id,
            content=workflow.user_request,
            user_request=workflow.user_request,
            model=workflow.model,
            max_loop=body.max_loop,
            workflow_profile=workflow.workflow_profile,
            auto_run=workflow.auto_run,
            human_review=workflow.hitl_enabled,
            review_nodes=workflow.review_nodes,
            sub_agent_configs=body.sub_agent_configs,
        ),
        user_id=user_id,
        workflow_service=service,
    )

    if workflow.workflow_snapshot:
        from app.core.supervisor.workflow import WorkflowSnapshot

        supervisor.context.workflow = WorkflowSnapshot.model_validate(
            workflow.workflow_snapshot
        )

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            await _append_supervisor_event(
                session_id,
                {
                    "type": "user_message",
                    "content": initial_input,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            started_payload = {
                "type": "supervisor_started",
                "workflow_id": workflow.id,
                "supervisor_session_id": session_id,
                "status": workflow.status,
                "workflow_profile": workflow.workflow_profile,
                "auto_run": workflow.auto_run,
            }
            await _append_supervisor_event(session_id, started_payload)
            yield f"data: {_to_sse_data(started_payload)}\n\n"

            async for event in supervisor.stream(initial_input=initial_input):
                payload = _to_event_payload(event)
                yield f"data: {_to_sse_data(payload)}\n\n"

                event_type = payload.get("type")
                if _should_persist_synthetic_event(event_type):
                    await _append_supervisor_event(session_id, payload)

                if event_type == "done":
                    loop_count, total_tokens = _extract_usage_metrics(payload)
                    workflow_record = await service.get_workflow_by_session(session_id)
                    if workflow_record is not None:
                        if loop_count > 0:
                            workflow_record.loop_count = loop_count
                        if total_tokens > 0:
                            workflow_record.total_tokens = total_tokens
                        await db.commit()

                if event_type == "interrupt":
                    try:
                        await service.save_workflow_snapshot(
                            supervisor_session_id=session_id,
                            workflow_snapshot=(
                                supervisor.context.workflow.model_dump()
                                if supervisor.context.workflow
                                else {}
                            ),
                        )
                        await service.update_status(session_id, "waiting_review")
                    except Exception as exc:
                        logger.warning(
                            "[supervisor/chat] failed to update status after continue: %s",
                            exc,
                        )
                elif event_type == "supervisor_done":
                    try:
                        await service.save_workflow_snapshot(
                            supervisor_session_id=session_id,
                            workflow_snapshot=(
                                supervisor.context.workflow.model_dump()
                                if supervisor.context.workflow
                                else {}
                            ),
                        )
                        await service.mark_completed(
                            session_id,
                            final_result=payload.get("final_result"),
                        )
                    except Exception as exc:
                        logger.warning(
                            "[supervisor/chat] failed to mark completed after continue: %s",
                            exc,
                        )

            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.exception("[supervisor/chat] continue stream error")
            try:
                await service.mark_failed(session_id, str(exc))
                error_payload = {"type": "error", "error": str(exc), "source": "supervisor"}
                await _append_supervisor_event(session_id, error_payload)
            except Exception as inner_exc:
                logger.warning(
                    "[supervisor/chat] failed to mark failed after continue: %s",
                    inner_exc,
                )
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
    from app.services.supervisor_workflow_service import SupervisorWorkflowService

    service = SupervisorWorkflowService(db)
    items, total = await service.list_workflows(
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
    from app.services.supervisor_workflow_service import SupervisorWorkflowService

    service = SupervisorWorkflowService(db)
    workflow = await service.get_workflow(workflow_id=workflow_id, project_id=project_id)
    if workflow is None or workflow.owner_id != user_id:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    detail = SupervisorWorkflowDetail.model_validate(workflow)
    detail.event_history = await _load_supervisor_event_history(
        db,
        workflow.supervisor_session_id,
    )
    return detail


def _create_supervisor(
    body: SupervisorStartRequest,
    user_id: Optional[int] = None,
    workflow_service=None,
):
    """Create a configured supervisor instance."""
    from app.core.middleware import HumanInTheLoopMiddleware
    from app.core.supervisor.factory import create_supervisor

    persist = DBPersistStrategy(
        session_factory=AsyncSessionFactory,
        supervisor_session_id=body.session_id,
    )

    middlewares = []
    if body.human_review:
        middlewares.append(
            HumanInTheLoopMiddleware(
                auto_tool_list=["get_workflow_state", "call_reviewer"],
                context={"review_sub_agents": body.review_nodes or []},
            )
        )

    return create_supervisor(
        supervisor_session_id=body.session_id,
        user_request=_resolve_user_request(body),
        model=body.model,
        max_loop=body.max_loop,
        persist=persist,
        sub_agent_configs=body.sub_agent_configs,
        workflow_profile=body.workflow_profile,
        auto_run=body.auto_run,
        workflow_service=workflow_service,
        middlewares=middlewares,
    )


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

    service = SupervisorWorkflowService(db)
    workflow = await service.get_workflow_by_session(session_id)
    if workflow is None or getattr(workflow, "owner_id", user_id) != user_id:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if workflow.status != "waiting_review":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Session status is '{workflow.status}', not 'waiting_review'",
        )

    persist = DBPersistStrategy(session_factory=AsyncSessionFactory)
    interrupt_state = await persist.load_interrupt_state(session_id)

    return SupervisorInterruptState(
        status=workflow.status,
        interrupt={
            "tool_name": interrupt_state.tool_name if interrupt_state else None,
            "arguments": interrupt_state.arguments if interrupt_state else {},
            "context": interrupt_state.context if interrupt_state else {},
        },
        workflow=workflow.workflow_snapshot,
    )


async def _resume_supervisor_stream(
    session_id: str,
    resume: SupervisorResumePayload,
    user_id: int,
    db: AsyncSession,
):
    """Resume a paused supervisor pipeline with a review decision."""
    from app.services.supervisor_workflow_service import SupervisorWorkflowService

    service = SupervisorWorkflowService(db)
    workflow = await service.get_workflow_by_session(session_id)
    if workflow is None or getattr(workflow, "owner_id", user_id) != user_id:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if workflow.status != "waiting_review":
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Session status is '{workflow.status}', expected 'waiting_review'",
        )

    await service.update_status(session_id, "running")

    persist = DBPersistStrategy(session_factory=AsyncSessionFactory)
    interrupt_state = await persist.load_interrupt_state(session_id)
    if not interrupt_state:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="No interrupt state found for session",
        )

    supervisor = _create_supervisor(
        SupervisorStartRequest(
            session_id=session_id,
            content=workflow.user_request,
            user_request=workflow.user_request,
            model=workflow.model,
            workflow_profile=workflow.workflow_profile,
            auto_run=workflow.auto_run,
            human_review=workflow.hitl_enabled,
            review_nodes=workflow.review_nodes,
        ),
        user_id=user_id,
        workflow_service=service,
    )

    if workflow.workflow_snapshot:
        from app.core.supervisor.workflow import WorkflowSnapshot

        supervisor.context.workflow = WorkflowSnapshot.model_validate(
            workflow.workflow_snapshot
        )

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for event in supervisor.resume(
                action=resume.action,
                feedback=resume.feedback,
            ):
                payload = _to_event_payload(event)
                yield f"data: {_to_sse_data(payload)}\n\n"

                event_type = payload.get("type")
                if _should_persist_synthetic_event(event_type):
                    await _append_supervisor_event(session_id, payload)

                if event_type == "done":
                    loop_count, total_tokens = _extract_usage_metrics(payload)
                    workflow_record = await service.get_workflow_by_session(session_id)
                    if workflow_record is not None:
                        if loop_count > 0:
                            workflow_record.loop_count = loop_count
                        if total_tokens > 0:
                            workflow_record.total_tokens = total_tokens
                        await db.commit()

                if event_type == "interrupt":
                    try:
                        await service.save_workflow_snapshot(
                            supervisor_session_id=session_id,
                            workflow_snapshot=(
                                supervisor.context.workflow.model_dump()
                                if supervisor.context.workflow
                                else {}
                            ),
                        )
                        await service.update_status(session_id, "waiting_review")
                    except Exception as exc:
                        logger.warning(
                            "[supervisor/chat] failed to update status after resume: %s",
                            exc,
                        )
                elif event_type == "supervisor_done":
                    try:
                        await service.save_workflow_snapshot(
                            supervisor_session_id=session_id,
                            workflow_snapshot=(
                                supervisor.context.workflow.model_dump()
                                if supervisor.context.workflow
                                else {}
                            ),
                        )
                        await service.mark_completed(
                            session_id,
                            final_result=payload.get("final_result"),
                        )
                    except Exception as exc:
                        logger.warning(
                            "[supervisor/chat] failed to mark completed after resume: %s",
                            exc,
                        )

            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.exception("[supervisor/chat] resume stream error")
            try:
                await service.mark_failed(session_id, str(exc))
                error_payload = {"type": "error", "error": str(exc), "source": "supervisor"}
                await _append_supervisor_event(session_id, error_payload)
            except Exception as inner_exc:
                logger.warning(
                    "[supervisor/chat] failed to mark failed after resume: %s",
                    inner_exc,
                )
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
