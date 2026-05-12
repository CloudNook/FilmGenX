"""
AI 工作台（Workspace）API 端点。

路由前缀：/api/v1/projects/{project_id}/workspaces

核心：通过 Agent 框架的 stream() 实现 SSE 流式多轮对话，
复用 DBPersistStrategy 持久化，复用 agent_messages 表存储消息。
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.db.session import AsyncSessionFactory
from app.core.agent.persist.models import AgentMessageRecord
from app.core.agent import (
    create_agent,
    ThinkingEvent,
    TextEvent,
    ToolStartEvent,
    ToolEndEvent,
    DoneEvent,
    UsageEvent,
    ErrorEvent,
    InterruptEvent,
    ReviewStartEvent,
    ReviewEndEvent,
)
from app.core.agent.reviewer import create_reviewer_agent
from app.core.agent.persist.db_strategy import DBPersistStrategy
from app.core.tools import ToolRegistry
from app.models.workspace import Workspace
from app.repositories.workspace import WorkspaceRepository
from app.repositories.project import ProjectRepository
from app.schemas.base import PageResponse
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    WorkspaceDetailResponse,
    WorkspaceChatRequest,
    AgentMessageResponse,
    PendingInterrupt,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# 默认 System Prompt
# ---------------------------------------------------------------------------

DEFAULT_SYSTEM_PROMPT = """你是 FilmGenX AI 视频制作助手。你具备专业的影视制作知识，能帮用户从剧本创作走到视频生成全流程。

# 你的能力

- 剧本创作与分析（大纲 / 场景 / 对白）
- 角色设计与形象生成
- 场景设计与氛围营造
- 分镜脚本规划与运镜设计
- 图片 / 视频生成提示词编写
- 项目级长期记忆维护（character / scene / style / outline / script 等 KV）

# 工具调用协议（强约束）

每次调用工具时，必须在**同一轮回复**里完成两件事：

1. 先输出 1-2 句文字，**说清你要调哪个工具、为什么调、期望得到什么**
2. **紧接着、在同一轮里**发起 tool_call

不要把"说明"和"调用"拆成两轮——AgentLoop 看到没 tool_call 会判定循环结束、任务卡死。你要持续工作，必须每次说完意图就立即调。

你具备以下几类能力（具体可用工具运行时可能扩展，**不要凭这段记忆作答**）：
- 加载领域知识（skill / reference）
- 写入项目级 memory（KV）
- 生成图像 / 视频（产物会自动落 ``assets`` 表并分配 asset_code）

# 用户问"你有什么工具 / 你能做什么"时

**必须**先调 ``list_tools`` 拿当前实时工具清单，再据此整理回答；
不要凭印象或上下文示例片段罗列——那些可能过时、不全。
``list_tools`` 是工具清单的**唯一权威来源**。

正例：
> "你想给萧炎做三视图。我先调 ``generate_image`` 出图，name 填 '萧炎' 让前端有人话标题，画幅 9:16 高质量 2K。"
> 〔同一轮 immediately 调用 ``generate_image(prompt='萧炎三视图：黑发、玄重尺背身、玄铁色战袍...', name='萧炎', aspect_ratio='9:16', resolution='2K', quality='high')``〕

工具返回 asset_code 后，下一轮再继续：
> "三视图已出（asset_code=img-abc123）。把它写回 ``character.萧炎.three_view_asset_code``。"
> 〔同一轮 immediately 调用 ``memory_save(...)``〕

反例（禁止）：
- 只输出说明文字、不发起 tool_call —— Agent 立刻退出循环
- 直接 tool_call 没说明 —— 用户无法跟上判断
- 把意图说明留到下一轮才调 —— 同样会卡死

任何动作都要先**讲清意图 + 理由**，但说完立即执行。涉及影视 / 编剧专业知识时同样按协议——先说要 load 哪个 skill，立即调。

# 项目级 Memory（KV 仓库）

每个 project 有一份有限集合的 KV 仓库，跨会话共享：

| kind | key | 关键字段 |
| --- | --- | --- |
| character | 角色名 | appearance / key_skills / three_view_url / reference_image_urls |
| scene | 场景名 | atmosphere / lighting / reference_image_urls |
| style | palette / lighting / composition / mood / camera | description / keywords |
| preference | genre / duration / pacing / format / structure | description |
| outline | main | summary / characters / key_arcs / duration_seconds |
| script | main | summary / scene_count / total_duration_seconds / famous_quotes |

**写入路径**：
- preference / outline：自动从对话抽取，**你不需要手动写**
- character / scene / style / script：你必须按工具调用协议显式调 ``memory_save`` 写入

**召回路径**：每次对话开始前，所有 active KV 自动注入到你的上下文，按 kind 分组。直接消费字段，不要让用户反复重述。

# 风格

始终用中文回复，专业且友好。回答前先看注入的 KV，已有的信息不要让用户重复说。
"""


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

async def _require_project(project_id: int, user_id: int, db: AsyncSession):
    project = await ProjectRepository(db).get_by_id_and_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project


async def _require_workspace(
    workspace_id: int, project_id: int, db: AsyncSession
) -> Workspace:
    ws = await WorkspaceRepository(db).get_by_id_and_project(workspace_id, project_id)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作台不存在")
    return ws


def _serialize_agent_event(event) -> dict:
    """将 Agent 流式事件序列化为 SSE data dict。"""
    if isinstance(event, ThinkingEvent):
        return {"type": "thinking", "content": event.content}
    elif isinstance(event, TextEvent):
        return {"type": "text", "content": event.content}
    elif isinstance(event, ToolStartEvent):
        return {
            "type": "tool_start",
            "tool_call_id": event.tool_call_id,
            "tool_name": event.tool_name,
            "arguments": event.arguments,
        }
    elif isinstance(event, ToolEndEvent):
        return {
            "type": "tool_end",
            "tool_call_id": event.tool_call_id,
            "tool_name": event.tool_name,
            "result": event.result,
            "is_error": event.is_error,
        }
    elif isinstance(event, DoneEvent):
        return {
            "type": "done",
            "usage": event.result.usage,
            "loop_count": event.result.loop_count,
            "finished": event.result.finished,
        }
    elif isinstance(event, UsageEvent):
        return {
            "type": "usage",
            "usage": event.usage,
            "accumulated_usage": event.accumulated_usage,
            "loop_count": event.loop_count,
        }
    elif isinstance(event, ErrorEvent):
        return {"type": "error", "error": event.error}
    elif isinstance(event, InterruptEvent):
        return {
            "type": "interrupt",
            "session_id": event.session_id,
            "tool_name": event.tool_name,
            "tool_call_id": event.tool_call_id,
            "arguments": event.arguments,
            "available_actions": event.available_actions,
            "context": event.context,
        }
    elif isinstance(event, ReviewStartEvent):
        return {
            "type": "review_start",
            "review_round": event.review_round,
            "candidate_preview": event.candidate_preview,
        }
    elif isinstance(event, ReviewEndEvent):
        return {
            "type": "review_end",
            "review_round": event.review_round,
            "score": event.review.score,
            "passed": event.review.passed,
            "feedback": event.review.feedback,
            "suggestions": event.review.suggestions,
        }
    return {"type": "unknown"}


# ---------------------------------------------------------------------------
# Workspace CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=PageResponse[WorkspaceResponse], summary="获取工作台列表")
async def list_workspaces(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    items, total = await WorkspaceRepository(db).get_by_project(
        project_id, page=page, page_size=page_size
    )
    return PageResponse(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新建工作台",
)
async def create_workspace(
    project_id: int,
    body: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)

    from uuid import uuid4
    session_id = f"ws_{uuid4().hex[:16]}"

    ws = await WorkspaceRepository(db).create(
        project_id=project_id,
        title=body.title,
        session_id=session_id,
        system_prompt=body.system_prompt,
    )
    await db.commit()
    return ws


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceDetailResponse,
    summary="获取工作台详情（含历史消息）",
)
async def get_workspace(
    project_id: int,
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    ws = await _require_workspace(workspace_id, project_id, db)

    # 从 agent_messages 表加载历史消息
    stmt = (
        select(AgentMessageRecord)
        .where(AgentMessageRecord.session_id == ws.session_id)
        .order_by(AgentMessageRecord.seq)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    messages = []
    for r in records:
        messages.append(
            AgentMessageResponse(
                role=r.role,
                content=r.content,
                seq=r.seq,
                tool_call_id=r.tool_call_id,
                tool_name=r.tool_name,
                usage=r.usage,
                extra_metadata=r.extra_metadata,
                created_at=r.created_at,
            )
        )

    # 检查是否有待审阅的中断状态
    pending_interrupt = None
    try:
        checkpoint = await DBPersistStrategy(db=db).load_interrupt_state(ws.session_id)
        if checkpoint is not None:
            pending_interrupt = PendingInterrupt(
                tool_name=checkpoint.tool_name,
                tool_call_id=checkpoint.tool_call_id,
                arguments=checkpoint.arguments,
                available_actions=checkpoint.available_actions,
                context=checkpoint.context,
            )
    except Exception:
        pass

    return WorkspaceDetailResponse(
        id=ws.id,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
        project_id=ws.project_id,
        title=ws.title,
        agent_name=ws.agent_name,
        session_id=ws.session_id,
        system_prompt=ws.system_prompt,
        status=ws.status,
        total_tokens=ws.total_tokens,
        last_message_at=ws.last_message_at,
        messages=messages,
        pending_interrupt=pending_interrupt,
    )


@router.patch("/{workspace_id}", response_model=WorkspaceResponse, summary="更新工作台")
async def update_workspace(
    project_id: int,
    workspace_id: int,
    body: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    ws = await _require_workspace(workspace_id, project_id, db)

    data = body.model_dump(exclude_none=True)
    ws = await WorkspaceRepository(db).update(ws, data)
    await db.commit()
    return ws


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除工作台",
)
async def delete_workspace(
    project_id: int,
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    ws = await _require_workspace(workspace_id, project_id, db)
    # 软删除 workspace（agent_messages 通过 session_id 关联，暂不级联删除）
    await WorkspaceRepository(db).soft_delete(ws)
    await db.commit()


# ---------------------------------------------------------------------------
# 核心端点：流式对话
# ---------------------------------------------------------------------------

# 后台 task 表：同一 workspace 同时只允许一个在跑（防止双击发送 / 并发 resume race），
# 任务完成后 done_callback 清理。模块级 dict 同时充当强引用防 GC。
# 同样模式见 supervisor.py，这里复用思路。
_BG_WORKSPACE_TASKS: Dict[int, "asyncio.Task[None]"] = {}

# session factory used by background workspace tasks。indirected through module attr
# so unit tests can monkeypatch it without spinning up a real DB.
_bg_session_factory = AsyncSessionFactory


# bg task 完成后 stream 保留这么久，让短暂网络断开 / 刷新页面也能追上后续事件。
_WORKSPACE_STREAM_GRACE_SECONDS = 60.0


class _WorkspaceStream:
    """每个 workspace 一个 in-memory 事件总线 + 历史 buffer。

    架构：
    - bg task 通过 ``publish(event)`` 写事件 → buffer 追加 + 现场订阅者 queue 推送
    - chat SSE 和 tail SSE 都通过 ``subscribe()`` 拿独立 queue；可选 ``from_seq=N``
      让 tail 先回放 buffer 已有事件再 wait 新事件
    - bg task 退出时调 ``mark_done()``，订阅者读完 queue 看到 sentinel 就退出
    - bg task 完成后 stream 仍保留 ``_WORKSPACE_STREAM_GRACE_SECONDS``，让刷新窗口
      内连入的 tail SSE 也能拿到完整 buffer 回放

    与 supervisor 的 ``supervisor_events`` 表设计的差异：workspace 这边只放内存，
    backend 重启 = stream 丢；但 agent_messages 表已经把完整消息持久化了，重启
    后用户能在初始 detail fetch 里拿到所有完整消息，只是丢掉了"in-flight 进度"——
    这跟"backend 重启时 bg task 自身也死了"是一致的代价。
    """

    def __init__(self) -> None:
        # _seq 是 1-indexed 单调递增；events[i] 的 seq = i + 1
        self.events: list[Dict[str, Any]] = []
        self.subscribers: set["asyncio.Queue[Dict[str, Any]]"] = set()
        self.done: bool = False
        self._done_event = asyncio.Event()

    def publish(self, event: Dict[str, Any]) -> None:
        """追加事件到 buffer + 广播给现场订阅者。"""
        event = dict(event)  # 不污染调用方的 dict
        event["_seq"] = len(self.events) + 1
        self.events.append(event)
        for q in list(self.subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # 订阅者跟不上 → 丢掉本条；buffer 仍保留，可通过重连重放追上
                pass

    def mark_done(self) -> None:
        self.done = True
        self._done_event.set()
        # 推一个 sentinel 让所有订阅者从 wait 中醒来
        for q in list(self.subscribers):
            try:
                q.put_nowait({"__sentinel__": "done"})
            except asyncio.QueueFull:
                pass

    def subscribe(self) -> "asyncio.Queue[Dict[str, Any]]":
        q: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=512)
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: "asyncio.Queue[Dict[str, Any]]") -> None:
        self.subscribers.discard(q)

    def events_after(self, from_seq: int) -> list[Dict[str, Any]]:
        """回放 ``_seq > from_seq`` 的所有缓冲事件（含尚未推完的）。"""
        if from_seq <= 0:
            return list(self.events)
        return [e for e in self.events if e.get("_seq", 0) > from_seq]


# 模块级注册表：workspace_id → _WorkspaceStream
_WORKSPACE_STREAMS: Dict[int, _WorkspaceStream] = {}


def _schedule_workspace_stream_gc(workspace_id: int) -> None:
    """bg task 完成后排定 grace 期清理：60s 后从注册表移除。"""

    async def _gc() -> None:
        await asyncio.sleep(_WORKSPACE_STREAM_GRACE_SECONDS)
        # 只在 task 已不在跑时才移除；如果同一 workspace 又起了新对话就别动
        current_task = _BG_WORKSPACE_TASKS.get(workspace_id)
        if current_task is None or current_task.done():
            _WORKSPACE_STREAMS.pop(workspace_id, None)
            logger.debug(
                "[Workspace:%s] stream gc'd after %ss grace",
                workspace_id, _WORKSPACE_STREAM_GRACE_SECONDS,
            )

    asyncio.create_task(_gc())


def _build_workspace_agent_args(
    *,
    ws: Workspace,
    body: WorkspaceChatRequest,
    bg_db: AsyncSession,
) -> Dict[str, Any]:
    """从 workspace 行 + chat 请求体构造 create_agent 入参。

    抽出来是为了让 chat_workspace 和 _workspace_producer 共享同一份装配逻辑——
    request handler 早期验证不需要构造 agent，bg task 真正运行时才构造。
    """
    from app.core.middleware.builtin import HumanInTheLoopMiddleware

    prompt = ws.system_prompt or DEFAULT_SYSTEM_PROMPT
    tools = ToolRegistry.get_all_schemas()
    persist = DBPersistStrategy(db=bg_db)

    middlewares: list = []
    hitl_auto_tools = body.hitl_auto_tools
    if hitl_auto_tools is None and ws.hitl_enabled:
        hitl_auto_tools = []
    if hitl_auto_tools is not None:
        middlewares.append(HumanInTheLoopMiddleware(auto_tool_list=hitl_auto_tools))

    enable_review = body.enable_review or ws.review_enabled
    reviewer = (
        create_reviewer_agent(
            criteria=["内容质量", "创意表达", "专业性", "可执行性"],
            min_score=7.0,
            max_revision_rounds=1,
            on_exhausted="accept_last",
        )
        if enable_review
        else None
    )

    memory_config = None
    if ws.memory_enabled:
        from app.memory import build_domain_memory_config

        memory_config = build_domain_memory_config(domain_id=ws.project_id)

    return dict(
        agent_name=ws.agent_name,
        session_id=ws.session_id,
        prompt=prompt,
        model=body.model or ws.model or "gemini-3-flash-preview",
        temperature=body.temperature if body.temperature is not None else ws.temperature,
        tools=tools,
        skill_names=ws.skill_names if hasattr(ws, "skill_names") else [],
        persist=persist,
        middlewares=middlewares,
        reviewer=reviewer,
        memory=memory_config,
    )


async def _workspace_producer(
    stream: _WorkspaceStream,
    *,
    workspace_id: int,
    project_id: int,
    body: WorkspaceChatRequest,
) -> None:
    """后台任务：用独立 db session 跑 workspace agent，把事件发到 stream（广播 + 缓存）。

    跟 supervisor 那套同款思路：刷新 / 断网导致 chat SSE consumer 退出时，本 task
    仍持有自己的 ``AsyncSessionFactory`` 会话继续跑完 agent，不会被 ``CancelledError`` 杀掉。
    agent_messages 表的写入由 DBPersistStrategy 完成，等于自动持久化进度。

    事件路径：
    - 每个 agent.stream 事件 → ``stream.publish(event)`` → 进入 buffer + 广播给所有订阅者
    - chat SSE / tail SSE 都从 ``stream.subscribe()`` 拿独立 queue 拉
    - bg task 退出（success / cancel / error）→ ``stream.mark_done()`` 推 sentinel
    """
    from app.core.agent.base import ResumeDecision

    try:
        async with _bg_session_factory() as bg_db:
            # 在 bg session 里重新拿 workspace 行（request session 已经关闭了）
            ws = (
                await bg_db.execute(
                    select(Workspace).where(
                        Workspace.id == workspace_id,
                        Workspace.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            if ws is None:
                stream.publish({"type": "error", "error": f"Workspace {workspace_id} not found"})
                return

            try:
                resume = (
                    ResumeDecision(action=body.resume.action)
                    if body.resume is not None
                    else None
                )
                agent = create_agent(**_build_workspace_agent_args(ws=ws, body=body, bg_db=bg_db))

                total_tokens_delta = 0
                async for event in agent.stream(body.content, resume=resume):
                    data = _serialize_agent_event(event)
                    stream.publish(data)

                    if isinstance(event, DoneEvent) and event.result.usage:
                        usage = event.result.usage
                        total_tokens_delta = usage.get("total_tokens") or 0

                # token 累加（成功路径才走，错误路径 db 已 rollback）
                if total_tokens_delta > 0:
                    try:
                        await WorkspaceRepository(bg_db).update_tokens(
                            workspace_id, total_tokens_delta
                        )
                        await bg_db.commit()
                    except Exception:
                        logger.exception(
                            "[Workspace:%s/bg] Failed to update tokens", workspace_id,
                        )
            except asyncio.CancelledError:
                # 唯一应该到这里的场景：应用 shutdown。Bg task 不应被请求生命周期取消。
                logger.warning("[Workspace:%s/bg] cancelled", workspace_id)
                try:
                    await bg_db.rollback()
                except Exception:
                    logger.exception("[Workspace:%s/bg] rollback on cancel failed", workspace_id)
                raise
            except Exception as exc:
                logger.exception("[Workspace:%s/bg] Agent stream error: %s", workspace_id, exc)
                stream.publish({"type": "error", "error": str(exc)})
                try:
                    await bg_db.rollback()
                except Exception:
                    logger.exception("[Workspace:%s/bg] rollback on error failed", workspace_id)
    finally:
        stream.mark_done()
        _schedule_workspace_stream_gc(workspace_id)


@router.post("/{workspace_id}/chat", summary="Agent 流式对话（SSE）/ HITL Resume")
async def chat_workspace(
    project_id: int,
    workspace_id: int,
    body: WorkspaceChatRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    通过 Agent 框架的 stream() 实现多轮流式对话，同时支持 HITL Resume。

    普通对话模式：body.resume 为 None，body.content 为用户消息。
    Resume 模式：body.resume 包含 action（approve/reject），content 可为空，
                 Agent 从持久化的中断快照恢复并继续执行。

    SSE 事件类型：
      - thinking: Agent 思考过程片段
      - text: Agent 回复文本片段
      - tool_start: 工具开始执行
      - tool_end: 工具执行完毕
      - interrupt: 工具调用等待人工审阅（HITL）
      - done: 对话结束（含 usage 统计）
      - error: 执行出错
    """
    # 同步验证（用 request db），bg task 后面会用自己的 session 重新 reload workspace。
    await _require_project(project_id, user_id, db)
    await _require_workspace(workspace_id, project_id, db)

    # 同 session 已有在跑的 bg task → 拒绝并发，避免 agent_messages 写入 race。
    existing_task = _BG_WORKSPACE_TASKS.get(workspace_id)
    if existing_task is not None and not existing_task.done():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Workspace {workspace_id} 已有一个对话在进行中，请等它结束 / 失败后再发"
            ),
        )

    # 新建 stream（替换上一次的 buffer，避免污染）+ 起 bg task。
    # bg task done 后 stream 还会保留 60 秒 grace 给晚到的 tail SSE 用。
    stream = _WorkspaceStream()
    _WORKSPACE_STREAMS[workspace_id] = stream

    task = asyncio.create_task(
        _workspace_producer(
            stream,
            workspace_id=workspace_id,
            project_id=project_id,
            body=body,
        )
    )
    _BG_WORKSPACE_TASKS[workspace_id] = task
    task.add_done_callback(lambda _t, wid=workspace_id: _BG_WORKSPACE_TASKS.pop(wid, None))

    # chat SSE 订阅 stream；从开头 (from_seq=0) 拿完整事件流
    return _build_workspace_event_stream_response(stream, from_seq=0)


def _build_workspace_event_stream_response(
    stream: _WorkspaceStream,
    *,
    from_seq: int,
) -> StreamingResponse:
    """构造 SSE 响应：先回放 buffer 已有事件（``_seq > from_seq``），再 live tail。

    chat SSE 和 tail SSE 走同一份消费逻辑：from_seq=0 = 从头看；from_seq=N = 续上。
    """

    async def event_stream() -> AsyncGenerator[str, None]:
        # 先订阅，再回放——保证回放期间产生的新事件也会落到 queue，不会"少看几条"
        queue = stream.subscribe()
        # 已经在 buffer 里的 seq 集合，防止 live queue 推过来的事件被重复 yield
        replayed_seqs: set[int] = set()
        try:
            # 1) 回放 buffer 中 _seq > from_seq 的历史事件
            for past in stream.events_after(from_seq):
                seq = past.get("_seq", 0)
                replayed_seqs.add(seq)
                yield f"data: {json.dumps(past, ensure_ascii=False)}\n\n"

            # 2) live tail：从 queue 拿新事件
            while True:
                # bg task 已 done 且 queue 已空 → 收尾
                if stream.done and queue.empty():
                    break
                item = await queue.get()
                if isinstance(item, dict) and item.get("__sentinel__") == "done":
                    # mark_done 推过来的；如果队列里还有别的事件，继续放完再退出
                    if queue.empty():
                        break
                    continue
                seq = item.get("_seq", 0) if isinstance(item, dict) else 0
                if seq and seq in replayed_seqs:
                    # 回放阶段已 yield 过，跳过
                    continue
                if isinstance(item, dict):
                    yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

            yield "data: [DONE]\n\n"
        except asyncio.CancelledError:
            # 客户端断开（刷新 / 关 tab）。bg task 不受影响；stream 仍在
            # 注册表里，下次连入还能回放 + 继续 tail。
            raise
        finally:
            stream.unsubscribe(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Tail SSE：刷新 / 跨 tab 时附到现有 in-flight bg task 的事件流
# ---------------------------------------------------------------------------

@router.get(
    "/{workspace_id}/stream",
    summary="Tail workspace agent 事件流",
    description=(
        "SSE 端点：附到 workspace 当前 in-flight bg task 的事件总线。"
        "先回放 buffer 里 _seq > from_seq 的所有事件，再 live tail 新事件，"
        "直到 bg task 完成。如果当前 workspace 没有 in-flight bg task（或已结束 60s）→"
        "立即 emit [DONE] 关闭。用于浏览器刷新 / 跨 tab 同步进度。"
    ),
)
async def tail_workspace(
    project_id: int,
    workspace_id: int,
    from_seq: int = Query(0, ge=0, description="只回放 _seq > 此值的事件；首次连接传 0"),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    await _require_workspace(workspace_id, project_id, db)

    stream = _WORKSPACE_STREAMS.get(workspace_id)

    if stream is None:
        # 没有 in-flight bg task，也没有 60s grace 内的残留 stream → 直接收尾。
        # 前端 fetch detail 已经拿到所有 finalized 消息，不需要 replay。
        async def _empty() -> AsyncGenerator[str, None]:
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            _empty(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return _build_workspace_event_stream_response(stream, from_seq=from_seq)
