"""
角色图片生成 Celery 任务。
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from celery import Task

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


class CharacterImageTask(Task):
    """角色图片任务基类，避免跨事件循环复用异步数据库资源。"""

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
    base=CharacterImageTask,
    name="app.tasks.character.generate_character_view_task",
    max_retries=3,
    default_retry_delay=30,
    queue="image",
)
def generate_character_view_task(self, task_db_id: int) -> dict:
    return asyncio.run(_run_view_generation(self, task_db_id))


@celery_app.task(
    bind=True,
    base=CharacterImageTask,
    name="app.tasks.character.generate_character_state_task",
    max_retries=3,
    default_retry_delay=30,
    queue="image",
)
def generate_character_state_task(self, task_db_id: int) -> dict:
    return asyncio.run(_run_state_generation(self, task_db_id))


async def _run_view_generation(task: CharacterImageTask, task_db_id: int) -> dict:
    import httpx

    from app.core.config import settings
    from app.repositories.character import CharacterRepository
    from app.repositories.task import TaskRepository
    from app.utils.image_gen import image_gen_client
    from app.utils.oss import oss_client

    engine, session_factory = task.get_session_factory()
    try:
        async with session_factory() as session:
            task_repo = TaskRepository(session)
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
                character_id = params.get("character_id")
                view_type = params.get("view_type", "front")
                prompt_override = params.get("prompt_override")
                base_prompt = params.get("base_prompt", "")
                reference_images = params.get("reference_images", [])

                char_repo = CharacterRepository(session)
                character = await char_repo.get(character_id)
                if not character:
                    raise RuntimeError(f"Character {character_id} does not exist")

                view_prompts = {
                    "front": "front view, facing camera, full body character design",
                    "side": "side view, profile, full body character design",
                    "back": "back view, from behind, full body character design",
                }
                view_prompt = view_prompts.get(view_type, view_prompts["front"])
                full_prompt = f"{base_prompt}, {view_prompt}" if base_prompt else view_prompt
                if prompt_override:
                    full_prompt = f"{prompt_override}, {view_prompt}"

                logger.info(
                    "Generate character view image: character_id=%s view_type=%s prompt=%s...",
                    character_id,
                    view_type,
                    full_prompt[:50],
                )

                if reference_images:
                    ref_image_data = []
                    async with httpx.AsyncClient(timeout=30, trust_env=settings.HTTP_TRUST_ENV) as http_client:
                        for url in reference_images[:3]:
                            try:
                                response = await http_client.get(url)
                                if response.status_code == 200:
                                    ref_image_data.append(response.content)
                            except Exception as exc:
                                logger.warning("Failed to download reference image %s: %s", url, exc)

                    if ref_image_data:
                        result = await image_gen_client.generate_with_reference(
                            prompt=full_prompt,
                            reference_images=ref_image_data,
                            aspect_ratio="2:3",
                            image_size="1K",
                        )
                    else:
                        result = await image_gen_client.generate(
                            prompt=full_prompt,
                            aspect_ratio="2:3",
                            image_size="1K",
                        )
                else:
                    result = await image_gen_client.generate(
                        prompt=full_prompt,
                        aspect_ratio="2:3",
                        image_size="1K",
                    )

                if not result.success or not result.image_data:
                    raise RuntimeError(result.error_message or "图像生成失败")

                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                filename = f"char_{character_id}_view_{view_type}_{timestamp}.png"
                image_url = oss_client.upload_bytes(
                    result.image_data,
                    filename,
                    directory="characters/views",
                )

                # 更新角色图片
                await char_repo.update(character, {"pic_url": image_url})

                await task_repo.update(
                    gen_task,
                    {
                        "status": "success",
                        "progress": 100,
                        "completed_at": datetime.now(timezone.utc),
                    },
                )
                await session.commit()

                return {"status": "success", "image_url": image_url, "view_type": view_type}

            except Exception as exc:
                logger.exception("Character view generation failed task_id=%d error=%s", task_db_id, exc)
                await task_repo.update(
                    gen_task,
                    {
                        "status": "failed",
                        "error_message": str(exc),
                        "completed_at": datetime.now(timezone.utc),
                    },
                )
                await session.commit()

                if task.request.retries < task.max_retries:
                    raise task.retry(exc=exc)

                return {"status": "failed", "error": str(exc)}
    finally:
        await engine.dispose()


async def _run_state_generation(task: CharacterImageTask, task_db_id: int) -> dict:
    import httpx

    from app.core.config import settings
    from app.repositories.character import CharacterRepository
    from app.repositories.task import TaskRepository
    from app.utils.image_gen import image_gen_client
    from app.utils.oss import oss_client

    engine, session_factory = task.get_session_factory()
    try:
        async with session_factory() as session:
            task_repo = TaskRepository(session)
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
                character_id = params.get("character_id")
                state_type = params.get("state_type", "neutral")
                state_description = params.get("state_description", "")
                prompt_override = params.get("prompt_override")
                base_prompt = params.get("base_prompt", "")
                reference_images = params.get("reference_images", [])
                view_front_url = params.get("view_front_url")

                char_repo = CharacterRepository(session)
                character = await char_repo.get(character_id)
                if not character:
                    raise RuntimeError(f"Character {character_id} does not exist")

                state_prompts = {
                    "anger": "angry expression, fierce eyes, aggressive stance, dynamic pose",
                    "happy": "happy smiling expression, joyful, bright eyes, relaxed pose",
                    "sad": "sad expression, downcast eyes, melancholic, depressed pose",
                    "surprise": "surprised expression, wide eyes, shocked face",
                    "fear": "fearful expression, scared eyes, defensive pose",
                    "determination": "determined expression, focused eyes, confident stance",
                    "skill_release": "casting magic spell, powerful pose, glowing effects, action scene",
                    "battle_stance": "battle ready pose, combat stance, holding weapon, dynamic action",
                    "injured": "injured pose, bleeding, pained expression, dramatic lighting",
                    "exhausted": "exhausted pose, tired expression, sweating, out of breath",
                    "meditation": "meditation pose, peaceful expression, closed eyes, serene atmosphere",
                    "triumph": "victorious pose, triumphant expression, arms raised, celebration",
                }

                state_prompt = state_prompts.get(state_type, "neutral expression")
                if state_description:
                    state_prompt = f"{state_prompt}, {state_description}"

                full_prompt = f"{base_prompt}, {state_prompt}" if base_prompt else state_prompt
                if prompt_override:
                    full_prompt = f"{prompt_override}, {state_prompt}"

                ref_image_data = []
                async with httpx.AsyncClient(timeout=30, trust_env=settings.HTTP_TRUST_ENV) as http_client:
                    if view_front_url:
                        try:
                            response = await http_client.get(view_front_url)
                            if response.status_code == 200:
                                ref_image_data.append(response.content)
                        except Exception as exc:
                            logger.warning("Failed to download front view image: %s", exc)

                    for url in reference_images[:2]:
                        if url and url != view_front_url:
                            try:
                                response = await http_client.get(url)
                                if response.status_code == 200:
                                    ref_image_data.append(response.content)
                            except Exception as exc:
                                logger.warning("Failed to download reference image %s: %s", url, exc)

                if ref_image_data:
                    result = await image_gen_client.generate_with_reference(
                        prompt=full_prompt,
                        reference_images=ref_image_data,
                        aspect_ratio="2:3",
                        image_size="1K",
                    )
                else:
                    result = await image_gen_client.generate(
                        prompt=full_prompt,
                        aspect_ratio="2:3",
                        image_size="1K",
                    )

                if not result.success or not result.image_data:
                    raise RuntimeError(result.error_message or "图像生成失败")

                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                filename = f"char_{character_id}_state_{state_type}_{timestamp}.png"
                image_url = oss_client.upload_bytes(
                    result.image_data,
                    filename,
                    directory="characters/states",
                )

                # 更新角色图片
                await char_repo.update(character, {"pic_url": image_url})

                await task_repo.update(
                    gen_task,
                    {
                        "status": "success",
                        "progress": 100,
                        "completed_at": datetime.now(timezone.utc),
                    },
                )
                await session.commit()

                return {"status": "success", "image_url": image_url, "state_type": state_type}

            except Exception as exc:
                logger.exception("Character state generation failed task_id=%d error=%s", task_db_id, exc)
                await task_repo.update(
                    gen_task,
                    {
                        "status": "failed",
                        "error_message": str(exc),
                        "completed_at": datetime.now(timezone.utc),
                    },
                )
                await session.commit()

                if task.request.retries < task.max_retries:
                    raise task.retry(exc=exc)

                return {"status": "failed", "error": str(exc)}
    finally:
        await engine.dispose()
