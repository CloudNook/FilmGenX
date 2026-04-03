# 核心配置模块
# 负责应用级别的基础设施配置，不包含业务逻辑：
#
#   config.py       - 环境变量读取与应用配置（数据库URL、API密钥、存储路径等）
#   security.py     - JWT 鉴权、密码哈希、API Key 验证
#   logging.py      - 统一日志配置（结构化日志，区分开发/生产环境）
#   exceptions.py   - 全局异常定义与 HTTP 异常处理器
#   dependencies.py - FastAPI 依赖注入（获取DB会话、当前用户等公共依赖）
