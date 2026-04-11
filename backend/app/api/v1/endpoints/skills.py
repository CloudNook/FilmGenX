"""
Skill Admin API 端点。

路由前缀：/api/v1/admin/skills
权限：仅 is_superuser 可访问
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.services.skill_parser import parse_skill_markdown
from app.services.skill_service import SkillService
from app.models.user import User
from app.schemas.base import PageResponse
from app.schemas.skill import (
    SkillCreate,
    SkillParseResult,
    SkillResponse,
    SkillUpdate,
    SkillUploadResponse,
    SkillMarkdownBody,
)

router = APIRouter()


# ===========================================================================
# 上传解析
# ===========================================================================

@router.post(
    "/upload",
    response_model=SkillUploadResponse,
    summary="上传 SKILL.md 并解析",
    status_code=status.HTTP_200_OK,
)
async def upload_skill_markdown(
    body: SkillMarkdownBody,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    上传 Markdown 文件内容 → 解析 → 返回结构化结果。

    如果同名 Skill 已存在于 DB，返回现有数据供前端对比。
    """
    service = SkillService(db)
    parse_result, existing, is_update = await service.upload_and_parse(body.content)

    return SkillUploadResponse(
        skill=SkillParseResult(**parse_result.to_dict()),
        existing=SkillResponse.model_validate(existing) if existing else None,
        is_update=is_update,
    )


# ===========================================================================
# 预览解析（不保存，仅解析）
# ===========================================================================

@router.post(
    "/preview",
    response_model=SkillParseResult,
    summary="预览 Markdown 解析结果",
    status_code=status.HTTP_200_OK,
)
async def preview_skill_markdown(
    body: SkillMarkdownBody,
    admin: User = Depends(get_current_admin),
):
    """
    仅解析 Markdown，不保存，不查 DB。
    用于 Admin 在编辑器中实时预览解析结果。
    """
    result = parse_skill_markdown(body.content)
    return SkillParseResult(**result.to_dict())


# ===========================================================================
# 列表
# ===========================================================================

@router.get(
    "",
    response_model=PageResponse[SkillResponse],
    summary="获取 Skill 列表（分页）",
)
async def list_skills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, description="按领域分类过滤"),
    is_active: Optional[bool] = Query(None, description="按启用状态过滤"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """分页获取 Skill 列表，支持按 category / is_active 过滤。"""
    service = SkillService(db)
    items, total = await service.list_skills(
        page=page,
        page_size=page_size,
        category=category,
        is_active=is_active,
    )
    return PageResponse(items=items, total=total, page=page, page_size=page_size)


# ===========================================================================
# 详情
# ===========================================================================

@router.get(
    "/{name}",
    response_model=SkillResponse,
    summary="获取 Skill 详情",
)
async def get_skill(
    name: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """按 name 获取 Skill 完整信息。"""
    service = SkillService(db)
    skill = await service.get_skill(name)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' 不存在",
        )
    return skill


# ===========================================================================
# 创建
# ===========================================================================

@router.post(
    "",
    response_model=SkillResponse,
    summary="创建 Skill",
    status_code=status.HTTP_201_CREATED,
)
async def create_skill(
    body: SkillCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    创建新 Skill。

    - name 唯一约束：重复则报错 409
    - 建议先调用 /upload 接口解析 Markdown，再用返回结果补全后提交
    """
    service = SkillService(db)

    existing = await service.get_skill(body.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Skill '{body.name}' 已存在，请使用 PUT 更新",
        )

    skill = await service.save_skill(
        create_data=body,
        raw_markdown=body.raw_markdown,
    )
    return skill


# ===========================================================================
# 更新
# ===========================================================================

@router.put(
    "/{name}",
    response_model=SkillResponse,
    summary="更新 Skill",
)
async def update_skill(
    name: str,
    body: SkillUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    部分更新 Skill。

    - 只更新传入的非空字段
    - 自动递增 version
    - 如 raw_markdown 传入，则覆盖存储的原文
    """
    service = SkillService(db)
    skill = await service.update_skill(
        name=name,
        update_data=body,
        raw_markdown=body.raw_markdown if body.raw_markdown is not None else None,
    )
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' 不存在",
        )
    return skill


# ===========================================================================
# 删除（软删除）
# ===========================================================================

@router.delete(
    "/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除 Skill（软删除）",
)
async def delete_skill(
    name: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """软删除 Skill，设置 is_deleted=True。"""
    service = SkillService(db)
    deleted = await service.delete_skill(name)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' 不存在",
        )


# ===========================================================================
# 下载原始 Markdown
# ===========================================================================

@router.get(
    "/{name}/markdown",
    response_class=PlainTextResponse,
    summary="下载 Skill 原始 Markdown",
)
async def download_skill_markdown(
    name: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """返回 Skill 存储的 raw_markdown（如果有）。"""
    service = SkillService(db)
    skill = await service.get_skill(name)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' 不存在",
        )
    if not skill.raw_markdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' 无原始 Markdown",
        )
    return skill.raw_markdown
