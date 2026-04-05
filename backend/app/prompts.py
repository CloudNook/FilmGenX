"""
FilmGenX 提示词统一管理。

同时定义与提示词配套的 LLM 结构化输出 Schema（Pydantic），
通过 response_schema 传给 Gemini，强制结构化输出，无需手动解析 JSON。
"""

from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.shot import Shot

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
你的输出将直接用于 AI 图像/视频生成，请确保每个字段都填写完整、具体。

## 通用要求
- 严格按照 JSON schema 输出，不要任何多余文字
- shot_code 格式：{scene_code}_S001、{scene_code}_S002 ...（序号三位补零）
- 严格按照剧情概述和关键事件顺序来编排镜头，不要自由发挥
- 情感曲线 emotion_curve 节点数量与镜头数对应，体现叙事节奏变化

## 字段填写规范

### camera（摄像机参数）— 所有字段必填
- shot_type：景别缩写，从以下选择：ECS(大特写)/ECU(超特写)/CU(特写)/MCU(中近景)/MS(中景)/MLS(中远景)/LS(远景)/ELS(大远景)
- angle：机位角度，从以下选择：eye_level/low_angle/high_angle/dutch/bird_eye
- movement：运镜方式，从以下选择：static/pan/tilt/dolly/zoom/handheld/crane
- focal_length（可选）：焦距描述，如 "35mm"、"85mm"
- depth_of_field（可选）：景深描述，如 "浅景深，主体清晰"（中文）

### composition（构图）— 所有字段使用中文描述
- subject_position：主体位置，如 center/left_third/right_third
- foreground（可选）：前景元素描述，如"破碎的石柱残骸"
- midground（可选）：中景元素描述
- background（可选）：背景元素描述，如"远处燃烧的宗门大殿"
- leading_lines（可选）：引导线方向，如 diagonal_left/converging/horizontal

### environment（场景环境）— 必填，每个镜头都必须有环境设定
- time_of_day：时间段，从以下选择：dawn/morning/noon/afternoon/sunset/dusk/night
- weather（可选）：天气，如 clear/cloudy/rain/storm/snow/fog
- lighting：光照描述（中文），如"暖色调逆光"、"冷色调侧光"、"火焰照亮整个场景"
- atmosphere：氛围描述（中文），如"压抑肃杀"、"热烈激昂"、"宁静祥和"、"紧张对峙"

### characters_config（角色配置）— 使用中文描述
每个镜头中出现的角色都应配置：
- action：角色动作描述，如"右手握拳高举，斗气火焰缠绕手臂"
- expression（可选）：表情描述，如"怒目圆睁，嘴角紧抿"
- emotion_intensity（可选）：情绪强度 1-10，高潮镜头建议 7-10

### dialogue（台词）— 使用中文
- dialogue_character：说话角色名
- dialogue_text：台词内容（动漫字幕风格，简洁有力）
- dialogue_delivery（可选）：台词演绎参数
  - tone：语气，如"坚定"、"愤怒"、"悲伤"、"调侃"
  - pace：语速，如"缓慢"、"正常"、"快速"、"渐快"
  - pause_positions（可选）：停顿位置，如"第2句后停顿1秒"
  - emphasis_words（可选）：重音词语
  - emotion_tags（可选）：情感标签列表

### sound_design（音效设计）— 每个镜头都应填写
- ambient：环境音描述（中文），如"风声呼啸、远处爆炸声、地面碎裂声"
- sfx_list（可选）：具体音效列表，如["火焰燃烧声","金属碰撞声","斗气爆发声"]
- music（可选）：背景音乐描述（中文），如"激昂鼓点渐入"、"空灵琴音"、"战鼓擂动"

### transition（转场）
- transition_in：入场转场，从 cut/fade/dissolve/wipe/smash 中选择
- transition_out：出场转场
- transition_notes（可选）：转场备注说明

### dependencies（镜头依赖）— 用于保证连续性
- type：依赖类型，从 character_continuity/prop_continuity/lighting_match/camera_match 中选择
- depends_on_shot_id（可选）：依赖的镜头序号（sequence 数字）
- dependency_detail（可选）：依赖详情

### 图像生成提示词 — 必须使用英文
- image_prompt：英文图像生成提示词，必须包含风格关键词 "anime style, high quality, dynamic lighting"，
  还应根据画面添加具体描述：角色外貌特征（发色、瞳色、表情）、服装细节、动作姿态、
  特效描述（火焰/斗气颜色和形态）、环境光影（光源方向、色温）、镜头效果（景深、运动模糊）。
  示例："anime style, high quality, dynamic lighting, close up of Xiao Yan's face, determined eyes,
  sharp facial features, blue and green fire reflection in eyes, sweat drops, torn clothes,
  warm orange backlight from sunset"
- negative_prompt：英文负面提示词，如 "low quality, blurry, modern buildings, realistic photo"
- style_preset（可选）：风格预设，从 cinematic/dramatic/ethereal/intense/vibrant/moody 中选择

### 视频生成提示词 — 用于 Kling API
视频提示词由系统自动从上述字段拼接生成，无需手动填写。构建规则：
1. 以 image_prompt 为视觉基础
2. 附加镜头运动描述（camera movement）
3. 附加角色动作描述（characters_config actions）
4. 附加环境氛围关键词（environment atmosphere, lighting）
5. 附加音效节奏提示（用于视频节奏控制）

## 注意事项
- 所有中文描述字段请使用生动、具体的语言，避免空泛
- environment 是必填项，每个镜头都必须有完整的环境设定
- sound_design 建议每个镜头都填写，至少包含 ambient 字段
- 战斗场景的 characters_config 应包含 2-3 个角色的动作描述
- 高潮镜头的 duration_sec 建议 2-4 秒（快节奏），铺垫镜头可 4-6 秒

## 分镜组（Shot Groups）
- 需要视觉连续性的连续镜头应归为一个 shot_group
- 分组后这些镜头将合并为一次 API 调用渲染，产生无缝连贯的视频
- 约束：每组 2-6 个镜头，总时长 ≤ 15 秒
- 不需要所有镜头都分组，独立镜头不设置 group_code
- 适合分组：快速剪辑的战斗、单一连续时刻、需要无缝过渡的跟踪镜头
- 不适合分组：对话场景、显著地点变化、静默/静态时刻
- 在 shot_groups 数组中定义组，每个组指定 group_code、name、shot_sequences
- 在每个属于组的 shot 上设置对应的 group_code"""


# ---------------------------------------------------------------------------
# 视频提示词构建器（Kling API）
# ---------------------------------------------------------------------------

# 镜头类型映射
SHOT_TYPE_MAP = {
    "ECS": "extreme close-up shot",
    "ECU": "extreme close-up",
    "CU": "close-up shot",
    "MCU": "medium close-up shot",
    "MS": "medium shot",
    "MLS": "medium long shot",
    "LS": "long shot",
    "ELS": "extreme long shot",
    "extreme_wide": "extreme wide shot",
    "wide": "wide shot",
    "medium_wide": "medium wide shot",
    "medium": "medium shot",
    "medium_close": "medium close-up shot",
    "close_up": "close-up shot",
    "extreme_close_up": "extreme close-up shot",
}

# 机位角度映射
ANGLE_MAP = {
    "eye_level": "eye level angle",
    "low_angle": "low angle looking up",
    "high_angle": "high angle looking down",
    "dutch": "dutch angle, tilted",
    "dutch_angle": "dutch angle, tilted",
    "birds_eye": "bird's eye view from above",
    "over_shoulder": "over the shoulder shot",
}

# 运镜方式映射
MOVEMENT_MAP = {
    "static": "static camera, locked off",
    "pan": "panning camera movement",
    "tilt": "tilting camera movement",
    "dolly": "dolly camera movement, tracking",
    "zoom": "zoom effect",
    "handheld": "handheld camera, slight shake",
    "crane": "crane shot, sweeping movement",
    "tracking": "tracking shot following subject",
}

# 时间段映射
TIME_OF_DAY_MAP = {
    "dawn": "dawn light, early morning",
    "morning": "morning light",
    "noon": "midday lighting",
    "afternoon": "afternoon light",
    "sunset": "golden hour, sunset lighting",
    "dusk": "dusk, twilight",
    "night": "night scene",
}

# 转场映射
TRANSITION_MAP = {
    "cut": "hard cut",
    "fade": "fade transition",
    "dissolve": "dissolve transition",
    "wipe": "wipe transition",
    "smash": "smash cut",
}


def build_video_prompt(shot: "Shot") -> str:
    """
    从 Shot 对象构建结构化的视频生成提示词。
    包含所有字段信息，输出清晰的分段格式。
    """
    lines = []

    camera = shot.camera or {}
    composition = shot.composition or {}
    environment = shot.environment or {}
    characters_config = shot.characters_config or []
    dialogue_delivery = shot.dialogue_delivery or {}
    sound_design = shot.sound_design or {}

    # ========== VISUAL DESCRIPTION ==========
    lines.append("========== VISUAL DESCRIPTION ==========")
    if shot.image_prompt:
        lines.append(shot.image_prompt)
    else:
        lines.append("anime style, high quality, dynamic lighting")

    # ========== SCENE ENVIRONMENT ==========
    lines.append("")
    lines.append("========== SCENE ENVIRONMENT ==========")

    time_of_day = environment.get("time_of_day")
    if time_of_day:
        time_desc = TIME_OF_DAY_MAP.get(time_of_day, time_of_day)
        lines.append(f"Time of Day: {time_desc}")

    lighting = environment.get("lighting")
    if lighting:
        lines.append(f"Lighting: {lighting}")

    atmosphere = environment.get("atmosphere") or environment.get("mood")
    if atmosphere:
        lines.append(f"Atmosphere: {atmosphere}")

    weather = environment.get("weather")
    if weather:
        lines.append(f"Weather: {weather}")

    # ========== COMPOSITION ==========
    lines.append("")
    lines.append("========== COMPOSITION ==========")

    shot_type = camera.get("shot_type")
    if shot_type:
        shot_type_desc = SHOT_TYPE_MAP.get(shot_type, shot_type)
        lines.append(f"Shot Type: {shot_type_desc}")

    angle = camera.get("angle")
    if angle:
        angle_desc = ANGLE_MAP.get(angle, angle.replace("_", " "))
        lines.append(f"Camera Angle: {angle_desc}")

    movement = camera.get("movement")
    if movement:
        movement_desc = MOVEMENT_MAP.get(movement, movement.replace("_", " "))
        lines.append(f"Camera Movement: {movement_desc}")

    subject_position = composition.get("subject_position")
    if subject_position:
        lines.append(f"Subject Position: {subject_position}")

    foreground = composition.get("foreground")
    if foreground:
        lines.append(f"Foreground: {foreground}")

    midground = composition.get("midground")
    if midground:
        lines.append(f"Midground: {midground}")

    background = composition.get("background")
    if background:
        lines.append(f"Background: {background}")

    # ========== CHARACTERS ==========
    lines.append("")
    lines.append("========== CHARACTERS ==========")

    for idx, char in enumerate(characters_config):
        if isinstance(char, dict):
            action = char.get("action")
            expression = char.get("expression")
            emotion_intensity = char.get("emotion_intensity")

            if action or expression:
                lines.append(f"Character {idx + 1}:")
                if action:
                    lines.append(f"  Action: {action}")
                if expression:
                    lines.append(f"  Expression: {expression}")
                if emotion_intensity:
                    lines.append(f"  Emotion Intensity: {emotion_intensity}/10")

    # ========== DIALOGUE ==========
    if shot.dialogue_character or shot.dialogue_text:
        lines.append("")
        lines.append("========== DIALOGUE ==========")

        if shot.dialogue_character:
            lines.append(f"Speaker: {shot.dialogue_character}")

        if shot.dialogue_text:
            lines.append(f"Line: \"{shot.dialogue_text}\"")

        tone = dialogue_delivery.get("tone")
        if tone:
            lines.append(f"Delivery Tone: {tone}")

        pace = dialogue_delivery.get("pace")
        if pace:
            lines.append(f"Delivery Pace: {pace}")

    # ========== SOUND DESIGN ==========
    if sound_design:
        lines.append("")
        lines.append("========== SOUND DESIGN ==========")

        ambient = sound_design.get("ambient")
        if ambient:
            lines.append(f"Ambient Sound: {ambient}")

        music = sound_design.get("music")
        if music:
            lines.append(f"Background Music: {music}")

        sfx_list = sound_design.get("sfx_list")
        if sfx_list and isinstance(sfx_list, list):
            lines.append(f"Sound Effects: {', '.join(sfx_list)}")

    # ========== TRANSITIONS ==========
    lines.append("")
    lines.append("========== TRANSITIONS ==========")

    transition_in = shot.transition_in or "cut"
    transition_in_desc = TRANSITION_MAP.get(transition_in, transition_in)
    lines.append(f"Transition In: {transition_in_desc}")

    transition_out = shot.transition_out or "cut"
    transition_out_desc = TRANSITION_MAP.get(transition_out, transition_out)
    lines.append(f"Transition Out: {transition_out_desc}")

    if shot.transition_notes:
        lines.append(f"Transition Notes: {shot.transition_notes}")

    # ========== DURATION & STYLE ==========
    lines.append("")
    lines.append("========== DURATION & STYLE ==========")

    lines.append(f"Duration: {int(shot.duration_sec or 3)} seconds")

    if shot.style_preset:
        lines.append(f"Style Preset: {shot.style_preset}")
    else:
        lines.append("Style Preset: cinematic")

    # ========== NEGATIVE PROMPT ==========
    lines.append("")
    lines.append("========== NEGATIVE PROMPT (AVOID) ==========")
    base_negative = "low quality, blurry, distorted, deformed, ugly, bad anatomy, watermark, text, logo"
    if shot.negative_prompt:
        lines.append(f"{base_negative}, {shot.negative_prompt}")
    else:
        lines.append(base_negative)

    # 组合最终提示词
    final_prompt = "\n".join(lines)

    # 限制长度（Kling API 最大 2000 字符）
    if len(final_prompt) > 2000:
        final_prompt = final_prompt[:2000]

    return final_prompt


def build_negative_prompt(shot: "Shot") -> str:
    """
    构建负面提示词。
    """
    base_negative = "low quality, blurry, distorted, deformed, ugly, bad anatomy, watermark, text, logo"

    if shot.negative_prompt:
        return f"{base_negative}, {shot.negative_prompt}"

    return base_negative


def build_compact_video_prompt(shot: "Shot") -> str:
    """
    从 Shot 对象构建紧凑的视频生成提示词，用于 Kling multi_shot 模式。

    multi_shot 模式下每个子镜头提示词限制 512 字符（远小于单镜头的 2000 字符）。
    按优先级截取最关键的视觉信息。
    """
    parts = []

    # 1. 主视觉描述（image_prompt 已经是精炼的英文）
    if shot.image_prompt:
        parts.append(shot.image_prompt[:300])

    # 2. 摄像机运动
    camera = shot.camera or {}
    movement = camera.get("movement")
    if movement:
        parts.append(MOVEMENT_MAP.get(movement, movement))

    # 3. 角色动作（最多 2 个，精简）
    characters_config = shot.characters_config or []
    for char in characters_config[:2]:
        if isinstance(char, dict):
            action = char.get("action", "")
            if action:
                parts.append(action[:80])

    # 4. 环境氛围
    environment = shot.environment or {}
    atmosphere = environment.get("atmosphere")
    if atmosphere:
        parts.append(atmosphere[:60])

    prompt = ", ".join(parts)
    return prompt[:512]  # Kling multi_shot 硬限制
