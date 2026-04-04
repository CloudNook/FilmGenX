"""
生成任务（GenerationTask）API 端点。

路由前缀：/api/v1/tasks
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.repositories.location import LocationRepository
from app.repositories.project import ProjectRepository
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
    from app.tasks.video import generate_video_task

    task_repo = TaskRepository(db)
    task = await task_repo.create(
        shot_id=body.shot_id,
        task_type="video_generation",
        status="pending",
        input_params=body.model_dump(),
    )
    await db.commit()
    await db.refresh(task)

    celery_result = generate_video_task.delay(task.id)
    await task_repo.update(task, {"celery_task_id": celery_result.id})
    await db.commit()
    return task


@router.post("/storyboard", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED, summary="触发分镜脚本生成")
async def trigger_storyboard_generation(
    body: StoryboardGenerationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    from app.tasks.storyboard import generate_storyboard_task

    task_repo = TaskRepository(db)
    task = await task_repo.create(
        shot_id=None,
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
    from app.tasks.image import generate_image_task

    task_repo = TaskRepository(db)

    if body.shot_id:
        from app.repositories.shot import ShotRepository

        shot = await ShotRepository(db).get(body.shot_id)
        if not shot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="镜头不存在")

    if body.location_id is not None:
        if body.project_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="location_id 生成时必须传 project_id",
            )
        project = await ProjectRepository(db).get_by_id_and_owner(body.project_id, user_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
        location = await LocationRepository(db).get_by_id_and_project(body.location_id, body.project_id)
        if not location:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场景不存在")

    task = await task_repo.create(
        shot_id=body.shot_id,
        task_type="image_generation",
        status="pending",
        input_params=body.model_dump(),
    )
    await db.commit()
    await db.refresh(task)

    celery_result = generate_image_task.delay(task.id)
    await task_repo.update(task, {"celery_task_id": celery_result.id})
    await db.commit()
    return task
