"""
Celery 应用实例配置。

启动 Worker（开发环境）：
    # Linux/macOS
    uv run celery -A app.tasks.celery_app worker --loglevel=info -Q default,video,image

    # Windows（使用 solo 模式避免进程池兼容问题）
    uv run celery -A app.tasks.celery_app worker --loglevel=info -Q default,video,image --pool=solo
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "filmgenx",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    # 任务序列化格式
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 任务路由：不同类型任务分发到对应队列，便于独立扩展 Worker
    task_routes={
        "app.tasks.video.*": {"queue": "video"},
        "app.tasks.image.*": {"queue": "image"},
        "app.tasks.storyboard.*": {"queue": "default"},
    },
    # 任务结果保留 24 小时
    result_expires=86400,
    # 单任务超时：30 分钟（视频生成耗时较长）
    task_time_limit=1800,
    task_soft_time_limit=1500,
    # Worker 并发数（视频生成 IO 密集，可适当调大）
    worker_concurrency=4,
    # 任务预取数量（视频任务重，设为 1 避免积压）
    worker_prefetch_multiplier=1,
)

# 自动发现任务模块
celery_app.autodiscover_tasks(["app.tasks.video", "app.tasks.image", "app.tasks.storyboard"])
