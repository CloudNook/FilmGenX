---
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

```
[Subject 主体]: 谁 / 什么。锁定角色五官 / 服装 / 物体材质（这部分主要靠参考图，文字补关键差异）
[Action 动作]:  做什么。肢体 / 表情 / 物体运动的连贯序列（强调"自然 / 缓慢 / 流畅"）
[Camera 运镜]: 镜头怎么动。用官方词汇（dolly in / pull back / orbit / pan / handheld / static…），同时指明景别
[Scene 场景]:  在哪里 + 光影。光源方向 / 行为（薄雾 / 雨 / 尘埃）/ 色调
[Style 风格]:  品质锚定 + 风格关键词（"4K, cinematic, UE5 render, no flicker"）
```

把这五段串成一句中文流畅文字（不是字段化），约 80-180 字。

## 时间戳分镜模板（4-15 秒视频）

短于 5 秒可以省略时间戳直接写一段；5 秒以上**强烈推荐用时间戳分镜**，把视频拆成 2-3 段递进的画面，模型对节奏的控制力大幅提升：

```
[5 秒, 史诗写实风格] 主角持剑站在悬崖边背身远眺，剑刃微闪寒光，山风吹起战袍下摆。
0-2 秒：static 长镜，主角剪影占画面右 1/3，远景云海翻涌。
2-4 秒：缓慢 dolly in 推进至 medium shot，主角缓慢转身，表情从平静转为 determined。
4-5 秒：停顿在主角侧脸特写，右手缓慢握紧剑柄。
光影：黄昏侧逆光，金红色调，远景薄雾扩散。
约束：no flicker, no face distortion, no extra characters, no text overlay.
```

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

例：``黄昏侧逆光（光源），远景薄雾扩散（行为），金红色调主导（色调）``

## 风格 / 品质锚定词

每条 prompt 尾部加品质锚定，比写 "电影感" 这种空词有效得多：

```
4K, cinematic, UE5 render, high detail, sharp focus, stable framing, no flicker, no blur
```

按题材换：

- 写实电影：``cinematic, anamorphic lens, film grain, Roger Deakins style``
- 动漫：``anime style, Makoto Shinkai, vibrant colors, clean lineart``
- 国风武侠：``Chinese ink painting style, mist, traditional brushwork``
- 赛博朋克：``cyberpunk neon, blade runner aesthetic, rainy night, holographic UI``

## 负面约束（防崩坏关键）

Seedance 不接受独立 negative_prompt 字段，所以负面约束**直接拼在 prompt 末尾**作为一段：

```
约束：no face distortion, no flicker, no character drift, no extra characters,
no sudden color shift, no text/subtitle/logo/watermark, no shaky cam,
no rapid scene change.
```

按场景额外加：

- 室内 → ``no outdoor sky, no daylight from outside``
- 单人镜 → ``no crowd, no background people``
- 远景 → ``no close-up face details, no extreme details``

## 与参考图配合

Seedance reference-to-video 通过 ``asset_codes`` 接受参考图：

```
generate_video(
  prompt="...",
  asset_codes=[character.主角.three_view_asset_code, scene.云岚宗广场.reference_asset_codes[0]],
  duration=8,
  aspect_ratio="16:9",
)
```

**参考图能确定的事**（服装 / 长相 / 场景结构 / 全片色调）→ **不在 prompt 里复述**。
**prompt 唯一的职责**：描述动作 + 运镜 + 节奏 + 情绪变化 + 光影变化。

参考图最多 9 张；通常 1-3 张够用：1 张主角三视图 + 1 张场景主 angle。

### Seedance 官方参考图引用语法：``@图片N``

**在 prompt 里精确指代某张参考图，用 ``@图片N``**（N = 1, 2, ..., 9）。
编号按 ``asset_codes`` 数组顺序，**1-indexed**：

| asset_codes 位置 | prompt 中的引用 |
| --- | --- |
| asset_codes[0] | ``@图片1`` |
| asset_codes[1] | ``@图片2`` |
| ... | ... |
| asset_codes[8] | ``@图片9`` |

**示例**（主角 + 场景两张参考图）：

```
generate_video(
  prompt="@图片1 持剑立于 @图片2 描绘的悬崖边背身远眺，山风吹动战袍下摆。
          0-2 秒：static long shot；2-4 秒：缓慢 dolly in 推到 medium close-up，
          @图片1 缓慢转身，表情从平静转为 determined。
          光影：黄昏侧逆光，金红色调。",
  asset_codes=["img-xiaoyan-3view", "img-yunlan-cliff"],   # ← img-xiaoyan-3view 是 @图片1
  duration=5,
  aspect_ratio="16:9",
)
```

工具会**预校验**：prompt 里 ``@图片N`` 编号必须在 ``1..len(asset_codes)`` 范围内，
越界（如只传 2 张但写 ``@图片3``）直接 fail-fast 返 ``VIDEO_PROMPT_REF_OUT_OF_RANGE``，
不会浪费配额打 Seedance。

工具返回的 ``image_refs`` 字段会回显当前映射：
``{"@图片1": "img-xiaoyan-3view", "@图片2": "img-yunlan-cliff"}``，
你可以复核 Seedance 看到的编号与你的意图是否一致。

**何时该用 ``@图片N`` vs 自然语言**：

- 多张参考图 + 需要精确指明"哪个角色做什么动作 / 哪个场景作背景" → 用 ``@图片N``
- 单张参考图，prompt 不会混淆 → 自然语言描述即可
- 参考图职责本身就含糊（如纯风格参考）→ 不用引用，让模型自行融合

### 自动别名注入：你写中文名，工具帮你桥接到 @图片N

工具会在内部反查 memory KV——如果某个 ``asset_code`` 在 ``character.<name>`` 或
``scene.<name>`` 的 KV 里出现过，**工具会自动在 prompt 头部前置一行别名表**：

```
素材引用：萧炎=@图片1，云岚宗广场=@图片2

(你写的 prompt 原文)
```

这样你 prompt 正文里直接用中文名就行（``萧炎冲向云岚宗广场``），Seedance 看到别名行后
就知道"萧炎"对应 @图片1。返回值的 ``name_refs`` 字段会回显反查到的映射，方便核对。

**两种写法可以混用**：

```
generate_video(
  prompt="萧炎在云岚宗广场中央，缓推到 @图片1 侧脸特写。光影：黄昏侧逆光。",
  asset_codes=["img-xy", "img-yl"],   # img-xy 在 character.萧炎 KV 里
  ...
)
# 实际送到 Seedance 的 prompt:
# "素材引用：萧炎=@图片1，云岚宗广场=@图片2\n\n萧炎在云岚宗广场中央，缓推到 @图片1 侧脸特写。..."
```

**反查失败的情况**：asset_code 不在 KV 里（如 workspace 调试台直接 ``generate_image`` 出
的临时图）→ ``name_refs`` 为空，工具不会前置别名行；你只能用 ``@图片N`` 显式索引。

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

每次调 ``generate_video`` 之前：

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

```
史诗写实风格，主角持剑站在悬崖边背身远眺，山风吹动战袍下摆。
0-2 秒：static 长镜，主角剪影占画面右 1/3，远景云海翻涌。
2-4 秒：缓慢 dolly in 推进至 medium shot，主角缓慢转身，
表情从平静转为 determined。
4-5 秒：停顿在主角侧脸特写，右手缓慢握紧剑柄。
光影：黄昏侧逆光，金红色调，远景薄雾扩散。
约束：4K, cinematic, UE5, no flicker, no face distortion, no text overlay.
```

### 2. 对话双人（8 秒，中景对话）

```
赛博朋克写实风，A 和 B 在霓虹雨夜街角对峙。
0-3 秒：static medium shot，OTS 视角从 A 肩头看 B，B 表情凝重缓慢说话。
3-6 秒：缓慢 pan 转到 B 的正反打，B 抬头反问，眼神锐利。
6-8 秒：crane up 升镜略仰，揭示 B 身后远处霓虹招牌。
光影：紫红色霓虹主光 + 蓝色雨夜冷调，水面反光，雨水缓慢落下。
约束：cinematic, anamorphic lens, no character drift, no extra people, no text.
```

### 3. 高潮战斗（10 秒，单人爆发）

```
史诗奇幻风，主角站在战场中央，双手凝聚异火。
0-3 秒：medium shot static，主角双手缓慢抬起，掌心红蓝双色火焰旋转融合。
3-6 秒：dolly in 缓推到 medium close-up，火焰加速旋转，主角眼神聚焦。
6-9 秒：火焰爆发瞬间——orbit 镜头快速环绕主角 1/4 圈，揭示火焰膨胀。
9-10 秒：拉远到 wide shot，火焰冲天，主角剪影。
光影：火焰自发光主导，冷蓝环境光对比，地面尘埃飞舞。
约束：UE5 render, no flicker, no rapid scene change, no text overlay,
no shaky cam, 4K detail.
```

### 4. 静谧抒情（6 秒，空镜过场）

```
日系治愈风，清晨田野，麦穗在微风中摇曳。
0-2 秒：static low angle close-up，麦穗占画面前景，远景模糊。
2-4 秒：缓慢 truck right 横移跟随风的方向。
4-6 秒：rack focus 焦点从前景麦穗虚化到远景日出。
光影：晨光侧逆光，金色高光，薄雾弥散，全片低饱和怀旧色。
约束：anime style, Makoto Shinkai aesthetic, soft focus, no flicker, no text.
```

### 5. 揭示式开场（12 秒，建立世界）

```
中国传统水墨风，悬浮的仙山远景，云雾环绕。
0-4 秒：static wide shot，仙山占画面中央，云雾从下方缓慢上升。
4-8 秒：缓慢 dolly in 推进，揭示山顶古亭轮廓。
8-12 秒：tilt down 缓慢下摇，最终落在亭中持剑的主角剪影。
光影：晨曦侧光，墨色与朱红对比，远景留白，水墨笔触可见。
约束：Chinese ink painting style, traditional brushwork, no flicker,
no character drift, stable framing, 4K.
```
