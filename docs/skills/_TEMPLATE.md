---
name: <skill-slug-kebab-case>
description: Use when <激活条件 / 触发场景> to <达到的目的>. Provides <核心内容简述>.
target_agents: [<agent_name_a>, <agent_name_b>]
tags: [<topic-1>, <topic-2>, <topic-3>]
author: filmgenx
---

<!--
========================================================================
Skill Body 写作模板（"专业老炮手册"标准）
========================================================================

写作原则：
1. 这不是"通才教程"，是"行业老手在给新人讲门道"——术语密度高、配方精度细、
   有大师 / 工作室 / 流派的具体锚点
2. 一切判断都给配方（参数 / 比例 / 标号）而不是抽象原则
3. prompt 片段直接可拼接（不要写"参考……"，写出可复制的字符串）
4. 引用业内权威（导演 / 摄影师 / 工作室 / 经典作品名）
5. 反例语料——告诉新人"这样写出来是什么后果"
6. 用 @ref:<key> 标记 L3 references——细节段落让 agent 按需 load_skill_reference 加载

文件结构（每个 skill 都按这个 8 节走，按需取舍）：
1. 这是什么            一段话讲清这个 skill 解决什么问题、为什么存在
2. 核心信条 / 第一原理  3-5 条专业准则，作为后续所有配方的源头
3. 术语词汇表          专业名词 → 含义 / 行业别名 / 通用误用纠正
4. 决策矩阵 / 配方表    场景 → 具体参数（数字 / 比例 / 标号）
5. Prompt 片段库       可直接拼接的字符串模板
6. 反例 / 陷阱          典型错误 + 后果（让 agent 知道"这样写完蛋"）
7. 工作流              如果有标准步骤序列，列出
8. @ref 入口            列出本 skill 的 L3 references，标明 ref_key

frontmatter 字段：
- name：kebab-case slug，与文件名一致（character-design / lighting-cookbook / ...）
- description：必须用 "Use when ... to ..." 句式，明确激活条件 + 目的——
  agent 在 L1 元信息列表里只能看到这一句，决定要不要 load_skill
- target_agents：列出主要使用者；agent 启动时框架按这个反查注入到 L1 列表
- tags：搜索 / 分类用；至少 2 个，最多 5 个
- author：作者标识

写作风格红线：
- ❌ "光照要漂亮" / "构图要丰富" / "色彩要协调" —— 空话，扣分
- ✅ "key:fill 1:4 ratio, 3200K key light at 45° camera-left" —— 配方精度
- ❌ "anime 风格" —— 信息密度低
- ✅ "anime cel-shading, in the style of Studio Trigger / Kyoto Animation" —— 锚点明确
- ❌ "用三分法" —— 谁不知道
- ✅ "主体放右三分点 vertical line 与下三分 horizontal line 交点 → '强势角点'，
       常用于 protagonist establishing shot；放左下三分 → '弱势角点'，常用于
       defeated character 倒地" —— 才是专业判断力
========================================================================
-->

# <skill 中文标题（业内用语）>

<一段话讲清楚：这是什么 skill、解决什么问题、为什么 agent 需要它。3-5 句以内。
强调用户场景而不是模糊概念——"当 character_ref_agent 要为某个 art_genre 选
具体头身比 / 描边粗细时，本 skill 给你 7 种主流 art_genre 的精确配方表"。>

## 核心信条 / 第一原理

<3-5 条**指导后续所有配方**的源头准则。这些准则在任何子情境下都成立，
是"为什么这套配方是这样"的根源。>

例（lighting-cookbook 的核心信条可能是）：
- **光的来源必须有动机（motivation）**：画面里观众应能识别光源（天窗 / 灯具 / 火 / 雷），无动机的光让画面假
- **三色温度规则**：3200K（warm）/ 5600K（neutral）/ 8000K+（cool blue）——一个镜头里不要混超过两种色温
- **1:N ratio 决定戏剧性**：1:2 自然柔和 / 1:4 戏剧温和 / 1:8 强烈戏剧 / 1:16 黑色电影
- **每个镜头至少 3 层光**：key（主光）+ fill（补光）+ rim/back（轮廓光）；缺一变平
- ...

## 术语词汇表（你必须知道的行业名词）

| 术语 | 含义 | 通用误用纠正 |
|---|---|---|
| **<术语 1>** | <精确定义> | <新人常误用为 / 混淆为 ……> |
| **<术语 2>** | <精确定义> | <例：dolly ≠ zoom——dolly 物理位移，zoom 焦距变> |
| ... | ... | ... |

## 决策矩阵 / 配方表

<给"什么场景 → 什么参数"的查找表。配方要精确到数字 / 比例 / 标号，
不要给原则，给可执行参数。>

### <子主题 A，例：art_genre × proportions>

| Genre | 头身比 | 描边 | 表情夸张度 | 代表工作室 / 大师 |
|---|---|---|---|---|
| shounen anime（少年漫） | 7-7.5 头身 | 中粗黑描边 | 中高 | Studio Trigger / MAPPA |
| shoujo anime（少女漫） | 7.5-8 头身 | 细黑描边或淡彩 | 中（眼睛大） | Madhouse |
| seinen anime（青年漫） | 7.5-8 头身 | 细描边或无描边 | 低（写实） | Production I.G |
| moe / chibi | 4-5 头身 | 中粗描边 | 高（夸张） | Kyoto Animation |
| ghibli | 6-7 头身 | 无描边或淡 | 低（自然） | Studio Ghibli |
| ... | ... | ... | ... | ... |

### <子主题 B，例：lighting × time-of-day>

| 时段 | 色温 | 方向 | 强度 | 阴影 | prompt 片段 |
|---|---|---|---|---|---|
| Golden Hour | 3200K | 低角度 15° 侧逆 | 中 | 长而柔 | ``"golden hour, warm 3200K key light from low 15° back-side, long soft shadows, atmospheric particles"`` |
| Blue Hour | 8000K | 漫散无方向 | 弱 | 几乎无 | ``"blue hour twilight, cool 8000K ambient sky light, diffuse soft shadow, magic hour mood"`` |
| Noon Harsh | 5600K | 垂直上方 90° | 强 | 短而硬 | ``"high noon, harsh 5600K overhead sunlight, short hard shadows, high contrast"`` |
| Overcast | 5500K | 漫散无方向 | 弱 | 几乎无 | ``"overcast soft daylight, 5500K diffused sky light, no clear shadows, low contrast"`` |
| ... | ... | ... | ... | ... | ... |

## Prompt 片段库

<可直接拼接的字符串。每条片段说明：用在哪 / 怎么拼 / 推荐 weight。>

### <片段类型 A，例：quality boosters>

```
masterpiece, best quality, highly detailed, sharp focus, professional photograph
```

适用：t2i 起步，作为 prompt 末尾质量锚。weight 推荐默认（不加权）。

### <片段类型 B，例：negative boosters>

```
deformed, extra limbs, missing fingers, blurry face, low quality, jpeg artifacts,
text, watermark, signature, ugly, disfigured
```

适用：所有 t2i 必带。anime 角色再加 ``photorealistic, real photo``；photoreal 加 ``anime, cartoon, illustration``。

## 反例 / 陷阱（**仔细读**）

<列出常见错误 + 错误后果。让 agent 知道"这样写出来是什么样"。>

### ❌ 反例 1：<错误描述>

```
<错误 prompt 示例>
```

**后果**：<错误会导致什么——五官漂移 / 风格冲突 / 模型忽略 / ...>

**正例**：

```
<正确 prompt 示例>
```

### ❌ 反例 2：<...>

...

## 工作流（如果适用）

<如果这个 skill 涉及多步骤流程，列出标准序列。每步说明：做什么、产出什么、何时进下一步。>

1. **Step 1: <名称>** — <做什么 + 产出>
2. **Step 2: <名称>** — <做什么 + 产出>
3. ...

## L3 References（按需 load_skill_reference 加载）

<列出本 skill 拆出的 L3 子文档。每条说明 ref_key + 内容简述。
agent 在主体（L2）里看到 @ref:<key> 标记时，按这个表去加载。>

### @ref: <ref-key-1>

<这个 reference 包含什么细节。例：完整的 expression-prompt-cookbook，
15 种表情的中英双语 prompt 片段 + 适用场景。>

### @ref: <ref-key-2>

<...>

---

<!-- 以下是 L3 reference 的实际内容，在 reference 章节下用 ## 二级标题切分 -->

## reference: <ref-key-1>

<完整 reference 内容，用 ## 标题与主体内容隔开。agent 调
``load_skill_reference(skill='<skill-name>', ref_key='<ref-key-1>')`` 时拿到这段。>

## reference: <ref-key-2>

<...>
