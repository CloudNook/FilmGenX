---
name: character-design
description: Use when designing character reference packs (base appearance + expression set + clothing + accessories) so every downstream shot can render the same character consistently. Provides decision rules for proportion / linework / expression coverage and prompt patterns for image generation.
target_agents: [character_ref_agent]
tags: [character-design, reference-image, prompt-engineering]
author: filmgenx
---

# 角色形象设计

角色形象设计的目标不是"画一个好看的人"，而是**把每个角色的视觉锚点钉死**——让后续每个镜头看到角色名都能直接复用同一套外观描述，不出现"长不一样"的灾难。

本 skill 给 character_ref_agent 在出 ``CharacterRefSet`` 时的设计原则、出图 prompt 模板、以及表情 / 服装变体的覆盖规则。

## 一致性的本质

角色"长不一样"通常是因为：
- **base_prompt 含动作 / 表情** → 每次生成都被动作姿态干扰
- **关键特征顺序不稳定** → 模型每次抓到的"这个角色是什么"不同
- **缺少 negative_prompt** → 被生成器的常见误区拉走（女主被画成男主、成人被画成少年）
- **服装描述跟身体描述混在一起** → 换装时连身体也变了

## base_prompt 的标准结构

按这个固定顺序写，能最大化模型的一致性：

```
{年龄段} + {性别} + {发型 + 发色} + {瞳色} + {体型} + {核心服装} + {核心特征 / 招牌道具} + {风格关键词}
```

例：
```
青年男子, 黑色长发束起, 黑色瞳孔, 偏瘦修长身形, 玄铁色长袍战服, 背负玄重尺,
anime cel shading style
```

**禁止**在 base_prompt 出现：表情（皱眉 / 微笑）、动作（站立 / 奔跑）、视角（正面 / 侧面）、特定光照。这些都是变体的工作。

## 三视图 prompt 公式

```
{base_prompt}, three view sheet, front view + side view + back view,
neutral pose, neutral expression, full body, plain white background, T-pose
```

固定参数：``aspect_ratio="9:16"``（角色竖图标准）、``model="gemini-3-pro-image-preview"``（主角必 pro）。

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

主角必须有 ``determined`` + 一种负面情绪（angry / sad）+ 一种正面情绪（smile / surprised）。这是叙事最低覆盖。

### 配角 1-3 种

按"该角色在剧情里只表现哪几种情绪"决定。例如纯反派可能只需要 ``angry`` + ``shocked``。

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
| 男主 / 男配 | ``female, woman, child, makeup, breasts`` |
| 女主 / 女配 | ``male, man, child, beard, muscular`` |
| 成年角色 | ``child, kid, baby, teenager`` |
| 少年角色 | ``adult, mature, beard`` |
| 凡人角色 | ``glowing eyes, magical aura, fantasy effects`` |

外加 art_genre 通用负面：anime 加 ``photorealistic, realistic skin texture``；photorealistic 加 ``anime, cartoon, illustration``。

## 反例

- base_prompt 写"萧炎，黑发，正在挥舞玄重尺"——含动作了
- 全部 expressions 用同样句式"皱眉 + xxx"——伪变体
- accessories 漏掉招牌武器——后续战斗镜头武器消失
- negative_prompt 只写 art_genre 通用项，没写性别——男主被画成女主
- name 和 outline 不一致（"陆沉"写成"陆沉君"）——下游引用断链

## 工作流（强调先口头说明再调用工具）

每次准备调 ``load_skill_reference`` / ``generate_image`` / ``memory_save``，都要：
1. 本轮先口头说明意图 + 理由
2. 下一轮才调工具

例：
> "我注意到萧炎是 anime 风格的玄幻男主，需要 4 张表情变体（determined / angry / smile / surprised）。下一步我会先调 ``load_skill_reference(skill='character-design', ref_key='expression-prompt-cookbook')`` 拿到具体的表情 prompt 片段模板，再回来写 expressions 字段。"

## reference: expression-prompt-cookbook

5 种核心表情的 prompt 片段（中文 + 英文 anime tag），可直接拼到角色变体里：

### determined（决心 / 战斗前）

```
中文: 紧抿嘴角, 瞳孔聚焦, 微皱眉, 下颌微抬, 眼神锐利
英文 tag: serious face, focused eyes, slight frown, tight lips, intense gaze
```

适用：战斗前夜、做出决定、面对反派。

### angry（愤怒 / 仇恨）

```
中文: 眉心紧锁, 咬牙切齿, 瞳孔放大, 青筋微现, 嘴角下扯
英文 tag: angry expression, gritted teeth, furrowed brow, dilated pupils, snarling
```

适用：受辱、仇恨爆发、被背叛。

### sad（悲伤 / 失落）

```
中文: 眉尾下垂, 眼神空洞, 唇角下拉, 眼眶微红, 头微低
英文 tag: sad face, downturned mouth, teary eyes, drooping eyebrows, downward gaze
```

适用：失去亲人、求而不得、回忆旧伤。

### surprised（惊讶 / 震惊）

```
中文: 瞳孔瞪大, 嘴微张, 眉毛抬高, 头部微后仰, 表情僵住
英文 tag: shocked face, wide eyes, open mouth, raised eyebrows, surprised expression
```

适用：突发事件、意外发现、剧情反转。

### smile（微笑 / 胜利）

```
中文: 嘴角上扬, 眼神柔和, 微眯眼, 下颌微抬, 神情释然
英文 tag: gentle smile, soft eyes, slight smirk, relaxed face, content expression
```

适用：胜利、释然、温情时刻。

### 反派专用：cold_smile（冷笑 / 优越）

```
中文: 嘴角单边上扬, 眼神锐利, 下巴微抬, 冷漠的笑意
英文 tag: smirk, cold smile, raised chin, disdainful eyes, condescending expression
```

适用：反派出场、傲慢宣言、阴谋得逞。

## reference: art-genre-character-proportions

不同 art_genre 对角色 proportion / linework 的要求：

### anime（玄幻战斗番）

- proportion: 7-7.5 头身（少年）/ 8-8.5 头身（成年战士）；夸张瞳孔（占脸 1/4）
- linework: clean cel shading，硬边阴影 2-3 层，无柔光过渡
- 标准 prompt 关键词: ``anime style, cel shaded, sharp linework, large expressive eyes, dynamic poses``

### photorealistic（都市 / 写实）

- proportion: 真人 7.5-8 头身，正常脸部比例
- linework: 无明显线条，靠光影建模
- 标准 prompt 关键词: ``photorealistic, true-to-life proportions, natural skin texture, 35mm, sharp focus, soft natural lighting``
- 注意: 慎写"细致 hair strands"，否则容易翻车

### pixar_3d（合家欢 / 温情）

- proportion: 矮胖化（5-6 头身），眼睛 + 头部放大
- linework: subsurface scattering，rim light 突出
- 标准 prompt 关键词: ``pixar 3d animation style, stylized proportions, large head, expressive face, subsurface scattering, warm lighting``

### ghibli（治愈 / 自然）

- proportion: 7-7.5 头身，柔和五官
- linework: painterly background + 简洁人物线条，水彩感
- 标准 prompt 关键词: ``ghibli studio style, soft watercolor, painterly, gentle expression, lush environment``

### cyberpunk（未来 / 暗调）

- proportion: 真人比例 + cybernetic 改造件
- linework: neon rim light，潮湿表面
- 标准 prompt 关键词: ``cyberpunk style, neon rim lighting, cybernetic implants, holographic UI elements, rain-slick reflections``

### noir（黑色悬疑）

- proportion: 真人 8 头身
- linework: 硬光 + 大面积阴影 + 单一红色 accent
- 标准 prompt 关键词: ``film noir, monochrome with red accent, harsh shadows, low-key lighting, smoky interior, venetian blind shadows``

### watercolor（诗意 / 文艺）

- proportion: 7-7.5 头身，柔化轮廓
- linework: visible brushstrokes，wet edges
- 标准 prompt 关键词: ``watercolor illustration, visible brushstrokes, soft saturation, paper texture, dreamy atmosphere``

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
