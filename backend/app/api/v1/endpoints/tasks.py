"""
生成任务（GenerationTask）API 端点。

路由前缀：/api/v1/tasks

提供任务状态查询与视频生成触发接口。
实际的异步生成逻辑由 Celery Worker 执行。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.repositories.task import TaskRepository
from app.schemas.task import (
    ImageGenerationRequest,
    StoryboardGenerationRequest,
    TaskResponse,
    VideoGenerationRequest,
)

router = APIRouter()


@router.get("/{task_id}", response_model=TaskResponse, summary="查询任务状态")
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """按数据库 ID 查询生成任务当前状态。"""
    task = await TaskRepository(db).get(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return task


@router.post("/video", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED, summary="触发视频生成")
async def trigger_video_generation(
    body: VideoGenerationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """为指定镜头触发视频生成 Celery 任务。

    返回 202 Accepted，任务在后台异步执行，可通过 GET /tasks/{task_id} 轮询状态。
    """
    from app.tasks.video import generate_video_task  # 延迟导入，避免循环依赖

    task_repo = TaskRepository(db)

    # 创建任务记录
    task = await task_repo.create(
        shot_id=body.shot_id,
        task_type="video_generation",
        status="pending",
        input_params=body.model_dump(),
    )
    await db.commit()
    await db.refresh(task)

    # 派发 Celery 任务
    celery_result = generate_video_task.delay(task.id)

    # 回写 Celery 任务ID
    await task_repo.update(task, {"celery_task_id": celery_result.id})
    await db.commit()

    return task


@router.post("/storyboard", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED, summary="触发分镜脚本生成")
async def trigger_storyboard_generation(
    body: StoryboardGenerationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """为指定片段触发 AI 分镜脚本生成任务（调用 Google Gemini）。

    返回 202 Accepted，任务在后台异步执行。
    """
    from app.tasks.storyboard import generate_storyboard_task  # 延迟导入，避免循环依赖

    task_repo = TaskRepository(db)

    task = await task_repo.create(
        shot_id=None,   # 分镜生成是场景级任务，不关联具体镜头
        task_type="storyboard_generation",
        status="pending",
        input_params=body.model_dump(),
    )
    await db.commit()
    await db.refresh(task)

    celery_result = generate_storyboard_task.delay(task.id)

    await task_repo.update(task, {"celery_task_id": celery_result.id})
    await db.commit()

    return task


@router.post("/image", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED, summary="触发图像生成")
async def trigger_image_generation(
    body: ImageGenerationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """触发 AI 图像生成任务（调用 Google Imagen）。

    Args:
        body: 图像生成请求参数
            - shot_id: 关联镜头ID（可选）
            - prompt: 正向提示词
            - negative_prompt: 负向提示词（可选）
            - aspect_ratio: 画幅比例（默认 16:9）
            - style_preset: 风格预设（可选）
            - reference_image_url: 参考图URL（可选）
            - save_to_shot: 是否保存到镜头素材库（默认 True）

    Returns:
        202 Accepted，任务在后台异步执行，可通过 GET /tasks/{task_id} 轮询状态。
    """
    from app.tasks.image import generate_image_task  # 延迟导入，避免循环依赖

    task_repo = TaskRepository(db)

    # 如果指定了 shot_id，验证镜头存在
    if body.shot_id:
        from app.repositories.shot import ShotRepository
        shot = await ShotRepository(db).get(body.shot_id)
        if not shot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="镜头不存在")

    # 创建任务记录
    task = await task_repo.create(
        shot_id=body.shot_id,
        task_type="image_generation",
        status="pending",
        input_params=body.model_dump(),
    )
    await db.commit()
    await db.refresh(task)

    # 派发 Celery 任务
    celery_result = generate_image_task.delay(task.id)

    # 回写 Celery 任务ID
    await task_repo.update(task, {"celery_task_id": celery_result.id})
    await db.commit()

    return task
