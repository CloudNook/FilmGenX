"""
Skill Admin API 端点（Claude SKILL.md 风格）。

路由前缀：/api/v1/admin/skills
权限：仅 is_superuser 可访问

L1（meta）/ L2（body）/ L3（reference）三层暴露：
- ``GET /admin/skills/meta?target_agent=outline_agent`` 仅元信息（启动注入用）
- ``GET /admin/skills/{name}`` 完整字段（admin 编辑视图）
- ``GET /admin/skills/{name}/reference/{ref_key}`` 单个 reference
- ``GET /admin/skills/{name}/lint`` 引用 lint 检查
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.user import User
from app.schemas.base import PageResponse
from app.schemas.skill import (
    LintIssueResponse,
    SkillCreate,
    SkillLintResponse,
    SkillMarkdownBody,
    SkillMetaResponse,
    SkillParseResult,
    SkillResponse,
    SkillUpdate,
    SkillUploadResponse,
)
from app.services.skill_parser import parse_skill_markdown
from app.services.skill_service import SkillService

router = APIRouter()


# ===========================================================================
# 上传 / 预览
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
    service = SkillService(db)
    parse_result, existing, is_update = await service.upload_and_parse(body.content)
    return SkillUploadResponse(
        skill=SkillParseResult(**parse_result.to_dict()),
        existing=SkillResponse.model_validate(existing) if existing else None,
        is_update=is_update,
    )


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
    """仅解析 Markdown，不保存，不查 DB。"""
    result = parse_skill_markdown(body.content)
    return SkillParseResult(**result.to_dict())


# ===========================================================================
# 列表（admin 全字段）
# ===========================================================================


@router.get(
    "",
    response_model=PageResponse[SkillResponse],
    summary="获取 Skill 列表（分页）",
)
async def list_skills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = Query(None, description="按启用状态过滤"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    service = SkillService(db)
    items, total = await service.list_skills(
        page=page,
        page_size=page_size,
        is_active=is_active,
    )
    return PageResponse(items=items, total=total, page=page, page_size=page_size)


# ===========================================================================
# 元信息列表（L1）
# ===========================================================================


@router.get(
    "/meta",
    response_model=List[SkillMetaResponse],
    summary="获取 Skill 元信息列表（L1）",
)
async def list_skill_meta(
    target_agent: Optional[str] = Query(
        None,
        description="按 target_agents 反查；不传则返回所有 active skill 的 meta",
    ),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """返回 active skill 的元信息（不含 body / references）。

    - 给前端 admin picker 用：``target_agent=None`` 列全集
    - 给 agent 启动注入用：``target_agent=outline_agent`` 反查
    """
    service = SkillService(db)
    rows = await service.list_active_meta(target_agent=target_agent)
    return [SkillMetaResponse(**row) for row in rows]


# ===========================================================================
# 详情（admin 全字段）/ Reference / Lint / Markdown 下载
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
    service = SkillService(db)
    skill = await service.get_skill(name)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' 不存在",
        )
    return skill


@router.get(
    "/{name}/reference/{ref_key}",
    summary="获取单个 reference 子文档（L3）",
)
async def get_skill_reference(
    name: str,
    ref_key: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    service = SkillService(db)
    payload = await service.get_reference(name, ref_key)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' 或 reference '{ref_key}' 不存在",
        )
    return payload


@router.get(
    "/{name}/lint",
    response_model=SkillLintResponse,
    summary="对 Skill 跑引用 lint",
)
async def lint_skill_endpoint(
    name: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    service = SkillService(db)
    issues = await service.lint(name)
    if issues is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' 不存在",
        )
    return SkillLintResponse(
        skill_name=name,
        issues=[
            LintIssueResponse(
                level=issue.level,
                code=issue.code,
                message=issue.message,
                field=issue.field,
                token=issue.token,
            )
            for issue in issues
        ],
    )


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


# ===========================================================================
# 创建 / 更新 / 删除
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
    service = SkillService(db)
    if await service.get_skill(body.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Skill '{body.name}' 已存在，请使用 PUT 更新",
        )
    return await service.save_skill(create_data=body, raw_markdown=body.raw_markdown)


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
    service = SkillService(db)
    skill = await service.update_skill(
        name=name,
        update_data=body,
        raw_markdown=body.raw_markdown,
    )
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' 不存在",
        )
    return skill


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
    service = SkillService(db)
    if not await service.delete_skill(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{name}' 不存在",
        )
