"""
通用工具错误响应载荷。

工具调用遇到 "非异常类失败"（依赖未满足、参数不合法、并发冲突等）时，应该
返回一个结构化的错误对象给 LLM，而不是 raise——LLM 才能从 tool_result 中
读到原因并自我纠正，前端也能用统一字段做高亮 / 重试 / 上报。

真正的工程异常（DB 不可用、LLM API 网络异常）仍然走 raise。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class ToolErrorPayload(BaseModel):
    """统一工具错误响应。

    Attributes:
        ok: 固定 False，便于 LLM / 前端用 ``result.get("ok")`` 一键判断成功
        error_code: 大写蛇形错误码，机器可读、可在前端按 code 翻译
        message: 1-2 句人类可读说明，给 LLM 看的"发生了什么"
        hint: 可选，给 LLM 看的"应该怎么做"。鼓励填写——能直接缩短修正回合
        context: 可选，与错误相关的结构化数据，便于前端展示和日志追溯
    """

    model_config = ConfigDict(extra="forbid")

    ok: bool = False
    error_code: str
    message: str
    hint: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)

    def to_result(self) -> Dict[str, Any]:
        """转成可直接放进 tool_result 的 dict。"""
        return self.model_dump(exclude_none=True)


def tool_error(
    *,
    error_code: str,
    message: str,
    hint: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """便捷构造器：直接返回 dict 形式（多数工具实现需要的形态）。"""
    return ToolErrorPayload(
        error_code=error_code,
        message=message,
        hint=hint,
        context=context or {},
    ).to_result()
