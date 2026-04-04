"""
对话会话（Conversation）和消息（Message）的请求/响应 Schema。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


# ---------------------------------------------------------------------------
# 剧本大纲（EpisodeOutline）
# ---------------------------------------------------------------------------

class ScoreDetail(BaseModel):
    dramatic_tension: int = Field(..., ge=0, le=10)
    visual_potential: int = Field(..., ge=0, le=10)
    emotional_resonance: int = Field(..., ge=0, le=10)
    narrative_importance: int = Field(..., ge=0, le=10)
    audience_familiarity: int = Field(..., ge=0, le=10)


class EpisodeOutline(BaseModel):
    """剧本大纲结构。由 AI 生成，可被用户编辑后确认。"""
    title: str = Field(..., description="本集标题")
    episode_code: Optional[str] = Field(None, description="分集编号，由后端 confirm 时自动生成，LLM 无需填写")
    synopsis: str = Field(..., description="本集剧情概述，100-300字")
    theme: str = Field(..., description="核心主题，一句话")
    novel_chapter_start: str = Field(..., description="起始章节")
    novel_chapter_end: str = Field(..., description="结束章节")
    novel_excerpt: str = Field(..., description="关键原著摘录，用于分镜参考")
    scene_types: List[str] = Field(default_factory=list)
    priority: str = Field("A", pattern="^[SABC]$")
    estimated_duration_sec: int = Field(..., gt=0)
    scores: ScoreDetail
    characters: List[str] = Field(default_factory=list, description="角色名列表")
    storyboard_style_notes: str = Field("", description="给分镜AI的风格指导")
    storyboard_shot_count: int = Field(8, ge=1, le=20, description="建议镜头数量")
    version: int = Field(1, ge=1, description="第几次总结，从1开始")
    generated_at: Optional[str] = None


# ---------------------------------------------------------------------------
# LLM 动态配置
# ---------------------------------------------------------------------------

class LLMConfigPayload(BaseModel):
    """随请求传入的 LLM 配置（API Key 由后端环境变量管理，前端只需传 model/temperature）。"""
    model: str = Field(..., description="模型名称，如 gemini-3-flash-preview")
    base_url: Optional[str] = Field(None, description="自定义端点（custom provider 时必填）")
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, gt=0)


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

class MessageCreate(BaseModel):
    """创建单条消息的请求体（前端每条消息发送后立即调用）。"""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    type: str = Field(
        "text",
        pattern="^(text|outline_draft|outline_confirmed|system_action)$",
        description="消息类型，影响渲染和 AI 上下文理解",
    )
    content: str = Field(..., description="消息正文（Markdown）")
    outline_data: Optional[EpisodeOutline] = Field(
        None, description="仅 outline_* 类型时携带"
    )


class MessageResponse(BaseResponse):
    """单条消息响应。"""
    conversation_id: int
    role: str
    type: str
    content: str
    outline_data: Optional[Dict[str, Any]]
    seq: int


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------

class ConversationCreate(BaseModel):
    """新建会话请求体。"""
    title: str = Field("新对话", max_length=200)


class ConversationUpdate(BaseModel):
    """更新会话请求体（标题、状态、最新大纲）。"""
    title: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = Field(
        None,
        pattern="^(active|draft_ready)$",
        description="只允许更新到 active/draft_ready；confirmed 由 /confirm 接口触发",
    )
    latest_outline: Optional[EpisodeOutline] = Field(
        None, description="用户编辑后的最新大纲（同步覆盖，不创建新消息）"
    )


class ConversationResponse(BaseResponse):
    """会话列表项响应（不含消息列表）。"""
    project_id: int
    title: str
    status: str
    latest_outline: Optional[Dict[str, Any]]
    scene_id: Optional[int]


class ConversationDetailResponse(ConversationResponse):
    """会话详情响应（含完整消息列表）。"""
    messages: List[MessageResponse]


# ---------------------------------------------------------------------------
# 确认执行（Confirm）
# ---------------------------------------------------------------------------

class ConversationConfirmRequest(BaseModel):
    """确认剧本大纲，创建 Scene 并触发分镜生成。"""
    outline: EpisodeOutline = Field(..., description="最终确认的剧本大纲（可能经用户编辑）")
    llm_config: LLMConfigPayload = Field(..., description="用于分镜生成的 LLM 配置")
    system_prompt: str = Field("", description="分镜生成系统提示词（用户可修改）")
    shot_count: Optional[int] = Field(None, ge=1, le=20, description="覆盖大纲中的镜头数量")


class ConversationConfirmResponse(BaseModel):
    """确认执行响应。"""
    scene_id: int
    task_id: int
    celery_task_id: str
