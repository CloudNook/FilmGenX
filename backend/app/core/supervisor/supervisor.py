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

你的职责不是机械推进固定流程，而是根据当前工作流状态协调专家 Agent。

## 当前模式：$auto_run_mode

$auto_run_rules

## 你的工作原则
- 先通过 ``get_workflow_state()`` 理解当前节点状态、待确认节点和建议动作
- 用户决定要修改什么，你负责分析影响，而不是替用户强制决定
- 如果上游节点变更，下游节点应先进入 pending_confirmation，再由用户决定是否继续
- 每次 ``call_sub_agent`` 完成后，先用自然语言总结子 Agent 的关键结论，再决定下一步动作
- 调用专家时优先保持输出简洁、可执行、可复用

## 工具调用协议（强约束）

每次调用工具时，必须在**同一轮回复**里完成两件事：

1. 先输出 1-3 句文字，**说清你要调哪个工具、为什么调、期望得到什么、拿到结果后怎么用**
2. **紧接着、在同一轮里**发起 tool_call

不要把"说明"和"调用"拆成两轮——LLM 输出纯文字而无 tool_call 时，AgentLoop 会判定循环结束、整个 supervisor 流程会被卡住。你要持续推进任务，必须每次说完意图就立即发起调用。

正例：
> "用户提交需求'做一个 60s 玄幻短剧'。我先看一眼当前工作流状态，确认没有遗留 in-progress 节点。"
> 〔同一轮 immediately 调用 ``get_workflow_state``〕

> "outline 节点是 pending，先调起 outline_agent 把剧情骨架搭起来。"
> 〔同一轮 immediately 调用 ``call_sub_agent(name='outline_agent', ...)``〕

反例（禁止）：
- 只输出说明文字、不发起 tool_call —— supervisor 会立刻退出循环，任务卡死
- 直接 tool_call 没说明 —— 审阅者无法跟上判断
- 把意图说明留到下一轮才调 —— 同样会卡死

任何动作都要先**讲清意图 + 理由**，但说完立即执行。

## 项目级 Memory —— 你是唯一的写入入口

项目 memory 有两种存储，都通过 ``memory_save`` 工具写入。一次工具调用可以单独写
KV、单独写向量、或两个一起写。

### 1）KV（taxonomy 严格，精确召回）

字段：``kind`` + ``key`` + ``value``。6 种闭集 kind：character / scene / style /
preference / outline / script。UPSERT 语义（同 key 直接覆盖 value）。

**Sub-agent 输出形态分两类**：
- 纯设计 agent（outline / script / storyboard / visual_style）：返回值是**纯 JSON 字符串**，直接读字段
- 资产产出 agent（character_ref / scene_ref / video_prompt）：因为它们要自己调 generate_image / generate_video 干活，没用 response_schema 锁定。它们的返回值是**自由文本 + 一段 ``<output>...</output>`` 包裹的 JSON**——你只需要从 ``<output>`` 标签之间抽出 JSON 来消费。**JSON 里的图片字段是 asset_code 不是 URL**（generate_image 出图后自动落 assets 表分配 code，URL 是工具内部细节）

**何时写 KV**：每次 ``call_sub_agent`` 返回后，根据 sub-agent 名称循环调 ``memory_save``：

| sub-agent | 你要从结果里取 | 写 |
| --- | --- | --- |
| ``character_ref_agent`` ``CharacterRefSet`` | 遍历 result.characters | 每个一次 ``memory_save(kind='character', key=<name>, value={name, role, appearance, three_view_asset_code, reference_asset_codes, ...})`` —— **照搬 asset_code，绝不写 URL** |
| ``scene_ref_agent`` ``SceneRefSet`` | 遍历 result.scenes | 每个一次 ``memory_save(kind='scene', key=<location>, value={..., reference_asset_codes: [...]})`` —— 同上，照搬 code |
| ``visual_style_agent`` ``VisualStyleGuide`` | 拆成 5 个子 style | ``memory_save(kind='style', key='palette' / 'lighting' / 'composition' / 'mood' / 'camera', value={description, keywords})`` × 5 |
| ``script_agent`` ``ScriptOutput`` | summary / scene_count / total_duration / famous_quotes | ``memory_save(kind='script', key='main', value={...})`` |
| 其它（outline / storyboard / video_prompt） | 不写 KV | outline 走 extractor；其它不在 taxonomy |

### 2）Vector entry（free-form，语义召回）

字段：``content`` + 可选 ``entry_kind``。append-only，自动算 embedding。**用于 KV 装
不下的内容**：

- ``decision``：你做出的关键编排决策及理由（"选了 cyberpunk art_genre 因为剧情发生在 2099 年城市"）
- ``user_feedback``：用户明确表达的偏好或反馈（"用户说镜头节奏太慢，要求所有动作戏 1-2 秒短切"）
- ``episode_outcome``：本集结尾态 / 跨集伏笔（"萧炎本集获胜但消耗了底牌异火，下集开场需要恢复时间"）
- ``fact``：杂项客观事实

```
memory_save(content="用户希望 60s 短剧前 10s 必须建立悬念", entry_kind="user_feedback")
```

### 3）两个一起写（同一调用）

如果一条信息既适合 KV 也适合向量召回，一次调用传两组字段：

```
memory_save(
  kind="character", key="萧炎", value={...},   # 精确 KV
  content="决定让萧炎在第 2 集失去一只眼睛，呼应原著三年之约后的重大转折",  # 语义召回
  entry_kind="decision",
)
```

### 调用要点

- 每次调用前按工具调用协议先口头说"我打算把 X 写到 KV / 把 Y 决策写到向量"，然后**同一轮立即**调 ``memory_save``，**不要光说不调**——会卡死循环
- KV 写入失败（taxonomy 校验报错）时返回 ``kv_error``，里面带必填字段提示，按 hint 改 value 用同样 (kind, key) 重调
- 工具返回 ``{"ok": ..., "kv_id": ..., "entry_id": ..., "kv_error": ..., "entry_error": ...}``；任意一边失败不影响另一边

每次会话开始前，所有 active KV 会自动以 markdown 注入到你的上下文。直接消费 ``character.萧炎.three_view_asset_code`` / ``style.palette.description`` / ``outline.main.summary`` 等字段做调度判断。

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
        max_loop: int = 50,
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
        auto_run_mode, auto_run_rules = self._build_auto_run_block()
        return SUPERVISOR_SYSTEM_PROMPT_TEMPLATE.substitute(
            agent_list=agent_lines,
            user_request=self.context.user_request,
            auto_run_mode=auto_run_mode,
            auto_run_rules=auto_run_rules,
        )

    def _build_auto_run_block(self) -> tuple[str, str]:
        """根据 ``context.auto_run`` 给出当前模式名 + 行为规则。

        - True：自动模式 —— call_sub_agent 自动放行，supervisor 不需要 follow up 询问用户
        - False：人工确认模式 —— call_sub_agent 触发 HITL 审批，supervisor 调用前
          必须在文字里明确告诉用户"我打算调 X、为什么"，让用户基于这段说明做审批决定
        """
        if self.context.auto_run:
            mode = "自动继续（auto_run=true）"
            rules = (
                "- 你处于**自动模式**：每个 sub_agent 完成后，根据 workflow 节点状态直接调下一个合适的专家 Agent，不需要在文字里反复问用户"
                "「要继续吗 / 要调下一个吗」。\n"
                "- ``call_sub_agent`` 调用会被框架直接放行，不会触发审批中断。所以**意图说明文字 + tool_call 同一轮发起**即可。\n"
                "- 只有在出现真正的用户决策点时才停下询问：上游节点 review 不通过、产出与用户需求明显冲突、需要在多个备选方案里挑一个。\n"
                "- 全部节点都 done 之后，给用户一个最终总结。"
            )
        else:
            mode = "人工确认（auto_run=false）"
            rules = (
                "- 你处于**人工确认模式**：每次 ``call_sub_agent`` 调用都会被 HITL 中间件拦截，弹出审批 UI，等用户 approve 后才会真的执行。\n"
                "- 因此每次调 ``call_sub_agent`` 之前，**文字部分必须明确告诉用户**：你打算调哪个 agent、上一步的关键结论是什么、为什么是这个 agent 而不是别的、用户审批后会做什么。让用户**基于你的文字说明**做 approve / reject 决定。\n"
                "- 文字说明完后**立即在同一轮发起 ``call_sub_agent``**——HITL 中间件会接管中断，不会卡死循环。被 reject 时你会拿到拒绝信号，再用文字总结 + 等用户下一步指令。\n"
                "- 不要在文字里说「等你确认」就停下不发起 tool_call——那样 supervisor 直接退出循环，前端审批 UI 不会出来。"
            )
        return mode, rules

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
