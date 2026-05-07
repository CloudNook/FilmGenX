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
];
