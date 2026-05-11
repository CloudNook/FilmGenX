---
name: frame-prompt-engineering
description: Use when translating storyboard shots into ready-to-generate Chinese image prompts for gemini-image. Provides the five-element prompt formula (composition + character + scene + lighting + props), per-shot-size templates, and rules for consuming character / scene / style KV without re-imagining content.
target_agents: [frame_prompt_agent]
tags: [image-prompt, frame, gemini-image, prompt-engineering]
author: filmgenx
---

# 首帧图 prompt 工程

frame_prompt_agent 的输出会**直接喂给图像模型**，所以 prompt 质量直接决定成片画面。本 skill 给五要素公式、按景别拆分的 prompt 模板、KV 引用规范，以及关键镜头草图验证的工具调用流程。

## 核心原则

下游已经为你准备好了 KV：``character.萧炎.appearance`` / ``scene.云岚宗广场.atmosphere`` / ``style.palette.description`` ……**直接复制字段值**到 prompt 里，不要"凭印象再描述一遍角色长什么样"——那会和 character_ref 失去一致性。

## 五要素公式

每个 ``image_prompt`` 必须涵盖五段，按这个顺序写最稳：

```
[1. 构图 / 景别]: 中景, 主角偏右 1/3 位置, 低角度仰拍
[2. 角色动作 + 表情]: 萧炎 {character.萧炎.appearance}, determined 表情 {character.萧炎.expressions.determined}, 双手紧握玄重尺侧身预备战姿态
[3. 场景背景]:        云岚宗广场 {scene.云岚宗广场.architecture}, {scene.云岚宗广场.atmosphere}
[4. 光影色调]:        {style.lighting.description}, {style.palette.description}, 黄昏侧光剪影主角, 远景烟雾扩散
[5. 关键道具]:        玄重尺(尺端微红), 飞扬战袍下摆
```

总长度约 80-200 字。低于 80 通常细节不够；高于 200 模型注意力会被稀释。

## 按景别选模板

不同 ``shot_size`` 的 prompt 重心不同：

### ELS / LS（远景）

重心在**场景** + **构图层次**，角色描述简化：

```
[构图]: 远景, 主角占画面 1/4, 居中略偏左
[角色]: 萧炎 silhouette, determined posture
[场景]: {scene.location.architecture 完整}, 远景到地平线, 三层纵深
[光影]: {style.lighting} 全景式, 大气透视
[道具]: 远处有 {props}
```

不要在远景里堆角色细节——根本看不见。

### MS / MCU（中景 / 中近）

主体是**对话戏 / 互动戏**的标准景别。重心是**角色 + 表情 + 动作**：

```
[构图]: 中景, 双人 OTS 或正反打, 主体占画面 1/2
[角色]: {character.A.appearance} {character.A.expressions.X}, {character.B.appearance} {character.B.expressions.Y}, 站姿距离 + 视线方向
[场景]: 简化背景, 局部 {scene.atmosphere}
[光影]: {style.lighting}, 注意角色面部受光
[道具]: 桌面 / 手中物
```

### CU / ECU（特写 / 大特写）

重心是**情绪 + 细节**，背景几乎抛弃：

```
[构图]: 特写, 主体占画面 2/3, 中心构图或斜对角线
[角色]: {character.X.expressions.<情绪>} 详细描述眼神 / 嘴角 / 微表情
[场景]: 极度虚化背景, 只保留 {scene.atmosphere} 色调氛围
[光影]: 高对比, 单一光源勾勒轮廓, eye light catchlight
[道具]: 手部特写时强调 {props 单件}
```

### POV / OTS（主观 / 过肩）

按"用谁的视线看出去"决定：

```
[构图]: OTS, A 的肩头剪影占左 1/3, B 在右 2/3
[角色]: B 占主体, B 表情 + 动作; A 仅剪影
[场景]: 适度可见
[光影]: B 受光, A 暗部剪影
```

## KV 引用规范

下面这些 KV 字段必须**直接复制**到 prompt 里，不重写：

| KV 字段 | 写到 prompt 里时 |
| --- | --- |
| ``character.<name>.appearance`` | 整段拼到角色描述前半 |
| ``character.<name>.expressions.<key>`` | 拼到角色描述的表情位 |
| ``scene.<location>.architecture`` | 拼到场景段第一句 |
| ``scene.<location>.atmosphere`` | 拼到场景段第二句 |
| ``scene.<location>.lighting`` 或 ``style.lighting`` | 拼到光影段，二选一（场景特有 vs 全片统一） |
| ``style.palette.description`` | 拼到光影段末尾 |
| ``style.composition.description`` | 影响构图段写法 |
| ``style.negative_anchor`` | 复制到 negative_prompt 字段开头 |

**character_refs / scene_ref 字段**只是引用 name / location 字符串，**不是把字段值写进去**——下游通过 name 反查 KV 拿完整数据。

## model_hint 选择

| 镜头类型 | model_hint | 理由 |
| --- | --- | --- |
| 高潮 / 转折 / 情感顶点 | ``gemini-3-pro-image-preview`` | 全片记忆点，必出最佳质量 |
| 角色 close-up / 关键表情 | ``gemini-3-pro-image-preview`` | 表情精度直接决定情绪传达 |
| 远景 / 过场 / 镜头连接 | ``gemini-3.1-flash-image-preview`` | 速度快、成本低、信息密度低 |
| 草图验证 / 临时确认 | ``gemini-3.1-flash-image-preview`` | 验证用，不入库 |

短剧（60 秒）建议 30% 用 pro、70% 用 flash。

## negative_prompt 公式

```
{style.negative_anchor} + {本镜特异}
```

本镜特异举例：
- OTS 镜头：``no front face, no two faces visible``
- 室内场景：``no outdoor, no sky``
- 单人镜：``no other characters, no crowd``
- 远景：``no detailed face, no close-up details``

## 关键镜头草图验证

frame_prompt_agent 可以在产出 ``FramePromptSet`` 之前 / 之中，对**最关键的 1-2 个镜头**调 ``generate_image`` 出草图验证。但要严格遵守工具调用协议：

### 流程

1. **本轮口头说明**:
> "镜头 7 是高潮决斗的关键 image_prompt（萧炎释放佛怒火莲），我担心 prompt 里"双色异火融合"模型理解不到位。下一步我会用 ``model="gemini-3.1-flash-image-preview"`` 出一张草图验证（flash 省额度、速度快），如果效果偏，会调整 prompt 里"火焰描述"那段再用 pro 出最终首帧。"

2. **下一轮**: 调 ``generate_image(prompt=<image_prompt>, model="gemini-3.1-flash-image-preview", aspect_ratio="16:9")``

3. **看结果再说**:
- 效果到位 → 把 prompt 锁定到最终 FramePromptSet
- 效果偏 → 本轮口头说"草图里异火没融合，我打算把 prompt 里 'two colors swirling together' 改成 'magenta and emerald flames spiraling and merging at the center'，下一步重新调 generate_image 验证"

### 不要做的

- 不要给所有镜头都调 generate_image（这是下游编排器的工作）
- 不要直接 call_tool 不解释（违反工具调用协议）

## 反例

- prompt 里漏掉光照 → 出图灰扁，缺氛围
- 把 character.appearance 自己改写一遍 → 和 character_ref 失去一致性
- character_refs 引用 character.* 里不存在的 name → 下游断链
- 一个 image_prompt 描述多个画面 → 违背"首帧"概念
- 把对白文字塞进 image_prompt → 图像不需要文字
- aspect_ratio 不统一 → 全片画面比例混乱

## 工作流（强调先口头说明再调用工具）

每次准备调 ``load_skill_reference`` / ``generate_image`` / ``memory_save``：
1. 本轮先口头说明意图 + 理由
2. 下一轮才调工具

例：
> "Storyboard 给了 24 个镜头，主要分散在 3 个 location。下一步我打算先按 location 分组、按景别从大到小排，一次性产出所有 image_prompt。其中镜头 7 / 12 是高潮，我想先调 ``load_skill_reference(skill='frame-prompt-engineering', ref_key='shot-size-prompt-templates')`` 拿到 ECU 模板，再回来写。"

## reference: shot-size-prompt-templates

10 种景别的 prompt 起手模板，可直接套用：

### ELS（大远景）

```
极远景, 主体仅占画面 1/8, 大量天空 + 地形, 大气透视, 三层纵深拉满
"extreme long shot, vast landscape, tiny figure in distance, atmospheric haze, layered depth"
```

### LS（远景）

```
远景, 主体占画面 1/4, 完整环境可见, 主体与周围关系
"long shot, full body visible, surrounding environment dominant, establishing shot"
```

### FS（全景）

```
全景, 主体占画面 1/3 ~ 1/2 高度, 头到脚清晰, 部分环境
"full shot, full body, character takes upper third, slight environment context"
```

### MS（中景）

```
中景, 腰部以上, 主体占画面 1/2, 对话戏标准
"medium shot, waist up, character occupies half frame, standard dialogue framing"
```

### MCU（中近景）

```
中近景, 胸口以上, 主体占画面 2/3
"medium close-up, chest up, character dominates two-thirds of frame"
```

### CU（特写）

```
特写, 头部 + 部分肩, 主体占画面 3/4, 情绪戏标准
"close-up, head and shoulders, dominates frame, emotional intensity"
```

### ECU（大特写）

```
大特写, 仅五官某部分（眼 / 嘴 / 手）, 占满画面, 极致情绪 / 关键细节
"extreme close-up, eyes only / mouth only / hand only, fills entire frame, intense emotion or key detail"
```

### OTS（过肩）

```
过肩镜头, 前景肩剪影占左 1/3, 主体在右 2/3, 双人对话标配
"over-the-shoulder shot, foreground shoulder silhouette on left third, subject in right two-thirds"
```

### POV（主观）

```
主观镜头, 第一人称视角, 视线引导, 看到的物体充满画面
"point of view shot, first person perspective, what the character sees fills frame"
```

### INSERT（插入特写）

```
插入特写, 单一道具或细节, 极简背景, 视觉锚点
"insert shot, isolated prop / detail, minimal background, visual anchor"
```

## reference: lighting-keyword-cookbook

光照关键词速查（可直接拼到 prompt）：

### 主光方向

| key | 中文描述 | 英文 tag |
| --- | --- | --- |
| top_light | 顶光（戏剧性 / 严肃） | overhead lighting, harsh top light |
| side_light | 侧光（雕塑感 / 强对比） | side lighting, dramatic chiaroscuro |
| back_light | 逆光（剪影 / 神秘） | backlight silhouette, rim light |
| three_quarter | 3/4 光（人像标准） | three-quarter lighting, classic portrait setup |
| under_light | 仰光（恐怖 / 反派） | uplight, sinister lighting from below |
| flat_light | 平光（柔和 / 治愈） | flat lighting, soft diffuse, no shadows |

### 光质

| key | 中文 | 英文 tag |
| --- | --- | --- |
| hard | 硬光 | hard light, sharp shadows, high contrast |
| soft | 柔光 | soft diffuse light, gentle shadows |
| rim | 边缘光 | rim lighting, edge highlight |
| volumetric | 体积光（光柱） | volumetric lighting, god rays, light shafts |

### 光色

| key | 中文 | 英文 tag |
| --- | --- | --- |
| warm | 暖光 | warm tungsten light, golden tone |
| cool | 冷光 | cool blue light, daylight tone |
| mixed | 冷暖对比 | mixed color temperature, teal-and-orange contrast |
| neon | 霓虹 | neon lighting, magenta and cyan |
| candlelight | 烛光 | candlelight, flickering warm orange |

### 时段叠加

```
golden_hour: warm golden hour light, low angle, long shadows
blue_hour: blue hour, dusk, purple-blue sky
night_practical: moonlit + practical lights (street lamps / windows / fire)
overcast: overcast diffused lighting, soft shadows, cool grey tone
```
