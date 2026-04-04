"""
图像生成 Celery 任务。

流程：
  1. 从数据库加载 GenerationTask + Shot 信息
  2. 拼装 Google Imagen API 请求
  3. 调用 Imagen API 生成图像
  4. 上传图片到 OSS，写入 Asset 表
  5. 更新 GenerationTask 状态为 success / failed
"""

import asyncio
import logging
from datetime import datetime, timezone

from celery import Task

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


class ImageGenerationTask(Task):
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
    base=ImageGenerationTask,
    name="app.tasks.image.generate_image_task",
    max_retries=3,
    default_retry_delay=30,  # 失败后 30 秒重试
    queue="image",
)
def generate_image_task(self, task_db_id: int) -> dict:
    """图像生成任务入口（同步包装，内部运行异步逻辑）。

    Args:
        task_db_id: GenerationTask 的数据库 ID。

    Returns:
        {"status": "success", "asset_id": int, "image_url": str}
    """
    return asyncio.get_event_loop().run_until_complete(
        _run_image_generation(self, task_db_id)
    )


async def _run_image_generation(task: ImageGenerationTask, task_db_id: int) -> dict:
    """图像生成异步核心逻辑。"""
    from app.repositories.asset import AssetRepository
    from app.repositories.shot import ShotRepository
    from app.repositories.task import TaskRepository
    from app.utils.image_gen import image_gen_client
    from app.utils.oss import oss_client

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
            params = gen_task.input_params or {}
            shot_id = params.get("shot_id")
            prompt = params.get("prompt", "")
            negative_prompt = params.get("negative_prompt")
            aspect_ratio = params.get("aspect_ratio", "16:9")
            style_preset = params.get("style_preset")
            save_to_shot = params.get("save_to_shot", True)

            # 构建完整提示词
            full_prompt = prompt
            if style_preset:
                full_prompt = f"{prompt}, {style_preset} style"

            logger.info(
                "开始生成图像：shot_id=%s prompt=%s...",
                shot_id, prompt[:50]
            )

            # 获取关联的 Shot 信息（如果有）
            shot = None
            project_id = None
            if shot_id:
                shot_repo = ShotRepository(session)
                shot = await shot_repo.get(shot_id)
                if shot:
                    # 尝试从 shot 获取项目 ID
                    if hasattr(shot, 'storyboard') and shot.storyboard:
                        project_id = shot.storyboard.scene.project_id
                    # 更新镜头状态
                    await shot_repo.update(shot, {"status": "generating"})
                    await session.commit()

            # 调用 Imagen 生成图像
            result = await image_gen_client.generate(
                prompt=full_prompt,
                negative_prompt=negative_prompt,
                aspect_ratio=aspect_ratio,
            )

            if not result.success:
                raise RuntimeError(result.error_message or "图像生成失败")

            logger.info("Imagen 生成成功：size=%d bytes", len(result.image_data or b""))

            # 上传图片到 OSS（同步调用，因为 oss_client 是同步的）
            file_format = "png" if "png" in (result.mime_type or "") else "jpg"
            asset_code = f"img_{task_db_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            if shot:
                asset_code = f"{shot.shot_code}_image"

            # 生成 OSS 路径和文件名
            filename = f"{asset_code}.{file_format}"
            image_url = oss_client.upload_bytes(
                result.image_data,
                filename,
                directory="generated/images",
            )

            logger.info("图片已上传到 OSS：%s", image_url)

            # 保存到素材库
            asset_id = None
            if save_to_shot and shot:
                asset_repo = AssetRepository(session)
                await asset_repo.deprecate_shot_assets(shot.id, "image")

                # 计算版本号
                existing = await asset_repo.get_by_shot(shot.id, current_only=False)
                image_versions = [a.version for a in existing if a.asset_type == "image"]
                next_version = (max(image_versions) + 1) if image_versions else 1

                new_asset = await asset_repo.create(
                    project_id=project_id or 0,
                    shot_id=shot.id,
                    asset_code=f"{shot.shot_code}_image_v{next_version}",
                    asset_type="image",
                    file_url=image_url,
                    file_format=file_format,
                    file_size_bytes=len(result.image_data or b""),
                    source="generated",
                    generator="imagen",
                    version=next_version,
                    is_current=True,
                    tags=[shot.shot_code, "image", "generated"],
                )
                asset_id = new_asset.id

                # 更新镜头状态
                await ShotRepository(session).update(shot, {"status": "review"})

            # 更新任务状态
            await task_repo.update(gen_task, {
                "status": "success",
                "progress": 100,
                "result_asset_id": asset_id,
                "completed_at": datetime.now(timezone.utc),
            })
            await session.commit()

            return {
                "status": "success",
                "asset_id": asset_id,
                "image_url": image_url,
            }

        except Exception as exc:
            logger.exception("图像生成失败：task_id=%d error=%s", task_db_id, exc)
            await task_repo.update(gen_task, {
                "status": "failed",
                "error_message": str(exc),
                "completed_at": datetime.now(timezone.utc),
            })

            # 恢复镜头状态
            shot_id = (gen_task.input_params or {}).get("shot_id")
            if shot_id:
                shot = await ShotRepository(session).get(shot_id)
                if shot:
                    await ShotRepository(session).update(shot, {"status": "draft"})

            await session.commit()

            # 可重试的异常
            retryable = (RuntimeError, TimeoutError, ConnectionError)
            if isinstance(exc, retryable) and task.request.retries < task.max_retries:
                raise task.retry(exc=exc)

            return {"status": "failed", "error": str(exc)}
