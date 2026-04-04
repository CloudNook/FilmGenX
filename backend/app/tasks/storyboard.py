"""
分镜脚本 AI 生成 Celery 任务。

流程：
  1. 加载 Scene 信息（含原著摘录、角色列表）
  2. 调用 Google Gemini 生成结构化分镜 JSON
  3. 解析 JSON，批量创建 Storyboard + Shot 记录
  4. 更新 Scene 状态为 in_production
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# 分镜生成系统提示词（固定模板）
_SYSTEM_PROMPT = """你是一名专业的动漫分镜导演，擅长将小说文本转化为精确的分镜脚本。

输出格式要求：
- 严格输出 JSON，不要任何多余的说明文字
- JSON 结构如下：
{
  "narrative_notes": "叙事设计备注",
  "pacing_ratio": {"buildup": 30, "climax": 50, "resolution": 20},
  "emotion_curve": [
    {"time_sec": 0, "intensity": 3, "label": "压抑开场"},
    {"time_sec": 8, "intensity": 8, "label": "战斗爆发"},
    {"time_sec": 15, "intensity": 10, "label": "最强一击"}
  ],
  "shots": [
    {
      "sequence": 1,
      "shot_code": "{scene_code}_S001",
      "duration_sec": 3.0,
      "camera": {
        "shot_type": "LS",
        "angle": "low_angle",
        "movement": "dolly",
        "focal_length": "24mm 广角",
        "depth_of_field": "深景深，全景清晰"
      },
      "composition": {
        "subject_position": "画面中央",
        "foreground": "碎石瓦砾",
        "background": "烟雾弥漫的擂台"
      },
      "character_action": "萧炎单膝跪地，缓缓抬头",
      "character_expression": "坚毅，不服输",
      "character_emotion_intensity": 7,
      "dialogue_text": null,
      "transition_in": "cut",
      "transition_out": "cut",
      "image_prompt": "xiao yan kneeling on arena, dust and smoke, low angle, wide shot, determination in eyes, anime style, high quality",
      "negative_prompt": "blurry, low quality, watermark"
    }
  ]
}
"""


@celery_app.task(
    name="app.tasks.storyboard.generate_storyboard_task",
    max_retries=2,
    default_retry_delay=30,
    queue="default",
)
def generate_storyboard_task(task_db_id: int) -> dict:
    """分镜脚本生成任务入口。

    Args:
        task_db_id: GenerationTask 的数据库 ID。
    """
    return asyncio.get_event_loop().run_until_complete(
        _run_storyboard_generation(task_db_id)
    )


async def _run_storyboard_generation(task_db_id: int) -> dict:
    """分镜生成异步核心逻辑。"""
    from app.db.session import AsyncSessionFactory
    from app.repositories.scene import SceneRepository
    from app.repositories.shot import ShotRepository
    from app.repositories.storyboard import StoryboardRepository
    from app.repositories.task import TaskRepository

    async with AsyncSessionFactory() as session:
        task_repo = TaskRepository(session)
        gen_task = await task_repo.get(task_db_id)
        if not gen_task:
            return {"status": "failed", "error": "任务记录不存在"}

        await task_repo.update(gen_task, {
            "status": "running",
            "started_at": datetime.now(timezone.utc),
        })
        await session.commit()

        try:
            params = gen_task.input_params or {}
            scene_id = params.get("scene_id")
            shot_count = params.get("shot_count", 6)
            style_notes = params.get("style_notes", "")
            llm_config = params.get("llm_config")       # 动态 LLM 配置（可选）
            system_prompt = params.get("system_prompt") # 用户自定义系统提示词（可选）

            scene = await SceneRepository(session).get(scene_id)
            if not scene:
                raise ValueError(f"Scene {scene_id} 不存在")

            # 构建 AI 请求
            user_prompt = _build_user_prompt(scene, shot_count, style_notes)
            ai_response = await _call_gemini(
                user_prompt,
                llm_config=llm_config,
                system_prompt_override=system_prompt,
            )
            data = json.loads(ai_response)

            # 创建分镜脚本
            sb_repo = StoryboardRepository(session)
            storyboard = await sb_repo.create(
                scene_id=scene_id,
                narrative_notes=data.get("narrative_notes"),
                pacing_ratio=data.get("pacing_ratio"),
                emotion_curve=data.get("emotion_curve"),
                status="review",
            )

            # 批量创建镜头
            shot_repo = ShotRepository(session)
            for shot_data in data.get("shots", []):
                await shot_repo.create(
                    storyboard_id=storyboard.id,
                    **{k: v for k, v in shot_data.items() if v is not None},
                )

            # 更新总时长
            total_dur = sum(s.get("duration_sec", 3.0) for s in data.get("shots", []))
            await sb_repo.update(storyboard, {"total_duration_sec": total_dur})

            # 更新片段状态
            await SceneRepository(session).update(scene, {"status": "in_production"})

            await task_repo.update(gen_task, {
                "status": "success",
                "progress": 100,
                "completed_at": datetime.now(timezone.utc),
            })
            await session.commit()

            logger.info("分镜生成完成：scene=%s storyboard_id=%d shots=%d",
                        scene.scene_code, storyboard.id, len(data.get("shots", [])))
            return {"status": "success", "storyboard_id": storyboard.id}

        except Exception as exc:
            logger.exception("分镜生成失败：task_id=%d error=%s", task_db_id, exc)
            await task_repo.update(gen_task, {
                "status": "failed",
                "error_message": str(exc),
                "completed_at": datetime.now(timezone.utc),
            })
            await session.commit()
            return {"status": "failed", "error": str(exc)}


def _build_user_prompt(scene, shot_count: int, style_notes: str) -> str:
    """根据 Scene 信息构建发给 AI 的用户提示词。"""
    lines = [
        f"片段标题：{scene.title}",
        f"类型：{', '.join(scene.scene_types)}",
        f"章节范围：{scene.novel_chapter_start or '未知'} — {scene.novel_chapter_end or '未知'}",
    ]
    if scene.novel_excerpt:
        lines.append(f"\n原著摘录：\n{scene.novel_excerpt}")
    lines.append(f"\n请生成 {shot_count} 个镜头的分镜脚本，scene_code 为 {scene.scene_code}。")
    if style_notes:
        lines.append(f"风格要求：{style_notes}")
    return "\n".join(lines)


async def _call_gemini(
    user_prompt: str,
    llm_config: dict | None = None,
    system_prompt_override: str | None = None,
) -> str:
    """调用 LLM API 生成分镜 JSON。

    优先使用调用方传入的 llm_config（动态配置），
    若未传则回退到环境变量中的 Google API Key + 默认模型。

    Args:
        user_prompt:           用户侧提示词（场景信息）。
        llm_config:            前端传来的 LLM 配置字典，包含
                               provider / model / api_key / temperature 等。
        system_prompt_override: 用户自定义的系统提示词，覆盖内置 _SYSTEM_PROMPT。
    """
    from google import genai
    from google.genai import types
    from app.core.config import settings

    system_prompt = system_prompt_override.strip() if system_prompt_override else _SYSTEM_PROMPT

    # 解析动态配置
    if llm_config:
        api_key = llm_config.get("api_key") or settings.GOOGLE_API_KEY
        model = llm_config.get("model", "gemini-2.0-flash")
        temperature = llm_config.get("temperature")
    else:
        api_key = settings.GOOGLE_API_KEY
        model = "gemini-2.0-flash"
        temperature = None

    client = genai.Client(api_key=api_key)

    gen_config_kwargs: dict = {"response_mime_type": "application/json"}
    if temperature is not None:
        gen_config_kwargs["temperature"] = temperature

    response = await client.aio.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            **gen_config_kwargs,
        ),
    )
    return response.text
