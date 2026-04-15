# FilmGenX

AI 驱动的动画内容生产系统，从剧本到成片的全流程智能化。

## 前置依赖

| 服务 | 版本 | 用途 |
|------|------|------|
| PostgreSQL | 15+ | 主数据库 |
| Redis | 7+ | Celery 任务队列 |
| Python | 3.13+ | 后端运行时 |
| uv | latest | Python 包管理器 |
| Node.js | 20+ | 前端运行时 |

## 快速开始

### 1. 后端

```bash
cd backend

# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入实际配置（数据库、Redis、API Key 等）

# 执行数据库迁移
uv run alembic upgrade head

# 启动 API 服务
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 启动 Celery Worker（新终端）
# Linux/macOS
uv run celery -A app.tasks.celery_app worker --loglevel=info -Q default,video,image

# Windows（使用 solo 模式避免进程池兼容问题）
uv run celery -A app.tasks.celery_app worker --loglevel=info -Q default,video,image --pool=solo
```

### 2. 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:3000

## Docker 部署

适合服务器直接拉代码后启动，内置：
- PostgreSQL
- Redis
- FastAPI backend
- Celery worker
- Next.js frontend

先准备后端配置文件：

```bash
cp backend/.env.example backend/.env
```

然后按需编辑 `backend/.env`。
Docker 启动时会直接读取这个文件，`backend`、`worker`、`postgres` 共用同一份配置。
其中：
- `POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD` 直接决定容器内 PostgreSQL 账号
- `backend` 和 `worker` 会基于这组值自动拼出容器内可用的数据库连接
- `REDIS_URL` 在 Docker 场景下也会自动切到容器内的 `redis`

启动命令：

```bash
docker compose up -d --build
```

停止命令：

```bash
docker compose down
```

查看日志：

```bash
docker compose logs -f
```

启动后访问：

- 前端：http://服务器IP:3000
- 后端健康检查：http://服务器IP:8000/health

说明：
- 后端容器启动时会自动执行 `alembic upgrade head`
- 默认会自动创建并使用容器内的 PostgreSQL 和 Redis
- 如果需要真实 AI/OSS 能力，把这些值直接填进 `backend/.env`：`EVOLINK_API_KEY`、`GOOGLE_API_KEY`、`OSS_ACCESS_KEY_ID`、`OSS_ACCESS_KEY_SECRET`、`OSS_BUCKET_NAME`、`OSS_ENDPOINT`
- 若不设置这些 key，基础页面和数据库服务可以启动，但相关 AI/存储能力不可用

## 数据库迁移

```bash
cd backend

# 执行所有迁移
uv run alembic upgrade head

# 回退一个版本
uv run alembic downgrade -1

# 查看当前版本
uv run alembic current

# 生成新的迁移脚本（修改 model 后执行）
uv run alembic revision --autogenerate -m "描述"
```

## 项目结构

```
FilmGenX/
├── backend/
│   ├── main.py                    # FastAPI 入口
│   ├── alembic.ini                # Alembic 配置
│   ├── app/
│   │   ├── api/v1/endpoints/      # API 端点
│   │   ├── core/config.py         # 配置（pydantic-settings）
│   │   ├── db/
│   │   │   ├── session.py         # 数据库连接
│   │   │   └── migrations/        # 迁移脚本
│   │   ├── models/                # SQLAlchemy 模型
│   │   ├── schemas/               # Pydantic Schema
│   │   ├── repositories/          # 数据访问层
│   │   ├── tasks/                 # Celery 异步任务
│   │   └── utils/                 # 工具函数
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── app/                       # Next.js App Router 页面
│   │   ├── (auth)/                # 认证相关页面
│   │   └── (main)/                # 主业务页面
│   ├── components/
│   │   ├── chat/                  # AI 对话工作流组件
│   │   ├── layout/                # 布局组件
│   │   └── ui/                    # shadcn/ui 组件
│   ├── lib/
│   │   ├── api.ts                 # API 客户端
│   │   └── auth.tsx               # 认证逻辑
│   ├── package.json
│   └── next.config.mjs
└── docs/                          # 设计文档
```
