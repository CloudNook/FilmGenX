"""
视频生成 Celery 任务。

流程：
  1. 从数据库加载 GenerationTask + Shot 信息
  2. 拼装 Evolink API 请求（文生视频 or 图生视频）
  3. 调用 Evolink API 提交任务，轮询直到完成
  4. 将视频 URL 写入 Asset 表，更新 Shot 状态
  5. 更新 GenerationTask 状态为 success / failed
"""

import asyncio
import logging
from datetime import datetime, timezone

from celery import Task

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


class VideoGenerationTask(Task):
    """自定义 Task 基类，提供数据库会话的懒加载。"""

    abstract = True
    _session_factory = None

    @property
    def session_factory(self):
        """懒加载 AsyncSessionFactory，避免 Worker 启动时触发数据库连接。"""
        if self._session_factory is None:
            from app.db.session import AsyncSessionFactory
            self._session_factory = AsyncSessionFactory
        return self._session_factory


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
        {"status": "success", "asset_id": int, "video_url": str}
    """
    return asyncio.get_event_loop().run_until_complete(
        _run_video_generation(self, task_db_id)
    )


async def _run_video_generation(task: VideoGenerationTask, task_db_id: int) -> dict:
    """视频生成异步核心逻辑。"""
    from app.models.asset import Asset
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

            # 构建视频提示词：优先使用 shot.image_prompt，降级到基础描述
            prompt = shot.image_prompt or f"shot {shot.shot_code}"

            logger.info("开始生成视频：shot=%s quality=%s sound=%s", shot.shot_code, quality, sound)

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

            # 轮询直到完成（最多 10 分钟）
            result = await evolink_client.wait_for_completion(
                video_task.id,
                poll_interval=8.0,
                timeout=600.0,
            )

            if not result.video_url:
                raise RuntimeError("Evolink 返回结果中无视频URL")

            logger.info("视频生成完成：%s  url=%s", shot.shot_code, result.video_url)

            # 写入 Asset 记录（先将旧的 video 素材标记为非当前版本）
            asset_repo = AssetRepository(session)
            await asset_repo.deprecate_shot_assets(shot.id, "video")

            # 查询当前最大版本号
            existing = await asset_repo.get_by_shot(shot.id, current_only=False)
            video_versions = [a.version for a in existing if a.asset_type == "video"]
            next_version = (max(video_versions) + 1) if video_versions else 1

            new_asset = await asset_repo.create(
                project_id=shot.storyboard.scene.project_id if hasattr(shot, "storyboard") else 0,
                shot_id=shot.id,
                asset_code=f"{shot.shot_code}_video_v{next_version}",
                asset_type="video",
                file_url=result.video_url,
                file_format="mp4",
                duration_sec=result.video_duration,
                source="generated",
                generator="kling",
                version=next_version,
                is_current=True,
                tags=[shot.shot_code, "video", quality],
            )

            # 更新镜头与任务状态
            await shot_repo.update(shot, {"status": "review"})
            await task_repo.update(gen_task, {
                "status": "success",
                "progress": 100,
                "result_asset_id": new_asset.id,
                "completed_at": datetime.now(timezone.utc),
            })
            await session.commit()

            return {"status": "success", "asset_id": new_asset.id, "video_url": result.video_url}

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
