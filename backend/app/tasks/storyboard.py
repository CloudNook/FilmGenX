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
    subject_position: str = Field(description="主体位置，如 center/left_third/right_third")
    foreground: Optional[str] = Field(None, description="前景元素描述")
    midground: Optional[str] = Field(None, description="中景元素描述")
    background: Optional[str] = Field(None, description="背景元素描述")
    leading_lines: Optional[str] = Field(None, description="引导线方向，如 diagonal_left/converging/horizontal")


class EnvironmentConfig(BaseModel):
    """场景环境配置。"""
    time_of_day: str = Field(description="时间段：dawn/morning/noon/afternoon/sunset/dusk/night")
    weather: Optional[str] = Field(None, description="天气：clear/cloudy/rain/storm/snow/fog")
    lighting: str = Field(description="光照描述，如'暖色调逆光'、'冷色调侧光'")
    atmosphere: str = Field(description="氛围描述，如'压抑肃杀'、'热烈激昂'、'宁静祥和'")


class DialogueDeliverySchema(BaseModel):
    """台词演绎参数。"""
    tone: str = Field(description="语气，如'坚定'、'愤怒'、'悲伤'、'调侃'")
    pace: str = Field(description="语速，如'缓慢'、'正常'、'快速'、'渐快'")
    pause_positions: Optional[str] = Field(None, description="停顿位置描述，如'第2句后停顿1秒'")
    emphasis_words: Optional[str] = Field(None, description="重音/强调的词语")
    emotion_tags: Optional[List[str]] = Field(None, description="情感标签，如['愤怒','决绝']")


class SoundDesignSchema(BaseModel):
    """音效设计。"""
    ambient: str = Field(description="环境音描述，如'风声、远处爆炸声'")
    sfx_list: Optional[List[str]] = Field(None, description="具体音效列表，如['火焰燃烧声','金属碰撞声','地面碎裂声']")
    music: Optional[str] = Field(None, description="背景音乐描述，如'激昂鼓点渐入'、'空灵琴音'")


class DependencySchema(BaseModel):
    """镜头依赖关系。"""
    type: str = Field(description="依赖类型：character_continuity/prop_continuity/lighting_match/camera_match")
    depends_on_shot_id: Optional[int] = Field(None, description="依赖的镜头序号（sequence）")
    dependency_detail: Optional[str] = Field(None, description="依赖详情说明")


class EmotionPoint(BaseModel):
    time_sec: float
    intensity: int = Field(ge=1, le=10)
    label: str


class PacingRatio(BaseModel):
    buildup: int = Field(ge=0, le=100)
    climax: int = Field(ge=0, le=100)
    resolution: int = Field(ge=0, le=100)


class CharacterInShotSchema(BaseModel):
    """镜头中的单个角色配置。"""
    action: str = Field(description="角色动作描述，如'右手握拳高举，斗气火焰缠绕'")
    expression: Optional[str] = Field(None, description="角色表情描述，如'怒目圆睁，嘴角紧抿'")
    emotion_intensity: Optional[int] = Field(None, ge=1, le=10, description="情绪强度 1-10")


class ShotSchema(BaseModel):
    sequence: int
    shot_code: str = Field(description="格式：{scene_code}_S001")
    duration_sec: int = Field(ge=1, le=15)
    camera: CameraConfig
    composition: CompositionConfig
    environment: EnvironmentConfig = Field(description="场景环境配置")

    # 角色配置
    characters_config: Optional[List[CharacterInShotSchema]] = Field(
        None, description="镜头中各角色的动作/表情/情绪配置，1-3个角色"
    )

    # 台词
    dialogue_character: Optional[str] = Field(None, description="说话角色名")
    dialogue_text: Optional[str] = Field(None, description="台词内容（中文）")
    dialogue_delivery: Optional[DialogueDeliverySchema] = Field(None, description="台词演绎参数")

    # 音效
    sound_design: Optional[SoundDesignSchema] = Field(None, description="音效设计方案")

    # 转场
    transition_in: str = Field(default="cut", description="入场转场：cut/fade/dissolve/wipe/smash")
    transition_out: str = Field(default="cut", description="出场转场：cut/fade/dissolve/wipe/smash")
    transition_notes: Optional[str] = Field(None, description="转场备注说明")

    # 镜头依赖
    dependencies: Optional[List[DependencySchema]] = Field(None, description="与其他镜头的依赖关系")

    # 生成提示词
    image_prompt: str = Field(description="英文图像生成提示词，包含 anime style, high quality, dynamic lighting")
    negative_prompt: Optional[str] = Field(None, description="英文负面提示词")
    style_preset: Optional[str] = Field(None, description="风格预设，如 cinematic/dramatic/ethereal/intense")

    # 分镜组
    group_code: Optional[str] = Field(
        None, description="所属分镜组编号（如 G001），NULL 表示独立分镜"
    )


class ShotGroupSchema(BaseModel):
    """分镜组定义。"""
    group_code: str = Field(description="组编号，如 G001、G002")
    name: Optional[str] = Field(None, description="组名称，如'快节奏战斗连段'")
    shot_sequences: List[int] = Field(
        description="组内分镜的 sequence 列表（按顺序）。最多 6 个，总时长 ≤ 15 秒"
    )


class StoryboardSchema(BaseModel):
    narrative_notes: str
    pacing_ratio: PacingRatio
    emotion_curve: List[EmotionPoint]
    shots: List[ShotSchema]
    shot_groups: Optional[List[ShotGroupSchema]] = Field(
        None, description="分镜组定义。每组 2-6 个镜头，总时长 ≤ 15 秒"
    )


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
    # 每次执行都创建新的事件循环，避免重试时 "Event loop is closed" 错误
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_storyboard_generation(task_db_id))
    finally:
        loop.close()


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
            created_shots = {}  # sequence → shot
            for shot_data in data.get("shots", []):
                safe = {
                    k: v for k, v in shot_data.items()
                    if v is not None and k in _shot_columns
                }
                # 确保 char_version_ids 有默认值
                if "char_version_ids" not in safe:
                    safe["char_version_ids"] = []
                shot = await shot_repo.create(storyboard_id=storyboard.id, **safe)
                created_shots[shot_data["sequence"]] = shot

            # 创建分镜组
            groups_data = data.get("shot_groups") or []
            if groups_data:
                from app.repositories.shot_group import ShotGroupRepository
                group_repo = ShotGroupRepository(session)
                for idx, g_data in enumerate(groups_data):
                    member_sequences = g_data.get("shot_sequences", [])
                    member_shots = [created_shots[seq] for seq in member_sequences if seq in created_shots]

                    if len(member_shots) < 2:
                        logger.warning("跳过分镜组 %s：成员不足 2 个", g_data.get("group_code"))
                        continue

                    total_dur = sum(s.duration_sec or 3.0 for s in member_shots)
                    group = await group_repo.create(
                        storyboard_id=storyboard.id,
                        group_code=g_data["group_code"],
                        name=g_data.get("name"),
                        sequence=idx + 1,
                        total_duration_sec=total_dur,
                    )
                    # 绑定成员分镜
                    for shot in member_shots:
                        await shot_repo.update(shot, {"shot_group_id": group.id})

                logger.info("创建了 %d 个分镜组", len(groups_data))

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
    synopsis: Optional[str] = None
    story_arc: Optional[str] = None
    key_events: Optional[list] = None
    emotional_arc: Optional[str] = None
    characters: Optional[List[str]] = None
    primary_location: Optional[str] = None
    location_atmosphere: Optional[str] = None
    visual_highlights: Optional[list] = None
    color_palette: Optional[str] = None
    scene_types: List[str] = []
    novel_chapter_start: Optional[str] = None
    novel_chapter_end: Optional[str] = None
    novel_excerpt: Optional[str] = None
    shot_count: int = 6
    style_notes: Optional[str] = None

    def to_prompt(self) -> str:
        lines = [
            f"片段标题：{self.title}",
            f"scene_code：{self.scene_code}",
        ]
        if self.synopsis:
            lines.append(f"剧情概述：{self.synopsis}")
        if self.story_arc:
            lines.append(f"叙事弧：{self.story_arc}")
        if self.key_events:
            events = [f"  {i+1}. {e}" for i, e in enumerate(self.key_events)]
            lines.append(f"关键事件：\n" + "\n".join(events))
        if self.emotional_arc:
            lines.append(f"情绪走势：{self.emotional_arc}")
        if self.characters:
            lines.append(f"涉及角色：{', '.join(self.characters)}")
        if self.primary_location:
            lines.append(f"主要地点：{self.primary_location}")
        if self.location_atmosphere:
            lines.append(f"场景氛围：{self.location_atmosphere}")
        if self.color_palette:
            lines.append(f"主色调：{self.color_palette}")
        if self.scene_types:
            lines.append(f"类型：{', '.join(self.scene_types)}")
        if self.novel_chapter_start:
            lines.append(f"章节范围：{self.novel_chapter_start} — {self.novel_chapter_end or '未知'}")
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
        synopsis=getattr(scene, 'synopsis', None),
        story_arc=getattr(scene, 'story_arc', None),
        key_events=getattr(scene, 'key_events', None),
        emotional_arc=getattr(scene, 'emotional_arc', None),
        characters=getattr(scene, 'characters', None),
        primary_location=getattr(scene, 'primary_location', None),
        location_atmosphere=getattr(scene, 'location_atmosphere', None),
        visual_highlights=getattr(scene, 'visual_highlights', None),
        color_palette=getattr(scene, 'color_palette', None),
        scene_types=scene.scene_types or [],
        novel_chapter_start=scene.novel_chapter_start,
        novel_chapter_end=scene.novel_chapter_end,
        novel_excerpt=scene.novel_excerpt,
        shot_count=shot_count,
        style_notes=style_notes or None,
    )


# ===========================================================================
# 三阶段分镜生成 v2（规划师 → 创作师并行 → 导演）
# ===========================================================================

@celery_app.task(
    name="app.tasks.storyboard.generate_storyboard_v2_task",
    max_retries=2,
    default_retry_delay=30,
    queue="default",
)
def generate_storyboard_v2_task(task_db_id: int) -> dict:
    """三阶段分镜脚本生成任务入口（v2）。

    Phase 1：规划师 AI 输出分组蓝图
    Phase 2：每组创作师 AI 并行生成具体镜头
    Phase 3：导演 AI 全局微调（仅输出 patch）
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_storyboard_generation_v2(task_db_id))
    finally:
        loop.close()


async def _run_storyboard_generation_v2(task_db_id: int) -> dict:
    """三阶段分镜生成异步核心逻辑。"""
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
            llm_config = params.get("llm_config") or {"model": "gemini-2.0-flash"}
            system_prompt = params.get("system_prompt", "")

            scene = await SceneRepository(session).get(scene_id)
            if not scene:
                raise ValueError(f"Scene {scene_id} 不存在")

            # 创建 Storyboard 记录（status=generating）
            sb_repo = StoryboardRepository(session)
            storyboard = await sb_repo.create(
                scene_id=scene_id,
                status="generating",
                generation_phase="phase1_planning",
            )
            await session.commit()

            # ── Phase 1：规划师 AI ──────────────────────────────────────────
            logger.info("v2 Phase 1 开始：scene=%s shot_count=%d", scene.scene_code, shot_count)
            groups = await _phase1_plan_groups(
                scene=scene,
                storyboard=storyboard,
                shot_count=shot_count,
                style_notes=style_notes,
                llm_config=llm_config,
                system_prompt=system_prompt,
                session=session,
            )

            # ── Phase 2：创作师 AI（并行）──────────────────────────────────
            logger.info("v2 Phase 2 开始：%d 个分镜组并行创作", len(groups))
            await sb_repo.update(storyboard, {"generation_phase": "phase2_creating"})
            await session.commit()

            results = await asyncio.gather(
                *[
                    _phase2_create_shots_for_group(
                        scene=scene,
                        storyboard=storyboard,
                        group_plan=g,
                        llm_config=llm_config,
                        system_prompt=system_prompt,
                    )
                    for g in groups
                ],
                return_exceptions=True,
            )

            success_count = 0
            for g, result in zip(groups, results):
                if isinstance(result, Exception):
                    logger.warning(
                        "v2 Phase 2 分镜组 %s 创作失败（跳过）：%s",
                        g.get("group_code"), result
                    )
                else:
                    success_count += 1

            logger.info("v2 Phase 2 完成：%d/%d 组成功", success_count, len(groups))

            # ── Phase 3：导演 AI 全局微调 ──────────────────────────────────
            await sb_repo.update(storyboard, {"generation_phase": "phase3_directing"})
            await session.commit()

            # 重新加载所有 shots（按 sequence 排序）
            shot_repo = ShotRepository(session)
            all_shots = await shot_repo.get_by_storyboard(storyboard.id)

            if all_shots:
                logger.info("v2 Phase 3 开始：对 %d 个镜头进行全局调度", len(all_shots))
                await _phase3_director_adjust(
                    scene=scene,
                    storyboard=storyboard,
                    all_shots=all_shots,
                    llm_config=llm_config,
                    system_prompt=system_prompt,
                    session=session,
                )
            else:
                logger.warning("v2 Phase 3 跳过：没有成功生成的镜头")

            # ── 收尾 ────────────────────────────────────────────────────────
            total_dur = sum(s.duration_sec or 3.0 for s in all_shots)
            await sb_repo.update(storyboard, {
                "total_duration_sec": total_dur,
                "status": "review",
                "generation_phase": "completed",
            })

            await SceneRepository(session).update(scene, {"status": "in_production"})

            await task_repo.update(gen_task, {
                "status": "success",
                "progress": 100,
                "completed_at": datetime.now(timezone.utc),
            })
            await session.commit()

            logger.info(
                "v2 分镜生成完成：scene=%s storyboard_id=%d shots=%d",
                scene.scene_code, storyboard.id, len(all_shots)
            )
            return {"status": "success", "storyboard_id": storyboard.id}

        except Exception as exc:
            logger.exception("v2 分镜生成失败：task_id=%d error=%s", task_db_id, exc)
            await task_repo.update(gen_task, {
                "status": "failed",
                "error_message": str(exc),
                "completed_at": datetime.now(timezone.utc),
            })
            await session.commit()
            return {"status": "failed", "error": str(exc)}


async def _phase1_plan_groups(
    scene,
    storyboard,
    shot_count: int,
    style_notes: str,
    llm_config: dict,
    system_prompt: str,
    session,
) -> list:
    """Phase 1：规划师 AI 输出分组蓝图，返回 group_plan dict 列表。"""
    from app.utils.llm_call import call_llm
    from app.repositories.storyboard import StoryboardRepository
    from app.prompts import STORYBOARD_PLANNER_PROMPT, ShotGroupPlanSchema

    req = _build_storyboard_request(scene, shot_count, style_notes)
    user_msg = req.to_prompt() + f"\n\n请将 {shot_count} 个镜头分成若干组，输出分组规划蓝图。"
    effective_system = system_prompt or STORYBOARD_PLANNER_PROMPT

    logger.info("=" * 60)
    logger.info("[Phase 1 规划师] SYSTEM PROMPT:\n%s", effective_system)
    logger.info("-" * 60)
    logger.info("[Phase 1 规划师] USER MESSAGE:\n%s", user_msg)
    logger.info("=" * 60)

    raw = await call_llm(
        messages=[{"role": "user", "content": user_msg}],
        llm_config=llm_config,
        system_prompt=effective_system,
        response_schema=ShotGroupPlanSchema,
    )

    logger.info("-" * 60)
    logger.info("[Phase 1 规划师] AI RAW RESPONSE (%d chars):\n%s", len(raw), raw)
    logger.info("=" * 60)

    data = json.loads(raw)

    # 验证序号连续性
    groups = data.get("groups", [])
    if not groups:
        raise ValueError("Phase 1 规划师 AI 未返回任何分镜组")

    expected_seq = 1
    for g in groups:
        if g.get("sequence_start") != expected_seq:
            raise ValueError(
                f"分镜组 {g.get('group_code')} sequence_start={g.get('sequence_start')} "
                f"期望 {expected_seq}，规划师 AI 输出了不连续的序号"
            )
        expected_seq = g.get("sequence_end", 0) + 1

    # 将 Phase 1 结果持久化到 Storyboard
    sb_repo = StoryboardRepository(session)
    await sb_repo.update(storyboard, {
        "generation_phase": "phase1_planning",
        "plan_data": data,
        "narrative_notes": data.get("narrative_notes"),
        "pacing_ratio": data.get("pacing_ratio"),
        "emotion_curve": data.get("emotion_curve"),
    })
    await session.commit()

    logger.info("Phase 1 完成：%d 个分镜组规划完毕，storyboard_id=%d", len(groups), storyboard.id)
    return groups


async def _phase2_create_shots_for_group(
    scene,
    storyboard,
    group_plan: dict,
    llm_config: dict,
    system_prompt: str,
) -> list:
    """Phase 2：创作师 AI 为单个分镜组生成具体镜头，使用独立 Session。"""
    from app.db.session import AsyncSessionFactory
    from app.utils.llm_call import call_llm
    from app.repositories.shot import ShotRepository
    from app.repositories.shot_group import ShotGroupRepository
    from app.models.shot import Shot as ShotModel
    from app.prompts import STORYBOARD_CREATOR_PROMPT, GroupShotDraftSchema

    group_code = group_plan.get("group_code", "G???")
    seq_start = group_plan.get("sequence_start", 1)
    seq_end = group_plan.get("sequence_end", 1)
    is_action = group_plan.get("is_action_group", False)

    req = _build_storyboard_request(scene, group_plan.get("shot_count", 2), "")
    group_context = (
        f"\n\n## 本次创作任务\n"
        f"你被分配创作分镜组：{group_code} — {group_plan.get('name', '')}\n"
        f"戏剧功能：{group_plan.get('dramatic_function', '')}\n"
        f"叙事意图：{group_plan.get('narrative_intent', '')}\n"
        f"镜头数量：{group_plan.get('shot_count', 2)} 个\n"
        f"全局序号范围：{seq_start} 到 {seq_end}\n"
        f"节奏类型：{'快切动作组（duration_sec 限制 1-3 秒，优先 cut/smash 转场）' if is_action else '情感铺垫组（duration_sec 建议 3-6 秒，可用 dissolve/fade 转场）'}\n"
        f"必须覆盖的视觉时刻：\n"
        + "\n".join(f"  - {m}" for m in group_plan.get("key_visual_moments", []))
        + f"\n\n请仅生成序号 {seq_start}-{seq_end} 的镜头，group_code 统一填写 {group_code}。"
    )

    user_msg = req.to_prompt() + group_context
    effective_system = system_prompt or STORYBOARD_CREATOR_PROMPT

    logger.info("=" * 60)
    logger.info("[Phase 2 创作师 %s] SYSTEM PROMPT:\n%s", group_code, effective_system)
    logger.info("-" * 60)
    logger.info("[Phase 2 创作师 %s] USER MESSAGE:\n%s", group_code, user_msg)
    logger.info("=" * 60)

    raw = await call_llm(
        messages=[{"role": "user", "content": user_msg}],
        llm_config=llm_config,
        system_prompt=effective_system,
        response_schema=GroupShotDraftSchema,
    )

    logger.info("-" * 60)
    logger.info("[Phase 2 创作师 %s] AI RAW RESPONSE (%d chars):\n%s", group_code, len(raw), raw)
    logger.info("=" * 60)

    data = json.loads(raw)
    shots_data = data.get("shots", [])

    # 验证序号范围
    for s in shots_data:
        seq = s.get("sequence", 0)
        if not (seq_start <= seq <= seq_end):
            raise ValueError(
                f"分镜组 {group_code}：镜头 sequence={seq} 超出分配范围 [{seq_start}, {seq_end}]"
            )

    _shot_columns = {c.key for c in ShotModel.__table__.columns}

    # 每个 Phase 2 调用使用独立 Session，避免并发冲突
    async with AsyncSessionFactory() as own_session:
        shot_repo = ShotRepository(own_session)
        group_repo = ShotGroupRepository(own_session)

        # 创建 ShotGroup 记录
        total_dur = sum(s.get("duration_sec", 3.0) for s in shots_data)
        group = await group_repo.create(
            storyboard_id=storyboard.id,
            group_code=group_plan.get("group_code"),
            name=group_plan.get("name"),
            sequence=group_plan.get("group_index", 0) + 1,
            total_duration_sec=total_dur,
            plan_intent=group_plan.get("narrative_intent"),
        )

        # 批量创建 Shot 记录
        created = []
        for shot_data in shots_data:
            safe = {
                k: v for k, v in shot_data.items()
                if v is not None and k in _shot_columns
            }
            if "char_version_ids" not in safe:
                safe["char_version_ids"] = []
            safe["shot_group_id"] = group.id
            # 移除 group_code（Shot 表没有该列，通过 shot_group_id 关联）
            safe.pop("group_code", None)
            await shot_repo.create(storyboard_id=storyboard.id, **safe)
            created.append(shot_data)

        await own_session.commit()

    logger.info("Phase 2 分镜组 %s 完成：创建 %d 个镜头", group_code, len(created))
    return created


async def _phase3_director_adjust(
    scene,
    storyboard,
    all_shots: list,
    llm_config: dict,
    system_prompt: str,
    session,
) -> None:
    """Phase 3：导演 AI 全局审校，应用 patch 微调。"""
    from app.utils.llm_call import call_llm
    from app.repositories.shot import ShotRepository
    from app.prompts import STORYBOARD_DIRECTOR_PROMPT, DirectorAdjustmentSchema
    import copy

    req = _build_storyboard_request(scene, len(all_shots), "")

    # 构建镜头摘要供导演审阅
    shot_summary_lines = []
    for shot in all_shots:
        cam = shot.camera or {}
        env = shot.environment or {}
        shot_summary_lines.append(
            f"[{shot.shot_code}] seq={shot.sequence} "
            f"dur={shot.duration_sec}s "
            f"type={cam.get('shot_type', '')} move={cam.get('movement', '')} "
            f"time={env.get('time_of_day', '')} atm={str(env.get('atmosphere', ''))[:30]} "
            f"trans_out={shot.transition_out}"
        )
    shot_summary = "\n".join(shot_summary_lines)

    director_msg = (
        req.to_prompt()
        + f"\n\n## 已生成的全部 {len(all_shots)} 个镜头摘要\n"
        + shot_summary
        + "\n\n请审查跨组连贯性并输出 patches。"
    )
    effective_system = system_prompt or STORYBOARD_DIRECTOR_PROMPT

    logger.info("=" * 60)
    logger.info("[Phase 3 导演] SYSTEM PROMPT:\n%s", effective_system)
    logger.info("-" * 60)
    logger.info("[Phase 3 导演] USER MESSAGE:\n%s", director_msg)
    logger.info("=" * 60)

    raw = await call_llm(
        messages=[{"role": "user", "content": director_msg}],
        llm_config=llm_config,
        system_prompt=effective_system,
        response_schema=DirectorAdjustmentSchema,
    )

    logger.info("-" * 60)
    logger.info("[Phase 3 导演] AI RAW RESPONSE (%d chars):\n%s", len(raw), raw)
    logger.info("=" * 60)

    data = json.loads(raw)
    patches = data.get("patches", [])

    logger.info(
        "Phase 3 导演审校完成：%d 个 patches，storyboard_id=%d",
        len(patches), storyboard.id
    )

    if not patches:
        return

    # 白名单：允许修改的顶层字段
    ALLOWED_TOP_LEVEL = {
        "image_prompt", "dialogue_text", "transition_in", "transition_out",
        "style_preset", "duration_sec", "transition_notes",
    }
    # 白名单：允许修改的嵌套 JSON 字段（父字段 → 允许的子字段）
    ALLOWED_JSON_FIELDS = {
        "camera": {"movement", "focal_length", "depth_of_field"},
        "environment": {"atmosphere", "lighting", "weather", "time_of_day"},
        "composition": {"background", "midground", "foreground", "subject_position"},
        "sound_design": {"music", "ambient"},
    }

    shot_map = {s.shot_code: s for s in all_shots}
    shot_repo = ShotRepository(session)
    applied = 0

    for patch in patches:
        shot_code = patch.get("shot_code")
        field_path = patch.get("field_path", "")
        new_value = patch.get("new_value")

        shot = shot_map.get(shot_code)
        if not shot:
            logger.warning("Phase 3 patch 跳过：shot_code=%s 不存在", shot_code)
            continue

        parts = field_path.split(".", 1)
        top_field = parts[0]

        if len(parts) == 1:
            # 顶层标量字段
            if top_field not in ALLOWED_TOP_LEVEL:
                logger.warning("Phase 3 patch 跳过：field_path=%s 不在白名单", field_path)
                continue
            # 数值类型转换
            cast_value = new_value
            if top_field == "duration_sec":
                try:
                    cast_value = float(new_value)
                except (ValueError, TypeError):
                    logger.warning("Phase 3 patch duration_sec 转换失败：%s", new_value)
                    continue
            await shot_repo.update(shot, {top_field: cast_value})
            applied += 1

        elif len(parts) == 2:
            # 嵌套 JSON 字段（如 camera.movement）
            sub_field = parts[1]
            if top_field not in ALLOWED_JSON_FIELDS:
                logger.warning("Phase 3 patch 跳过：JSON 父字段 %s 不在白名单", top_field)
                continue
            if sub_field not in ALLOWED_JSON_FIELDS[top_field]:
                logger.warning("Phase 3 patch 跳过：%s.%s 不在白名单", top_field, sub_field)
                continue

            # 深拷贝 JSON 字段后修改子键，再整体更新
            current_json = getattr(shot, top_field) or {}
            updated_json = copy.deepcopy(current_json)
            updated_json[sub_field] = new_value
            await shot_repo.update(shot, {top_field: updated_json})
            applied += 1

    await session.commit()
    logger.info("Phase 3 patch 应用完成：%d/%d 个 patch 生效", applied, len(patches))
