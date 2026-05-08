"""
FilmGenX 后端主入口。

启动方式（开发环境）：
    uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import os
from contextlib import asynccontextmanager

# uvicorn 默认只给自己的 access / error logger 配 handler，应用代码 ``logger.info``
# 走 root logger 会因为没 handler 被静默丢弃。这里在 import 任何 app.* 模块之前
# 装一次 basicConfig，保证 sub-agent prompt / call_sub_agent 等 INFO 级日志能落
# 到 stderr。LOG_LEVEL 环境变量可调（默认 INFO）。
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.api.v1.router import api_router  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.utils.evolink import evolink_client  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化资源，关闭时释放连接。"""
    # 启动阶段：此处可预热数据库连接池等（当前无需额外操作）
    yield
    # 关闭阶段：释放 Evolink HTTP 连接
    await evolink_client.close()


app = FastAPI(
    title="FilmGenX API",
    description="AI 动漫视频生产流水线 —— 《斗破苍穹》专项项目",
    version="0.1.0",
    lifespan=lifespan,
    # 生产环境关闭文档
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
)

# ---------------------------------------------------------------------------
# 跨域配置（开发环境放行所有来源）
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_ENV == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 路由注册
# ---------------------------------------------------------------------------
app.include_router(api_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# 健康检查（不走鉴权，供 k8s / 负载均衡探活）
# ---------------------------------------------------------------------------
@app.get("/health", tags=["系统"])
async def health_check():
    """服务健康检查。"""
    return {"status": "ok", "env": settings.APP_ENV}
