"""Assets API endpoints.

仅暴露 project 级素材增删查与上传，按 asset_type 区分图片 / 视频 / 音频 / 参考。
不再绑定 shot / character / location 等业务子表。
"""

import os
import uuid
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.repositories.asset import AssetRepository
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


@router.get("", response_model=PageResponse[AssetResponse], summary="获取素材列表")
async def list_assets(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    asset_type: Optional[str] = Query(None, description="按类型过滤"),
    source: Optional[str] = Query(None, description="按来源过滤"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    repo = AssetRepository(db)
    items, total = await repo.get_by_project(
        project_id,
        asset_type=asset_type,
        source=source,
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


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED, summary="手动创建素材记录")
async def create_asset(
    project_id: int,
    body: AssetCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    payload = body.model_dump()
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
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)

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

    file_url = oss_client.upload_bytes(content, filename=filename, directory=f"projects/{project_id}/uploads")

    asset = await AssetRepository(db).create(
        project_id=project_id,
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
