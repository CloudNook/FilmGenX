"""
``create_agent(memory=MemoryConfig(...))`` 的声明式入参。

跟 ``Reviewer`` 同级——framework 唯一的入口。内部 ``MemoryHarness`` 负责接线。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.agent.memory.extractor import MemoryExtractor
from app.core.agent.memory.filter import FilterChain
from app.core.agent.memory.provider import MemoryProvider
from app.core.agent.memory.ranker import MemoryRanker

InjectStrategy = Literal["structured_block", "system_message", "user_preamble"]


class MemoryConfig(BaseModel):
    """Agent memory 用户面配置。

    framework 不内置任何具体实现 —— provider / ranker / extractor 全由业务在
    ``app/memory/`` 下实现并注入。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # ---- 必填：业务实现的 plug-in ----
    provider: MemoryProvider
    extractor: MemoryExtractor
    ranker: MemoryRanker

    # ---- 双 filter chain（空 chain 表示不做该层过滤，等价无 filter）----
    pre_extraction_filters: FilterChain = Field(default_factory=FilterChain)
    post_extraction_filters: FilterChain = Field(default_factory=FilterChain)

    # ---- 召回参数 ----
    recall_threshold: float = Field(0.5, ge=0.0, le=1.0)
    recall_max_items: int = Field(10, gt=0)
    recall_timeout_seconds: float = Field(2.0, gt=0)

    # ---- 写入触发 ----
    save_tool_enabled: bool = True
    fallback_compact_every_n_loops: int = Field(5, gt=0)
    fallback_compact_message_window: int = Field(20, gt=0)

    # ---- 注入 prompt 形态 ----
    inject_strategy: InjectStrategy = "structured_block"
    inject_section_title: str = "## 召回记忆"

    # ---- scope：业务塞 project_id / user_id 等，框架透传给 provider ----
    scope_metadata: dict[str, Any] = Field(default_factory=dict)
    # 注：provider / extractor / ranker 三个 Protocol 字段由 Pydantic 自身的
    # arbitrary_types_allowed + isinstance 校验把关；不满足 Protocol 直接 ValidationError。
