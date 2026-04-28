# CLAUDE.md

本文件是 Claude 在 FilmGenX 仓库工作时的入口指引。Claude Code 会在每次会话开始时自动加载本文件。

## 必读文档

开始任何工作前，先读取并遵守 [AGENTS.md](AGENTS.md)。`Agent.md` 是同一文档的兼容软链接。AGENTS.md 是本仓库的工程契约源头，本文件不复述其内容，只补充 Claude 专属的协作约定。

## Claude 工作准则

### 1. 先读再改
- 涉及 Agent core / Supervisor / Review / Middleware / Tool / Persist 的改动，先按 AGENTS.md 的"必读代码地图"读取相关文件，再动手。
- 不要凭印象修改 core 框架的形状。需要 Harness Engineering 的项目内具体定义而上下文不足时，先向用户确认。

### 2. 接口先行
- core 框架能力先定义接口契约，再做业务适配。
- 不允许用一次性业务实现反向驱动 `backend/app/core` 的内部形状。

### 3. 测试护栏
- 改动 AgentLoop / Review / Middleware / Tool / Persist / Supervisor 生命周期 必须补单元测试。
- 每个切片提交前确认 `backend/tests/unit/core/agent/`、`backend/tests/unit/core/supervisor/`、`backend/tests/unit/api/v1/endpoints/test_supervisor_endpoint.py` 保持绿灯。

### 4. 同步 TODO 日志
- 完成有意义的框架或文档变更后，同步更新 [docs/engineering/TODO.md](docs/engineering/TODO.md)。
- 新增长期方向时也要在 TODO 日志中记录。

### 5. Harness Engineering 优先
- 新增 Agent 框架能力时，优先满足：可追踪、可回放、可评估、可审阅、可持久化、可自我优化。
- RoadBook、RAG 召回、Review Agent 等长期方向涉及时，按 AGENTS.md 中的概念约定执行。

## 沟通风格

- 默认中文回复。用户用英文提问时切换英文。
- 简洁直接，不复述用户已知信息，不在结尾加多余总结。
- 引用代码位置使用 markdown 链接格式：[文件名](path#Lline)。

## 不要做的事

- 不要在没有读 AGENTS.md / 相关代码时就动 core 框架。
- 不要让 core 直接依赖业务实现。
- 不要跳过测试或 `--no-verify` 提交。
- 不要在未经用户确认时执行不可逆操作（force push、reset --hard、删除分支等）。
- 用户没要求时不要主动 commit。
