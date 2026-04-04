"""
单镜头（Shot）API 端点。

路由前缀：/api/v1/storyboards/{storyboard_id}/shots
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.repositories.shot import ShotRepository
from app.repositories.storyboard import StoryboardRepository
from app.schemas.shot import ShotCreate, ShotResponse, ShotUpdate

router = APIRouter()


async def _require_storyboard(storyboard_id: int, db: AsyncSession):
    """校验分镜脚本存在。"""
    sb = await StoryboardRepository(db).get(storyboard_id)
    if not sb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分镜脚本不存在")
    return sb


@router.get("", response_model=List[ShotResponse], summary="获取镜头列表")
async def list_shots(
    storyboard_id: int,
    shot_status: Optional[str] = Query(None, alias="status", description="按状态过滤"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """获取分镜脚本下所有镜头（按 sequence 排序，不分页）。"""
    await _require_storyboard(storyboard_id, db)
    shots = await ShotRepository(db).get_by_storyboard(storyboard_id, status=shot_status)
    return shots


@router.post("", response_model=ShotResponse, status_code=status.HTTP_201_CREATED, summary="创建镜头")
async def create_shot(
    storyboard_id: int,
    body: ShotCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_storyboard(storyboard_id, db)
    repo = ShotRepository(db)

    if await repo.get_by_code(body.shot_code):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"shot_code '{body.shot_code}' 已存在")

    data = body.model_dump(exclude_none=True)
    # 将嵌套 Pydantic 对象序列化为 dict，SQLAlchemy JSON 列需要原生 dict
    for field in ("camera", "composition"):
        if field in data and hasattr(data[field], "model_dump"):
            data[field] = data[field].model_dump(exclude_none=True)

    shot = await repo.create(storyboard_id=storyboard_id, **data)
    await db.commit()
    return shot


@router.get("/{shot_id}", response_model=ShotResponse, summary="获取镜头详情")
async def get_shot(
    storyboard_id: int,
    shot_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_storyboard(storyboard_id, db)
    shot = await ShotRepository(db).get_by_id_and_storyboard(shot_id, storyboard_id)
    if not shot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="镜头不存在")
    return shot


@router.patch("/{shot_id}", response_model=ShotResponse, summary="更新镜头")
async def update_shot(
    storyboard_id: int,
    shot_id: int,
    body: ShotUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_storyboard(storyboard_id, db)
    repo = ShotRepository(db)
    shot = await repo.get_by_id_and_storyboard(shot_id, storyboard_id)
    if not shot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="镜头不存在")

    data = body.model_dump(exclude_none=True)
    for field in ("camera", "composition"):
        if field in data and hasattr(data[field], "model_dump"):
            data[field] = data[field].model_dump(exclude_none=True)

    shot = await repo.update(shot, data)
    await db.commit()
    return shot


@router.delete("/{shot_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除镜头")
async def delete_shot(
    storyboard_id: int,
    shot_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_storyboard(storyboard_id, db)
    repo = ShotRepository(db)
    shot = await repo.get_by_id_and_storyboard(shot_id, storyboard_id)
    if not shot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="镜头不存在")
    await repo.soft_delete(shot)
    await db.commit()
