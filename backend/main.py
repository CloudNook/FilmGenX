"""
FilmGenX 后端主入口。

启动方式（开发环境）：
    uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.utils.evolink import evolink_client


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
