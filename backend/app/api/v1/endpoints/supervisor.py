"""
Supervisor 流式 API 端点。

路由前缀：/api/v1/supervisor
权限：需登录用户
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# 请求 / 响应 Schema
# ---------------------------------------------------------------------------

class SupervisorStartRequest(BaseModel):
    """启动 Supervisor 流水线请求。"""
    user_request: str = Field(..., description="用户原始需求描述")
    model: str = Field("gemini-3-flash-preview", description="LLM 模型")
    max_loop: int = Field(30, ge=1, le=100, description="最大循环次数")
    persist: Optional[str] = Field(
        "redis",
        description="持久化策略：'redis' | None",
    )
    sub_agent_configs: Dict[str, Any] = Field(
        default_factory=dict,
        description="SubAgent 配置映射（预留）",
    )


# ---------------------------------------------------------------------------
# 流式端点
# ---------------------------------------------------------------------------

@router.post(
    "/stream",
    summary="启动 Supervisor 流水线（流式 SSE）",
    description="""
创建 SupervisorAgent，流式返回所有事件（Thinking/Text/SubAgent/Review/Done）。

前端按 `event.type` 渲染对应 UI 区块。
    """,
)
async def start_supervisor_pipeline(
    body: SupervisorStartRequest,
    user_id: int = Depends(get_current_user_id),
):
    """
    启动 Supervisor 视频生成流水线，流式返回 SSE 事件。

    权限：任何已登录用户均可调用。
    """
    logger.info(
        f"[supervisor/stream] user_id={user_id}, "
        f"user_request={body.user_request[:50]}..."
    )

    supervisor = _create_supervisor(body, user_id)

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for event in supervisor.stream(initial_input=body.user_request):
                # 所有事件统一转为 JSON 行
                if hasattr(event, "model_dump"):
                    payload = event.model_dump()
                else:
                    # 兜底：未知事件类型直接转 str
                    payload = {"type": "unknown", "repr": str(event)}

                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.exception("[supervisor/stream] stream error")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


def _create_supervisor(body: SupervisorStartRequest, user_id: int):
    """
    创建 SupervisorAgent 实例。

    延迟导入以避免循环依赖。
    """
    from app.core.supervisor.factory import create_supervisor

    persist: Any = None
    if body.persist and body.persist != "none":
        persist = body.persist  # "redis" → factory 内部解析

    return create_supervisor(
        user_request=body.user_request,
        model=body.model,
        max_loop=body.max_loop,
        persist=persist,
        sub_agent_configs=body.sub_agent_configs,
    )
