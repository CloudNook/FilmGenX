"""
对话会话（Conversation）API 端点。

路由前缀：/api/v1/projects/{project_id}/conversations

每个 Conversation 对应一集动画的完整创作对话：
  - 消息逐条持久化
  - 支持多次总结（outline_draft 消息）
  - 确认后创建 Scene 并触发分镜 Celery 任务
"""

from datetime import datetime, timezone
from typing import AsyncGenerator

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


# ---------------------------------------------------------------------------
# 请求 Schema（新增）
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """发送聊天消息请求。"""
    content: str = Field(..., description="用户消息内容")
    llm_config: dict = Field(..., description="LLM 配置，包含 provider/model/api_key/temperature 等")
    system_prompt: str = Field("", description="可选的系统提示词覆盖")


class SummarizeRequest(BaseModel):
    """触发剧本总结请求。"""
    llm_config: dict = Field(..., description="LLM 配置")
    system_prompt: str = Field("", description="总结提示词模板（可选覆盖）")


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
            system_prompt=body.system_prompt,
        ):
            full_response += chunk
            # SSE 格式：data: <chunk>\n\n
            yield f"data: {chunk}\n\n"

        # 4. 流式结束后，保存 AI 完整回复
        await msg_repo.create_message(
            conversation_id=conversation_id,
            role="assistant",
            type="text",
            content=full_response,
        )
        await db.commit()

        # 发送完成标记（让前端知道流式结束）
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
      3. 解析 <outline>...</outline> 中的 JSON
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
    import json
    next_version = 1
    if conv.latest_outline:
        next_version = conv.latest_outline.get("version", 0) + 1

    async def stream_summarize() -> AsyncGenerator[str, None]:
        from app.utils.llm_call import call_llm_stream

        # 构建总结提示词
        summarize_prompt = body.system_prompt.strip() or _get_default_summarize_prompt()
        summarize_prompt += f"\n\n当前是第 {next_version} 次总结。"

        full_response = ""
        async for chunk in call_llm_stream(
            messages=llm_messages,
            llm_config=body.llm_config,
            system_prompt=summarize_prompt,
        ):
            full_response += chunk
            yield f"data: {chunk}\n\n"

        # 解析 <outline>...</outline> 中的 JSON
        import re
        match = re.search(r"<outline>(.*?)</outline>", full_response, re.DOTALL)
        if not match:
            # 尝试直接解析整个响应为 JSON
            try:
                outline_json = json.loads(full_response)
            except json.JSONDecodeError:
                yield f"data: [ERROR] 无法解析剧本大纲 JSON\n\n"
                return
        else:
            outline_json = json.loads(match.group(1))

        # 更新 version
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


def _get_default_summarize_prompt() -> str:
    return """你是一名动漫制片总监助手。

根据以下对话内容（包括此前生成的所有大纲草稿和用户的修改意见），
生成一份最新的剧本大纲。

输出格式：
1. 先用1-2句话说明这次相比上一版的主要变化（若是第一版则跳过）
2. 输出 <outline> 标签包裹的 JSON，格式如下：

<outline>
{
  "title": "本集标题",
  "episode_code": "项目前缀_EP序号",
  "synopsis": "100-300字的本集剧情概述",
  "theme": "一句话核心主题",
  "novel_chapter_start": "起始章节",
  "novel_chapter_end": "结束章节",
  "novel_excerpt": "关键原著摘录，1-3段，用\\\\n\\\\n分隔",
  "scene_types": ["emotional_peak", "character_introduction"],
  "priority": "S",
  "estimated_duration_sec": 120,
  "scores": {
    "dramatic_tension": 9,
    "visual_potential": 8,
    "emotional_resonance": 10,
    "narrative_importance": 9,
    "audience_familiarity": 8
  },
  "characters": ["萧炎", "药老"],
  "storyboard_style_notes": "给分镜导演的具体风格指导...",
  "storyboard_shot_count": 10,
  "version": 2
}
</outline>

注意：
- version 会自动填充，无需在 JSON 中指定
- storyboard_style_notes 要具体，包括色调、运镜风格、特效建议
- 充分吸收用户在对话中提出的所有修改意见"""


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

    # 2. 创建 Scene
    scene_repo = SceneRepository(db)
    if await scene_repo.get_by_code(outline.episode_code):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"episode_code '{outline.episode_code}' 已存在，请修改后重试",
        )

    scores = outline.scores
    score_total = (
        scores.dramatic_tension
        + scores.visual_potential
        + scores.emotional_resonance
        + scores.narrative_importance
        + scores.audience_familiarity
    )
    scene = await scene_repo.create(
        project_id=project_id,
        scene_code=outline.episode_code,
        title=outline.title,
        novel_chapter_start=outline.novel_chapter_start,
        novel_chapter_end=outline.novel_chapter_end,
        novel_excerpt=outline.novel_excerpt,
        scene_types=outline.scene_types,
        priority=outline.priority,
        estimated_duration_sec=outline.estimated_duration_sec,
        score_dramatic_tension=scores.dramatic_tension,
        score_visual_potential=scores.visual_potential,
        score_emotional_resonance=scores.emotional_resonance,
        score_narrative_importance=scores.narrative_importance,
        score_audience_familiarity=scores.audience_familiarity,
        score_total=score_total,
        character_ids=[],
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

    # 5. 创建 GenerationTask 并派发 Celery
    from app.tasks.storyboard import generate_storyboard_task

    task_repo = TaskRepository(db)
    task = await task_repo.create(
        shot_id=None,
        task_type="storyboard_generation",
        status="pending",
        input_params={
            "scene_id": scene.id,
            "shot_count": shot_count,
            "style_notes": outline.storyboard_style_notes,
            "novel_excerpt": outline.novel_excerpt,
            "llm_config": body.llm_config.model_dump(),
            "system_prompt": body.system_prompt,
        },
    )

    await db.commit()

    # commit 之后再派发，确保 task.id 已落库
    celery_result = generate_storyboard_task.delay(task.id)
    await task_repo.update(task, {"celery_task_id": celery_result.id})
    await db.commit()

    return ConversationConfirmResponse(
        scene_id=scene.id,
        task_id=task.id,
        celery_task_id=celery_result.id,
    )
