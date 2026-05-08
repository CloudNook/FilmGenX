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
| 2026-05-06 | Agent core | AgentLoop 重构 Slice 1：删除死代码 `_resume_from_checkpoint`；同时删除孤立测试 `test_review_harness.py`（reviewer 重构遗留，import 已废弃 `ReviewPolicy`）。 | Done | 无可见行为变化；测试保持 50 passed / 1 skipped。 |
| 2026-05-06 | Agent core | AgentLoop 重构 Slice 2：抽出 `_persist_turn(assistant_seq, content, metadata, usage, tool_persist_items, is_checkpoint)`，统一 run / stream_run 中"assistant 先写，tool 紧随其后"的持久化块。 | Done | 修复 `tool_executor=None` 分支下 `tool_persist_items` 未定义的潜在 UnboundLocalError。 |
| 2026-05-06 | Agent core | AgentLoop 重构 Slice 3：抽出 `_lookup_pending_tool_call(tool_call_id)`，去除三处 resume tool 查找的重复实现。 | Done | 行为对齐：仍走"从最后一条 assistant 回溯"的语义。 |
| 2026-05-06 | Agent core | AgentLoop 重构 Slice 4：`_handle_candidate_review` → 纯函数 `_decide_review_action`，返回 `ReviewDecision(action, events, feedback, review_exhausted)`。决策与副作用（追加 feedback、置 result 终态、`on_loop_end`、yield 事件）解耦，由调用方按需收尾。 | Done | review 调用点的状态机一目了然；后续 review 提到 while 外的依赖。 |
| 2026-05-06 | Agent core | AgentLoop 重构 Slice 5：`run()` 退化成 `stream_run` 的事件消费者；删除与 `_stream_loop` 95% 重复的 ~250 行循环体。同步删除 `_execute_pending_tool` / `_execute_single_tool` / `_record_tool_result`（仅被旧 run 使用）。HITL 中断由监听 `InterruptEvent` 后 `raise AgentInterrupted()` 维持原契约。 | Done | loop.py 1545 → 1124 行；修复 `stream_run` 在 None initial_input 下追加空 user 消息的旧 bug。 |
| 2026-05-06 | Agent core | AgentLoop 重构 Slice 6：`_stream_loop` 拆分为外层修订编排 + 内层 `_stream_until_candidate`。内层只负责 think/tool 迭代直到产出候选物（`_CandidateReady` sentinel）或终态（max_loop / fallback / HITL / 异常）；外层根据 `ReviewDecision` 决定 revise / pass / fail。Review 终于真正在 while 外处理。 | Done | 与原 `_stream_loop` 行为对齐；为后续把候选物生成、tool 执行、resume tool 进一步独立成更小单元铺路。 |
| 2026-05-06 | Agent core | AgentLoop 重构 Slice 7：`tool_executor` 改为构造时必填（原来 `Optional[ToolExecutor] = None`），删除 `_stream_until_candidate` 与 `_do_resume_tool` 中 `if self.tool_executor is None` 的死防御分支。Agent 唯一构造点 `_init_tool_executor()` 永远返回 `ToolExecutor()` 实例，None 路径在生产中无法触达。 | Done | 减少 ~30 行死代码；与"不为永远不会发生的场景加防御代码"原则对齐。 |
| 2026-05-06 | 测试 | 新增 `test_agent_loop_real_llm.py`：端到端真实 Gemini + 真实 PostgreSQL DBPersistStrategy，覆盖 think → tool → HITL 拦截 → resume → final 链路。 | Done | 数据真实落 `agent_messages` 表，session_id 用时间戳隔离每次跑。第一次 run 触发 HITL 拦截 → `error="interrupted"`；从 DB 恢复 checkpoint 后 resume(approve) 执行 pending tool → 拿到 1234*5678 的最终答案。无 `GOOGLE_API_KEY` 或 DB 不可达时 skip。 |
| 2026-05-06 | Agent core | 修复 `_do_resume_tool` 中 tool 消息在 in-memory 与 DB 之间 seq 断档：原来 `result.messages.append` 调一次 `_alloc_seq()`，紧接 `_persist("tool", ...)` 没传 seq 又自动 alloc 了一次，导致 DB 行 seq 比 result.messages 大 1。现在统一用一个 `tool_seq` 变量。 | Done | 真实 DB e2e 测试暴露的预存 bug；fix 后 DB 序号 0/1/2/3 连续。 |
| 2026-05-06 | Agent core | AgentLoop 重构 Slice 8：抽 `_execute_tool_calls_streaming(tool_calls)` + `_record_tool_results(tool_results, result)` 给 `_stream_until_candidate` 和 `_do_resume_tool` 共用。 | Done | 删除两处重复的"yield ToolStart → execute → 收 ToolEnd → 写 in-memory tool 消息"约 60 行；resume 现在和主路径走同一份 tool 执行实现。 |
| 2026-05-06 | Agent core | AgentLoop 重构 Slice 9：抽 `_emit_hitl_interrupt(...)` 把"标 checkpoint + 写 interrupt 快照 + yield InterruptEvent"三步合一。 | Done | `_stream_until_candidate` 拦截分支从 14 行内联代码降到 7 行调用；HITL 相关副作用集中。 |
| 2026-05-06 | Agent core | AgentLoop 重构 Slice 10：抽 `_finalize_terminal(result, *, error, raw_output)` 替换 7 处散落的 `result.error/finished/finished_at/loop_count` 终态赋值。 | Done | 终态写入语义统一（``error=None`` 视为成功）；调用点从 4-5 行减到 1 行；下游若新增 finalize 字段只需改 helper。 |
| 2026-05-06 | Agent core | AgentLoop 重构 Slice 11：把 `_stream_until_candidate` 内的 LLM 流式调用与 assistant 内存记账拆出 `_stream_llm_response(buffer_text)` + `_record_assistant_message(...)`。 | Done | LLM 调用通过 `_LLMStreamResult` sentinel 返回累计 content/thinking/final_chunk；assistant 记账返回 (seq, msg_idx)。`_stream_until_candidate` 主体压到 ~80 行编排代码。 |
| 2026-05-06 | Agent core | AgentLoop 重构 Slice 12：`agent.py` 抽 `_prepare_request(initial_input, request_id, resume)`，`Agent.run` 与 `Agent.stream` 各有 ~60 行 setup（init llm/tool_executor/inject skills/build loop/绑定 on_loop_*）合并。 | Done | agent.py 286 → 237 行；run/stream 现在只剩各自的 result 后处理逻辑。 |
| 2026-05-06 | Agent core | AgentLoop 重构 Slice 13：`tool_persist_items` 4-tuple `(tr, formatted, raw_content, tool_seq)` → `_PersistTurnItem` dataclass。 | Done | 调用点用 `item.tool_seq` 等命名属性，不再靠位置解构；可读性 + 类型友好。 |
| 2026-05-06 | Agent core | AgentLoop 重构 Slice 14：`_load_history` 中 Gemini `thought_signature` base64 解码 + raw 重建抽成 `_rebuild_persisted_tool_calls(persisted)`。 | Done | Provider 兼容代码从历史回放主路径里隔离；`_load_history` 主体回归"按 seq 排序逐条还原"的清晰形态。 |
| 2026-05-06 | Supervisor | Slice 15：Reviewer 下沉到 sub-agent 层，删除 Supervisor 的 `call_reviewer` 工具 + `supervisor/reviewer.py`。 | Done | `RegisteredAgent` 增 `reviewer: Optional[Any]` 字段；`call_sub_agent` 转发 `reviewer=registered.reviewer` 给 `create_agent`；删除 `call_reviewer` / `_build_call_reviewer_schema` / `build_reviewer_prompt` / `supervisor/reviewer.py`；HITL `auto_tool_list` 去掉 `"call_reviewer"`；测试同步更新。每个 sub-agent 可独立挂载 domain-specific ReviewerAgent，不再经由 Supervisor 工具中转。 |
| 2026-05-07 | Supervisor / 业务 | Sub-agent prompts + Pydantic 输出 schema + reviewer domain prompt 落地。 | Done | 新增 `app/agents/supervisor_agents.py` 装配 outline / script / storyboard 三个 sub-agent 的 system prompt + reviewer prompt + criteria；`app/schemas/agent_outputs/{outline,script,storyboard}.py` 用 Pydantic 类定义结构化输出契约；`RegisteredAgent` 加 `prompt` + `response_schema`，`call_sub_agent` 透传给 `create_agent`，修掉之前 prompt 被硬编码 `""` 的旧形态。测试 `test_default_registry_wiring.py` 钉死 prompt + schema + reviewer prompt 三件齐全。 |
| 2026-05-07 | Supervisor | Workflow 依赖 guard：`call_sub_agent` 入口拒绝上游未 fresh 的调用，返回结构化 ToolError。 | Done | 新增 `app/core/agent/tool_errors.py`（`ToolErrorPayload` + `tool_error()`）统一非异常类失败响应。`call_sub_agent` 在启动 sub-agent 前检查 `node_keys.depends_on`，未 fresh 时直接 yield `SubAgentEndEvent(result=tool_error(error_code="DEPENDENCY_NOT_SATISFIED", ...))`。`UNKNOWN_SUB_AGENT` 也对齐到同结构。LLM 能从 result 读到原因纠正，不抛异常。 |
| 2026-05-07 | Skill | Skill 模型按 Claude SKILL.md 风格重构（三层渐进披露）。 | Done | 加 `target_agents` (JSONB list, GIN 索引) / `body` (Text) / `references` (JSONB list[obj])；删 `title / content / examples / constraints / parameters / category / difficulty`。alembic 迁移 `skill_claude_style` 把旧 content + 拼接 examples / constraints / parameters 段落迁到 body。`agent._inject_skills` 默认按 `target_agents @> [agent_name]` 反查；`skill_names` 显式给出走子集（覆盖通道）。`load_skill_lite` 工具删除（L1 已系统注入），`load_skill` 简化为返回 body，新增 `load_skill_reference(name, ref_key)` 工具。 |
| 2026-05-07 | Skill | @ 引用语法 + 解析 + lint。 | Done | 三种 token：`@ref:<key>` / `@skill:<name>` / `@skill:<name>#<key>`，前后端都按这个语法读写。`services/skill_references.py` 提供 `parse_reference_tokens` + `lint_skill`，覆盖 DEAD_REF / ORPHAN_REF / UNKNOWN_SKILL / INACTIVE_SKILL / UNKNOWN_SKILL_REF / DUPLICATE_REF_KEY 六类 issue。`skill_parser.py` 重写：YAML frontmatter + body + `## reference: <key>` 章节剥离到 references 数组；旧格式（`## content` / `## examples` 等）兼容降级并给迁移 warning。Admin 编辑页加 @ 引用 picker（本 skill / 跨 skill 两栏）和 lint 按钮。 |
| 2026-05-07 | Supervisor / 业务 | Sub-agent 链路扩到 8 节点（路径 B：单一职责拆分）。 | Done | 新增 5 个 Pydantic 输出 schema（`visual_style` / `character_ref` / `scene_ref` / `frame_prompt` / `video_prompt`）+ 5 个对应 sub-agent 装配（业务 prompt + reviewer + criteria 全在 `app/agents/supervisor_agents.py`）。workflow 节点图扩到 8 个：outline → script → storyboard → visual_style → character_ref → scene_ref → frame_prompt → video_prompt。`backend/tests/unit/core/supervisor/test_extended_registry.py` + `test_factory.py` 钉死。 |
| 2026-05-07 | Tools | 新增 `app/core/tools/media_tools.py`：4 个生成工具（`generate_image_pro` / `generate_image_flash` / `generate_video_text_to_video` / `generate_video_image_to_video`）。 | Superseded | 同日审查后收敛为 2 工具，见下条。框架边界设计 + OSS 落 URL 设计保留。 |
| 2026-05-07 | Tools | media_tools 收敛为 2 个工具：`generate_image` / `generate_video`，model 走参数（带默认值）。**本期改为文字驱动**，不接受参考图入参。 | Done | 删除 4 个老工具；`generate_image(model="gemini-3-pro-image-preview" 默认 / "gemini-3.1-flash-image-preview")`、`generate_video(model="kling" 默认 / "seedance" 占位返回 MODEL_NOT_AVAILABLE)`。后续新增模型 / provider 不开新工具，扩 model 字面量 + utils 加 adapter 即可。`video_prompt` schema 同步删除 `seed_image_source` / `seed_image_url` / `end_frame_hint`；`frame_prompt` 的 `character_refs` / `scene_ref` 保留但 description 标注"工具不消费，等 memory 接入后驱动 reference image"。`frame_prompt_agent.extra_tool_names=["generate_image"]`、`video_prompt_agent.extra_tool_names=["generate_video"]`。tests 同步重写。理由：避免按模型拆工具表面 + asset_code 注入会把业务建模带进框架，等 project-level memory 落地后再加 reference_assets 入参。 |

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
| High | Agent core | 完善 Review Harness 的事件、持久化和默认 reviewer Agent 策略。 | In Progress | ReviewStart/EndEvent、Redis 评审记录、on_exhausted、ReviewerAgent + create_reviewer_agent + structured output、DBPersistStrategy.append_review_record（含 advisory lock）、领域特化 reviewer prompt（outline / script / storyboard）已落地；剩余：escalate_hitl 策略、跨域 reviewer 集成测试、reviewer 命中后的 trace 指标。 |
| High | Harness Engineering | 建立 Agent 运行 trace / replay / evaluation 基础能力。 | Pending | 支撑失败复盘、版本对比、prompt/roadbook/review 变化后的回放评估。 |
| Medium | Agent core | 分片清理 `AgentLoop` 的工具执行、resume 和流式/非流式重复代码。 | Done | Slice 1-14 完成；loop.py 从 1545 行压缩到 ~1200 行，核心循环结构清晰。 |
| High | Core 边界 | 后续 Agent 框架能力继续保持 `backend/app/core` 内接口驱动。 | Ongoing | 避免 core 框架耦合具体业务实现。 |
| High | 业务接轨 | 设计 core 到 AI 视频业务的适配边界。 | Pending | core 提供接口，业务接入人物图、场景图、剧情衔接、分镜制作等流程，不让 core 依赖业务细节。 |
| High | AI 视频业务 | 人物一致性工程方案。 | Pending | 需要支持人物图生成、角色特征记忆、LoRA/参考图/提示词一致性策略。 |
| High | AI 视频业务 | 场景一致性工程方案。 | Pending | 需要支持场景图生成、空间关系、风格、时间和镜头连续性。 |
| High | AI 视频业务 | 剧情逻辑和衔接一致性方案。 | Pending | 大纲、剧本、分镜和镜头之间需要可评估的依赖和冲突检测。 |
| High | AI 视频业务 | 分镜制作 Agent 流程。 | Pending | 需要结合 Review Agent、RoadBook、上下文召回，产出可执行分镜计划。 |
| High | 测试工程 | 建立 Agent harness 级测试集。 | Pending | 覆盖 review-revise、roadbook recall、context recall、HITL reject/approve、supervisor workflow replay。 |
| Medium | 测试工程 | 建立 AI 视频业务回归样例。 | Pending | 固定人物、场景、剧情、分镜样例，用于验证一致性和质量提升。 |
| Medium | Harness Engineering | 澄清 Harness Engineering 在本项目里的精确定义。 | Pending | 当实现细节依赖该定义时，先向用户确认。 |
| High | Memory / 业务接轨 | Project-level memory（剧本级跨会话上下文）。 | Pending | FilmGenX 一个 project 即一个剧本，outline / script / 角色设定 / 场景设定 / 已生成 asset / 剧情进展都是 project 级长期资产。不同会话只是生成不同集数。需要 memory 模型 + 召回接口让 sub-agent 跨会话感知这些上下文（不再依赖 outline_agent → script_agent → ... 同会话顺序）。落地后 generate_image / generate_video 才能基于 memory 中的角色/场景图做 reference 驱动。 |
| High | Tools | memory 落地后给 `generate_image` / `generate_video` 加 `reference_assets` 入参。 | Pending | 当前是文字驱动；memory 完成后 sub-agent 在 prompt 里引用角色 / 场景 → 编排层从 memory 取对应参考图喂给图生图 / 图生视频接口。配套字段：`frame_prompt.character_refs` / `scene_ref`、`video_prompt` 的 seed_image / end_frame 这些已删字段会按新接入方式重新引入（不一定还叫这个名）。 |
| Medium | Tools | Seedance 适配器接入 + `generate_video model="seedance"` 路径解禁。 | Pending | 当前 `app/utils/seedance.py` 是占位 NotImplementedError，工具层调到 model='seedance' 直接返回 MODEL_NOT_AVAILABLE。等 utils 真接入后只需改 media_tools 内部 dispatch。 |
