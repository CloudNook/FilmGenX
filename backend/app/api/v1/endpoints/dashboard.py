"""
Dashboard API 端点。

路由前缀：/api/v1/projects/{project_id}/dashboard
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.repositories.asset import AssetRepository
from app.repositories.character import CharacterRepository
from app.repositories.location import LocationRepository
from app.repositories.project import ProjectRepository
from app.schemas.asset import AssetDashboardResponse
from app.schemas.character import CharacterDashboardResponse
from app.schemas.location import LocationDashboardResponse

router = APIRouter()


async def _require_project(project_id: int, user_id: int, db: AsyncSession):
    project = await ProjectRepository(db).get_by_id_and_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project


@router.get("/character", response_model=CharacterDashboardResponse, summary="获取角色总览")
async def get_character_dashboard(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = CharacterRepository(db)
    total_characters = await repo.get_dashboard_stats(project_id)
    recent_characters = await repo.get_recent_by_project(project_id, limit=5)
    return CharacterDashboardResponse(
        total_characters=total_characters,
        recent_characters=recent_characters,
    )


@router.get("/location", response_model=LocationDashboardResponse, summary="获取场景总览")
async def get_location_dashboard(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = LocationRepository(db)
    total_locations, total_images = await repo.get_dashboard_stats(project_id)
    recent_locations = await repo.get_recent_by_project(project_id, limit=5)
    return LocationDashboardResponse(
        total_locations=total_locations,
        total_images=total_images,
        recent_locations=recent_locations,
    )


@router.get("/asset", response_model=AssetDashboardResponse, summary="获取素材总览")
async def get_asset_dashboard(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = AssetRepository(db)
    asset_type_counts = await repo.get_stats_by_project(project_id)
    recent_assets = await repo.get_recent_by_project(project_id, limit=6)
    return AssetDashboardResponse(
        total_assets=sum(asset_type_counts.values()),
        asset_type_counts=asset_type_counts,
        recent_assets=recent_assets,
    )
