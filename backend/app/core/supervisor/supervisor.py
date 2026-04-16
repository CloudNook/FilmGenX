"""
SupervisorAgent - 版本化工作流编排器。

在不改动 create_agent / AgentLoop 内核的前提下，
重建一层高层 orchestrator，用于：
- 管理工作流节点与依赖
- 通过 registry 动态选择专家 Agent
- 维持与现有 stream / resume API 的兼容
"""

import logging
from string import Template
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.agent.base import AgentResult, DoneEvent, ErrorEvent, InterruptEvent, ResumeDecision
from app.core.agent.factory import create_agent
from app.core.agent.persist.base import PersistStrategy
from app.core.middleware.chain import AgentMiddleware
from app.core.supervisor.context import SupervisorContext
from app.core.supervisor.registry import (
    SupervisorAgentRegistry,
    WorkflowNodeDefinition,
    build_default_registry,
    build_default_workflow_definitions,
)
from app.core.supervisor.session import SupervisorSession
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
- 调用专家时优先保持输出简洁、可执行、可复用

## 当前可用专家 Agent
$agent_list

## 当前用户需求
$user_request
"""
)


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
    ):
        self.supervisor_session_id = supervisor_session_id
        self.registry = registry or build_default_registry()
        self.workflow_definitions = workflow_definitions or build_default_workflow_definitions()
        self.workflow_profile = workflow_profile
        self.context = SupervisorContext(
            supervisor_session_id=supervisor_session_id,
            user_request=user_request,
            workflow_profile=workflow_profile,
            workflow_definitions=self.workflow_definitions,
            auto_run=auto_run,
        )
        self.session = SupervisorSession(supervisor_session_id)
        self._sub_agent_configs = sub_agent_configs

        self._tool_ctx: Dict[str, Any] = {
            "supervisor_context": self.context,
            "workflow_service": None,
            "registry": self.registry,
        }

        self._agent = create_agent(
            agent_name="supervisor",
            session_id=supervisor_session_id,
            prompt=self._build_system_prompt(),
            model=model,
            tools=get_supervisor_tool_schemas(self.registry.agent_names()),
            max_loop=max_loop,
            persist=persist,
            middlewares=middlewares,
        )

        from app.core.agent.tool import ToolExecutor

        self._agent._tool_executor = ToolExecutor(extra_kwargs=self._tool_ctx)

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

    async def run(self, initial_input: str) -> AgentResult:
        return await self._agent.run(initial_input)

    async def stream(self, initial_input: str) -> AsyncGenerator:
        from app.core.supervisor.events import SupervisorDoneEvent

        accumulated_result = ""
        was_interrupted = False

        try:
            async for event in self._agent.stream(initial_input):
                if hasattr(event, "source") and getattr(event, "source", None) is None:
                    event.source = "supervisor"

                if getattr(event, "type", None) == "text" and hasattr(event, "content"):
                    accumulated_result += event.content

                if isinstance(event, InterruptEvent):
                    was_interrupted = True

                yield event

            if not was_interrupted:
                yield SupervisorDoneEvent(
                    supervisor_session_id=self.supervisor_session_id,
                    workflow=self._build_workflow_payload(),
                    final_result=accumulated_result or "工作流执行完毕",
                )
        except Exception as exc:
            logger.exception("[SupervisorAgent] stream error: %s", exc)
            yield ErrorEvent(error=str(exc), source="supervisor")
            yield SupervisorDoneEvent(
                supervisor_session_id=self.supervisor_session_id,
                workflow=self._build_workflow_payload(),
                final_result=f"执行出错：{exc}",
            )

    async def resume(
        self,
        action: str,
        feedback: Optional[str] = None,
    ) -> AsyncGenerator:
        from app.core.supervisor.events import SupervisorDoneEvent

        decision = ResumeDecision(action=action, feedback=feedback)

        async for event in self._agent.stream(
            "",
            resume=decision,
        ):
            if hasattr(event, "source") and getattr(event, "source", None) is None:
                event.source = "supervisor"

            yield event

            if isinstance(event, DoneEvent):
                yield SupervisorDoneEvent(
                    supervisor_session_id=self.supervisor_session_id,
                    workflow=self._build_workflow_payload(),
                    final_result=event.result.raw_output or "Workflow completed",
                )

    def _build_workflow_payload(self) -> Dict[str, Any]:
        if self.context.workflow is None:
            return {}
        return self.context.workflow.model_dump()
