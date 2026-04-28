# FilmGenX 工程 TODO

本文档记录 Agent 框架相关的共享工程操作和后续任务。

## 操作日志

| 日期 | 范围 | 操作 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 2026-04-24 | Agent core | 移除 `ResumeDecision.feedback`，resume 决策只保留 `action`。 | Done | 保持 HITL resume 协议最小化。 |
| 2026-04-24 | 工程文档 | 新增 `AGENTS.md`，记录长期 Agent 框架约定。 | Done | 明确 `backend/app/core` 是框架边界和核心资产。 |
| 2026-04-24 | 工程文档 | 新增本 TODO 操作日志，并从 `AGENTS.md` 链接过来。 | Done | 后续有意义的框架操作都同步记录到这里。 |
| 2026-04-24 | 工程文档 | 新增 `Agent.md -> AGENTS.md` 兼容软链接。 | Done | 保留用户指定的文件入口，同时使用标准 agent instruction 文件名。 |
| 2026-04-24 | Agent core | 新增通用 Review Harness 第一版。 | Done | `create_agent` 支持 `review_policy` 和 reviewer 注入；候选输出未通过 review 时写入 synthetic reviewer feedback 并回到 AgentLoop。 |
| 2026-04-24 | Agent core | 将 Review Harness 细节从 `AgentLoop` 抽到 `app.core.agent.review`。 | Done | `AgentLoop` 保留候选结果 review 控制点，reviewer 调用、默认 prompt、JSON 解析和 feedback 构造由 `ReviewHarness` 承担。 |
| 2026-04-24 | Agent core | 为业务自定义 reviewer 增加显式 core 协议。 | Done | 新增 `Reviewer` Protocol、`ReviewOutput` 和 `ReviewError`，非法 reviewer 返回值会给出明确错误。 |
| 2026-04-28 | 工程文档 | 扩展 `AGENTS.md` 和 TODO，记录长期 Agent 框架、AI 视频业务和 RoadBook 方向。 | Done | 新增当前能力、RoadBook 概念、业务落地方向、技术问题和必读代码地图。 |
| 2026-04-29 | Agent core | 新增 `ReviewStartEvent` / `ReviewEndEvent` 流式事件。 | Done | `ReviewHarness.review_candidate` 返回 `ReviewOutcome`（review + events），AgentLoop 在 stream_run 中 yield，便于前端展示评审进度。 |
| 2026-04-29 | Agent core | `ReviewPolicy.on_exhausted` 策略可配置。 | Done | 支持 `"fail"`（默认）和 `"accept_last"`；`AgentResult.review_exhausted` 标记是否耗尽修订次数。 |
| 2026-04-29 | Agent core | Review 持久化接入 `PersistStrategy.append_review_record`。 | Done | 默认 no-op；Redis 策略实现 `agent:reviews:{session_id}` list，支撑后续 trace/replay。 |
| 2026-04-29 | 测试 | 新增 `test_create_agent_review.py`：7 用例覆盖 create_agent + review_policy 全链路。 | Superseded | 后续被 ReviewerAgent 重构覆盖；见下条。 |
| 2026-04-29 | Agent core | Reviewer 重构：拆出 `ReviewerAgent` + `create_reviewer_agent` 工厂。 | Done | 删除 `ReviewPolicy` 和 `_run_default_reviewer` 隐式分支；`create_agent(reviewer=...)` 是唯一挂载入口；reviewer 携带 `max_revision_rounds / on_exhausted / min_score / json_schema`。 |
| 2026-04-29 | Agent core | `AgentConfig.response_schema` 透传到 LLMAdapter，OpenAI adapter 升级为 `response_format=json_schema` 模式。 | Done | Reviewer 输出走 Provider 原生结构化输出；Gemini 已就绪，OpenAI GPT-4o+ 可用。 |
| 2026-04-29 | 测试 | `test_create_agent_review.py` 重写为 11 个用例覆盖 ReviewerAgent 全链路。 | Done | 覆盖默认 reviewer、自定义 prompt/schema/criteria、on_exhausted=fail/accept_last、流式事件、纯函数 reviewer、reviewer=None、response_schema 透传、持久化、非法 JSON / 非法 ReviewResult。 |

## 待办事项

| 优先级 | 范围 | 任务 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| High | Agent core | 设计上下文召回接口。 | Pending | 覆盖 RAG、会话历史、项目上下文、RoadBook、Skill 摘要等来源；输出必须有来源、置信度和适用范围。 |
| High | Agent core | 设计全局记忆和分层记忆模型。 | Pending | 至少区分 user / project / agent / tool / workflow scope，并处理冲突、过期和覆盖。 |
| High | Agent core | 设计上下文腐烂治理机制。 | Pending | 需要 freshness、confidence、source priority、conflict policy，避免旧信息污染当前任务。 |
| High | Agent core | 设计信息权重提升机制。 | Pending | 用户明确纠正、review 失败原因、业务硬规则、RoadBook 命中应有可解释的优先级。 |
| High | Harness Engineering | 定义“用户纠正 -> 路书 -> 相似场景复用”的自我优化契约。 | Pending | 需要覆盖采集、归纳、召回、应用和审计事件。 |
| High | RoadBook | 实现 RoadBook 条目模型和存储接口。 | Pending | 条目字段建议包含 scope、trigger、preference、evidence、confidence、status、created_from_session。 |
| High | RoadBook | 实现 reject -> adjust -> approve 的偏好归纳。 | Pending | 从 HITL 工具调用被拒、后续参数调整、最终 approve 中总结用户偏好。 |
| High | RoadBook | 实现显式记忆写入。 | Pending | 用户说“记住这个”“以后都这样”“放到全局信息”时，将信息写入 RoadBook。 |
| High | RoadBook | 实现 RoadBook 召回和注入策略。 | Pending | 只注入当前任务相关条目，并保留来源和适用说明，避免上下文污染。 |
| High | Agent core | 完善 Review Harness 的事件、持久化和默认 reviewer Agent 策略。 | In Progress | ReviewStart/EndEvent、Redis 评审记录、on_exhausted、ReviewerAgent + create_reviewer_agent + structured output 已落地；剩余：DB 持久化（DBPersistStrategy.append_review_record）、escalate_hitl 策略、领域特化 reviewer prompt 库。 |
| High | Harness Engineering | 建立 Agent 运行 trace / replay / evaluation 基础能力。 | Pending | 支撑失败复盘、版本对比、prompt/roadbook/review 变化后的回放评估。 |
| Medium | Agent core | 分片清理 `AgentLoop` 的工具执行、resume 和流式/非流式重复代码。 | Pending | 每片都必须保持现有测试绿灯；优先抽 ToolCall runner 和 Candidate lifecycle。 |
| High | Core 边界 | 后续 Agent 框架能力继续保持 `backend/app/core` 内接口驱动。 | Ongoing | 避免 core 框架耦合具体业务实现。 |
| High | 业务接轨 | 设计 core 到 AI 视频业务的适配边界。 | Pending | core 提供接口，业务接入人物图、场景图、剧情衔接、分镜制作等流程，不让 core 依赖业务细节。 |
| High | AI 视频业务 | 人物一致性工程方案。 | Pending | 需要支持人物图生成、角色特征记忆、LoRA/参考图/提示词一致性策略。 |
| High | AI 视频业务 | 场景一致性工程方案。 | Pending | 需要支持场景图生成、空间关系、风格、时间和镜头连续性。 |
| High | AI 视频业务 | 剧情逻辑和衔接一致性方案。 | Pending | 大纲、剧本、分镜和镜头之间需要可评估的依赖和冲突检测。 |
| High | AI 视频业务 | 分镜制作 Agent 流程。 | Pending | 需要结合 Review Agent、RoadBook、上下文召回，产出可执行分镜计划。 |
| High | 测试工程 | 建立 Agent harness 级测试集。 | Pending | 覆盖 review-revise、roadbook recall、context recall、HITL reject/approve、supervisor workflow replay。 |
| Medium | 测试工程 | 建立 AI 视频业务回归样例。 | Pending | 固定人物、场景、剧情、分镜样例，用于验证一致性和质量提升。 |
| Medium | Harness Engineering | 澄清 Harness Engineering 在本项目里的精确定义。 | Pending | 当实现细节依赖该定义时，先向用户确认。 |
