---
name: video-prompt-engineering
description: Use when translating storyboard shots into Kling-ready text-to-video prompts. Provides the four-element motion formula (camera + character action + rhythm + opening frame), Kling parameter rules (duration 5/10, aspect ratio, quality), and templates for common camera moves and action types.
target_agents: [video_prompt_agent]
tags: [video-prompt, kling, text-to-video, prompt-engineering]
author: filmgenx
---

# 视频镜头 prompt 工程

video_prompt_agent 的输出会**直接喂给视频模型**（当前 Kling，未来 Seedance）。本期是**纯文字驱动**——没有 seed image，所以 prompt 必须把"画面起手"也写清楚，不然模型自己脑补画面起点会和 frame_prompt 完全不同。

本 skill 给四要素公式、Kling 参数规则、常见运镜与动作类型模板，以及关键运动验证的工具调用流程。

## 四要素公式

每个 ``motion_description`` 必须涵盖：

```
[1. 画面起手]: 第 0 秒看到什么 (借鉴 frame_prompt.image_prompt 关键描述)
[2. 运镜]:    pan / dolly / zoom / static, 起止位置, 速度
[3. 角色动作]: 肢体 / 表情变化, 节奏分段
[4. 镜头节奏]: 时间分配 (前 X 秒做 A, 中 Y 秒做 B, 末 Z 秒做 C)
```

总长度 80-180 字。低于 80 通常运动不够清晰；高于 180 模型注意力分散。

## 完整模板

```
画面起手: 萧炎背身站立云岚宗广场中央, 玄重尺横置背后, 黄昏侧光剪影; 远景宗门殿宇模糊。
运镜: 镜头以 dolly in 缓慢推进, 起始 medium shot, 推进到 medium close-up, 停在主角侧脸位置。
角色动作: 主角缓慢转身, 表情从平静转为 determined, 右手缓慢握紧尺柄。
节奏: 前 2 秒画面静止建立氛围, 2-4 秒推镜 + 转身同步, 4-5 秒停顿在表情特写。

duration: 5 sec
aspect_ratio: 16:9
quality: hq
```

## Kling 参数规则（硬约束）

| 参数 | 允许值 | 备注 |
| --- | --- | --- |
| ``duration_seconds`` | **必须取整 5 或 10** | 其它值 Kling 直接拒绝 |
| ``aspect_ratio`` | ``16:9`` / ``9:16`` / ``1:1`` | 必须与对应 frame_prompt 一致 |
| ``quality`` | ``std`` / ``hq`` | std=720p, hq=1080p; hq 额度贵 |
| ``model_hint`` | 当前只有 ``kling`` | seedance 是占位 |

### duration 选择规则

storyboard 里每个镜头的 ``duration_seconds`` 是设计意图，**video_prompt 的 duration 是 Kling 实际生成时长**。两者不必完全一致：

| storyboard.duration_seconds | video_prompt.duration_seconds | 理由 |
| --- | --- | --- |
| 1-3 秒（快切） | 5 | Kling 最短就 5；剪辑时再裁短 |
| 4-6 秒 | 5 | 直接对齐 |
| 7-10 秒 | 10 | 长镜要求 |
| > 10 秒 | 拆分成多段 5/10 秒 | 单个镜头超过 Kling 限制 |

### quality 分配（额度有限）

短剧（60 秒）按这个比例分配：

| 镜头类型 | quality | 占比 |
| --- | --- | --- |
| 高潮 / 转场 / 情感顶点 | hq | 20-30% |
| 关键叙事 / 角色 close-up 运动 | hq | 视情况 |
| 常规过场 / 简单运镜 | std | 60-70% |

**不要全 hq**——一个 60 秒短剧 12-15 个 video shot 全 hq 会爆额度。

## 文字驱动的"画面起手"为什么关键

Kling 文字驱动模式没有 seed image，模型完全靠 prompt 起步。如果你的 motion_description 直接写"萧炎转身"——模型不知道萧炎长什么样、站在哪里、什么角度。

正确做法：**前 2-3 句必须复述 frame_prompt.image_prompt 的关键内容**：

```
画面起手: {frame_prompt 的构图 + 角色描述 + 场景描述 + 光影},  ← 这一段是"种子"
然后镜头 ...                                                   ← 这一段是"运动"
角色 ...
节奏 ...
```

下游 frame_prompt 已经为这个 shot 设计好了首帧 prompt，你**直接借用核心描述**作为画面起手，不要重新发明。

## 常见运镜模板

### static（静止 / 标准对话）

```
镜头静止保持 medium shot 不动, 不推不拉不摇.
适用: 对话戏, 仪式感, 抒情戏长镜.
```

### pan（横摇 / 跟随）

```
镜头以中速 pan {左→右 / 右→左}, 跟随主体平移, 揭示空间.
适用: 揭示场景, 角色行走, 空间过渡.
```

### tilt（俯仰摇）

```
镜头以缓慢 tilt {上→下 / 下→上}, 揭示高度差.
适用: 展现建筑高度, 权力关系仰拍, 揭示天空 / 地面.
```

### dolly_in（推进）

```
镜头以中速 dolly in 推进, 从 long shot 推到 medium close-up, 介入角色情绪.
适用: 情绪升级, 决心时刻, 揭示真相前的预备.
```

### dolly_out（拉远）

```
镜头以缓慢 dolly out 拉远, 从 close-up 拉到 long shot, 角色逐渐渺小.
适用: 离别, 揭示孤立, 结尾场景.
```

### whip_pan（急摇）

```
镜头以极快 whip pan 切换, 用动作模糊连接两个画面.
适用: 转场, 时空跳跃, 动作戏过渡.
```

### handheld（手持）

```
镜头以手持轻微抖动跟随主体, 真实感, 紧张感.
适用: 紧张戏, 第一人称感, 现实主义.
```

### crane（升降）

```
镜头从低位 crane up 升起, 揭示全景或转换视角.
适用: 开场, 结尾, 仪式感时刻.
```

### zoom_in（变焦推近）

```
镜头 zoom in (不是物理移动), 突出心理变化或细节.
适用: 心理戏, 特定道具特写, 复古电视感.
注意: 慎用. 现代电影感少用.
```

## 常见角色动作模板

### 战斗动作

```
主角举武器, 蓄力 1 秒, 挥下时武器尾随光迹, 击中目标产生粒子爆发.
英文 tag: character raises weapon, charges energy 1 sec, swings down with motion blur trail, particle explosion on impact
```

### 释放招式 / 异能

```
主角双手聚气, 手心光球渐大, 双色异火融合, 释放冲击波.
英文 tag: character channels energy, palm glows brighter, two-color flames merge, releases shockwave
```

### 转身 / 揭示表情

```
主角缓慢转身, 头先转, 身体跟随, 表情从平静过渡到 determined, 视线锁定.
英文 tag: character slowly turns around, head first, body follows, expression transitions from calm to determined, locked gaze
```

### 行走 / 离开

```
主角缓慢迈步前进, 步速节奏稳定, 长袍 / 头发飘动.
英文 tag: character walks forward at steady pace, robes / hair flowing, determined posture
```

### 摔倒 / 受击

```
主角被击中, 身体后仰, 武器脱手飞出, 着地腾起尘土.
英文 tag: character takes hit, body recoils backward, weapon flies out of grip, dust kicks up on impact
```

### 抒情 / 静默

```
主角静止, 仅风吹动头发 / 衣物, 眼神缓慢眨动, 微表情变化.
英文 tag: character stands still, hair / clothes drift in wind, slow blink, subtle facial micro-expression shift
```

## 反例

- motion_description 写"角色移动"——通用描述, 模型乱画
- duration_seconds 取 7（不是 5/10）——Kling 拒绝
- aspect_ratio 与 frame_prompt 不一致——画面拉伸
- 漏写画面起手——文字驱动模式下模型完全靠 prompt 起步
- 全部 quality=hq——额度爆掉
- 把 frame_prompt 的整段 image_prompt 完整复制——重复信息, 浪费 prompt 长度

## 工作流（强调先口头说明再调用工具）

每次准备调 ``load_skill_reference`` / ``generate_video``：
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

```
0-1秒: 静止建立 (起手画面)
1-3秒: 主动作执行 (挥武器 / 释放招式 / 转身)
3-5秒: 余波 + 表情 (击中后烟尘 / 表情切换 / 武器停顿)
```

### 5 秒抒情型（情绪戏）

```
0-2秒: 静止微动 (风吹头发 / 缓慢眨眼)
2-4秒: 表情过渡 (平静→悲伤 / 决心→释然)
4-5秒: 微表情定格 (眼角泪光 / 嘴角微扬)
```

### 5 秒推镜型（情绪升级）

```
0-1秒: long shot 静止
1-4秒: 缓慢 dolly in 到 medium close-up
4-5秒: 停在 close-up 的表情
```

### 10 秒长镜型（仪式感）

```
0-2秒: 起手画面建立
2-4秒: 角色动作起步
4-6秒: 主动作展开 (招式 / 对峙 / 行走)
6-8秒: 高潮点 (击中 / 决断 / 揭示)
8-10秒: 收尾 (余波 / 镜头停顿 / 转场预备)
```

### 10 秒揭示型（开场 / 结尾）

```
0-2秒: 局部细节特写
2-5秒: crane / zoom out 揭示更大场景
5-8秒: 角色出现 / 走入画面
8-10秒: 全景定格
```
