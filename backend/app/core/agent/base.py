"""
Agent 核心数据模型。

仅包含数据结构定义，不包含业务逻辑。
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ----------------------------------------------------------------------
# LLM 响应结构（替代纯文本返回，支持原生 function calling）
# ----------------------------------------------------------------------


class StructuredToolCall(BaseModel):
    """
    结构化工具调用。

    各 Provider API 原生返回的结构化 tool_call 统一为本格式，
    消除文本解析的脆弱性。
    """

    id: str = Field(default_factory=lambda: str(uuid4()), description="调用 ID（Provider 原生或自动生成）")
    name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="调用参数（已解析为 dict）")
    # Provider 原生字段透传（如 OpenAI 的 index、Claude 的 id）
    raw: Optional[Dict[str, Any]] = Field(default=None, description="Provider 原生原始数据")


class LLMResponse(BaseModel):
    """
    LLM 结构化响应。

    替代原来 generate() 返回纯文本的设计，
    包含文本内容和结构化工具调用（原生 API 返回）。
    """

    content: str = Field(default="", description="文本内容")
    tool_calls: List[StructuredToolCall] = Field(default_factory=list, description="结构化工具调用列表")
    finish_reason: Optional[str] = Field(None, description="停止原因（stop / tool_calls 等）")
    usage: Optional[Dict[str, Any]] = Field(None, description="Token 用量")
    raw: Optional[Dict[str, Any]] = Field(default=None, description="Provider 原生响应数据")


# ----------------------------------------------------------------------
# 消息格式（统一格式，各 Provider 适配器负责转换）
# ----------------------------------------------------------------------


class UnifiedToolMessage(BaseModel):
    """
    统一的 tool 角色消息。

    用于将工具结果加入消息历史时构建的标准格式。
    各 Provider 适配器在 build_request 时转换为 Provider 原生格式。

    OpenAI 格式: {"role": "tool", "tool_call_id": "...", "content": "..."}
    Gemini 格式: {"role": "user", "parts": [{"functionResponse": {...}}]
    """

    role: Literal["tool"] = "tool"
    tool_call_id: str = Field(..., description="工具调用 ID（必须与请求中的 tool_call.id 对应）")
    tool_name: str = Field(..., description="工具名称")
    content: str = Field(default="", description="工具执行结果（序列化后的字符串）")

    def to_provider_format(self, provider: str) -> Dict[str, Any]:
        """转换为 Provider 原生消息格式。"""
        if provider == "openai":
            return {
                "role": "tool",
                "tool_call_id": self.tool_call_id,
                "content": self.content,
            }
        elif provider == "gemini":
            return {
                "role": "user",
                "parts": [{
                    "functionResponse": {
                        "name": self.tool_name,
                        "response": {"result": self.content},
                    }
                }],
            }
        else:
            # 默认 OpenAI 兼容格式
            return {
                "role": "tool",
                "tool_call_id": self.tool_call_id,
                "content": self.content,
            }


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
