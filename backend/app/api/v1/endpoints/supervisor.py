"""
Supervisor 流式 API 端点。

路由前缀：/api/v1/supervisor
权限：需登录用户
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# 请求 / 响应 Schema
# ---------------------------------------------------------------------------

class SupervisorStartRequest(BaseModel):
    """启动 Supervisor 流水线请求。"""
    project_id: int = Field(..., description="所属项目 ID（用于流水线记录）")
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
    db: AsyncSession = Depends(get_db),
):
    """
    启动 Supervisor 视频生成流水线，流式返回 SSE 事件。

    权限：任何已登录用户均可调用。
    """
    from app.services.supervisor_workflow_service import SupervisorWorkflowService

    service = SupervisorWorkflowService(db)
    workflow_service = service  # SupervisorWorkflowService 实例，供 call_sub_agent 持久化

    supervisor = _create_supervisor(body, user_id, workflow_service)

    # 在流式开始前创建 DB 记录（使用与 supervisor 相同的 session_id）
    try:
        await service.create_workflow(
            project_id=body.project_id,
            owner_id=user_id,
            supervisor_session_id=supervisor.supervisor_session_id,
            user_request=body.user_request,
            model=body.model,
        )
        await db.commit()
        logger.info(
            f"[supervisor/stream] workflow created: session={supervisor.supervisor_session_id}"
        )
    except Exception as e:
        logger.warning(f"[supervisor/stream] failed to create workflow record: {e}")
        # 不阻断流式，workflow 记录是可选的

    logger.info(
        f"[supervisor/stream] user_id={user_id}, project_id={body.project_id}, "
        f"user_request={body.user_request[:50]}..., supervisor_session={supervisor.supervisor_session_id}"
    )

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


def _create_supervisor(body: SupervisorStartRequest, user_id: int, workflow_service):
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
        workflow_service=workflow_service,
    )
