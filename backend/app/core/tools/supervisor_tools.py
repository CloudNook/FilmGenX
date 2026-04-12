"""
Supervisor 工具注册入口。

通过 import 触发 @register_tool 装饰器，将工具注册到 ToolRegistry。
"""

from app.core.supervisor.tools import call_sub_agent, call_reviewer, get_workflow_state

# 以下 import 仅用于触发 @register_tool 装饰器注册
# 实际工具在 SupervisorAgent._agent.stream() 中通过 ToolExecutor 执行
_imported = (call_sub_agent, call_reviewer, get_workflow_state)

__all__ = ["_imported"]
