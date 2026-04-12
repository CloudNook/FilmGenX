# Agent Framework Human-in-the-Loop (HITL) Design

**Date:** 2026-04-12
**Status:** Draft
**Depends on:** `2026-04-11-supervisor-design.md` (Supervisor base implementation)

---

## 1. Problem Statement

HITL (Human-in the-Loop) 目前仅作为 SupervisorAgent 的私有实现存在（`asyncio.Event` 阻塞、`submit_review()`、`HumanReviewEvent`），存在三个架构问题：

1. **HITL 不属于框架层** — 当前 HITL 是 SupervisorAgent 的专属能力，但任何 Agent 都可能需要人工审核。Supervisor 本质只是 `create_agent()` + 专有 tools + system prompt 的封装，HITL 应该是 Agent 框架的通用能力。
2. **SSE 长连接阻塞** — `asyncio.Event.wait()` 在 SSE 流中阻塞等待人工审核，无法应对代理超时和服务器重启。
3. **无状态持久化** — 审核状态仅存在于内存中的 Python 对象，服务器重启后丢失。

## 2. Design Approach: Framework-Level Interrupt/Resume

借鉴 LangGraph 的 `interrupt/resume` 模式，将 HITL 作为 Agent 框架的一等公民能力。

### 2.1 核心原则

**HITL 是 Agent 框架的能力，不是 Supervisor 的私有功能。**

```
正确的设计:

  Agent Framework (框架级 HITL)
  ├── AgentConfig.interrupt_config    — 配置中断策略
  ├── AgentLoop                       — 检测中断点，yield InterruptEvent
  ├── Agent.resume()                  — 从 checkpoint 恢复执行
  └── InterruptEvent                  — 框架级中断事件

  SupervisorAgent (应用层，只是 create_agent 的封装)
  └── create_agent(interrupt_config=InterruptConfig(
        tool_names=["call_sub_agent"],   // 哪些 tool 执行完需要审核
        ...                              // Supervisor 特定配置
      ))
```

### 2.2 两阶段 SSE + REST 模式

中断时关闭 SSE 流，持久化状态到 DB；恢复时创建新 SSE 流。

```
Phase 1: Start → Interrupt
  POST /supervisor/stream → SSE → ... → InterruptEvent → [DONE]

Phase 2: Resume → Continue
  POST /supervisor/{session_id}/resume → SSE → ... → DoneEvent → [DONE]
```

## 3. Framework-Level HITL: InterruptConfig

### 3.1 InterruptConfig（框架级配置）

在 `app/core/agent/base.py` 中新增：

```python
class InterruptMode(str, Enum):
    """中断模式。"""
    AFTER_TOOL = "after_tool"     # ToolEndEvent 后中断（审核工具结果）
    BEFORE_TOOL = "before_tool"   # ToolStartEvent 前中断（审批工具调用）

class InterruptConfig(BaseModel):
    """
    Agent 框架级 HITL 配置。

    任何通过 create_agent() 创建的 Agent 都可以配置中断策略。
    AgentLoop 在检测到匹配条件时自动中断执行。
    """
    enabled: bool = False
    mode: InterruptMode = InterruptMode.AFTER_TOOL
    # 哪些 tool 触发中断。空列表 = 所有 tool 都触发。
    tool_names: List[str] = []
    # 中断时携带的附加上下文（由业务层填充）
    context: Dict[str, Any] = {}
```

### 3.2 配置方式

```python
# 通过 create_agent() 配置 HITL
agent = create_agent(
    agent_name="supervisor",
    session_id=session_id,
    prompt="...",
    tools=tool_schemas,
    interrupt_config=InterruptConfig(
        enabled=True,
        mode=InterruptMode.AFTER_TOOL,
        tool_names=["call_sub_agent"],  # 只在 call_sub_agent 完成后中断
    ),
)
```

### 3.3 设计决策：为什么放在 AgentConfig 而不是 tool 层

虽然 LangGraph 支持 `interrupt()` 函数在 tool 内部调用，但我们选择**声明式配置**而非**命令式调用**：

- 声明式：Agent 的创建者（Supervisor、API 层）决定哪些 tool 需要审核，tool 本身不需要知道
- 命令式：tool 内部调用 `interrupt()`，tool 需要感知框架

声明式的好处：
1. tool 代码不需要改动（`call_sub_agent` 不需要感知 HITL）
2. 同一个 tool 在不同 Agent 中可以有不同的 HITL 策略
3. 前端/API 层完全控制审核粒度

## 4. Event Model Changes

### 4.1 框架级：InterruptEvent（新增到 `base.py`）

```python
class InterruptEvent(BaseModel):
    """
    Agent 执行被中断，等待外部输入。

    这是框架级事件，任何配置了 interrupt_config 的 Agent 都可能产生。
    """
    type: Literal["interrupt"] = "interrupt"
    session_id: str
    # 触发中断的 tool 信息
    tool_name: str
    tool_call_id: str
    # 模式决定内容：
    # AFTER_TOOL: tool_result 是工具返回值
    # BEFORE_TOOL: tool_result 是 None，arguments 包含拟执行的参数
    tool_result: Any = None
    arguments: Dict[str, Any] = {}
    # 可用的操作列表
    available_actions: List[str] = ["approve", "reject", "edit", "skip", "abort"]
    # 业务层附加上下文
    context: Dict[str, Any] = {}
```

### 4.2 应用层：Supervisor 的 InterruptEvent 扩展

Supervisor 在 `context` 字段中携带 supervisor 特定信息：

```python
# Supervisor 层在 yield InterruptEvent 时附加的 context:
{
    "sub_agent_name": "outline_writer",
    "artifacts_snapshot": {"outline_writer": "..."},
    "current_phase": "outline",
    "completed_nodes": [],
}
```

Supervisor 仍保留 `SupervisorDoneEvent` 等应用级事件。`HumanReviewEvent` 改为 `InterruptEvent` + supervisor context 的语义等价物。

### 4.3 事件模型变更总结

| 事件 | 层级 | 变更 |
|------|------|------|
| `InterruptEvent` | 框架 (`base.py`) | **新增** — 通用中断事件 |
| `HumanReviewEvent` | 应用 (`supervisor/events.py`) | **移除** — 被 `InterruptEvent` + context 替代 |
| `SubAgentStartEvent` | 应用 (`supervisor/events.py`) | 保留 |
| `SubAgentEndEvent` | 应用 (`supervisor/events.py`) | 保留，但不再触发 HITL（由框架处理） |
| `SupervisorDoneEvent` | 应用 (`supervisor/events.py`) | 保留 |
| `ReviewStartEvent` / `ReviewEndEvent` | 应用 (`supervisor/events.py`) | 保留 |

## 5. AgentLoop Changes

### 5.1 中断检测逻辑

在 `AgentLoop.stream_run()` 中，**ToolEndEvent 之后**插入中断检查：

```python
# AgentLoop.stream_run() 中，工具执行完毕后：

# --- 现有代码：yield ToolEndEvent ---
yield ToolEndEvent(...)

# --- 新增：框架级中断检查 ---
if self._should_interrupt(tool_name=tc.name):
    yield InterruptEvent(
        session_id=self.session_id,
        tool_name=tc.name,
        tool_call_id=tc.id,
        tool_result=tr.result,
        arguments=tc.arguments,
        available_actions=["approve", "reject", "edit", "skip", "abort"],
        context=self.interrupt_config.context,
    )
    # 保存 checkpoint 后结束 generator
    await self._save_checkpoint()
    # 不再 continue 循环，generator 正常结束
    return
```

### 5.2 Checkpoint 保存

中断时，AgentLoop 将当前执行状态序列化：

```python
async def _save_checkpoint(self) -> None:
    """保存中断点到持久化存储。"""
    checkpoint = AgentCheckpoint(
        session_id=self.session_id,
        messages=self.messages,           # 完整对话历史
        loop_count=self.loop_count,       # 当前循环次数
        interrupt_tool_name=...,
        interrupt_config=self.interrupt_config,
    )
    # 通过 persist strategy 保存
    if self.persist:
        await self.persist.save_checkpoint(checkpoint)
```

### 5.3 中断条件判断

```python
def _should_interrupt(self, tool_name: str) -> bool:
    if self.interrupt_config is None or not self.interrupt_config.enabled:
        return False
    if self.interrupt_config.mode != InterruptMode.AFTER_TOOL:
        return False
    # 空 tool_names = 所有 tool 都中断
    if not self.interrupt_config.tool_names:
        return True
    return tool_name in self.interrupt_config.tool_names
```

## 6. Agent.resume() — 框架级恢复

### 6.1 Agent 新增方法

```python
class Agent:
    # ... 现有代码 ...

    async def resume(
        self,
        action: Literal["approve", "reject", "edit", "skip", "abort"],
        feedback: Optional[str] = None,
        edited_content: Optional[str] = None,
        *,
        request_id: Optional[str] = None,
    ):
        """
        从中断点恢复执行（流式），yield StreamEvent。

        action 决定如何处理被中断的工具结果：
        - approve: 工具结果原样保留，继续 LLM 循环
        - reject: 注入反馈到 messages，LLM 决定下一步
        - edit: 替换工具结果为 edited_content，继续
        - skip: 移除工具结果，注入跳过指令，继续
        - abort: yield DoneEvent (failed)，终止
        """
```

### 6.2 恢复逻辑

```python
async def resume(self, action, feedback=None, edited_content=None, *, request_id=None):
    await self._inject_skills()
    self._init_llm()
    self._init_tool_executor()

    rid = request_id or str(uuid4())

    # 1. 从 persist 加载 checkpoint
    checkpoint = await self.persist.load_checkpoint(self.session_id)

    # 2. 根据 action 修改 messages
    if action == "abort":
        yield DoneEvent(result=AgentResult(agent_name=self.config.agent_name, error="Aborted by user"))
        return

    if action == "approve":
        # 不修改 messages，直接继续
        pass
    elif action == "reject":
        # 追加用户反馈作为新消息
        checkpoint.messages.append({
            "role": "user",
            "content": f"[Human Review Feedback] {feedback}",
        })
    elif action == "edit":
        # 替换最后一个 tool 消息的内容
        for msg in reversed(checkpoint.messages):
            if msg["role"] == "tool":
                msg["content"] = edited_content
                break
    elif action == "skip":
        # 追加跳过指令
        checkpoint.messages.append({
            "role": "user",
            "content": "[Human Review] Skip this step, proceed to next.",
        })

    # 3. 创建新 AgentLoop，注入恢复的 messages
    loop = AgentLoop(
        config=self.config,
        llm=self._llm,
        tool_executor=self._tool_executor,
        persist=self.persist,
        session_id=self.session_id,
        request_id=rid,
        interrupt_config=self.interrupt_config,  # 保留中断配置
        initial_messages=checkpoint.messages,      # 恢复的对话历史
        initial_loop_count=checkpoint.loop_count,  # 恢复的循环计数
    )

    # 4. 继续 stream_run（无新的 user input，从 messages 继续）
    async for event in loop.stream_run(""):
        yield event
```

### 6.3 AgentLoop 构造函数扩展

```python
class AgentLoop:
    def __init__(
        self,
        # ... 现有参数 ...
        interrupt_config: Optional[InterruptConfig] = None,
        initial_messages: Optional[List[Dict]] = None,      # 恢复时注入
        initial_loop_count: int = 0,                         # 恢复时注入
    ):
        # ...
        self.interrupt_config = interrupt_config
        if initial_messages is not None:
            self.messages = initial_messages
        self.loop_count = initial_loop_count
```

## 7. AgentConfig & Factory Changes

### 7.1 AgentConfig 新增字段

```python
class AgentConfig(BaseModel):
    # ... 现有字段 ...
    interrupt_config: Optional[InterruptConfig] = None
```

### 7.2 create_agent() 新增参数

```python
def create_agent(
    # ... 现有参数 ...
    interrupt_config: Optional[InterruptConfig] = None,
) -> Agent:
    config = AgentConfig(
        # ... 现有字段 ...
        interrupt_config=interrupt_config,
    )
    return Agent(config=config, ...)
```

## 8. PersistStrategy Extension

### 8.1 Checkpoint 模型

```python
class AgentCheckpoint(BaseModel):
    """中断时的 Agent 状态快照。"""
    session_id: str
    messages: List[Dict[str, Any]]    # 完整对话历史
    loop_count: int
    interrupt_tool_name: str
    interrupt_config: InterruptConfig
    created_at: datetime
```

### 8.2 PersistStrategy 新增方法

```python
class PersistStrategy(ABC):
    # ... 现有方法 ...

    @abstractmethod
    async def save_checkpoint(self, checkpoint: AgentCheckpoint) -> None:
        """保存中断检查点。"""

    @abstractmethod
    async def load_checkpoint(self, session_id: str) -> Optional[AgentCheckpoint]:
        """加载中断检查点。"""

    @abstractmethod
    async def clear_checkpoint(self, session_id: str) -> None:
        """清除检查点（恢复成功后调用）。"""
```

### 8.3 RedisPersistStrategy 实现

Checkpoint 存储为 Redis hash，key = `agent:checkpoint:{session_id}`，TTL = 24h。

对于数据库持久化，复用 `supervisor_workflows` 表的 `interrupt_state` 字段（见第 9 节）。

## 9. Supervisor Changes (Application Layer)

### 9.1 SupervisorAgent 简化

SupervisorAgent 移除所有 HITL 私有实现，改为使用框架能力：

**移除：**
- `_human_review` 字段
- `_review_event: asyncio.Event`
- `_review_feedback` 字段
- `submit_review()` 方法
- `_inject_feedback_to_prompt()` 方法
- `stream()` 中的 `asyncio.Event.wait()` 阻塞逻辑
- `HumanReviewEvent` 的产生逻辑

**保留：**
- `SupervisorContext` — 工作内存
- `SupervisorSession` — session 映射
- `stream()` 的透传逻辑（yield 子 agent 事件）
- Supervisor 特有事件：`SubAgentStartEvent`, `SubAgentEndEvent`, `SupervisorDoneEvent`

**新增：**
- 构造函数接受 `interrupt_config: Optional[InterruptConfig]`，传递给内部 Agent
- `resume()` 方法：封装框架级 `Agent.resume()` + Supervisor 上下文恢复

### 9.2 call_sub_agent tool 与框架 HITL 的协作

关键问题：`InterruptConfig.tool_names = ["call_sub_agent"]` 会在**任何** `call_sub_agent` 调用后中断，但业务上可能只想审核特定子 agent（如只审核 `outline_writer`）。

**解决方案：InterruptConfig.context 携带动态过滤条件。**

Supervisor 在创建时设置：
```python
InterruptConfig(
    enabled=True,
    mode=InterruptMode.AFTER_TOOL,
    tool_names=["call_sub_agent"],
    context={
        "review_sub_agents": ["outline_writer", "storyboarder"],  # 只审核这些子 agent
    },
)
```

AgentLoop 的中断检查扩展：
```python
def _should_interrupt(self, tool_name: str, tool_result: Any = None) -> bool:
    # ... 基本检查 ...
    # 业务层过滤：检查 context 中的 review_sub_agents
    review_filter = self.interrupt_config.context.get("review_sub_agents", [])
    if review_filter and tool_result:
        # call_sub_agent 的 result 包含 sub_agent_name
        sub_agent_name = tool_result.get("sub_agent_name", "") if isinstance(tool_result, dict) else ""
        if sub_agent_name not in review_filter:
            return False
    return True
```

**但更优的设计是：让 tool_result 携带结构化信息。** `call_sub_agent` 的 `SubAgentEndEvent` 已经有 `sub_agent_name`。AgentLoop 在检查时可以访问最近一个 tool 的结构化返回值。

实际上，由于 `call_sub_agent` 是 async generator（yield 中间事件，最终返回 result dict），`ToolEndEvent.result` 已经包含 `{"output": "...", "sub_agent_name": "outline_writer"}` 这样的信息。

所以在 `_should_interrupt` 中：
```python
def _should_interrupt(self, tool_name: str, tool_result: Any = None) -> bool:
    # ... 基本检查 ...
    # 业务过滤
    ctx = self.interrupt_config.context
    if ctx.get("review_sub_agents"):
        result = tool_result or {}
        if isinstance(result, str):
            return False  # 无法解析，不中断
        sub_name = result.get("sub_agent_name", "")
        if sub_name and sub_name not in ctx["review_sub_agents"]:
            return False
    return True
```

### 9.3 SupervisorAgent.resume()

```python
async def resume(
    self,
    action: str,
    feedback: Optional[str] = None,
    edited_content: Optional[str] = None,
) -> AsyncGenerator:
    """从中断点恢复 Supervisor 执行。"""
    from app.core.supervisor.events import SupervisorDoneEvent

    async for event in self._agent.resume(
        action=action,
        feedback=feedback,
        edited_content=edited_content,
    ):
        # 透传框架级事件（Thinking, Text, ToolStart, ToolEnd, InterruptEvent, DoneEvent）
        if hasattr(event, "source") and getattr(event, "source", None) is None:
            event.source = "supervisor"

        # 将框架级 InterruptEvent 包装为 supervisor 语义的事件
        # 前端通过 context 字段获取 supervisor 特定信息
        yield event

        # DoneEvent → yield SupervisorDoneEvent
        if isinstance(event, DoneEvent):
            yield SupervisorDoneEvent(
                supervisor_session_id=self.supervisor_session_id,
                artifacts=dict(self.context.artifacts),
                final_result=event.result.raw_output or "Pipeline completed",
            )
```

### 9.4 SupervisorContext 与 checkpoint 的关系

InterruptEvent 的 `context` 字段携带 SupervisorContext 的快照：

```python
# Supervisor 在 AgentLoop 检测到中断时，将 context 注入 InterruptEvent
# 这通过 InterruptConfig.context 动态更新实现

# 方案：在 call_sub_agent tool 内部，每次调用完成后更新 InterruptConfig.context
# AgentLoop 在 yield InterruptEvent 时读取最新的 context
```

具体实现：`call_sub_agent` 在完成时更新 `supervisor_context`，而 `InterruptConfig.context` 指向 `supervisor_context` 的引用（通过 tool_ctx 机制已实现）。

## 10. API Design

### 10.1 通用 Agent API（框架级）

```python
# 新增到 app/api/v1/endpoints/ 下，适用于所有 Agent
POST /api/v1/agents/{session_id}/resume
Body: {
    "action": "approve" | "reject" | "edit" | "skip" | "abort",
    "feedback": "optional feedback",
    "edited_content": "only for edit"
}
Response: SSE text/event-stream
```

### 10.2 Supervisor API（应用级路由）

Supervisor API 代理到通用 Agent resume：

```python
POST /api/v1/supervisor/{session_id}/resume
# 内部调用 Agent.resume()
```

### 10.3 修改 Start Pipeline

```python
POST /api/v1/supervisor/stream
Body: {
    ...现有字段,
    human_review: bool = false,
    review_nodes: ["outline_writer", "storyboarder"]  // 可选
}
```

### 10.4 查询中断状态

```python
GET /api/v1/supervisor/{session_id}/state
Response: {
    "status": "waiting_review",
    "interrupt": {
        "tool_name": "call_sub_agent",
        "context": {
            "sub_agent_name": "outline_writer",
            "artifacts_snapshot": {"outline_writer": "..."},
        }
    }
}
```

### 10.5 Review Actions

| Action | Framework Behavior | Supervisor Behavior |
|--------|-------------------|-------------------|
| `approve` | 保留 tool result，继续 LLM 循环 | 子 agent 结果通过，supervisor 继续 |
| `reject` | 注入 feedback 到 messages | supervisor LLM 决定重试或换策略 |
| `edit` | 替换 tool result 为 edited_content | 覆盖子 agent 输出，supervisor 继续 |
| `skip` | 注入跳过指令到 messages | supervisor 跳过当前子 agent |
| `abort` | yield DoneEvent (failed) | 流水线终止 |

## 11. Database Changes

### 11.1 agent_checkpoints 表（通用）

新建通用 checkpoint 表，供所有 Agent 使用：

```sql
CREATE TABLE agent_checkpoints (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL UNIQUE,
    agent_name VARCHAR(50) NOT NULL,
    messages JSON NOT NULL,           -- 完整对话历史
    loop_count INTEGER NOT NULL DEFAULT 0,
    interrupt_tool_name VARCHAR(100),
    interrupt_config JSON,            -- InterruptConfig 快照
    context JSON,                     -- 业务层附加上下文
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,  -- 过期时间（可选）
    INDEX idx_session_id (session_id),
    INDEX idx_expires_at (expires_at)
);
```

### 11.2 supervisor_workflows 表扩展

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `hitl_enabled` | Boolean | `false` | 是否启用 HITL |
| `review_nodes` | JSON | `null` | 配置的审核节点列表 |
| `status` | String | — | 新增 `waiting_review` 状态值 |

`interrupt_state` 不再需要单独存此处 — 通用 checkpoint 在 `agent_checkpoints` 表中。

### 11.3 WorkflowService 新增方法

- `save_interrupt(session_id, checkpoint_id)` — 关联 workflow 与 checkpoint
- `load_interrupt(session_id)` — 加载 checkpoint + workflow 信息

## 12. Frontend Integration

### 12.1 前端状态机

```
IDLE → STREAMING → WAITING_REVIEW → STREAMING → ... → COMPLETED
                      │
                      └──→ ABORTED
```

### 12.2 事件处理

前端通过 `event.type` 统一处理：

| event.type | 来源 | 前端行为 |
|-----------|------|---------|
| `interrupt` | 框架 | 渲染审核面板，等待用户操作 |
| `sub_agent_start` | Supervisor | 显示子 agent 面板 |
| `sub_agent_end` | Supervisor | 子 agent 完成 |
| `supervisor_done` | Supervisor | 流水线完成 |
| `thinking` / `text` / `tool_start` / `tool_end` / `done` | 框架 | 现有渲染逻辑 |

### 12.3 审核面板数据来源

`InterruptEvent.context` 携带 supervisor 特定信息：

```json
{
    "type": "interrupt",
    "session_id": "sv-xxx",
    "tool_name": "call_sub_agent",
    "tool_result": {"output": "...", "sub_agent_name": "outline_writer"},
    "available_actions": ["approve", "reject", "edit", "skip", "abort"],
    "context": {
        "sub_agent_name": "outline_writer",
        "artifacts_snapshot": {},
        "current_phase": "outline"
    }
}
```

前端从 `context.sub_agent_name` 判断当前审核的是哪个子 agent，从 `tool_result.output` 展示内容。

### 12.4 组件结构

```
SupervisorPipeline
├── PipelineStatus          // 状态栏
├── EventRenderer           // SSE 事件渲染
│   ├── SupervisorMessage
│   ├── SubAgentPanel
│   └── ReviewResult
├── InterruptReviewPanel    // 通用中断审核面板
│   ├── ContentPreview      // tool_result.output 预览
│   ├── ActionButtons       // approve/reject/edit/skip/abort
│   ├── FeedbackInput       // reject 时的反馈输入
│   └── EditEditor          // edit 时的内容编辑器
└── PipelineTimeline
```

## 13. File Change Summary

### Agent Framework (核心改动)

| File | Change | Description |
|------|--------|-------------|
| `core/agent/base.py` | Modify + Add | 新增 `InterruptConfig`, `InterruptMode`, `InterruptEvent`, `AgentCheckpoint` |
| `core/agent/loop.py` | Modify | 新增 `_should_interrupt()`, `_save_checkpoint()`；`stream_run()` 中 ToolEndEvent 后插入中断检查 |
| `core/agent/agent.py` | Modify | 新增 `resume()` 方法 |
| `core/agent/factory.py` | Modify | `create_agent()` 接受 `interrupt_config` 参数 |
| `core/agent/persist/base.py` | Modify | `PersistStrategy` 新增 `save_checkpoint()`, `load_checkpoint()`, `clear_checkpoint()` |
| `core/agent/persist/redis_strategy.py` | Modify | 实现 checkpoint 的 Redis 存取 |

### Supervisor (应用层简化)

| File | Change | Description |
|------|--------|-------------|
| `supervisor/supervisor.py` | Modify | 移除 HITL 私有实现，使用框架 `interrupt_config`；新增 `resume()` |
| `supervisor/factory.py` | Modify | 接受 `interrupt_config` 并传递给 `create_agent()` |
| `supervisor/events.py` | Modify | 移除 `HumanReviewEvent`（由框架 `InterruptEvent` 替代） |
| `supervisor/tools.py` | Modify | `call_sub_agent` 返回值携带 `sub_agent_name` 供框架过滤 |

### API & Data

| File | Change | Description |
|------|--------|-------------|
| `models/agent_checkpoint.py` | **New** | `AgentCheckpoint` ORM 模型 |
| `models/supervisor_workflow.py` | Modify | 新增 `hitl_enabled`, `review_nodes` 字段 |
| `services/supervisor_workflow_service.py` | Modify | 新增 `save_interrupt()`, `load_interrupt()` |
| `api/v1/endpoints/supervisor.py` | Modify | 新增 `GET /state`, `POST /resume`；修改 start 请求体 |
| `api/v1/endpoints/agents.py` | **New** (可选) | 通用 Agent resume 端点 |
| `repositories/agent_checkpoint.py` | **New** | Checkpoint CRUD |
| `alembic/versions/xxx_add_hitl.py` | **New** | 数据库 migration |

### Frontend

- `SupervisorPipeline` 容器组件
- `InterruptReviewPanel` 通用审核组件
- SSE 连接管理器

## 14. Migration Path

1. **Phase 1: Framework HITL** — 在 Agent 框架层实现 interrupt/resume
2. **Phase 2: Supervisor Adaptation** — Supervisor 迁移到框架 HITL，移除私有实现
3. **Phase 3: API Endpoints** — 新增 resume/state 端点
4. **Phase 4: Frontend** — 实现审核面板和 SSE 管理

## 15. Out of Scope

- `BEFORE_TOOL` 模式实现（当前只做 `AFTER_TOOL`，`BEFORE_TOOL` 预留接口）
- Tool 内部调用 `interrupt()` 的命令式 API
- 并行分支中断
- WebSocket 传输
- 状态版本管理 / 回滚
- 框架级 checkpoint 清理策略（先简单 TTL，后续优化）
