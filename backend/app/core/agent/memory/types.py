"""Memory framework data types."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field


class WriteTrigger(str, Enum):
    """Memory 写入路径来源。三个触发都汇聚到 MemoryHarness.write()。"""

    EXPLICIT_SAVE = "explicit_save"        # LLM 主动调 memory_save 工具
    FALLBACK_COMPACT = "fallback_compact"  # AgentLoop N 轮兜底
    USER_CORRECTION = "user_correction"    # 业务/endpoint 直接注入


class ToolCallSummary(BaseModel):
    """Filter 拿到的工具调用概要（不需要完整 ToolCall）。"""

    tool_name: str
    succeeded: bool


class RecallQuery(BaseModel):
    """召回查询。framework 不做语义解释，provider 自己决定。"""

    agent_name: str
    session_id: str
    initial_input: Optional[str] = None
    recent_messages: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecalledMemory(BaseModel):
    """provider.recall() 返回的原始候选条目。"""

    id: str
    content: str
    kind: str
    entity: Optional[dict[str, Any]] = None
    confidence: float = 1.0
    created_at: Optional[datetime] = None
    embedding: Optional[list[float]] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScoredMemory(BaseModel):
    """Ranker 处理后的结果，带打分明细给上层调试。"""

    memory: RecalledMemory
    score: float
    breakdown: dict[str, float] = Field(default_factory=dict)


class CandidateMemory(BaseModel):
    """Extractor 抽出的候选条目，等待 post-extraction filter + 写入。"""

    content: str
    kind: str
    entity: Optional[dict[str, Any]] = None
    confidence: float = 1.0
    source_message_indices: list[int] = Field(default_factory=list)
    extraction_metadata: dict[str, Any] = Field(default_factory=dict)


class FilterScore(BaseModel):
    """单个 filter 给的评分。"""

    score: float = Field(..., ge=0.0, le=1.0)
    reason: Optional[str] = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class FilterDecision(BaseModel):
    """FilterChain 聚合后的决策。caller 自己决定要不要 log。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    passed: bool
    aggregate_score: float
    threshold: float
    individual: list[Tuple[str, FilterScore]] = Field(default_factory=list)
    rejected_by: Optional[str] = None  # min 聚合时记录拉低 chain 的 filter


class PreExtractionContext(BaseModel):
    """抽取前 filter 拿到的全套上下文。预留扩展。"""

    messages: list[dict[str, Any]]
    loop_count: int
    tool_calls_made: list[ToolCallSummary] = Field(default_factory=list)
    session_started_at: datetime
    session_duration_seconds: float
    session_id: str
    agent_name: str
    user_id: Optional[str] = None
    scope_metadata: dict[str, Any] = Field(default_factory=dict)
    trigger: WriteTrigger


class PostExtractionContext(PreExtractionContext):
    """post-extraction filter 多看到一个 candidate。"""

    candidate: CandidateMemory


class WriteOutcome(BaseModel):
    """write_path 的返回，让 caller 知道发生了什么。"""

    pre_decision: FilterDecision
    candidates_total: int
    candidates_written: int
    written_ids: list[str] = Field(default_factory=list)
    post_decisions: list[FilterDecision] = Field(default_factory=list)
