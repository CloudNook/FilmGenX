"""
素材（Asset）API 端点。

路由前缀：/api/v1/projects/{project_id}/assets
"""

import os
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
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


# 支持的文件类型和大小限制
ALLOWED_TYPES = {
    # 图片类型（最大 10MB）
    "image/jpeg": {"asset_type": "image", "max_size": 10 * 1024 * 1024},
    "image/png": {"asset_type": "image", "max_size": 10 * 1024 * 1024},
    "image/webp": {"asset_type": "image", "max_size": 10 * 1024 * 1024},
    "image/gif": {"asset_type": "image", "max_size": 10 * 1024 * 1024},
    # 视频类型（最大 100MB）
    "video/mp4": {"asset_type": "video", "max_size": 100 * 1024 * 1024},
    "video/webm": {"asset_type": "video", "max_size": 100 * 1024 * 1024},
    "video/quicktime": {"asset_type": "video", "max_size": 100 * 1024 * 1024},
    # 音频类型（最大 20MB）
    "audio/mpeg": {"asset_type": "audio", "max_size": 20 * 1024 * 1024},
    "audio/wav": {"asset_type": "audio", "max_size": 20 * 1024 * 1024},
    "audio/mp3": {"asset_type": "audio", "max_size": 20 * 1024 * 1024},
}


@router.post("/upload", response_model=AssetResponse, status_code=status.HTTP_201_CREATED, summary="上传素材文件")
async def upload_asset(
    project_id: int,
    file: UploadFile = File(..., description="要上传的文件"),
    shot_id: Optional[int] = Form(None, description="关联镜头ID（可选）"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """上传素材文件到 OSS 并创建素材记录。

    支持的文件类型：
    - 图片：image/jpeg, image/png, image/webp, image/gif（最大 10MB）
    - 视频：video/mp4, video/webm, video/quicktime（最大 100MB）
    - 音频：audio/mpeg, audio/wav, audio/mp3（最大 20MB）

    Args:
        project_id: 项目ID
        file: 上传的文件
        shot_id: 关联的镜头ID（可选）

    Returns:
        创建的素材记录
    """
    await _require_project(project_id, user_id, db)

    # 验证文件类型
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_TYPES:
        allowed = ", ".join(ALLOWED_TYPES.keys())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {content_type}。支持的类型: {allowed}",
        )

    type_config = ALLOWED_TYPES[content_type]
    asset_type = type_config["asset_type"]
    max_size = type_config["max_size"]

    # 读取文件内容
    content = await file.read()
    file_size = len(content)

    # 验证文件大小
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小 {file_size / (1024 * 1024):.1f}MB 超过限制 {max_mb:.0f}MB",
        )

    # 生成素材代码和文件名
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    original_filename = file.filename or "upload"
    file_ext = os.path.splitext(original_filename)[1] or f".{asset_type}"
    asset_code = f"upload_{timestamp}_{project_id}"
    filename = f"{asset_code}{file_ext}"

    # 确定上传目录
    directory = "uploads"
    if shot_id:
        directory = f"shots/{shot_id}"

    # 上传到 OSS
    file_url = oss_client.upload_bytes(
        content,
        filename=filename,
        directory=directory,
    )

    # 创建素材记录
    repo = AssetRepository(db)
    asset = await repo.create(
        project_id=project_id,
        shot_id=shot_id,
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
