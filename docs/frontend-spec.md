# FilmGenX 前端规格文档

> 给 Gemini 的完整前端构建指南  
> 版本：v2.0 | 日期：2026-04-04

---

## 一、核心理念：人机协作的分集动画生产系统

FilmGenX 不是全自动流水线，也不是纯手工工具。**核心价值在于每个阶段的中间状态完整保留，人可以在任意节点介入查看、编辑、微调，然后重新触发后续流程。**

### 1.1 每集动画的完整生命周期

```
[对话选段] ──→ [AI总结确认] ──→ [锁定本集内容] ──→ [生成分镜] ──→ [微调分镜] ──→ [生成图像] ──→ [生成视频]
     ↑                ↑                                    ↑              ↑               ↑
  人工介入          人工确认                             人工介入        人工微调         人工选图
  随时修改          才能推进                             可重新生成      重新生成视频      重新生成
```

每个箭头之间的状态都**持久化到数据库**，页面随时可以回到任意节点继续操作。

### 1.2 一个 Scene = 一集动画

- **Project**（项目）= 一部小说（如《斗破苍穹》）
- **Scene**（场景/分集）= 一集动画，有完整的从选段到视频的生产记录
- 每个 Scene 有唯一的 `scene_code`（如 `DQCK_EP01`）
- Scene 的生产状态机：`draft` → `confirmed` → `in_production` → `completed`

### 1.3 人工介入节点

| 阶段 | AI 做什么 | 人可以做什么 |
|------|-----------|-------------|
| 选段对话 | 分析小说，推荐高光片段 | 追问、修正、补充信息 |
| **总结确认** | 将对话总结为结构化的分集内容 | **审阅、编辑所有字段，确认后才能进入下一步** |
| 分镜生成 | 自动生成全部镜头的分镜脚本 | 编辑任意镜头，拖拽排序，手动增删镜头 |
| 图像生成 | 按 image_prompt 生成参考图 | 修改 prompt 重新生成，多选一 |
| 视频生成 | 按图像+参数生成视频片段 | 调整参数，不满意重新生成 |

---

## 二、数据模型（前端视角）

### 2.1 Scene 完整数据结构

```typescript
interface Scene {
  // 基础信息
  id: number
  scene_code: string            // "DQCK_EP01"
  title: string                 // "萧炎逆袭大会"
  project_id: number

  // 原著定位
  novel_chapter_start: number
  novel_chapter_end: number
  novel_excerpt: string         // 核心原著摘录（可长文本）

  // 分集定义（AI总结后确认的内容）
  episode_synopsis: string      // 本集剧情概述（100-300字）
  episode_theme: string         // 本集核心主题，如"逆袭与证明自我"
  scene_types: string[]         // ['battle_highlight', 'emotional_peak']
  character_ids: number[]       // 本集出场角色
  estimated_duration_sec: number

  // 优先级与评分
  priority: 'S' | 'A' | 'B' | 'C'
  score_dramatic_tension: number      // 0-10
  score_visual_potential: number
  score_emotional_resonance: number
  score_narrative_importance: number
  score_audience_familiarity: number
  score_total: number

  // 生产状态
  status: 'draft' | 'confirmed' | 'in_production' | 'completed'

  // 选段对话记录（关键：保存完整对话）
  selection_chat_id: string | null    // 关联的对话会话 ID

  created_at: string
  updated_at: string
}
```

### 2.2 ChatSession（对话会话）

选段对话的完整记录持久化到后端，而非只存 localStorage。

```typescript
interface ChatSession {
  id: string                    // UUID
  project_id: number
  scene_id: number | null       // 对话结束并确认后，关联到 Scene
  title: string                 // 自动生成，如"第01集选段对话 - 2026-04-04"
  messages: ChatMessage[]
  status: 'active' | 'summarized' | 'confirmed'
  summary: SceneSummary | null  // AI总结结果
  llm_config_snapshot: object   // 使用的LLM配置快照（历史可查）
  created_at: string
  updated_at: string
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string               // Markdown 格式
  timestamp: string
  // 若此消息包含片段建议
  scene_suggestions?: SceneSuggestion[]
}

interface SceneSuggestion {
  title: string
  chapter_start: number
  chapter_end: number
  novel_excerpt: string
  episode_synopsis: string
  episode_theme: string
  scene_types: string[]
  scores: {
    dramatic_tension: number
    visual_potential: number
    emotional_resonance: number
    narrative_importance: number
    audience_familiarity: number
  }
  priority: 'S' | 'A' | 'B' | 'C'
  estimated_duration_sec: number
  recommended_characters: string[]   // 角色名列表
}
```

### 2.3 SceneSummary（AI总结结果，用于人工确认）

```typescript
interface SceneSummary {
  // AI从对话中提取的结构化内容
  title: string
  episode_synopsis: string          // 本集概述
  episode_theme: string
  novel_chapter_start: number
  novel_chapter_end: number
  novel_excerpt: string             // AI推荐的核心摘录段落
  scene_types: string[]
  priority: 'S' | 'A' | 'B' | 'C'
  estimated_duration_sec: number
  scores: {
    dramatic_tension: number
    visual_potential: number
    emotional_resonance: number
    narrative_importance: number
    audience_familiarity: number
  }
  recommended_characters: string[]  // 角色名（需人工对应到 character_id）
  storyboard_style_notes: string    // AI建议的分镜风格备注（传给下一步）
  // 元信息
  generated_from_message_count: number
  generated_at: string
}
```

---

## 三、后端 API 说明

Base URL: `http://localhost:8000/api/v1`

所有请求需携带 `Authorization: Bearer <token>` Header。

### 3.1 认证

```
POST /auth/login    { email, password } → { access_token, token_type }
POST /auth/register { email, username, password }
```

### 3.2 项目（Project）

```
GET    /projects                    列表（分页）
POST   /projects                    创建
GET    /projects/{id}               详情
PATCH  /projects/{id}               更新
DELETE /projects/{id}               删除
```

Project 字段：`id, name, description, novel_title, cover_image_url, status(active|archived)`

### 3.3 场景/分集（Scene）

```
GET    /projects/{project_id}/scenes              列表（按 status、priority 过滤）
POST   /projects/{project_id}/scenes              创建（草稿）
GET    /projects/{project_id}/scenes/{id}         详情
PATCH  /projects/{project_id}/scenes/{id}         更新（包括人工确认后的全字段更新）
DELETE /projects/{project_id}/scenes/{id}         删除
POST   /projects/{project_id}/scenes/{id}/confirm 确认本集内容，状态变为 confirmed
```

### 3.4 对话会话（ChatSession）——需新增

```
GET    /projects/{project_id}/chat-sessions              列表
POST   /projects/{project_id}/chat-sessions              创建新会话
GET    /projects/{project_id}/chat-sessions/{id}         详情（含完整消息列表）
PATCH  /projects/{project_id}/chat-sessions/{id}         更新（保存消息、更新状态）
POST   /projects/{project_id}/chat-sessions/{id}/summarize   触发AI总结
POST   /projects/{project_id}/chat-sessions/{id}/confirm     确认总结，创建Scene记录
```

**注意**：对话消息通过 PATCH 接口批量保存，不需要每条消息单独请求。前端维护消息列表，在适当时机（会话结束、触发总结前）整体保存。

### 3.5 分镜脚本（Storyboard）

```
GET    /scenes/{scene_id}/storyboard   获取（一对一）
POST   /scenes/{scene_id}/storyboard   手动创建空白分镜
PATCH  /scenes/{scene_id}/storyboard   更新分镜元信息
```

### 3.6 镜头（Shot）

```
GET    /storyboards/{sb_id}/shots          列表（有序）
POST   /storyboards/{sb_id}/shots          创建单个镜头
GET    /storyboards/{sb_id}/shots/{id}     详情
PATCH  /storyboards/{sb_id}/shots/{id}     更新（人工微调关键入口）
DELETE /storyboards/{sb_id}/shots/{id}     删除
PATCH  /storyboards/{sb_id}/shots/reorder  批量更新 sequence（拖拽排序）
```

### 3.7 角色（Character）

```
GET    /projects/{project_id}/characters
POST   /projects/{project_id}/characters
GET    /projects/{project_id}/characters/{id}    （含版本列表）
PATCH  /projects/{project_id}/characters/{id}
DELETE /projects/{project_id}/characters/{id}

GET/POST/PATCH/DELETE  /projects/{project_id}/characters/{id}/versions/{vid}
```

### 3.8 AI 任务（GenerationTask）

```
POST /tasks/storyboard    触发分镜生成
  Body: {
    scene_id,
    shot_count,
    style_notes,
    llm_config: { provider, model, api_key, temperature },
    system_prompt           // 可被用户临时修改的系统提示词
  }

POST /tasks/video         触发视频生成
  Body: { shot_id, quality, sound, use_image_start }

GET  /tasks/{task_id}     轮询任务状态
  Response: { status, progress, error_message, result_asset_id }
```

---

## 四、核心设计需求：配置驱动

### 4.1 LLM 配置（存储在 localStorage）

```typescript
interface LLMConfig {
  id: string
  name: string
  provider: 'google' | 'openai' | 'anthropic' | 'custom'
  model: string
  api_key: string               // btoa 混淆存储
  base_url?: string
  temperature?: number          // 0-2，默认 0.7
  max_tokens?: number
  is_default: boolean
}
```

### 4.2 提示词模板（存储在 localStorage）

```typescript
interface PromptTemplate {
  id: string
  name: string
  workflow: 'scene_selection' | 'scene_summary' | 'storyboard' | 'video_prompt'
  system_prompt: string
  user_prompt_template: string   // 支持 {{variable}} 插值
  variables: string[]
  llm_config_id: string
  project_id?: string            // null = 全局
  created_at: string
  updated_at: string
}
```

**四种 workflow 说明：**
- `scene_selection`：选段对话阶段使用，多轮对话
- `scene_summary`：**对话结束后，触发AI总结**，将全部对话提炼为结构化 SceneSummary
- `storyboard`：分镜生成阶段，传给后端 Celery 任务
- `video_prompt`：图像/视频生成时优化 prompt

---

## 五、三大工作流 UI 详细设计

### 5.1 工作流一：AI 对话选段 + 总结确认

**这是整个流程的起点，对话内容完整保存，最终由 AI 总结后人工确认，才进入下一步。**

#### 5.1.1 对话选段页面

**路由**: `/projects/:projectId/scene-selection`

**功能**：查看所有已有的对话会话列表，以及新建会话的入口。

```
┌────────────────────────────────────────────────────────┐
│  《斗破苍穹》/ 选段工作台                  [+ 新建会话] │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ ● 第01集选段对话          2026-04-04   [已确认] │  │
│  │   萧炎逆袭大会 · 第38-45章             → EP01   │  │
│  │                            [查看对话] [查看分集] │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ ● 第02集选段对话          2026-04-05   [待确认] │  │
│  │   药老现身 · 第46-58章                          │  │
│  │                            [继续对话] [查看总结] │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ ○ 草稿                    2026-04-06   [进行中] │  │
│  │   尚未总结                                      │  │
│  │                                    [继续对话]   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
└────────────────────────────────────────────────────────┘
```

#### 5.1.2 对话页面

**路由**: `/projects/:projectId/chat-sessions/:sessionId`

```
┌──────────────────────────────────────────────────────────────────┐
│  第02集选段对话                          [保存] [触发AI总结 ▶]   │
├─────────────────────────────┬────────────────────────────────────┤
│                             │                                     │
│   对话面板  (左 65%)        │   本次建议列表  (右 35%)            │
│                             │                                     │
│  ┌───────────────────────┐  │  待采纳建议（来自AI回复）           │
│  │ 🤖 AI                 │  │                                     │
│  │ 根据第46-58章，我找到  │  │  ┌─────────────────────────────┐  │
│  │ 以下高光片段：         │  │  │ 药老出现                     │  │
│  │                       │  │  │ 章节：46-52 | 评分: ★★★★★  │  │
│  │  ┌─────────────────┐  │  │  │ 视觉★5 情感★4 冲突★5       │  │
│  │  │ [片段建议卡片]  │  │  │  │ 预计时长：90秒              │  │
│  │  │ 药老出现        │  │  │  │ [采纳] [忽略]               │  │
│  │  │ 第46-52章  ★★★ │  │  │  └─────────────────────────────┘  │
│  │  │ [采纳] [详情]  │  │  │                                     │
│  │  └─────────────────┘  │  │  已采纳（将进入AI总结）            │
│  │                       │  │  ┌─────────────────────────────┐  │
│  │ 🧑 用户               │  │  │ ✓ 药老出现  [移除]           │  │
│  │ 重点突出药老初次       │  │  └─────────────────────────────┘  │
│  │ 展示斗技的场景         │  │                                     │
│  │                       │  │  ─────────────────────────────     │
│  │ 🤖 AI                 │  │                                     │
│  │ 好的，我来分析...     │  │  LLM 配置                          │
│  └───────────────────────┘  │  [Gemini Flash ▼]                  │
│                             │  提示词模板                         │
│  ┌─────────────────────┐    │  [选段对话 v1.2 ▼]                 │
│  │ 小说上下文注入      │    │                                     │
│  │ [粘贴章节文本...]   │    │  [预设引导语 ▼]                    │
│  └─────────────────────┘    │                                     │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │ 输入消息...                                        [发送]│     │
│  └─────────────────────────────────────────────────────────┘     │
└─────────────────────────────┴────────────────────────────────────┘
```

**功能细节：**

- 对话历史实时保存（每次发送消息后自动 PATCH 到后端）
- AI 回复自动检测 JSON 片段建议格式，渲染为卡片
- [采纳] → 移入右侧"已采纳"列表，等待触发总结
- [预设引导语] 下拉菜单：常用引导语一键发送
  - "请分析第X-X章，找出最适合动画化的战斗高光片段"
  - "请评估以上片段的视觉化难度"
  - "请帮我确定本集的核心情感弧线"
- 小说上下文注入：粘贴原著文本后，拼入 system prompt 末尾
- [保存] 按钮：强制保存当前对话状态

#### 5.1.3 触发 AI 总结

点击 [触发AI总结 ▶] 后：

1. 选择使用的 `scene_summary` 提示词模板
2. 显示预览弹窗：
   - 将要发送给AI的完整 prompt（含全部对话历史 + 已采纳建议 + 总结指令）
   - [确认发送]
3. 调用 LLM（前端直接调，不经后端），将整个对话 + 采纳建议总结为 `SceneSummary` JSON
4. 总结结果保存到 ChatSession，状态变为 `summarized`
5. 跳转到**总结确认页**

**AI 总结的 System Prompt 模板示例（用户可在设置中自定义）：**
```
你是一名动漫制片总监助手，负责将选段对话内容整理为结构化的分集制作方案。

请根据以下对话内容和已采纳的片段建议，输出一个 JSON 格式的分集内容总结。
要求：
1. episode_synopsis: 100-300字的本集剧情概述
2. episode_theme: 一句话概括本集核心主题
3. novel_excerpt: 从原著中选取最核心的1-3段摘录（用于后续分镜参考）
4. 五维评分: 综合对话讨论给出最终评分
5. storyboard_style_notes: 给分镜导演的风格指导建议
6. recommended_characters: 本集出场的主要角色名列表

输出纯 JSON，不要额外说明。
```

#### 5.1.4 总结确认页

**路由**: `/projects/:projectId/chat-sessions/:sessionId/summary`

**这是整个流程的关键决策节点。人工审阅并编辑 AI 总结，确认后才能进入分镜流程。**

```
┌─────────────────────────────────────────────────────────────────┐
│  AI 总结结果 — 第02集                  [重新总结] [确认并创建 ▶] │
├──────────────────────────────────────────────────────────────────┤
│  ⚠ 请仔细审阅以下内容，确认后将创建分集记录，并可进入分镜流程     │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  分集标识                                                         │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 分集编号  [DQCK_EP02      ] （自动生成，可修改）            │  │
│  │ 标题      [药老现身 · 灵魂之约                           ]  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  剧情内容                                                         │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 本集概述（可直接编辑）                                      │  │
│  │ 萧炎在绝境中意外激活祖传戒指，神秘药老现身。两人建立灵魂    │  │
│  │ 契约，药老承诺帮助萧炎恢复实力。本集核心是希望的重燃与      │  │
│  │ 师徒情谊的建立...                                          │  │
│  └────────────────────────────────────────────────────────────┘  │
│  核心主题  [逆境中的转机与师徒羁绊的建立                      ]  │
│                                                                   │
│  章节范围  [第 46 章] 至 [第 58 章]                               │
│                                                                   │
│  原著摘录（核心段落，用于分镜参考）                               │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ "戒指微微震颤，一道苍老的声音在萧炎耳边响起..."             │  │
│  │ [可编辑，支持多段摘录]                                      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  优先级与评分                                                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 优先级: [S ▼]   预计时长: [120] 秒                         │  │
│  │                                                             │  │
│  │ 戏剧张力  ██████████ 9    视觉潜力  █████████░ 8           │  │
│  │ 情感共鸣  ████████░░ 8    叙事重要  ██████████ 9           │  │
│  │ 观众熟悉  █████████░ 8                                     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  场景类型  ☑ emotional_peak  ☑ character_introduction  ☐ ...    │
│                                                                   │
│  本集角色（关联到角色库）                                         │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ AI建议: 萧炎、药老、萧薰儿                                  │  │
│  │ 关联角色: [萧炎(CHAR_001) ×] [药老(CHAR_002) ×] [+ 添加]  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  分镜风格备注（将传递给分镜生成AI）                               │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 整体色调偏暗，以冷蓝色为主基调。药老出现时可用金色粒子      │  │
│  │ 特效。镜头切换以慢推为主，营造神秘感...                     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  [← 返回对话]                    [重新总结] [确认并创建分集 ▶]   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**确认后的操作：**
1. 调用 `POST /projects/{id}/scenes` 创建 Scene 记录（使用确认后的数据）
2. 调用 `PATCH /chat-sessions/{id}` 将 scene_id 关联到会话，状态变为 `confirmed`
3. 页面跳转到**分集详情页**（Scene 详情，状态为 `confirmed`，显示"开始制作分镜"按钮）

---

### 5.2 工作流二：分镜生成与微调

**路由**: `/projects/:projectId/scenes/:sceneId/storyboard`

**核心理念：AI生成只是起点，每个镜头都可以独立编辑，修改后可以只重新生成该镜头的图像，不影响其他镜头。**

#### 页面布局

```
┌────────────────────────────────────────────────────────────────┐
│ [← 分集] 药老现身 DQCK_EP02  状态: in_production  [全局操作▼] │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  情感曲线图（折叠，可展开）  ▼                                  │
│                                                                 │
├──────────────────┬──────────────────────────────────────────────┤
│                  │                                              │
│  生成配置面板    │   分镜时间轴                                 │
│  (左 28%)        │   (右 72%)                                   │
│                  │                                              │
│  LLM配置         │  ← 拖拽可排序 →                             │
│  [Gemini Flash▼] │                                              │
│                  │  ┌──────────────────────────────────────┐   │
│  提示词模板      │  │ #1 DQCK_EP02_S001  3.0s  [draft]     │   │
│  [分镜导演v2 ▼] │  │ LS 低角度 | 推镜头                   │   │
│                  │  │ 萧炎独坐废墟，握紧戒指               │   │
│  系统提示词      │  │ ┌────────┐  image prompt:            │   │
│  ┌────────────┐  │  │ │  占位  │  xiao yan sitting in...   │   │
│  │ 你是一名专 │  │  │ │  图像  │                           │   │
│  │ 业分镜导演 │  │  │ └────────┘  [编辑] [生成图] [删除]   │   │
│  │ ...（可编辑)│  │  └──────────────────────────────────────┘   │
│  └────────────┘  │                                              │
│                  │  ┌──────────────────────────────────────┐   │
│  镜头数量        │  │ #2 DQCK_EP02_S002  2.5s  [approved]  │   │
│  [8 ────────]    │  │ CU 平视 | 静止                       │   │
│                  │  │ 药老从戒指中缓缓现身                  │   │
│  风格备注        │  │ ┌────────┐  ✓ 已生成图像              │   │
│  ┌────────────┐  │  │ │  缩略图 │  [编辑] [重新生成] [删除] │   │
│  │ AI建议风格 │  │  │ └────────┘                           │   │
│  │ 整体色调偏 │  │  └──────────────────────────────────────┘   │
│  │ 暗...      │  │                                              │
│  └────────────┘  │  ┌──────────────────────────────────────┐   │
│                  │  │ [+ 手动添加镜头]                      │   │
│  [触发AI生成▶]   │  └──────────────────────────────────────┘   │
│                  │                                              │
└──────────────────┴──────────────────────────────────────────────┘
```

#### 功能细节

**分镜已存在时的操作选项（全局操作下拉）：**
- [重新生成全部] → 确认后覆盖所有镜头（危险操作，需二次确认）
- [在现有基础上追加] → AI在现有镜头后继续生成
- [批量生成图像] → 对所有 draft 状态镜头批量触发图像生成
- [导出分镜PDF] → 生成可打印的分镜表

**镜头卡片操作：**
- [编辑] → 展开完整编辑表单（见下方）
- [生成图] / [重新生成] → 触发该镜头的图像生成任务
- 拖拽手柄 → 调整镜头顺序（实时调用 reorder API）

#### 镜头编辑表单（侧滑抽屉）

```
┌──────────────────────────────────────────────────┐
│  镜头 #2 DQCK_EP02_S002          [保存] [×关闭]  │
├──────────────────────────────────────────────────┤
│                                                   │
│  基础信息                                         │
│  镜头编号  [DQCK_EP02_S002]  时长 [2.5] 秒       │
│                                                   │
│  相机参数                                         │
│  景别  [CU 特写 ▼]  角度  [平视 ▼]  运动 [静止 ▼] │
│  焦距  [85mm 中长焦]  景深 [浅景深，背景虚化]     │
│                                                   │
│  构图                                             │
│  主体位置  [画面右三分之一处]                     │
│  前景  [无]  背景  [戒指内部空间，金光萦绕]       │
│                                                   │
│  角色                                             │
│  角色  [药老 ▼]  版本  [初始版 ▼]                │
│  动作  [从戒指中缓缓现身，衣袍飘动]               │
│  表情  [威严慈祥]  情感强度 [7]                   │
│                                                   │
│  对白                                             │
│  [     ] 有对白                                   │
│  台词  [小家伙，你终于找到我了...]                │
│  口吻  [低沉、略带感慨]                           │
│                                                   │
│  图像生成提示词                                   │
│  ┌──────────────────────────────────────────────┐ │
│  │ yao lao emerging from ring, mystical golden  │ │
│  │ particles, ancient sage, white hair, anime   │ │
│  │ style, close up shot, ethereal atmosphere    │ │
│  └──────────────────────────────────────────────┘ │
│  负面提示词  [blurry, low quality, watermark]     │
│                                                   │
│  转场                                             │
│  入场  [fade_in ▼]   出场  [cut ▼]               │
│                                                   │
│  已生成图像                                       │
│  ┌────┐ ┌────┐ ┌────┐                            │
│  │ ★  │ │    │ │    │  [+ 生成更多]              │
│  └────┘ └────┘ └────┘                            │
│  ★ = 当前主图（用于视频生成）                     │
│                                                   │
│  [保存修改]  [保存并重新生成图像]                 │
│                                                   │
└──────────────────────────────────────────────────┘
```

---

### 5.3 工作流三：视频制作

**路由**: `/projects/:projectId/scenes/:sceneId/production`

**核心理念：每个镜头独立可控，不满意随时重新生成，历史版本保留可回溯。**

```
┌──────────────────────────────────────────────────────────────────┐
│ [← 分镜] 药老现身 DQCK_EP02 - 视频制作                   [导出] │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  镜头总览（横向时间轴，可滚动）                                   │
│  总时长: 24.5s                                                   │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐         │
│  │S001  │ │S002  │ │S003  │ │S004  │ │S005  │ │S006  │  ...     │
│  │3.0s  │ │2.5s  │ │3.5s  │ │4.0s  │ │3.0s  │ │2.5s  │         │
│  │[图]  │ │[图]✓ │ │[图]  │ │[视]✓ │ │[图]  │ │[草]  │         │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘         │
│  图=已生图  视=已生视频  草=草稿   ✓=已批准                       │
│                                                                  │
├─────────────────────────┬────────────────────────────────────────┤
│                         │                                        │
│   当前镜头: #2 S002     │   生成记录                             │
│   (左 50%)              │   (右 50%)                             │
│                         │                                        │
│   2.5秒 | CU 平视静止   │  [图像记录] [视频记录]                 │
│                         │                                        │
│   当前主图:             │  图像记录:                             │
│   ┌──────────────────┐  │  ┌─────────────────────────────────┐  │
│   │                  │  │  │ v3 ★主图   2026-04-05 14:32    │  │
│   │   药老现身图像   │  │  │ [预览图]  [设为主图] [删除]      │  │
│   │                  │  │  ├─────────────────────────────────┤  │
│   └──────────────────┘  │  │ v2        2026-04-05 14:20    │  │
│                         │  │ [预览图]  [设为主图] [删除]      │  │
│   Image Prompt:         │  ├─────────────────────────────────┤  │
│   ┌──────────────────┐  │  │ v1        2026-04-05 14:05    │  │
│   │ yao lao emerging │  │  │ [预览图]  [设为主图] [删除]      │  │
│   │ from ring...     │  │  └─────────────────────────────────┘  │
│   └──────────────────┘  │                                        │
│   [修改后重新生成图像]  │  [+ 生成新图像]                        │
│                         │                                        │
│   当前视频:             │  视频记录:                             │
│   [无视频，尚未生成]    │  ┌─────────────────────────────────┐  │
│                         │  │ （暂无视频）                     │  │
│   生成参数:             │  └─────────────────────────────────┘  │
│   质量 [1080p ▼]        │                                        │
│   音效 [开启 ▼]         │  [生成视频 ▶]                          │
│   起始帧锁定 [✓]        │  将使用当前主图作为起始帧              │
│                         │                                        │
└─────────────────────────┴────────────────────────────────────────┘
```

---

## 六、分集详情页（Scene 详情，流程总控）

**路由**: `/projects/:projectId/scenes/:sceneId`

**这个页面是一集动画的"控制台"，展示整集的生产状态，所有工作流都从这里出发。**

```
┌──────────────────────────────────────────────────────────────────┐
│  DQCK_EP02  药老现身 · 灵魂之约             状态: in_production  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  本集概述                                                 │   │
│  │  萧炎在绝境中意外激活祖传戒指，神秘药老现身...           │   │
│  │  章节: 46-58  |  优先级: S  |  预计时长: 120s            │   │
│  │  主题: 逆境中的转机与师徒羁绊的建立                      │   │
│  │                                [查看对话记录] [编辑信息]  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  生产进度                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                                                           │   │
│  │  ① 选段对话  ✓ 已确认    [查看对话]                      │   │
│  │                  ↓                                        │   │
│  │  ② 分镜脚本  ⟳ 进行中    [进入分镜工作台]               │   │
│  │     8个镜头 | 已审核: 3/8 | 待生成图像: 5               │   │
│  │                  ↓                                        │   │
│  │  ③ 图像生成  ○ 待开始    [批量生成图像]                  │   │
│  │                  ↓                                        │   │
│  │  ④ 视频合成  ○ 待开始    [进入视频制作]                  │   │
│  │                                                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  出场角色                                                        │
│  [萧炎] [药老] [萧薰儿]                                          │
│                                                                  │
│  最近任务记录                                                    │
│  ● 分镜生成  成功  2026-04-04 15:30  8个镜头                    │
│  ● 图像生成 S001  进行中...                                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 七、全局配置中心

**路由**: `/settings`

### 7.1 LLM 配置管理

（参见第四章数据结构）

新建/编辑表单字段：
- 配置名称（必填）
- Provider（Google / OpenAI / Anthropic / 自定义）
- Model 名称（自由输入）
- API Key（password 输入）
- Base URL（自定义 provider 时显示）
- Temperature 滑块（0-2）
- Max Tokens（可选）
- [测试连接] → 发送 "hello" 验证 key 有效性
- [设为默认] checkbox

### 7.2 提示词模板管理

按工作流分组展示，每个模板显示名称、绑定模型、变量列表。

新建/编辑表单：
- 模板名称
- 工作流类型：`scene_selection` / `scene_summary` / `storyboard` / `video_prompt`
- 绑定 LLM 配置
- 适用项目（可选，null=全局）
- System Prompt（大文本框）
- User Prompt Template（大文本框，支持 `{{variable}}` 高亮）
- 变量自动解析展示
- [保存] [另存为新版本]

---

## 八、项目与角色管理

### 8.1 项目列表 `/projects`

卡片网格，显示封面、名称、小说名、分集数/完成度进度条。

### 8.2 项目工作台 `/projects/:projectId`

Tabs：[分集列表] [角色管理] [素材库] [项目设置]

**分集列表 Tab：**
- 所有 Scene 卡片，按状态分组（制作中 / 已完成 / 草稿）
- 每个卡片显示：编号、标题、状态、分镜进度、视频进度
- [+ 新建分集对话] 按钮

### 8.3 角色管理 `/projects/:projectId/characters`

角色列表 → 点击进入角色详情，含版本时间线。

---

## 九、路由总览

```
/                                                    → 重定向 /projects
/login                                               → 登录
/register                                            → 注册
/projects                                            → 项目列表
/projects/:projectId                                 → 项目工作台（分集列表）
/projects/:projectId/scene-selection                 → 选段会话列表
/projects/:projectId/chat-sessions/:sessionId        → 对话页面（工作流一）
/projects/:projectId/chat-sessions/:sessionId/summary → 总结确认页（关键节点）
/projects/:projectId/scenes/:sceneId                 → 分集详情（流程总控）
/projects/:projectId/scenes/:sceneId/storyboard      → 分镜工作台（工作流二）
/projects/:projectId/scenes/:sceneId/production      → 视频制作（工作流三）
/projects/:projectId/characters                      → 角色列表
/projects/:projectId/characters/:charId              → 角色详情
/projects/:projectId/assets                          → 素材库
/settings                                            → 全局配置（LLM + 提示词）
```

---

## 十、Pinia Store 结构

```typescript
// stores/auth.ts
authStore {
  user: User | null
  token: string | null
  login(email, password): Promise<void>
  logout(): void
}

// stores/project.ts
projectStore {
  projects: Project[]
  currentProject: Project | null
  fetchProjects(): Promise<void>
  fetchProject(id): Promise<void>
}

// stores/scene.ts
sceneStore {
  scenes: Scene[]
  currentScene: Scene | null
  fetchScenes(projectId): Promise<void>
  fetchScene(id): Promise<void>
  confirmScene(id): Promise<void>         // 触发确认，推进状态机
}

// stores/chat.ts
chatStore {
  sessions: ChatSession[]
  currentSession: ChatSession | null
  messages: ChatMessage[]                 // 当前会话的消息（含未保存的）
  isDirty: boolean                        // 有未保存的消息
  fetchSessions(projectId): Promise<void>
  fetchSession(id): Promise<void>
  sendMessage(content): Promise<void>     // 调LLM → 追加消息 → 自动保存
  saveSession(): Promise<void>            // 强制保存
  triggerSummary(templateId): Promise<SceneSummary>
  confirmSummary(summary, edits): Promise<Scene>  // 确认后创建Scene
}

// stores/storyboard.ts
storyboardStore {
  storyboard: Storyboard | null
  shots: Shot[]
  generatingTaskId: string | null
  fetchStoryboard(sceneId): Promise<void>
  triggerGeneration(params): Promise<void>
  pollTask(taskId): Promise<void>
  updateShot(id, data): Promise<void>      // 人工微调
  reorderShots(orderedIds): Promise<void>  // 拖拽排序
}

// stores/production.ts
productionStore {
  currentShot: Shot | null
  assets: Asset[]                           // 当前镜头的所有资源版本
  fetchAssets(shotId): Promise<void>
  generateImage(shotId, promptOverride?): Promise<void>
  generateVideo(shotId, params): Promise<void>
  setMainAsset(shotId, assetId): Promise<void>
}

// stores/config.ts  （localStorage 持久化）
configStore {
  llmConfigs: LLMConfig[]
  promptTemplates: PromptTemplate[]
  // CRUD 方法...
  getDefaultConfig(): LLMConfig | null
  getTemplatesByWorkflow(workflow: string): PromptTemplate[]
}
```

---

## 十一、关键组件清单

```
components/
├── common/
│   ├── AppHeader.vue
│   ├── TaskProgress.vue          # 接受 task_id，自动轮询，显示进度
│   ├── LLMConfigSelector.vue     # 下拉选择 LLMConfig（全局复用）
│   ├── PromptEditor.vue          # 大文本框，{{var}} 语法高亮
│   └── StatusBadge.vue           # 状态标签（draft/confirmed/in_production/...）
├── chat/
│   ├── ChatPanel.vue             # 对话主面板
│   ├── ChatMessage.vue           # 单条消息，支持 Markdown
│   ├── SceneSuggestionCard.vue   # AI建议的片段卡片（内嵌于消息中）
│   └── SummaryConfirmForm.vue    # 总结确认表单（核心组件）
├── scene/
│   ├── SceneCard.vue             # 分集卡片（列表用）
│   ├── ProductionPipeline.vue    # 流程进度展示（分集详情页用）
│   └── ScoreEditor.vue           # 五维评分编辑器
├── storyboard/
│   ├── ShotCard.vue              # 镜头卡片（时间轴中）
│   ├── ShotEditDrawer.vue        # 镜头完整编辑抽屉
│   ├── EmotionCurve.vue          # 情感曲线折线图
│   └── StoryboardConfig.vue      # 生成配置面板（左侧）
├── production/
│   ├── ShotTimeline.vue          # 顶部镜头总览时间轴
│   ├── AssetHistory.vue          # 图像/视频历史版本列表
│   └── VideoPlayer.vue           # 视频播放器
├── character/
│   ├── CharacterCard.vue
│   └── CharacterVersionTimeline.vue
└── settings/
    ├── LLMConfigForm.vue
    └── PromptTemplateForm.vue
```

---

## 十二、AI 调用说明

### 12.1 工作流一：选段对话（前端直接调用 LLM）

对话消息流，前端直接调 LLM API，不经过后端。

```typescript
// composables/useLLMChat.ts
async function* streamMessage(
  config: LLMConfig,
  messages: ChatMessage[]
): AsyncGenerator<string> {
  // 根据 provider 调用对应 API（streaming 模式）
  // google: streamGenerateContent
  // openai/custom: chat completions with stream=true
  // anthropic: messages stream
}
```

每次 AI 回复完成后，前端解析是否包含 `SceneSuggestion` JSON 块，若有则渲染为建议卡片。

### 12.2 工作流一：AI总结（前端直接调用 LLM）

```typescript
// 总结时将完整对话历史 + 已采纳建议 + 总结指令一起发给 LLM
async function summarizeSession(
  session: ChatSession,
  adoptedSuggestions: SceneSuggestion[],
  template: PromptTemplate,
  config: LLMConfig
): Promise<SceneSummary> {
  const systemPrompt = template.system_prompt
  const userContent = buildSummaryPrompt(session.messages, adoptedSuggestions)
  // 非流式调用，要求返回 JSON
  const result = await callLLM(config, systemPrompt, userContent, { json: true })
  return JSON.parse(result) as SceneSummary
}
```

### 12.3 工作流二：分镜生成（经后端 Celery 任务）

```typescript
await axios.post('/tasks/storyboard', {
  scene_id: scene.id,
  shot_count: shotCount,
  style_notes: styleNotes,
  llm_config: {
    provider: config.provider,
    model: config.model,
    api_key: config.api_key,
    temperature: config.temperature,
  },
  system_prompt: currentSystemPrompt,
})
```

---

## 十三、UI 风格规范

- 主题：暗色主题为主（dark mode），可选亮色
- 色调：深蓝 `#1a1f2e` 背景，金色 `#f0a500` 强调色
- 字体：中文用系统字体，提示词/代码区用 monospace
- 卡片圆角：8px
- 动画：页面切换 fade+slide，进度条平滑过渡
- 响应式：优先 1440px 宽屏，最低 1024px

---

## 十四、开发优先级

1. 认证（登录/注册）
2. 项目列表 + 新建项目
3. 全局配置中心（LLM 配置 + 提示词模板）
4. **选段对话 + AI总结确认**（工作流一，含 ChatSession 持久化）
5. 分集详情页（流程总控）
6. **分镜工作台 + 人工微调**（工作流二）
7. **视频制作 + 资源版本管理**（工作流三）
8. 角色管理
9. 素材库

---

## 附录：后端需新增的接口

当前后端缺少以下接口，需补充：

### A. ChatSession CRUD

```python
# backend/app/api/v1/endpoints/chat_sessions.py
GET    /projects/{project_id}/chat-sessions
POST   /projects/{project_id}/chat-sessions        # 创建新会话
GET    /projects/{project_id}/chat-sessions/{id}   # 含完整 messages
PATCH  /projects/{project_id}/chat-sessions/{id}   # 保存消息/更新状态
POST   /projects/{project_id}/chat-sessions/{id}/confirm  # 确认后创建 Scene
```

ChatSession 数据库模型需新增：
- `title`, `status`, `messages`(JSON), `summary`(JSON)
- `scene_id`(FK, nullable), `llm_config_snapshot`(JSON)

### B. Scene 状态推进

```python
POST /projects/{project_id}/scenes/{id}/confirm    # draft → confirmed
```

### C. Shot 批量排序

```python
PATCH /storyboards/{sb_id}/shots/reorder
Body: { ordered_ids: [3, 1, 4, 2, ...] }
```

### D. Storyboard 任务接收动态 LLM 配置

```python
# backend/app/schemas/task.py
class StoryboardGenerationRequest(BaseModel):
    scene_id: int
    shot_count: int = 6
    style_notes: str = ""
    llm_config: dict        # 新增：{ provider, model, api_key, temperature }
    system_prompt: str = "" # 新增：用户可能临时修改的系统提示词
```
