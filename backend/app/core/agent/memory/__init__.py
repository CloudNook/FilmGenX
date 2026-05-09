"""
Agent memory framework —— 抽象层。

通过 ``create_agent(memory=MemoryConfig(...))`` 挂载，跟 reviewer / skill 同级。
framework 只定义接口 + 调度时机；具体的 provider / extractor / ranker / filter
全由业务在 ``app/memory/`` 下实现。

入口：
- ``MemoryConfig``: 用户面声明式配置
- ``MemoryHarness``: 框架内部协调器，AgentLoop 直接持有

约定：
- 召回是同步带 timeout，失败静默降级（不阻塞主流）
- 写入流：raw → pre_filter → extract → post_filter → provider.write
- Filter 评分制 + chain 聚合 + 阈值
- Filter 实现自己负责 logging（框架不提供 sink）

不提供任何具体实现 —— 业务自定义符合 Protocol 的 provider / ranker / extractor /
filter 后注入即可。
"""

from app.core.agent.memory.config import MemoryConfig
from app.core.agent.memory.embedding import EmbeddingService
from app.core.agent.memory.extractor import MemoryExtractor
from app.core.agent.memory.filter import FilterChain, MemoryFilter
from app.core.agent.memory.harness import MemoryHarness
from app.core.agent.memory.provider import MemoryProvider
from app.core.agent.memory.ranker import MemoryRanker
from app.core.agent.memory.tool import (  # noqa: F401  triggers @register_tool
    build_memory_save_tool_schema,
    memory_save_handler,
)
from app.core.agent.memory.types import (
    CandidateMemory,
    FilterDecision,
    FilterScore,
    PostExtractionContext,
    PreExtractionContext,
    RecallQuery,
    RecalledMemory,
    ScoredMemory,
    ToolCallSummary,
    WriteOutcome,
    WriteTrigger,
)

__all__ = [
    # 用户面
    "MemoryConfig",
    "MemoryHarness",
    # Protocol
    "MemoryProvider",
    "MemoryRanker",
    "MemoryExtractor",
    "MemoryFilter",
    "EmbeddingService",
    # framework 自有的聚合逻辑
    "FilterChain",
    # 数据类型
    "RecallQuery",
    "RecalledMemory",
    "ScoredMemory",
    "CandidateMemory",
    "FilterScore",
    "FilterDecision",
    "PreExtractionContext",
    "PostExtractionContext",
    "ToolCallSummary",
    "WriteOutcome",
    "WriteTrigger",
    # tool registration
    "build_memory_save_tool_schema",
    "memory_save_handler",
]
