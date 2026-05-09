"""
SupervisorAgent - 版本化工作流编排器。

在不改动 create_agent / AgentLoop 内核的前提下，
重建一层高层 orchestrator，用于：
- 管理工作流节点与依赖
- 通过 registry 动态选择专家 Agent
- 通过统一 stream 入口管理生命周期与持久化
"""

import logging
from string import Template
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.agent.base import AgentResult, DoneEvent, InterruptEvent, ResumeDecision
from app.core.agent.factory import create_agent
from app.core.agent.memory.config import MemoryConfig
from app.core.agent.persist.base import PersistStrategy
from app.core.middleware.chain import AgentMiddleware
from app.core.supervisor.context import SupervisorContext
from app.core.supervisor.errors import SupervisorInvalidStateError
from app.core.supervisor.events import SupervisorErrorEvent
from app.core.supervisor.persist import SupervisorWorkflowStore
from app.core.supervisor.registry import (
    SupervisorAgentRegistry,
    WorkflowNodeDefinition,
    build_default_registry,
    build_default_workflow_definitions,
)
from app.core.supervisor.runtime import PreparedSupervisorStream, SupervisorRuntime
from app.core.supervisor.tools import get_supervisor_tool_schemas

logger = logging.getLogger(__name__)

SUPERVISOR_SYSTEM_PROMPT_TEMPLATE = Template(
    """你是 FilmGenX 的 Supervisor Orchestrator。

你的职责不是机械推进固定流程，而是根据当前工作流状态协调专家 Agent：

## 你的工作原则
- 先通过 get_workflow_state() 理解当前节点状态、待确认节点和建议动作
- 用户决定要修改什么，你负责分析影响，而不是替用户强制决定
- 如果上游节点变更，下游节点应先进入 pending_confirmation，再由用户决定是否继续
- 用户开启自动继续时，你可以按建议调用合适的专家 Agent
- 每次 `call_sub_agent` 完成后，先用自然语言总结子 Agent 的关键结论，再决定下一步动作
- 调用专家时优先保持输出简洁、可执行、可复用

## 当前可用专家 Agent
$agent_list

## 当前用户需求
$user_request
"""
)


def _maybe_build_memory(
    domain_id: int | str | None,
    memory_enabled: bool,
) -> Optional[MemoryConfig]:
    """根据 domain_id + memory_enabled 决定是否构造 MemoryConfig。

    domain_id 为 None 或 memory_enabled=False → 返回 None（agent 不挂 memory）。
    framework 不知道 domain 是什么；FilmGenX 业务（这里）把 project.id 当 domain_id
    传进来；其它业务可以传 user.id / repo.id 等。
    """
    if not memory_enabled or domain_id is None:
        return None
    # 延迟 import 避免 supervisor 模块永远依赖业务实现（极端业务可能不需要 memory）
    from app.memory import build_domain_memory_config

    return build_domain_memory_config(domain_id=domain_id)


class SupervisorAgent:
    """
    高层 Supervisor 编排器。

    仍然复用标准 Agent 作为执行内核，但将状态、registry、工作流定义提升到 Python 层。
    """

    def __init__(
        self,
        supervisor_session_id: str,
        user_request: str,
        sub_agent_configs: Dict[str, Any],
        middlewares: List[AgentMiddleware],
        persist: Optional[PersistStrategy],
        model: str = "gemini-3-flash-preview",
        max_loop: int = 30,
        registry: Optional[SupervisorAgentRegistry] = None,
        workflow_definitions: Optional[List[WorkflowNodeDefinition]] = None,
        workflow_profile: str = "default",
        auto_run: bool = False,
        hitl_enabled: bool = False,
        review_nodes: Optional[List[str]] = None,
        db: Any = None,
        domain_id: int | str | None = None,
        memory_enabled: bool = True,
    ):
        self.supervisor_session_id = supervisor_session_id
        self.model = model
        self.registry = registry or build_default_registry()
        self.workflow_definitions = workflow_definitions or build_default_workflow_definitions()
        self.workflow_profile = workflow_profile
        self.hitl_enabled = hitl_enabled
        self.review_nodes = list(review_nodes or [])
        self._db = db
        self._workflow_store_cls = SupervisorWorkflowStore
        self.context = SupervisorContext(
            supervisor_session_id=supervisor_session_id,
            user_request=user_request,
            workflow_profile=workflow_profile,
            workflow_definitions=self.workflow_definitions,
            auto_run=auto_run,
            domain_id=domain_id,
            memory_enabled=memory_enabled,
        )
        self._sub_agent_configs = sub_agent_configs

        self._tool_ctx: Dict[str, Any] = {
            "supervisor_context": self.context,
            "registry": self.registry,
        }

        # Supervisor 自己也可挂 memory（它本质就是 Agent，可以借项目级记忆做调度判断）
        supervisor_memory = _maybe_build_memory(domain_id, memory_enabled)
        if supervisor_memory is not None:
            logger.info(
                "[SupervisorAgent] memory enabled (domain_id=%s) for supervisor itself",
                domain_id,
            )

        self._agent = create_agent(
            agent_name="supervisor",
            session_id=supervisor_session_id,
            prompt=self._build_system_prompt(),
            model=model,
            tools=get_supervisor_tool_schemas(self.registry.agent_names()),
            max_loop=max_loop,
            persist=persist,
            middlewares=middlewares,
            memory=supervisor_memory,
        )

        from app.core.agent.tool import ToolExecutor

        # Agent 内部 _init_tool_executor 已经把 memory_harness 塞进 extra_kwargs；
        # 这里在它基础上再叠加 supervisor_context / registry，保持原有 supervisor 工具的注入
        merged_extra = dict(self._tool_ctx)
        if supervisor_memory is not None:
            merged_extra["memory_harness"] = self._agent.memory
        self._agent._tool_executor = ToolExecutor(extra_kwargs=merged_extra)

        logger.info(
            "[SupervisorAgent] created supervisor_session=%s, workflow_profile=%s, agents=%s",
            supervisor_session_id,
            workflow_profile,
            self.registry.agent_names(),
        )

    def _build_system_prompt(self) -> str:
        agent_lines = "\n".join(
            f"- {agent.name}: {agent.description}" for agent in self.registry.agents
        ) or "- 当前尚未注册专家 Agent"
        return SUPERVISOR_SYSTEM_PROMPT_TEMPLATE.substitute(
            agent_list=agent_lines,
            user_request=self.context.user_request,
        )

    async def run(
        self,
        initial_input: str,
        *,
        resume: Optional[ResumeDecision] = None,
    ) -> AgentResult:
        return await self._agent.run(initial_input, resume=resume)

    async def _stream_agent(
        self,
        initial_input: str,
        *,
        resume: Optional[ResumeDecision] = None,
    ) -> AsyncGenerator:
        from app.core.supervisor.events import SupervisorDoneEvent

        accumulated_result = ""
        done_output: Optional[str] = None
        was_interrupted = False

        async for event in self._agent.stream(initial_input, resume=resume):
            if getattr(event, "type", None) == "text" and hasattr(event, "content"):
                accumulated_result += event.content

            if isinstance(event, InterruptEvent):
                was_interrupted = True

            if isinstance(event, DoneEvent):
                done_output = event.result.raw_output or done_output

            yield event

        if not was_interrupted:
            yield SupervisorDoneEvent(
                supervisor_session_id=self.supervisor_session_id,
                workflow=self._build_workflow_payload(),
                final_result=done_output or accumulated_result or "工作流执行完毕",
            )

    def _build_runtime(self) -> SupervisorRuntime:
        if self._db is None:
            raise SupervisorInvalidStateError(
                "Supervisor runtime requires a database session"
            )
        return SupervisorRuntime(self._workflow_store_cls(self._db))

    def apply_workflow_runtime(self, workflow_record: Any) -> None:
        stored_model = getattr(workflow_record, "model", None)
        if isinstance(stored_model, str) and stored_model:
            self.model = stored_model
            self._agent.config.model = stored_model

        stored_profile = getattr(workflow_record, "workflow_profile", None)
        if isinstance(stored_profile, str) and stored_profile:
            self.workflow_profile = stored_profile
            self.context.workflow_profile = stored_profile

        stored_user_request = getattr(workflow_record, "user_request", None)
        if isinstance(stored_user_request, str) and stored_user_request:
            self.context.user_request = stored_user_request

        stored_auto_run = getattr(workflow_record, "auto_run", None)
        if isinstance(stored_auto_run, bool):
            self.context.auto_run = stored_auto_run

        stored_hitl_enabled = getattr(workflow_record, "hitl_enabled", None)
        if isinstance(stored_hitl_enabled, bool):
            self.hitl_enabled = stored_hitl_enabled

        stored_review_nodes = getattr(workflow_record, "review_nodes", None)
        self.review_nodes = (
            list(stored_review_nodes)
            if isinstance(stored_review_nodes, list)
            else []
        )

        self._agent.config.prompt = self._build_system_prompt()

    @staticmethod
    def _event_payload(event: Any) -> Dict[str, Any]:
        if hasattr(event, "model_dump"):
            payload = event.model_dump()
        else:
            payload = {"type": "unknown", "repr": str(event)}

        for extra_field in ("source", "session_id"):
            extra_value = getattr(event, extra_field, None)
            if extra_value is not None:
                payload[extra_field] = extra_value
        return payload

    async def stream(
        self,
        initial_input: str,
        *,
        project_id: int,
        owner_id: int,
        resume: Optional[ResumeDecision] = None,
        require_existing: bool = False,
    ) -> AsyncGenerator:
        runtime = self._build_runtime()
        prepared_stream = await runtime.prepare_stream(
            self,
            project_id=project_id,
            owner_id=owner_id,
            initial_input=initial_input,
            resume=resume,
            allow_create=not require_existing,
        )

        async def _generate_managed(prepared: PreparedSupervisorStream):
            try:
                if prepared.pending_user_message is not None:
                    await runtime.append_user_message(
                        self.supervisor_session_id,
                        prepared.pending_user_message,
                    )

                if prepared.emit_started_event and prepared.workflow_record is not None:
                    yield await runtime.append_started_event(
                        prepared.workflow_record,
                        self.supervisor_session_id,
                    )

                async for event in self._stream_agent(
                    prepared.stream_input,
                    resume=prepared.resume_decision,
                ):
                    yield event
                    await runtime.handle_stream_event(self, self._event_payload(event))
            except Exception as exc:
                logger.exception("[SupervisorAgent] managed stream error: %s", exc)
                await runtime.mark_failed(self.supervisor_session_id, str(exc))
                yield SupervisorErrorEvent(error=str(exc), source="supervisor")

        return _generate_managed(prepared_stream)

    def _build_workflow_payload(self) -> Dict[str, Any]:
        if self.context.workflow is None:
            return {}
        return self.context.workflow.model_dump()
