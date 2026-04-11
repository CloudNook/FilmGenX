"""
AI 工作台（Workspace）请求/响应 Schema。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


# ---------------------------------------------------------------------------
# Workspace CRUD
# ---------------------------------------------------------------------------

class WorkspaceCreate(BaseModel):
    """新建工作台请求体。"""

    title: str = Field("新工作台", max_length=200)
    system_prompt: Optional[str] = Field(None, description="自定义 system prompt")


class WorkspaceUpdate(BaseModel):
    """更新工作台请求体。"""

    title: Optional[str] = Field(None, max_length=200)
    system_prompt: Optional[str] = Field(None, description="自定义 system prompt")
    status: Optional[str] = Field(None, pattern="^(active|archived)$")


class WorkspaceResponse(BaseResponse):
    """工作台列表项响应。"""

    project_id: int
    title: str
    agent_name: str
    session_id: str
    system_prompt: Optional[str]
    status: str
    total_tokens: int
    last_message_at: Optional[datetime]


# ---------------------------------------------------------------------------
# Agent Message（历史消息，从 agent_messages 表读取）
# ---------------------------------------------------------------------------

class AgentMessageResponse(BaseModel):
    """Agent 历史消息响应。"""

    role: str
    content: str
    seq: int
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    thinking: Optional[str] = Field(None, description="思考过程，从 metadata 中提取")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        None, description="工具调用列表，从 metadata 中提取"
    )
    usage: Optional[Dict[str, Any]] = Field(None, description="本条消息的 token 用量（assistant 消息）")
    accumulated_usage: Optional[Dict[str, Any]] = Field(None, description="截至本条消息的会话累积 token 用量")
    created_at: Optional[datetime] = None


class WorkspaceDetailResponse(WorkspaceResponse):
    """工作台详情响应（含历史消息）。"""

    messages: List[AgentMessageResponse]


# ---------------------------------------------------------------------------
# Chat 请求
# ---------------------------------------------------------------------------

class WorkspaceChatRequest(BaseModel):
    """发送工作台聊天消息请求。"""

    content: str = Field(..., description="用户消息内容")
    model: Optional[str] = Field(None, description="LLM 模型，默认使用系统配置")
    temperature: Optional[float] = Field(None, ge=0, le=2)
