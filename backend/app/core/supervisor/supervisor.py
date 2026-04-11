"""
SupervisorAgent — 视频生成流水线的元 Agent。
"""

import logging
from string import Template
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.agent.agent import Agent
from app.core.agent.base import AgentResult
from app.core.agent.factory import create_agent
from app.core.agent.persist.base import PersistStrategy
from app.core.middleware.chain import AgentMiddleware
from app.core.supervisor.context import SupervisorContext
from app.core.supervisor.session import SupervisorSession
from app.core.supervisor.tools import get_supervisor_tool_schemas

logger = logging.getLogger(__name__)

SUPERVISOR_SYSTEM_PROMPT_TEMPLATE = Template("""你是一个视频生成流水线的 Supervisor Agent。你的职责是：

## 可用工具
- call_sub_agent(sub_agent_name, task_description, context_snapshot)
- call_reviewer(content, review_criteria)
- get_workflow_state()

## 流水线阶段
1. outline_writer → 生成视频大纲（JSON Schema: OutlineSchema）
2. script_writer → 基于大纲创作剧本（JSON Schema: ScriptSchema）
3. storyboarder → 生成分镜组（JSON Schema: StoryboardSchema）

## 工作原则
- 先理解用户需求，制定流水线计划
- 每个 SubAgent 调用后，用 Reviewer 评估结果（threshold = 7/10）
- 评估不通过时，说明原因并决定：重试同 Agent 或调整策略
- 流水线完成后，汇总所有产物并返回最终结果
- 遇到错误时，尝试恢复或换备选方案，不要轻易放弃
- 重要：不要让用户等待太久，每轮决策尽量简洁

## Supervisor 工具说明

### call_sub_agent
调用 SubAgent 执行任务：
- sub_agent_name: outline_writer | script_writer | storyboarder
- task_description: 角色定义 + 具体任务描述
- context_snapshot: 前序产物 JSON（选择性注入）

### call_reviewer
评估内容质量：
- content: 待评估内容
- review_criteria: 评估维度列表
- 返回: {score, passed, feedback, suggestions}

### get_workflow_state
查询当前流水线状态（ Supervisor 决策参考）。

## 当前用户需求
$user_request
""")


class SupervisorAgent:
    """
    Supervisor Agent。

    组合标准 Agent 能力，复用 run()/stream() 模式。
    差异点：
    - 有自己的 system prompt（流水线描述 + 工具说明）
    - 持有 SupervisorContext（工作内存，SubAgent 无法访问）
    - 持有 SupervisorSession（session 关联管理）
    - 工具集为 {call_sub_agent, call_reviewer, get_workflow_state}
    - stream() 将 SubAgent 事件实时透传到 SSE
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
    ):
        self.supervisor_session_id = supervisor_session_id
        self.context = SupervisorContext(
            supervisor_session_id=supervisor_session_id,
            user_request=user_request,
        )
        self.session = SupervisorSession(supervisor_session_id)
        self._sub_agent_configs = sub_agent_configs

        tool_schemas = get_supervisor_tool_schemas()

        self._tool_ctx: Dict[str, Any] = {
            "supervisor_context": self.context,
        }

        self._agent = create_agent(
            agent_name="supervisor",
            session_id=supervisor_session_id,
            prompt=self._build_system_prompt(),
            tools=tool_schemas,
            max_loop=max_loop,
            persist=persist,
            middlewares=middlewares,
        )

        logger.info(
            f"[SupervisorAgent] created supervisor_session={supervisor_session_id}, "
            f"max_loop={max_loop}"
        )

    def _build_system_prompt(self) -> str:
        return SUPERVISOR_SYSTEM_PROMPT_TEMPLATE.substitute(
            user_request=self.context.user_request,
        )

    async def run(self, initial_input: str) -> AgentResult:
        """
        非流式执行，返回流水线最终结果。

        Supervisor 不使用 run()，流水线推荐使用 stream()。
        此方法用于简单场景。
        """
        return await self._agent.run(initial_input)

    async def stream(
        self,
        initial_input: str,
    ) -> AsyncGenerator:
        """
        流式执行，yield SupervisorStreamEvent。

        事件透传逻辑：
        - Supervisor 的 Thinking/Text 事件：透传（source = "supervisor"）
        - ToolStart/ToolEnd 事件：透传（source = "supervisor"）
        - SubAgentStart/SubAgentEnd 事件：工具内部 yield
        - SupervisorDoneEvent：最后 yield
        """
        from app.core.supervisor.events import SupervisorDoneEvent

        accumulated_result = ""

        try:
            async for event in self._agent.stream(initial_input):
                if hasattr(event, "source") and getattr(event, "source", None) is None:
                    event.source = "supervisor"

                if hasattr(event, "content") and getattr(event, "type", None) == "text":
                    accumulated_result += event.content

                yield event

            final_artifacts = dict(self.context.artifacts)
            yield SupervisorDoneEvent(
                supervisor_session_id=self.supervisor_session_id,
                artifacts=final_artifacts,
                final_result=accumulated_result or "流水线执行完毕",
            )

        except Exception as e:
            logger.exception(f"[SupervisorAgent] stream error: {e}")
            from app.core.agent.base import ErrorEvent
            yield ErrorEvent(error=str(e), source="supervisor")
            yield SupervisorDoneEvent(
                supervisor_session_id=self.supervisor_session_id,
                artifacts=dict(self.context.artifacts),
                final_result=f"执行出错：{str(e)}",
            )
