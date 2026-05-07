"""
业务层 Agent 定义（与 core 框架解耦）。

存放 supervisor sub-agent 的 prompt、reviewer prompt、output schema 绑定。
core/supervisor/registry.py 从这里导入装配，业务演化只动这一层。
"""

from app.agents.supervisor_agents import (
    REVIEWER_CRITERIA,
    REVIEWER_PROMPT,
    SUB_AGENT_PROMPT,
    SUB_AGENT_RESPONSE_SCHEMA,
)

__all__ = [
    "SUB_AGENT_PROMPT",
    "SUB_AGENT_RESPONSE_SCHEMA",
    "REVIEWER_PROMPT",
    "REVIEWER_CRITERIA",
]
