"""
图像生成 Celery 任务。
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from celery import Task

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


class ImageGenerationTask(Task):
    """自定义 Task 基类，避免跨事件循环复用异步数据库资源。"""

    abstract = True

    def get_session_factory(self):
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from app.core.config import settings

        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_size=5,
            max_overflow=10,
            json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
        )
        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        return engine, session_factory


@celery_app.task(
    bind=True,
    base=ImageGenerationTask,
    name="app.tasks.image.generate_image_task",
    max_retries=3,
    default_retry_delay=30,
    queue="image",
)
def generate_image_task(self, task_db_id: int) -> dict:
    return asyncio.run(_run_image_generation(self, task_db_id))


async def _run_image_generation(task: ImageGenerationTask, task_db_id: int) -> dict:
    import httpx

    from app.repositories.asset import AssetRepository
    from app.repositories.character import CharacterRepository, CharacterVersionRepository
    from app.repositories.location import LocationRepository, LocationVersionRepository
    from app.repositories.shot import ShotRepository
    from app.repositories.shot_group import ShotGroupRepository
    from app.repositories.task import TaskRepository
    from app.utils.image_gen import image_gen_client
    from app.utils.oss import oss_client

    engine, session_factory = task.get_session_factory()
    try:
        async with session_factory() as session:
            task_repo = TaskRepository(session)
            asset_repo = AssetRepository(session)
            shot_repo = ShotRepository(session)
            location_repo = LocationRepository(session)
            location_version_repo = LocationVersionRepository(session)
            character_repo = CharacterRepository(session)
            character_version_repo = CharacterVersionRepository(session)

            gen_task = await task_repo.get(task_db_id)
            if not gen_task:
                logger.error("GenerationTask %d does not exist", task_db_id)
                return {"status": "failed", "error": "任务记录不存在"}

            await task_repo.update(
                gen_task,
                {
                    "status": "running",
                    "started_at": datetime.now(timezone.utc),
                },
            )
            await session.commit()

            try:
                params = gen_task.input_params or {}
                project_id = params.get("project_id")
                shot_id = params.get("shot_id")
                location_id = params.get("location_id")
                location_version_id = params.get("location_version_id")
                character_id = params.get("character_id")
                character_version_id = params.get("character_version_id")
                prompt = params.get("prompt", "")
                negative_prompt = params.get("negative_prompt")
                aspect_ratio = params.get("aspect_ratio", "16:9")
                resolution = params.get("resolution", "1K")
                style_preset = params.get("style_preset")
                character_image_kind = params.get("character_image_kind")
                reference_image_urls = params.get("reference_image_urls") or []
                save_to_library = params.get("save_to_shot", True)

                full_prompt = prompt
                if style_preset:
                    full_prompt = f"{prompt}, {style_preset} style"

                shot = None
                if shot_id:
                    shot = await shot_repo.get(shot_id)
                    if shot:
                        await shot_repo.update(shot, {"status": "generating"})
                        await session.commit()
                        if not project_id and getattr(shot, "storyboard", None) and shot.storyboard:
                            project_id = shot.storyboard.scene.project_id

                location = None
                if location_id:
                    location = await location_repo.get(location_id)
                location_version = None
                if location_id and location_version_id:
                    location_version = await location_version_repo.get_by_id_and_location(
                        location_version_id,
                        location_id,
                    )

                character = None
                if character_id:
                    character = await character_repo.get_by_id_and_project(character_id, project_id or 0)

                character_version = None
                if character_id and character_version_id:
                    character_version = await character_version_repo.get_by_id_and_character(
                        character_version_id,
                        character_id,
                    )

                logger.info(
                    "Start image generation task=%s project=%s shot=%s location=%s location_version=%s character=%s character_version=%s image_kind=%s refs=%s",
                    task_db_id,
                    project_id,
                    shot_id,
                    location_id,
                    location_version_id,
                    character_id,
                    character_version_id,
                    character_image_kind,
                    len(reference_image_urls),
                )

                if reference_image_urls:
                    reference_images: list[bytes] = []
                    async with httpx.AsyncClient(timeout=30) as http_client:
                        for url in reference_image_urls[:5]:
                            try:
                                response = await http_client.get(url)
                                if response.status_code == 200:
                                    reference_images.append(response.content)
                                else:
                                    logger.warning(
                                        "Failed to download reference image %s: %s",
                                        url,
                                        response.status_code,
                                    )
                            except Exception as exc:
                                logger.warning("Failed to download reference image %s: %s", url, exc)

                    if not reference_images:
                        raise RuntimeError("所有参考图下载失败")

                    result = await image_gen_client.generate_with_reference(
                        prompt=full_prompt,
                        reference_images=reference_images,
                        negative_prompt=negative_prompt,
                        aspect_ratio=aspect_ratio,
                        image_size=resolution,
                    )
                else:
                    result = await image_gen_client.generate(
                        prompt=full_prompt,
                        negative_prompt=negative_prompt,
                        aspect_ratio=aspect_ratio,
                        image_size=resolution,
                    )

                if not result.success or not result.image_data:
                    raise RuntimeError(result.error_message or "图像生成失败")

                file_format = "png" if "png" in (result.mime_type or "") else "jpg"
                asset_code = f"img_{task_db_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                if shot:
                    asset_code = f"{shot.shot_code}_image"
                elif character:
                    asset_code = f"{character.char_code.lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    if character_version:
                        asset_code = (
                            f"{character.char_code.lower()}_{character_version.version_code}_"
                            f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        )
                elif location:
                    asset_code = f"{location.loc_code.lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    if location_version:
                        asset_code = (
                            f"{location.loc_code.lower()}_{location_version.version_code}_"
                            f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        )

                filename = f"{asset_code}.{file_format}"
                directory = "generated/images"
                if character:
                    directory = f"generated/characters/{character.id}"
                elif location:
                    directory = f"generated/locations/{location.id}"

                image_url = oss_client.upload_bytes(result.image_data, filename, directory=directory)
                logger.info("Generated image uploaded to %s", image_url)

                asset_id = None
                shot_group_id = params.get("shot_group_id")
                if save_to_library and project_id:
                    tags = ["image", "generated", "global"]
                    if shot:
                        tags = [shot.shot_code, "image", "generated"]
                    elif character:
                        tags = [character.char_code, "image", "generated", "character"]
                        if character_version:
                            tags.append(character_version.version_code)
                        if character_image_kind:
                            tags.append(character_image_kind)
                    elif location:
                        tags = [location.loc_code, "image", "generated", "location"]
                        if location_version:
                            tags.append(location_version.version_code)

                    if shot:
                        await asset_repo.deprecate_shot_assets(shot.id, "image")
                        existing_assets = await asset_repo.get_by_shot(shot.id, current_only=False)
                        image_versions = [asset.version for asset in existing_assets if asset.asset_type == "image"]
                        next_version = (max(image_versions) + 1) if image_versions else 1
                        new_asset = await asset_repo.create(
                            project_id=project_id,
                            shot_id=shot.id,
                            location_id=location.id if location else None,
                            location_version_id=location_version.id if location_version else None,
                            character_id=character.id if character else None,
                            asset_code=f"{shot.shot_code}_image_v{next_version}",
                            asset_type="image",
                            file_url=image_url,
                            file_format=file_format,
                            file_size_bytes=len(result.image_data),
                            source="generated",
                            generator="gemini",
                            version=next_version,
                            is_current=True,
                            tags=tags,
                        )
                        asset_id = new_asset.id
                        await shot_repo.update(shot, {"status": "review"})
                    else:
                        import uuid

                        new_asset = await asset_repo.create(
                            project_id=project_id,
                            shot_id=None,
                            location_id=location.id if location else None,
                            location_version_id=location_version.id if location_version else None,
                            character_id=character.id if character else None,
                            asset_code=f"img_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                            asset_type="image",
                            file_url=image_url,
                            file_format=file_format,
                            file_size_bytes=len(result.image_data),
                            source="generated",
                            generator="gemini",
                            version=1,
                            is_current=True,
                            tags=tags,
                        )
                        asset_id = new_asset.id

                    # Update character version with generated image
                    if character_version:
                        if character_image_kind == "three_view":
                            await character_version_repo.update(
                                character_version,
                                {"three_view_url": image_url},
                            )
                        else:
                            reference_urls = list(character_version.reference_image_urls or [])
                            if image_url not in reference_urls:
                                reference_urls.append(image_url)
                                await character_version_repo.update(
                                    character_version,
                                    {"reference_image_urls": reference_urls},
                                )
                    elif character:
                        # If no version specified, update the character's default reference images
                        pass  # Character doesn't have direct reference_image_urls, only versions do

                    if location_version:
                        reference_urls = list(location_version.reference_image_urls or [])
                        if image_url not in reference_urls:
                            reference_urls.append(image_url)
                            await location_version_repo.update(
                                location_version,
                                {"reference_image_urls": reference_urls},
                            )
                    elif location:
                        reference_urls = list(location.reference_image_urls or [])
                        if image_url not in reference_urls:
                            reference_urls.append(image_url)
                            await location_repo.update(location, {"reference_image_urls": reference_urls})

                # 将生成的图片写入 ShotGroup.image_start_url（首帧参考图）
                if shot_group_id:
                    shot_group_repo = ShotGroupRepository(session)
                    shot_group = await shot_group_repo.get(shot_group_id)
                    if shot_group:
                        await shot_group_repo.update(shot_group, {"image_start_url": image_url})

                await task_repo.update(
                    gen_task,
                    {
                        "status": "success",
                        "progress": 100,
                        "result_asset_id": asset_id,
                        "completed_at": datetime.now(timezone.utc),
                    },
                )
                await session.commit()

                return {"status": "success", "asset_id": asset_id, "image_url": image_url}

            except Exception as exc:
                logger.exception("Image generation failed task_id=%d error=%s", task_db_id, exc)
                await task_repo.update(
                    gen_task,
                    {
                        "status": "failed",
                        "error_message": str(exc),
                        "completed_at": datetime.now(timezone.utc),
                    },
                )

                shot_id = (gen_task.input_params or {}).get("shot_id")
                if shot_id:
                    shot = await shot_repo.get(shot_id)
                    if shot:
                        await shot_repo.update(shot, {"status": "draft"})

                await session.commit()

                retryable = (RuntimeError, TimeoutError, ConnectionError)
                if isinstance(exc, retryable) and task.request.retries < task.max_retries:
                    raise task.retry(exc=exc)

                return {"status": "failed", "error": str(exc)}
    finally:
        await engine.dispose()
