"""Supervisor persistence stores owned by the framework core."""

from __future__ import annotations

from datetime import datetime, timezone
import inspect
import json
from typing import Any, Dict, List, Optional, Tuple

from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent.persist.models import AgentMessageRecord
from app.core.supervisor.workflow import (
    WorkflowNodeDefinition,
    WorkflowNodeState,
    WorkflowSnapshot,
    build_suggested_actions,
)
from app.models.supervisor_event import SupervisorEvent
from app.models.supervisor_workflow import SupervisorWorkflow
from app.models.supervisor_workflow_node import (
    SupervisorWorkflowNode,
    SupervisorWorkflowNodeDependency,
)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _scalars_all(result: Any) -> List[Any]:
    scalars_result = result.scalars()
    if inspect.isawaitable(scalars_result):
        scalars_result = await scalars_result

    items = scalars_result.all()
    if inspect.isawaitable(items):
        items = await items

    return list(items)


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
    session_id = record.session_id if record.session_id.startswith("sub-") else None
    events: List[Dict[str, Any]] = []

    # Reviewer 的 feedback 也以 role=assistant / tool_name=reviewer 写在 sub-agent
    # session 里（DBPersistStrategy.append_review_record，便于按 session replay 看
    # 评审上下文）。但 review_start / review_end 已经走 supervisor_events 表单独
    # 持久化；如果这里再合成 text 事件，前端 reducer 会按 (source, session_id)
    # 把 reviewer feedback 拼到 sub-agent 的 JSON 输出末尾，导致 JSON.parse 失败。
    if record.role == "assistant" and (
        record.tool_name == "reviewer" or metadata.get("kind") == "review"
    ):
        return []

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
        # ``agent_messages.content`` 是 str；工具返回结构化值时这里存的就是 JSON 字符串。
        # 重建 tool_end event 时尝试反序列化一次，让前端拿到的 result 已经是 dict / list /
        # 标量，避免 ``"{\"output\": ...}"`` 这种被当成字符串渲染的双重转义。
        result_value: Any = record.content
        if isinstance(result_value, str):
            stripped = result_value.strip()
            if (stripped.startswith("{") and stripped.endswith("}")) or (
                stripped.startswith("[") and stripped.endswith("]")
            ):
                try:
                    result_value = json.loads(stripped)
                except json.JSONDecodeError:
                    pass

        event = {
            "type": "tool_end",
            "tool_call_id": record.tool_call_id or "",
            "tool_name": record.tool_name or "",
            "result": result_value,
            "is_error": False,
            "source": source,
        }
        if session_id:
            event["session_id"] = session_id
        events.append(event)

    return events


def _supervisor_event_payload(event: Any) -> Optional[Dict[str, Any]]:
    payload = getattr(event, "payload", None)
    if isinstance(payload, dict):
        return dict(payload)

    to_payload = getattr(event, "to_payload", None)
    if callable(to_payload):
        payload = to_payload()
        if isinstance(payload, dict):
            return payload

    return None


class SupervisorEventStore:
    """Core-owned persistence for supervisor timeline events."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def append_event(
        self,
        supervisor_session_id: str,
        payload: Dict[str, Any],
    ) -> SupervisorEvent:
        encoded_payload = jsonable_encoder(payload)
        event = SupervisorEvent(
            supervisor_session_id=supervisor_session_id,
            event_type=str(encoded_payload.get("type") or "unknown"),
            source=str(encoded_payload.get("source") or "supervisor"),
            source_session_id=self._source_session_id(encoded_payload),
            payload=encoded_payload,
        )
        self.db.add(event)
        await self.db.commit()
        await _maybe_await(self.db.refresh(event))
        return event

    async def list_events_by_session(
        self,
        supervisor_session_id: str,
    ) -> List[SupervisorEvent]:
        result = await self.db.execute(
            select(SupervisorEvent)
            .where(
                SupervisorEvent.supervisor_session_id == supervisor_session_id,
                SupervisorEvent.is_deleted.is_(False),
            )
            .order_by(SupervisorEvent.created_at.asc(), SupervisorEvent.id.asc())
        )
        return list(result.scalars().all())

    async def list_events_after(
        self,
        supervisor_session_id: str,
        after_id: int,
        *,
        limit: int = 500,
    ) -> List[SupervisorEvent]:
        """按 ``id`` 增量取 ``after_id`` 之后的事件。给 SSE tail 端点的 replay + poll 用。

        ``id`` 是 BIGINT auto-increment，单调递增，比 ``created_at`` 更适合做增量游标
        （并发写入时间戳可能并列）。
        """
        result = await self.db.execute(
            select(SupervisorEvent)
            .where(
                SupervisorEvent.supervisor_session_id == supervisor_session_id,
                SupervisorEvent.is_deleted.is_(False),
                SupervisorEvent.id > after_id,
            )
            .order_by(SupervisorEvent.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    def _source_session_id(payload: Dict[str, Any]) -> str | None:
        session_id = payload.get("session_id")
        if isinstance(session_id, str) and session_id:
            return session_id
        return None


class SupervisorWorkflowStore:
    """Core-owned persistence for supervisor workflow runs."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_workflow(
        self,
        project_id: int,
        owner_id: int,
        supervisor_session_id: str,
        user_request: str,
        model: str = "gemini-3-flash-preview",
        workflow_profile: str = "default",
        auto_run: bool = False,
        hitl_enabled: bool = False,
        review_nodes: Optional[List[str]] = None,
        memory_enabled: bool = True,
    ) -> SupervisorWorkflow:
        workflow = await self._create_workflow_record(
            project_id=project_id,
            owner_id=owner_id,
            supervisor_session_id=supervisor_session_id,
            user_request=user_request,
            model=model,
            status="running",
            workflow_profile=workflow_profile,
            auto_run=auto_run,
            hitl_enabled=hitl_enabled,
            review_nodes=review_nodes,
            memory_enabled=memory_enabled,
        )
        await self.db.commit()
        await _maybe_await(self.db.refresh(workflow))
        return workflow

    async def _create_workflow_record(self, **kwargs: Any) -> SupervisorWorkflow:
        workflow = SupervisorWorkflow(**kwargs)
        self.db.add(workflow)
        await self.db.flush()
        return workflow

    async def get_workflow_by_session(
        self,
        supervisor_session_id: str,
        *,
        project_id: int | None = None,
        owner_id: int | None = None,
    ) -> Optional[SupervisorWorkflow]:
        filters = [
            SupervisorWorkflow.supervisor_session_id == supervisor_session_id,
            SupervisorWorkflow.is_deleted.is_(False),
        ]
        if project_id is not None:
            filters.append(SupervisorWorkflow.project_id == project_id)
        if owner_id is not None:
            filters.append(SupervisorWorkflow.owner_id == owner_id)

        result = await self.db.execute(select(SupervisorWorkflow).where(*filters))
        return result.scalar_one_or_none()

    async def get_workflow(
        self,
        workflow_id: int,
        project_id: int,
        owner_id: int | None = None,
    ) -> Optional[SupervisorWorkflow]:
        filters = [
            SupervisorWorkflow.id == workflow_id,
            SupervisorWorkflow.project_id == project_id,
            SupervisorWorkflow.is_deleted.is_(False),
        ]
        if owner_id is not None:
            filters.append(SupervisorWorkflow.owner_id == owner_id)

        result = await self.db.execute(select(SupervisorWorkflow).where(*filters))
        return result.scalar_one_or_none()

    async def list_workflows(
        self,
        project_id: int,
        owner_id: int,
        *,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Tuple[List[SupervisorWorkflow], int]:
        filters = [
            SupervisorWorkflow.project_id == project_id,
            SupervisorWorkflow.owner_id == owner_id,
            SupervisorWorkflow.is_deleted.is_(False),
        ]
        if status:
            filters.append(SupervisorWorkflow.status == status)

        total = (
            await self.db.execute(
                select(func.count()).select_from(SupervisorWorkflow).where(*filters)
            )
        ).scalar_one()

        items = (
            await self.db.execute(
                select(SupervisorWorkflow)
                .where(*filters)
                .order_by(SupervisorWorkflow.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()

        return list(items), int(total)

    async def update_status(
        self,
        supervisor_session_id: str,
        status_value: str,
    ) -> Optional[SupervisorWorkflow]:
        workflow = await self.get_workflow_by_session(supervisor_session_id)
        if workflow is None:
            return None
        workflow.status = status_value
        if status_value == "completed":
            workflow.completed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await _maybe_await(self.db.refresh(workflow))
        return workflow

    async def save_workflow_state(
        self,
        supervisor_session_id: str,
        workflow_snapshot: WorkflowSnapshot,
        workflow_definitions: list[WorkflowNodeDefinition] | None = None,
        active_node_key: Optional[str] = None,
    ) -> Optional[SupervisorWorkflow]:
        workflow = await self.get_workflow_by_session(supervisor_session_id)
        if workflow is None:
            return None
        await self._replace_workflow_state(
            workflow,
            workflow_snapshot,
            workflow_definitions=workflow_definitions,
        )
        workflow.active_node_key = active_node_key or self._infer_active_node_key(
            workflow_snapshot
        )
        await self.db.commit()
        await _maybe_await(self.db.refresh(workflow))
        return workflow

    async def load_workflow_state(
        self,
        workflow_record: SupervisorWorkflow,
    ) -> Optional[WorkflowSnapshot]:
        node_result = await self.db.execute(
            select(SupervisorWorkflowNode)
            .where(
                SupervisorWorkflowNode.workflow_id == workflow_record.id,
                SupervisorWorkflowNode.is_deleted.is_(False),
            )
            .order_by(SupervisorWorkflowNode.id.asc())
        )
        nodes = list(node_result.scalars().all())
        if not nodes:
            return None

        dependency_result = await self.db.execute(
            select(SupervisorWorkflowNodeDependency)
            .where(
                SupervisorWorkflowNodeDependency.workflow_id == workflow_record.id,
                SupervisorWorkflowNodeDependency.is_deleted.is_(False),
            )
            .order_by(SupervisorWorkflowNodeDependency.id.asc())
        )
        dependency_rows = list(dependency_result.scalars().all())

        snapshot_nodes = {
            node.node_key: WorkflowNodeState(
                key=node.node_key,
                version=node.version,
                status=node.status,
                artifact=self._deserialize_artifact(node.artifact_content),
                updated_by=node.updated_by,
                last_agent=node.last_agent,
                updated_at=node.node_updated_at,
            )
            for node in nodes
        }
        dependency_map = {node.node_key: [] for node in nodes}
        for dependency in dependency_rows:
            dependency_map.setdefault(dependency.node_key, []).append(
                dependency.depends_on_key
            )

        snapshot = WorkflowSnapshot(
            profile=workflow_record.workflow_profile,
            nodes=snapshot_nodes,
            dependency_map=dependency_map,
            updated_at=workflow_record.updated_at,
        )
        snapshot.suggested_actions = build_suggested_actions(snapshot)
        return snapshot

    async def load_event_history(
        self,
        supervisor_session_id: str,
    ) -> List[Dict[str, Any]]:
        result = await self.db.execute(
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
        records = await _scalars_all(result)
        supervisor_events = await SupervisorEventStore(self.db).list_events_by_session(
            supervisor_session_id
        )

        history_entries: List[tuple[datetime, str, Dict[str, Any]]] = []
        for record in records:
            for index, event_payload in enumerate(
                _record_to_history_events(record, supervisor_session_id)
            ):
                history_entries.append(
                    (
                        record.created_at,
                        f"agent:{record.id}:{index}",
                        event_payload,
                    )
                )

        for event in supervisor_events:
            payload = _supervisor_event_payload(event)
            if payload is None:
                continue
            history_entries.append(
                (
                    event.created_at,
                    f"supervisor:{event.id}",
                    payload,
                )
            )

        history_entries.sort(key=lambda item: (item[0], item[1]))
        return [payload for _, _, payload in history_entries]

    async def mark_completed(
        self,
        supervisor_session_id: str,
        final_result: Optional[str] = None,
    ) -> Optional[SupervisorWorkflow]:
        workflow = await self.get_workflow_by_session(supervisor_session_id)
        if workflow is None:
            return None
        workflow.status = "completed"
        workflow.completed_at = datetime.now(timezone.utc)
        if final_result is not None:
            workflow.final_result = final_result
        await self.db.commit()
        await _maybe_await(self.db.refresh(workflow))
        return workflow

    async def mark_failed(
        self,
        supervisor_session_id: str,
        error_message: str,
    ) -> Optional[SupervisorWorkflow]:
        workflow = await self.get_workflow_by_session(supervisor_session_id)
        if workflow is None:
            return None
        workflow.status = "failed"
        workflow.error_message = error_message
        workflow.completed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await _maybe_await(self.db.refresh(workflow))
        return workflow

    async def _replace_workflow_state(
        self,
        workflow: SupervisorWorkflow,
        workflow_snapshot: WorkflowSnapshot,
        *,
        workflow_definitions: list[WorkflowNodeDefinition] | None = None,
    ) -> None:
        definition_map = {
            definition.key: definition for definition in workflow_definitions or []
        }

        await self.db.execute(
            delete(SupervisorWorkflowNodeDependency).where(
                SupervisorWorkflowNodeDependency.workflow_id == workflow.id
            )
        )
        await self.db.execute(
            delete(SupervisorWorkflowNode).where(
                SupervisorWorkflowNode.workflow_id == workflow.id
            )
        )

        for node_key, node_state in workflow_snapshot.nodes.items():
            definition = definition_map.get(node_key)
            self.db.add(
                SupervisorWorkflowNode(
                    workflow_id=workflow.id,
                    node_key=node_key,
                    label=(
                        definition.label
                        if definition is not None
                        else node_key.replace("_", " ").title()
                    ),
                    node_type=definition.node_type if definition is not None else "text",
                    status=node_state.status,
                    version=node_state.version,
                    produces_artifact=(
                        definition.produces_artifact if definition is not None else True
                    ),
                    can_run_automatically=(
                        definition.can_run_automatically
                        if definition is not None
                        else True
                    ),
                    artifact_content=self._serialize_artifact(node_state.artifact),
                    updated_by=node_state.updated_by,
                    last_agent=node_state.last_agent,
                    node_updated_at=node_state.updated_at,
                )
            )

        for node_key, depends_on in workflow_snapshot.dependency_map.items():
            for depends_on_key in depends_on:
                self.db.add(
                    SupervisorWorkflowNodeDependency(
                        workflow_id=workflow.id,
                        node_key=node_key,
                        depends_on_key=depends_on_key,
                    )
                )

    @staticmethod
    def _infer_active_node_key(
        workflow_snapshot: Optional[Dict[str, Any] | WorkflowSnapshot],
    ) -> Optional[str]:
        if isinstance(workflow_snapshot, WorkflowSnapshot):
            suggested_actions = workflow_snapshot.suggested_actions
            for action in suggested_actions:
                if action.target_node:
                    return str(action.target_node)
            nodes = {
                node_key: node.model_dump()
                for node_key, node in workflow_snapshot.nodes.items()
            }
        else:
            nodes = None
            suggested_actions = None

        if not isinstance(workflow_snapshot, dict):
            workflow_snapshot = {}

        if suggested_actions is None:
            suggested_actions = workflow_snapshot.get("suggested_actions")
            if isinstance(suggested_actions, list):
                for action in suggested_actions:
                    if isinstance(action, dict):
                        if action.get("target_node"):
                            return str(action["target_node"])
                        if action.get("node_key"):
                            return str(action["node_key"])

        if nodes is None:
            nodes = workflow_snapshot.get("nodes")
            if not isinstance(nodes, dict):
                return None

        for desired_status in ("running", "pending_confirmation", "ready", "stale"):
            for node_key, node in nodes.items():
                if isinstance(node, dict) and node.get("status") == desired_status:
                    return str(node_key)

        return None

    @staticmethod
    def _serialize_artifact(artifact: Any) -> str | None:
        if artifact is None:
            return None
        if isinstance(artifact, str):
            return artifact
        if isinstance(artifact, dict):
            output = artifact.get("output")
            if isinstance(output, str):
                return output
        return json.dumps(jsonable_encoder(artifact), ensure_ascii=False)

    @staticmethod
    def _deserialize_artifact(artifact_content: str | None) -> dict[str, Any] | None:
        if artifact_content is None:
            return None
        return {"output": artifact_content}
