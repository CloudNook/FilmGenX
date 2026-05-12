/**
 * 示例 SKILL.md 模板，对应 supervisor sub-agent。
 *
 * 仓库 canonical 版本在 ``docs/skills/examples/*.md``，这份是前端 "新建 Skill" 对话框
 * 的内置快速模板，方便 admin 一键插入起点内容。两份内容应保持同步：
 * 修改其中一份后，把改动同步到另一份（diff 区域很小，按需手工对齐即可）。
 */

export interface SkillSample {
  /** 显示名（dropdown 用） */
  label: string;
  /** sub-agent 归属，仅做展示 */
  targetAgent: string;
  /** 完整 SKILL.md 文本（包含 frontmatter 和 body） */
  markdown: string;
}

const NARRATIVE_STRUCTURE = `---
name: narrative-structure
description: Use when designing story outlines or evaluating narrative pacing to ensure three-act structure, clear stakes, and meaningful turning points.
target_agents: [outline_agent]
tags: [storytelling, structure, three-act]
author: filmgenx
---

# 三幕结构与叙事节奏

经典三幕结构是商业叙事的骨架。它解释每一段情节为什么存在、节奏是否平衡、转折点是否扎实。
本 skill 给 outline_agent 在写大纲时提供三幕的功能描述、关键节拍和写作禁忌。

## 三幕的功能

- **第一幕（建置）**：占总长度 20-25%。建立主角日常、内在缺失、激励事件、第一转折点。观众必须在前 10-15% 看到一个"打破日常"的事件。
- **第二幕（对抗）**：占 50-55%。主角追求外在目标，遇到障碍升级，在中点发生重大反转，跌入低谷，第二转折点带来内在转变。
- **第三幕（解决）**：占 20-25%。最终对抗、高潮、落幕。主角的内在改变与外在胜利同时发生。

## 关键节拍清单

写大纲时逐项检查以下节拍是否成立：

- 激励事件 (inciting incident)：在前 10-15% 出现
- 第一转折点 (plot point 1)：第一幕末尾，主角主动承诺
- 中点 (midpoint)：第二幕中段，发生伪胜利或伪失败
- 第二转折点 (plot point 2)：第二幕末尾，跌入低谷但获得内在转变
- 高潮 (climax)：第三幕，主角弧线 + 外部目标双完成
- 落幕 (denouement)：留白与新平衡

## 写作禁忌

- 第一幕铺垫超过 30% 导致中段塌陷
- 主角没有"想要 vs 需要"的双层欲望
- 中点没有反转，只是"剧情继续推进"
- 高潮靠外部力量解决，不是主角弧线驱动
- 主题靠台词宣讲，不是通过情节自然展开

## 何时加载附加资料

按以下规则**按需**触发工具调用，不要预先全部加载：

- 当你要落具体到每一幕的开场画面、节拍顺序、转折点位置时 → 加载 @ref:act-templates，拿到三幕的标准节拍模板（共 17 个步骤）
- 当你设计主角变化曲线、选择故事是"成长 / 立场坚守 / 走向毁灭"哪种走向时 → 加载 @ref:character-arc-frameworks，看正向 / 平面 / 负向三种弧线的适用场景

## reference: act-templates

第一幕模板：

1. 开场画面（建立基调与主角日常）
2. 主题陈述（通常由配角说出，主角不接受）
3. 建置（介绍世界、关键人物）
4. 激励事件（外部事件打破日常）
5. 拒绝召唤（主角抗拒变化）
6. 第一转折点（主角承诺追求目标）

第二幕 A 模板（前半）：

7. 进入新世界
8. B 故事登场（爱情线 / 友谊线 / 师徒线）
9. 玩耍与挑战（节奏可松一些）
10. 中点（伪胜利或伪失败，改变主角内心）

第二幕 B 模板（后半）：

11. 反派加压（外部力量升级）
12. 失去一切（盟友散去 / 计划破产）
13. 灵魂黑夜（主角内在低谷）
14. 第二转折点（顿悟，找到内在转变）

第三幕模板：

15. 完成最终对抗（主角主动出击）
16. 高潮（内在 + 外在双完成）
17. 落幕（新平衡 / 主题回响）

## reference: character-arc-frameworks

正向弧线 (Positive Arc)：

主角持有错误信念 → 在追求目标中被逐渐击碎 → 接受真相 → 行动改变 → 战胜反派
适合：英雄之旅、成长故事、商业大片

平面弧线 (Flat Arc)：

主角已经持有真理 → 用真理改变世界 → 让反派或盟友最终认同
适合：偶像剧、奇幻原型、动漫主角

负向弧线 (Negative Arc)：

主角持有错误信念 → 拒绝真相 → 拥抱谎言 → 走向毁灭
适合：悲剧、犯罪片、反英雄
`;

const DIALOGUE_CRAFT = `---
name: dialogue-craft
description: Use when writing or revising scene dialogue to ensure each character has a recognizable voice, subtext drives meaning, and information is delivered through conflict rather than exposition.
target_agents: [script_agent]
tags: [dialogue, scriptwriting, voice, subtext]
author: filmgenx
---

# 对白工艺

电影 / 电视的对白不是日常对话；每一句台词都要服务角色塑造、推进冲突、或埋伏后续情节。
本 skill 给 script_agent 在写场景时提供常用的对白原则、反例和检查清单。

## 三大原则

- **角色化 (Voice)**：每个角色说话的句长、词汇、节奏可被识别。盲读时观众能猜出是谁。
- **潜台词 (Subtext)**：角色说 A 但意思是 B。冲突 / 欲望 / 恐惧通过潜台词传达，而不是直白宣告。
- **冲突驱动 (Conflict)**：每一段对白都要有目标对立。无目的的"闲聊"应当删除或合并。

## 反例（写完一定回头检查）

- **互相讲对方已知的事**："你知道我父亲三年前死了吗？" "嗯，我们一起参加的葬礼。" — 信息倾倒
- **过度直白**：角色把心理活动直接说出来，没有潜台词
- **泛角色腔**：所有人说话腔调一致，无法区分
- **现代俚语乱入**：除非风格设定明确允许，否则破坏世界观
- **超长独白**：超过 4 行的台词必须有戏剧理由（人物的演讲时刻、自白）

## 角色化检查清单

写完一场戏后，逐句检查：

1. 这句话的目标是什么？（说服 / 逼迫 / 试探 / 回避 / 调情 / 攻击）
2. 角色真正想说的是什么？台面上和心里是否不一致？
3. 这句话能换给另一个角色说吗？如果能，说明角色化不够。
4. 信息是通过冲突自然传达的，还是被生硬解释的？
5. parenthetical（表演提示）有没有在写台词已经表达的情绪？克制使用。

## 何时加载附加资料

按以下规则**按需**触发工具调用，不要预先全部加载：

- 当你要写"角色不直说"、需要靠对白让观众读出隐藏冲突或情绪时 → 加载 @ref:subtext-techniques，拿到四种常用潜台词手法（偏移 / 过度礼貌 / 沉默 / 第三方代言）的具体范例
- 当你不确定场景头格式、时间段词、INT/EXT 写法、或者需要按页数估算成片时长时 → 加载 @ref:scene-format-spec

## reference: subtext-techniques

偏移 (Deflection)：

角色不直接回答，转移话题或反问。
> A: 你昨晚在哪里？
> B: 你今天的咖啡又没加糖吧。
潜台词：B 在隐瞒，但不愿正面对抗。

过度礼貌 (Hyper-politeness)：

强调礼节往往暗示敌意或距离。
> "如果不太麻烦您的话，能否劳驾把那份文件递给我。"
潜台词：愤怒被压抑成形式礼仪。

沉默 (Silence)：

没有回答 = 最强的回答。剧本里写 (beat) 或 (...) 让演员表演。

第三方代言：

角色通过谈论第三人来谈论自己。
> "我隔壁家那个女人啊，她丈夫一直骗她。她明明知道，但就是不肯走。"
潜台词：B 在说自己。

## reference: scene-format-spec

标准场景头格式：\`INT./EXT. 地点 - 时间\`

常见形式：

- \`INT. 地铁站台 - 夜\`
- \`EXT. 海滩 - 黎明\`
- \`INT./EXT. 出租车 - 日 - 行驶中\`

时间词：DAY / NIGHT / DAWN / DUSK / CONTINUOUS / LATER

每场戏必须能用一句话回答："这场戏推进了什么？"
不能回答的场景应合并或删除。

行业惯例：1 页剧本 ≈ 1 分钟成片，可用作时长估算。
`;

const CINEMATIC_COMPOSITION = `---
name: cinematic-composition
description: Use when designing storyboards or evaluating shot lists to ensure each frame uses composition, lensing, and camera movement intentionally to support emotion and rhythm.
target_agents: [storyboard_agent]
tags: [cinematography, composition, shot-language]
author: filmgenx
---

# 镜头语言与构图

镜头不是"把场景拍下来"，而是用景别、机位、运动、构图来表达情绪和节奏。
本 skill 给 storyboard_agent 在设计分镜时提供构图原则、镜头选择逻辑和节奏控制策略。

## 三层考虑

每一个镜头都要在三个维度做出决定：

1. **景别**：远景给信息，近景给情绪。变化越大冲击越强。
2. **构图**：主体位置、引导线、纵深、留白共同决定观众视线和心理感受。
3. **运动**：静止 = 稳定；横移 = 跟随；推进 = 介入；摇晃 = 不安。

## 构图原则

- **三分法 (Rule of thirds)**：主体落在 1/3 线交点，画面活跃
- **引导线 (Leading lines)**：用建筑、地平线、肢体引导观众视线到主体
- **三层纵深**：每个镜头至少包含前景 / 中景 / 背景两层，营造空间感
- **留白 (Negative space)**：主体周围留出"呼吸空间"，反映情绪状态
- **轴线 (180° rule)**：相邻镜头不跨轴，除非有明确叙事意图（如表现混乱、迷失）

## 节奏控制

- **紧张戏 / 动作戏**：1-3 秒短切；快速景别变化（MS → CU → ECU）；手持或斜机位
- **抒情戏 / 仪式感**：4-8 秒长镜；缓慢横移；对称构图；静止机位
- **对话戏**：OTS 来回，关键台词上 CU；切忌从头到尾用一个景别
- **战斗戏**：穿插一个长镜头收尾，给观众喘息

## 反例

- 全片同景别（节奏死板）
- 紧张戏配长镜头、抒情戏配急摇（情绪不匹配）
- 跨轴而无叙事理由（观众迷失方向）
- 没有留白，画面塞满（视觉疲劳）
- 镜头之间动作不接（剪辑生硬）

## 何时加载附加资料

按以下规则**按需**触发工具调用，不要预先全部加载：

- 当你要给某个具体镜头选定景别、纠结 ECU 还是 CU 还是 MS 时 → 加载 @ref:shot-types-cheatsheet，拿到 10 种景别的中英对照表和适用场景
- 当你要给镜头配机位运动、纠结 dolly 还是 zoom 还是 pan、或不确定手持是否合适时 → 加载 @ref:camera-movement-guide，看每种运动的情绪含义和禁忌

## reference: shot-types-cheatsheet

| 缩写 | 全称 | 作用 |
| --- | --- | --- |
| ELS | Extreme Long Shot 大远景 | 展示环境 / 史诗感 / 孤立感 |
| LS | Long Shot 远景 | 全身 + 周围环境 |
| FS | Full Shot 全景 | 全身 |
| MS | Medium Shot 中景 | 半身，对话基础景别 |
| MCU | Medium Close-up 中近景 | 胸口以上 |
| CU | Close-up 特写 | 头部特写，情绪 |
| ECU | Extreme Close-up 大特写 | 眼睛 / 手指，强烈情绪 |
| OTS | Over-the-shoulder 过肩 | 双人对话标配 |
| POV | Point of View 主观 | 角色视角，代入感 |
| INSERT | 插入镜头 | 关键道具特写 |

## reference: camera-movement-guide

静止 (Static)：

中性、稳定。对话戏 / 仪式感 / 对称构图首选。

摇 (Pan / Tilt)：

横摇 = 跟随主体或揭示空间；俯仰 = 强调高度差或权力关系。仰拍 = 权威 / 压迫；俯拍 = 弱势 / 全局。

推拉 (Dolly)：

推进 = 介入角色情绪；拉远 = 抽离 / 揭示孤立感。和 zoom 不同：dolly 改变了视角和透视，zoom 没有。

横移 (Truck)：

跟随平行运动，最常用于角色行走或跑动。

升降 (Crane)：

开场或结尾，营造仪式感或视角转换。预算允许时极有冲击力。

手持 / Steadicam：

紧张戏 / 第一人称 / 现实主义；轻微抖动给真实感，过度抖动出戏。

急摇 (Whip pan)：

快速衔接 / 动作戏过渡 / 时空跳跃。常用作转场。

变焦 (Zoom)：

慎用。zoom in 强调心理变化（不是物理移动）；zoom out 揭示情境。复古、电视感，剧情片少用。
`;

const VISUAL_STYLE_ANCHORS = `---
name: visual-style-anchors
description: Use when establishing the project's overall visual identity from outline + storyboard, defining art genre, color palette, lighting, composition, and per-element art rules so character_ref / scene_ref / video_prompt all share one consistent visual prior.
target_agents: [visual_style_agent]
tags: [visual-direction, art-genre, color, lighting, composition]
author: filmgenx
---

# 视觉锚点设计

视觉锚点不是"挑一个好看的风格"，而是给整片定义一份**全局视觉先验**——色调、光照、构图、角色画风、场景画风、负面提示词——让下游所有出图 / 出视频环节都消费同一份语言，保证全片不"撞风格"。

本 skill 给 visual_style_agent 在 outline + storyboard 完成后输出 \`VisualStyleGuide\` 时的设计原则、决策路径和反例。

## 核心命题

\`visual_style_agent\` 接收：
- \`outline.main\`（剧情综述 + 主要角色 + 关键情节）
- 已完成的 storyboard
- \`preference.*\`（用户对题材 / 时长 / 节奏 / 结构的偏好）

输出一份 \`VisualStyleGuide\`，包含 8 个字段。**字段之间必须互相支撑，不能拼凑**。

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
- **复用 > 创造**：80% 的项目都能落到 7 个预设 ArtGenre 里；不要轻易选 \`custom\`，custom 会让下游加载锚定失败。
- **服务剧情**：如果 outline 是"小人物逆袭"，就别选"史诗级镜头语言"——视觉要服务情绪，不是炫技。

## 反例（出现就要回去重做）

- art_genre=\`pixar_3d\` + lighting=\`noir 高反差硬光\` —— 风格分裂
- art_genre=\`watercolor\` + character_art_style.linework=\`极细数字硬边\` —— 互相打架
- color_palette.primary 和 secondary 是同色系（都偏冷蓝）—— 没张力，画面发闷
- negative_anchor 留空 —— 下游必定会跑偏到常见误区
- composition_style 和 storyboard 已选的镜头表不一致 —— 浪费上游劳动

## 何时加载附加资料

按需触发工具调用，不要预先全部加载：

- 当你在 art_genre 之间纠结、不确定 cyberpunk 和 noir 的边界时 → 加载 @ref:art-genre-decision-tree
- 当 color_palette 字段难以落地、不知道 primary/secondary/accent 怎么搭配时 → 加载 @ref:color-palette-recipes
- 当 lighting_style 不知道 key/fill/practical 怎么写才"可执行"时 → 加载 @ref:lighting-style-cookbook

## 工作流（强调：调工具前先说为什么）

**重要**：每次准备调用 \`load_skill_reference\` / \`load_skill\` / \`memory_save\` / 任何工具前，**先在当前回复里口头说明**：

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

\`\`\`
key: hard rim light from neon sign, magenta + cyan
fill: 1:8 ratio, deep shadows in lower half
practical: rooftop hologram display (cyan), street lamps (warm sodium yellow), wet asphalt reflection
default_time_of_day: night, post-rain
\`\`\`

下游 SD / Gemini 拿到这一段直接能吃，不用再脑补。
`;

const CHARACTER_DESIGN = `---
name: character-design
description: Use when designing character reference packs (base appearance + expression set + clothing + accessories) so every downstream shot can render the same character consistently. Provides decision rules for proportion / linework / expression coverage and prompt patterns for image generation.
target_agents: [character_ref_agent]
tags: [character-design, reference-image, prompt-engineering]
author: filmgenx
---

# 角色形象设计

角色形象设计的目标不是"画一个好看的人"，而是**把每个角色的视觉锚点钉死**——让后续每个镜头看到角色名都能直接复用同一套外观描述，不出现"长不一样"的灾难。

本 skill 给 character_ref_agent 在出 \`\`CharacterRefSet\`\` 时的设计原则、出图 prompt 模板、以及表情 / 服装变体的覆盖规则。

## 一致性的本质

角色"长不一样"通常是因为：
- **base_prompt 含动作 / 表情** → 每次生成都被动作姿态干扰
- **关键特征顺序不稳定** → 模型每次抓到的"这个角色是什么"不同
- **缺少 negative_prompt** → 被生成器的常见误区拉走（女主被画成男主、成人被画成少年）
- **服装描述跟身体描述混在一起** → 换装时连身体也变了

## base_prompt 的标准结构

按这个固定顺序写，能最大化模型的一致性：

\`\`\`
{年龄段} + {性别} + {发型 + 发色} + {瞳色} + {体型} + {核心服装} + {核心特征 / 招牌道具} + {风格关键词}
\`\`\`

例：
\`\`\`
青年男子, 黑色长发束起, 黑色瞳孔, 偏瘦修长身形, 玄铁色长袍战服, 背负玄重尺,
anime cel shading style
\`\`\`

**禁止**在 base_prompt 出现：表情（皱眉 / 微笑）、动作（站立 / 奔跑）、视角（正面 / 侧面）、特定光照。这些都是变体的工作。

## 三视图 prompt 公式

\`\`\`
{base_prompt}, three view sheet, front view + side view + back view,
neutral pose, neutral expression, full body, plain white background, T-pose
\`\`\`

固定参数：\`\`aspect_ratio="9:16"\`\`（角色竖图标准）、\`\`model="gemini-3-pro-image-preview"\`\`（主角必 pro）。

## 表情变体设计

### 主角必有 4-5 种

按情感弧线挑，不要全是相邻表情：

| 表情 key | 何时用 | prompt 片段示例 |
| --- | --- | --- |
| determined | 决心做某事 / 战斗前 | 紧抿嘴角, 瞳孔聚焦, 微皱眉 |
| angry | 受辱 / 仇恨爆发 | 眉心紧锁, 露出獠牙或咬牙, 瞳孔放大 |
| sad | 失去 / 悲伤 | 眉尾下垂, 眼神空洞, 唇角下拉 |
| surprised | 突变 / 意外 | 瞳孔瞪大, 嘴微张, 眉毛抬高 |
| smile | 胜利 / 释然 | 嘴角上扬, 眼神柔和 |

主角必须有 \`\`determined\`\` + 一种负面情绪（angry / sad）+ 一种正面情绪（smile / surprised）。这是叙事最低覆盖。

### 配角 1-3 种

按"该角色在剧情里只表现哪几种情绪"决定。例如纯反派可能只需要 \`\`angry\`\` + \`\`shocked\`\`。

## 服装与配件

**clothing_detail 与 base_prompt 分开**，让换装可独立替换：

- base_prompt 里只写"核心服装"（角色无论什么场合都穿的——比如玄铁色长袍是萧炎的常服）
- clothing_detail 字段写"本次场景的具体服装"（战斗服 / 日常服 / 礼服 / 受伤后的破损版）

**accessories 必须独立列**，因为模型很容易遗漏：
- 武器（玄重尺 / 法剑 / 手枪）
- 首饰（项链 / 耳环 / 戒指）
- 标志性道具（眼镜 / 拐杖 / 怀表）

如果不单独列，prompt 一长就被压缩到"忘了"。

## negative_prompt 必含项

按角色性别 / 年龄写防误生成：

| 角色类型 | negative_prompt 必含 |
| --- | --- |
| 男主 / 男配 | \`\`female, woman, child, makeup, breasts\`\` |
| 女主 / 女配 | \`\`male, man, child, beard, muscular\`\` |
| 成年角色 | \`\`child, kid, baby, teenager\`\` |
| 少年角色 | \`\`adult, mature, beard\`\` |
| 凡人角色 | \`\`glowing eyes, magical aura, fantasy effects\`\` |

外加 art_genre 通用负面：anime 加 \`\`photorealistic, realistic skin texture\`\`；photorealistic 加 \`\`anime, cartoon, illustration\`\`。

## 反例

- base_prompt 写"萧炎，黑发，正在挥舞玄重尺"——含动作了
- 全部 expressions 用同样句式"皱眉 + xxx"——伪变体
- accessories 漏掉招牌武器——后续战斗镜头武器消失
- negative_prompt 只写 art_genre 通用项，没写性别——男主被画成女主
- name 和 outline 不一致（"陆沉"写成"陆沉君"）——下游引用断链

## 工作流（强调先口头说明再调用工具）

每次准备调 \`\`load_skill_reference\`\` / \`\`generate_image\`\` / \`\`memory_save\`\`，都要：
1. 本轮先口头说明意图 + 理由
2. 下一轮才调工具

例：
> "我注意到萧炎是 anime 风格的玄幻男主，需要 4 张表情变体（determined / angry / smile / surprised）。下一步我会先调 \`\`load_skill_reference(skill='character-design', ref_key='expression-prompt-cookbook')\`\` 拿到具体的表情 prompt 片段模板，再回来写 expressions 字段。"

## reference: expression-prompt-cookbook

5 种核心表情的 prompt 片段（中文 + 英文 anime tag），可直接拼到角色变体里：

### determined（决心 / 战斗前）

\`\`\`
中文: 紧抿嘴角, 瞳孔聚焦, 微皱眉, 下颌微抬, 眼神锐利
英文 tag: serious face, focused eyes, slight frown, tight lips, intense gaze
\`\`\`

适用：战斗前夜、做出决定、面对反派。

### angry（愤怒 / 仇恨）

\`\`\`
中文: 眉心紧锁, 咬牙切齿, 瞳孔放大, 青筋微现, 嘴角下扯
英文 tag: angry expression, gritted teeth, furrowed brow, dilated pupils, snarling
\`\`\`

适用：受辱、仇恨爆发、被背叛。

### sad（悲伤 / 失落）

\`\`\`
中文: 眉尾下垂, 眼神空洞, 唇角下拉, 眼眶微红, 头微低
英文 tag: sad face, downturned mouth, teary eyes, drooping eyebrows, downward gaze
\`\`\`

适用：失去亲人、求而不得、回忆旧伤。

### surprised（惊讶 / 震惊）

\`\`\`
中文: 瞳孔瞪大, 嘴微张, 眉毛抬高, 头部微后仰, 表情僵住
英文 tag: shocked face, wide eyes, open mouth, raised eyebrows, surprised expression
\`\`\`

适用：突发事件、意外发现、剧情反转。

### smile（微笑 / 胜利）

\`\`\`
中文: 嘴角上扬, 眼神柔和, 微眯眼, 下颌微抬, 神情释然
英文 tag: gentle smile, soft eyes, slight smirk, relaxed face, content expression
\`\`\`

适用：胜利、释然、温情时刻。

### 反派专用：cold_smile（冷笑 / 优越）

\`\`\`
中文: 嘴角单边上扬, 眼神锐利, 下巴微抬, 冷漠的笑意
英文 tag: smirk, cold smile, raised chin, disdainful eyes, condescending expression
\`\`\`

适用：反派出场、傲慢宣言、阴谋得逞。

## reference: art-genre-character-proportions

不同 art_genre 对角色 proportion / linework 的要求：

### anime（玄幻战斗番）

- proportion: 7-7.5 头身（少年）/ 8-8.5 头身（成年战士）；夸张瞳孔（占脸 1/4）
- linework: clean cel shading，硬边阴影 2-3 层，无柔光过渡
- 标准 prompt 关键词: \`\`anime style, cel shaded, sharp linework, large expressive eyes, dynamic poses\`\`

### photorealistic（都市 / 写实）

- proportion: 真人 7.5-8 头身，正常脸部比例
- linework: 无明显线条，靠光影建模
- 标准 prompt 关键词: \`\`photorealistic, true-to-life proportions, natural skin texture, 35mm, sharp focus, soft natural lighting\`\`
- 注意: 慎写"细致 hair strands"，否则容易翻车

### pixar_3d（合家欢 / 温情）

- proportion: 矮胖化（5-6 头身），眼睛 + 头部放大
- linework: subsurface scattering，rim light 突出
- 标准 prompt 关键词: \`\`pixar 3d animation style, stylized proportions, large head, expressive face, subsurface scattering, warm lighting\`\`

### ghibli（治愈 / 自然）

- proportion: 7-7.5 头身，柔和五官
- linework: painterly background + 简洁人物线条，水彩感
- 标准 prompt 关键词: \`\`ghibli studio style, soft watercolor, painterly, gentle expression, lush environment\`\`

### cyberpunk（未来 / 暗调）

- proportion: 真人比例 + cybernetic 改造件
- linework: neon rim light，潮湿表面
- 标准 prompt 关键词: \`\`cyberpunk style, neon rim lighting, cybernetic implants, holographic UI elements, rain-slick reflections\`\`

### noir（黑色悬疑）

- proportion: 真人 8 头身
- linework: 硬光 + 大面积阴影 + 单一红色 accent
- 标准 prompt 关键词: \`\`film noir, monochrome with red accent, harsh shadows, low-key lighting, smoky interior, venetian blind shadows\`\`

### watercolor（诗意 / 文艺）

- proportion: 7-7.5 头身，柔化轮廓
- linework: visible brushstrokes，wet edges
- 标准 prompt 关键词: \`\`watercolor illustration, visible brushstrokes, soft saturation, paper texture, dreamy atmosphere\`\`

## reference: clothing-and-accessories-checklist

设计 clothing_detail 时检查清单：

### 服装（clothing_detail）

必含：
1. **衣型**：长袍 / 短打 / 制服 / 战斗服 / 西装 / 校服
2. **主色**：和 visual_style.color_palette 不冲突
3. **材质**：玄铁 / 丝绸 / 皮革 / 棉麻 / 金属
4. **状态**：完整 / 磨损 / 破损 / 染血 / 干净

可选：
- 装饰：花纹 / 刺绣 / 徽章
- 层次：内衣 / 外袍 / 披风

### 配件（accessories）

按角色设定逐项列，不要合并：

| 类别 | 例子 |
| --- | --- |
| 武器 | 玄重尺、法剑、手枪、十字弓 |
| 首饰 | 项链、耳环、戒指、手镯 |
| 道具 | 眼镜、拐杖、怀表、烟斗、剑鞘 |
| 防具 | 护腕、护肩、面具、头盔 |
| 标志符号 | 宗门徽章、家族纹样 |

每个配件单独写一行，避免被 prompt 长度压缩"忘记"。
`;

const SCENE_DESIGN = `---
name: scene-design
description: Use when designing scene reference packs (location description + atmosphere + lighting + time variants + props) so every shot in that location renders with consistent environment language. Provides decision rules for atmosphere / lighting / time-of-day handling and prompt templates for environment image generation.
target_agents: [scene_ref_agent]
tags: [scene-design, environment, reference-image, prompt-engineering]
author: filmgenx
---

# 场景设计

场景设计的目标不是"画一个好看的地方"，而是**把每个 location 的视觉锚点钉死**——让后续每个发生在这里的镜头都共享同一份"这里长什么样"，并按时段 / 天气提供变体。

本 skill 给 scene_ref_agent 在出 \`\`SceneRefSet\`\` 时的设计原则、出图 prompt 模板、以及 time_variants 的覆盖规则。

## 一致性的本质

场景"画得不像同一处"通常是因为：
- **architecture / atmosphere / lighting 写在一句话里** → 模型抓不住主导特征
- **缺 negative_prompt** → 室内场景被画到了室外、白天场景被画成了夜晚
- **时段变体堆在主 prompt 里** → 每次生成天气不可控
- **props 被压缩** → "云岚宗"少了那口标志性青铜钟，下游看了不认识

## 三段式 prompt 结构

把场景描述拆成三个独立段，模型对每段的注意力更稳定：

\`\`\`
[architecture]: 建筑 / 地形 / 空间结构（"白玉广场, 高耸古青铜钟, 远处有重重宗门殿宇, 三层石阶")
[atmosphere]:   情绪 / 氛围（"肃杀压抑, 万人聚集后的死寂, 弥漫沉重战意")
[lighting]:     光照 / 时段（"清晨薄雾, 顶光散射, 地面反射冷灰光, 远景剪影")
\`\`\`

合起来给模型：\`\`{architecture}, {atmosphere}, {lighting}, {color_restrictions}\`\`

## time_variants 的边界

每个 location **最多 3 个时段变体**，按以下优先级挑：

1. **剧情明确出现的时段**（如剧本写"日落决斗"）—— 必出
2. **戏剧反差大的时段**（如同一场地白天 / 夜晚出现两次）—— 必出
3. **气氛抓手的时段**（cyberpunk 必夜、ghibli 必日）—— 必出

如果剧情里只在一个时段出现，**不要凑变体**——单一变体就够了。

每个 variant 的 value 写**该时段下变化的部分**（光照 / 氛围 / 颜色），不要重复 architecture：

\`\`\`python
time_variants = {
    "day":   "顶光强烈, 白玉反光刺眼, 暖橙色调",
    "night": "月光冷光, 青铜钟反射蓝灰光, 远景灯火点点",
    "rain": "雨幕笼罩, 地面湿润反光, 雾气朦胧, 整体降饱和"
}
\`\`\`

## color_restrictions（喂给 SD 模型的英文标签）

写法用 SD-style 英文标签，不是中文长句：

| 题材 | color_restrictions |
| --- | --- |
| anime 玄幻 | \`\`saturated reds and golds with cool blue accents, slightly desaturated\`\` |
| photorealistic 都市 | \`\`muted greys and browns, cold blue sky, warm orange streetlights\`\` |
| pixar_3d | \`\`high saturation warm orange and yellow with cool teal accents\`\` |
| ghibli | \`\`soft greens and blues, cream whites, occasional warm reds\`\` |
| cyberpunk | \`\`deep blue and magenta neon, teal-and-orange complementary, electric blue accents\`\` |
| noir | \`\`monochrome black and grey with single red accent, harsh shadows\`\` |
| watercolor | \`\`soft pastels, watercolor washes, muted palette\`\` |

## mood_keywords（中文短词列表）

中文短词，3-6 个，给下游 video_prompt 拼镜头描述时复用：

\`\`\`python
["废墟感", "压抑", "肃杀", "孤立", "庄严"]
["温馨", "亲密", "怀旧", "柔软", "日常"]
["冷峻", "未来感", "潮湿", "霓虹", "疏离"]
\`\`\`

不要写句子（"主角在这里发现真相"是情节，不是 mood）。

## negative_prompt 必含

按场景类型写：

| 场景类型 | negative_prompt 必含 |
| --- | --- |
| 室内 | \`\`no outdoor, no sky, no horizon, no daylight from outside\`\` |
| 室外开阔 | \`\`no ceiling, no walls, no enclosed space\`\` |
| 室外建筑环绕 | \`\`no isolated structure, no empty plain\`\` |
| 黑夜 | \`\`no daytime, no bright sunlight, no clear blue sky\`\` |
| 白天 | \`\`no nighttime, no neon, no artificial bright lights\`\` |
| 自然环境 | \`\`no concrete buildings, no urban infrastructure\`\` |
| 城市 | \`\`no rural, no wilderness, no isolated landscape\`\` |

外加 art_genre 通用项（同 character_ref）。

## reference_image_count 分配

**每个 location 最少 2 张**：

- 1 张主 angle（最具代表性的视角，下游引用最多）
- 1 张副 angle 或副 time_variant（给 video_prompt 提供构图选择）

最多 3 张。**不要每个 time_variant 都出**——下游 video_prompt 会按文字提示自己融合时段，参考图给"建筑骨架"就够。

## 反例

- 同一 location 拆成两个 SceneRef（"云岚宗" + "云岚宗大殿"）—— 该合并就合并
- atmosphere 写"主角在这里第一次见到反派"—— 这是情节
- time_variants 4 个以上 —— 资源浪费且模型混乱
- color_restrictions 用中文长句 —— SD 不识别
- props 漏关键道具 —— 下游镜头里宗门标志性青铜钟消失

## 工作流（强调先口头说明再调用工具）

每次准备调 \`\`load_skill_reference\`\` / \`\`generate_image\`\` / \`\`memory_save\`\`：
1. 本轮先口头说意图 + 理由
2. 下一轮才调工具

例：
> "云岚宗广场是高潮决斗场，需要 2 张参考图：1 张主 angle（白天空荡的全景），1 张副 angle（决斗时的近景仰拍）。下一步我会先调 \`\`load_skill_reference(skill='scene-design', ref_key='environment-prompt-cookbook')\`\` 看一下宗门类场景的标准 prompt 模板，再回来定稿 architecture 字段。"

## reference: environment-prompt-cookbook

按场景类型给的标准 prompt 配方：

### 玄幻宗门（仙侠 / 修仙）

\`\`\`
architecture: 巨型石阶 / 白玉广场 / 飞檐殿宇 / 古铜钟 / 灵气云雾
atmosphere: 庄严 / 肃杀 / 上古遗留 / 仙气缭绕
lighting: 清晨薄雾 + 顶光散射 / 黄昏霞光 / 月华笼罩
props: 青铜钟 / 古旗帜 / 门派牌匾 / 镇宗石碑
英文 tag: ancient sect courtyard, white jade plaza, towering stone steps, mountain backdrop, mystical mist
负面: no modern building, no concrete, no urban
\`\`\`

### 都市街景（现代 / 都市剧）

\`\`\`
architecture: 高楼大厦 / 街道 / 红绿灯 / 玻璃幕墙 / 招牌
atmosphere: 繁忙 / 冷漠 / 都市疏离 / 节奏感
lighting: 正午硬光 / 夜晚霓虹 / 黄昏街灯
props: 出租车 / 便利店招牌 / 公交站 / 路人
英文 tag: modern city street, glass skyscrapers, neon signs, urban realistic, rain-slick asphalt
负面: no rural, no wilderness, no fantasy elements
\`\`\`

### 末日 / 废墟

\`\`\`
architecture: 倒塌建筑 / 锈蚀金属 / 杂草丛生 / 弃车
atmosphere: 死寂 / 绝望 / 末世 / 寂寥
lighting: 暗沉灰蓝 / 偶尔斜射光柱 / 黄昏沙尘
props: 废弃汽车 / 破碎招牌 / 杂草藤蔓 / 残骸
英文 tag: post-apocalyptic ruins, abandoned cityscape, overgrown vegetation, rusted metal, debris
负面: no clean modern building, no people, no daily life
\`\`\`

### 室内对话（家 / 办公室 / 咖啡厅）

\`\`\`
architecture: 桌椅 / 窗 / 地板 / 墙面装饰
atmosphere: 私密 / 日常 / 温暖 / 紧绷（视情境而定）
lighting: 实用光源（台灯 / 窗户日光）+ 柔光
props: 茶杯 / 笔记本 / 装饰画 / 植物 / 抱枕
英文 tag: cozy interior, soft natural window light, wooden floor, intimate atmosphere
负面: no outdoor, no sky, no horizon
\`\`\`

### 自然 / 田园

\`\`\`
architecture: 山 / 河 / 树林 / 田野 / 小路
atmosphere: 宁静 / 治愈 / 自然 / 季节感
lighting: 清晨薄雾 / 正午斑驳树影 / 黄昏暖光
props: 野花 / 溪水 / 石头 / 木桥
英文 tag: lush natural landscape, dappled sunlight through leaves, peaceful atmosphere, painterly
负面: no urban, no concrete, no neon
\`\`\`

### 战斗场（决斗台 / 修罗场）

\`\`\`
architecture: 开阔平台 / 残骸地形 / 围观看台 / 高空场地
atmosphere: 紧张 / 杀气 / 史诗感 / 万人屏息
lighting: 戏剧性硬光 / 风沙效果 / 仰角顶光
props: 武器残骸 / 战旗 / 血迹 / 裂痕
英文 tag: dramatic battlefield, dust and debris, low-angle shot, cinematic lighting
负面: no peaceful, no warm, no ordinary daily scene
\`\`\`

## reference: time-of-day-lighting-recipes

5 种核心时段的光照模板（直接拼到 prompt 里）：

### dawn（黎明）

\`\`\`
柔和 backlight 从地平线来, 蓝紫色天空过渡到暖粉, 雾气未散, 主体剪影清晰
英文 tag: soft golden hour backlight, dawn mist, purple-pink sky gradient, silhouettes
适用: 决心 / 重生 / 新开始的情绪
\`\`\`

### day（正午）

\`\`\`
顶光强烈, 短阴影硬, 高对比, 蓝天明亮
英文 tag: harsh midday sunlight, sharp shadows, high contrast, clear blue sky
适用: 戏剧性时刻 / 揭示真相 / 公开对峙
\`\`\`

### golden_hour（黄金时刻 / 日落前 1h）

\`\`\`
低角度暖橙光, 长阴影, 全场镀金, 浪漫感
英文 tag: warm golden hour light, long shadows, magic hour glow, romantic atmosphere
适用: 抒情 / 离别 / 反思 / 万能选项
\`\`\`

### dusk（黄昏 / 日落后）

\`\`\`
紫蓝色天空, 实用光源点亮, 远景轮廓模糊, 神秘感
英文 tag: blue hour twilight, purple-blue sky, practical lights starting to glow, mysterious
适用: 转折 / 悬疑 / 剧情进入下半段
\`\`\`

### night（黑夜）

\`\`\`
月光冷蓝, 实用光源（街灯 / 窗光 / 火光）作主光, 阴影深邃
英文 tag: moonlit night, cool blue ambient, warm practical lights, deep shadows
适用: 阴谋 / 战斗高潮 / 内心独白 / cyberpunk 默认
\`\`\`

### rain（雨景，可叠加在任意时段）

\`\`\`
雨幕灰白, 地面镜面反光, 雾气朦胧, 降饱和
英文 tag: rain-soaked atmosphere, wet reflective surfaces, atmospheric fog, desaturated
适用: 悲伤 / 转折 / 净化 / noir 必备
\`\`\`
`;

const VIDEO_PROMPT_ENGINEERING = `---
name: video-prompt-engineering
description: Use when translating storyboard shots into Seedance reference-to-video prompts. Provides the four-element motion formula (camera + character action + rhythm + opening frame), Seedance parameter rules (duration 4-15, aspect ratio, asset_codes), and templates for common camera moves and action types.
target_agents: [video_prompt_agent]
tags: [video-prompt, seedance, reference-to-video, prompt-engineering]
author: filmgenx
---

# 视频镜头 prompt 工程

video_prompt_agent 的输出会**直接喂给 Seedance reference-to-video**。参考图（character.three_view_asset_code / scene.reference_asset_codes）保证角色 / 场景一致性，prompt 描述运动 + 节奏 + 起手构图。

本 skill 给四要素公式、Seedance 参数规则、常见运镜与动作类型模板，以及关键运动验证的工具调用流程。

## 四要素公式

每个 \`\`motion_description\`\` 必须涵盖：

\`\`\`
[1. 画面起手]: 第 0 秒看到什么 (景别 / 主体位置 / 光影氛围，结合参考图)
[2. 运镜]:    pan / dolly / zoom / static, 起止位置, 速度
[3. 角色动作]: 肢体 / 表情变化, 节奏分段
[4. 镜头节奏]: 时间分配 (前 X 秒做 A, 中 Y 秒做 B, 末 Z 秒做 C)
\`\`\`

总长度 80-180 字。低于 80 通常运动不够清晰；高于 180 模型注意力分散。

## 完整模板

\`\`\`
画面起手: 萧炎背身站立云岚宗广场中央, 玄重尺横置背后, 黄昏侧光剪影; 远景宗门殿宇模糊。
运镜: 镜头以 dolly in 缓慢推进, 起始 medium shot, 推进到 medium close-up, 停在主角侧脸位置。
角色动作: 主角缓慢转身, 表情从平静转为 determined, 右手缓慢握紧尺柄。
节奏: 前 2 秒画面静止建立氛围, 2-4 秒推镜 + 转身同步, 4-5 秒停顿在表情特写。

duration: 5 sec
aspect_ratio: 16:9
quality: hq
\`\`\`

## Seedance 参数规则（硬约束）

| 参数 | 允许值 | 备注 |
| --- | --- | --- |
| \`\`duration_seconds\`\` | **4-15 整数** | 越界 Seedance 直接拒绝 |
| \`\`aspect_ratio\`\` | \`\`16:9\`\` / \`\`9:16\`\` / \`\`1:1\`\` / \`\`4:3\`\` / \`\`3:4\`\` / \`\`21:9\`\` | 必须与对应 storyboard.shot 一致 |
| \`\`asset_codes\`\` | **必填**，从 character.* / scene.* 取 | 参考图保证角色 / 场景一致性；不能为空 |
| \`\`quality\`\` | \`\`std\`\` / \`\`hq\`\` | std=720p, hq=1080p; hq 额度贵 |

### duration 选择规则

storyboard 里每个镜头的 \`\`duration_seconds\`\` 是设计意图，**video_prompt 的 duration 是 Seedance 实际生成时长**。两者不必完全一致：

| storyboard.duration_seconds | video_prompt.duration_seconds | 理由 |
| --- | --- | --- |
| 1-3 秒（快切） | 5 | Seedance 最短 4 秒；统一取 5 后剪辑时再裁短 |
| 4-6 秒 | 5 | 直接对齐 |
| 7-10 秒 | 8-10 | 长镜要求 |
| 11-15 秒 | 12-15 | 极少数特殊高潮 |
| > 15 秒 | 拆分成多段 | 单个镜头超过 Seedance 限制 |

### quality 分配（额度有限）

短剧（60 秒）按这个比例分配：

| 镜头类型 | quality | 占比 |
| --- | --- | --- |
| 高潮 / 转场 / 情感顶点 | hq | 20-30% |
| 关键叙事 / 角色 close-up 运动 | hq | 视情况 |
| 常规过场 / 简单运镜 | std | 60-70% |

**不要全 hq**——一个 60 秒短剧 12-15 个 video shot 全 hq 会爆额度。

## "画面起手"为什么关键

Seedance 虽然有参考图保证角色 / 场景一致性，但**镜头起手的构图 / 景别 / 主体位置**得靠 prompt 写明，否则模型自由发挥起手画面，会和你预期的镜头语言对不上。

正确做法：**前 1-2 句明确锁定起手构图**：

\`\`\`
画面起手: {景别（中景 / 全景 / 特写）} + {主体在画面中位置} + {光影氛围},  ← "种子"
然后镜头 ...                                                                 ← "运动"
角色 ...
节奏 ...
\`\`\`

不用复述参考图里能看到的细节（服装 / 长相 / 场景结构），那些 Seedance 看参考图就知道。重点是**起手构图 + 动态变化**。

## 常见运镜模板

### static（静止 / 标准对话）

\`\`\`
镜头静止保持 medium shot 不动, 不推不拉不摇.
适用: 对话戏, 仪式感, 抒情戏长镜.
\`\`\`

### pan（横摇 / 跟随）

\`\`\`
镜头以中速 pan {左→右 / 右→左}, 跟随主体平移, 揭示空间.
适用: 揭示场景, 角色行走, 空间过渡.
\`\`\`

### tilt（俯仰摇）

\`\`\`
镜头以缓慢 tilt {上→下 / 下→上}, 揭示高度差.
适用: 展现建筑高度, 权力关系仰拍, 揭示天空 / 地面.
\`\`\`

### dolly_in（推进）

\`\`\`
镜头以中速 dolly in 推进, 从 long shot 推到 medium close-up, 介入角色情绪.
适用: 情绪升级, 决心时刻, 揭示真相前的预备.
\`\`\`

### dolly_out（拉远）

\`\`\`
镜头以缓慢 dolly out 拉远, 从 close-up 拉到 long shot, 角色逐渐渺小.
适用: 离别, 揭示孤立, 结尾场景.
\`\`\`

### whip_pan（急摇）

\`\`\`
镜头以极快 whip pan 切换, 用动作模糊连接两个画面.
适用: 转场, 时空跳跃, 动作戏过渡.
\`\`\`

### handheld（手持）

\`\`\`
镜头以手持轻微抖动跟随主体, 真实感, 紧张感.
适用: 紧张戏, 第一人称感, 现实主义.
\`\`\`

### crane（升降）

\`\`\`
镜头从低位 crane up 升起, 揭示全景或转换视角.
适用: 开场, 结尾, 仪式感时刻.
\`\`\`

### zoom_in（变焦推近）

\`\`\`
镜头 zoom in (不是物理移动), 突出心理变化或细节.
适用: 心理戏, 特定道具特写, 复古电视感.
注意: 慎用. 现代电影感少用.
\`\`\`

## 常见角色动作模板

### 战斗动作

\`\`\`
主角举武器, 蓄力 1 秒, 挥下时武器尾随光迹, 击中目标产生粒子爆发.
英文 tag: character raises weapon, charges energy 1 sec, swings down with motion blur trail, particle explosion on impact
\`\`\`

### 释放招式 / 异能

\`\`\`
主角双手聚气, 手心光球渐大, 双色异火融合, 释放冲击波.
英文 tag: character channels energy, palm glows brighter, two-color flames merge, releases shockwave
\`\`\`

### 转身 / 揭示表情

\`\`\`
主角缓慢转身, 头先转, 身体跟随, 表情从平静过渡到 determined, 视线锁定.
英文 tag: character slowly turns around, head first, body follows, expression transitions from calm to determined, locked gaze
\`\`\`

### 行走 / 离开

\`\`\`
主角缓慢迈步前进, 步速节奏稳定, 长袍 / 头发飘动.
英文 tag: character walks forward at steady pace, robes / hair flowing, determined posture
\`\`\`

### 摔倒 / 受击

\`\`\`
主角被击中, 身体后仰, 武器脱手飞出, 着地腾起尘土.
英文 tag: character takes hit, body recoils backward, weapon flies out of grip, dust kicks up on impact
\`\`\`

### 抒情 / 静默

\`\`\`
主角静止, 仅风吹动头发 / 衣物, 眼神缓慢眨动, 微表情变化.
英文 tag: character stands still, hair / clothes drift in wind, slow blink, subtle facial micro-expression shift
\`\`\`

## 反例

- motion_description 写"角色移动"——通用描述, 模型乱画
- duration_seconds 越界（不在 4-15）——Seedance 拒绝
- aspect_ratio 与 storyboard.shot 不一致——画面拉伸
- 漏写画面起手——起手构图全靠模型自由发挥
- 全部 quality=hq——额度爆掉
- 把参考图能看到的细节（服装 / 场景结构）整段复述进 prompt——重复信息, 浪费 prompt 长度
- asset_codes 列表为空——Seedance reference-to-video 直接拒绝

## 工作流（强调先口头说明再调用工具）

每次准备调 \`\`load_skill_reference\`\` / \`\`generate_video\`\`：
1. 本轮先口头说明意图 + 理由
2. 下一轮才调工具

例：
> "我打算只对镜头 7（佛怒火莲释放）和镜头 12（决战收尾）做 generate_video 验证。这两镜是高潮 + 收尾, 运动复杂, 担心 prompt 写得不够具体. 下一步先用镜头 7 跑一次（duration=5, quality=hq）, 看异火融合的运动是否到位, 不到位再调整 prompt 重跑."

## reference: kling-camera-motion-cheatsheet

Kling 实测表现较好的运镜关键词（中英对照）：

| 中文 | 英文 prompt 关键词 | Kling 表现 |
| --- | --- | --- |
| 静止 | static camera, no movement | 稳定 |
| 缓慢推进 | slow dolly in, gradual zoom in | 稳定 |
| 缓慢拉远 | slow dolly out, gradual zoom out | 稳定 |
| 横移跟随 | smooth pan following the subject | 较稳定 |
| 仰角推进 | low-angle dolly in, looking up | 稳定 |
| 俯角拉远 | overhead pull back, bird's eye | 稳定 |
| 手持跟拍 | handheld camera following, slight shake | 较稳定 |
| 急速横摇 | whip pan transition | 不稳定（常被忽略） |
| 360 环绕 | orbit around the subject | 不稳定（容易变形） |
| 升降镜 | crane up / crane down | 较稳定 |

**避免**：复杂复合运镜（如 dolly + tilt 同时）、超过 2 个动作的串联——Kling 容易"做一半"。

## reference: motion-pacing-templates

5 种常见镜头节奏模板，按 5 秒和 10 秒拆解：

### 5 秒爆发型（动作戏）

\`\`\`
0-1秒: 静止建立 (起手画面)
1-3秒: 主动作执行 (挥武器 / 释放招式 / 转身)
3-5秒: 余波 + 表情 (击中后烟尘 / 表情切换 / 武器停顿)
\`\`\`

### 5 秒抒情型（情绪戏）

\`\`\`
0-2秒: 静止微动 (风吹头发 / 缓慢眨眼)
2-4秒: 表情过渡 (平静→悲伤 / 决心→释然)
4-5秒: 微表情定格 (眼角泪光 / 嘴角微扬)
\`\`\`

### 5 秒推镜型（情绪升级）

\`\`\`
0-1秒: long shot 静止
1-4秒: 缓慢 dolly in 到 medium close-up
4-5秒: 停在 close-up 的表情
\`\`\`

### 10 秒长镜型（仪式感）

\`\`\`
0-2秒: 起手画面建立
2-4秒: 角色动作起步
4-6秒: 主动作展开 (招式 / 对峙 / 行走)
6-8秒: 高潮点 (击中 / 决断 / 揭示)
8-10秒: 收尾 (余波 / 镜头停顿 / 转场预备)
\`\`\`

### 10 秒揭示型（开场 / 结尾）

\`\`\`
0-2秒: 局部细节特写
2-5秒: crane / zoom out 揭示更大场景
5-8秒: 角色出现 / 走入画面
8-10秒: 全景定格
\`\`\`
`;


const SEEDANCE_PROMPT_GUIDE = `---
name: seedance-prompt-guide
description: Use when writing motion_description for Seedance 2.0 reference-to-video. Covers Volcengine's S-A-C-S-C formula, camera codec system (Z/Y/X/F), timestamped shot structure, lighting / quality anchors, official negative prompts, and reference-image integration rules.
target_agents: [video_prompt_agent]
tags: [seedance, video-prompt, prompt-engineering, camera-codec]
author: filmgenx
---

# Seedance 2.0 提示词指南

火山引擎官方 prompt 公式 + Volcengine 摄影术语词汇表。本 skill 把 motion_description
的"凭感觉写"升级为"按公式套"，让生成结果稳定可控。

## S-A-C-S-C 五要素公式

每个 motion_description 必须涵盖五个要素，按这个顺序写最稳：

\`\`\`
[Subject 主体]: 谁 / 什么。锁定角色五官 / 服装 / 物体材质（这部分主要靠参考图，文字补关键差异）
[Action 动作]:  做什么。肢体 / 表情 / 物体运动的连贯序列（强调"自然 / 缓慢 / 流畅"）
[Camera 运镜]: 镜头怎么动。用官方词汇（dolly in / pull back / orbit / pan / handheld / static…），同时指明景别
[Scene 场景]:  在哪里 + 光影。光源方向 / 行为（薄雾 / 雨 / 尘埃）/ 色调
[Style 风格]:  品质锚定 + 风格关键词（"4K, cinematic, UE5 render, no flicker"）
\`\`\`

把这五段串成一句中文流畅文字（不是字段化），约 80-180 字。

## 时间戳分镜模板（4-15 秒视频）

短于 5 秒可以省略时间戳直接写一段；5 秒以上**强烈推荐用时间戳分镜**，把视频拆成 2-3 段递进的画面，模型对节奏的控制力大幅提升：

\`\`\`
[5 秒, 史诗写实风格] 主角持剑站在悬崖边背身远眺，剑刃微闪寒光，山风吹起战袍下摆。
0-2 秒：static 长镜，主角剪影占画面右 1/3，远景云海翻涌。
2-4 秒：缓慢 dolly in 推进至 medium shot，主角缓慢转身，表情从平静转为 determined。
4-5 秒：停顿在主角侧脸特写，右手缓慢握紧剑柄。
光影：黄昏侧逆光，金红色调，远景薄雾扩散。
约束：no flicker, no face distortion, no extra characters, no text overlay.
\`\`\`

每个时间戳片段都要包含 **[画面] + [运镜]**。光影和约束统一放尾部一段。

## 相机运镜官方词汇表

按运动类型分四类，**用英文术语**模型识别更准（中文是辅助）：

| 类型 | 英文 | 中文 | 用途 |
| --- | --- | --- | --- |
| 推 | dolly in, push in, zoom in | 推 / 拉近 | 聚焦主体细节，建立情感 |
| 拉 | dolly out, pull back, zoom out | 拉远 | 揭示更大空间，渐入全景 |
| 摇 | pan left/right, tilt up/down | 横摇 / 俯仰 | 揭示空间或高度差 |
| 移 | truck left/right, crane up/down | 横移 / 升降 | 平移跟随主体或揭示纵深 |
| 跟 | tracking shot, follow shot | 跟拍 | 跟随角色行走 / 奔跑 |
| 环绕 | orbit, arc around | 环绕 | 360° 展示主体 |
| 手持 | handheld, shaky cam | 手持 | 紧张 / 纪实感（慎用，易崩） |
| 静止 | static, locked shot | 静止 | 对话 / 仪式 / 抒情长镜 |

**铁律**：单镜头最多双轴运动（例如 dolly in + pan 可，加 tilt 就崩）。镜头变化越多模型越乱。

更深一层的"相机四维编码（Z/Y/X/F）+ 14 种情绪坐标"是这个 skill 的进阶部分——
**当你不确定某个情绪 / 场景对应什么运镜组合时**，加载 @ref:camera-codec。

## 主体描述要点

- 优先靠**参考图保证一致性**——文字不复述参考图能看到的细节（服装款式、长相、场景结构）
- 文字只补**当前镜头的关键差异**：情绪 / 当下动作 / 与参考图不同的姿态或道具
- 多角色场景必须指明"哪个角色做什么"，否则模型混合特征

## 动作 / 节奏写法

- **用慢词**："缓慢 / 轻柔 / 连贯 / 自然 / 流畅" 比 "快速 / 剧烈 / 暴烈" 出片稳定
- 节奏分段：用 "前 X 秒做 A，X-Y 秒做 B，末 Z 秒做 C" 给模型时间分配
- 复杂多人互动（拥抱 / 打斗）容易崩——拆成两个镜头分别拍

## 光影三层结构

光影描述按三层写最完整：

1. **光源层**：黄昏侧逆光 / 顶光 / 月光 + 实用灯（路灯 / 烛火） / 自然漫射光
2. **光行为层**：薄雾弥散 / 尘埃飞舞 / 雨水粘镜 / 阴影闪烁
3. **色调层**：金红色调 / 冷蓝色调 / 高对比黑白 / 低饱和怀旧

例：\`\`黄昏侧逆光（光源），远景薄雾扩散（行为），金红色调主导（色调）\`\`

## 风格 / 品质锚定词

每条 prompt 尾部加品质锚定，比写 "电影感" 这种空词有效得多：

\`\`\`
4K, cinematic, UE5 render, high detail, sharp focus, stable framing, no flicker, no blur
\`\`\`

按题材换：
- 写实电影：\`\`cinematic, anamorphic lens, film grain, Roger Deakins style\`\`
- 动漫：\`\`anime style, Makoto Shinkai, vibrant colors, clean lineart\`\`
- 国风武侠：\`\`Chinese ink painting style, mist, traditional brushwork\`\`
- 赛博朋克：\`\`cyberpunk neon, blade runner aesthetic, rainy night, holographic UI\`\`

## 负面约束（防崩坏关键）

Seedance 不接受独立 negative_prompt 字段，所以负面约束**直接拼在 prompt 末尾**作为一段：

\`\`\`
约束：no face distortion, no flicker, no character drift, no extra characters,
no sudden color shift, no text/subtitle/logo/watermark, no shaky cam,
no rapid scene change.
\`\`\`

按场景额外加：
- 室内 → \`\`no outdoor sky, no daylight from outside\`\`
- 单人镜 → \`\`no crowd, no background people\`\`
- 远景 → \`\`no close-up face details, no extreme details\`\`

## 与参考图配合

Seedance reference-to-video 通过 \`\`asset_codes\`\` 接受参考图：

\`\`\`
generate_video(
  prompt="...",
  asset_codes=[character.主角.three_view_asset_code, scene.云岚宗广场.reference_asset_codes[0]],
  duration=8,
  aspect_ratio="16:9",
)
\`\`\`

**参考图能确定的事**（服装 / 长相 / 场景结构 / 全片色调）→ **不在 prompt 里复述**。
**prompt 唯一的职责**：描述动作 + 运镜 + 节奏 + 情绪变化 + 光影变化。

参考图最多 9 张；通常 1-3 张够用：1 张主角三视图 + 1 张场景主 angle。

## 平台参数限制（硬约束）

| 参数 | 范围 | 备注 |
| --- | --- | --- |
| duration | 4-15 秒整数 | 越界 Seedance 直接拒 |
| aspect_ratio | 16:9 / 9:16 / 1:1 / 4:3 / 3:4 / 21:9 | 必须与 storyboard.shot 一致 |
| asset_codes | **必填**，≤9 张 | reference-to-video 不接受空参考图 |
| 单条 prompt | 建议 80-180 字 | 越长注意力越稀释 |

## Do & Don't

### Do（推荐做法）
- 分镜式时间戳结构（5+ 秒视频）
- 用英文官方术语写运镜（dolly in / orbit），中文是辅助
- 品质锚定词焊死在结尾（4K / UE5 / cinematic / no flicker）
- 同一场戏相邻镜头保持布景连续（不要每镜大改场景）

### Don't（避免陷阱）
- 单条 prompt 描述超过 15 秒内容 → 拆分成多个 generate_video 调用
- 同一镜头叠加 3+ 种运动（dolly + pan + tilt 一起来）→ 必崩
- 把参考图能看到的服装 / 长相再用文字复述一遍 → 浪费 prompt 长度
- 写"很美 / 很震撼 / 很有感觉"等主观空词 → 模型不识别
- "瞬移 / 闪现 / 突变" → 易崩；改成 "缓慢淡出 / 渐入"
- asset_codes 为空 → Seedance 直接拒绝（reference-to-video 模式硬约束）

## 工作流（先口头说明再调工具）

每次调 \`\`generate_video\`\` 之前：
1. 本轮先口头说：本镜的 Subject / Action / Camera / Scene / Style / 约束 是什么，预计要哪几个参考图 asset_code
2. 下一轮发起 generate_video tool_call

复杂题材不确定运镜组合时：
> "本镜是高潮决战，我不确定 dolly in + orbit + tilt 这种组合会不会崩。下一步先 load_skill_reference(skill='seedance-prompt-guide', ref_key='camera-codec') 拿四维坐标判断。"

## reference: camera-codec

相机四维编码（Z 距离 / Y 高度 / X 方位 / F 焦段），用于精确控制镜头：

| 维度 | 范围 | 含义 |
| --- | --- | --- |
| Z 距离 | Z1 大特写 → Z9 大远景 | 控制画面细节密度 |
| Y 高度 | Y1 虫视（仰拍） → Y7 顶视（俯拍） | 控制心理角度（仰拍崇高 / 俯拍渺小） |
| X 方位 | X1 正面 / X2 3/4 侧 / X3 全侧 / X4 背面 | 控制立体感 |
| F 焦段 | 24mm 广角 / 50mm 标准 / 85mm 中长焦 / 135mm 长焦 | 控制畸变与压缩感 |

**14 种情绪 → 推荐坐标**（速查表）：

| 情绪 | Z | Y | X | F | 备注 |
| --- | --- | --- | --- | --- | --- |
| 崇高 / 英雄 | Z4 中景 | Y2 微仰 | X1 正面 | 50mm | 经典英雄构图 |
| 压抑 / 弱小 | Z5 中远 | Y6 高俯 | X1 正面 | 24mm | 角色被空间压制 |
| 紧张 / 对峙 | Z3 中近 | Y4 平视 | X2 3/4 | 85mm | 压缩空间制造对抗 |
| 亲密 / 情感 | Z2 近 | Y4 平视 | X1 正面 | 85mm | 大光圈虚化背景 |
| 神秘 / 揭示 | Z1 → Z6 渐拉 | Y3 略仰 | X4 背面 | 50mm | 背身渐拉揭示场景 |
| 焦虑 / 慌乱 | Z3 中近 | Y4 平视 | 摇晃 | handheld | 手持微抖 |
| 静谧 / 抒情 | Z6 远 | Y4 平视 | static | 35mm | 长镜静止 |
| 史诗 / 宏大 | Z8 大远景 | Y7 顶视 | X1 | 24mm 广角 | 渺小感 |
| 回忆 / 怀旧 | Z3 中近 | Y3 略仰 | X2 3/4 | 50mm 柔焦 | 加 film grain |
| 决心 / 觉醒 | Z2 近 | Y2 微仰 | X1 | 50mm | 缓推到特写 |
| 失落 / 孤独 | Z6 远 | Y3 略仰 | X4 背面 | 35mm | 背身远景 |
| 暴怒 / 爆发 | Z2 近 → Z1 大特写 | Y4 平视 | X1 | 85mm | 急推到大特写 |
| 悬疑 / 黑色 | Z5 中远 | Y4 平视 | X3 全侧 | 50mm | 测光暗部 |
| 释然 / 升华 | Z5 中远 → Z8 远 | Y2 微仰 | X1 | 50mm | 缓拉开升镜 |

**铁律**：每镜头最多双轴变化；Z1-Z3 近景 + X 轴 / Y 轴大幅旋转**必崩面部**。

## reference: lighting-vocabulary

光影词库——按"光源 / 行为 / 色调"三层各列一组高频词：

**光源**：side light, backlight, top light, three-point lighting, golden hour, blue hour,
moonlit, candlelight, neon practical, soft window light, harsh sun, overcast

**行为**：mist diffusion, dust motes, rain streaks, light leaks, lens flare,
volumetric shadow, god rays, flickering candle, prism refraction

**色调**：warm golden, cool blue-cyan, high contrast B&W, low saturation,
teal-and-orange, monochromatic green, neon magenta + emerald

## reference: example-prompts

5 套完整的 Seedance prompt 实战示例：

### 1. 角色觉醒（5 秒，单人镜头）

\`\`\`
史诗写实风格，主角持剑站在悬崖边背身远眺，山风吹动战袍下摆。
0-2 秒：static 长镜，主角剪影占画面右 1/3，远景云海翻涌。
2-4 秒：缓慢 dolly in 推进至 medium shot，主角缓慢转身，
表情从平静转为 determined。
4-5 秒：停顿在主角侧脸特写，右手缓慢握紧剑柄。
光影：黄昏侧逆光，金红色调，远景薄雾扩散。
约束：4K, cinematic, UE5, no flicker, no face distortion, no text overlay.
\`\`\`

### 2. 对话双人（8 秒，中景对话）

\`\`\`
赛博朋克写实风，A 和 B 在霓虹雨夜街角对峙。
0-3 秒：static medium shot，OTS 视角从 A 肩头看 B，B 表情凝重缓慢说话。
3-6 秒：缓慢 pan 转到 B 的正反打，B 抬头反问，眼神锐利。
6-8 秒：crane up 升镜略仰，揭示 B 身后远处霓虹招牌。
光影：紫红色霓虹主光 + 蓝色雨夜冷调，水面反光，雨水缓慢落下。
约束：cinematic, anamorphic lens, no character drift, no extra people, no text.
\`\`\`

### 3. 高潮战斗（10 秒，单人爆发）

\`\`\`
史诗奇幻风，主角站在战场中央，双手凝聚异火。
0-3 秒：medium shot static，主角双手缓慢抬起，掌心红蓝双色火焰旋转融合。
3-6 秒：dolly in 缓推到 medium close-up，火焰加速旋转，主角眼神聚焦。
6-9 秒：火焰爆发瞬间——orbit 镜头快速环绕主角 1/4 圈，揭示火焰膨胀。
9-10 秒：拉远到 wide shot，火焰冲天，主角剪影。
光影：火焰自发光主导，冷蓝环境光对比，地面尘埃飞舞。
约束：UE5 render, no flicker, no rapid scene change, no text overlay,
no shaky cam, 4K detail.
\`\`\`

### 4. 静谧抒情（6 秒，空镜过场）

\`\`\`
日系治愈风，清晨田野，麦穗在微风中摇曳。
0-2 秒：static low angle close-up，麦穗占画面前景，远景模糊。
2-4 秒：缓慢 truck right 横移跟随风的方向。
4-6 秒：rack focus 焦点从前景麦穗虚化到远景日出。
光影：晨光侧逆光，金色高光，薄雾弥散，全片低饱和怀旧色。
约束：anime style, Makoto Shinkai aesthetic, soft focus, no flicker, no text.
\`\`\`

### 5. 揭示式开场（12 秒，建立世界）

\`\`\`
中国传统水墨风，悬浮的仙山远景，云雾环绕。
0-4 秒：static wide shot，仙山占画面中央，云雾从下方缓慢上升。
4-8 秒：缓慢 dolly in 推进，揭示山顶古亭轮廓。
8-12 秒：tilt down 缓慢下摇，最终落在亭中持剑的主角剪影。
光影：晨曦侧光，墨色与朱红对比，远景留白，水墨笔触可见。
约束：Chinese ink painting style, traditional brushwork, no flicker,
no character drift, stable framing, 4K.
\`\`\`
`;


const BLANK_TEMPLATE = `---
name: my-skill
description: Use when ... to ...
target_agents: []
tags: []
author: ""
---

# 标题

## 主体内容

写在这里...

## 何时加载附加资料

- 当 ... 时 → 加载 @ref:example-key

## reference: example-key

reference 子文档内容，body 内通过 @ref:example-key 显式引用，LLM 才会按需调 load_skill_reference 加载它。
`;

export const SKILL_SAMPLES: SkillSample[] = [
  {
    label: '空白模板',
    targetAgent: '通用',
    markdown: BLANK_TEMPLATE,
  },
  {
    label: 'narrative-structure（三幕结构）',
    targetAgent: 'outline_agent',
    markdown: NARRATIVE_STRUCTURE,
  },
  {
    label: 'dialogue-craft（对白工艺）',
    targetAgent: 'script_agent',
    markdown: DIALOGUE_CRAFT,
  },
  {
    label: 'cinematic-composition（镜头语言）',
    targetAgent: 'storyboard_agent',
    markdown: CINEMATIC_COMPOSITION,
  },
  {
    label: 'visual-style-anchors（视觉锚点）',
    targetAgent: 'visual_style_agent',
    markdown: VISUAL_STYLE_ANCHORS,
  },
  {
    label: 'character-design（角色设计）',
    targetAgent: 'character_ref_agent',
    markdown: CHARACTER_DESIGN,
  },
  {
    label: 'scene-design（场景设计）',
    targetAgent: 'scene_ref_agent',
    markdown: SCENE_DESIGN,
  },
  {
    label: 'video-prompt-engineering（视频 prompt 工程）',
    targetAgent: 'video_prompt_agent',
    markdown: VIDEO_PROMPT_ENGINEERING,
  },
  {
    label: 'seedance-prompt-guide（Seedance 官方指南 + 相机四维）',
    targetAgent: 'video_prompt_agent',
    markdown: SEEDANCE_PROMPT_GUIDE,
  },
];
