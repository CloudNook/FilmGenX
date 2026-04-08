"""
角色（Character）API 端点。

路由前缀：/api/v1/projects/{project_id}/characters
"""

import random
import string

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.repositories.character import CharacterRepository
from app.repositories.project import ProjectRepository
from app.schemas.base import PageResponse
from app.schemas.character import (
    CharacterCreate, CharacterResponse, CharacterUpdate,
)

router = APIRouter()


async def _require_project(project_id: int, user_id: int, db: AsyncSession):
    project = await ProjectRepository(db).get_by_id_and_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project


@router.get("", response_model=PageResponse[CharacterResponse], summary="获取角色列表")
async def list_characters(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = CharacterRepository(db)
    items, total = await repo.get_by_project(project_id, page=page, page_size=page_size)
    return PageResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED, summary="创建角色")
async def create_character(
    project_id: int,
    body: CharacterCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = CharacterRepository(db)

    # 自动生成 6 位随机 char_code
    while True:
        char_code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        if not await repo.get_by_code(char_code, include_deleted=True):
            break

    character = await repo.create(project_id=project_id, char_code=char_code, **body.model_dump())
    await db.commit()
    return character


@router.get("/{character_id}", response_model=CharacterResponse, summary="获取角色详情")
async def get_character(
    project_id: int,
    character_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    character = await CharacterRepository(db).get_by_id_and_project(character_id, project_id)
    if not character or character.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    return character


@router.patch("/{character_id}", response_model=CharacterResponse, summary="更新角色")
async def update_character(
    project_id: int,
    character_id: int,
    body: CharacterUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = CharacterRepository(db)
    character = await repo.get_by_id_and_project(character_id, project_id)
    if not character:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    character = await repo.update(character, body.model_dump(exclude_none=True))
    await db.commit()
    return character


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除角色")
async def delete_character(
    project_id: int,
    character_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = CharacterRepository(db)
    character = await repo.get_by_id_and_project(character_id, project_id)
    if not character:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    await repo.soft_delete(character)
    await db.commit()
