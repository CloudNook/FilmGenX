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
from typing import List, Optional

from pydantic import BaseModel, Field

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 结构化输出 Schema（传给 Gemini response_schema）
# ---------------------------------------------------------------------------

class CameraConfig(BaseModel):
    shot_type: str = Field(description="景别：ECS/ECU/CU/MCU/MS/MLS/LS/ELS")
    angle: str = Field(description="机位角度：eye_level/low_angle/high_angle/dutch/bird_eye")
    movement: str = Field(description="运镜方式：static/pan/tilt/dolly/zoom/handheld/crane")
    focal_length: Optional[str] = None
    depth_of_field: Optional[str] = None


class CompositionConfig(BaseModel):
    subject_position: str
    foreground: Optional[str] = None
    background: Optional[str] = None


class EmotionPoint(BaseModel):
    time_sec: float
    intensity: int = Field(ge=1, le=10)
    label: str


class PacingRatio(BaseModel):
    buildup: int = Field(ge=0, le=100)
    climax: int = Field(ge=0, le=100)
    resolution: int = Field(ge=0, le=100)


class ShotSchema(BaseModel):
    sequence: int
    shot_code: str = Field(description="格式：{scene_code}_S001")
    duration_sec: float = Field(ge=0.5, le=30.0)
    camera: CameraConfig
    composition: CompositionConfig
    character_action: str
    character_expression: Optional[str] = None
    character_emotion_intensity: Optional[int] = Field(None, ge=1, le=10)
    dialogue_text: Optional[str] = None
    transition_in: str = Field(default="cut", description="cut/fade/dissolve/wipe")
    transition_out: str = Field(default="cut")
    image_prompt: str = Field(description="英文图像生成提示词")
    negative_prompt: Optional[str] = None


class StoryboardSchema(BaseModel):
    narrative_notes: str
    pacing_ratio: PacingRatio
    emotion_curve: List[EmotionPoint]
    shots: List[ShotSchema]


from app.prompts import STORYBOARD_SYSTEM_PROMPT


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
            from app.utils.llm_call import call_llm
            req = _build_storyboard_request(scene, shot_count, style_notes)
            effective_system = (system_prompt or "").strip() or STORYBOARD_SYSTEM_PROMPT
            effective_llm_config = llm_config or {"model": "gemini-2.0-flash"}
            raw = await call_llm(
                messages=[{"role": "user", "content": req.to_prompt()}],
                llm_config=effective_llm_config,
                system_prompt=effective_system,
                response_schema=StoryboardSchema,
            )
            data = json.loads(raw)

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
            from app.models.shot import Shot as ShotModel
            _shot_columns = {c.key for c in ShotModel.__table__.columns}

            shot_repo = ShotRepository(session)
            for shot_data in data.get("shots", []):
                safe = {
                    k: v for k, v in shot_data.items()
                    if v is not None and k in _shot_columns
                }
                await shot_repo.create(storyboard_id=storyboard.id, **safe)

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


class StoryboardRequest(BaseModel):
    """传给 LLM 的分镜生成请求，结构化表示所有输入信息。"""
    scene_code: str
    title: str
    scene_types: List[str]
    novel_chapter_start: Optional[str]
    novel_chapter_end: Optional[str]
    novel_excerpt: Optional[str]
    shot_count: int
    style_notes: Optional[str]

    def to_prompt(self) -> str:
        lines = [
            f"片段标题：{self.title}",
            f"scene_code：{self.scene_code}",
            f"类型：{', '.join(self.scene_types)}",
            f"章节范围：{self.novel_chapter_start or '未知'} — {self.novel_chapter_end or '未知'}",
        ]
        if self.novel_excerpt:
            lines.append(f"\n原著摘录：\n{self.novel_excerpt}")
        lines.append(f"\n请生成 {self.shot_count} 个镜头的分镜脚本。")
        if self.style_notes:
            lines.append(f"风格要求：{self.style_notes}")
        return "\n".join(lines)


def _build_storyboard_request(scene, shot_count: int, style_notes: str) -> StoryboardRequest:
    return StoryboardRequest(
        scene_code=scene.scene_code,
        title=scene.title,
        scene_types=scene.scene_types or [],
        novel_chapter_start=scene.novel_chapter_start,
        novel_chapter_end=scene.novel_chapter_end,
        novel_excerpt=scene.novel_excerpt,
        shot_count=shot_count,
        style_notes=style_notes or None,
    )
