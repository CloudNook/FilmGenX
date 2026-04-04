"""
生成任务（GenerationTask）的请求/响应 Schema。
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


class TaskResponse(BaseResponse):
    """AI 生成任务响应（只读，任务由系统自动创建）。"""
    shot_id: Optional[int]
    celery_task_id: Optional[str]
    task_type: str
    status: str
    progress: int
    input_params: Optional[dict]
    result_asset_id: Optional[int]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    retry_count: int
    max_retries: int


class VideoGenerationRequest(BaseModel):
    """触发视频生成任务的请求体。"""
    shot_id: int = Field(..., description="要生成视频的镜头ID")
    quality: str = Field("1080p", pattern="^(720p|1080p)$", description="分辨率")
    sound: str = Field("on", pattern="^(on|off)$", description="是否生成音效")
    use_image_start: bool = Field(False, description="是否将当前镜头首帧图作为视频起始帧")
    callback_url: Optional[str] = Field(None, description="任务完成后的回调地址（可选）")


class StoryboardGenerationRequest(BaseModel):
    """触发分镜脚本 AI 生成的请求体。"""
    scene_id: int = Field(..., description="要生成分镜脚本的高光片段ID")
    shot_count: int = Field(6, ge=1, le=6, description="目标镜头数量（1-6）")
    style_notes: Optional[str] = Field(None, description="风格备注，如 '强调动作感，大量特写'")
