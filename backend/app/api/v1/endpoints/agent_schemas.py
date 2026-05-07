"""
Agent 输出 schema 暴露端点。

把 ``app.schemas.agent_outputs`` 下的 Pydantic 类的 JSON Schema 通过 HTTP 暴露给
前端，让前端 sub-agent 结果渲染器拿到字段元数据（``title`` 做 UI 标签、
``description`` 做 hover 说明、``properties`` / ``$defs`` 做字段发现），不再
硬编码字段名。

需要登录但不需要 admin 权限——这条信息属于"agent 框架契约"，普通用户也会看到
sub-agent 输出。
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.agent_outputs import (
    OutlineOutput,
    ScriptOutput,
    StoryboardOutput,
)

router = APIRouter()


# Sub-agent 名 → 对应输出 Pydantic 类。新增 sub-agent 时在这里加一行。
_SUB_AGENT_OUTPUT_SCHEMAS = {
    "outline_agent": OutlineOutput,
    "script_agent": ScriptOutput,
    "storyboard_agent": StoryboardOutput,
}


@router.get(
    "",
    summary="获取所有 sub-agent 输出 schema",
)
def list_agent_schemas(
    _user: User = Depends(get_current_user),
) -> Dict[str, Dict[str, Any]]:
    """
    返回 ``{sub_agent_name: <JSON Schema>}`` 字典。

    每个 schema 是 Pydantic ``model_json_schema()`` 的输出，包含：
    - ``title`` / ``description`` / ``type``
    - ``properties``：每个字段的 ``title`` / ``description`` / ``type`` / ``items`` 等
    - ``$defs``：嵌套类型定义（CharacterArc / Act / Scene / Shot ...）
    - ``required``：必填字段列表
    """
    return {
        name: cls.model_json_schema()
        for name, cls in _SUB_AGENT_OUTPUT_SCHEMAS.items()
    }
