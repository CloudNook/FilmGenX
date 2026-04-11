# Supervisor Agent 设计方案

**日期**: 2026-04-11
**状态**: 已批准
**设计人**: Claude

---

## 1. 背景与目标

FilmGenX 视频生成流水线需要从用户需求出发，依次完成：

1. **大纲撰写**（outline_writer）
2. **剧本创作**（script_writer）
3. **分镜组生成编排**（storyboarder）

每个步骤是一个独立的 SubAgent，Supervisor 负责动态调度这些 SubAgent：根据任务状态自主决定调用哪个 Agent、调用几次、是否需要 Reviewer 评估并循环优化。

---

## 2. 方案选择

选择 **方案 A：Supervisor 作为 Meta-Agent**。

理由：
- 用户明确要求"完全动态"——只有 LLM 驱动的 Supervisor 才能自主决策
- 完全复用现有 Agent/Loop/Middleware 框架，改动最小
- 流水线事件天然通过 `stream()` 向上透传，前端体验一致
- SubAgent 和 Reviewer 都是 Tool，完全对称

---

## 3. 核心设计原则

1. **Supervisor 是决策者，SubAgent 是执行者**：Supervisor 拥有自己的 LLM 和 session，独立做流水线决策
2. **SubAgent 不访问 Supervisor 内部状态**：SubAgent 只通过 `call_sub_agent` 的参数接收选择性传递的上下文，不持有 SupervisorContext
3. **流式事件实时透传**：SubAgent 的内部事件（Thinking/Text/ToolStart/ToolEnd）通过 SSE 实时流向前端，前端可感知每个 SubAgent 的执行状态
4. **Session 关联但不共享**：Supervisor 和 SubAgent 各自有独立 session_id，通过 SupervisorSession 记录关联关系

---

## 4. 文件结构

```
backend/app/core/supervisor/
├── context.py          # SupervisorContext（Pydantic，流水线工作内存）
├── session.py          # SupervisorSession（SubAgent session 关联管理）
├── events.py           # 流式事件扩展（SubAgentStart/SubAgentEnd/SupervisorDone/ReviewStart/ReviewEnd）
├── tools.py            # Supervisor 工具：call_sub_agent / call_reviewer / get_workflow_state
├── reviewer.py         # Reviewer Agent 配置和 prompt
├── supervisor.py       # SupervisorAgent 核心类
└── factory.py          # create_supervisor() 工厂

backend/app/core/tools/
└── supervisor_tools.py  # Supervisor 工具注册到 ToolRegistry
```

---

## 5. 数据模型

### 5.1 SupervisorContext

```python
class SupervisorContext(BaseModel):
    supervisor_session_id: str
    user_request: str
    current_phase: str = "init"  # init | outline | script | storyboard | review | done
    artifacts: Dict[str, Any] = {}  # 各阶段产物
    sub_agent_sessions: Dict[str, str] = {}  # sub_agent_name → session_id
    review_history: List[Dict[str, Any]] = []  # [{agent, score, feedback}, ...]
    metadata: Dict[str, Any] = {}
```

### 5.2 SupervisorSession

```python
class SupervisorSession:
    def __init__(self, supervisor_session_id: str): ...
    def register_sub_session(self, sub_agent_name: str, sub_session_id: str) -> None: ...
    def get_sub_session(self, sub_agent_name: str) -> str | None: ...
    def get_all_sessions(self) -> Dict[str, str]: ...
```

---

## 6. 工具定义

### 6.1 call_sub_agent

**注册名**: `call_sub_agent`
**类型**: 流式工具（async generator）

```python
class Input(BaseModel):
    sub_agent_name: str           # outline_writer | script_writer | storyboarder
    task_description: str        # Supervisor 构造的 prompt（角色 + 任务 + 参考产物）
    context_snapshot: str         # 前序 SubAgent 产物 JSON（选择性注入）

class Output(BaseModel):
    success: bool
    sub_agent_name: str
    session_id: str
    result: Dict[str, Any]        # AgentResult.schema_data
    raw_output: str
    error: Optional[str]
```

**执行流程**：
1. 分配/复用 SubAgent session_id（格式：`sub-{agent_name}-{uuid4()[:8]}`）
2. `SupervisorSession.register_sub_session()` 记录关联
3. 创建 SubAgent 实例（`create_agent(sub_session_id, prompt=task_description, ...)`）
4. `async for event in sub_agent.stream()`：实时 yield SubAgent 的所有 StreamEvent
5. 执行完毕后返回 AgentResult

**关键约束**：SubAgent 实例化时只传入 `task_description` 作为 prompt，不传入任何 Supervisor 内部状态。

### 6.2 call_reviewer

**注册名**: `call_reviewer`
**类型**: 标准工具（返回 Output）

```python
class Input(BaseModel):
    content: str
    review_criteria: List[str]  # ["情感张力", "结构完整性", "分镜合理性"]

class Output(BaseModel):
    score: float          # 0-10
    passed: bool          # score >= 7
    feedback: str         # 详细反馈
    suggestions: List[str]  # 改进建议
```

Reviewer Agent 也是一个标准 Agent，封装为一个 Tool。

### 6.3 get_workflow_state

**注册名**: `get_workflow_state`
**类型**: 标准工具（返回 Dict）

```python
async def execute(ctx: SupervisorContext) -> Dict[str, Any]:
    return {
        "current_phase": ctx.current_phase,
        "artifacts": ctx.artifacts,
        "review_history": ctx.review_history,
    }
```

> **注意**：`get_workflow_state` 供 Supervisor Agent 自身使用（LLM 决策参考），不是给 SubAgent 用的。

---

## 7. 流式事件增强

在 `app/core/agent/base.py` 的 StreamEvent 联合类型基础上，新增 Supervisor 相关事件：

```python
# SupervisorStreamEvent 继承自 StreamEvent，带 source 标记

class SubAgentStartEvent(StreamEvent):
    type: Literal["sub_agent_start"] = "sub_agent_start"
    sub_agent_name: str
    session_id: str
    task_description: str
    source: str = "supervisor"  # 前端渲染标识

class SubAgentEndEvent(StreamEvent):
    type: Literal["sub_agent_end"] = "sub_agent_end"
    sub_agent_name: str
    session_id: str
    result: AgentResult
    review_result: Optional[Dict[str, Any]]

class ReviewStartEvent(StreamEvent):
    type: Literal["review_start"] = "review_start"
    sub_agent_name: str
    criteria: List[str]

class ReviewEndEvent(StreamEvent):
    type: Literal["review_end"] = "review_end"
    sub_agent_name: str
    score: float
    passed: bool
    feedback: str

class SupervisorDoneEvent(StreamEvent):
    type: Literal["supervisor_done"] = "supervisor_done"
    supervisor_session_id: str
    artifacts: Dict[str, Any]
    final_result: str

SupervisorStreamEvent = (
    ThinkingEvent | TextEvent | ToolStartEvent | ToolEndEvent |
    SubAgentStartEvent | SubAgentEndEvent |
    ReviewStartEvent | ReviewEndEvent |
    SupervisorDoneEvent | ErrorEvent
)
```

### 7.1 前端 SSE 事件格式（带 source 标记）

```json
{"type": "text", "content": "正在分析您的需求...", "source": "supervisor"}
{"type": "sub_agent_start", "sub_agent_name": "outline_writer", "source": "supervisor"}
{"type": "text", "content": "正在构思故事大纲...", "source": "outline_writer"}
{"type": "tool_start", "tool_name": "search_reference", "source": "outline_writer"}
{"type": "tool_end", "tool_name": "search_reference", "source": "outline_writer"}
{"type": "text", "content": "大纲已完成。", "source": "outline_writer"}
{"type": "sub_agent_end", "sub_agent_name": "outline_writer", "result": {...}, "source": "supervisor"}
{"type": "review_start", "sub_agent_name": "outline_writer", "criteria": [...], "source": "supervisor"}
{"type": "review_end", "sub_agent_name": "outline_writer", "score": 8.5, "passed": true, "source": "supervisor"}
{"type": "supervisor_done", "artifacts": {...}, "source": "supervisor"}
```

**前端渲染规则**：根据 `source` 字段渲染不同的 UI 区域（Supervisor 区域 / 各 SubAgent 区域）。

---

## 8. ToolExecutor 流式工具支持

```python
# tool.py — 新增 async generator 执行路径

class ToolExecutor:
    async def execute_streaming_tool(self, tool_call: ToolCall) -> AsyncGenerator[StreamEvent, None]:
        """
        执行返回 AsyncGenerator[StreamEvent] 的流式工具。
        透传所有事件，不缓冲。
        """
        tool_func = self.get_tool(tool_call.name)
        kwargs = dict(tool_call.arguments)
        if self.db and "db" not in kwargs:
            kwargs["db"] = self.db

        result = tool_func.execute(**kwargs)

        # 兼容：旧工具返回 ToolResult，新工具返回 AsyncGenerator
        if hasattr(result, "__aiter__"):
            async for event in result:
                yield event
        else:
            # 同步结果转为单个 ToolEndEvent
            yield ToolEndEvent(...)
```

---

## 9. SupervisorAgent 核心类

```python
# supervisor/supervisor.py

class SupervisorAgent:
    """
    Supervisor Agent。

    继承/组合标准 Agent 能力，复用 run()/stream() 模式。
    差异点：
    - 有自己的 system prompt（流水线描述 + 工具说明）
    - 持有 SupervisorContext（工作内存，SubAgent 无法访问）
    - 持有 SupervisorSession（session 关联管理）
    - 工具集 = {call_sub_agent, call_reviewer, get_workflow_state}
    - stream() 将 SubAgent 事件实时透传到 SSE
    """

    def __init__(
        self,
        supervisor_session_id: str,
        user_request: str,
        sub_agent_configs: Dict[str, SubAgentConfig],
        middlewares: List[AgentMiddleware],
        persist: PersistArg,
        model: str = "gemini-3-flash-preview",
        max_loop: int = 30,
    ):
        self.context = SupervisorContext(
            supervisor_session_id=supervisor_session_id,
            user_request=user_request,
        )
        self.session = SupervisorSession(supervisor_session_id)
        self._agent = create_agent(
            agent_name="supervisor",
            session_id=supervisor_session_id,
            prompt=self._build_system_prompt(),
            tools=self._build_tools(sub_agent_configs),
            max_loop=max_loop,
            persist=persist,
            middlewares=middlewares,
        )

    async def run(self, initial_input: str) -> AgentResult:
        """非流式执行，返回流水线最终结果。"""

    async def stream(self, initial_input: str):
        """
        流式执行，yield SupervisorStreamEvent。

        事件透传逻辑：
        - ToolStart/End 事件：透传（标记 source = 当前活跃的 sub_agent_name）
        - SubAgentStart/End 事件：透传
        - ReviewStart/End 事件：透传
        - Thinking/Text 事件：透传（标记 source）
        - SupervisorDoneEvent：最后 yield
        """

    def _build_system_prompt(self) -> str:
        return SUPERVISOR_SYSTEM_PROMPT_TEMPLATE.format(
            user_request=self.context.user_request,
        )

    def _build_tools(self, configs: Dict[str, SubAgentConfig]) -> List[Dict]:
        return [
            build_call_sub_agent_tool(configs),
            build_call_reviewer_tool(),
            build_get_workflow_state_tool(),
        ]
```

### 9.1 Supervisor System Prompt 模板

```
你是一个视频生成流水线的 Supervisor Agent。你的职责是：

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

## 当前用户需求
{user_request}
```

---

## 10. Factory

```python
# supervisor/factory.py

def create_supervisor(
    user_request: str,
    *,
    supervisor_name: str = "supervisor",
    model: str = "gemini-3-flash-preview",
    max_loop: int = 30,
    persist: PersistArg = "redis",
    middlewares: Optional[List[AgentMiddleware]] = None,
    sub_agent_configs: Dict[str, SubAgentConfig] = None,
) -> SupervisorAgent:
    """创建 SupervisorAgent 实例。"""
    supervisor_session_id = f"sv-{uuid4()}"
    return SupervisorAgent(
        supervisor_session_id=supervisor_session_id,
        user_request=user_request,
        sub_agent_configs=sub_agent_configs or {},
        middlewares=middlewares or [],
        persist=persist,
        model=model,
        max_loop=max_loop,
    )
```

---

## 11. API 接口

```python
# backend/app/api/supervisor.py

@router.post("/supervisor/stream")
async def supervisor_stream(request: SupervisorStreamRequest):
    """
    启动 Supervisor 流水线，流式返回 SSE 事件。

    请求体：
    {
        "user_request": "帮我生成一个科幻短片的剧本，时长2分钟",
        "model": "gemini-3-flash-preview",
        "sub_agent_configs": {
            "outline_writer": {...},
            "script_writer": {...},
            "storyboarder": {...}
        }
    }
    """
    supervisor = create_supervisor(
        user_request=request.user_request,
        model=request.model,
        sub_agent_configs=request.sub_agent_configs,
        persist="redis",
        middlewares=request.middlewares,
    )
    return StreamingResponse(
        supervisor.stream(request.user_request),
        media_type="text/event-stream",
    )
```

---

## 12. 实现顺序（分阶段）

### 阶段 1：基础设施
- [ ] `context.py` — SupervisorContext 模型
- [ ] `session.py` — SupervisorSession
- [ ] `events.py` — 流式事件扩展

### 阶段 2：工具层
- [ ] `reviewer.py` — Reviewer Agent 配置
- [ ] `tools.py` — call_sub_agent / call_reviewer / get_workflow_state
- [ ] `tool.py` — ToolExecutor 新增 execute_streaming_tool() 方法

### 阶段 3：SupervisorAgent
- [ ] `supervisor.py` — SupervisorAgent 核心类
- [ ] `factory.py` — create_supervisor()

### 阶段 4：集成
- [ ] `tools/supervisor_tools.py` — 注册工具到 ToolRegistry
- [ ] API 路由接入

---

## 13. 已知约束

1. **Supervisor 和 SubAgent 共用同一个 ToolRegistry**：ToolRegistry 全局单例，Supervisor 工具和业务工具共存，需要命名空间隔离（如 `supervisor.call_sub_agent` vs `outline_writer.generate`）
2. **SubAgent 的 Skill 注入**：SubAgent 通过 `create_agent(skill_lite_list=...)` 注入 Skill 知识，Supervisor 本身也可以注入 Skill（如 `supervisor_skill`）
3. **max_loop 设置**：Supervisor 的 max_loop 需要比 SubAgent 更大（建议 30+），因为 Supervisor 需要多轮决策
4. **Reviewer 的 prompt 工程**：Reviewer Agent 的 prompt 质量直接影响流水线效果，建议将 Reviewer 也设计为可配置的 Skill
