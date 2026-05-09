"""
Memory 业务实现层。

framework 在 ``app.core.agent.memory`` 下定义抽象（Protocol + Harness +
FilterChain）；这一层是具体后端 / 算法的实现，由业务装配后通过
``create_agent(memory=MemoryConfig(...))`` 注入。

入口子模块：
- ``embeddings/``  EmbeddingService 实现（Gemini）
- ``providers/``   MemoryProvider 实现（pgvector 双表）
- ``rankers/``     MemoryRanker 实现（HybridRanker）
- ``extractors/``  MemoryExtractor 实现（GeminiLLMExtractor）
- ``filters/``     业务自定义 MemoryFilter（按需创建）
"""

from app.memory.embeddings import GeminiEmbeddingService
from app.memory.extractors import GeminiLLMExtractor
from app.memory.factory import build_project_memory_config
from app.memory.providers import PgvectorMemoryProvider
from app.memory.rankers import HybridRanker

__all__ = [
    "GeminiEmbeddingService",
    "GeminiLLMExtractor",
    "PgvectorMemoryProvider",
    "HybridRanker",
    "build_project_memory_config",
]
