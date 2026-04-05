"""
分镜组（ShotGroup）API 端点。

路由前缀：/api/v1/storyboards/{storyboard_id}/groups
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.repositories.shot_group import ShotGroupRepository
from app.repositories.shot import ShotRepository
from app.repositories.storyboard import StoryboardRepository
from app.schemas.shot_group import ShotGroupCreate, ShotGroupResponse, ShotGroupUpdate

router = APIRouter()

# Kling multi_shot 约束
MAX_SHOTS_PER_GROUP = 6
MAX_TOTAL_DURATION = 15.0


async def _require_storyboard(storyboard_id: int, db: AsyncSession):
    sb = await StoryboardRepository(db).get(storyboard_id)
    if not sb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分镜脚本不存在")
    return sb


def _validate_group_constraints(shots: list) -> None:
    """校验分镜组约束。"""
    if len(shots) > MAX_SHOTS_PER_GROUP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"每组最多 {MAX_SHOTS_PER_GROUP} 个分镜，当前选择了 {len(shots)} 个",
        )
    total = sum(s.duration_sec or 3.0 for s in shots)
    if total > MAX_TOTAL_DURATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"每组总时长不得超过 {MAX_TOTAL_DURATION}s，当前为 {total:.1f}s",
        )


def _build_group_response(group, member_shots=None):
    """从 ORM 对象构建 ShotGroupResponse，避免 Pydantic 直接访问 lazy-loaded 关系。"""
    shots = member_shots if member_shots is not None else getattr(group, 'shots', [])
    group_data = {
        "id": group.id,
        "storyboard_id": group.storyboard_id,
        "group_code": group.group_code,
        "name": group.name,
        "sequence": group.sequence,
        "total_duration_sec": group.total_duration_sec,
        "video_url": group.video_url,
        "status": group.status,
        "plan_intent": getattr(group, 'plan_intent', None),
        "image_references": getattr(group, 'image_references', []) or [],
        "image_start_url": getattr(group, 'image_start_url', None),
        "created_at": group.created_at,
        "updated_at": group.updated_at,
        "shots": [
            {"id": s.id, "shot_code": s.shot_code, "sequence": s.sequence, "duration_sec": s.duration_sec}
            for s in (shots or [])
        ],
    }
    return ShotGroupResponse.model_validate(group_data)


@router.get("", response_model=List[ShotGroupResponse], summary="获取分镜组列表")
async def list_groups(
    storyboard_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_storyboard(storyboard_id, db)
    groups = await ShotGroupRepository(db).get_by_storyboard(storyboard_id)
    return [_build_group_response(g) for g in groups]


@router.post("", response_model=ShotGroupResponse, status_code=status.HTTP_201_CREATED, summary="创建分镜组")
async def create_group(
    storyboard_id: int,
    body: ShotGroupCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_storyboard(storyboard_id, db)
    shot_repo = ShotRepository(db)
    group_repo = ShotGroupRepository(db)

    # 加载所有指定的分镜
    shots = []
    for sid in body.shot_ids:
        shot = await shot_repo.get_by_id_and_storyboard(sid, storyboard_id)
        if not shot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"分镜 {sid} 不存在")
        shots.append(shot)

    _validate_group_constraints(shots)

    # 计算组的 sequence（现有组数 + 1）
    existing = await group_repo.get_by_storyboard(storyboard_id)
    group_seq = len(existing) + 1

    total_duration = sum(s.duration_sec or 3.0 for s in shots)

    group = await group_repo.create(
        storyboard_id=storyboard_id,
        group_code=body.group_code,
        name=body.name,
        sequence=group_seq,
        total_duration_sec=total_duration,
    )

    # 将分镜绑定到组
    for shot in shots:
        await shot_repo.update(shot, {"shot_group_id": group.id})

    await db.commit()
    await db.refresh(group)

    resp = _build_group_response(group, shots)
    return resp


@router.get("/{group_id}", response_model=ShotGroupResponse, summary="获取分镜组详情")
async def get_group(
    storyboard_id: int,
    group_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_storyboard(storyboard_id, db)
    group_repo = ShotGroupRepository(db)
    group = await group_repo.get_by_id_and_storyboard(group_id, storyboard_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分镜组不存在")

    return _build_group_response(group)


@router.patch("/{group_id}", response_model=ShotGroupResponse, summary="更新分镜组")
async def update_group(
    storyboard_id: int,
    group_id: int,
    body: ShotGroupUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_storyboard(storyboard_id, db)
    group_repo = ShotGroupRepository(db)
    shot_repo = ShotRepository(db)
    group = await group_repo.get_by_id_and_storyboard(group_id, storyboard_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分镜组不存在")

    update_data = body.model_dump(exclude_none=True)

    # 如果更新了成员列表
    new_shot_ids = update_data.pop("shot_ids", None)
    if new_shot_ids is not None:
        # 解绑旧成员
        old_shots = await shot_repo.get_by_storyboard(storyboard_id)
        for s in old_shots:
            if s.shot_group_id == group.id:
                await shot_repo.update(s, {"shot_group_id": None})

        # 绑定新成员
        shots = []
        for sid in new_shot_ids:
            shot = await shot_repo.get_by_id_and_storyboard(sid, storyboard_id)
            if not shot:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"分镜 {sid} 不存在")
            shots.append(shot)

        _validate_group_constraints(shots)
        for shot in shots:
            await shot_repo.update(shot, {"shot_group_id": group.id})

        update_data["total_duration_sec"] = sum(s.duration_sec or 3.0 for s in shots)

    if update_data:
        await group_repo.update(group, update_data)

    await db.commit()
    await db.refresh(group)

    # 重新加载成员
    all_shots = await shot_repo.get_by_storyboard(storyboard_id)
    member_shots = [s for s in all_shots if s.shot_group_id == group.id]
    return _build_group_response(group, member_shots)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除分镜组")
async def delete_group(
    storyboard_id: int,
    group_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_storyboard(storyboard_id, db)
    group_repo = ShotGroupRepository(db)
    shot_repo = ShotRepository(db)
    group = await group_repo.get_by_id_and_storyboard(group_id, storyboard_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分镜组不存在")

    # 解绑所有成员（SET NULL 由 FK 处理，但显式清除更安全）
    all_shots = await shot_repo.get_by_storyboard(storyboard_id)
    for s in all_shots:
        if s.shot_group_id == group.id:
            await shot_repo.update(s, {"shot_group_id": None})

    await group_repo.soft_delete(group)
    await db.commit()
