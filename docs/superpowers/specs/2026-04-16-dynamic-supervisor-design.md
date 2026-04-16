# Dynamic Supervisor Orchestrator 设计方案

**日期**: 2026-04-16
**状态**: 已批准
**设计人**: Codex

---

## 1. 背景

FilmGenX 的目标不是做一个固定的三段式流水线，而是做一个面向创作者的 AI 视频创作平台。

对于真实 3D AI 漫剧，核心难点不是单个镜头生成，而是：

1. 用户可以从任意阶段回退修改
2. 角色、场景、分镜、运镜之间存在强依赖
3. 需要在不牺牲创作者控制权的前提下，给出稳定的编排与建议
4. 需要为后续 Harness Engineering 预留结构化评测与回放能力

当前 `backend/app/core/supervisor` 的实现仍然以固定阶段推进为主，无法承载“动态选专家 Agent + 用户主导回退 + 一致性治理”的目标。

---

## 2. 设计目标

本次重构的目标不是一次性把所有专家 Agent 做完，而是先把稳定的高层编排骨架搭好。

必须满足：

1. **不改 `create_agent` 主干行为**
   现有 `create_agent -> Agent -> AgentLoop -> ToolExecutor` 被视为稳定内核。
   新能力优先做高层封装，不侵入底层循环。

2. **Supervisor 完全重构**
   旧的固定阶段 prompt 不再作为设计依据。
   新 Supervisor 是“版本化工作流编排器”，不是“固定流程执行器”。

3. **用户决定改什么**
   用户可以要求修改剧本、角色图、场景图、分镜组、运镜等任意节点。
   系统不强控流程。

4. **系统必须治理依赖**
   当上游节点变化时，下游节点不能静默继续沿用。
   受影响节点需要被标记为 `pending_confirmation`。

5. **自动继续是可选能力**
   默认由 Supervisor 给建议；
   用户可开启“按建议自动继续”。

6. **核心专家可插拔**
   专家 Agent 列表后续逐步扩展。
   本次先实现可插拔注册与编排能力，不把专家集合硬编码死。

---

## 3. 选型结论

采用 **方案 B：分层 Orchestrator 架构**。

系统拆成四层：

1. **Agent Runtime 层**
   复用现有 `create_agent` 和 `AgentLoop`。

2. **Supervisor Orchestrator 层**
   理解用户意图、读取工作流状态、选择专家 Agent、给出建议、在允许时继续执行。

3. **Versioned Workflow State 层**
   管理节点、版本、依赖、产物、状态、推荐动作。

4. **Harness Layer**
   记录执行轨迹、节点质量、待确认状态、推荐动作，为后续评测和回放提供数据基础。

---

## 4. 关键原则

### 4.1 用户控制编辑权

用户决定：

- 改哪个节点
- 是否接受系统建议
- 是否自动继续执行
- 哪些待确认节点继续沿用

### 4.2 Supervisor 控制分析权

Supervisor 负责：

- 将用户请求映射到工作流节点
- 计算受影响节点
- 标记 `fresh / pending_confirmation / running / completed / failed`
- 给出下一步推荐动作
- 在允许时调用对应专家 Agent

### 4.3 系统控制状态一致性

系统不能再用 `current_phase` 这种单值状态描述整个流程。

必须改成：

- 工作流节点 `WorkflowNode`
- 节点版本 `NodeVersion`
- 节点依赖 `depends_on`
- 节点状态 `status`
- 推荐动作 `SuggestedAction`

### 4.4 不把专家写死进核心逻辑

Supervisor 不直接假设只有 `outline_writer / script_writer / storyboarder`。

它只依赖一份 **Agent Registry**：

- 节点名称
- 节点类型
- 所需专家 Agent
- 依赖节点
- 可用 tools
- 可选 skills

---

## 5. 新的最小架构

### 5.1 Workflow Graph

引入版本化工作流图模型：

```python
class WorkflowNodeDefinition(BaseModel):
    key: str
    label: str
    node_type: str
    depends_on: list[str]
    produces_artifact: bool = True
    can_run_automatically: bool = True

class WorkflowNodeState(BaseModel):
    key: str
    version: int = 0
    status: Literal[
        "missing",
        "fresh",
        "pending_confirmation",
        "ready",
        "running",
        "completed",
        "failed",
    ] = "missing"
    artifact: dict[str, Any] | None = None
    last_agent: str | None = None
    updated_at: datetime | None = None

class WorkflowSnapshot(BaseModel):
    profile: str
    nodes: dict[str, WorkflowNodeState]
    dependency_map: dict[str, list[str]]
    suggested_actions: list[SuggestedAction]
    auto_run: bool = False
```

### 5.2 Agent Registry

引入可插拔 Agent 注册表：

```python
class RegisteredAgent(BaseModel):
    name: str
    label: str
    description: str
    node_keys: list[str]
    tools: list[dict[str, Any]] = []
    skill_names: list[str] = []
    model: str = "gemini-3-flash-preview"
```

这层只负责声明能力，不强耦合业务实现。

### 5.3 Supervisor Context

`SupervisorContext` 从“阶段型上下文”升级成“工作流型上下文”：

- 用户请求
- 工作流快照
- 会话映射
- 评审历史
- 执行历史
- 用户偏好（是否自动继续）

### 5.4 SuggestedAction

Supervisor 对用户的输出不只是文本，还要有结构化推荐：

```python
class SuggestedAction(BaseModel):
    action: Literal["run_agent", "confirm_node", "revise_node", "review_impacts"]
    target_node: str
    reason: str
    agent_name: str | None = None
    blocking_nodes: list[str] = []
```

---

## 6. 回退与待确认机制

这是本次设计最重要的部分。

### 6.1 用户修改任意节点

例如用户说“重新修改剧本”，系统会：

1. 增加 `script` 节点版本
2. 写入新的脚本 artifact
3. 将下游依赖节点标为 `pending_confirmation`

例如：

- `shot_group_plan`
- `storyboard`
- `camera_motion`

### 6.2 为什么选 `pending_confirmation`

我们不采用：

- `只提示可忽略`
- `强制必须重做`

而采用：

- **待确认**

原因：

1. 更符合创作者平台定位
2. 保留用户主导权
3. 又不会让依赖关系失控
4. 后续适合做 Harness 回放和质量分析

### 6.3 用户与系统职责边界

用户负责：

- 决定是否重做
- 决定是否接受建议

系统负责：

- 识别影响
- 标注过期
- 给出推荐

---

## 7. Supervisor 运行方式

Supervisor 的系统 prompt 不再描述固定阶段，而描述编排职责：

1. 读取当前工作流状态
2. 识别用户是在“创建 / 修改 / 确认 / 继续执行”
3. 判断是否需要调用专家 Agent
4. 判断是否需要先确认受影响节点
5. 若用户允许，按建议自动继续

其可用工具仍然基于现有 Agent runtime，但变成新的通用集合：

- `call_sub_agent`
- `get_workflow_state`
- `update_workflow_node`
- `confirm_workflow_node`
- `suggest_next_actions`

其中：

- `call_sub_agent` 继续复用现有 Agent 机制
- 其他工具优先在高层完成状态操作

---

## 8. 与现有代码的兼容策略

### 8.1 保持不变

- `app.core.agent.factory.create_agent`
- `app.core.agent.Agent`
- `app.core.agent.loop.AgentLoop`
- `app.core.agent.tool.ToolExecutor`

### 8.2 重点重构

- `app.core.supervisor.context`
- `app.core.supervisor.tools`
- `app.core.supervisor.supervisor`
- `app.core.supervisor.factory`
- `app.core.supervisor.__init__`

### 8.3 尽量兼容现有 API

保留：

- `create_supervisor(...)`
- `/api/v1/supervisor/stream`
- `/api/v1/supervisor/{session_id}/state`
- `/api/v1/supervisor/{session_id}/resume`

但这些入口返回的状态内容会升级为新版工作流快照。

---

## 9. Harness Engineering 落地点

本次不做完整 Harness 平台，但必须把结构预埋好。

最小落地点：

1. **每次节点执行记录版本**
2. **每次用户修改记录来源**
3. **每次下游失效记录影响链**
4. **每次 Supervisor 推荐动作结构化保存**
5. **每次 Agent 运行记录输入、输出、节点、状态变化**

这会让后续可以做：

- 失败回放
- 节点级 A/B 测试
- 质量评分统计
- 自动评测基准

---

## 10. 本次实施范围

本次实现只做稳定骨架，不做完整专家生态。

### 10.1 要实现

1. 版本化工作流节点模型
2. 依赖失效与 `pending_confirmation`
3. 可插拔 Agent Registry
4. 新版 Supervisor Context
5. 新版 Supervisor 工具集合
6. 新版 SupervisorAgent 高层编排
7. 兼容现有 API 入口
8. 单元测试覆盖核心状态机行为

### 10.2 暂不实现

1. 全量 AI 漫剧专家 Agent
2. 完整 UI 编辑器
3. 完整 Harness 后台
4. 自动剪辑 / 自动配音 / 自动终剪

---

## 11. 风险与控制

### 风险 1：Supervisor 过于抽象，难以落地

控制：

- 先实现通用节点图和状态机
- 暂时只保留少量默认节点定义
- 把专家实现推迟到插件层

### 风险 2：与现有 API 断裂

控制：

- 保持 `create_supervisor` 和现有 endpoints 不变
- 仅升级返回的上下文结构

### 风险 3：又回到 prompt 驱动的脆弱流程

控制：

- 关键依赖判断放进 Python 状态层
- 不把“节点失效判断”交给 LLM 自由发挥

---

## 12. 结论

本次重构要建立的是：

`稳定 Agent Runtime`
`+ 版本化 Workflow Graph`
`+ 用户主导的待确认机制`
`+ 可插拔专家注册`
`+ 可扩展 Harness 数据基础`

这样后续即使继续补 `角色生图 Agent`、`场景生图 Agent`、`运镜 Agent`、`一致性 Agent`，也不需要再频繁推翻底层 Supervisor 架构。
