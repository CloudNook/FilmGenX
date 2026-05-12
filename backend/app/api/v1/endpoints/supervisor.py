"""Supervisor API endpoints."""

import asyncio
import inspect
import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional
from uuid import uuid4

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
from app.db.session import AsyncSessionFactory
from app.models.project import Project
from app.schemas.base import PageResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Supervisor 后台执行任务表：key=supervisor_session_id，value=asyncio.Task。
# 同一 session 同时只允许一个后台 task（防止双击发送/并发 resume 冲突）；
# 任务完成后回调里清理。模块级 set 同时充当强引用，防止 GC。
_BG_SUPERVISOR_TASKS: Dict[str, "asyncio.Task[None]"] = {}

# Session factory used by background supervisor tasks. Indirected via module
# attribute so unit tests can monkeypatch it without spinning up a real DB.
_bg_session_factory = AsyncSessionFactory


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
        "done",
        "usage",
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
    max_loop: int = Field(50, ge=1, le=100, description="Maximum loop count")
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
    memory_enabled: bool = Field(
        True,
        description=(
            "Global memory toggle. When True (default), supervisor + all sub-agents "
            "automatically attach project-scoped memory using project_id as the "
            "domain_id. Set to False to opt out (e.g. ad-hoc tests, tasks where "
            "long-term memory shouldn't apply)."
        ),
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
    memory_enabled: bool = True
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SupervisorWorkflowDetail(SupervisorWorkflowSummary):
    """Supervisor workflow detail response."""

    workflow_snapshot: Optional[Dict[str, Any]] = None
    event_history: List[Dict[str, Any]] = Field(default_factory=list)
    last_usage: Optional[Dict[str, Any]] = None


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


async def _supervisor_producer(
    queue: "asyncio.Queue[Any]",
    *,
    session_id: str,
    project_id: int,
    user_id: int,
    user_request: str,
    body: SupervisorStartRequest,
    resume_action: Optional[str],
) -> None:
    """后台任务：用独立 db session 跑 supervisor，把事件转给 chat SSE 的 queue。

    与请求生命周期解耦：浏览器刷新/断网导致 chat SSE 中断时，event_stream 这个
    consumer 退出，本任务仍持有自己的 ``async with AsyncSessionFactory()`` 会话，
    继续执行 supervisor 并把事件写进 ``supervisor_events`` 表。用户刷新后通过
    ``/{session_id}/stream`` tail 端点 replay 即可看到完整进度。

    所有 framework 调用（``create_supervisor`` / ``supervisor.stream``）走 core，
    持久化由 core 自己的 runtime/persist 完成，本函数只负责"在后台跑 + 推到 queue"。
    """
    from app.core.agent.base import ResumeDecision
    from app.core.supervisor.factory import create_supervisor
    from app.core.supervisor.persist import SupervisorWorkflowStore

    sentinel_done: Dict[str, Any] = {"__sentinel__": "done"}

    try:
        async with _bg_session_factory() as bg_db:
            supervisor = create_supervisor(
                supervisor_session_id=session_id,
                user_request=user_request,
                model=body.model,
                max_loop=body.max_loop,
                persist=None,
                sub_agent_configs=body.sub_agent_configs,
                workflow_profile=body.workflow_profile,
                auto_run=body.auto_run,
                hitl_enabled=body.human_review,
                review_nodes=body.review_nodes,
                db=bg_db,
                domain_id=project_id,
                memory_enabled=body.memory_enabled,
            )
            resume_decision = (
                ResumeDecision(action=resume_action)
                if resume_action is not None
                else None
            )

            try:
                stream_result = supervisor.stream(
                    initial_input=user_request,
                    project_id=project_id,
                    owner_id=user_id,
                    resume=resume_decision,
                    require_existing=body.session_id is not None,
                )
                if inspect.isawaitable(stream_result):
                    stream_result = await stream_result

                async for event in stream_result:
                    # 事件已由 core supervisor runtime 持久化；这里只是把它转给
                    # 当前活跃的 chat SSE consumer。Queue 满（chat 端慢/断开）时
                    # 直接丢掉——客户端可通过 tail 从 event_store replay 补回。
                    try:
                        queue.put_nowait(event)
                    except asyncio.QueueFull:
                        pass
            except (
                SupervisorInterruptNotFoundError,
                SupervisorSessionNotFoundError,
                SupervisorInvalidStateError,
            ) as exc:
                # 验证类异常：bg task 没法返回 HTTP 4xx，转成 SSE error 事件。
                logger.info(
                    "[supervisor/bg] validation error session=%s: %s",
                    session_id,
                    exc,
                )
                try:
                    queue.put_nowait({"__sentinel__": "error", "error": str(exc)})
                except asyncio.QueueFull:
                    pass
                try:
                    await SupervisorWorkflowStore(bg_db).mark_failed(
                        session_id, str(exc)
                    )
                except Exception:
                    logger.exception(
                        "[supervisor/bg] mark_failed after validation error failed"
                    )
            except asyncio.CancelledError:
                # 唯一应该到这里的场景：应用 shutdown。Bg task 不应该被请求生命周期取消。
                logger.warning(
                    "[supervisor/bg] cancelled session=%s, marking failed",
                    session_id,
                )
                try:
                    await SupervisorWorkflowStore(bg_db).mark_failed(
                        session_id, "supervisor execution cancelled"
                    )
                except Exception:
                    logger.exception("[supervisor/bg] mark_failed on cancel failed")
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("[supervisor/bg] unexpected error session=%s", session_id)
                try:
                    queue.put_nowait({"__sentinel__": "error", "error": str(exc)})
                except asyncio.QueueFull:
                    pass
                try:
                    await SupervisorWorkflowStore(bg_db).mark_failed(session_id, str(exc))
                except Exception:
                    logger.exception("[supervisor/bg] mark_failed on error failed")
    finally:
        try:
            queue.put_nowait(sentinel_done)
        except asyncio.QueueFull:
            pass


async def _stream_supervisor(
    body: SupervisorStartRequest,
    user_id: int,
    db: AsyncSession,
):
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

    # 提前敲定 session_id，让 chat SSE 和 bg task 用同一个 key 协同去重。
    # 新 run：用与 framework factory 一致的 ``sv-<uuid>`` 格式；后续 prepare_stream
    # 不再重新生成。继续 run：尊重客户端传的 session_id。
    session_id = body.session_id or f"sv-{uuid4()}"
    # body 里的 session_id 决定 framework 的 require_existing 分支，所以 bg task
    # 用一份带新 session_id 的 copy（保持原 body.session_id 语义，避免误走 continue
    # 分支）。
    body_for_bg = body.model_copy(update={"session_id": body.session_id})
    resume_action = body.resume.action if body.resume is not None else None

    logger.info(
        "[supervisor/chat] user_id=%s, project_id=%s, user_request=%s..., supervisor_session=%s",
        user_id,
        body.project_id,
        user_request[:50],
        session_id,
    )

    # 去重：同一 session 已有在跑的 bg task → 拒绝并发，避免 prepare_existing_stream
    # race 或事件错序。客户端可改走 tail 端点恢复 SSE。
    existing_task = _BG_SUPERVISOR_TASKS.get(session_id)
    if existing_task is not None and not existing_task.done():
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=(
                f"Supervisor session {session_id} is already running; "
                "subscribe via /supervisor/{session_id}/stream to tail it"
            ),
        )

    # Queue maxsize 限制内存增长。Bg task put_nowait，满了就丢——丢失的事件可通过
    # tail 从 event_store replay 补回。
    queue: "asyncio.Queue[Any]" = asyncio.Queue(maxsize=512)

    task = asyncio.create_task(
        _supervisor_producer(
            queue,
            session_id=session_id,
            project_id=body.project_id,
            user_id=user_id,
            user_request=user_request,
            body=body_for_bg,
            resume_action=resume_action,
        )
    )
    _BG_SUPERVISOR_TASKS[session_id] = task
    task.add_done_callback(lambda _t, sid=session_id: _BG_SUPERVISOR_TASKS.pop(sid, None))

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            while True:
                item = await queue.get()
                if isinstance(item, dict) and item.get("__sentinel__") == "done":
                    break
                if isinstance(item, dict) and item.get("__sentinel__") == "error":
                    yield f"data: {_to_sse_data({'type': 'error', 'error': item.get('error', '')})}\n\n"
                    break
                payload = _to_event_payload(item)
                yield f"data: {_to_sse_data(payload)}\n\n"
            yield "data: [DONE]\n\n"
        except asyncio.CancelledError:
            # 客户端断开（刷新/关 tab）。Bg task 不受影响，继续把事件写进 event_store；
            # 重新连接时走 /{session_id}/stream tail 端点 replay 即可。
            raise

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
    detail.last_usage = detail_record.last_usage
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


@router.get(
    "/{session_id}/stream",
    summary="Tail supervisor event stream",
    description=(
        "SSE 端点：先 replay supervisor_events 表里 id > from_seq 的全部事件，"
        "然后服务端 1 秒一次拉新事件直到 workflow status 进入 completed / failed。"
        "用于刷新页面 / 跨 tab 同步进度，替代轮询。"
    ),
)
async def tail_supervisor_stream(
    session_id: str,
    from_seq: int = Query(0, ge=0, description="只 replay id > 此值的事件；首次连接传 0"),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    import asyncio

    from app.core.supervisor.persist import (
        SupervisorEventStore,
        SupervisorWorkflowStore,
    )

    # 校验 session 归属于本 user
    workflow_store = SupervisorWorkflowStore(db)
    workflow_record = await workflow_store.get_workflow_by_session(
        session_id, owner_id=user_id
    )
    if workflow_record is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Supervisor session {session_id} not found or access denied",
        )

    event_store = SupervisorEventStore(db)

    async def event_stream() -> AsyncGenerator[str, None]:
        last_seq = from_seq
        terminal_states = {"completed", "failed"}

        # 一次性 replay 历史
        try:
            history = await event_store.list_events_after(session_id, last_seq, limit=5000)
            for ev in history:
                payload = dict(ev.payload or {})
                payload["_seq"] = ev.id  # 前端可以用 _seq 做下次 from_seq
                yield f"data: {_to_sse_data(payload)}\n\n"
                last_seq = ev.id
        except Exception as exc:
            logger.exception("[supervisor/stream] replay failed")
            yield f"data: {_to_sse_data({'type': 'error', 'error': f'replay failed: {exc}'})}\n\n"

        # tail：每 1 秒拉一次新事件
        idle_ticks = 0
        max_idle_ticks = 600  # 10 分钟无新事件 → 自动断开（防止永久挂连接）
        while True:
            await asyncio.sleep(1.0)

            try:
                fresh = await event_store.list_events_after(session_id, last_seq, limit=200)
            except Exception as exc:
                logger.exception("[supervisor/stream] tail poll failed")
                yield f"data: {_to_sse_data({'type': 'error', 'error': f'tail poll failed: {exc}'})}\n\n"
                break

            if fresh:
                idle_ticks = 0
                for ev in fresh:
                    payload = dict(ev.payload or {})
                    payload["_seq"] = ev.id
                    yield f"data: {_to_sse_data(payload)}\n\n"
                    last_seq = ev.id
            else:
                idle_ticks += 1

            # 检查 run 是否结束
            wf = await workflow_store.get_workflow_by_session(session_id, owner_id=user_id)
            if wf is None or wf.status in terminal_states:
                break

            if idle_ticks >= max_idle_ticks:
                logger.info(
                    "[supervisor/stream] idle too long, closing tail for session=%s",
                    session_id,
                )
                break

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
