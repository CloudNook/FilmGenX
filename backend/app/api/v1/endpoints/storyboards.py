"""
分镜脚本（Storyboard）API 端点。

路由前缀：/api/v1/scenes/{scene_id}/storyboard
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from app.api.deps import get_current_user_id, get_db
from app.repositories.scene import SceneRepository
from app.repositories.storyboard import StoryboardRepository
from app.schemas.storyboard import StoryboardCreate, StoryboardResponse, StoryboardUpdate

router = APIRouter()


class VisualPromptsResponse(BaseModel):
    """图生图视觉提示词响应。"""
    character_image_prompts: list[dict[str, Any]] = []
    scene_image_prompts: list[dict[str, Any]] = []
    shot_group_frame_plans: list[dict[str, Any]] = []
    visual_style_guide: dict[str, Any] = {}


async def _require_scene(scene_id: int, user_id: int, db: AsyncSession):
    """校验片段存在（通过 project 的 owner 校验用户权限）。

    暂时只校验片段存在，权限校验待引入 JWT 后补全。
    """
    scene = await SceneRepository(db).get(scene_id)
    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="片段不存在")
    return scene


@router.get("", response_model=StoryboardResponse, summary="获取分镜脚本")
async def get_storyboard(
    scene_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """获取片段对应的分镜脚本（含镜头列表）。"""
    await _require_scene(scene_id, user_id, db)
    sb = await StoryboardRepository(db).get_by_scene(scene_id)
    if not sb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分镜脚本不存在")
    return sb


@router.post("", response_model=StoryboardResponse, status_code=status.HTTP_201_CREATED, summary="创建分镜脚本")
async def create_storyboard(
    scene_id: int,
    body: StoryboardCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """为片段创建分镜脚本（每个片段只能有一份）。"""
    await _require_scene(scene_id, user_id, db)
    repo = StoryboardRepository(db)

    if await repo.get_by_scene(scene_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该片段已存在分镜脚本")

    data = body.model_dump(exclude_none=True)
    # 嵌套对象序列化为 dict
    if "emotion_curve" in data and data["emotion_curve"]:
        data["emotion_curve"] = [p.model_dump() if hasattr(p, "model_dump") else p for p in data["emotion_curve"]]
    if "pacing_ratio" in data and data["pacing_ratio"]:
        data["pacing_ratio"] = data["pacing_ratio"].model_dump() if hasattr(data["pacing_ratio"], "model_dump") else data["pacing_ratio"]

    sb = await repo.create(scene_id=scene_id, **data)
    await db.commit()
    return sb


@router.patch("", response_model=StoryboardResponse, summary="更新分镜脚本")
async def update_storyboard(
    scene_id: int,
    body: StoryboardUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_scene(scene_id, user_id, db)
    repo = StoryboardRepository(db)
    sb = await repo.get_by_scene(scene_id)
    if not sb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分镜脚本不存在")

    data = body.model_dump(exclude_none=True)
    if "emotion_curve" in data and data["emotion_curve"]:
        data["emotion_curve"] = [p.model_dump() if hasattr(p, "model_dump") else p for p in data["emotion_curve"]]
    if "pacing_ratio" in data and data["pacing_ratio"]:
        data["pacing_ratio"] = data["pacing_ratio"].model_dump() if hasattr(data["pacing_ratio"], "model_dump") else data["pacing_ratio"]

    sb = await repo.update(sb, data)
    await db.commit()
    return sb


@router.get("/visual-prompts", response_model=VisualPromptsResponse, summary="获取图生图视觉提示词")
async def get_visual_prompts(
    scene_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """获取分镜脚本的四层视觉提示词（角色图、场景图、分镜组首帧图、全局风格）。

    从 Storyboard.plan_data 中提取，供前端在角色/场景/分镜组页面
    人工选择基础图后触发图生图。
    """
    await _require_scene(scene_id, user_id, db)
    sb = await StoryboardRepository(db).get_by_scene(scene_id)
    if not sb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分镜脚本不存在")

    plan_data = sb.plan_data or {}
    return VisualPromptsResponse(
        character_image_prompts=plan_data.get("character_image_prompts", []),
        scene_image_prompts=plan_data.get("scene_image_prompts", []),
        shot_group_frame_plans=plan_data.get("shot_group_frame_plans", []),
        visual_style_guide=plan_data.get("visual_style_guide", {}),
    )
