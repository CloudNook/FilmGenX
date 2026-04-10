"""
Agent 框架 - 统一导出。
"""

from app.core.agent.agent import Agent
from app.core.agent.base import (
    AgentConfig,
    AgentMessage,
    AgentResult,
    LLMResponse,
    StructuredToolCall,
    ToolCall,
    ToolResult,
    UnifiedToolMessage,
)
from app.core.agent.factory import create_agent
from app.core.agent.loop import AgentLoop
from app.core.agent.llm import LLMAdapter
from app.core.agent.tool import ToolExecutor
from app.core.agent.persist import (
    PersistStrategy,
    AgentMessageRecord,
    RedisPersistStrategy,
    DBPersistStrategy,
)
from app.core.middleware.chain import AgentMiddleware, MiddlewareChain, MiddlewareContext
from app.core.middleware.builtin import LoggingMiddleware
from app.core.tools import ToolRegistry, get_tool_registry, register_tool

__all__ = [
    # 工厂函数
    "create_agent",
    # Agent 主类
    "Agent",
    # 数据模型
    "AgentConfig",
    "AgentMessage",
    "AgentResult",
    "LLMResponse",
    "StructuredToolCall",
    "ToolCall",
    "ToolResult",
    "UnifiedToolMessage",
    # 核心组件
    "AgentLoop",
    "LLMAdapter",
    "ToolExecutor",
    # 持久化
    "PersistStrategy",
    "AgentMessageRecord",
    "RedisPersistStrategy",
    "DBPersistStrategy",
    # Tool 系统
    "ToolRegistry",
    "get_tool_registry",
    "register_tool",
    # Middleware 系统
    "AgentMiddleware",
    "MiddlewareChain",
    "MiddlewareContext",
    "LoggingMiddleware",
]
