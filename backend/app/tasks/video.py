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
import math
from datetime import datetime, timezone

from celery import Task

from app.tasks.celery_app import celery_app
from app.prompts import build_video_prompt, build_compact_video_prompt

logger = logging.getLogger(__name__)


def _normalize_kling_duration(seconds: float | None) -> int:
    """将时长规范为 Kling 可接受的整数秒。

    使用 floor 向下取整（如 3.5s → 3s），并确保最小为 1 秒。
    """
    raw = seconds if seconds is not None else 3.0
    return max(1, math.floor(raw))


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
        try:
            from app.utils.evolink import evolink_client
            loop.run_until_complete(evolink_client.close())
        except Exception as exc:
            logger.warning("关闭 Evolink 客户端失败，将继续关闭事件循环: %s", exc)
        loop.close()


async def _run_video_generation(task: VideoGenerationTask, task_db_id: int) -> dict:
    """视频生成异步核心逻辑。"""
    from app.models.task import GenerationTask
    from app.repositories.asset import AssetRepository
    from app.repositories.shot import ShotRepository
    from app.repositories.task import TaskRepository
    from app.utils.evolink import evolink_client

    async with task.get_session_factory()() as session:
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
            from app.repositories.character import CharacterRepository
            from app.repositories.location import LocationRepository
            from app.repositories.shot_group import ShotGroupRepository

            shot_repo = ShotRepository(session)
            char_repo = CharacterRepository(session)
            loc_repo = LocationRepository(session)
            group_repo = ShotGroupRepository(session)

            shot = await shot_repo.get(gen_task.shot_id)
            if not shot:
                raise ValueError(f"Shot {gen_task.shot_id} 不存在")

            # 获取镜头的分镜组（用于获取 image_references）
            group_image_refs: list[dict] = []
            if shot.shot_group_id:
                group = await group_repo.get(shot.shot_group_id)
                if group and group.image_references:
                    group_image_refs = group.image_references

            # 构建角色版本ID→角色名映射
            char_version_lookup: dict[int, str] = {}
            if shot.char_version_ids:
                from app.repositories.storyboard import StoryboardRepository
                sb_repo = StoryboardRepository(session)
                project_id = await sb_repo.get_project_id(shot.storyboard_id) or 0

                chars = await char_repo.get_by_project(project_id, page=1, page_size=100)
                for char in chars.items if hasattr(chars, 'items') else chars:
                    for v in char.versions:
                        if v.id in shot.char_version_ids:
                            char_version_lookup[v.id] = char.name

            # 构建场景版本ID→"场景名·版本名"映射
            from app.repositories.storyboard import StoryboardRepository
            sb_repo = StoryboardRepository(session)
            project_id = await sb_repo.get_project_id(shot.storyboard_id) or 0

            location_version_lookup: dict[int, str] = {}
            env = shot.environment or {}
            loc_ver_id = env.get("location_version_id") or env.get("location_id")
            if loc_ver_id:
                locs = await loc_repo.get_by_project(project_id, page=1, page_size=100)
                for loc in locs.items if hasattr(locs, 'items') else locs:
                    for v in loc.versions:
                        if v.id == loc_ver_id or v.location_id == loc_ver_id:
                            label = v.label or v.version_code or f"版本{v.id}"
                            location_version_lookup[v.id] = f"{loc.name}·{label}"
            # Also build all location version mappings for image refs
            locs = await loc_repo.get_by_project(project_id, page=1, page_size=100)
            for loc in locs.items if hasattr(locs, 'items') else locs:
                for v in loc.versions:
                    if v.id not in location_version_lookup:
                        label = v.label or v.version_code or f"版本{v.id}"
                        location_version_lookup[v.id] = f"{loc.name}·{label}"

            # 更新镜头状态为生成中
            await shot_repo.update(shot, {"status": "generating"})
            await session.commit()

            params = gen_task.input_params or {}
            quality = params.get("quality", "1080p")
            sound = params.get("sound", "on")

            evolink_task_id = params.get("evolink_task_id")

            # 根据是否有首帧图决定调用文生视频还是图生视频
            if params.get("use_image_start") and shot.assets:
                # 找到当前镜头的图片素材作为首帧
                asset_repo = AssetRepository(session)
                image_assets = await asset_repo.get_by_shot(shot.id, current_only=True)
                image_asset = next((a for a in image_assets if a.asset_type == "image"), None)
                image_start = image_asset.file_url if image_asset else None
            else:
                image_start = None

            # 构建完整的视频提示词（含角色参考图标记、角色名、场景名）
            prompt = build_video_prompt(shot, char_version_lookup, location_version_lookup, group_image_refs)

            logger.info("开始生成视频：shot=%s quality=%s sound=%s", shot.shot_code, quality, sound)
            logger.info("=" * 60)
            logger.info("Kling 视频提示词:\n%s", prompt)
            logger.info("=" * 60)

            if evolink_task_id:
                logger.info("检测到已提交的 Evolink 任务，继续轮询：%s", evolink_task_id)
            else:
                if image_start:
                    normalized_duration = _normalize_kling_duration(shot.duration_sec)
                    if normalized_duration < 3 or normalized_duration > 15:
                        raise ValueError(
                            f"镜头 {shot.shot_code} 提交 Kling 的时长必须在 3-15 秒之间，"
                            f"当前规范化后为 {normalized_duration}s"
                        )
                    video_task = await evolink_client.image_to_video(
                        prompt=prompt,
                        image_start=image_start,
                        duration=normalized_duration,
                        quality=quality,
                        sound=sound,
                    )
                else:
                    normalized_duration = _normalize_kling_duration(shot.duration_sec)
                    if normalized_duration < 3 or normalized_duration > 15:
                        raise ValueError(
                            f"镜头 {shot.shot_code} 提交 Kling 的时长必须在 3-15 秒之间，"
                            f"当前规范化后为 {normalized_duration}s"
                        )
                    video_task = await evolink_client.text_to_video(
                        prompt=prompt,
                        duration=normalized_duration,
                        quality=quality,
                        sound=sound,
                    )

                evolink_task_id = video_task.id
                params = {**params, "evolink_task_id": evolink_task_id}
                await task_repo.update(gen_task, {"input_params": params})
                await session.commit()
                logger.info("Evolink 任务已提交：%s，开始轮询…", evolink_task_id)

            # 轮询直到完成（最多 10 分钟），自动下载并上传到 OSS
            result = await evolink_client.wait_for_completion(
                evolink_task_id,
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


# ---------------------------------------------------------------------------
# Multi-shot 视频生成任务（Kling multi_shot 模式）
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    base=VideoGenerationTask,
    name="app.tasks.video.generate_multi_shot_video_task",
    max_retries=3,
    default_retry_delay=60,
    queue="video",
)
def generate_multi_shot_video_task(self, task_db_id: int) -> dict:
    """多镜头视频生成任务入口。

    将一个分镜组的所有成员分镜合并为一次 Kling multi_shot API 调用。

    Args:
        task_db_id: GenerationTask 的数据库 ID。

    Returns:
        {"status": "success", "video_url": str}
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_multi_shot_video_generation(self, task_db_id))
    finally:
        try:
            from app.utils.evolink import evolink_client
            loop.run_until_complete(evolink_client.close())
        except Exception as exc:
            logger.warning("关闭 Evolink 客户端失败：%s", exc)
        loop.close()


async def _run_multi_shot_video_generation(task: VideoGenerationTask, task_db_id: int) -> dict:
    """多镜头视频生成异步核心逻辑。"""
    from app.models.task import GenerationTask
    from app.repositories.shot import ShotRepository
    from app.repositories.shot_group import ShotGroupRepository
    from app.repositories.character import CharacterRepository
    from app.repositories.storyboard import StoryboardRepository
    from app.repositories.task import TaskRepository
    from app.utils.evolink import evolink_client, MultiShotPrompt

    async with task.get_session_factory()() as session:
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
            shot_group_id = params.get("shot_group_id")
            quality = params.get("quality", "1080p")
            sound = params.get("sound", "on")

            # 加载分镜组及成员
            group_repo = ShotGroupRepository(session)
            group = await group_repo.get(shot_group_id)
            if not group:
                raise ValueError(f"ShotGroup {shot_group_id} 不存在")

            shot_repo = ShotRepository(session)
            all_shots = await shot_repo.get_by_storyboard(group.storyboard_id)
            member_shots = sorted(
                [s for s in all_shots if s.shot_group_id == group.id],
                key=lambda s: s.sequence,
            )

            if not member_shots:
                raise ValueError(f"ShotGroup {shot_group_id} 没有成员分镜")

            # 更新所有成员分镜状态
            for shot in member_shots:
                await shot_repo.update(shot, {"status": "generating"})
            await group_repo.update(group, {"status": "generating"})
            await session.commit()

            # 构建角色版本ID→角色名映射 & 场景版本ID→"场景名·版本名"映射
            char_version_lookup: dict[int, str] = {}
            location_version_lookup: dict[int, str] = {}
            all_char_version_ids = set()
            all_location_version_ids = set()
            for s in member_shots:
                all_char_version_ids.update(s.char_version_ids or [])
                env = s.environment or {}
                lvid = env.get("location_version_id") or env.get("location_id")
                if lvid:
                    all_location_version_ids.add(lvid)
            if all_char_version_ids or all_location_version_ids:
                char_repo = CharacterRepository(session)
                loc_repo = LocationRepository(session)
                sb_repo = StoryboardRepository(session)
                project_id = await sb_repo.get_project_id(group.storyboard_id) or 0
                chars = await char_repo.get_by_project(project_id, page=1, page_size=100)
                for char in chars.items if hasattr(chars, 'items') else chars:
                    for v in char.versions:
                        if v.id in all_char_version_ids:
                            char_version_lookup[v.id] = char.name
                locs = await loc_repo.get_by_project(project_id, page=1, page_size=100)
                for loc in locs.items if hasattr(locs, 'items') else locs:
                    for v in loc.versions:
                        if v.id in all_location_version_ids:
                            label = v.label or v.version_code or f"版本{v.id}"
                            location_version_lookup[v.id] = f"{loc.name}·{label}"

            # 构建多镜头提示词
            shot_durations = [_normalize_kling_duration(shot.duration_sec) for shot in member_shots]
            multi_prompts = []
            for i, (shot, normalized_duration) in enumerate(zip(member_shots, shot_durations, strict=False)):
                prompt_text = build_compact_video_prompt(shot)
                multi_prompts.append(MultiShotPrompt(
                    index=i + 1,
                    prompt=prompt_text,
                    duration=str(normalized_duration),
                ))

            total_duration = sum(shot_durations)
            if total_duration < 3 or total_duration > 15:
                raise ValueError(
                    "Kling multi-shot 总时长必须等于各镜头整数时长之和，且在 3-15 秒之间；"
                    f"当前各镜头时长={shot_durations}，总时长={total_duration}s"
                )

            group_code = group.group_code

            logger.info(
                "开始多镜头视频生成：group=%s shots=%d total_duration=%ds",
                group_code, len(member_shots), total_duration,
            )
            logger.info("=" * 60)
            logger.info("Kling Multi-Shot 提示词明细：group=%s", group_code)
            for mp in multi_prompts:
                logger.info("  镜头 %d (%ss) 提示词:\n%s", mp.index, mp.duration, mp.prompt)
            logger.info("=" * 60)

            evolink_task_id = params.get("evolink_task_id")

            if evolink_task_id:
                logger.info("检测到已提交的 Evolink 任务，继续轮询：%s", evolink_task_id)
            else:
                # Check if the group has associated reference images for image-to-video
                image_refs = getattr(group, 'image_references', None) or []
                has_images = len(image_refs) > 0

                if has_images:
                    # Use image-to-video mode
                    image_start = getattr(group, 'image_start_url', None) or None
                    reference_urls = [ref['url'] for ref in image_refs if ref.get('url')]

                    # If no explicit image_start, use the first reference image
                    if not image_start and reference_urls:
                        image_start = reference_urls[0]

                    # Inject 角色参考图标记 into prompts
                    from app.prompts import inject_image_refs_into_prompts
                    multi_prompts = inject_image_refs_into_prompts(multi_prompts, image_refs, char_version_lookup, location_version_lookup)


                    logger.info(
                        "使用 image-to-video 模式：image_start=%s, reference_urls=%d张, 提示词:\n%s",
                        image_start,
                        len(reference_urls),
                        "\n".join([f"  镜头 {mp.index} 提示词:\n{mp.prompt}" for mp in multi_prompts])
                    )
                    video_task = await evolink_client.image_to_video(
                        multi_shot_prompts=multi_prompts,
                        image_start=None,
                        image_urls=reference_urls if reference_urls else None,
                        duration=total_duration,
                        quality=quality,
                        sound=sound,
                    )
                else:
                    # Existing text-to-video path
                    video_task = await evolink_client.text_to_video(
                        multi_shot_prompts=multi_prompts,
                        duration=total_duration,
                        quality=quality,
                        sound=sound,
                    )
                evolink_task_id = video_task.id
                params = {**params, "evolink_task_id": evolink_task_id}
                await task_repo.update(gen_task, {"input_params": params})
                await session.commit()
                logger.info("Evolink 多镜头任务已提交：%s", evolink_task_id)

            # 轮询直到完成
            result = await evolink_client.wait_for_completion(
                evolink_task_id,
                poll_interval=8.0,
                timeout=600.0,
                upload_to_oss=True,
                oss_directory=f"videos/{group_code}",
                oss_filename=f"{group_code}.mp4",
            )

            if not result.video_url:
                raise RuntimeError("Evolink 返回结果中无视频URL")

            logger.info("多镜头视频生成完成：%s url=%s", group_code, result.video_url)

            # 更新分镜组的视频 URL
            await group_repo.update(group, {
                "status": "review",
                "video_url": result.video_url,
            })

            # 同步更新所有成员分镜
            for shot in member_shots:
                await shot_repo.update(shot, {
                    "status": "review",
                    "video_url": result.video_url,
                })

            await task_repo.update(gen_task, {
                "status": "success",
                "progress": 100,
                "completed_at": datetime.now(timezone.utc),
            })
            await session.commit()

            return {"status": "success", "video_url": result.video_url}

        except Exception as exc:
            logger.exception("多镜头视频生成失败：task_id=%d error=%s", task_db_id, exc)
            await task_repo.update(gen_task, {
                "status": "failed",
                "error_message": str(exc),
                "completed_at": datetime.now(timezone.utc),
            })

            # 恢复成员分镜状态
            try:
                shot_group_id = (gen_task.input_params or {}).get("shot_group_id")
                if shot_group_id:
                    group_repo = ShotGroupRepository(session)
                    group = await group_repo.get(shot_group_id)
                    if group:
                        await group_repo.update(group, {"status": "draft"})
                        shot_repo = ShotRepository(session)
                        all_shots = await shot_repo.get_by_storyboard(group.storyboard_id)
                        for s in all_shots:
                            if s.shot_group_id == group.id:
                                await shot_repo.update(s, {"status": "draft"})
            except Exception:
                pass
            await session.commit()

            retryable = (RuntimeError, TimeoutError, ConnectionError)
            if isinstance(exc, retryable) and task.request.retries < task.max_retries:
                raise task.retry(exc=exc)

            return {"status": "failed", "error": str(exc)}
