"""
角色图片管理 API 端点。

路由前缀：/api/v1/projects/{project_id}/characters/{character_id}/versions/{version_id}/images

功能：
- 图片上传（参考图、三视图、状态图）
- 图片生成（三视图、状态图）
"""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.repositories.character import CharacterRepository, CharacterVersionRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.schemas.base import BaseResponse
from app.schemas.character import (
    CharacterStateImageGenerateRequest,
    CharacterVersionResponse,
    CharacterViewGenerateRequest,
)
from app.utils.oss import oss_client

router = APIRouter()


async def _require_project(project_id: int, user_id: int, db: AsyncSession):
    project = await ProjectRepository(db).get_by_id_and_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project


async def _require_version(
    project_id: int, character_id: int, version_id: int, user_id: int, db: AsyncSession
):
    """验证版本存在且属于该角色和项目。"""
    await _require_project(project_id, user_id, db)
    char = await CharacterRepository(db).get_by_id_and_project(character_id, project_id)
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    version = await CharacterVersionRepository(db).get_by_id_and_character(version_id, character_id)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="版本不存在")
    return version


# ---------------------------------------------------------------------------
# 图片上传
# ---------------------------------------------------------------------------

@router.post("/reference", response_model=CharacterVersionResponse, summary="上传参考图")
async def upload_reference_image(
    project_id: int,
    character_id: int,
    version_id: int,
    file: UploadFile = File(..., description="图片文件"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """上传角色参考图（添加到 reference_image_urls 列表）。"""
    version = await _require_version(project_id, character_id, version_id, user_id, db)

    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持图片文件")

    # 上传到 OSS
    content = await file.read()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    filename = f"char_{character_id}_v{version_id}_ref_{timestamp}.jpg"
    image_url = oss_client.upload_bytes(content, filename, directory="characters/reference")

    # 更新版本记录
    urls = list(version.reference_image_urls or [])
    urls.append(image_url)
    version_repo = CharacterVersionRepository(db)
    await version_repo.update(version, {"reference_image_urls": urls})
    await db.commit()

    return version


@router.post("/view/{view_type}", response_model=CharacterVersionResponse, summary="上传三视图")
async def upload_view_image(
    project_id: int,
    character_id: int,
    version_id: int,
    view_type: str,  # front / side / back
    file: UploadFile = File(..., description="图片文件"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """上传角色三视图（正面/侧面/背面）。"""
    if view_type not in ("front", "side", "back"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="view_type 必须是 front/side/back")

    version = await _require_version(project_id, character_id, version_id, user_id, db)

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持图片文件")

    content = await file.read()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    filename = f"char_{character_id}_v{version_id}_view_{view_type}_{timestamp}.jpg"
    image_url = oss_client.upload_bytes(content, filename, directory="characters/views")

    # 更新对应字段
    field_map = {"front": "view_front_url", "side": "view_side_url", "back": "view_back_url"}
    version_repo = CharacterVersionRepository(db)
    await version_repo.update(version, {field_map[view_type]: image_url})
    await db.commit()

    return version


@router.post("/state/{state_type}", response_model=CharacterVersionResponse, summary="上传状态图")
async def upload_state_image(
    project_id: int,
    character_id: int,
    version_id: int,
    state_type: str,  # anger / happy / skill_release / etc
    file: UploadFile = File(..., description="图片文件"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """上传角色状态图（愤怒/开心/释放技能等）。"""
    version = await _require_version(project_id, character_id, version_id, user_id, db)

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持图片文件")

    content = await file.read()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    filename = f"char_{character_id}_v{version_id}_state_{state_type}_{timestamp}.jpg"
    image_url = oss_client.upload_bytes(content, filename, directory="characters/states")

    # 更新 state_images 字典
    state_images = dict(version.state_images or {})
    state_images[state_type] = image_url
    version_repo = CharacterVersionRepository(db)
    await version_repo.update(version, {"state_images": state_images})
    await db.commit()

    return version


# ---------------------------------------------------------------------------
# 图片删除
# ---------------------------------------------------------------------------

@router.delete("/reference/{image_index}", response_model=CharacterVersionResponse, summary="删除参考图")
async def delete_reference_image(
    project_id: int,
    character_id: int,
    version_id: int,
    image_index: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """删除指定索引的参考图。"""
    version = await _require_version(project_id, character_id, version_id, user_id, db)

    urls = list(version.reference_image_urls or [])
    if image_index < 0 or image_index >= len(urls):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片索引越界")

    # 删除 OSS 文件（可选）
    try:
        oss_client.delete_by_url(urls[image_index])
    except Exception:
        pass  # OSS 删除失败不影响数据库操作

    urls.pop(image_index)
    version_repo = CharacterVersionRepository(db)
    await version_repo.update(version, {"reference_image_urls": urls})
    await db.commit()

    return version


@router.delete("/view/{view_type}", response_model=CharacterVersionResponse, summary="删除三视图")
async def delete_view_image(
    project_id: int,
    character_id: int,
    version_id: int,
    view_type: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """删除指定视图的图片。"""
    if view_type not in ("front", "side", "back"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="view_type 必须是 front/side/back")

    version = await _require_version(project_id, character_id, version_id, user_id, db)

    field_map = {"front": "view_front_url", "side": "view_side_url", "back": "view_back_url"}
    url = getattr(version, field_map[view_type])

    if url:
        try:
            oss_client.delete_by_url(url)
        except Exception:
            pass

    version_repo = CharacterVersionRepository(db)
    await version_repo.update(version, {field_map[view_type]: None})
    await db.commit()

    return version


@router.delete("/state/{state_type}", response_model=CharacterVersionResponse, summary="删除状态图")
async def delete_state_image(
    project_id: int,
    character_id: int,
    version_id: int,
    state_type: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """删除指定状态的图片。"""
    version = await _require_version(project_id, character_id, version_id, user_id, db)

    state_images = dict(version.state_images or {})
    if state_type in state_images:
        try:
            oss_client.delete_by_url(state_images[state_type])
        except Exception:
            pass
        del state_images[state_type]

    version_repo = CharacterVersionRepository(db)
    await version_repo.update(version, {"state_images": state_images})
    await db.commit()

    return version


# ---------------------------------------------------------------------------
# 图片生成任务
# ---------------------------------------------------------------------------

class ImageGenerateTaskResponse(BaseResponse):
    """图片生成任务响应。"""
    task_id: int
    task_type: str
    status: str
    message: str


@router.post("/generate/view", response_model=ImageGenerateTaskResponse, status_code=status.HTTP_202_ACCEPTED, summary="生成三视图")
async def generate_view_image(
    project_id: int,
    character_id: int,
    version_id: int,
    body: CharacterViewGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """异步生成角色三视图（基于角色描述和参考图）。"""
    version = await _require_version(project_id, character_id, version_id, user_id, db)

    # 创建生成任务
    task_repo = TaskRepository(db)
    task = await task_repo.create(
        shot_id=None,  # 角色生成不关联镜头
        celery_task_id=None,  # Celery 任务 ID 在任务启动后填充
        task_type="character_view_generation",
        input_params={
            "project_id": project_id,
            "character_id": character_id,
            "version_id": version_id,
            "view_type": body.view_type,
            "prompt_override": body.prompt_override,
            "base_prompt": version.base_image_prompt,
            "reference_images": version.reference_image_urls,
        },
    )
    await db.commit()

    # 触发 Celery 任务
    from app.tasks.character import generate_character_view_task
    celery_result = generate_character_view_task.delay(task.id)
    await task_repo.update(task, {"celery_task_id": celery_result.id})
    await db.commit()

    return ImageGenerateTaskResponse(
        id=task.id,
        task_id=task.id,
        task_type="character_view_generation",
        status="pending",
        message=f"三视图生成任务已创建，正在生成 {body.view_type} 视图",
    )


@router.post("/generate/state", response_model=ImageGenerateTaskResponse, status_code=status.HTTP_202_ACCEPTED, summary="生成状态图")
async def generate_state_image(
    project_id: int,
    character_id: int,
    version_id: int,
    body: CharacterStateImageGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """异步生成角色状态图（愤怒/开心/释放技能等）。"""
    version = await _require_version(project_id, character_id, version_id, user_id, db)

    task_repo = TaskRepository(db)
    task = await task_repo.create(
        shot_id=None,
        celery_task_id=None,
        task_type="character_state_generation",
        input_params={
            "project_id": project_id,
            "character_id": character_id,
            "version_id": version_id,
            "state_type": body.state_type,
            "state_description": body.state_description,
            "prompt_override": body.prompt_override,
            "base_prompt": version.base_image_prompt,
            "reference_images": version.reference_image_urls,
            "view_front_url": version.view_front_url,
        },
    )
    await db.commit()

    from app.tasks.character import generate_character_state_task
    celery_result = generate_character_state_task.delay(task.id)
    await task_repo.update(task, {"celery_task_id": celery_result.id})
    await db.commit()

    return ImageGenerateTaskResponse(
        id=task.id,
        task_id=task.id,
        task_type="character_state_generation",
        status="pending",
        message=f"状态图生成任务已创建，正在生成 {body.state_type} 状态",
    )
