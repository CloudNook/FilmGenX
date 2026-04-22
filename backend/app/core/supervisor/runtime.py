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

        if _should_persist_synthetic_event(event_type):
            await self.append_event(supervisor_session_id, payload)

        if event_type == "done":
            loop_count, total_tokens = _extract_usage_metrics(payload)
            if loop_count > 0 or total_tokens > 0:
                workflow_record = await self.workflow_store.get_workflow_by_session(
                    supervisor_session_id
                )
                if workflow_record is not None:
                    if loop_count > 0:
                        workflow_record.loop_count = loop_count
                    if total_tokens > 0:
                        workflow_record.total_tokens = total_tokens
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
