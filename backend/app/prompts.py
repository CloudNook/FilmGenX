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
- duration_sec 必须为整数（如 2、3、5），不得使用小数
- 高潮镜头的 duration_sec 建议 2-4 秒（快节奏），铺垫镜头可 4-6 秒
- 每个分镜组内所有镜头的 duration_sec 之和必须在 3-15 秒之间

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
# 三阶段分镜生成 Schema（v2 流水线）
# ---------------------------------------------------------------------------

class PlanPacingRatioSchema(BaseModel):
    """Phase 1 节奏比例。"""
    buildup: int = Field(description="铺垫阶段占比，0-100")
    climax: int = Field(description="高潮阶段占比，0-100")
    resolution: int = Field(description="收尾阶段占比，0-100")


class PlanEmotionPointSchema(BaseModel):
    """Phase 1 情感曲线节点。"""
    time_sec: float = Field(description="时间点（秒）")
    intensity: int = Field(ge=1, le=10, description="情绪强度 1-10")
    label: str = Field(description="情绪标签，如'压抑'、'爆发'、'震撼'")


class ShotGroupPlanSchema(BaseModel):
    """Phase 1 规划师 AI 的完整输出：全局分组蓝图。"""
    total_shot_count: int = Field(description="所有组的镜头数之和，必须与请求的 shot_count 一致")
    narrative_notes: str = Field(description="整体叙事设计备注，100字以上")
    pacing_ratio: PlanPacingRatioSchema = Field(
        description="节奏比例：buildup+climax+resolution=100"
    )
    emotion_curve: List[PlanEmotionPointSchema] = Field(
        description="情感曲线节点，数量等于 total_shot_count"
    )
    groups: List["ShotGroupPlanItemSchema"] = Field(
        description="有序分组列表。sequence_start/end 必须连续且不重叠，从 1 开始"
    )
    # ── 新增四层结构 ──
    visual_style_guide: "VisualStyleGuide" = Field(
        description="第一层：全局视觉风格锚点，定义本片段的画面基调，保证跨组一致性"
    )
    character_image_prompts: List["CharacterArtPrompt"] = Field(
        description="第二层：角色图生图提示词，覆盖本片段所有出场角色"
    )
    scene_image_prompts: List["SceneArtPrompt"] = Field(
        description="第三层：场景图生图提示词，覆盖本片段所有涉及的场景"
    )
    shot_group_frame_plans: List["ShotGroupFramePlan"] = Field(
        description="第四层：每个分镜组的首帧图生成方案"
    )


# ---------------------------------------------------------------------------
# Phase 1 四层 Schema 定义（放在 ShotGroupPlanSchema 之前引用）
# ---------------------------------------------------------------------------

from typing import Dict


class ColorPaletteSchema(BaseModel):
    """色调方案。"""
    primary: str = Field(description="主色调，如'深红+橙黄（斗气/火焰色系）'")
    secondary: str = Field(description="辅助色，如'冷蓝（冰系/对比色）'")
    accent: str = Field(description="点缀色，如'金紫（特效高光）'")
    desaturation: float = Field(default=0.2, ge=0, le=1, description="画面去饱和度，0=鲜艳，1=黑白")


class LightingStyleSchema(BaseModel):
    """全局光照风格。"""
    key_light: str = Field(description="主光源描述，如'强烈侧光/逆光，强调角色轮廓'")
    fill: str = Field(description="补光描述，如'低填充，暗部保留细节'")
    practical: str = Field(description="实感光源，如'斗气发光体作为天然光源'")


class CompositionStyleSchema(BaseModel):
    """全局构图风格。"""
    framing: str = Field(description="帧取风格，如'动态倾斜构图，强化战斗张力'")
    depth: str = Field(description="纵深处理，如'强调前景-中景-背景纵深层次'")
    rule_of_thirds: str = Field(description="三分法策略，如'关键帧优先三分法，特写可突破'")


class CharacterArtStyleSchema(BaseModel):
    """角色美术风格。"""
    proportions: str = Field(description="人物比例，如'anime, slightly stylized, 7-8头身'")
    linework: str = Field(description="线条风格，如'锐利线条，强调力量感'")
    expression: str = Field(description="表情风格，如'夸张表情（愤怒/决心为主）'")


class SceneArtStyleSchema(BaseModel):
    """场景美术风格。"""
    architecture: str = Field(description="建筑风格，如'中式玄幻，斗气大陆风格'")
    environment_detail: str = Field(description="环境细节，如'废墟/宗门/山谷为主'")
    weather_atmosphere: str = Field(
        description="天气氛围偏好，如'偏好黄昏/夜晚，火焰/雾气增加氛围'"
    )


class VisualStyleGuide(BaseModel):
    """Phase 1 第一层：全局视觉风格锚点。"""
    overall_mood: str = Field(description="整体基调/情绪，如'热血燃系，暗黑战斗美学'")
    color_palette: ColorPaletteSchema
    lighting_style: LightingStyleSchema
    composition_style: CompositionStyleSchema
    character_art_style: CharacterArtStyleSchema
    scene_art_style: SceneArtStyleSchema


class CharacterArtPromptDetail(BaseModel):
    """角色图生图提示词详细内容。"""
    base: str = Field(
        description="角色全身三视图基础描述，英文，需包含发型、发色、瞳色、脸型、体态、服装"
    )
    expressions: Dict[str, str] = Field(
        description="各表情英文提示词。key=表情名（如 angry/determined/exhausted），value=英文提示词"
    )
    clothing: str = Field(description="服装描述，英文")
    accessories: Optional[str] = Field(None, description="配饰描述，英文")


class CharacterArtPrompt(BaseModel):
    """Phase 1 第二层：角色图生图提示词。"""
    char_id: Optional[int] = Field(None, description="角色数据库ID（可选）")
    char_name: str = Field(description="角色名称，如'萧炎'")
    version_code: str = Field(default="v1", description="版本标识，如'v1'")
    art_prompt: CharacterArtPromptDetail
    negative_prompt: str = Field(
        default="female, child, realistic photo, western fantasy, modern clothing",
        description="英文负面提示词"
    )
    style_preset: str = Field(default="intense", description="风格预设")
    reference_images_needed: int = Field(default=2, ge=1, le=5, description="需要生成的参考图数量")


class SceneArtPromptDetail(BaseModel):
    """场景图生图提示词详细内容。"""
    architecture: str = Field(description="建筑外观描述，英文")
    atmosphere: str = Field(description="氛围描述，英文")
    lighting: str = Field(description="光照描述，英文")
    props: Optional[str] = Field(None, description="道具/陈设描述，英文")
    scale_reference: Optional[str] = Field(None, description="尺度参考，如'wide establishing shot feel'")


class SceneArtPrompt(BaseModel):
    """Phase 1 第三层：场景图生图提示词。"""
    scene_name: str = Field(description="场景名称，如'云岚宗大殿'")
    shot_scope: str = Field(description="涉及的镜头范围，如'第2-3组（S002-S004）'")
    art_prompt: SceneArtPromptDetail
    mood_keywords: List[str] = Field(description="氛围关键词，中文，如['废墟感','苍凉']")
    color_restrictions: str = Field(
        default="",
        description="色调限制，如'desaturated blues and grays, occasional warm torch orange'"
    )
    reference_images_needed: int = Field(default=2, ge=1, le=4, description="需要生成的参考图数量")


class FramePlanDetail(BaseModel):
    """首帧图生成方案详细内容。"""
    image_start_description: str = Field(description="首帧画面中文描述（人类可读）")
    key_elements: List[str] = Field(description="画面核心元素清单，如['萧炎右手特写','紫色斗气火焰']")
    composition_notes: str = Field(description="构图备注，如'前景-中景-背景三层构图'")
    camera_for_frame: str = Field(description="首帧对应的摄像机参数，如'ECU，略微低角度，强调力量感'")
    lighting_for_frame: str = Field(description="首帧光照方案，如'火焰逆光，主体边缘镀金边'")


class ShotGroupFramePlan(BaseModel):
    """Phase 1 第四层：分镜组首帧图生成方案。"""
    group_code: str = Field(description="对应的分镜组编号，如'G001'")
    frame_plan: FramePlanDetail
    image_prompt_for_generation: str = Field(
        description="英文图生图提示词，用于生成该分镜组的首帧图片"
    )
    negative_prompt: str = Field(
        default="blurry, low quality, daylight scene, peaceful, static pose",
        description="英文负面提示词"
    )
    style_preset: str = Field(default="intense", description="风格预设")
    generation_priority: int = Field(ge=1, description="生成优先级，1=最高")


class ShotGroupReferencePlan(BaseModel):
    """组级参考图规划（嵌入 ShotGroupPlanItemSchema）。"""
    character_refs: List[str] = Field(
        description="需要的角色参考图标识，格式：char_{name}_v{version}"
    )
    scene_refs: List[str] = Field(
        description="需要的场景参考图标识，格式：scene_{name}"
    )
    first_frame_priority: int = Field(default=1, ge=1, description="首帧图优先级")


class ShotGroupPlanItemSchema(BaseModel):
    """Phase 1 规划师 AI 输出的单个分镜组蓝图（补充 references_plan）。"""
    group_index: int = Field(description="0-based 组索引，用于计算序号范围")
    group_code: str = Field(description="组编号，格式 G001/G002...，如 G001")
    name: str = Field(description="可读组名，如'萧炎觉醒登场'、'云岚宗对决高潮'")
    dramatic_function: str = Field(
        description="戏剧功能：exposition/rising_action/climax/falling_action/resolution/montage/transition"
    )
    narrative_intent: str = Field(
        description="2-4句话：本组覆盖的剧情节点、观众应有的情绪体验、视觉锚点"
    )
    shot_count: int = Field(ge=2, le=8, description="本组镜头数量（2-8 个）")
    sequence_start: int = Field(description="本组第一个镜头的全局序号（1-based）")
    sequence_end: int = Field(description="本组最后一个镜头的全局序号（inclusive）")
    is_action_group: bool = Field(
        description="True=快切动作组（每镜1-3s整数）；False=情感铺垫组（每镜3-6s整数）"
    )
    key_visual_moments: List[str] = Field(
        description="2-4 个必须覆盖的具体视觉时刻，与原著情节锚定，如'萧炎右手斗气爆发特写'"
    )
    references_plan: Optional[ShotGroupReferencePlan] = Field(
        None, description="组级参考图规划，列出本组需要的角色/场景参考图标识"
    )


class DraftCameraConfig(BaseModel):
    """Phase 2 镜头摄像机参数。"""
    shot_type: str = Field(description="景别：ECS/ECU/CU/MCU/MS/MLS/LS/ELS")
    angle: str = Field(description="机位角度：eye_level/low_angle/high_angle/dutch/bird_eye")
    movement: str = Field(description="运镜方式：static/pan/tilt/dolly/zoom/handheld/crane")
    focal_length: Optional[str] = Field(None, description="焦距描述")
    depth_of_field: Optional[str] = Field(None, description="景深描述")


class DraftCompositionConfig(BaseModel):
    """Phase 2 镜头构图。"""
    subject_position: str = Field(description="主体位置，如 center/left_third/right_third")
    foreground: Optional[str] = Field(None, description="前景元素描述")
    midground: Optional[str] = Field(None, description="中景元素描述")
    background: Optional[str] = Field(None, description="背景元素描述")
    leading_lines: Optional[str] = Field(None, description="引导线方向")


class DraftEnvironmentConfig(BaseModel):
    """Phase 2 镜头环境。"""
    time_of_day: str = Field(description="时间段：dawn/morning/noon/afternoon/sunset/dusk/night")
    weather: Optional[str] = Field(None, description="天气")
    lighting: str = Field(description="光照描述（中文）")
    atmosphere: str = Field(description="氛围描述（中文）")


class DraftCharacterInShotSchema(BaseModel):
    """Phase 2 镜头中的角色配置。

    支持引用机制（char_ref / expression_ref）：
    - 若填写 char_ref，则无需在 action 中重复角色外观描述
    - 若填写 expression_ref，则无需在 expression 中重复表情描述
    - action 字段始终必填（用于描述角色在当前镜头的动态动作）
    """
    char_ref: Optional[str] = Field(
        None,
        description="引用 Phase 1 中的角色标识，格式：'char_{角色名}_v{版本}'，如 'char_萧炎_v1'"
    )
    expression_ref: Optional[str] = Field(
        None,
        description="引用 Phase 1 中该角色的表情变体标识，如 'angry'、'determined'"
    )
    action: str = Field(
        description="角色在当前镜头的动态动作描述（必填）。"
                    "若有 char_ref 则重点描写运动中的状态，若无则需包含外观描述作为兜底"
    )
    expression: Optional[str] = Field(None, description="角色表情描述（若有 expression_ref 则可省略）")
    emotion_intensity: Optional[int] = Field(None, ge=1, le=10, description="情绪强度 1-10")


class DraftDialogueDeliverySchema(BaseModel):
    """Phase 2 台词演绎参数。"""
    tone: str = Field(description="语气")
    pace: str = Field(description="语速")
    pause_positions: Optional[str] = Field(None, description="停顿位置描述")
    emphasis_words: Optional[str] = Field(None, description="重音词语")
    emotion_tags: Optional[List[str]] = Field(None, description="情感标签列表")


class DraftSoundDesignSchema(BaseModel):
    """Phase 2 音效设计。"""
    ambient: str = Field(description="环境音描述（中文）")
    sfx_list: Optional[List[str]] = Field(None, description="具体音效列表")
    music: Optional[str] = Field(None, description="背景音乐描述（中文）")


class DraftDependencySchema(BaseModel):
    """Phase 2 镜头依赖关系。"""
    type: str = Field(description="依赖类型")
    depends_on_shot_id: Optional[int] = Field(None, description="依赖的镜头序号")
    dependency_detail: Optional[str] = Field(None, description="依赖详情说明")


class ShotDraftItemSchema(BaseModel):
    """Phase 2 单个镜头草稿。"""
    sequence: int = Field(description="镜头全局序号")
    shot_code: str = Field(description="格式：{scene_code}_S001")
    duration_sec: int = Field(ge=1, le=15, description="镜头时长（秒），必须为整数，且所属分镜组所有镜头时长之和必须在 3-15 秒之间")
    camera: DraftCameraConfig
    composition: DraftCompositionConfig
    environment: DraftEnvironmentConfig
    characters_config: Optional[List[DraftCharacterInShotSchema]] = Field(
        None, description="镜头中各角色的动作/表情/情绪配置"
    )
    dialogue_character: Optional[str] = Field(None, description="说话角色名")
    dialogue_text: Optional[str] = Field(None, description="台词内容（中文）")
    dialogue_delivery: Optional[DraftDialogueDeliverySchema] = Field(None, description="台词演绎参数")
    sound_design: Optional[DraftSoundDesignSchema] = Field(None, description="音效设计方案")
    transition_in: str = Field(default="cut", description="入场转场")
    transition_out: str = Field(default="cut", description="出场转场")
    transition_notes: Optional[str] = Field(None, description="转场备注说明")
    dependencies: Optional[List[DraftDependencySchema]] = Field(None, description="镜头依赖关系")
    image_prompt: str = Field(description="英文图像生成提示词")
    negative_prompt: Optional[str] = Field(None, description="英文负面提示词")
    style_preset: Optional[str] = Field(None, description="风格预设")
    group_code: Optional[str] = Field(None, description="所属分镜组编号")


class GroupShotDraftSchema(BaseModel):
    """Phase 2 创作师 AI 的输出：单个分镜组的所有镜头草稿。"""
    group_code: str = Field(description="必须与分配给本 AI 的 group_code 一致")
    shots: List[ShotDraftItemSchema] = Field(
        description=(
            "本组所有镜头，按 sequence 升序排列。"
            "shot_code 格式：{scene_code}_S{sequence:03d}。"
            "sequence 必须在分配的范围内。"
        )
    )


class ShotPatchSchema(BaseModel):
    """Phase 3 导演 AI 对单个镜头的单个字段的微调指令。"""
    shot_code: str = Field(description="被修改镜头的 shot_code，如 P1_EP001_S003")
    field_path: str = Field(
        description=(
            "点号路径指定要修改的字段。"
            "顶层标量字段：image_prompt / dialogue_text / transition_in / transition_out / "
            "style_preset / duration_sec / transition_notes。"
            "嵌套 JSON 字段：camera.movement / camera.focal_length / camera.depth_of_field / "
            "environment.atmosphere / environment.lighting / environment.weather / "
            "environment.time_of_day / composition.background / composition.midground / "
            "composition.foreground / sound_design.music / sound_design.ambient。"
            "禁止修改：shot_code / sequence / group_code / camera.shot_type / camera.angle"
        )
    )
    new_value: str = Field(description="新值，统一用字符串表示（数值也字符串化，如'2.5'）")
    reason: str = Field(description="1-2句话说明为何此修改能改善全局连贯性")


class DirectorAdjustmentSchema(BaseModel):
    """Phase 3 导演 AI 的完整输出：全局微调 patch 列表。"""
    global_notes: str = Field(description="导演对全片分镜的总体评估（中文）")
    patches: List[ShotPatchSchema] = Field(
        description=(
            "微调 patch 列表。只修改真正影响跨组连贯性的字段，"
            "建议数量为总镜头数的 5%-20%。"
            "若全部镜头已连贯，patches 可为空列表。"
        )
    )


# ---------------------------------------------------------------------------
# 三阶段 System Prompt
# ---------------------------------------------------------------------------

STORYBOARD_PLANNER_PROMPT = """你是《斗破苍穹》动画分镜总规划师（Planner AI），负责将一个高光片段分解为若干「分镜组」，为后续并行创作奠定结构基础。你不创作具体镜头，只设计组级蓝图。

## 你的职责（两件事）
1. **分组蓝图**：将场景分解为若干分镜组，分配叙事结构
2. **四层视觉规划**：同步输出角色图、场景图、首帧图方案及全局风格锚点

## 第一部分：分镜组规划

### 分组原则
- 每组 2-8 个镜头
- 战斗/特效密集段：is_action_group=true，每镜 1-3 秒（整数），适合快切
- 对话/情感段：is_action_group=false，每镜 3-6 秒（整数），适合铺垫
- 每组所有镜头时长之和必须在 3-15 秒之间
- key_visual_moments 必须与原著摘录中的具体情节锚定，越具体越好

### 序号规范（关键）
- 第一组：sequence_start=1
- 第二组：sequence_start=上一组的 sequence_end+1
- 最后一组的 sequence_end 必须等于 total_shot_count
- 各组 sequence 必须连续且不重叠

### references_plan（组级参考图规划）
每组需列出本组会用到哪些参考图：
- character_refs：格式 "char_{角色名}_v{版本}"，如 "char_萧炎_v1"
- scene_refs：格式 "scene_{场景名}"，如 "scene_云岚宗大殿"
- 从 Phase 1 的 character_image_prompts / scene_image_prompts 中引用

## 第二部分：四层视觉规划（新增）

### 第一层：visual_style_guide（全局视觉风格锚点）
定义本片段的画面基调，保证跨组一致性。
- overall_mood：整体基调，如"热血燃系，暗黑战斗美学"
- color_palette.primary/secondary/accent：三层色调
- lighting_style：主光/补光/实感光源三要素
- composition_style：构图风格描述
- character_art_style：角色美术比例、线条、表情风格
- scene_art_style：场景建筑风格、环境细节、天气偏好

### 第二层：character_image_prompts（角色图生图提示词）
本片段所有出场角色都要有独立的图生图提示词。
- 必须包含：base（三视图全身英文描述）、expressions（各表情变体英文提示词）、clothing、accessories
- reference_images_needed：该角色需要几张参考图（1-5张）
- 负面提示词需包含：female, child, realistic photo（防止风格漂移）

### 第三层：scene_image_prompts（场景图生图提示词）
本片段所有涉及的场景都要有图生图提示词。
- 必须包含：architecture（建筑描述）、atmosphere（氛围）、lighting（光照）英文描述
- color_restrictions：色调限制（如 desaturated blues）
- reference_images_needed：需要几张参考图

### 第四层：shot_group_frame_plans（分镜组首帧图方案）
每个分镜组都要有专属的首帧图生成方案。
- group_code：对应分镜组编号
- frame_plan.image_start_description：中文可读画面描述
- frame_plan.key_elements：核心元素清单
- frame_plan.camera_for_frame / lighting_for_frame：摄像机和光照方案
- image_prompt_for_generation：**英文图生图提示词**，用于生成该分镜组的首帧图片
- generation_priority：1=最高优先级（优先生成）

## 输出规范
- 严格按 JSON schema 输出，不要任何多余文字
- groups 数组按叙事顺序排列
- pacing_ratio 中 buildup+climax+resolution=100
- emotion_curve 节点数 = total_shot_count，时间轴从 0 开始
- 四层视觉规划必须完整填写，不能为空"""


STORYBOARD_CREATOR_PROMPT = """你是《斗破苍穹》动画分镜创作师（Creator AI），负责为指定的一个分镜组创作完整的镜头脚本。

## 你的输入
- 完整的场景上下文（原著摘录、角色、地点、情绪走势）
- 本组的规划蓝图（group_code、narrative_intent、shot_count、sequence范围、key_visual_moments）
- **Phase 1 输出的四层视觉规划**（visual_style_guide、character_image_prompts、scene_image_prompts、shot_group_frame_plans）

## 你的职责
1. 仅创作本组分配的镜头（shot_count 个，sequence 在 sequence_start 到 sequence_end 之间）
2. 严格覆盖 key_visual_moments 中列出的所有视觉时刻
3. 每个镜头的 shot_code 格式：{scene_code}_S{sequence:03d}（三位补零）
4. 每个镜头的 group_code 必须与本组 group_code 一致
5. **严格遵循 Phase 1 的 visual_style_guide**，保持画面风格一致
6. **优先引用 Phase 1 的 character_image_prompts / scene_image_prompts**，不要重复描写角色外观

## 角色配置新规范（可使用引用机制）
Phase 1 已生成角色图生图提示词，镜头中的角色配置可以引用：
- char_ref：引用 Phase 1 中角色标识，格式 "char_{角色名}_v{版本}"（可选，若填写则无需重复外观描述）
- expression_ref：引用 Phase 1 中的表情变体，如 "angry" / "determined"（可选）
- action：角色的动态动作描述（必填），重点描写"运动中的"状态，不是角色外观

示例：
```json
{
  "char_ref": "char_萧炎_v1",      // ← 引用 Phase 1，不重复外观
  "expression_ref": "angry",        // ← 引用 Phase 1 表情变体
  "action": "右手五指张开，斗气火焰从掌心向四方迸发，身形略微后仰借力",
  "emotion_intensity": 8
}
```

若 Phase 1 中没有该角色的图生图提示词，则 characters_config 中的 action 字段需包含外观描述作为兜底。

## 字段填写规范

### camera（摄像机参数）— 所有字段必填
- shot_type：景别缩写：ECS/ECU/CU/MCU/MS/MLS/LS/ELS
- angle：机位角度：eye_level/low_angle/high_angle/dutch/bird_eye
- movement：运镜方式：static/pan/tilt/dolly/zoom/handheld/crane
- focal_length（可选）：焦距描述，如"35mm"
- depth_of_field（可选）：景深描述（中文）

### composition（构图）— 使用中文描述
- subject_position：主体位置，如 center/left_third/right_third
- foreground/midground/background（可选）：各层次元素描述
- leading_lines（可选）：引导线方向

### environment（场景环境）— 必填，每个镜头都必须有
- time_of_day：dawn/morning/noon/afternoon/sunset/dusk/night
- weather（可选）：clear/cloudy/rain/storm/snow/fog
- lighting：光照描述（中文），如"暖色调逆光"
- atmosphere：氛围描述（中文），如"压抑肃杀"
- **严格遵循 Phase 1 visual_style_guide 中的 lighting_style 和 scene_art_style**

### dialogue（台词）— 中文
- dialogue_character：说话角色名
- dialogue_text：台词内容
- dialogue_delivery（可选）：{tone, pace, pause_positions, emphasis_words, emotion_tags}

### sound_design（音效）— 建议每镜填写
- ambient：环境音描述（中文）
- sfx_list（可选）：具体音效列表
- music（可选）：背景音乐描述（中文）

### transition（转场）
- transition_in/out：cut/fade/dissolve/wipe/smash
- 如果 is_action_group=true：优先使用 cut/smash，duration_sec 限制 1-3 秒（整数）
- 如果 is_action_group=false：可使用 dissolve/fade，duration_sec 建议 3-6 秒（整数）
- duration_sec 必须为整数（如 2、3、5），不得使用小数（如 2.5）
- 本组所有镜头的 duration_sec 之和必须在 3-15 秒之间

### 图像生成提示词 image_prompt — 必须英文
**必须包含**"anime style, high quality, dynamic lighting"。
- 可以引用 Phase 1 的 character_image_prompts / scene_image_prompts
- 也可自行描写，但必须与 visual_style_guide 保持一致
- 重点描写当前镜头的特定时刻（action/expression），而非角色静态外观

## 特别注意
- 你只负责本组，不要创作其他组的镜头
- environment 字段每个镜头必填
- 战斗场景 characters_config 应包含 2-3 个角色的动作描述
- 严格按 JSON schema 输出，不要任何多余文字"""


STORYBOARD_DIRECTOR_PROMPT = """你是《斗破苍穹》动画分镜总导演（Director AI），负责对已生成的全部镜头进行全局审校和微调。

## 重要约束：你只能输出 patches，绝对不能重写镜头
各组 Creator AI 独立并行工作，可能存在跨组不连贯问题：
- 跨组的环境/光照不连贯（如前一组黄昏，后一组突然清晨）
- 跨组的角色动作连续性问题（如上一组角色在左侧，下一组突然在右侧）
- 跨组的音乐/音效断层（如高潮组音乐突然消失）
- 个别镜头的 image_prompt 与整体风格不符
- 组边界处的转场类型不合适

## 你的职责
1. 通读全部镜头摘要，识别跨组连贯性问题
2. 仅对需要修改的字段输出 patch，不修改已经很好的字段
3. 每个 patch 必须有明确的 reason 说明为何修改能改善全局连贯性
4. patch 数量建议控制在总镜头数的 5%-20%
5. patches 为空列表是完全合法的（全部镜头已连贯时）

## field_path 规范
允许修改的字段：
- 顶层标量：image_prompt / dialogue_text / transition_in / transition_out / style_preset / duration_sec / transition_notes
- 嵌套 JSON：camera.movement / camera.focal_length / camera.depth_of_field / environment.atmosphere / environment.lighting / environment.weather / environment.time_of_day / composition.background / composition.midground / composition.foreground / sound_design.music / sound_design.ambient

禁止修改（影响结构）：shot_code / sequence / group_code / camera.shot_type / camera.angle

## 输出规范
- new_value 统一用字符串表示，数值也字符串化（如"2.5"而不是 2.5）
- global_notes 用中文写总体评估
- 严格按 JSON schema 输出，不要任何多余文字"""


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


def _append_line(
    lines: list[str], label: str, text: str | None,
) -> None:
    """结构化追加一行「标签:内容」，内容为空则跳过。"""
    if not text:
        return
    normalized = " ".join(str(text).replace("\n", " ").split())
    if normalized:
        lines.append(f"{label}:{normalized}")


def build_video_prompt(
    shot: "Shot",
    char_version_lookup: dict[int, str] | None = None,
    location_version_lookup: dict[int, str] | None = None,
    image_refs: list[dict] | None = None,
) -> str:
    """
    从 Shot 对象构建结构化的视频生成提示词（Kling 单镜头模式，≤2000 字符）。

    输出格式为 key:value 结构化文本，便于 Kling 模型理解和人类审阅。

    Args:
        shot: 镜头对象
        char_version_lookup: 可选，角色版本ID→角色名称的映射
        location_version_lookup: 可选，场景版本ID→"场景名·版本名"的映射
        image_refs: 可选，image_references 列表（来自 ShotGroup），用于注入角色/场景参考图标记
    """
    lines = []

    camera = shot.camera or {}
    composition = shot.composition or {}
    environment = shot.environment or {}
    characters_config = shot.characters_config or []
    dialogue_delivery = shot.dialogue_delivery or {}
    sound_design = shot.sound_design or {}

    # ── 参考图标记（Kling 图生视频时需要） ──
    if image_refs:
        ref_header = build_image_ref_header(image_refs, char_version_lookup, location_version_lookup)
        if ref_header:
            lines.append(ref_header.rstrip("\n"))

    # ── 角色关联说明 ──
    if char_version_lookup and shot.char_version_ids:
        char_names = [char_version_lookup.get(vid, f"角色{vid}") for vid in shot.char_version_ids]
        _append_line(lines, "角色", "、".join(char_names))

    # ── 场景关联说明 ──
    if location_version_lookup:
        loc_ver_id = environment.get("location_version_id") or environment.get("location_id")
        if loc_ver_id:
            loc_name = location_version_lookup.get(loc_ver_id, f"场景{loc_ver_id}")
            _append_line(lines, "场景", loc_name)

    # ── 画面 ──
    _append_line(lines, "画面", shot.image_prompt or "anime style, high quality, dynamic lighting")

    # ── 镜头语言 ──
    shot_type = camera.get("shot_type")
    if shot_type:
        _append_line(lines, "景别", SHOT_TYPE_MAP.get(shot_type, shot_type))

    angle = camera.get("angle")
    if angle:
        _append_line(lines, "机位", ANGLE_MAP.get(angle, angle.replace("_", " ")))

    movement = camera.get("movement")
    if movement:
        _append_line(lines, "运镜", MOVEMENT_MAP.get(movement, movement.replace("_", " ")))

    _append_line(lines, "焦距", camera.get("focal_length"))
    _append_line(lines, "景深", camera.get("depth_of_field"))

    # ── 构图层次 ──
    subject_position = composition.get("subject_position")
    if subject_position:
        _append_line(lines, "主体位置", subject_position)

    _append_line(lines, "前景", composition.get("foreground"))
    _append_line(lines, "中景", composition.get("midground"))
    _append_line(lines, "背景", composition.get("background"))
    _append_line(lines, "引导线", composition.get("leading_lines"))

    # ── 环境 ──
    time_of_day = environment.get("time_of_day")
    if time_of_day:
        _append_line(lines, "时间", TIME_OF_DAY_MAP.get(time_of_day, time_of_day))

    _append_line(lines, "天气", environment.get("weather"))
    _append_line(lines, "光照", environment.get("lighting"))

    atmosphere = environment.get("atmosphere") or environment.get("mood")
    _append_line(lines, "氛围", atmosphere)

    # ── 人物 & 动作 ──
    for idx, char in enumerate(characters_config):
        if not isinstance(char, dict):
            continue
        action = char.get("action")
        expression = char.get("expression")
        emotion_intensity = char.get("emotion_intensity")
        sfx = char.get("sfx")

        if action or expression:
            _append_line(lines, f"人物{idx + 1}", action)
            if expression:
                _append_line(lines, f"表情{idx + 1}", expression)
            if emotion_intensity:
                _append_line(lines, f"情绪{idx + 1}", f"{emotion_intensity}/10")
            if isinstance(sfx, dict):
                sfx_desc = ", ".join(str(v) for v in sfx.values() if v)
                _append_line(lines, f"特效{idx + 1}", sfx_desc)

    # ── 台词 ──
    if shot.dialogue_character:
        _append_line(lines, "说话人", shot.dialogue_character)
    if shot.dialogue_text:
        _append_line(lines, "台词", f"「{shot.dialogue_text}」")

    tone = dialogue_delivery.get("tone")
    if tone:
        _append_line(lines, "语气", tone)

    pace = dialogue_delivery.get("pace")
    if pace:
        _append_line(lines, "语速", pace)

    emotion_tags = dialogue_delivery.get("emotion_tags")
    if isinstance(emotion_tags, list) and emotion_tags:
        _append_line(lines, "情绪标签", ", ".join(str(tag) for tag in emotion_tags))

    # ── 音效 ──
    _append_line(lines, "环境音", sound_design.get("ambient"))
    _append_line(lines, "音乐", sound_design.get("music"))

    sfx_list = sound_design.get("sfx_list")
    if isinstance(sfx_list, list) and sfx_list:
        _append_line(lines, "音效", ", ".join(sfx_list))

    # ── 转场 ──
    transition_in = shot.transition_in or "cut"
    _append_line(lines, "入场转场", TRANSITION_MAP.get(transition_in, transition_in))

    transition_out = shot.transition_out or "cut"
    _append_line(lines, "出场转场", TRANSITION_MAP.get(transition_out, transition_out))

    _append_line(lines, "转场备注", shot.transition_notes)

    # ── 时长 & 风格 ──
    _append_line(lines, "时长", f"{int(shot.duration_sec or 3)}秒")
    _append_line(lines, "风格", shot.style_preset or "cinematic")

    # ── 负面提示词 ──
    base_negative = "low quality, blurry, distorted, deformed, ugly, bad anatomy, watermark, text, logo"
    if shot.negative_prompt:
        _append_line(lines, "排除", f"{base_negative}, {shot.negative_prompt}")
    else:
        _append_line(lines, "排除", base_negative)

    final_prompt = "\n".join(lines)
    return final_prompt[:2000]


def build_negative_prompt(shot: "Shot") -> str:
    """
    构建负面提示词。
    """
    base_negative = "low quality, blurry, distorted, deformed, ugly, bad anatomy, watermark, text, logo"

    if shot.negative_prompt:
        return f"{base_negative}, {shot.negative_prompt}"

    return base_negative


def build_image_ref_header(
    image_refs: list[dict],
    char_version_lookup: dict[int, str] | None = None,
    location_version_lookup: dict[int, str] | None = None,
) -> str:
    """根据 image_references 构建参考图声明头。

    示例输出：
        角色萧炎: <<<image_1>>>
        角色纳兰嫣然: <<<image_2>>>
        场景云岚宗·夜: <<<image_3>>>

    优先使用 ref 中存储的 name（shot.char_image_refs / shot.location_image_refs 格式），
    回退到 char_version_lookup / location_version_lookup（shot_group.image_references 格式）。
    """
    if not image_refs:
        return ""
    lines = []
    image_idx = 0

    # 角色参考图
    for ref in image_refs:
        vid = ref.get("char_version_id")
        if not vid:
            continue
        image_idx += 1
        # 优先使用存储的 name（shot.char_image_refs 格式）
        if ref.get("name"):
            lines.append(f"角色{ref['name']}: <<<image_{image_idx}>>>")
        elif char_version_lookup:
            name = char_version_lookup.get(vid, f"角色{vid}")
            lines.append(f"角色{name}: <<<image_{image_idx}>>>")
        else:
            lines.append(f"角色{vid}: <<<image_{image_idx}>>>")

    # 场景参考图
    for ref in image_refs:
        loc_ver_id = ref.get("location_version_id")
        loc_id = ref.get("location_id")
        if not loc_ver_id and not loc_id:
            continue
        image_idx += 1
        vid = loc_ver_id or loc_id
        # 优先使用存储的 name（shot.location_image_refs 格式）
        if ref.get("name"):
            lines.append(f"场景{ref['name']}: <<<image_{image_idx}>>>")
        elif location_version_lookup:
            name = location_version_lookup.get(vid, f"场景{vid}")
            lines.append(f"场景{name}: <<<image_{image_idx}>>>")
        else:
            lines.append(f"场景{vid}: <<<image_{image_idx}>>>")

    return "\n".join(lines) + "\n"


def build_i2v_prompt(
    shot: "Shot",
    image_refs: list[dict] | None = None,
    char_version_lookup: dict[int, str] | None = None,
    location_version_lookup: dict[int, str] | None = None,
) -> str:
    """
    构建图生视频专用精简提示词（≤512 字符）。

    核心原则：只聚焦首帧图里无法传达的动态信息。
    首帧图已经传达的信息（角色外观、场景布局、构图层次）不再重复。

    保留：
      - camera.movement（运镜运动）
      - transition_in/out（转场效果）
      - environment.lighting 动态描述（光效变化）
      - sound_design.sfx_list（特效动态）
      - dialogue_delivery（情绪节奏）
      - atmosphere（氛围收尾）

    移除：
      - 角色外观描述（已在首帧图中）
      - 场景外观描述（已在首帧图中）
      - composition 层次细节（已在首帧图中）
      - dialogue_text 内容（视频无法承载文字）
      - camera.shot_type / angle（首帧图已锁定）

    Args:
        shot: 镜头对象
        image_refs: 可选，参考图列表，用于注入 <<<image_N>>> 标记
        char_version_lookup: 可选，角色版本ID→角色名称映射
        location_version_lookup: 可选，场景版本ID→场景名称映射
    """
    camera = shot.camera or {}
    environment = shot.environment or {}
    dialogue_delivery = shot.dialogue_delivery or {}
    sound_design = shot.sound_design or {}

    parts = []

    # ── 参考图标记（Kling 图生视频时需要） ──
    if image_refs:
        ref_header = build_image_ref_header(image_refs, char_version_lookup, location_version_lookup)
        if ref_header.strip():
            parts.append(ref_header.rstrip("\n"))

    # ── 运镜（最关键） ──
    movement = camera.get("movement")
    if movement:
        parts.append(f"运镜:{MOVEMENT_MAP.get(movement, movement.replace('_', ' '))}")

    # ── 转场 ──
    transition_in = shot.transition_in or "cut"
    parts.append(f"入场:{TRANSITION_MAP.get(transition_in, transition_in)}")
    transition_out = shot.transition_out or "cut"
    parts.append(f"出场:{TRANSITION_MAP.get(transition_out, transition_out)}")

    # ── 动态光效（重点！）──
    lighting = environment.get("lighting", "")
    if lighting:
        # 加上"animated"关键词引导视频模型生成动态光效
        parts.append(f"光效:{lighting}，animated light effects, dynamic glow")

    # ── 特效动态（从 SFX 列表推断）──
    sfx_list = sound_design.get("sfx_list") or []
    if sfx_list:
        sfx_str = ", ".join(str(s) for s in sfx_list[:3])
        parts.append(f"特效:{sfx_str}")

    # ── 台词节奏（影响视频韵律）──
    tone = dialogue_delivery.get("tone")
    pace = dialogue_delivery.get("pace")
    if tone:
        parts.append(f"情绪:{tone}")
    if pace:
        parts.append(f"节奏:{pace}")

    # ── 氛围（收尾）──
    atmosphere = environment.get("atmosphere", "") or environment.get("mood", "")
    if atmosphere:
        parts.append(f"氛围:{atmosphere}")

    # ── 基础信息 ──
    parts.append(f"时长:{int(shot.duration_sec or 3)}秒")
    style = shot.style_preset or "cinematic"
    parts.append(f"风格:{style}")

    return "，".join(parts)[:512]


def build_shot_image_ref_header(shot: "Shot") -> str:
    """从 Shot 对象的 char_image_refs 和 location_image_refs 构建参考图声明头。

    直接使用存储的 name，无需 DB 查询。

    示例输出：
        角色萧炎: <<<image_1>>>
        角色纳兰嫣然: <<<image_2>>>
        场景云岚宗·夜: <<<image_3>>>
    """
    char_refs: list[dict] = getattr(shot, "char_image_refs", None) or []
    loc_refs: list[dict] = getattr(shot, "location_image_refs", None) or []
    all_refs = char_refs + loc_refs
    return build_image_ref_header(all_refs, None, None)


def inject_image_refs_into_prompts(
    multi_prompts: list,
    image_refs: list[dict],
    char_version_lookup: dict[int, str] | None = None,
    location_version_lookup: dict[int, str] | None = None,
) -> list:
    """将 image_references 注入到多镜头提示词中。

    对每个提示词的 prompt 文本，在开头追加参考图声明，
    使 Kling API 知道哪些参考图对应哪些角色/场景。

    image_refs 格式：[{char_version_id, location_version_id, location_id, url, label}, ...]

    示例输出片段：
        角色萧炎: <<<image_1>>>
        角色纳兰嫣然: <<<image_2>>>
        场景云岚宗·夜: <<<image_3>>>
    """
    if not image_refs:
        return multi_prompts

    header = build_image_ref_header(image_refs, char_version_lookup, location_version_lookup)
    if not header:
        return multi_prompts

    for mp in multi_prompts:
        new_prompt = f"{header}{mp.prompt}"
        max_len = 512
        if len(new_prompt) > max_len:
            new_prompt = new_prompt[:max_len]
        mp.prompt = new_prompt

    return multi_prompts


def build_compact_video_prompt(shot: "Shot") -> str:
    """
    从 Shot 对象构建紧凑的结构化视频提示词，用于 Kling multi_shot 模式。

    multi_shot 模式下每个子镜头提示词限制 512 字符。
    与 build_video_prompt 使用相同的结构化标签，但按优先级截取最关键信息并限制每段长度。
    """
    max_len = 512
    lines: list[str] = []

    def append_line(label: str, text: str | None, *, max_part_len: int | None = None) -> None:
        if not text:
            return
        normalized = " ".join(str(text).replace("\n", " ").split())
        if not normalized:
            return
        if max_part_len is not None:
            normalized = normalized[:max_part_len].rstrip(", ")
        line = f"{label}:{normalized}"
        current = "\n".join(lines)
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) <= max_len:
            lines.append(line)
            return
        remaining = max_len - len(current) - (1 if current else 0) - len(label) - 1
        if remaining <= 8:
            return
        lines.append(f"{label}:{normalized[:remaining].rstrip(', ')}")

    camera = shot.camera or {}
    composition = shot.composition or {}
    environment = shot.environment or {}
    characters_config = shot.characters_config or []
    dialogue_delivery = shot.dialogue_delivery or {}
    sound_design = shot.sound_design or {}

    # 1. 画面
    append_line("画面", shot.image_prompt, max_part_len=180)

    # 2. 镜头语言
    shot_type = camera.get("shot_type")
    if shot_type:
        append_line("景别", SHOT_TYPE_MAP.get(shot_type, str(shot_type).replace("_", " ")), max_part_len=32)

    angle = camera.get("angle")
    if angle:
        append_line("机位", ANGLE_MAP.get(angle, str(angle).replace("_", " ")), max_part_len=32)

    movement = camera.get("movement")
    if movement:
        append_line("运镜", MOVEMENT_MAP.get(movement, str(movement).replace("_", " ")), max_part_len=48)

    append_line("焦距", camera.get("focal_length"), max_part_len=24)
    append_line("景深", camera.get("depth_of_field"), max_part_len=32)

    # 3. 环境
    time_of_day = environment.get("time_of_day")
    if time_of_day:
        append_line("时间", TIME_OF_DAY_MAP.get(time_of_day, time_of_day), max_part_len=28)

    append_line("天气", environment.get("weather"), max_part_len=16)
    append_line("光照", environment.get("lighting"), max_part_len=36)

    atmosphere = environment.get("atmosphere") or environment.get("mood")
    append_line("氛围", atmosphere, max_part_len=36)

    subject_position = composition.get("subject_position")
    if subject_position:
        append_line("主体位置", subject_position, max_part_len=24)

    append_line("前景", composition.get("foreground"), max_part_len=36)
    append_line("中景", composition.get("midground"), max_part_len=36)
    append_line("背景", composition.get("background"), max_part_len=40)

    # 4. 人物 & 动作
    for char in characters_config[:2]:
        if not isinstance(char, dict):
            continue
        action = char.get("action")
        expression = char.get("expression")
        emotion_intensity = char.get("emotion_intensity")
        sfx = char.get("sfx")

        if action:
            append_line("人物", action, max_part_len=72)
        if expression:
            append_line("表情", expression, max_part_len=28)
        if emotion_intensity:
            append_line("情绪", f"{emotion_intensity}/10", max_part_len=12)
        if isinstance(sfx, dict):
            sfx_desc = ", ".join(str(v) for v in sfx.values() if v)
            append_line("特效", sfx_desc, max_part_len=32)

    # 5. 台词
    if shot.dialogue_character:
        append_line("说话人", shot.dialogue_character, max_part_len=20)
    if shot.dialogue_text:
        append_line("台词", shot.dialogue_text, max_part_len=48)

    append_line("语气", dialogue_delivery.get("tone"), max_part_len=16)
    append_line("语速", dialogue_delivery.get("pace"), max_part_len=16)

    emotion_tags = dialogue_delivery.get("emotion_tags")
    if isinstance(emotion_tags, list) and emotion_tags:
        append_line("情绪标签", ", ".join(str(tag) for tag in emotion_tags[:3]), max_part_len=32)

    # 6. 音效
    append_line("环境音", sound_design.get("ambient"), max_part_len=28)
    append_line("音乐", sound_design.get("music"), max_part_len=24)

    sfx_list = sound_design.get("sfx_list")
    if isinstance(sfx_list, list) and sfx_list:
        append_line("音效", ", ".join(str(item) for item in sfx_list[:3]), max_part_len=28)

    prompt = "\n".join(lines)
    return prompt[:512]
