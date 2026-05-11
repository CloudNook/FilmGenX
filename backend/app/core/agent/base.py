"""
Agent 核心数据模型。

仅包含数据结构定义，不包含业务逻辑。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Awaitable, Dict, List, Literal, Optional, Protocol, TypeAlias
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentInterrupted(Exception):
    """
    Agent 执行被 middleware 拦截并中断。

    在 AgentLoop.run() 中，当 before_tool_calls 设置 ctx.metadata["interrupt"] 时抛出，
    中断信息从 ctx.metadata["interrupt"] 中读取。
    Agent.run() 捕获此异常并转换为 AgentResult（error="interrupted"）。
    """

    pass


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
    包含文本内容、思考过程和结构化工具调用（原生 API 返回）。
    """

    content: str = Field(default="", description="文本内容（最终回答）")
    thinking: str = Field(default="", description="思考过程（仅 thinking 模型填充，如 Gemini Flash Thinking）")
    tool_calls: List[StructuredToolCall] = Field(default_factory=list, description="结构化工具调用列表")
    finish_reason: Optional[str] = Field(None, description="停止原因（stop / tool_calls 等）")
    usage: Optional[Dict[str, Any]] = Field(None, description="Token 用量")
    raw: Optional[Dict[str, Any]] = Field(default=None, description="Provider 原生响应数据")


class ReviewError(Exception):
    """Raised when reviewer execution or output normalization fails."""


class ReviewResult(BaseModel):
    """Review Agent 对候选输出的结构化评审结果。"""

    score: float = Field(default=0.0, ge=0, le=10, description="0-10 分质量评分")
    passed: bool = Field(default=False, description="是否通过评审")
    feedback: str = Field(default="", description="评审反馈")
    suggestions: List[str] = Field(default_factory=list, description="可执行修改建议")


class ReviewRequest(BaseModel):
    """发送给 reviewer 的候选输出评审请求。"""

    agent_name: str
    session_id: str = ""
    request_id: str = ""
    user_input: str = ""
    candidate_output: str
    loop_count: int = 0
    review_round: int = 1
    criteria: List[str] = Field(default_factory=list)


ReviewOutput: TypeAlias = ReviewResult | dict[str, Any]


class Reviewer(Protocol):
    """Callable contract for custom Agent reviewers."""

    def __call__(
        self,
        request: ReviewRequest,
    ) -> ReviewOutput | Awaitable[ReviewOutput]:
        ...


class AgentConfig(BaseModel):
    """Agent 配置参数。"""

    model_config = {"frozen": False}

    agent_name: str = Field(..., description="Agent 名称")
    prompt: str = Field(default="", description="系统提示词")
    model: str = Field(default="gemini-3-flash-preview", description="LLM 模型")
    temperature: Optional[float] = Field(None, ge=0, le=2, description="温度参数")
    max_tokens: Optional[int] = Field(None, gt=0, description="最大 token 数")
    max_loop: int = Field(default=20, ge=1, le=100, description="最大循环次数")
    tools: List[Dict[str, Any]] = Field(default_factory=list, description="工具列表")
    response_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "可选 JSON Schema，启用 Provider 原生结构化输出（Gemini response_schema / "
            "OpenAI response_format=json_schema）。AgentLoop 会在每次 LLM 调用时透传。"
        ),
    )


class AgentMessage(BaseModel):
    """
    Agent 内部消息结构。

    这份消息历史主要用于：
    - 下一轮 LLM 调用时恢复上下文
    - 调试 Agent 内部 think/act/observe 过程
    - 持久化会话记录
    """

    role: str = Field(..., description="user | assistant | system | tool")
    content: str = Field(default="", description="消息内容；assistant/tool/user 的原始文本")
    thinking: str = Field(default="", description="思考过程，仅 assistant 消息使用，不一定会展示给最终用户")
    agent_name: Optional[str] = Field(None, description="所属 Agent 名称")
    tool_call_id: Optional[str] = Field(None, description="工具调用 ID")
    tool_name: Optional[str] = Field(None, description="调用的工具名称")
    seq: int = Field(default=0, description="消息序号（用于跨请求排序）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据，用于调试、持久化和中间件扩展")


class ToolCall(BaseModel):
    """工具调用结构。"""

    id: str = Field(default_factory=lambda: str(uuid4()), description="调用 ID")
    name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="调用参数")


class AgentResult(BaseModel):
    """
    Agent 执行结果。

    这是业务侧最终消费的结果对象。

    设计上：
    - `messages` 更偏向调试/追踪 Agent 内部过程
    - `raw_output` 是最终自然语言结论
    - `schema_data` 是给业务代码直接使用的结构化结果
    """

    agent_id: str = Field(default_factory=lambda: str(uuid4()), description="Agent 实例 ID")
    agent_name: str = Field(..., description="Agent 名称")
    request_id: str = Field(default_factory=lambda: str(uuid4()), description="本次请求 ID")
    loop_count: int = Field(default=0, description="本次执行的循环次数，便于判断 Agent 在多少轮内完成")
    messages: List[AgentMessage] = Field(default_factory=list, description="完整消息历史，主要用于调试、回放和会话持久化")
    usage: Optional[Dict[str, Any]] = Field(None, description="累计 token 用量，供 credit/billing/监控使用")
    schema_data: Optional[Dict[str, Any]] = Field(None, description="最终结构化结果，供业务代码直接消费，例如落库或编排工作流")
    schema_error: Optional[str] = Field(None, description="最终结构化后处理失败时的错误信息，不影响原始文本结果")
    review_history: List[ReviewResult] = Field(default_factory=list, description="候选输出的评审历史")
    review_exhausted: bool = Field(default=False, description="评审修订轮次是否耗尽（即使最终 finished=True 也可能为 True）")
    raw_output: Optional[str] = Field(None, description="最终自然语言输出，适合展示给用户或写入日志")
    error: Optional[str] = Field(None, description="Agent 执行失败或提前退出时的错误信息")
    finished: bool = Field(default=False, description="是否正常完成整个 Agent 流程")
    finished_at: Optional[datetime] = Field(None, description="本次请求结束时间")


class ToolResult(BaseModel):
    """工具执行结果。"""

    tool_call_id: str = Field(..., description="调用 ID")
    tool_name: str = Field(..., description="工具名称")
    result: Any = Field(..., description="执行结果")
    is_error: bool = Field(default=False, description="是否错误")


class ToolExecutionResult:
    """
    execute_all 批量执行完毕后的结果集合。

    与中间事件（ToolEndEvent 等）的区别：
    - 中间事件由 execute_all 即时 yield，供调用方实时流式处理
    - ToolExecutionResult 是最后一个产出，表示本批所有工具执行完毕
    """

    def __init__(self, results: List["ToolResult"]):
        self.results: List["ToolResult"] = results


# ----------------------------------------------------------------------
# 流式事件模型
# ----------------------------------------------------------------------


class ThinkingEvent(BaseModel):
    """LLM 思考过程片段（仅 thinking 模型产生，通常用于前端实时展示调试过程）。"""
    type: Literal["thinking"] = "thinking"
    content: str


class TextEvent(BaseModel):
    """LLM 输出的文本片段（面向前端实时渲染的自然语言内容）。"""
    type: Literal["text"] = "text"
    content: str


class ToolStartEvent(BaseModel):
    """工具开始执行事件（面向前端展示 Agent 正在调用哪个工具）。"""
    type: Literal["tool_start"] = "tool_start"
    tool_call_id: str
    tool_name: str
    arguments: Dict[str, Any]


class ToolEndEvent(BaseModel):
    """工具执行完毕事件（面向前端展示工具结果或错误）。"""
    type: Literal["tool_end"] = "tool_end"
    tool_call_id: str
    tool_name: str
    result: Any
    is_error: bool = False


class UsageEvent(BaseModel):
    """单次 LLM 调用结束后的 usage 上报事件。

    每个 AgentLoop 迭代（一次 think→act→observe）末尾都会 fire 一次，
    携带这次 LLM 调用消耗的 token 数（``usage``）以及到这一刻为止本 session
    的累积消耗（``accumulated_usage``）。

    用于：
    - 前端实时 token 计费展示
    - supervisor 流水线把所有 agent（自己 + sub-agent）的 LLM call 累加到 workflow.total_tokens
    """
    type: Literal["usage"] = "usage"
    usage: Dict[str, Any] = Field(
        default_factory=dict,
        description="本次 LLM 调用的 usage（prompt_tokens / completion_tokens / thinking_tokens / total_tokens）",
    )
    accumulated_usage: Optional[Dict[str, Any]] = Field(
        None,
        description="到这一刻为止本 agent session 的累积 usage",
    )
    loop_count: int = Field(default=0, description="当前 loop 迭代次数")


class DoneEvent(BaseModel):
    """
    流结束事件，携带完整 AgentResult。

    约定上：
    - 流式过程事件给前端实时消费
    - DoneEvent.result 给业务代码读取最终结果
    """
    type: Literal["done"] = "done"
    result: "AgentResult"


class ErrorEvent(BaseModel):
    """执行出错。"""
    type: Literal["error"] = "error"
    error: str


class InterruptDecision(BaseModel):
    """
    Middleware 在 before_tool_calls 钩子中写入 ctx.metadata["interrupt"] 的中断信息。

    AgentLoop 检测到此字段后：
    1. 通过 persist.save_interrupt_state 持久化完整 checkpoint
    2. yield InterruptEvent 给前端
    3. 停止本轮循环
    """
    # 待审阅的工具调用
    tool_call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    # 中断上下文，供前端展示和后续 resume 使用
    context: Dict[str, Any] = Field(default_factory=dict)
    # 可用操作
    available_actions: List[str] = Field(
        default_factory=lambda: ["approve", "reject"],
    )


class AgentCheckpoint(BaseModel):
    """
    Agent 中断时的完整快照。

    包含：
    - 被拦截的 tool_call 信息（用于 approve 后直接执行）
    - 中断时刻的消息历史（用于 resume 时完整恢复上下文）
    - 中断时的 loop_count（用于 resume 后继续计数）

    由 persist.save_interrupt_state 持久化，resume 时通过 load_interrupt_state 恢复。
    """
    tool_call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    context: Dict[str, Any] = Field(default_factory=dict)
    available_actions: List[str] = Field(
        default_factory=lambda: ["approve", "reject"],
    )
    # 中断时刻的完整消息历史（dict 列表，与 self.messages 格式一致）
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    # 中断时的循环次数
    loop_count: int = 0


class ResumeDecision(BaseModel):
    """
    用户在人工审阅后传入的决策。

    对应 LangChain 的 Command(resume={"decisions": [{"type": "approve"}]})。
    """
    action: Literal["approve", "reject"] = Field(
        ...,
        description="approve | reject",
    )


class InterruptEvent(BaseModel):
    """
    Agent 执行被中断，等待人工审阅。

    中断发生在工具执行之前，前端收到此事件时应展示：
    - 即将执行哪个工具（tool_name）
    - 工具的参数是什么（arguments）
    - 用户可以 approve / reject
    """
    type: Literal["interrupt"] = "interrupt"
    session_id: str
    tool_name: str
    tool_call_id: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    available_actions: List[str] = Field(
        default_factory=lambda: ["approve", "reject"],
    )
    context: Dict[str, Any] = Field(default_factory=dict)


class ReviewStartEvent(BaseModel):
    """
    Review Agent 开始评审一个候选输出。

    流式场景下，候选 TextEvent 会被 buffer 直到 review 通过；
    前端可借此事件展示「评审中」状态。
    """
    type: Literal["review_start"] = "review_start"
    agent_name: str
    session_id: str = ""
    request_id: str = ""
    review_round: int
    loop_count: int = 0
    candidate_preview: str = ""


class ReviewEndEvent(BaseModel):
    """
    Review Agent 完成一次评审。

    携带本轮评审结果。前端可据此展示分数、反馈、是否进入修订循环。
    """
    type: Literal["review_end"] = "review_end"
    agent_name: str
    session_id: str = ""
    request_id: str = ""
    review_round: int
    loop_count: int = 0
    review: ReviewResult
    will_revise: bool = False
    exhausted: bool = False


# 所有事件类型的联合，用于类型标注
StreamEvent = (
    ThinkingEvent
    | TextEvent
    | ToolStartEvent
    | ToolEndEvent
    | DoneEvent
    | ErrorEvent
    | InterruptEvent
    | ReviewStartEvent
    | ReviewEndEvent
)
