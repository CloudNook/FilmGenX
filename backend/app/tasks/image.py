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
    # 每次执行都创建新的事件循环，避免重试时 "Event loop is closed" 错误
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_image_generation(self, task_db_id))
    finally:
        loop.close()


async def _run_image_generation(task: ImageGenerationTask, task_db_id: int) -> dict:
    """图像生成异步核心逻辑。"""
    import httpx
    import uuid
    from app.repositories.asset import AssetRepository
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
            project_id = params.get("project_id")
            prompt = params.get("prompt", "")
            negative_prompt = params.get("negative_prompt")
            aspect_ratio = params.get("aspect_ratio", "16:9")
            resolution = params.get("resolution", "1K")
            style_preset = params.get("style_preset")
            reference_image_urls = params.get("reference_image_urls", [])
            save_to_library = params.get("save_to_library", True)

            # 构建完整提示词
            full_prompt = prompt
            if style_preset:
                full_prompt = f"{prompt}, {style_preset} style"

            logger.info(
                "开始生成图像：project_id=%s prompt=%s... resolution=%s aspect_ratio=%s ref_count=%d",
                project_id, prompt[:50], resolution, aspect_ratio, len(reference_image_urls or [])
            )

            # 根据是否有参考图选择生成方法
            if reference_image_urls and len(reference_image_urls) > 0:
                # 图生图模式：下载参考图
                reference_images = []
                async with httpx.AsyncClient(timeout=30) as http_client:
                    for url in reference_image_urls[:5]:  # 最多 5 张
                        try:
                            resp = await http_client.get(url)
                            if resp.status_code == 200:
                                reference_images.append(resp.content)
                            else:
                                logger.warning(f"下载参考图失败: {url}, status={resp.status_code}")
                        except Exception as e:
                            logger.warning(f"下载参考图异常: {url}, error={e}")

                if not reference_images:
                    raise RuntimeError("所有参考图下载失败")

                logger.info(f"成功下载 {len(reference_images)} 张参考图，开始图生图...")
                result = await image_gen_client.generate_with_reference(
                    prompt=full_prompt,
                    reference_images=reference_images,
                    negative_prompt=negative_prompt,
                    aspect_ratio=aspect_ratio,
                    image_size=resolution,
                )
            else:
                # 文生图模式
                result = await image_gen_client.generate(
                    prompt=full_prompt,
                    negative_prompt=negative_prompt,
                    aspect_ratio=aspect_ratio,
                    image_size=resolution,
                )

            if not result.success:
                raise RuntimeError(result.error_message or "图像生成失败")

            logger.info("图像生成成功：size=%d bytes", len(result.image_data or b""))

            # 上传图片到 OSS
            file_format = "png" if "png" in (result.mime_type or "") else "jpg"
            asset_code = f"img_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

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
            if save_to_library and project_id:
                asset_repo = AssetRepository(session)

                new_asset = await asset_repo.create(
                    project_id=project_id,
                    shot_id=None,
                    asset_code=asset_code,
                    asset_type="image",
                    file_url=image_url,
                    file_format=file_format,
                    file_size_bytes=len(result.image_data or b""),
                    source="generated",
                    generator="gemini",
                    version=1,
                    is_current=True,
                    tags=["image", "generated"],
                )
                asset_id = new_asset.id
                logger.info(f"素材已保存到项目 {project_id} 素材库，asset_id={asset_id}")

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
            await session.commit()

            # 可重试的异常
            retryable = (RuntimeError, TimeoutError, ConnectionError)
            if isinstance(exc, retryable) and task.request.retries < task.max_retries:
                raise task.retry(exc=exc)

            return {"status": "failed", "error": str(exc)}
