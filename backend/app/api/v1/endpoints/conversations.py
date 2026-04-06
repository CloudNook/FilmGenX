"""
对话会话（Conversation）API 端点。

路由前缀：/api/v1/projects/{project_id}/conversations

每个 Conversation 对应一集动画的完整创作对话：
  - 消息逐条持久化
  - 支持多次总结（outline_draft 消息）
  - 确认后创建 Scene 并触发分镜 Celery 任务
"""

import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.repositories.conversation import ConversationRepository, MessageRepository
from app.repositories.project import ProjectRepository
from app.repositories.scene import SceneRepository
from app.repositories.task import TaskRepository
from app.schemas.base import PageResponse
from app.schemas.conversation import (
    ConversationConfirmRequest,
    ConversationConfirmResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
)

router = APIRouter()

from app.prompts import CHAT_SYSTEM_PROMPT, SUMMARIZE_SYSTEM_PROMPT
from app.schemas.conversation import EpisodeOutline


# ---------------------------------------------------------------------------
# 请求 Schema（新增）
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """发送聊天消息请求。"""
    content: str = Field(..., description="用户消息内容")
    llm_config: dict = Field(..., description="LLM 配置，包含 provider/model/api_key/temperature 等")


class SummarizeRequest(BaseModel):
    """触发剧本总结请求。"""
    llm_config: dict = Field(..., description="LLM 配置")


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

async def _require_project(project_id: int, user_id: int, db: AsyncSession):
    project = await ProjectRepository(db).get_by_id_and_owner(project_id, user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project


async def _require_conversation(conversation_id: int, project_id: int, db: AsyncSession):
    conv = await ConversationRepository(db).get_by_id_and_project(conversation_id, project_id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    return conv


# ---------------------------------------------------------------------------
# Conversation CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=PageResponse[ConversationResponse], summary="获取会话列表")
async def list_conversations(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    items, total = await ConversationRepository(db).get_by_project(
        project_id, page=page, page_size=page_size
    )
    return PageResponse(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新建会话",
)
async def create_conversation(
    project_id: int,
    body: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    conv = await ConversationRepository(db).create(
        project_id=project_id,
        title=body.title,
    )
    await db.commit()
    return conv


@router.get("/{conversation_id}", response_model=ConversationDetailResponse, summary="获取会话详情（含消息）")
async def get_conversation(
    project_id: int,
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    conv = await ConversationRepository(db).get_with_messages(conversation_id)
    if not conv or conv.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    return conv


@router.patch("/{conversation_id}", response_model=ConversationResponse, summary="更新会话信息")
async def update_conversation(
    project_id: int,
    conversation_id: int,
    body: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """更新会话标题或状态（不新增消息）。

    若需保存 outline_draft/outline_confirmed 消息，请使用聊天/总结接口。
    """
    await _require_project(project_id, user_id, db)
    conv = await _require_conversation(conversation_id, project_id, db)

    if conv.status == "confirmed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="已确认的会话不可修改状态",
        )

    data = body.model_dump(exclude_none=True)
    # EpisodeOutline → dict
    if body.latest_outline is not None:
        data["latest_outline"] = body.latest_outline.model_dump()

    conv = await ConversationRepository(db).update(conv, data)
    await db.commit()
    return conv


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除会话")
async def delete_conversation(
    project_id: int,
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    await _require_project(project_id, user_id, db)
    conv = await _require_conversation(conversation_id, project_id, db)
    await ConversationRepository(db).soft_delete(conv)
    await db.commit()


# ---------------------------------------------------------------------------
# 聊天（流式）
# ---------------------------------------------------------------------------

@router.post("/{conversation_id}/chat", summary="发送聊天消息（流式返回）")
async def chat_message(
    project_id: int,
    conversation_id: int,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """发送用户消息，流式返回 AI 回复。

    流程：
      1. 保存用户消息（type=text）
      2. 调用 LLM（流式）
      3. 保存 AI 消息（type=text）
      4. 返回完整 AI 消息记录

    返回格式：text/event-stream
    """
    await _require_project(project_id, user_id, db)
    conv = await _require_conversation(conversation_id, project_id, db)

    if conv.status == "confirmed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="已确认的会话不可继续对话",
        )

    msg_repo = MessageRepository(db)

    # 1. 保存用户消息
    await msg_repo.create_message(
        conversation_id=conversation_id,
        role="user",
        type="text",
        content=body.content,
    )
    await db.commit()

    # 2. 构建消息历史（用于 LLM 上下文）
    messages = await msg_repo.get_by_conversation(conversation_id)
    llm_messages = [
        {"role": m.role, "content": m.content}
        for m in messages
    ]

    # 3. 调用 LLM 流式生成
    async def stream_llm() -> AsyncGenerator[str, None]:
        from app.utils.llm_call import call_llm_stream

        full_response = ""
        async for chunk in call_llm_stream(
            messages=llm_messages,
            llm_config=body.llm_config,
            system_prompt=CHAT_SYSTEM_PROMPT,
        ):
            full_response += chunk
            # 每个 chunk 单独作为一个完整 SSE 事件发送，避免多行 chunk 导致的解析问题
            yield f"data: {chunk}\n\n"

        # 4. 流式结束后，保存 AI 完整回复
        await msg_repo.create_message(
            conversation_id=conversation_id,
            role="assistant",
            type="text",
            content=full_response,
        )
        await db.commit()

        # 发送完成标记
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_llm(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


# ---------------------------------------------------------------------------
# 总结剧本（流式）
# ---------------------------------------------------------------------------

@router.post("/{conversation_id}/summarize", summary="触发剧本总结（流式返回）")
async def summarize_outline(
    project_id: int,
    conversation_id: int,
    body: SummarizeRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """将全部对话总结为剧本大纲（EpisodeOutline JSON）。

    流程：
      1. 构建总结提示词（含全部对话历史）
      2. 调用 LLM 流式生成
      3. 流结束后解析完整 JSON
      4. 保存 outline_draft 消息
      5. 更新 Conversation.latest_outline 和 status=draft_ready
    """
    await _require_project(project_id, user_id, db)
    conv = await _require_conversation(conversation_id, project_id, db)

    msg_repo = MessageRepository(db)

    # 构建消息历史
    messages = await msg_repo.get_by_conversation(conversation_id)
    llm_messages = [
        {"role": m.role, "content": m.content}
        for m in messages
    ]

    # 下一版本号
    next_version = 1
    if conv.latest_outline:
        next_version = conv.latest_outline.get("version", 0) + 1

    async def stream_summarize() -> AsyncGenerator[str, None]:
        from app.utils.llm_call import call_llm_stream, parse_llm_json

        summarize_prompt = SUMMARIZE_SYSTEM_PROMPT + f"\n\n当前是第 {next_version} 次总结。"

        # Gemini 要求最后一条消息必须是 user 角色
        messages_for_summary = llm_messages.copy()
        if not messages_for_summary or messages_for_summary[-1]["role"] != "user":
            messages_for_summary.append({"role": "user", "content": "请根据以上对话内容生成剧本大纲。"})

        full_response = ""
        try:
            async for chunk in call_llm_stream(
                messages=messages_for_summary,
                llm_config=body.llm_config,
                system_prompt=summarize_prompt,
                response_schema=EpisodeOutline,
            ):
                full_response += chunk
                yield f"data: {chunk}\n\n"
        except Exception as e:
            logger.error("LLM summarize error: %s", e)
            yield f"data: [ERROR] LLM 调用失败: {e}\n\n"
            return

        outline_json = parse_llm_json(full_response)
        if outline_json is None:
            logger.error("Failed to parse summarize outline JSON: %s", full_response[:500])
            yield "data: [ERROR] 总结结果不是合法 JSON\n\n"
            return

        outline_json["version"] = next_version
        outline_json["generated_at"] = datetime.now(timezone.utc).isoformat()

        # 保存 outline_draft 消息
        await msg_repo.create_message(
            conversation_id=conversation_id,
            role="assistant",
            type="outline_draft",
            content=f"## 剧本大纲草稿 v{next_version}\n\n**{outline_json.get('title', '未命名')}**\n\n{outline_json.get('synopsis', '')}",
            outline_data=outline_json,
        )

        # 更新 Conversation
        await ConversationRepository(db).update(conv, {
            "status": "draft_ready",
            "latest_outline": outline_json,
        })
        await db.commit()

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_summarize(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )



# ---------------------------------------------------------------------------
# 确认执行（Confirm）：创建 Scene + 触发分镜 Celery 任务
# ---------------------------------------------------------------------------

@router.post(
    "/{conversation_id}/confirm",
    response_model=ConversationConfirmResponse,
    status_code=status.HTTP_201_CREATED,
    summary="确认剧本大纲，创建分集并触发分镜生成",
)
async def confirm_conversation(
    project_id: int,
    conversation_id: int,
    body: ConversationConfirmRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """原子操作：
    1. 检查会话未被确认
    2. 追加 outline_confirmed 消息
    3. 创建 Scene 记录
    4. 更新 Conversation（status=confirmed, scene_id）
    5. 追加 system_action 消息（记录操作）
    6. 创建 GenerationTask 并派发 Celery 任务
    """
    await _require_project(project_id, user_id, db)
    conv = await _require_conversation(conversation_id, project_id, db)

    if conv.status == "confirmed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该会话已确认，请勿重复操作",
        )

    outline = body.outline
    outline_dict = outline.model_dump()

    # 1. 追加 outline_confirmed 消息（用户最终确认的版本）
    msg_repo = MessageRepository(db)
    await msg_repo.create_message(
        conversation_id=conversation_id,
        role="assistant",
        type="outline_confirmed",
        content=f"## 剧本大纲已确认（v{outline.version}）\n\n**{outline.title}**\n\n{outline.synopsis}",
        outline_data=outline_dict,
    )

    # 2. 创建 Scene（episode_code 由后端按项目序号自动生成，格式 P{project_id}_EP{N:03d}）
    scene_repo = SceneRepository(db)
    next_num = await scene_repo.count_by_project(project_id) + 1
    scene_code = f"P{project_id}_EP{next_num:03d}"
    # 极端情况下防重（并发创建时序号可能碰撞）
    while await scene_repo.get_by_code(scene_code):
        next_num += 1
        scene_code = f"P{project_id}_EP{next_num:03d}"

    scene = await scene_repo.create(
        project_id=project_id,
        scene_code=scene_code,
        title=outline.title,
        synopsis=outline.synopsis,
        theme=outline.theme,
        novel_chapter_start=outline.novel_chapter_start,
        novel_chapter_end=outline.novel_chapter_end,
        novel_excerpt=outline.novel_excerpt,
        story_arc=outline.story_arc,
        key_events=[e.model_dump() for e in outline.key_events],
        emotional_arc=outline.emotional_arc,
        characters=outline.characters,
        character_focus=outline.character_focus,
        character_ids=[],
        primary_location=outline.primary_location,
        location_atmosphere=outline.location_atmosphere,
        visual_highlights=[v.model_dump() for v in outline.visual_highlights],
        color_palette=outline.color_palette,
        bgm_direction=outline.bgm_direction,
        storyboard_style_notes=outline.storyboard_style_notes,
        previous_episode_hint=outline.previous_episode_hint,
        next_episode_hint=outline.next_episode_hint,
        scene_types=outline.scene_types,
        priority=outline.priority,
        estimated_duration_sec=outline.estimated_duration_sec,
        status="in_production",
    )

    # 3. 更新 Conversation
    conv_repo = ConversationRepository(db)
    await conv_repo.update(conv, {
        "status": "confirmed",
        "scene_id": scene.id,
        "latest_outline": outline_dict,
    })

    # 4. 追加 system_action 消息（操作记录）
    shot_count = body.shot_count or outline.storyboard_shot_count
    await msg_repo.create_message(
        conversation_id=conversation_id,
        role="system",
        type="system_action",
        content=f"✅ 分集已创建（scene_id={scene.id}），分镜生成任务已启动，计划生成 {shot_count} 个镜头。",
    )

    # 5. 创建 GenerationTask 并派发 Celery（v2 三阶段流水线）
    from app.tasks.storyboard import generate_storyboard_v2_task

    task_repo = TaskRepository(db)
    task = await task_repo.create(
        shot_id=None,
        task_type="storyboard_generation_v2",
        status="pending",
        input_params={
            "scene_id": scene.id,
            "shot_count": shot_count,
            "style_notes": outline.storyboard_style_notes,
            "novel_excerpt": outline.novel_excerpt,
            "llm_config": body.llm_config.model_dump(),
        },
    )

    await db.commit()

    # commit 之后再派发，确保 task.id 已落库
    celery_result = generate_storyboard_v2_task.delay(task.id)
    await task_repo.update(task, {"celery_task_id": celery_result.id})
    await db.commit()

    return ConversationConfirmResponse(
        scene_id=scene.id,
        task_id=task.id,
        celery_task_id=celery_result.id,
    )
