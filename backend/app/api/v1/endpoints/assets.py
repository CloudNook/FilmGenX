"""
素材（Asset）API 端点。

路由前缀：/api/v1/projects/{project_id}/assets
"""

from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.repositories.asset import AssetRepository
from app.repositories.project import ProjectRepository
from app.schemas.asset import AssetCreate, AssetResponse
from app.schemas.base import PageResponse

router = APIRouter()


async def _require_project(project_id: int, user_id: int, db: AsyncSession):
    project = await ProjectRepository(db).get_by_id_and_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project


@router.get("", response_model=PageResponse[AssetResponse], summary="获取素材列表")
async def list_assets(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    asset_type: Optional[str] = Query(None, description="按类型过滤：image/video/audio/reference"),
    shot_id: Optional[int] = Query(None, description="按镜头ID过滤"),
    source: Optional[str] = Query(None, description="按来源过滤：generated/uploaded"),
    is_current: Optional[bool] = Query(None, description="是否只看当前版本"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = AssetRepository(db)
    items, total = await repo.get_by_project(
        project_id,
        asset_type=asset_type,
        shot_id=shot_id,
        source=source,
        is_current=is_current,
        page=page,
        page_size=page_size,
    )
    return PageResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/stats", response_model=Dict[str, int], summary="获取素材统计")
async def get_asset_stats(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """获取项目下各类型素材的数量统计。"""
    await _require_project(project_id, user_id, db)
    repo = AssetRepository(db)
    return await repo.get_stats_by_project(project_id)


@router.get("/shot/{shot_id}/stats", response_model=Dict[str, int], summary="获取镜头素材统计")
async def get_shot_asset_stats(
    project_id: int,
    shot_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """获取指定镜头下各类型素材的数量统计。"""
    await _require_project(project_id, user_id, db)
    repo = AssetRepository(db)
    return await repo.get_stats_by_shot(shot_id)


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED, summary="手动创建素材记录")
async def create_asset(
    project_id: int,
    body: AssetCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """手动登记素材（如上传参考图）。AI 生成任务完成后由系统自动创建素材记录。"""
    await _require_project(project_id, user_id, db)
    asset = await AssetRepository(db).create(project_id=project_id, **body.model_dump())
    await db.commit()
    return asset


@router.get("/{asset_id}", response_model=AssetResponse, summary="获取素材详情")
async def get_asset(
    project_id: int,
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    asset = await AssetRepository(db).get(asset_id)
    if not asset or asset.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="素材不存在")
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除素材")
async def delete_asset(
    project_id: int,
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = AssetRepository(db)
    asset = await repo.get(asset_id)
    if not asset or asset.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="素材不存在")
    await repo.soft_delete(asset)
    await db.commit()
