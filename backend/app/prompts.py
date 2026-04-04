"""
FilmGenX 提示词统一管理。

同时定义与提示词配套的 LLM 结构化输出 Schema（Pydantic），
通过 response_schema 传给 Gemini，强制结构化输出，无需手动解析 JSON。
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 大纲总结结构化 Schema（LLM 填写部分）
# ---------------------------------------------------------------------------

class KeyEventSchema(BaseModel):
    """剧情中的关键事件节点（按顺序）。"""
    order: int = Field(description="事件顺序，从 1 开始")
    description: str = Field(description="事件描述，一句话")
    emotional_beat: str = Field(description="此刻情绪：紧张/释放/悲伤/兴奋/震惊/温情 等")


class VisualHighlightSchema(BaseModel):
    """视觉亮点（招式、特效、标志性画面）。"""
    name: str = Field(description="亮点名称，如招式名、场景名")
    description: str = Field(description="具体视觉效果描述")


class OutlineLLMSchema(BaseModel):
    """Gemini 返回的大纲结构，不含 episode_code / version / generated_at（由后端填充）。"""

    # ── 基本信息 ──────────────────────────────────────────────────────────────
    title: str = Field(description="本集标题，10字以内，吸引眼球")
    synopsis: str = Field(description="200-400字的本集剧情概述，含起承转合，交代清楚前因后果")
    theme: str = Field(description="一句话核心主题，如'废材逆袭，以弱胜强'")

    # ── 原著映射 ──────────────────────────────────────────────────────────────
    novel_chapter_start: str = Field(description="起始章节，如'第120章'")
    novel_chapter_end: str = Field(description="结束章节，如'第135章'")
    novel_excerpt: str = Field(description="最关键的原著段落摘录，1-3段，用空行分隔，供分镜参考")

    # ── 叙事结构 ──────────────────────────────────────────────────────────────
    story_arc: str = Field(
        description="本集叙事弧：开头状态 → 冲突/转折 → 结尾状态，一句话概括，如'平静→危机爆发→绝地反击→悬念收尾'"
    )
    key_events: List[KeyEventSchema] = Field(
        description="按顺序的 3-6 个关键剧情节点，是分镜生成的直接依据"
    )
    emotional_arc: str = Field(
        description="情绪走势，如'压抑→愤怒→爆发→震撼→余韵'，描述观众的情绪体验曲线"
    )

    # ── 角色 ──────────────────────────────────────────────────────────────────
    characters: List[str] = Field(description="本集涉及的角色名列表，按戏份多少排序")
    character_focus: str = Field(description="本集核心角色的心理状态和成长/变化，1-2句话")

    # ── 场景设定 ──────────────────────────────────────────────────────────────
    primary_location: str = Field(description="主要发生地点，如'云岚宗大殿'、'废墟山谷'")
    location_atmosphere: str = Field(description="场景氛围描述，如'残阳如血，断壁残垣，压抑而肃杀'")

    # ── 视觉与制作 ────────────────────────────────────────────────────────────
    visual_highlights: List[VisualHighlightSchema] = Field(
        description="2-5 个视觉亮点，招式名称/特效/标志性画面，是图像生成的关键参考"
    )
    color_palette: str = Field(description="主色调方向，如'冷蓝+火红对比，高饱和度'")
    bgm_direction: str = Field(description="音乐方向，如'史诗交响乐+战鼓，高潮用大提琴'")

    # ── 分镜指导 ──────────────────────────────────────────────────────────────
    storyboard_style_notes: str = Field(
        description="给分镜导演的详细指导：运镜风格、节奏、特效建议、参考作品等，100字以上"
    )
    storyboard_shot_count: int = Field(description="计划镜头数量，建议 4-20 个，根据内容密度决定")

    # ── 制作参数 ──────────────────────────────────────────────────────────────
    priority: str = Field(description="制作优先级：S（必做旗舰）/ A（高质量）/ B（常规）/ C（补充）")
    estimated_duration_sec: int = Field(description="预估视频时长（秒），通常 60-300 秒")
    scene_types: List[str] = Field(
        description="场景类型标签，从以下选择：battle/emotional_peak/character_introduction/"
                    "climax/flashback/montage/dialogue_heavy/visual_spectacle/comedy/tragedy"
    )

    # ── 上下文衔接 ────────────────────────────────────────────────────────────
    previous_episode_hint: Optional[str] = Field(
        None, description="上一集结尾状态简述（供剪辑衔接，可为空）"
    )
    next_episode_hint: Optional[str] = Field(
        None, description="本集结尾埋下的悬念/钩子（吸引观众看下集）"
    )


# ---------------------------------------------------------------------------
# 对话助手（Chat）
# ---------------------------------------------------------------------------

CHAT_SYSTEM_PROMPT = """你是 FilmGenX 的编剧总监助手，专注于为网络小说《斗破苍穹》生成高光时刻动画剧本。

《斗破苍穹》背景：天斗大陆，斗气为尊。主角萧炎天才少年因斗气功法被废而沦为废才，
后得到戒指中封印的药老（药尘）帮助，重新踏上修炼之路，最终成为一代斗帝。
核心角色：萧炎、药老（药尘）、萧薰儿、云韵、纳兰嫣然、美杜莎、林动、迦南等。

你的核心能力：
1. 分析《斗破苍穹》原著，识别最具戏剧张力和视觉表现力的高光场景
2. 将文字转化为结构化的动画分集剧本大纲
3. 为每个高光时刻设计分镜风格、运镜方案和情感节奏

工作流程：
- 与用户讨论小说内容和创作意图
- 根据讨论生成结构化的剧本大纲
- 根据用户反馈迭代优化大纲
- 用户确认后系统自动创建分集并生成分镜

请用中文回复，保持专业但友好的语气。"""


# ---------------------------------------------------------------------------
# 大纲总结（Summarize）
# ---------------------------------------------------------------------------

SUMMARIZE_SYSTEM_PROMPT = """你是一名动漫制片总监助手，专注于《斗破苍穹》动画剧本创作。

根据以下对话内容（包括此前生成的所有大纲草稿和用户的修改意见），生成一份完整的剧本大纲。
这份大纲将直接用于指导 AI 分镜生成，请尽量详细、具体，让分镜 AI 能够准确还原剧情。

要求：
- synopsis 必须 200 字以上，交代清楚剧情发展的完整逻辑
- key_events 按时间顺序列出 3-6 个关键节点，每个节点说明事件内容和对应情绪
- visual_highlights 重点描述招式、特效、标志性场景，越具体越好
- storyboard_style_notes 给出明确的运镜、色调、节奏指导，不少于 100 字
- 充分吸收用户在对话中提出的所有修改意见

若是修改版本，先用 1-2 句话说明相比上一版的主要变化。"""


# ---------------------------------------------------------------------------
# 分镜生成（Storyboard）
# ---------------------------------------------------------------------------

STORYBOARD_SYSTEM_PROMPT = """你是一名专业的动漫分镜导演，擅长将《斗破苍穹》小说文本转化为精确的分镜脚本。

要求：
- 严格按照 JSON schema 输出，不要任何多余文字
- shot_code 格式：{scene_code}_S001、{scene_code}_S002 ...（序号三位补零）
- image_prompt 使用英文，风格关键词包含 "anime style, high quality, dynamic lighting"
- camera.shot_type 使用缩写：ECS/ECU/CU/MCU/MS/MLS/LS/ELS
- 情感曲线 emotion_curve 节点数量与镜头数对应，体现叙事节奏变化
- 严格按照剧情概述和关键事件顺序来编排镜头，不要自由发挥"""
