---
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
