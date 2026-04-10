"""
Agent 核心数据模型。

仅包含数据结构定义，不包含业务逻辑。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Agent 配置参数。"""

    agent_name: str = Field(..., description="Agent 名称")
    prompt: str = Field(default="", description="系统提示词")
    model: str = Field(default="gemini-3-flash-preview", description="LLM 模型")
    temperature: Optional[float] = Field(None, ge=0, le=2, description="温度参数")
    max_tokens: Optional[int] = Field(None, gt=0, description="最大 token 数")
    response_schema: Optional[Dict[str, Any]] = Field(None, description="响应 JSON Schema")
    max_loop: int = Field(default=20, ge=1, le=100, description="最大循环次数")
    tools: List[Dict[str, Any]] = Field(default_factory=list, description="工具列表")
    skill_names: List[str] = Field(default_factory=list, description="引用的 Skill 名称列表")
    middleware: List[str] = Field(default_factory=list, description="中间件名称列表")


class AgentMessage(BaseModel):
    """Agent 内部消息结构。"""

    role: str = Field(..., description="user | assistant | system | tool")
    content: str = Field(default="", description="消息内容")
    agent_name: Optional[str] = Field(None, description="所属 Agent 名称")
    tool_call_id: Optional[str] = Field(None, description="工具调用 ID")
    tool_name: Optional[str] = Field(None, description="调用的工具名称")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")


class ToolCall(BaseModel):
    """工具调用结构。"""

    id: str = Field(default_factory=lambda: str(uuid4()), description="调用 ID")
    name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="调用参数")


class AgentResult(BaseModel):
    """
    Agent 执行结果。

    包含 agent_id、request_id、schema_data 等返回数据。
    """

    agent_id: str = Field(default_factory=lambda: str(uuid4()), description="Agent 实例 ID")
    agent_name: str = Field(..., description="Agent 名称")
    request_id: str = Field(default_factory=lambda: str(uuid4()), description="本次请求 ID")
    loop_count: int = Field(default=0, description="本次执行的循环次数")
    messages: List[AgentMessage] = Field(default_factory=list, description="完整消息历史")
    schema_data: Optional[Dict[str, Any]] = Field(None, description="结构化 Schema 数据")
    raw_output: Optional[str] = Field(None, description="原始文本输出")
    error: Optional[str] = Field(None, description="错误信息")
    finished: bool = Field(default=False, description="是否正常结束")
    finished_at: Optional[datetime] = Field(None, description="结束时间")


class ToolResult(BaseModel):
    """工具执行结果。"""

    tool_call_id: str = Field(..., description="调用 ID")
    tool_name: str = Field(..., description="工具名称")
    result: Any = Field(..., description="执行结果")
    is_error: bool = Field(default=False, description="是否错误")
