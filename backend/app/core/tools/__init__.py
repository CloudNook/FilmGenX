"""
Tools 系统 - 装饰器式工具注册与调用。

使用方式::

    from app.core.tools import register_tool, ToolRegistry

    @register_tool(name="calculate", description="执行数学计算")
    def calculate(expression: str) -> str:
        return str(eval(expression))

内置工具::

    from app.core.tools.builtin import load_skill, load_skill_reference
"""

from app.core.tools.builtin import load_skill, load_skill_reference
from app.core.tools.registry import ToolRegistry, get_tool_registry, register_tool
from app.core.tools import examples as _examples  # noqa: F401 — 触发示例工具注册


def _ensure_supervisor_tools():
    """Lazy import to avoid circular import with app.core.agent."""
    from app.core.tools import supervisor_tools  # noqa: F401

    return supervisor_tools


__all__ = [
    "ToolRegistry",
    "get_tool_registry",
    "register_tool",
    "load_skill",
    "load_skill_reference",
    "_ensure_supervisor_tools",
]
