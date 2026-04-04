"""
视频生成 Celery 任务。

流程：
  1. 从数据库加载 GenerationTask + Shot 信息
  2. 构建完整视频提示词（从 shot 各字段拼接）
  3. 拼装 Evolink API 请求（文生视频 or 图生视频）
  4. 调用 Evolink API 提交任务，轮询直到完成
  5. 下载视频并上传到 OSS，将永久 URL 写入 Shot.video_url
  6. 更新 GenerationTask 状态为 success / failed
"""

import asyncio
import logging
from datetime import datetime, timezone

from celery import Task

from app.tasks.celery_app import celery_app
from app.prompts import build_video_prompt

logger = logging.getLogger(__name__)


class VideoGenerationTask(Task):
    """自定义 Task 基类，提供数据库会话的懒加载。"""

    abstract = True

    def get_session_factory(self):
        """每次任务执行时重新创建 session factory，避免事件循环冲突。"""
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.core.config import settings
        import json

        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_size=5,
            max_overflow=10,
            json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
        )
        return async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )


@celery_app.task(
    bind=True,
    base=VideoGenerationTask,
    name="app.tasks.video.generate_video_task",
    max_retries=3,
    default_retry_delay=60,   # 失败后 60 秒重试
    queue="video",
)
def generate_video_task(self, task_db_id: int) -> dict:
    """视频生成任务入口（同步包装，内部运行异步逻辑）。

    Args:
        task_db_id: GenerationTask 的数据库 ID。

    Returns:
        {"status": "success", "video_url": str}
    """
    # 每次执行都创建新的事件循环，避免重试时 "Event loop is closed" 错误
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_video_generation(self, task_db_id))
    finally:
        loop.close()


async def _run_video_generation(task: VideoGenerationTask, task_db_id: int) -> dict:
    """视频生成异步核心逻辑。"""
    from app.models.task import GenerationTask
    from app.repositories.asset import AssetRepository
    from app.repositories.shot import ShotRepository
    from app.repositories.task import TaskRepository
    from app.utils.evolink import evolink_client

    async with task.session_factory() as session:
        task_repo = TaskRepository(session)
        gen_task = await task_repo.get(task_db_id)
        if not gen_task:
            logger.error("GenerationTask %d 不存在", task_db_id)
            return {"status": "failed", "error": "任务记录不存在"}

        # 标记任务开始
        await task_repo.update(gen_task, {
            "status": "running",
            "started_at": datetime.now(timezone.utc),
        })
        await session.commit()

        try:
            shot_repo = ShotRepository(session)
            shot = await shot_repo.get(gen_task.shot_id)
            if not shot:
                raise ValueError(f"Shot {gen_task.shot_id} 不存在")

            # 更新镜头状态为生成中
            await shot_repo.update(shot, {"status": "generating"})
            await session.commit()

            params = gen_task.input_params or {}
            quality = params.get("quality", "1080p")
            sound = params.get("sound", "on")

            # 根据是否有首帧图决定调用文生视频还是图生视频
            if params.get("use_image_start") and shot.assets:
                # 找到当前镜头的图片素材作为首帧
                asset_repo = AssetRepository(session)
                image_assets = await asset_repo.get_by_shot(shot.id, current_only=True)
                image_asset = next((a for a in image_assets if a.asset_type == "image"), None)
                image_start = image_asset.file_url if image_asset else None
            else:
                image_start = None

            # 构建完整的视频提示词（从 shot 各字段拼接，含负面提示词）
            prompt = build_video_prompt(shot)

            logger.info("开始生成视频：shot=%s quality=%s sound=%s", shot.shot_code, quality, sound)
            logger.info("=" * 60)
            logger.info("Kling 视频提示词:\n%s", prompt)
            logger.info("=" * 60)

            if image_start:
                video_task = await evolink_client.image_to_video(
                    prompt=prompt,
                    image_start=image_start,
                    duration=max(3, min(15, int(shot.duration_sec))),
                    quality=quality,
                    sound=sound,
                )
            else:
                video_task = await evolink_client.text_to_video(
                    prompt=prompt,
                    duration=max(3, min(15, int(shot.duration_sec))),
                    quality=quality,
                    sound=sound,
                )

            logger.info("Evolink 任务已提交：%s，开始轮询…", video_task.id)

            # 轮询直到完成（最多 10 分钟），自动下载并上传到 OSS
            result = await evolink_client.wait_for_completion(
                video_task.id,
                poll_interval=8.0,
                timeout=600.0,
                upload_to_oss=True,
                oss_directory=f"videos/{shot.shot_code}",
                oss_filename=f"{shot.shot_code}.mp4",
            )

            if not result.video_url:
                raise RuntimeError("Evolink 返回结果中无视频URL")

            logger.info("视频生成完成：%s  url=%s", shot.shot_code, result.video_url)

            # 更新镜头状态和视频 URL（result.video_url 已是 OSS 永久链接）
            await shot_repo.update(shot, {
                "status": "review",
                "video_url": result.video_url,
            })

            # 更新任务状态
            await task_repo.update(gen_task, {
                "status": "success",
                "progress": 100,
                "completed_at": datetime.now(timezone.utc),
            })
            await session.commit()

            return {"status": "success", "video_url": result.video_url}

        except Exception as exc:
            logger.exception("视频生成失败：task_id=%d error=%s", task_db_id, exc)
            await task_repo.update(gen_task, {
                "status": "failed",
                "error_message": str(exc),
                "completed_at": datetime.now(timezone.utc),
            })
            # 更新镜头状态为 draft，便于重试
            if gen_task.shot_id:
                shot = await ShotRepository(session).get(gen_task.shot_id)
                if shot:
                    await ShotRepository(session).update(shot, {"status": "draft"})
            await session.commit()

            # 可重试的异常（网络问题、限流）自动重试
            retryable = (RuntimeError, TimeoutError, ConnectionError)
            if isinstance(exc, retryable) and task.request.retries < task.max_retries:
                raise task.retry(exc=exc)

            return {"status": "failed", "error": str(exc)}
