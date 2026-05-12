"""Supervisor runtime lifecycle orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
import inspect
from typing import TYPE_CHECKING
from typing import Any, Dict, Optional

from app.core.agent.base import ResumeDecision
from app.core.agent.persist.db_strategy import DBPersistStrategy
from app.core.supervisor.errors import (
    SupervisorInterruptNotFoundError,
    SupervisorInvalidStateError,
    SupervisorSessionNotFoundError,
)
from app.core.supervisor.events import SupervisorStartedEvent
from app.core.supervisor.persist import SupervisorEventStore, SupervisorWorkflowStore
from app.core.supervisor.workflow import WorkflowNodeDefinition, WorkflowSnapshot

if TYPE_CHECKING:
    from app.core.agent.base import AgentCheckpoint


def _should_persist_synthetic_event(event_type: Optional[str]) -> bool:
    """直接持久化（非聚合）的事件类型。

    ``thinking`` / ``text`` 走聚合路径——在 ``usage`` 事件时把本次 LLM 调用
    累积的 chunks 合成一条完整事件后再写表，避免 per-chunk INSERT 写放大。
    """
    return event_type in {
        "supervisor_started",
        "interrupt",
        "sub_agent_start",
        "sub_agent_end",
        "review_start",
        "review_end",
        "supervisor_done",
        "error",
        "tool_start",
        "tool_end",
        "usage",
    }


def _extract_usage_delta(payload: Dict[str, Any]) -> int:
    """从 ``usage`` 事件抽这次 LLM 调用的 ``total_tokens`` 增量。"""
    if payload.get("type") != "usage":
        return 0
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return 0
    return int(usage.get("total_tokens") or 0)


def _extract_loop_count(payload: Dict[str, Any]) -> int:
    """从 ``done``（supervisor 自己的最终事件）抽 loop_count。"""
    if payload.get("type") != "done":
        return 0
    result = payload.get("result")
    if not isinstance(result, dict):
        return 0
    return int(result.get("loop_count") or 0)


def _workflow_definitions(supervisor: Any) -> list[WorkflowNodeDefinition] | None:
    context = getattr(supervisor, "context", None)
    if context is None:
        return None
    definitions = getattr(context, "workflow_definitions", None)
    return definitions if isinstance(definitions, list) else None


class PreparedSupervisorStream:
    """Resolved runtime inputs for a supervisor stream request."""

    def __init__(
        self,
        *,
        workflow_record: Any | None = None,
        stream_input: str,
        pending_user_message: str | None = None,
        emit_started_event: bool = False,
        resume_decision: ResumeDecision | None = None,
    ) -> None:
        self.workflow_record = workflow_record
        self.stream_input = stream_input
        self.pending_user_message = pending_user_message
        self.emit_started_event = emit_started_event
        self.resume_decision = resume_decision


class SupervisorRuntime:
    """Owns supervisor workflow/event persistence for a single request lifecycle."""

    def __init__(
        self,
        workflow_store: SupervisorWorkflowStore,
        event_store: Optional[SupervisorEventStore] = None,
    ) -> None:
        self.workflow_store = workflow_store
        self.db = workflow_store.db
        self.event_store = event_store or SupervisorEventStore(self.db)
        # 流式聚合 buffer：per-(source, session_id) 累积本次 LLM 调用内的
        # thinking / text chunks。在 ``usage`` 事件（= LLM call 结束）时 flush
        # 成一条完整事件持久化，避免 per-chunk INSERT 的写放大。
        self._thinking_buffer: Dict[tuple, str] = {}
        self._text_buffer: Dict[tuple, str] = {}

    async def _create_workflow_record(
        self,
        *,
        project_id: int,
        owner_id: int,
        supervisor: Any,
        user_request: str,
        model: str,
        workflow_profile: str,
        auto_run: bool,
        hitl_enabled: bool,
        review_nodes: Optional[list[str]],
        memory_enabled: bool,
    ) -> Any:
        workflow = await self.workflow_store.create_workflow(
            project_id=project_id,
            owner_id=owner_id,
            supervisor_session_id=supervisor.supervisor_session_id,
            user_request=user_request,
            model=model,
            workflow_profile=workflow_profile,
            auto_run=auto_run,
            hitl_enabled=hitl_enabled,
            review_nodes=review_nodes,
            memory_enabled=memory_enabled,
        )
        await self.save_snapshot(
            supervisor.supervisor_session_id,
            supervisor.context.workflow,
            _workflow_definitions(supervisor),
        )
        return workflow

    async def save_snapshot(
        self,
        supervisor_session_id: str,
        workflow: Optional[WorkflowSnapshot],
        workflow_definitions: list[WorkflowNodeDefinition] | None = None,
    ) -> None:
        if workflow is None:
            return
        await self.workflow_store.save_workflow_state(
            supervisor_session_id=supervisor_session_id,
            workflow_snapshot=workflow,
            workflow_definitions=workflow_definitions,
        )

    async def hydrate_supervisor(
        self,
        workflow_record: Any,
        supervisor: Any,
    ) -> None:
        apply_runtime = getattr(supervisor, "apply_workflow_runtime", None)
        if callable(apply_runtime):
            apply_runtime(workflow_record)

        workflow_state = await self.workflow_store.load_workflow_state(workflow_record)
        if workflow_state is not None:
            supervisor.context.workflow = workflow_state

    async def load_interrupt_checkpoint(
        self,
        supervisor_session_id: str,
    ) -> "AgentCheckpoint | None":
        return await DBPersistStrategy(db=self.db).load_interrupt_state(
            supervisor_session_id
        )

    async def prepare_existing_stream(
        self,
        workflow_record: Any,
        *,
        user_message: str,
        resume: ResumeDecision | None,
    ) -> PreparedSupervisorStream:
        supervisor_session_id = getattr(workflow_record, "supervisor_session_id", None)
        if not isinstance(supervisor_session_id, str) or not supervisor_session_id:
            raise SupervisorInvalidStateError("Workflow is missing supervisor_session_id")

        if resume is not None:
            if workflow_record.status != "waiting_review":
                raise SupervisorInvalidStateError(
                    f"Session status is '{workflow_record.status}', expected 'waiting_review'"
                )
            checkpoint = await self.load_interrupt_checkpoint(
                supervisor_session_id
            )
            if checkpoint is None:
                raise SupervisorInterruptNotFoundError(
                    f"No interrupt state found for session {supervisor_session_id}"
                )

            await self.prepare_existing_workflow(
                workflow_record,
                clear_terminal_state=False,
            )
            return PreparedSupervisorStream(
                workflow_record=workflow_record,
                stream_input="",
                resume_decision=resume,
            )

        if not user_message:
            raise SupervisorInvalidStateError(
                "content is required when sending a new supervisor message"
            )
        if workflow_record.status == "waiting_review":
            raise SupervisorInvalidStateError(
                "Session is waiting for review; provide a decision instead of a new message"
            )

        await self.prepare_existing_workflow(
            workflow_record,
            clear_terminal_state=True,
        )
        return PreparedSupervisorStream(
            workflow_record=workflow_record,
            stream_input=user_message,
            pending_user_message=user_message,
            emit_started_event=True,
        )

    async def prepare_stream(
        self,
        supervisor: Any,
        *,
        project_id: int,
        owner_id: int,
        initial_input: str,
        resume: ResumeDecision | None,
        allow_create: bool = True,
    ) -> PreparedSupervisorStream:
        workflow_record = await self.workflow_store.get_workflow_by_session(
            supervisor.supervisor_session_id,
            project_id=project_id,
            owner_id=owner_id,
        )

        if workflow_record is None:
            if not allow_create:
                raise SupervisorSessionNotFoundError(
                    f"Session not found: {supervisor.supervisor_session_id}"
                )
            if resume is not None:
                raise SupervisorInvalidStateError(
                    "Cannot resume a supervisor session that has not been created"
                )
            if not initial_input:
                raise SupervisorInvalidStateError(
                    "content is required when starting a new supervisor run"
                )

            workflow_record = await self._create_workflow_record(
                project_id=project_id,
                owner_id=owner_id,
                supervisor=supervisor,
                user_request=initial_input,
                model=supervisor.model,
                workflow_profile=supervisor.workflow_profile,
                auto_run=supervisor.context.auto_run,
                hitl_enabled=supervisor.hitl_enabled,
                review_nodes=supervisor.review_nodes,
                memory_enabled=supervisor.context.memory_enabled,
            )
            return PreparedSupervisorStream(
                workflow_record=workflow_record,
                stream_input=initial_input,
                emit_started_event=True,
            )

        await self.hydrate_supervisor(workflow_record, supervisor)
        return await self.prepare_existing_stream(
            workflow_record,
            user_message=initial_input,
            resume=resume,
        )

    async def append_event(
        self,
        supervisor_session_id: str,
        payload: Dict[str, Any],
    ) -> None:
        await self.event_store.append_event(supervisor_session_id, payload)

    async def append_started_event(
        self,
        workflow_record: Any,
        supervisor_session_id: str,
    ) -> SupervisorStartedEvent:
        event = SupervisorStartedEvent(
            workflow_id=workflow_record.id,
            supervisor_session_id=supervisor_session_id,
            status=workflow_record.status,
            workflow_profile=workflow_record.workflow_profile,
            auto_run=workflow_record.auto_run,
        )
        await self.append_event(supervisor_session_id, event.model_dump())
        return event

    async def append_user_message(
        self,
        supervisor_session_id: str,
        content: str,
    ) -> None:
        await self.append_event(
            supervisor_session_id,
            {
                "type": "user_message",
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def prepare_existing_workflow(
        self,
        workflow_record: Any,
        *,
        clear_terminal_state: bool,
    ) -> Any:
        workflow_record.status = "running"
        if clear_terminal_state:
            workflow_record.completed_at = None
            workflow_record.error_message = None
            workflow_record.final_result = None
        await self.db.commit()
        refresh_result = self.db.refresh(workflow_record)
        if inspect.isawaitable(refresh_result):
            await refresh_result
        return workflow_record

    async def handle_stream_event(
        self,
        supervisor: Any,
        payload: Dict[str, Any],
    ) -> None:
        event_type = payload.get("type")
        supervisor_session_id = supervisor.supervisor_session_id

        # ── thinking / text 聚合 ─────────────────────────────────────────
        # per-chunk 直接持久化会写放大；改为按 (source, session_id) 累积，
        # usage 事件时 flush 一次完整事件，频率从"每 chunk 一次"降到"每 LLM call 一次"。
        if event_type in ("thinking", "text"):
            buffer_key = (
                payload.get("source") or "supervisor",
                payload.get("session_id"),
            )
            chunk = payload.get("content") or ""
            if event_type == "thinking":
                self._thinking_buffer[buffer_key] = (
                    self._thinking_buffer.get(buffer_key, "") + chunk
                )
            else:
                self._text_buffer[buffer_key] = (
                    self._text_buffer.get(buffer_key, "") + chunk
                )
            return

        # usage 事件 = LLM call 完成 → 把这次调用累积的 thinking / text flush 进表
        if event_type == "usage":
            buffer_key = (
                payload.get("source") or "supervisor",
                payload.get("session_id"),
            )
            thinking_full = self._thinking_buffer.pop(buffer_key, "")
            text_full = self._text_buffer.pop(buffer_key, "")
            if thinking_full:
                await self.append_event(
                    supervisor_session_id,
                    {
                        "type": "thinking",
                        "content": thinking_full,
                        "source": payload.get("source") or "supervisor",
                        "session_id": payload.get("session_id"),
                    },
                )
            if text_full:
                await self.append_event(
                    supervisor_session_id,
                    {
                        "type": "text",
                        "content": text_full,
                        "source": payload.get("source") or "supervisor",
                        "session_id": payload.get("session_id"),
                    },
                )

        if _should_persist_synthetic_event(event_type):
            await self.append_event(supervisor_session_id, payload)

        # 实时 token 计费：每次 LLM call 结束都 fire 一次 ``usage`` 事件（不管是
        # supervisor 自己还是 sub-agent 内部循环）。每个 delta **累加**到
        # workflow.total_tokens——这就是项目级累计 token 消耗的唯一来源。
        if event_type == "usage":
            total_tokens_delta = _extract_usage_delta(payload)
            if total_tokens_delta > 0:
                workflow_record = await self.workflow_store.get_workflow_by_session(
                    supervisor_session_id
                )
                if workflow_record is not None:
                    workflow_record.total_tokens = (
                        (workflow_record.total_tokens or 0) + total_tokens_delta
                    )
                    await self.db.commit()
            return

        if event_type == "done":
            # supervisor 自己的 done 不再累加 total_tokens（usage 事件已经累过了），
            # 只用来 SET loop_count
            loop_count = _extract_loop_count(payload)
            if loop_count > 0:
                workflow_record = await self.workflow_store.get_workflow_by_session(
                    supervisor_session_id
                )
                if workflow_record is not None:
                    workflow_record.loop_count = loop_count
                    await self.db.commit()
            return

        if event_type == "interrupt":
            await self.save_snapshot(
                supervisor_session_id,
                supervisor.context.workflow,
                _workflow_definitions(supervisor),
            )
            await self.workflow_store.update_status(
                supervisor_session_id,
                "waiting_review",
            )
            return

        if event_type in {"sub_agent_end", "review_end"}:
            await self.save_snapshot(
                supervisor_session_id,
                supervisor.context.workflow,
                _workflow_definitions(supervisor),
            )
            return

        if event_type == "supervisor_done":
            await self.save_snapshot(
                supervisor_session_id,
                supervisor.context.workflow,
                _workflow_definitions(supervisor),
            )
            await self.workflow_store.mark_completed(
                supervisor_session_id,
                final_result=payload.get("final_result"),
            )

    async def mark_failed(
        self,
        supervisor_session_id: str,
        error_message: str,
    ) -> Dict[str, Any]:
        await self.workflow_store.mark_failed(supervisor_session_id, error_message)
        payload = {
            "type": "error",
            "error": error_message,
            "source": "supervisor",
        }
        await self.append_event(supervisor_session_id, payload)
        return payload
