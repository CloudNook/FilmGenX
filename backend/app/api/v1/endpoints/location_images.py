"""
场景图片管理 API 端点。

路由前缀：/api/v1/projects/{project_id}/locations/{location_id}/images

功能：
- 场景封面图上传/删除
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.repositories.location import LocationRepository
from app.repositories.project import ProjectRepository
from app.schemas.location import LocationResponse
from app.utils.oss import oss_client

router = APIRouter()


async def _require_location(
    project_id: int, location_id: int, user_id: int, db: AsyncSession
):
    project = await ProjectRepository(db).get_by_id_and_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    loc = await LocationRepository(db).get_by_id_and_project(location_id, project_id)
    if not loc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="场景不存在")
    return loc


@router.post("/pic", response_model=LocationResponse, summary="上传场景封面图")
async def upload_pic_image(
    project_id: int,
    location_id: int,
    file: UploadFile = File(..., description="场景封面图文件"),
    pic_name: str | None = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """上传场景封面图。"""
    location = await _require_location(project_id, location_id, user_id, db)

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持图片文件")

    content = await file.read()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    filename = f"loc_{location_id}_pic_{timestamp}.jpg"
    image_url = oss_client.upload_bytes(content, filename, directory="locations/pics")

    update_data: dict = {"pic_url": image_url}
    if pic_name:
        update_data["pic_name"] = pic_name

    repo = LocationRepository(db)
    await repo.update(location, update_data)
    await db.commit()
    await db.refresh(location)
    return location


@router.delete("/pic", response_model=LocationResponse, summary="删除场景封面图")
async def delete_pic_image(
    project_id: int,
    location_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """删除场景封面图。"""
    location = await _require_location(project_id, location_id, user_id, db)

    if location.pic_url:
        try:
            oss_client.delete_by_url(location.pic_url)
        except Exception:
            pass

    repo = LocationRepository(db)
    await repo.update(location, {"pic_url": None, "pic_name": None})
    await db.commit()
    await db.refresh(location)
    return location
