# FilmGenX Agent 工程约定

本文档记录本仓库中 Agent 协作需要长期遵守的工程约定。

`Agent.md` 是指向本文档的兼容软链接。

## Core 框架边界

- 所有关于 Agent 框架的设计都放在 `backend/app/core` 下。
- `backend/app/core` 是我们的核心资产，应与具体业务实现保持清晰边界。
- Agent 流程必须由接口驱动，包括 registry、tool schema、middleware hook、runtime context、persistence strategy、workflow definition 等契约。
- 不要用一次性的业务实现反向驱动 core 框架行为。业务代码应适配 core 暴露的接口，而不是让 core 依赖业务细节。

## 当前已有框架能力

- ReAct Agent：`create_agent -> Agent -> AgentLoop -> ToolExecutor` 是底层执行内核。
- Supervisor Agent：负责高层工作流编排、sub-agent 调度、workflow 状态治理和流式生命周期。
- Human In The Loop：通过 middleware 在工具调用前中断，支持 approve / reject / resume。
- 自动上下文管理：Agent 消息、tool call、checkpoint、usage 和 supervisor 事件都有持久化基础。
- Middleware：提供 before / after / loop / tool / finalize 等 hook，是 harness 能力的重要挂载面。
- 披露式 Skills 注入：Agent 先拿 Skill 摘要，需要时再通过 `load_skill` / `load_skill_reference` 渐进式加载详细知识；Skill 通过 `target_agents` 反查注入，admin 编辑页支持 `@ref:` / `@skill:` 引用语法 + lint。
- Review Harness：`create_agent(reviewer=...)` 显式挂载 reviewer；reviewer 由独立工厂 `create_reviewer_agent(prompt, json_schema, max_loop, max_revision_rounds, on_exhausted, ...)` 构造，返回 `ReviewerAgent`；不传则完全无 review 链路。reviewer 内部 Agent 通过 `AgentConfig.response_schema` 走 Provider 原生结构化输出。`Reviewer` Protocol 保留作为最小 callable 契约。
- Memory Harness：`create_agent(memory=MemoryConfig(...))` 与 Reviewer / Skill 同级。framework 内部 `MemoryHarness` 协调 recall（同步带 timeout，AgentLoop 主路径显式调用）+ write（raw → pre_filter → extract → post_filter → provider，filter 评分制 + chain 聚合 + 阈值）。`Provider` / `Extractor` / `Ranker` / `Embedder` 都是 Protocol。Phase 1 默认实现：`PgvectorMemoryProvider`（双表 `memory_entries` 向量 + `memory_profile` KV）、`GeminiLLMExtractor`、`GeminiEmbedder`。KV 走 UPDATE-in-place，6 个闭集 kind（character / scene / style / preference / outline / script）由 `app/memory/taxonomy.py` 严格校验。`memory_save` 工具双字段（KV `kind/key/value` + 向量 `content/entry_kind`）可单写可同写，**只挂在 supervisor**，sub-agent JSON-locked 不挂工具。
- Token 实时计费：`AgentLoop` 每次 LLM finish chunk 都 yield `UsageEvent(usage, accumulated_usage, loop_count)`；supervisor 与 sub-agent 各自触发，`call_sub_agent` 把 sub-agent UsageEvent 打上 `source=<sub_agent_name>` 转发；前端按这条事件实时更新 token 卡片。
- 资产句柄系统：图像 / 视频产物自动入 `assets` 表并分配 `img-<uuid>` / `vid-<uuid>` 稳定句柄；**Agent 永远只看 asset_code，不看 URL**。`generate_image` 传 `asset_codes` 自动走 i2i 保人物 / 场景一致性。
- SSE Tail：`GET /supervisor/{session_id}/stream?from_seq=N` 先 replay `supervisor_events` 历史事件再 1s 轮询新事件；`text` / `thinking` 走 per `(source, session_id)` 聚合 buffer，`usage` 事件时 flush，写入频率从 per-chunk 降到 per-LLM-call。

## 正在推进的核心方向

- 上下文召回：Memory Harness Phase 0/1 已落地（pgvector + Gemini extractor/embedder + 闭集 taxonomy + UPDATE-in-place）；下一步要把 RAG / session recall / RoadBook recall 统一进同一套召回接口，避免散落。
- Review Agent：目标是让任意 Agent 的输出都能被评审、评分、修订，而不是只在 Supervisor 中使用 reviewer。
- Harness Engineering：围绕 Agent 运行时建立可追踪、可回放、可评估、可审阅、可持久化、可自我优化的工程控制层。
- RoadBook（路书）：记录用户纠正、拒绝工具调用、后续 approve、明确要求记住的信息，并在相似场景召回，让 Agent 学习用户习惯。可与 Memory `add_entry` 向量路径复用底层存储。
- 业务接轨：core 不直接依赖业务；FilmGenX 业务通过 `app/agents/supervisor_agents.py` + `app/memory/*` + `app/core/tools/media_tools.py` 装配 8 个 sub-agent 的 prompt / schema / reviewer / 工具，core 仅暴露 Protocol。

## RoadBook 概念约定

RoadBook 是本项目面向“Agent 越用越懂用户”的长期记忆机制，不等同于普通聊天历史。

- 采集来源包括：用户 reject 工具调用、用户多轮修正后 approve、用户明确说“记住这个”、review 中反复出现的质量问题。
- RoadBook 条目应尽量结构化：scope、trigger、preference、evidence、confidence、status、created_from_session。
- RoadBook 召回应服务于当前 Agent 任务，而不是无脑注入全部历史，避免上下文腐烂。
- RoadBook 必须可审计：Agent 应能解释某条偏好来自哪里、为什么在当前场景被应用。
- RoadBook 不应替代系统约束。稳定用户偏好可以召回；全局硬规则才提升为更高权重约束。

## AI 视频业务落地方向

业务层会围绕 AI 视频制作持续扩展，core 框架需要支撑但不耦合这些实现。

- 自动生成人物图、场景图、镜头图、分镜和视频片段。
- 维护人物一致性、场景一致性、剧情逻辑一致性、镜头衔接一致性。
- 支持专业视频制作链路：剧情大纲、剧本、角色、场景、分镜、运镜、灯光、风格、审核和重做。
- 很多问题只能在落地中发现，框架设计要保留追踪、回放、评估和渐进优化的接口。

## 需要重点研究的技术问题

- RAG 上下文召回：如何从项目、会话、RoadBook、知识库中召回相关上下文。
- 全局记忆：用户级、项目级、Agent 级、工具级记忆如何分层。
- 上下文腐烂：如何避免旧信息、低置信信息、冲突信息污染当前推理。
- 信息权重提升：关键用户纠正、审核意见、业务硬规则如何在上下文中获得更高优先级。
- 自我优化闭环：失败、review、reject/approve、用户修正如何沉淀为可复用经验。

## 必读代码地图

开始任何 Agent core 工作前，先按任务读取相关代码，不要凭印象改。

- Agent 入口和配置：`backend/app/core/agent/factory.py`、`backend/app/core/agent/agent.py`、`backend/app/core/agent/base.py`
- Agent 循环内核：`backend/app/core/agent/loop.py`
- Review Harness：`backend/app/core/agent/review.py`、`backend/app/core/agent/reviewer.py`、`backend/tests/unit/core/agent/test_create_agent_review.py`
- Tool 执行：`backend/app/core/agent/tool.py`、`backend/app/core/tools/registry.py`
- 持久化：`backend/app/core/agent/persist/base.py`、`backend/app/core/agent/persist/db_strategy.py`、`backend/app/core/agent/persist/models.py`
- Middleware：`backend/app/core/middleware/chain.py`、`backend/app/core/middleware/builtin.py`
- Skills：`backend/app/core/skill/loader.py`、`backend/app/core/tools/builtin.py`、`backend/app/services/skill_references.py`
- Memory（框架契约）：`backend/app/core/agent/memory/harness.py`、`backend/app/core/agent/memory/tool.py`、`backend/app/core/agent/memory/filter.py`
- Memory（默认实现）：`backend/app/memory/factory.py`、`backend/app/memory/taxonomy.py`、`backend/app/memory/providers/pgvector_provider.py`、`backend/app/memory/extractors/gemini_llm.py`、`backend/app/memory/embeddings/gemini.py`
- Supervisor：`backend/app/core/supervisor/supervisor.py`、`runtime.py`、`context.py`、`workflow.py`、`tools.py`、`registry.py`、`factory.py`
- Supervisor 持久化和查询：`backend/app/core/supervisor/persist/store.py`、`backend/app/core/supervisor/query.py`
- 业务装配：`backend/app/agents/supervisor_agents.py`（8 个 sub-agent 的 prompt / response_schema / reviewer / criteria）、`backend/app/schemas/agent_outputs/`、`backend/app/core/tools/media_tools.py`
- API 接轨示例：`backend/app/api/v1/endpoints/supervisor.py`（含 `/stream` tail endpoint）、`backend/app/api/v1/endpoints/workspaces.py`、`backend/app/api/v1/endpoints/agent_schemas.py`
- 测试护栏：`backend/tests/unit/core/agent/`、`backend/tests/unit/core/supervisor/`、`backend/tests/unit/api/v1/endpoints/test_supervisor_endpoint.py`

## Harness Engineering

- Harness Engineering 是本项目的核心思想。
- 新增 Agent 框架能力时，优先考虑可追踪、可回放、可评估、可审阅、可持久化，以及可持续自我优化。
- 如果某个任务依赖 Harness Engineering 的项目内具体定义，而上下文不足，先向用户确认再实现。

## 工程和测试要求

- 框架能力要先有接口契约，再有业务适配；不要让业务实现倒逼 core 内部形状。
- 涉及 AgentLoop、Review、Middleware、Tool、Persist、Supervisor 生命周期的改动必须补单元测试。
- 每个重构切片都要保持现有 core agent、core supervisor、supervisor endpoint 测试绿灯。
- 新增长期方向或完成重要工程操作时，同步更新 `docs/engineering/TODO.md`。

## 开发 TODO

- 共享工程操作日志维护在 [docs/engineering/TODO.md](docs/engineering/TODO.md)。
- 每次进行有意义的框架或文档变更，都要同步更新 TODO 日志。
- TODO 日志是开发工程的一部分，需要和当前工程状态保持同步。
