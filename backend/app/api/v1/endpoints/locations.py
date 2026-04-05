"""
场景地点（Location / LocationVersion）API 端点。

路由前缀：/api/v1/projects/{project_id}/locations
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.repositories.location import LocationRepository, LocationVersionRepository
from app.repositories.project import ProjectRepository
from app.schemas.base import PageResponse
from app.schemas.location import (
    LocationCreate, LocationDetailResponse, LocationResponse, LocationUpdate,
    LocationVersionCreate, LocationVersionResponse, LocationVersionUpdate,
    LocationBrief,
)

router = APIRouter()


async def _require_project(project_id: int, user_id: int, db: AsyncSession):
    project = await ProjectRepository(db).get_by_id_and_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project


async def _generate_location_code(repo: LocationRepository, project_id: int) -> str:
    """按项目自动生成 loc_code。"""
    next_num = await repo.count_by_project(project_id, include_deleted=True) + 1
    loc_code = f"P{project_id}_LOC{next_num:03d}"
    while await repo.get_by_code(loc_code, include_deleted=True):
        next_num += 1
        loc_code = f"P{project_id}_LOC{next_num:03d}"
    return loc_code


# ---------------------------------------------------------------------------
# 场景 CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=PageResponse[LocationResponse], summary="获取场景列表")
async def list_locations(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    is_active: Optional[bool] = Query(None, description="按状态过滤"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = LocationRepository(db)
    items, total = await repo.get_by_project(project_id, page=page, page_size=page_size, is_active=is_active)
    return PageResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/brief", response_model=List[LocationBrief], summary="获取场景简要列表（下拉选择用）")
async def list_locations_brief(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """获取启用状态的场景简要信息，用于下拉选择。"""
    await _require_project(project_id, user_id, db)
    repo = LocationRepository(db)
    items = await repo.get_active_list(project_id)
    return items


@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED, summary="创建场景")
async def create_location(
    project_id: int,
    body: LocationCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = LocationRepository(db)

    data = body.model_dump()
    data["loc_code"] = await _generate_location_code(repo, project_id)
    # 处理 nested dict
    if data.get("default_atmosphere") and hasattr(data["default_atmosphere"], "model_dump"):
        data["default_atmosphere"] = data["default_atmosphere"].model_dump()

    location = await repo.create(project_id=project_id, **data)
    await db.commit()
    return location


@router.get("/{location_id}", response_model=LocationDetailResponse, summary="获取场景详情")
async def get_location(
    project_id: int,
    location_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = LocationRepository(db)
    location = await repo.get_with_versions(location_id)
    if not location or location.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场景不存在")

    # 构建响应
    default_version = None
    for v in location.versions:
        if v.is_default:
            default_version = v
            break

    return LocationDetailResponse(
        **{c.name: getattr(location, c.name) for c in location.__table__.columns},
        versions=location.versions,
        default_version=default_version,
        version_count=len(location.versions),
    )


@router.patch("/{location_id}", response_model=LocationResponse, summary="更新场景")
async def update_location(
    project_id: int,
    location_id: int,
    body: LocationUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = LocationRepository(db)
    location = await repo.get_by_id_and_project(location_id, project_id)
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场景不存在")

    data = body.model_dump(exclude_none=True)
    if data.get("default_atmosphere") and hasattr(data["default_atmosphere"], "model_dump"):
        data["default_atmosphere"] = data["default_atmosphere"].model_dump()

    location = await repo.update(location, data)
    await db.commit()
    return location


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除场景")
async def delete_location(
    project_id: int,
    location_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = LocationRepository(db)
    location = await repo.get_by_id_and_project(location_id, project_id)
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场景不存在")
    await repo.soft_delete(location)
    await db.commit()


# ---------------------------------------------------------------------------
# 场景版本 CRUD
# ---------------------------------------------------------------------------

@router.get("/{location_id}/versions", response_model=List[LocationVersionResponse], summary="获取场景版本列表")
async def list_versions(
    project_id: int,
    location_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    # 确认场景属于该项目
    loc = await LocationRepository(db).get_by_id_and_project(location_id, project_id)
    if not loc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场景不存在")
    versions = await LocationVersionRepository(db).get_by_location(location_id)
    return versions


@router.post("/{location_id}/versions", response_model=LocationVersionResponse, status_code=status.HTTP_201_CREATED, summary="添加场景版本")
async def create_version(
    project_id: int,
    location_id: int,
    body: LocationVersionCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    loc = await LocationRepository(db).get_by_id_and_project(location_id, project_id)
    if not loc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场景不存在")

    data = body.model_dump()
    if data.get("atmosphere_override") and hasattr(data["atmosphere_override"], "model_dump"):
        data["atmosphere_override"] = data["atmosphere_override"].model_dump()

    repo = LocationVersionRepository(db)
    version = await repo.create(location_id=location_id, **data)
    if version.is_default:
        await repo.clear_default_for_location(location_id, exclude_id=version.id)
    await db.commit()
    return version


@router.patch("/{location_id}/versions/{version_id}", response_model=LocationVersionResponse, summary="更新场景版本")
async def update_version(
    project_id: int,
    location_id: int,
    version_id: int,
    body: LocationVersionUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = LocationVersionRepository(db)
    version = await repo.get_by_id_and_location(version_id, location_id)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="版本不存在")

    data = body.model_dump(exclude_none=True)
    if data.get("atmosphere_override") and hasattr(data["atmosphere_override"], "model_dump"):
        data["atmosphere_override"] = data["atmosphere_override"].model_dump()

    version = await repo.update(version, data)
    if version.is_default:
        await repo.clear_default_for_location(location_id, exclude_id=version.id)
    await db.commit()
    return version


@router.delete("/{location_id}/versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除场景版本")
async def delete_version(
    project_id: int,
    location_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = LocationVersionRepository(db)
    version = await repo.get_by_id_and_location(version_id, location_id)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="版本不存在")
    await repo.soft_delete(version)
    await db.commit()
