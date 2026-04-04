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
uv run celery -A app.tasks.celery_app worker --loglevel=info -Q default,video,image
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
