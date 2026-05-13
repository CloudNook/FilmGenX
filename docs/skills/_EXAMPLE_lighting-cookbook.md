---
name: lighting-cookbook
description: Use when designing the lighting language for a character / scene reference image, or when describing time-of-day / weather / dramatic mood in a video prompt. Provides classic light positions (Rembrandt / loop / split / butterfly / rim), time-of-day color temperature recipes, and genre-specific lighting formulas (noir 1:8 / Pixar 1:2 / anime cel-shading) with prompt fragments ready to splice.
target_agents: [character_ref_agent, scene_ref_agent, video_prompt_agent, visual_style_agent]
tags: [lighting, cinematography, prompt-engineering, visual-style]
author: filmgenx
---

# 灯光配方手册（Lighting Cookbook）

下游 character_ref / scene_ref / video_prompt / visual_style 在写灯光描述时经常陷入"光照柔和、气氛肃穆"这种空话。本 skill 给一套**业内通用**的灯光配方——精确到色温（K）、光比（key:fill ratio）、方向（degrees）、prompt 片段——让 agent 写出来的 prompt 模型能直接执行。

源头思想来自 ASC（American Society of Cinematographers）的工作流：每个镜头先定**光源动机**（motivation），再定 key / fill / rim 三层，最后定**色温 + 强度 + 方向**。

## 核心信条 / 第一原理

1. **光必须有动机（motivation）**：画面里观众应能识别光源——窗 / 灯 / 火 / 雷 / 屏幕 / 月。无动机的光让画面假，模型生成时也会随机摆光，每张图光照不一致
2. **三色温度规则**：3200K（warm tungsten）/ 5600K（neutral daylight）/ 8000K+（cool blue twilight）——一个镜头里**最多混两种色温**，混三种以上观众解读为"廉价滤镜"
3. **1:N ratio 决定戏剧性**：1:1 平光、1:2 自然柔和、1:4 戏剧温和、1:8 强烈戏剧、1:16 黑色电影。Roger Deakins 在《1917》大多 1:2~1:4，《银翼杀手 2049》大多 1:8~1:16
4. **三层光是底线**：key（主光，定形）+ fill（补光，控反差）+ rim/back（轮廓光，分离主体与背景）。缺 rim 主体糊进背景，缺 fill 反差太大像监控
5. **lighting consistency 锁角色一致性**：同一角色的三视图 + 所有变体都用**同方向 key light**，i2i 变体才不会"看起来像不同时段拍的"

## 术语词汇表（你必须知道的行业名词）

| 术语 | 含义 | 通用误用纠正 |
|---|---|---|
| **Key light** | 主光，定义主体形状 | ≠ "最亮的光"——key 不一定最亮，rim 可以更亮 |
| **Fill light** | 补光，填阴影、控反差 | fill 不是"第二个光源"——可以是反光板、墙面反射、大软光 |
| **Rim / Back light** | 轮廓光，从主体后方打出边缘 | rim 是侧后 45°；back 是正后 180°；hair light 是头顶后方 |
| **Practical** | 画面里看得到的人造光（灯笼 / 台灯 / 电脑屏） | 不是"装饰"——practical 是 motivation 的载体 |
| **Motivated light** | 能合理化的光源（说有月 / 雷 / 法器，所以有光） | 玄幻题材高频用——剧情说有火，就有暖光 |
| **Lighting ratio** | key 强度 : fill 强度（如 1:4 = key 是 fill 的 4 倍） | 不是"亮暗对比度"——是两个光源的物理强度比 |
| **Chiaroscuro** | 高对比明暗，Caravaggio / Rembrandt 风格 | 不是"黑底亮主体"——是用一束光在黑暗里雕出体积 |
| **High key** | 整体亮、低对比、柔光 | Pixar / 治愈系 / 喜剧用 |
| **Low key** | 整体暗、高对比、硬光 | Noir / 悬疑 / 战斗用 |
| **Hard light** | 锐利阴影、清晰边缘 | 通常 = 点光源 + 小面积；正午阳光、裸灯 |
| **Soft light** | 柔和阴影、模糊边缘 | 通常 = 大面积漫射；阴天、柔光箱、墙面反射 |
| **Color temperature** | 光的颜色，单位 Kelvin | 3200K 偏暖橙、5600K 中性白、8000K+ 偏冷蓝 |
| **Golden hour** | 日出后 / 日落前 30-60 分钟 | 不是"傍晚"——具体时间段、光质独特 |
| **Blue hour** | 日落后 / 日出前 20-30 分钟 | 太阳已下但天还有冷蓝余光 |
| **Motivated practical** | 画面里可见光源照亮主体 | 烛台 / 灯笼 / 屏幕——电影质感来源 |

## 经典光位配方（Classic Lighting Setups）

按"key light 与主体的相对角度"分。每种光位有自己的戏剧表达。

### 1. Rembrandt Lighting（伦勃朗光）

- **角度**：key light 45° 侧前方，主体面部背光一侧的颧骨下出现**倒三角形高光**
- **戏剧表达**：内省、严肃、人物有重量感——经典肖像光
- **prompt 片段**：``"Rembrandt lighting, key light 45° camera-left from front, small inverted triangle highlight on shadow-side cheek under the eye, low fill, soft shadow"``
- **用在哪**：character_ref 严肃角色三视图 / 反派立绘 / 关键情绪 close-up

### 2. Loop Lighting（环形光）

- **角度**：key light 30-45° 侧前方，主体鼻翼阴影**不接**到嘴角（环形悬空）
- **戏剧表达**：自然、亲切、最常用——证件照、日常对话戏
- **prompt 片段**：``"loop lighting, key light 30° camera-left and slightly above, nose shadow loops to cheek but does not touch lip"``
- **用在哪**：常规对话戏 / 主角日常 establishing

### 3. Split Lighting（侧光 / 半阴半阳）

- **角度**：key light 90° 正侧方，主体半边脸亮、半边脸暗，**明暗中线竖直穿过鼻梁**
- **戏剧表达**：分裂、矛盾、双面性——心理戏 / 反派揭面 / 高潮决断
- **prompt 片段**：``"split lighting, hard key light 90° side, half face brightly lit, other half in deep shadow, clear vertical division along nose bridge"``
- **用在哪**：角色内心矛盾镜头 / 反派揭露真面目

### 4. Butterfly / Paramount Lighting（蝶光 / 派拉蒙光）

- **角度**：key light 正前上方 45°，主体鼻下出现**蝴蝶形阴影**
- **戏剧表达**：明媚、华丽——好莱坞黄金时代女星标准光
- **prompt 片段**：``"butterfly lighting, key light directly above and slightly in front, distinctive small butterfly-shaped shadow under nose, glamour portrait look"``
- **用在哪**：女主美化镜头 / 杂志风 close-up / 时尚感场景

### 5. Rim / Back Light Only（逆光剪影）

- **角度**：key light 在主体后方，正面几乎无光
- **戏剧表达**：神秘、登场、危险——反派出场 / 决斗起手
- **prompt 片段**：``"strong rim light from behind, character mostly in silhouette, glowing edge around hair and shoulders, atmospheric haze catches the backlight"``
- **用在哪**：反派出场 / 高潮决斗 / 剪影叙事

### 6. Three-Point Lighting（三点光，工作室标准）

- **配置**：key 45° 侧前 + fill 45° 对侧补光（1:2~1:4 ratio）+ rim/back 后上 45° 分离主体
- **戏剧表达**：标准、安全、商业感——访谈 / 产品拍摄 / 教学
- **prompt 片段**：``"three-point lighting setup, key light 45° front-left, fill light 45° front-right at half intensity (1:2 ratio), back rim light 45° behind separating subject from background"``
- **用在哪**：常规对话戏 / 角色立绘 / 不知道用啥光位时的 safe default

## Time-of-Day 配方表

| 时段 | 色温 (K) | 方向 | 强度 | 阴影 | 大气 | prompt 片段 |
|---|---|---|---|---|---|---|
| **Golden Hour** | 3200K | 低 15° 侧逆 | 中 | 长而柔、暖橙 | 颗粒、薄雾 | ``"golden hour, warm 3200K key light from low 15° back-side, long soft amber shadows, atmospheric haze, dust motes catching light"`` |
| **Blue Hour** | 8000K | 漫散无方向 | 弱 | 几乎无 | 冷蓝余光 | ``"blue hour twilight, cool 8000K ambient sky light, diffuse soft shadow, magic hour mood, deep purple-blue gradient sky"`` |
| **Noon Harsh** | 5600K | 垂直上方 90° | 强 | 短、硬、深 | 透明 | ``"high noon, harsh 5600K overhead sunlight, short hard black shadows, high contrast, sharp edges"`` |
| **Overcast** | 5500K | 漫散无方向 | 弱 | 几乎无 | 灰白 | ``"overcast soft daylight, 5500K diffused sky light, no clear shadows, low contrast, even illumination"`` |
| **Dusk** | 4500K → 6500K | 漫散 + 残余地平线 | 中 → 弱 | 模糊、长 | 温度过渡 | ``"dusk, transitioning from warm 4500K sun glow to cool 6500K sky, long blurred shadows, atmospheric perspective"`` |
| **Dawn** | 4500K → 5500K | 漫散 + 地平线起 | 弱 → 中 | 模糊、长 | 晨雾 | ``"dawn, soft 4500K sunrise glow rising from horizon, ground-level mist, gentle long shadows, cool ambient sky"`` |
| **Night - Moonlit** | 8000K + practicals | 顶部漫散 + 局部暖 | 弱 + 强 practical | 深、模糊 | 蓝灰 | ``"moonlit night, cool 8000K moonlight from above, warm 2700K practical lanterns scattered, deep blue-grey shadows, strong cool-warm contrast"`` |
| **Night - Urban** | mixed practicals | 多源混合 | 局部强 | 多重 | neon glow | ``"urban night, mixed practical lighting from neon signs and street lamps, multi-colored ambient glow, deep shadows between light pools"`` |
| **Stormy** | 5500K + 雷电 | 顶部漫散 + 瞬时硬光 | 弱 + 极强瞬时 | 模糊 + 锐 | 雨雾 | ``"stormy weather, 5500K diffused stormy daylight, occasional sharp lightning flash from upper-right, wet atmospheric haze, rain streaks"`` |

## 流派配方表（Genre-Specific Lighting Formulas）

不同流派有自己的灯光习惯——选错流派下游图风格脱节。

### Anime（动画）

- **典型**：cel-shading 2-tone（光面 / 暗面分离，无渐变）
- **key:fill**：1:2 ~ 1:4
- **rim light**：必有——anime 角色离不开 rim 分离背景
- **practicals**：高频用（灯笼 / 火焰 / 魔法光球）
- **prompt 片段**：``"anime cel-shading lighting, clear 2-tone separation of lit and shadow areas, soft 1:2 key:fill ratio, strong rim light from behind, vibrant colors"``
- **代表**：Studio Trigger / Kyoto Animation / Madhouse

### Photorealistic / Film（实拍电影）

- **典型**：三点光 + practicals
- **key:fill**：1:4 ~ 1:8（戏剧）/ 1:2（柔和）
- **rim light**：subtle，靠 fill + back combined
- **practicals**：必有 motivated（窗 / 灯 / 火）
- **prompt 片段**：``"cinematic film lighting, motivated key from window 45° camera-left, 1:4 key:fill ratio, subtle rim from window edge, warm practical lamps in background, shot on Arri Alexa"``
- **代表**：Roger Deakins / Hoyte van Hoytema / Bradford Young

### Noir（黑色电影）

- **典型**：low key + 硬光 + chiaroscuro
- **key:fill**：1:8 ~ 1:16（极高对比）
- **rim light**：常用百叶窗 venetian blind 投影
- **色温**：低饱和单色调（cool blue 或 warm sepia）
- **prompt 片段**：``"film noir lighting, low key chiaroscuro, hard 1:8 key:fill ratio, single source key from upper-side casting dramatic shadows, venetian blind slat shadow patterns, desaturated cool palette"``
- **代表**：Citizen Kane / Blade Runner / The Lighthouse

### Pixar / Disney 3D

- **典型**：high key + 多源软光 + practicals
- **key:fill**：1:2（柔和）
- **rim light**：subtle，多为环境光
- **色温**：饱和、温暖、对比中等
- **prompt 片段**：``"Pixar-style 3D lighting, high key with 1:2 soft fill ratio, multiple soft sources, warm saturated colors, subtle rim light, no harsh shadows, optimistic mood"``
- **代表**：Toy Story / Coco / Up

### Ghibli / Watercolor

- **典型**：natural light + atmospheric perspective
- **key:fill**：1:2 ~ 1:3（柔和）
- **rim light**：靠天空漫射，无明显 rim
- **色温**：自然、大地色系
- **prompt 片段**：``"Ghibli-style natural lighting, soft 1:2 fill from open sky, atmospheric perspective with hazy distant elements, warm earth tones, painterly soft shadows"``
- **代表**：Studio Ghibli（Spirited Away / Howl's Moving Castle）

### Cyberpunk

- **典型**：multi-color practicals（cyan + magenta + amber）+ 湿地面反光
- **key:fill**：1:8（高对比、低饱和环境 + 高饱和 practicals）
- **rim light**：常用 neon 边缘
- **色温**：极端混合（冷主调 + 暖局部）
- **prompt 片段**：``"cyberpunk neon lighting, mixed cyan and magenta practicals, 1:8 contrast ratio between dark ambient and bright neon, wet reflective surfaces, atmospheric haze with light beams"``
- **代表**：Blade Runner / Ghost in the Shell

## Lighting Consistency 铁律（角色一致性的关键）

同一角色的三视图 + 所有变体 i2i，**key light 方向必须一致**——否则下游 i2i 出来五官的阴影漂移，看起来像不同时段拍的不同人。

- 三视图（front + side + back）默认 ``front-left 45° soft light``
- 表情变体（angry / smile / 等）i2i 时**不要改变 key 方向**
- 服装变体 / 战斗姿态 i2i 时**也保持同 key 方向**

只有在做"特定场景下的角色镜头"时（如角色 close-up 在战火中），才按场景的 motivated light 调整方向——但那是 video_prompt 阶段的事，不是 character_ref 阶段。

## 反例 / 陷阱

### ❌ 反例 1：无 motivation 的光

```
"光照柔和，气氛肃穆"
```

**后果**：模型不知道光从哪来，每张图光照随机摆，三视图各张光照不一致；i2i 变体光照漂移。

**正例**：

```
"motivated soft key light from upper-right window at 45°, 5500K natural daylight,
1:3 key:fill ratio, soft shadow fall-off"
```

### ❌ 反例 2：色温混乱

```
"warm golden sunlight + cool blue moonlight + magenta neon"
```

**后果**：三种色温在一个镜头里，模型解读为"廉价滤镜"，画面发腻。

**正例**：

```
"warm 3200K golden sunlight as key, cool 6500K skylight as fill,
two-temperature contrast"
```

只用两种色温，对比明确。

### ❌ 反例 3：缺 rim light，主体糊进背景

```
"key light from front, fill from side"
```

**后果**：anime 风格里没 rim light = 角色边缘融化进背景，立体感丢失。

**正例**：

```
"key light 45° front-left, fill 45° front-right at half intensity (1:2),
strong rim light from upper-back at 45°, clear separation between subject and background"
```

### ❌ 反例 4：lighting consistency 违反

三视图 front 用 ``key from left``，side view 用 ``key from right`` —— i2i 出表情变体时，模型不知道哪边是受光面，每张变体阴影方向随机变。

**正例**：所有三视图 + 所有变体都用 ``soft front-left 45° key``，方向钉死。

## L3 References

### @ref: time-of-day-recipes

完整的 12 个时段配方表，含 prompt 片段 + 适用场景 + 色温过渡曲线。比主体里的简表多包括 mid-morning / late-afternoon / pre-dawn / post-dusk 等过渡时段。

### @ref: classic-light-positions

完整的 8 种经典光位（Rembrandt / loop / split / butterfly / broad / short / rim / silhouette），每种含 prompt 片段 + 代表电影 + 示意图描述。

### @ref: genre-lighting-cheatsheet

10 种流派的灯光速查表，含具体导演 / 摄影师 / 工作室引用作为风格锚点。

---

## reference: time-of-day-recipes

<这里放完整 12 时段的扩展配方，结构与主体的简表一致但内容更全。
用户后续按这个 ref_key 由 video_prompt_agent / scene_ref_agent 调
load_skill_reference 加载。>

（此 example 文件保留入口，完整内容由用户根据实际需要扩展）

## reference: classic-light-positions

<8 种经典光位的完整 cookbook。完整内容由用户扩展。>

## reference: genre-lighting-cheatsheet

<10 种流派的灯光速查表。完整内容由用户扩展。>
