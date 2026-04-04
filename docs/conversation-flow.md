# FilmGenX 核心对话流程设计

> 类比：Claude Code 的 Plan 模式
> 版本：v1.0 | 日期：2026-04-04

---

## 一、核心概念

**一集 = 一个 Conversation**

所有内容，包括：
- 用户的提问
- AI 的分析和建议
- AI 生成的剧本大纲草稿
- 用户对大纲的反馈
- 修改后的新版大纲
- ……

**全部是这个 Conversation 的 Message，永远保留在上下文中。**

直到用户点击"确认执行" → 才真正把大纲写入数据库，触发分镜生成。

---

## 二、数据模型

### Conversation（一集对话）

```typescript
interface Conversation {
  id: number
  project_id: number
  title: string                    // "第01集 - 药老现身"，可编辑
  status: 'active'                 // 永远 active，消息全保留
                 | 'draft_ready'   // 用户点了"总结剧本"，有了草稿大纲
                 | 'confirmed'     // 用户点了"确认执行"，Scene 已创建
  
  messages: Message[]              // 全量消息，按时间顺序
  
  // 最新的剧本大纲（可能经历多次总结，这里存最新版）
  // 注意：历史版本的大纲也作为消息保存在 messages 中
  latest_outline: EpisodeOutline | null
  
  // 确认后关联的 Scene
  scene_id: number | null
  
  created_at: string
  updated_at: string
}
```

### Message（消息）

```typescript
interface Message {
  id: number
  conversation_id: number
  role: 'user' | 'assistant' | 'system'
  content: string                  // Markdown 文本
  
  // 消息类型（影响渲染方式）
  type: 'text'                     // 普通对话消息
      | 'outline_draft'            // AI生成的剧本大纲草稿
      | 'outline_confirmed'        // 用户确认的最终大纲（只有一条）
      | 'system_action'            // 系统操作记录（如"用户确认了大纲"）
  
  // 若 type = 'outline_draft' | 'outline_confirmed'
  outline_data: EpisodeOutline | null
  
  created_at: string
}
```

### EpisodeOutline（剧本大纲）

```typescript
interface EpisodeOutline {
  // 基本信息
  title: string                    // 本集标题，如"药老现身 · 灵魂之约"
  episode_code: string             // 如 "DQCK_EP02"
  
  // 剧情内容
  synopsis: string                 // 本集剧情概述，100-300字
  theme: string                    // 核心主题，如"逆境中的转机"
  
  // 原著定位
  novel_chapter_start: number
  novel_chapter_end: number
  novel_excerpt: string            // 关键原著摘录，用于后续分镜参考
  
  // 制作参数
  scene_types: string[]            // ['battle', 'emotional_peak', ...]
  priority: 'S' | 'A' | 'B' | 'C'
  estimated_duration_sec: number
  
  // 五维评分
  scores: {
    dramatic_tension: number       // 0-10
    visual_potential: number
    emotional_resonance: number
    narrative_importance: number
    audience_familiarity: number
  }
  
  // 角色
  characters: string[]             // 角色名列表（确认时映射到 character_id）
  
  // 给下一步的指导
  storyboard_style_notes: string   // 分镜风格备注，直接传给分镜生成AI
  storyboard_shot_count: number    // 建议的镜头数量
  
  // 元信息
  version: number                  // 第几次总结，从1开始
  generated_at: string
}
```

---

## 三、状态流转

```
[新建 Conversation]
        ↓
  status: 'active'
  用户和AI自由对话，分析小说、讨论剧情
        ↓
  用户点击 [总结剧本] 按钮
        ↓
  AI 读取全部历史消息，生成 EpisodeOutline JSON
  以 type='outline_draft' 的消息追加到对话中
  status → 'draft_ready'
  latest_outline = 这次的大纲
        ↓
  用户看到大纲渲染在对话中
        ↓
  ┌─────────────────────────────────────────────┐
  │  满意？                                      │
  │  [✓ 确认执行]         [继续对话，修改大纲]   │
  └─────────────────────────────────────────────┘
        ↓                         ↓
  status → 'confirmed'      继续聊天（包括对大纲的反馈）
  创建 Scene 记录            status 回到 'active' 或保持
  关联 scene_id              用户可以再次点 [总结剧本]
  追加 type='outline_confirmed' 消息  → AI生成新版大纲（version+1）
  跳转到分镜工作台           追加到对话中，覆盖 latest_outline
                             ……循环，直到满意
```

**关键设计原则：**
- 剧本大纲草稿本身就是一条消息，和其他对话消息平等地存在于上下文中
- AI 下次总结时能"看到"上次的大纲以及用户的修改意见
- 没有独立的"编辑大纲"界面，所有修改通过对话进行
- "确认执行"是不可逆操作（会创建 Scene），需要二次确认

---

## 四、UI 交互设计

### 4.1 对话页面布局

**路由**: `/projects/:projectId/conversations/:conversationId`

```
┌──────────────────────────────────────────────────────────────────┐
│  第02集对话  《斗破苍穹》             [重命名]  状态: 草稿待确认  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  消息列表（滚动区，占满高度）                                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                                                            │  │
│  │  🧑 用户  14:20                                            │  │
│  │  请分析第46-58章，找出最适合动画化的片段                   │  │
│  │                                                            │  │
│  │  🤖 AI  14:21                                             │  │
│  │  第46-58章主要讲述了萧炎激活戒指、药老现身的故事...       │  │
│  │  我找到以下几个关键场景：                                  │  │
│  │  1. 第47章：萧炎绝望中握紧戒指，戒指发光                  │  │
│  │  2. 第49章：药老首次现身，两人的对话                      │  │
│  │  3. 第52章：签订灵魂契约                                  │  │
│  │                                                            │  │
│  │  🧑 用户  14:25                                            │  │
│  │  重点放在药老现身那一刻，要有震撼感                        │  │
│  │                                                            │  │
│  │  🤖 AI  14:26                                             │  │
│  │  明白，那一刻确实是本章的情感高峰...                      │  │
│  │                                                            │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │  📋 剧本大纲草稿  v1  14:30              [收起]      │ │  │
│  │  │  ─────────────────────────────────────────────────   │ │  │
│  │  │  标题：药老现身 · 灵魂之约                           │ │  │
│  │  │  章节：第46-58章  |  优先级：S  |  预计：120秒       │ │  │
│  │  │                                                      │ │  │
│  │  │  剧情概述：                                          │ │  │
│  │  │  萧炎在绝境中意外激活祖传戒指，神秘药老现身。         │ │  │
│  │  │  两人建立灵魂契约，药老承诺帮助萧炎恢复实力...       │ │  │
│  │  │                                                      │ │  │
│  │  │  核心主题：逆境中的转机与师徒羁绊的建立              │ │  │
│  │  │                                                      │ │  │
│  │  │  五维评分：张力9 | 视觉8 | 情感9 | 叙事9 | 熟悉8    │ │  │
│  │  │                                                      │ │  │
│  │  │  分镜建议：10个镜头，整体色调偏暗...                │ │  │
│  │  │                                                      │ │  │
│  │  │  出场角色：萧炎、药老、萧薰儿                        │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  │                                                            │  │
│  │  🧑 用户  14:35                                            │  │
│  │  评分里情感共鸣应该是10，不是9，这一集是全书情感高峰之一  │  │
│  │                                                            │  │
│  │  🤖 AI  14:36                                             │  │
│  │  你说得对，药老现身是萧炎命运的转折点，情感共鸣确实是     │  │
│  │  满分。我来重新总结一版...                               │  │
│  │                                                            │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │  📋 剧本大纲草稿  v2  14:37  ★当前版本   [收起]    │ │  │
│  │  │  ─────────────────────────────────────────────────   │ │  │
│  │  │  情感共鸣：10  （已调整）                            │ │  │
│  │  │  ... 其他内容同v1 ...                                │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  │                                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  底部操作区                                                      │
│                                                                  │
│  ┌─ 配置（可折叠）──────────────────────────────────────────┐   │
│  │  LLM: [Gemini Flash ▼]   模板: [选段对话 v1.2 ▼]        │   │
│  │  [小说上下文：粘贴章节文本...]                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌───────────────────────────────────────────────────┐          │
│  │ 继续输入...                                        │          │
│  └───────────────────────────────────────────────────┘          │
│                                                                  │
│  [预设引导语 ▼]   [总结剧本 📋]              [发送 →]           │
│                        ↑                                         │
│               有草稿时变为:                                      │
│            [再次总结 📋]  [✓ 确认执行，开始分镜]                │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 剧本大纲卡片（消息中内嵌）

大纲以特殊卡片形式渲染在消息流中，支持展开/收起：

- **标题行**：`📋 剧本大纲草稿 v{n}` + 时间戳 + `★当前版本`（最新版才有）+ [展开/收起]
- **展开内容**：完整大纲字段，**只读展示**（不能在这里直接编辑，修改通过对话进行）
- **历史版本**：自动折叠，只有最新版默认展开

### 4.3 "总结剧本"按钮行为

1. 按钮变为 loading 状态
2. 前端把全部消息（含历史大纲）传给 LLM，附加总结指令
3. LLM 以流式输出，先输出普通分析文本，最后输出 `<outline>...</outline>` 标签包裹的 JSON
4. 前端解析出 JSON，创建 `type='outline_draft'` 消息，追加到消息列表
5. 渲染为大纲卡片
6. 保存整个 Conversation 到后端
7. 底部操作区出现 `[✓ 确认执行，开始分镜]` 按钮

### 4.4 "确认执行"按钮行为

1. 弹出确认对话框：
   ```
   ┌──────────────────────────────────────────────┐
   │  确认执行                                     │
   │                                              │
   │  将基于 v2 大纲创建分集记录，并进入分镜流程。 │
   │  此操作不可撤销。                            │
   │                                              │
   │  分集：药老现身 · 灵魂之约                   │
   │  章节：第46-58章                             │
   │  计划镜头数：10                              │
   │                                              │
   │              [取消]  [确认，开始制作 ▶]      │
   └──────────────────────────────────────────────┘
   ```
2. 确认后：
   - 追加 `type='outline_confirmed'` 消息到对话（"用户已确认执行，本集制作开始"）
   - 调用 `POST /projects/{id}/scenes` 用大纲数据创建 Scene
   - 调用 `PATCH /conversations/{id}` 更新 `status='confirmed'`, `scene_id=新Scene.id`
   - **直接触发分镜生成任务**（不再跳转到配置页，使用当前选中的 LLM 配置）
   - 跳转到分集分镜页面

### 4.5 "继续对话"场景

用户觉得大纲不满意，直接在输入框里说：
```
用户："分镜风格备注需要更具体，能否加上斗气的颜色描述？"
AI："好的，萧炎的斗气在这个阶段是绿色..."
用户："对，而且药老用的是金色斗气"
用户：[再次点击 总结剧本]
→ AI 看到v1大纲 + 用户的修改意见 + v2大纲 + 又一轮对话，生成 v3 大纲
```

---

## 五、后端数据结构

### 5.1 新增数据库表

#### conversations 表

```sql
CREATE TABLE conversations (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER NOT NULL REFERENCES projects(id),
    title           VARCHAR(200) NOT NULL DEFAULT '新对话',
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
                    -- active | draft_ready | confirmed
    latest_outline  JSONB,              -- 最新的 EpisodeOutline
    scene_id        INTEGER REFERENCES scenes(id),  -- 确认后关联
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### messages 表

```sql
CREATE TABLE messages (
    id                  SERIAL PRIMARY KEY,
    conversation_id     INTEGER NOT NULL REFERENCES conversations(id),
    role                VARCHAR(20) NOT NULL,   -- user | assistant | system
    content             TEXT NOT NULL,          -- Markdown 文本
    type                VARCHAR(30) NOT NULL DEFAULT 'text',
                        -- text | outline_draft | outline_confirmed | system_action
    outline_data        JSONB,                  -- 仅 outline_* 类型时有值
    seq                 INTEGER NOT NULL,        -- 消息序号（排序用）
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id, seq);
```

### 5.2 新增 API 端点

```
# Conversation
GET    /projects/{project_id}/conversations          列表
POST   /projects/{project_id}/conversations          新建
GET    /projects/{project_id}/conversations/{id}     详情（含所有 messages）
PATCH  /projects/{project_id}/conversations/{id}     更新（保存消息、更新状态）
DELETE /projects/{project_id}/conversations/{id}     软删除

# 确认执行（关键动作）
POST   /projects/{project_id}/conversations/{id}/confirm
  Body: { outline: EpisodeOutline, llm_config: {...}, shot_count: int }
  → 创建 Scene + 触发分镜 Celery 任务
  Response: { scene_id, task_id }
```

### 5.3 PATCH /conversations/{id} 的 Body

```typescript
// 前端在适当时机调用（发消息后、总结后、页面离开前）
{
  title?: string
  status?: 'active' | 'draft_ready'
  latest_outline?: EpisodeOutline | null
  messages?: Message[]    // 全量消息列表（后端做 upsert）
}
```

### 5.4 POST /conversations/{id}/confirm 的后端逻辑

```python
async def confirm_conversation(conversation_id, body):
    # 1. 创建 Scene 记录
    scene = await scene_repo.create(
        project_id=conversation.project_id,
        scene_code=body.outline.episode_code,
        title=body.outline.title,
        novel_excerpt=body.outline.novel_excerpt,
        # ... 其他字段从 outline 映射
        status='in_production',
    )

    # 2. 更新 Conversation
    await conv_repo.update(conversation, {
        'status': 'confirmed',
        'scene_id': scene.id,
    })

    # 3. 追加确认消息
    await msg_repo.create(
        conversation_id=conversation_id,
        role='system',
        type='outline_confirmed',
        content='剧本大纲已确认，分镜生成任务已启动。',
        outline_data=body.outline,
    )

    # 4. 触发分镜 Celery 任务
    task = await task_repo.create(
        task_type='storyboard_generation',
        input_params={
            'scene_id': scene.id,
            'shot_count': body.shot_count,
            'style_notes': body.outline.storyboard_style_notes,
            'llm_config': body.llm_config,
            'system_prompt': body.system_prompt,
            'novel_excerpt': body.outline.novel_excerpt,
        }
    )
    celery_task = generate_storyboard_task.delay(task.id)
    await task_repo.update(task, {'celery_task_id': celery_task.id})

    return {'scene_id': scene.id, 'task_id': task.id}
```

---

## 六、前端消息保存策略

对话消息的保存不需要每条都请求一次后端，采用以下策略：

```typescript
// 触发保存的时机
const SAVE_TRIGGERS = [
  'after_ai_reply',        // 每次AI回复完成后（最重要）
  'after_outline_generated', // 总结剧本完成后（必须保存）
  'before_page_leave',     // 页面离开前（beforeUnload）
  'manual_save',           // 用户手动点保存
]

// 不需要每次用户发消息就保存
// 因为用户消息只是文本，AI回复后一起保存即可
```

---

## 七、LLM 总结指令（scene_summary 提示词模板）

这是 `workflow='scene_summary'` 的系统提示词默认模板，用户可在设置中修改：

```
你是一名动漫制片总监助手。

根据以下对话内容（包括此前生成的所有大纲草稿和用户的修改意见），
生成一份最新的剧本大纲。

输出格式：
1. 先用1-2句话说明这次相比上一版的主要变化（若是第一版则跳过）
2. 输出 <outline> 标签包裹的 JSON，格式如下：

<outline>
{
  "title": "本集标题",
  "episode_code": "项目前缀_EP序号",
  "synopsis": "100-300字的本集剧情概述",
  "theme": "一句话核心主题",
  "novel_chapter_start": 46,
  "novel_chapter_end": 58,
  "novel_excerpt": "关键原著摘录，1-3段，用\\n\\n分隔",
  "scene_types": ["emotional_peak", "character_introduction"],
  "priority": "S",
  "estimated_duration_sec": 120,
  "scores": {
    "dramatic_tension": 9,
    "visual_potential": 8,
    "emotional_resonance": 10,
    "narrative_importance": 9,
    "audience_familiarity": 8
  },
  "characters": ["萧炎", "药老"],
  "storyboard_style_notes": "给分镜导演的具体风格指导...",
  "storyboard_shot_count": 10,
  "version": 2
}
</outline>

注意：
- version 从1开始，每次重新总结递增
- storyboard_style_notes 要具体，包括色调、运镜风格、特效建议
- 充分吸收用户在对话中提出的所有修改意见
```

---

## 八、前端组件设计

### ChatConversationPage.vue

主页面，包含：
- 消息列表（`MessageList.vue`）
- 底部输入区（`ChatInputArea.vue`）
- 配置折叠面板（`LLMConfigPanel.vue`）

### MessageList.vue

遍历 `messages`，根据 `type` 渲染：
- `text` → `TextMessage.vue`（普通气泡）
- `outline_draft` → `OutlineDraftCard.vue`（大纲卡片，可展开）
- `outline_confirmed` → `OutlineConfirmedCard.vue`（已确认标记，绿色）
- `system_action` → 居中小字系统提示

### OutlineDraftCard.vue

```
┌──────────────────────────────────────────────────────┐
│  📋 剧本大纲草稿  v2  14:37  ★当前版本        [▼]  │
├──────────────────────────────────────────────────────┤
│  标题：药老现身 · 灵魂之约                           │
│  章节：第46-58章  |  优先级：S  |  预计时长：120秒  │
│  ...（折叠后只显示标题行）                           │
└──────────────────────────────────────────────────────┘
```

展开后显示完整大纲，**只读**。

### ChatInputArea.vue

状态决定底部按钮显示：

```typescript
type ConversationStatus = 'active' | 'draft_ready' | 'confirmed'

// active 状态：
// [预设引导语 ▼]  [总结剧本 📋]  [发送 →]

// draft_ready 状态：
// [预设引导语 ▼]  [再次总结 📋]  [✓ 确认执行]  [发送 →]

// confirmed 状态：
// [查看分镜] （对话区变为只读，可以滚动查看但不能继续发消息）
```

---

## 九、Pinia Store

```typescript
// stores/conversation.ts
conversationStore {
  conversations: Conversation[]          // 项目下的所有对话
  current: Conversation | null
  messages: Message[]                    // 当前对话的消息（含未保存的）
  isSaving: boolean
  isSummarizing: boolean
  
  // Actions
  fetchConversations(projectId): Promise<void>
  openConversation(id): Promise<void>    // 加载会话和全量消息
  
  sendMessage(content: string): Promise<void>
  // 内部流程：
  //   1. 追加 user 消息到本地 messages
  //   2. 调用 LLM（streaming）
  //   3. 追加 assistant 消息到本地 messages
  //   4. 调用 save()

  summarize(): Promise<void>
  // 内部流程：
  //   1. 把所有 messages 传给 LLM + 总结指令
  //   2. 解析 <outline>...</outline> 中的 JSON
  //   3. 追加 outline_draft 消息
  //   4. 更新 latest_outline
  //   5. 更新 status = 'draft_ready'
  //   6. 调用 save()

  confirm(outline: EpisodeOutline): Promise<{ scene_id, task_id }>
  // 调用 POST /conversations/{id}/confirm
  // 成功后跳转到分镜页面

  save(): Promise<void>
  // PATCH /conversations/{id}，保存当前状态
}
```
