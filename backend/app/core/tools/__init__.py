"""
Tools 系统 - 装饰器式工具注册与调用。

使用方式：
    from app.core.tools import register_tool, ToolRegistry

    @register_tool(name="calculate", description="执行数学计算")
    def calculate(expression: str) -> str:
        return str(eval(expression))

内置工具：
    from app.core.tools.builtin import load_skill, load_skill_lite
"""

from app.core.tools.builtin import load_skill, load_skill_lite
from app.core.tools import supervisor_tools  # noqa: F401 — 触发 Supervisor 工具注册
from app.core.tools.registry import ToolRegistry, get_tool_registry, register_tool

__all__ = [
    "ToolRegistry",
    "get_tool_registry",
    "register_tool",
    "load_skill",
    "load_skill_lite",
    "supervisor_tools",
]
