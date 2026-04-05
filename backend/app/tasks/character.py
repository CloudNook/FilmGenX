"""
角色图片生成 Celery 任务。

功能：
- 生成角色三视图（正面/侧面/背面）
- 生成角色状态图（愤怒/开心/释放技能等）
"""

import asyncio
import logging
from datetime import datetime, timezone

from celery import Task

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


class CharacterImageTask(Task):
    """角色图片生成任务基类。"""

    abstract = True
    _session_factory = None

    @property
    def session_factory(self):
        if self._session_factory is None:
            from app.db.session import AsyncSessionFactory
            self._session_factory = AsyncSessionFactory
        return self._session_factory


@celery_app.task(
    bind=True,
    base=CharacterImageTask,
    name="app.tasks.character.generate_character_view_task",
    max_retries=3,
    default_retry_delay=30,
    queue="image",
)
def generate_character_view_task(self, task_db_id: int) -> dict:
    """生成角色三视图任务入口。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_view_generation(self, task_db_id))
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    base=CharacterImageTask,
    name="app.tasks.character.generate_character_state_task",
    max_retries=3,
    default_retry_delay=30,
    queue="image",
)
def generate_character_state_task(self, task_db_id: int) -> dict:
    """生成角色状态图任务入口。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_state_generation(self, task_db_id))
    finally:
        loop.close()


async def _run_view_generation(task: CharacterImageTask, task_db_id: int) -> dict:
    """三视图生成核心逻辑。"""
    from app.core.config import settings
    from app.repositories.character import CharacterVersionRepository
    from app.repositories.task import TaskRepository
    from app.utils.image_gen import image_gen_client
    from app.utils.oss import oss_client

    async with task.session_factory() as session:
        task_repo = TaskRepository(session)
        gen_task = await task_repo.get(task_db_id)
        if not gen_task:
            logger.error("GenerationTask %d 不存在", task_db_id)
            return {"status": "failed", "error": "任务记录不存在"}

        await task_repo.update(gen_task, {
            "status": "running",
            "started_at": datetime.now(timezone.utc),
        })
        await session.commit()

        try:
            params = gen_task.input_params or {}
            version_id = params.get("version_id")
            view_type = params.get("view_type", "front")  # front / side / back
            prompt_override = params.get("prompt_override")
            base_prompt = params.get("base_prompt", "")
            reference_images = params.get("reference_images", [])

            # 获取角色版本
            version_repo = CharacterVersionRepository(session)
            version = await version_repo.get(version_id)
            if not version:
                raise RuntimeError(f"CharacterVersion {version_id} 不存在")

            # 构建视图提示词
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
                "生成角色三视图：version_id=%s view_type=%s prompt=%s...",
                version_id, view_type, full_prompt[:50]
            )

            # 调用图片生成
            if reference_images:
                # 下载参考图
                import httpx
                ref_image_data = []
                async with httpx.AsyncClient(timeout=30, trust_env=settings.HTTP_TRUST_ENV) as http_client:
                    for url in reference_images[:3]:
                        try:
                            resp = await http_client.get(url)
                            if resp.status_code == 200:
                                ref_image_data.append(resp.content)
                        except Exception as e:
                            logger.warning(f"下载参考图失败: {url}, error={e}")

                if ref_image_data:
                    result = await image_gen_client.generate_with_reference(
                        prompt=full_prompt,
                        reference_images=ref_image_data,
                        aspect_ratio="2:3",  # 角色图常用比例
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

            if not result.success:
                raise RuntimeError(result.error_message or "图像生成失败")

            # 上传到 OSS
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            filename = f"char_v{version_id}_view_{view_type}_{timestamp}.png"
            image_url = oss_client.upload_bytes(
                result.image_data,
                filename,
                directory="characters/views"
            )

            logger.info("三视图已上传：%s", image_url)

            # 更新角色版本
            field_map = {"front": "view_front_url", "side": "view_side_url", "back": "view_back_url"}
            await version_repo.update(version, {field_map[view_type]: image_url})

            # 更新任务状态
            await task_repo.update(gen_task, {
                "status": "success",
                "progress": 100,
                "completed_at": datetime.now(timezone.utc),
            })
            await session.commit()

            return {
                "status": "success",
                "image_url": image_url,
                "view_type": view_type,
            }

        except Exception as exc:
            logger.exception("三视图生成失败：task_id=%d error=%s", task_db_id, exc)
            await task_repo.update(gen_task, {
                "status": "failed",
                "error_message": str(exc),
                "completed_at": datetime.now(timezone.utc),
            })
            await session.commit()

            if task.request.retries < task.max_retries:
                raise task.retry(exc=exc)

            return {"status": "failed", "error": str(exc)}


async def _run_state_generation(task: CharacterImageTask, task_db_id: int) -> dict:
    """状态图生成核心逻辑。"""
    from app.core.config import settings
    from app.repositories.character import CharacterVersionRepository
    from app.repositories.task import TaskRepository
    from app.utils.image_gen import image_gen_client
    from app.utils.oss import oss_client

    async with task.session_factory() as session:
        task_repo = TaskRepository(session)
        gen_task = await task_repo.get(task_db_id)
        if not gen_task:
            logger.error("GenerationTask %d 不存在", task_db_id)
            return {"status": "failed", "error": "任务记录不存在"}

        await task_repo.update(gen_task, {
            "status": "running",
            "started_at": datetime.now(timezone.utc),
        })
        await session.commit()

        try:
            params = gen_task.input_params or {}
            version_id = params.get("version_id")
            state_type = params.get("state_type", "neutral")
            state_description = params.get("state_description", "")
            prompt_override = params.get("prompt_override")
            base_prompt = params.get("base_prompt", "")
            reference_images = params.get("reference_images", [])
            view_front_url = params.get("view_front_url")

            version_repo = CharacterVersionRepository(session)
            version = await version_repo.get(version_id)
            if not version:
                raise RuntimeError(f"CharacterVersion {version_id} 不存在")

            # 构建状态提示词
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

            state_prompt = state_prompts.get(state_type, state_prompts.get("neutral", "neutral expression"))
            if state_description:
                state_prompt = f"{state_prompt}, {state_description}"

            full_prompt = f"{base_prompt}, {state_prompt}" if base_prompt else state_prompt
            if prompt_override:
                full_prompt = f"{prompt_override}, {state_prompt}"

            logger.info(
                "生成角色状态图：version_id=%s state_type=%s prompt=%s...",
                version_id, state_type, full_prompt[:50]
            )

            # 准备参考图
            ref_image_data = []
            if view_front_url:
                import httpx
                async with httpx.AsyncClient(timeout=30, trust_env=settings.HTTP_TRUST_ENV) as http_client:
                    try:
                        resp = await http_client.get(view_front_url)
                        if resp.status_code == 200:
                            ref_image_data.append(resp.content)
                    except Exception as e:
                        logger.warning(f"下载正面视图失败: {e}")

            for url in reference_images[:2]:
                if url and url != view_front_url:
                    import httpx
                    async with httpx.AsyncClient(timeout=30, trust_env=settings.HTTP_TRUST_ENV) as http_client:
                        try:
                            resp = await http_client.get(url)
                            if resp.status_code == 200:
                                ref_image_data.append(resp.content)
                        except Exception:
                            pass

            # 生成图片
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

            if not result.success:
                raise RuntimeError(result.error_message or "图像生成失败")

            # 上传到 OSS
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            filename = f"char_v{version_id}_state_{state_type}_{timestamp}.png"
            image_url = oss_client.upload_bytes(
                result.image_data,
                filename,
                directory="characters/states"
            )

            logger.info("状态图已上传：%s", image_url)

            # 更新角色版本的 state_images
            state_images = dict(version.state_images or {})
            state_images[state_type] = image_url
            await version_repo.update(version, {"state_images": state_images})

            # 更新任务状态
            await task_repo.update(gen_task, {
                "status": "success",
                "progress": 100,
                "completed_at": datetime.now(timezone.utc),
            })
            await session.commit()

            return {
                "status": "success",
                "image_url": image_url,
                "state_type": state_type,
            }

        except Exception as exc:
            logger.exception("状态图生成失败：task_id=%d error=%s", task_db_id, exc)
            await task_repo.update(gen_task, {
                "status": "failed",
                "error_message": str(exc),
                "completed_at": datetime.now(timezone.utc),
            })
            await session.commit()

            if task.request.retries < task.max_retries:
                raise task.retry(exc=exc)

            return {"status": "failed", "error": str(exc)}
