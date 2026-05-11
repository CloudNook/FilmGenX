---
name: scene-design
description: Use when designing scene reference packs (location description + atmosphere + lighting + time variants + props) so every shot in that location renders with consistent environment language. Provides decision rules for atmosphere / lighting / time-of-day handling and prompt templates for environment image generation.
target_agents: [scene_ref_agent]
tags: [scene-design, environment, reference-image, prompt-engineering]
author: filmgenx
---

# 场景设计

场景设计的目标不是"画一个好看的地方"，而是**把每个 location 的视觉锚点钉死**——让后续每个发生在这里的镜头都共享同一份"这里长什么样"，并按时段 / 天气提供变体。

本 skill 给 scene_ref_agent 在出 ``SceneRefSet`` 时的设计原则、出图 prompt 模板、以及 time_variants 的覆盖规则。

## 一致性的本质

场景"画得不像同一处"通常是因为：
- **architecture / atmosphere / lighting 写在一句话里** → 模型抓不住主导特征
- **缺 negative_prompt** → 室内场景被画到了室外、白天场景被画成了夜晚
- **时段变体堆在主 prompt 里** → 每次生成天气不可控
- **props 被压缩** → "云岚宗"少了那口标志性青铜钟，下游看了不认识

## 三段式 prompt 结构

把场景描述拆成三个独立段，模型对每段的注意力更稳定：

```
[architecture]: 建筑 / 地形 / 空间结构（"白玉广场, 高耸古青铜钟, 远处有重重宗门殿宇, 三层石阶")
[atmosphere]:   情绪 / 氛围（"肃杀压抑, 万人聚集后的死寂, 弥漫沉重战意")
[lighting]:     光照 / 时段（"清晨薄雾, 顶光散射, 地面反射冷灰光, 远景剪影")
```

合起来给模型：``{architecture}, {atmosphere}, {lighting}, {color_restrictions}``

## time_variants 的边界

每个 location **最多 3 个时段变体**，按以下优先级挑：

1. **剧情明确出现的时段**（如剧本写"日落决斗"）—— 必出
2. **戏剧反差大的时段**（如同一场地白天 / 夜晚出现两次）—— 必出
3. **气氛抓手的时段**（cyberpunk 必夜、ghibli 必日）—— 必出

如果剧情里只在一个时段出现，**不要凑变体**——单一变体就够了。

每个 variant 的 value 写**该时段下变化的部分**（光照 / 氛围 / 颜色），不要重复 architecture：

```python
time_variants = {
    "day":   "顶光强烈, 白玉反光刺眼, 暖橙色调",
    "night": "月光冷光, 青铜钟反射蓝灰光, 远景灯火点点",
    "rain": "雨幕笼罩, 地面湿润反光, 雾气朦胧, 整体降饱和"
}
```

## color_restrictions（喂给 SD 模型的英文标签）

写法用 SD-style 英文标签，不是中文长句：

| 题材 | color_restrictions |
| --- | --- |
| anime 玄幻 | ``saturated reds and golds with cool blue accents, slightly desaturated`` |
| photorealistic 都市 | ``muted greys and browns, cold blue sky, warm orange streetlights`` |
| pixar_3d | ``high saturation warm orange and yellow with cool teal accents`` |
| ghibli | ``soft greens and blues, cream whites, occasional warm reds`` |
| cyberpunk | ``deep blue and magenta neon, teal-and-orange complementary, electric blue accents`` |
| noir | ``monochrome black and grey with single red accent, harsh shadows`` |
| watercolor | ``soft pastels, watercolor washes, muted palette`` |

## mood_keywords（中文短词列表）

中文短词，3-6 个，给下游 frame_prompt 拼镜头描述时复用：

```python
["废墟感", "压抑", "肃杀", "孤立", "庄严"]
["温馨", "亲密", "怀旧", "柔软", "日常"]
["冷峻", "未来感", "潮湿", "霓虹", "疏离"]
```

不要写句子（"主角在这里发现真相"是情节，不是 mood）。

## negative_prompt 必含

按场景类型写：

| 场景类型 | negative_prompt 必含 |
| --- | --- |
| 室内 | ``no outdoor, no sky, no horizon, no daylight from outside`` |
| 室外开阔 | ``no ceiling, no walls, no enclosed space`` |
| 室外建筑环绕 | ``no isolated structure, no empty plain`` |
| 黑夜 | ``no daytime, no bright sunlight, no clear blue sky`` |
| 白天 | ``no nighttime, no neon, no artificial bright lights`` |
| 自然环境 | ``no concrete buildings, no urban infrastructure`` |
| 城市 | ``no rural, no wilderness, no isolated landscape`` |

外加 art_genre 通用项（同 character_ref）。

## reference_image_count 分配

**每个 location 最少 2 张**：

- 1 张主 angle（最具代表性的视角，下游引用最多）
- 1 张副 angle 或副 time_variant（给 frame_prompt 提供构图选择）

最多 3 张。**不要每个 time_variant 都出**——下游 frame_prompt 会按文字提示自己融合时段，参考图给"建筑骨架"就够。

## 反例

- 同一 location 拆成两个 SceneRef（"云岚宗" + "云岚宗大殿"）—— 该合并就合并
- atmosphere 写"主角在这里第一次见到反派"—— 这是情节
- time_variants 4 个以上 —— 资源浪费且模型混乱
- color_restrictions 用中文长句 —— SD 不识别
- props 漏关键道具 —— 下游镜头里宗门标志性青铜钟消失

## 工作流（强调先口头说明再调用工具）

每次准备调 ``load_skill_reference`` / ``generate_image`` / ``memory_save``：
1. 本轮先口头说意图 + 理由
2. 下一轮才调工具

例：
> "云岚宗广场是高潮决斗场，需要 2 张参考图：1 张主 angle（白天空荡的全景），1 张副 angle（决斗时的近景仰拍）。下一步我会先调 ``load_skill_reference(skill='scene-design', ref_key='environment-prompt-cookbook')`` 看一下宗门类场景的标准 prompt 模板，再回来定稿 architecture 字段。"

## reference: environment-prompt-cookbook

按场景类型给的标准 prompt 配方：

### 玄幻宗门（仙侠 / 修仙）

```
architecture: 巨型石阶 / 白玉广场 / 飞檐殿宇 / 古铜钟 / 灵气云雾
atmosphere: 庄严 / 肃杀 / 上古遗留 / 仙气缭绕
lighting: 清晨薄雾 + 顶光散射 / 黄昏霞光 / 月华笼罩
props: 青铜钟 / 古旗帜 / 门派牌匾 / 镇宗石碑
英文 tag: ancient sect courtyard, white jade plaza, towering stone steps, mountain backdrop, mystical mist
负面: no modern building, no concrete, no urban
```

### 都市街景（现代 / 都市剧）

```
architecture: 高楼大厦 / 街道 / 红绿灯 / 玻璃幕墙 / 招牌
atmosphere: 繁忙 / 冷漠 / 都市疏离 / 节奏感
lighting: 正午硬光 / 夜晚霓虹 / 黄昏街灯
props: 出租车 / 便利店招牌 / 公交站 / 路人
英文 tag: modern city street, glass skyscrapers, neon signs, urban realistic, rain-slick asphalt
负面: no rural, no wilderness, no fantasy elements
```

### 末日 / 废墟

```
architecture: 倒塌建筑 / 锈蚀金属 / 杂草丛生 / 弃车
atmosphere: 死寂 / 绝望 / 末世 / 寂寥
lighting: 暗沉灰蓝 / 偶尔斜射光柱 / 黄昏沙尘
props: 废弃汽车 / 破碎招牌 / 杂草藤蔓 / 残骸
英文 tag: post-apocalyptic ruins, abandoned cityscape, overgrown vegetation, rusted metal, debris
负面: no clean modern building, no people, no daily life
```

### 室内对话（家 / 办公室 / 咖啡厅）

```
architecture: 桌椅 / 窗 / 地板 / 墙面装饰
atmosphere: 私密 / 日常 / 温暖 / 紧绷（视情境而定）
lighting: 实用光源（台灯 / 窗户日光）+ 柔光
props: 茶杯 / 笔记本 / 装饰画 / 植物 / 抱枕
英文 tag: cozy interior, soft natural window light, wooden floor, intimate atmosphere
负面: no outdoor, no sky, no horizon
```

### 自然 / 田园

```
architecture: 山 / 河 / 树林 / 田野 / 小路
atmosphere: 宁静 / 治愈 / 自然 / 季节感
lighting: 清晨薄雾 / 正午斑驳树影 / 黄昏暖光
props: 野花 / 溪水 / 石头 / 木桥
英文 tag: lush natural landscape, dappled sunlight through leaves, peaceful atmosphere, painterly
负面: no urban, no concrete, no neon
```

### 战斗场（决斗台 / 修罗场）

```
architecture: 开阔平台 / 残骸地形 / 围观看台 / 高空场地
atmosphere: 紧张 / 杀气 / 史诗感 / 万人屏息
lighting: 戏剧性硬光 / 风沙效果 / 仰角顶光
props: 武器残骸 / 战旗 / 血迹 / 裂痕
英文 tag: dramatic battlefield, dust and debris, low-angle shot, cinematic lighting
负面: no peaceful, no warm, no ordinary daily scene
```

## reference: time-of-day-lighting-recipes

5 种核心时段的光照模板（直接拼到 prompt 里）：

### dawn（黎明）

```
柔和 backlight 从地平线来, 蓝紫色天空过渡到暖粉, 雾气未散, 主体剪影清晰
英文 tag: soft golden hour backlight, dawn mist, purple-pink sky gradient, silhouettes
适用: 决心 / 重生 / 新开始的情绪
```

### day（正午）

```
顶光强烈, 短阴影硬, 高对比, 蓝天明亮
英文 tag: harsh midday sunlight, sharp shadows, high contrast, clear blue sky
适用: 戏剧性时刻 / 揭示真相 / 公开对峙
```

### golden_hour（黄金时刻 / 日落前 1h）

```
低角度暖橙光, 长阴影, 全场镀金, 浪漫感
英文 tag: warm golden hour light, long shadows, magic hour glow, romantic atmosphere
适用: 抒情 / 离别 / 反思 / 万能选项
```

### dusk（黄昏 / 日落后）

```
紫蓝色天空, 实用光源点亮, 远景轮廓模糊, 神秘感
英文 tag: blue hour twilight, purple-blue sky, practical lights starting to glow, mysterious
适用: 转折 / 悬疑 / 剧情进入下半段
```

### night（黑夜）

```
月光冷蓝, 实用光源（街灯 / 窗光 / 火光）作主光, 阴影深邃
英文 tag: moonlit night, cool blue ambient, warm practical lights, deep shadows
适用: 阴谋 / 战斗高潮 / 内心独白 / cyberpunk 默认
```

### rain（雨景，可叠加在任意时段）

```
雨幕灰白, 地面镜面反光, 雾气朦胧, 降饱和
英文 tag: rain-soaked atmosphere, wet reflective surfaces, atmospheric fog, desaturated
适用: 悲伤 / 转折 / 净化 / noir 必备
```
