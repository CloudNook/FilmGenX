"""
项目（Project）API 端点。

路由前缀：/api/v1/projects
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.repositories.project import ProjectRepository
from app.schemas.base import PageResponse
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter()


@router.get("", response_model=PageResponse[ProjectResponse], summary="获取项目列表")
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """分页获取当前用户的所有项目。"""
    repo = ProjectRepository(db)
    items, total = await repo.get_by_owner(user_id, page=page, page_size=page_size)
    return PageResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, summary="创建项目")
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """创建新项目。"""
    repo = ProjectRepository(db)
    project = await repo.create(owner_id=user_id, **body.model_dump())
    await db.commit()
    return project


@router.get("/{project_id}", response_model=ProjectResponse, summary="获取项目详情")
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    repo = ProjectRepository(db)
    project = await repo.get_by_id_and_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse, summary="更新项目")
async def update_project(
    project_id: int,
    body: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    repo = ProjectRepository(db)
    project = await repo.get_by_id_and_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    # 只更新传入的非 None 字段
    update_data = body.model_dump(exclude_none=True)
    project = await repo.update(project, update_data)
    await db.commit()
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除项目")
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    repo = ProjectRepository(db)
    project = await repo.get_by_id_and_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    await repo.soft_delete(project)
    await db.commit()
