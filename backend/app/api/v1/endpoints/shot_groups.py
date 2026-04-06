"""
分镜组（ShotGroup）API 端点。

路由前缀：/api/v1/storyboards/{storyboard_id}/groups
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.repositories.scene import SceneRepository
from app.repositories.shot_group import ShotGroupRepository
from app.repositories.shot import ShotRepository
from app.repositories.storyboard import StoryboardRepository
from app.repositories.task import TaskRepository
from app.schemas.shot_group import ShotGroupCreate, ShotGroupResponse, ShotGroupUpdate
from app.schemas.task import TaskResponse

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
        "prev_shot_group_id": getattr(group, 'prev_shot_group_id', None),
        "end_frame_description": getattr(group, 'end_frame_description', None),
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


class FrameGenerationRequest(BaseModel):
    """分镜组首帧图生成请求体。

    用户在分镜组页面选择基础图（角色图/场景图），结合 Phase 1 输出的
    image_prompt_for_generation 生成首帧参考图，写入 ShotGroup.image_start_url。
    """
    prompt: Optional[str] = Field(
        None,
        description="图生图提示词（可覆盖 plan_data 中的默认值）",
    )
    negative_prompt: Optional[str] = Field(
        None,
        max_length=1000,
        description="负向提示词",
    )
    aspect_ratio: str = Field(
        "16:9",
        pattern="^(1:1|16:9|9:16|4:3|3:4)$",
        description="画幅比例",
    )
    resolution: str = Field(
        "1K",
        pattern="^(512|1K|2K|4K)$",
        description="分辨率：512 / 1K / 2K / 4K",
    )
    style_preset: Optional[str] = Field(None, max_length=100, description="风格预设")
    reference_image_urls: Optional[List[str]] = Field(
        None,
        max_length=5,
        description="基础参考图 URL 列表（来自角色库/场景库），最多 5 张",
    )


class FramePlanResponse(BaseModel):
    """单个分镜组首帧图方案。"""
    group_code: str
    image_prompt: str
    negative_prompt: Optional[str] = None
    style_preset: str = "intense"
    generation_priority: int = 1
    frame_description: Optional[str] = None
    key_elements: list[str] = []
    camera_notes: Optional[str] = None
    lighting_notes: Optional[str] = None


@router.get(
    "/{group_id}/frame-plan",
    response_model=Optional[FramePlanResponse],
    summary="获取分镜组首帧图方案",
)
async def get_group_frame_plan(
    storyboard_id: int,
    group_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """从 Storyboard.plan_data 中获取指定分镜组的首帧图生成方案。

    返回 image_prompt_for_generation（英文图生图提示词）及其他元数据，
    供前端在生成页面展示和用户选择基础图后触发图生图。
    """
    storyboard = await _require_storyboard(storyboard_id, db)
    group_repo = ShotGroupRepository(db)

    group = await group_repo.get_by_id_and_storyboard(group_id, storyboard_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分镜组不存在")

    plan_data = storyboard.plan_data or {}
    frame_plans = plan_data.get("shot_group_frame_plans", [])
    frame_plan = next((fp for fp in frame_plans if fp.get("group_code") == group.group_code), None)

    if not frame_plan:
        return None

    # 提取 frame_plan.frame_plan 子对象的字段
    inner = frame_plan.get("frame_plan") or {}
    return FramePlanResponse(
        group_code=frame_plan.get("group_code", group.group_code),
        image_prompt=frame_plan.get("image_prompt_for_generation", ""),
        negative_prompt=frame_plan.get("negative_prompt"),
        style_preset=frame_plan.get("style_preset", "intense"),
        generation_priority=frame_plan.get("generation_priority", 1),
        frame_description=inner.get("image_start_description"),
        key_elements=inner.get("key_elements", []),
        camera_notes=inner.get("camera_for_frame"),
        lighting_notes=inner.get("lighting_for_frame"),
    )


@router.post("/{group_id}/generate-frame", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED, summary="生成分镜组首帧参考图")
async def generate_group_frame(
    storyboard_id: int,
    group_id: int,
    body: FrameGenerationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """生成分镜组首帧参考图。

    流程：
    1. 根据 group_id 找到分镜组，从 Storyboard.plan_data 中取对应的 frame_plan
    2. 用用户选择的 base reference images + frame_plan 的 prompt 生成图片
    3. 图片 URL 写入 ShotGroup.image_start_url
    4. 图片资产写入第一个分镜的素材库
    """
    storyboard = await _require_storyboard(storyboard_id, db)
    group_repo = ShotGroupRepository(db)

    group = await group_repo.get_by_id_and_storyboard(group_id, storyboard_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分镜组不存在")

    # 从 plan_data 取出 frame_plan
    plan_data = storyboard.plan_data or {}
    frame_plans = plan_data.get("shot_group_frame_plans", [])
    frame_plan = next((fp for fp in frame_plans if fp.get("group_code") == group.group_code), None)

    if not frame_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"分镜组 {group.group_code} 在 plan_data 中无首帧图方案",
        )

    # 取 prompt（用户可覆盖）
    prompt = body.prompt or frame_plan.get("image_prompt_for_generation", "")
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无可用图生图提示词，请传入 prompt 参数",
        )

    # 取组内第一个分镜（用于保存素材）
    shot_repo = ShotRepository(db)
    group_shots = await shot_repo.get_by_shot_group(group.id)
    first_shot = min(group_shots, key=lambda s: s.sequence) if group_shots else None

    # 从 scene 获取 project_id
    scene = await SceneRepository(db).get(storyboard.scene_id)
    project_id = scene.project_id if scene else None

    task_repo = TaskRepository(db)

    input_params = {
        "project_id": project_id,
        "shot_id": first_shot.id if first_shot else None,
        "prompt": prompt,
        "negative_prompt": body.negative_prompt or frame_plan.get("negative_prompt"),
        "style_preset": body.style_preset or frame_plan.get("style_preset", "intense"),
        "aspect_ratio": body.aspect_ratio,
        "resolution": body.resolution,
        "reference_image_urls": body.reference_image_urls or [],
        "save_to_shot": True,
        "shot_group_id": group.id,
    }

    gen_task = await task_repo.create(
        task_type="image_generation",
        input_params=input_params,
    )
    await db.commit()
    await db.refresh(gen_task)

    # 异步提交（不等待结果）
    from app.tasks.image import generate_image_task  # noqa: PLC0415 — Celery task import deferred to avoid circular import
    celery_result = generate_image_task.delay(gen_task.id)
    await task_repo.update(gen_task, {"celery_task_id": celery_result.id})
    await db.commit()

    return gen_task
