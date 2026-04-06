"""
API v1 总路由。

将各业务模块的子路由聚合到 /api/v1 前缀下。
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, projects, scenes, storyboards, shots, shot_groups, characters, character_images,
    assets, tasks, conversations, locations, dashboard
)

api_router = APIRouter()

api_router.include_router(auth.router,            prefix="/auth",                                        tags=["认证"])
api_router.include_router(projects.router,       prefix="/projects",                                    tags=["项目"])
api_router.include_router(conversations.router,  prefix="/projects/{project_id}/conversations",         tags=["对话会话"])
api_router.include_router(dashboard.router,      prefix="/projects/{project_id}/dashboard",             tags=["总览"])
api_router.include_router(scenes.router,         prefix="/projects/{project_id}/scenes",                tags=["高光片段"])
api_router.include_router(storyboards.router,    prefix="/scenes/{scene_id}/storyboard",                tags=["分镜脚本"])
api_router.include_router(shots.router,          prefix="/storyboards/{storyboard_id}/shots",           tags=["镜头"])
api_router.include_router(shot_groups.router,    prefix="/storyboards/{storyboard_id}/groups",          tags=["分镜组"])
api_router.include_router(characters.router,     prefix="/projects/{project_id}/characters",            tags=["角色"])
api_router.include_router(
    character_images.router,
    prefix="/projects/{project_id}/characters/{character_id}/versions/{version_id}/images",
    tags=["角色图片"]
)
api_router.include_router(locations.router,      prefix="/projects/{project_id}/locations",             tags=["场景"])
api_router.include_router(assets.router,         prefix="/projects/{project_id}/assets",                tags=["素材"])
api_router.include_router(tasks.router,          prefix="/tasks",                                       tags=["生成任务"])
