# 核心配置模块
# 负责应用级别的基础设施配置，不包含业务逻辑：
#
#   config.py       - 环境变量读取与应用配置（数据库URL、API密钥、存储路径等）
#   security.py     - JWT 鉴权、密码哈希、API Key 验证
#   logging.py      - 统一日志配置（结构化日志，区分开发/生产环境）
#   exceptions.py   - 全局异常定义与 HTTP 异常处理器
#   dependencies.py - FastAPI 依赖注入（获取DB会话、当前用户等公共依赖）
#
#   agent/          - Agent 框架
#       base.py     - AgentConfig、AgentMessage、AgentResult 等数据模型
#       llm.py      - LLM 适配器，封装 call_llm/call_llm_stream
#       skill.py    - Skill 加载与执行器（Stub，后期从数据库加载）
#       loop.py     - Agent 循环控制器（Stub）
#       persist.py  - Agent 结果持久化
#       factory.py  - create_agent 工厂函数，返回 Agent 实例
#       agent.py    - Agent 主类，提供 run() / stream() 方法
#
#   skill/          - Skill 动态加载系统
#       base.py     - SkillBase 抽象基类
#       registry.py - SkillRegistry，支持装饰器注册和自动发现
#
#   tools/          - Tool 装饰器注册系统
#       registry.py - ToolRegistry，@register_tool 装饰器
#
#   middleware/     - Agent 中间件系统
#       chain.py    - AgentMiddleware 基类、MiddlewareChain 链式调用
#       builtin.py  - 内置中间件（LoggingMiddleware、PersistMiddleware）
#
#   supervisor/     - Supervisor 元 Agent（动态调度 SubAgent）
#       supervisor.py   - SupervisorAgent 核心类
#       factory.py      - create_supervisor() 工厂
#       tools.py        - call_sub_agent / call_reviewer / get_workflow_state
#       context.py      - SupervisorContext 工作内存
#       session.py      - SupervisorSession 管理
#       events.py       - SupervisorStreamEvent 事件类型
#       reviewer.py     - Reviewer Agent 配置
