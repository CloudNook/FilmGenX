"""
高光片段（Scene）API 端点。

路由前缀：/api/v1/projects/{project_id}/scenes
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.repositories.project import ProjectRepository
from app.repositories.scene import SceneRepository
from app.schemas.base import PageResponse
from app.schemas.scene import SceneCreate, SceneResponse, SceneUpdate

router = APIRouter()


async def _require_project(project_id: int, user_id: int, db: AsyncSession):
    """校验项目存在且属于当前用户，失败则抛 404。"""
    project = await ProjectRepository(db).get_by_id_and_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project



@router.get("", response_model=PageResponse[SceneResponse], summary="获取片段列表")
async def list_scenes(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    scene_status: str | None = Query(None, alias="status", description="按状态过滤"),
    priority: str | None = Query(None, description="按优先级过滤：S/A/B/C"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """分页获取项目下的高光片段列表。"""
    await _require_project(project_id, user_id, db)
    repo = SceneRepository(db)
    items, total = await repo.get_by_project(
        project_id, status=scene_status, priority=priority, page=page, page_size=page_size
    )
    return PageResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=SceneResponse, status_code=status.HTTP_201_CREATED, summary="创建高光片段")
async def create_scene(
    project_id: int,
    body: SceneCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = SceneRepository(db)

    # 检查 scene_code 唯一性
    if await repo.get_by_code(body.scene_code):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"scene_code '{body.scene_code}' 已存在")

    data = body.model_dump()
    scene = await repo.create(project_id=project_id, **data)
    await db.commit()
    return scene


@router.get("/{scene_id}", response_model=SceneResponse, summary="获取片段详情")
async def get_scene(
    project_id: int,
    scene_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    scene = await SceneRepository(db).get_by_id_and_project(scene_id, project_id)
    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="片段不存在")
    return scene


@router.patch("/{scene_id}", response_model=SceneResponse, summary="更新高光片段")
async def update_scene(
    project_id: int,
    scene_id: int,
    body: SceneUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = SceneRepository(db)
    scene = await repo.get_by_id_and_project(scene_id, project_id)
    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="片段不存在")

    data = body.model_dump(exclude_none=True)
    scene = await repo.update(scene, data)
    await db.commit()
    return scene


@router.delete("/{scene_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除高光片段")
async def delete_scene(
    project_id: int,
    scene_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = SceneRepository(db)
    scene = await repo.get_by_id_and_project(scene_id, project_id)
    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="片段不存在")
    await repo.soft_delete(scene)
    await db.commit()
