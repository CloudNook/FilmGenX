---
name: visual-style-anchors
description: Use when establishing the project's overall visual identity from outline + storyboard, defining art genre, color palette, lighting, composition, and per-element art rules so character_ref / scene_ref / frame_prompt all share one consistent visual prior.
target_agents: [visual_style_agent]
tags: [visual-direction, art-genre, color, lighting, composition]
author: filmgenx
---

# 视觉锚点设计

视觉锚点不是"挑一个好看的风格"，而是给整片定义一份**全局视觉先验**——色调、光照、构图、角色画风、场景画风、负面提示词——让下游所有出图 / 出视频环节都消费同一份语言，保证全片不"撞风格"。

本 skill 给 visual_style_agent 在 outline + storyboard 完成后输出 `VisualStyleGuide` 时的设计原则、决策路径和反例。

## 核心命题

`visual_style_agent` 接收：
- `outline.main`（剧情综述 + 主要角色 + 关键情节）
- 已完成的 storyboard
- `preference.*`（用户对题材 / 时长 / 节奏 / 结构的偏好）

输出一份 `VisualStyleGuide`，包含 8 个字段。**字段之间必须互相支撑，不能拼凑**。

## 八字段决策顺序

按这个顺序定，前面定下来后面才有依据，不要倒着想：

1. **art_genre** —— 全片美术大类。先看 outline 题材 + preference.genre：玄幻 → anime / pixar_3d；硬科幻 → photorealistic / cyberpunk；江湖武侠 → ghibli / watercolor；都市悬疑 → noir。
2. **overall_mood** —— 一句话的整体基调。**和 genre 必须自洽**：cyberpunk 不会"温暖治愈"；ghibli 不会"暗黑战斗"。
3. **color_palette** —— primary / secondary / accent / desaturation。primary 服务 mood；accent 给特效点睛；desaturation 偏 0.0-0.4，太高会失去画面层次。
4. **lighting_style** —— key / fill / practical / time_of_day。和 genre 配套：noir 要硬光 + 大反差；watercolor 要柔光 + 高 fill；pixar_3d 要动画感分层光。
5. **composition_style** —— framing / depth / rule_of_thirds 策略。**和 storyboard 已经给的镜头表对齐**——如果 storyboard 多用 OTS / CU，这里就别选"宏大全景为主"。
6. **character_art_style** —— proportions / linework / expression。anime 的 proportions ≠ pixar_3d 的；photorealistic 不允许变形夸张。
7. **scene_art_style** —— architecture / environment_detail / weather_atmosphere。和 outline 的场景设定对齐：玄幻多山门 / 都市多街景。
8. **negative_anchor** —— 全局负面 prompt。把"不允许出现的风格"写死，挡 SD/Gemini 滑向常见误区：写实风的工程要明确禁止 anime；动画风工程要禁止 photorealistic / overly grainy。

## 决策原则

- **一致性 > 漂亮**：8 个字段必须围绕同一个 mood 彼此印证。出现矛盾立刻改，不要"两个都好看就都留"。
- **可执行 > 文采**：每个字段的 description 要能直接喂给 SD / Gemini Image。"暗黑、压抑、史诗级"是文学描述；"硬光 key + 低 fill + 高对比 + 蓝绿色环境光"是可执行描述。
- **复用 > 创造**：80% 的项目都能落到 7 个预设 ArtGenre 里；不要轻易选 `custom`，custom 会让下游加载锚定失败。
- **服务剧情**：如果 outline 是"小人物逆袭"，就别选"史诗级镜头语言"——视觉要服务情绪，不是炫技。

## 反例（出现就要回去重做）

- art_genre=`pixar_3d` + lighting=`noir 高反差硬光` —— 风格分裂
- art_genre=`watercolor` + character_art_style.linework=`极细数字硬边` —— 互相打架
- color_palette.primary 和 secondary 是同色系（都偏冷蓝）—— 没张力，画面发闷
- negative_anchor 留空 —— 下游必定会跑偏到常见误区
- composition_style 和 storyboard 已选的镜头表不一致 —— 浪费上游劳动

## 何时加载附加资料

按需触发工具调用，不要预先全部加载：

- 当你在 art_genre 之间纠结、不确定 cyberpunk 和 noir 的边界时 → 加载 @ref:art-genre-decision-tree
- 当 color_palette 字段难以落地、不知道 primary/secondary/accent 怎么搭配时 → 加载 @ref:color-palette-recipes
- 当 lighting_style 不知道 key/fill/practical 怎么写才"可执行"时 → 加载 @ref:lighting-style-cookbook

## 工作流（强调：调工具前先说为什么）

**重要**：每次准备调用 `load_skill_reference` / `load_skill` / `memory_save` / 任何工具前，**先在当前回复里口头说明**：

> "我现在需要加载 @ref:color-palette-recipes，因为剧情是科幻短剧但 art_genre 我打算选 cyberpunk，这个 reference 能给我具体的色彩配方。下一步我就调用这个工具。"

然后**结束当前发言**，等下一轮再发起 tool_call。**不要在同一轮里既宣告又调用**——这是 supervisor 工作流要求的可解释性约定，让人类审阅者能跟上你的判断。

## reference: art-genre-decision-tree

7 个预设 art_genre 的分边界、典型场景、负面提示词模板：

### anime
- **典型**：玄幻 / 修仙 / 战斗番。中日韩动漫审美。
- **关键词**：cel shading、saturated colors、dynamic poses、speed lines。
- **负面**：no realistic skin pores、no photorealistic、no western fantasy。
- **不要选**：硬科幻、严肃悬疑。

### photorealistic
- **典型**：现代都市剧、纪实风短片、明星广告。
- **关键词**：high detail、true-to-life lighting、natural skin texture、35mm grain。
- **负面**：no anime、no cartoon、no toon shading。
- **不要选**：玄幻、奇幻。会让"飞剑斗法"看起来像 cosplay 翻车现场。

### pixar_3d
- **典型**：合家欢、儿童向、温情科幻。
- **关键词**：subsurface scattering skin、stylized proportions、warm rim light。
- **负面**：no photorealistic、no horror、no excessive grime。
- **不要选**：暗黑战斗（出戏）、严肃武侠。

### ghibli
- **典型**：自然 / 治愈 / 日常奇幻。东方风景 + 慢节奏。
- **关键词**：painterly background、soft watercolor textures、lush nature、whimsical creatures。
- **负面**：no harsh shadows、no metallic textures、no cyberpunk neon。
- **不要选**：高对抗动作戏。

### cyberpunk
- **典型**：未来都市、AI 反乌托邦、霓虹夜景。
- **关键词**：neon signs、rain-slick streets、teal-and-orange palette、holographic UI。
- **负面**：no daylight outdoor、no rural、no warm wood texture。
- **不要选**：温馨家庭剧、田园风。

### noir
- **典型**：黑色悬疑、侦探片、高反差对话戏。
- **关键词**：venetian blind shadows、low-key lighting、monochrome with red accent、smoky interior。
- **负面**：no bright sunlight、no saturated colors、no anime。
- **不要选**：动作番、轻喜剧。

### watercolor
- **典型**：诗意散文、童话、回忆段落。
- **关键词**：visible brushstrokes、wet edges、soft saturation、paper texture。
- **负面**：no sharp digital lines、no metallic、no neon。
- **不要选**：硬科幻、激烈战斗。

### 决策路径

1. outline 题材是现代 / 写实 → photorealistic 或 noir（看是否暗黑）
2. outline 题材是奇幻 / 玄幻 / 修仙 → anime（动作戏多） / ghibli（治愈） / pixar_3d（合家欢）
3. outline 题材是科幻 → cyberpunk（未来都市暗调） / photorealistic（硬科幻）/ pixar_3d（轻科幻）
4. outline 题材是诗意 / 回忆 / 心理 → watercolor / ghibli
5. 实在不匹配预设 → custom，但必须在 negative_anchor 写得极其详细，否则下游必跑偏

## reference: color-palette-recipes

按 art_genre 给的标准色彩配方（primary / secondary / accent / desaturation）：

| genre | primary | secondary | accent | desaturation |
| --- | --- | --- | --- | --- |
| anime（玄幻战斗） | 深红 + 橙黄（斗气） | 冷蓝（冰系阴影） | 金紫（异火 / 异能） | 0.2 |
| anime（治愈） | 暖粉 + 米白 | 浅蓝 | 樱粉 | 0.3 |
| photorealistic（都市） | 中性灰 + 棕 | 冷蓝（窗外天空） | 暖橙（人造光源） | 0.3 |
| pixar_3d | 高饱和暖色（橙 / 黄） | 互补冷色（青 / 紫） | 鲜亮 accent | 0.0 |
| ghibli | 草绿 + 天蓝 | 米白 + 木棕 | 红屋顶 / 黄花 | 0.4 |
| cyberpunk | 深蓝 + 紫黑 | 霓虹粉 / 青 | 酸黄 / 电光蓝 | 0.2 |
| noir | 几乎黑白 | 深棕 / 烟灰 | **单一红** 点睛 | 0.85 |
| watercolor | 柔米色 + 浅水蓝 | 苔绿 / 暖灰 | 朱砂红 / 藏青 | 0.5 |

### 配方规则

- primary 占画面 60%，secondary 30%，accent 10%。
- accent 必须是**单一**色：红就只用红，金就只用金。多个 accent 会让画面"脏"。
- desaturation 0 = 纯饱和（pixar / 童话），0.2-0.4 = 主流叙事，0.5-0.7 = 文艺 / 回忆，0.85+ = noir / 黑白。
- 同色系不能进 primary + secondary：都冷或都暖会让画面没张力。

## reference: lighting-style-cookbook

把光照写得"可执行"的 4 个维度模板：

### key_light（主光）

- 硬光（hard）：太阳直射 / 顶灯。强阴影边缘。**用于**：noir、cyberpunk 夜戏、戏剧性时刻。
- 柔光（soft）：散射 / 反射。无明显阴影。**用于**：ghibli、pixar、对话日常戏。
- 边缘光（rim）：背光勾边。**用于**：anime 战斗 high-key、photorealistic 人物特写。

### fill_light（补光）

- 低 fill（fill ratio 1:8 ~ 1:16）= 高反差，暗部沉。noir / cyberpunk / 严肃戏。
- 中 fill（1:4 ~ 1:8）= 主流叙事。photorealistic / pixar 日常。
- 高 fill（1:2 ~ 1:4）= 平光，温馨柔和。ghibli / watercolor / 治愈戏。

### practical_sources（场景灯）

- 实用光源（屏幕 / 灯具 / 蜡烛 / 火焰）必须在 prompt 里**写明位置和颜色**。否则下游 SD 会自动加，但位置不可控。
- cyberpunk 必须有：霓虹招牌 / 全息屏 / 街灯。
- noir 必须有：百叶窗光 / 烟雾 / 单点台灯。
- ghibli 必须有：户外日光 / 室内炉火（暖橙）。

### default_time_of_day

- magic hour（金时刻 / 日落前 1h）：万能选项，最讨巧。
- noon：硬影子，戏剧性强。
- night：逼着你思考 practical_sources。
- 全片**只定一个 default**，例外镜头单独讨论。

### 完整示例（cyberpunk 短剧）

```
key: hard rim light from neon sign, magenta + cyan
fill: 1:8 ratio, deep shadows in lower half
practical: rooftop hologram display (cyan), street lamps (warm sodium yellow), wet asphalt reflection
default_time_of_day: night, post-rain
```

下游 SD / Gemini 拿到这一段直接能吃，不用再脑补。
