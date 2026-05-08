"""
API v1 总路由。

将各业务模块的子路由聚合到 /api/v1 前缀下。

仅保留 agent-driven 链路：auth / projects / workspaces / assets / supervisor /
admin skills / agent-schemas。老的工作流 endpoints（characters / locations /
scenes / storyboards / shots / shot_groups / character_images / location_images
/ tasks / conversations / dashboard）已经在 2026-05-07 重构中删除。
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    agent_schemas,
    assets,
    auth,
    projects,
    skills,
    supervisor,
    workspaces,
)

api_router = APIRouter()

api_router.include_router(auth.router,        prefix="/auth",                                tags=["认证"])
api_router.include_router(projects.router,    prefix="/projects",                            tags=["项目"])
api_router.include_router(workspaces.router,  prefix="/projects/{project_id}/workspaces",   tags=["AI 工作台"])
api_router.include_router(assets.router,      prefix="/projects/{project_id}/assets",        tags=["素材"])

# Admin 路由
api_router.include_router(skills.router, prefix="/admin/skills", tags=["Admin - Skill 管理"])

# Supervisor 路由
api_router.include_router(supervisor.router, prefix="/supervisor", tags=["Supervisor 流水线"])

# Agent 输出 schema（前端渲染器用 title / description 做字段标签和 hover 说明）
api_router.include_router(agent_schemas.router, prefix="/agent-schemas", tags=["Agent Schemas"])
