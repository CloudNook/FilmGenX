"""
角色图片管理 API 端点。

路由前缀：/api/v1/projects/{project_id}/characters/{character_id}/images

功能：
- 角色图片上传/删除
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.repositories.character import CharacterRepository
from app.repositories.project import ProjectRepository
from app.schemas.character import CharacterResponse
from app.utils.oss import oss_client

router = APIRouter()


async def _require_character(
    project_id: int, character_id: int, user_id: int, db: AsyncSession
):
    project = await ProjectRepository(db).get_by_id_and_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    char = await CharacterRepository(db).get_by_id_and_project(character_id, project_id)
    if not char:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    return char


@router.post("/pic", response_model=CharacterResponse, summary="上传角色图片")
async def upload_pic_image(
    project_id: int,
    character_id: int,
    file: UploadFile = File(..., description="角色图片文件"),
    pic_name: str | None = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """上传角色主图。"""
    character = await _require_character(project_id, character_id, user_id, db)

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持图片文件")

    content = await file.read()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    filename = f"char_{character_id}_pic_{timestamp}.jpg"
    image_url = oss_client.upload_bytes(content, filename, directory="characters/pics")

    update_data: dict = {"pic_url": image_url}
    if pic_name:
        update_data["pic_name"] = pic_name

    repo = CharacterRepository(db)
    await repo.update(character, update_data)
    await db.commit()
    await db.refresh(character)
    return character


@router.delete("/pic", response_model=CharacterResponse, summary="删除角色图片")
async def delete_pic_image(
    project_id: int,
    character_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """删除角色主图。"""
    character = await _require_character(project_id, character_id, user_id, db)

    if character.pic_url:
        try:
            oss_client.delete_by_url(character.pic_url)
        except Exception:
            pass

    repo = CharacterRepository(db)
    await repo.update(character, {"pic_url": None, "pic_name": None})
    await db.commit()
    await db.refresh(character)
    return character
