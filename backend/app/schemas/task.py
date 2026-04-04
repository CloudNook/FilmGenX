"""
生成任务（GenerationTask）的请求/响应 Schema。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

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
    shot_count: int = Field(8, ge=1, le=20, description="目标镜头数量（1-20）")
    style_notes: Optional[str] = Field(None, description="风格备注，如 '强调动作感，大量特写'")


class ImageGenerationRequest(BaseModel):
    """触发图像生成的请求体。"""
    project_id: Optional[int] = Field(None, description="项目ID，用于保存到项目素材库")
    shot_id: Optional[int] = Field(None, description="关联镜头ID，不传则为全局素材")
    prompt: str = Field(..., min_length=1, max_length=2000, description="正向提示词，描述想要生成的画面")
    negative_prompt: Optional[str] = Field(None, max_length=1000, description="负向提示词，描述不想要出现的元素")
    aspect_ratio: str = Field(
        "16:9",
        pattern="^(1:1|1:4|1:8|2:3|3:2|3:4|4:1|4:3|4:5|5:4|8:1|9:16|16:9|21:9)$",
        description="画幅比例",
    )
    resolution: str = Field(
        "1K",
        pattern="^(512|1K|2K|4K)$",
        description="分辨率：512 / 1K / 2K / 4K",
    )
    style_preset: Optional[str] = Field(None, max_length=100, description="风格预设，如 cinematic / anime / realistic")
    reference_image_urls: Optional[List[str]] = Field(
        None,
        max_length=5,
        description="参考图URL列表（最多5个，用于图生图）",
    )
    save_to_shot: bool = Field(True, description="是否保存到素材库")
