"""Assets API endpoints."""

import os
import uuid
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.repositories.asset import AssetRepository
from app.repositories.location import LocationRepository, LocationVersionRepository
from app.repositories.project import ProjectRepository
from app.schemas.asset import AssetCreate, AssetResponse
from app.schemas.base import PageResponse
from app.utils.oss import oss_client

router = APIRouter()


async def _require_project(project_id: int, user_id: int, db: AsyncSession):
    project = await ProjectRepository(db).get_by_id_and_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project


async def _resolve_location_scope(
    db: AsyncSession,
    project_id: int,
    *,
    location_id: Optional[int],
    location_version_id: Optional[int],
) -> tuple[Optional[int], Optional[int]]:
    """Validate location scope and infer location_id from location_version_id when needed."""
    if location_version_id is not None:
        version_repo = LocationVersionRepository(db)
        if location_id is not None:
            version = await version_repo.get_by_id_and_location(location_version_id, location_id)
        else:
            version = await version_repo.get(location_version_id)
        if not version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场景版本不存在")
        location_id = location_id or version.location_id

    if location_id is not None:
        location = await LocationRepository(db).get_by_id_and_project(location_id, project_id)
        if not location:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场景不存在")

    return location_id, location_version_id


@router.get("", response_model=PageResponse[AssetResponse], summary="获取素材列表")
async def list_assets(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    asset_type: Optional[str] = Query(None, description="按类型过滤"),
    shot_id: Optional[int] = Query(None, description="按镜头过滤"),
    location_id: Optional[int] = Query(None, description="按场景过滤"),
    location_version_id: Optional[int] = Query(None, description="按场景版本过滤"),
    source: Optional[str] = Query(None, description="按来源过滤"),
    is_current: Optional[bool] = Query(None, description="是否仅返回当前版本"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = AssetRepository(db)
    items, total = await repo.get_by_project(
        project_id,
        asset_type=asset_type,
        shot_id=shot_id,
        location_id=location_id,
        location_version_id=location_version_id,
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
    await _require_project(project_id, user_id, db)
    return await AssetRepository(db).get_stats_by_project(project_id)


@router.get("/shot/{shot_id}/stats", response_model=Dict[str, int], summary="获取镜头素材统计")
async def get_shot_asset_stats(
    project_id: int,
    shot_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    return await AssetRepository(db).get_stats_by_shot(shot_id)


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED, summary="手动创建素材记录")
async def create_asset(
    project_id: int,
    body: AssetCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    location_id, location_version_id = await _resolve_location_scope(
        db,
        project_id,
        location_id=body.location_id,
        location_version_id=body.location_version_id,
    )

    payload = body.model_dump()
    payload["location_id"] = location_id
    payload["location_version_id"] = location_version_id

    asset = await AssetRepository(db).create(project_id=project_id, **payload)
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

    try:
        oss_client.delete_by_url(asset.file_url)
    except Exception:
        pass

    if asset.location_version_id is not None:
        version_repo = LocationVersionRepository(db)
        version = await version_repo.get(asset.location_version_id)
        if version and asset.file_url in (version.reference_image_urls or []):
            urls = [url for url in (version.reference_image_urls or []) if url != asset.file_url]
            await version_repo.update(version, {"reference_image_urls": urls})
    elif asset.location_id is not None:
        location_repo = LocationRepository(db)
        location = await location_repo.get(asset.location_id)
        if location and asset.file_url in (location.reference_image_urls or []):
            urls = [url for url in (location.reference_image_urls or []) if url != asset.file_url]
            await location_repo.update(location, {"reference_image_urls": urls})

    await repo.soft_delete(asset)
    await db.commit()


ALLOWED_TYPES = {
    "image/jpeg": {"asset_type": "image", "max_size": 10 * 1024 * 1024},
    "image/png": {"asset_type": "image", "max_size": 10 * 1024 * 1024},
    "image/webp": {"asset_type": "image", "max_size": 10 * 1024 * 1024},
    "image/gif": {"asset_type": "image", "max_size": 10 * 1024 * 1024},
    "video/mp4": {"asset_type": "video", "max_size": 100 * 1024 * 1024},
    "video/webm": {"asset_type": "video", "max_size": 100 * 1024 * 1024},
    "video/quicktime": {"asset_type": "video", "max_size": 100 * 1024 * 1024},
    "audio/mpeg": {"asset_type": "audio", "max_size": 20 * 1024 * 1024},
    "audio/wav": {"asset_type": "audio", "max_size": 20 * 1024 * 1024},
    "audio/mp3": {"asset_type": "audio", "max_size": 20 * 1024 * 1024},
}


@router.post("/upload", response_model=AssetResponse, status_code=status.HTTP_201_CREATED, summary="上传素材文件")
async def upload_asset(
    project_id: int,
    file: UploadFile = File(..., description="要上传的文件"),
    shot_id: Optional[int] = Form(None, description="关联镜头 ID"),
    location_id: Optional[int] = Form(None, description="关联场景 ID"),
    location_version_id: Optional[int] = Form(None, description="关联场景版本 ID"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)

    location_id, location_version_id = await _resolve_location_scope(
        db,
        project_id,
        location_id=location_id,
        location_version_id=location_version_id,
    )

    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_TYPES:
        allowed = ", ".join(ALLOWED_TYPES.keys())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {content_type}。支持类型: {allowed}",
        )

    type_config = ALLOWED_TYPES[content_type]
    asset_type = type_config["asset_type"]
    max_size = type_config["max_size"]

    content = await file.read()
    file_size = len(content)
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小 {file_size / (1024 * 1024):.1f}MB 超过限制 {max_mb:.0f}MB",
        )

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    original_filename = file.filename or "upload"
    file_ext = os.path.splitext(original_filename)[1] or f".{asset_type}"
    asset_code = f"upload_{timestamp}_{project_id}_{uuid.uuid4().hex[:8]}"
    filename = f"{asset_code}{file_ext}"

    directory = "uploads"
    if shot_id:
        directory = f"shots/{shot_id}"
    elif location_version_id:
        directory = f"locations/{location_id}/versions/{location_version_id}"
    elif location_id:
        directory = f"locations/{location_id}"

    file_url = oss_client.upload_bytes(content, filename=filename, directory=directory)

    asset = await AssetRepository(db).create(
        project_id=project_id,
        shot_id=shot_id,
        location_id=location_id,
        location_version_id=location_version_id,
        asset_code=asset_code,
        asset_type=asset_type,
        file_url=file_url,
        file_format=file_ext.lstrip("."),
        file_size_bytes=file_size,
        source="uploaded",
        tags=["uploaded", asset_type],
    )
    await db.commit()
    await db.refresh(asset)
    return asset
