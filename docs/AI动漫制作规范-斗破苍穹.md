# AI 动漫制作规范文档
## 项目：《斗破苍穹》AI 视频系列

> 目标：制作媲美专业团队水准的 AI 动漫视频，建立可复用、可扩展的生产流水线。

---

## 目录

1. [整体生产流程](#1-整体生产流程)
2. [高光片段选取规范](#2-高光片段选取规范)
3. [分镜脚本输出格式](#3-分镜脚本输出格式)
4. [世界观视觉规范库 (Visual Bible)](#4-世界观视觉规范库-visual-bible)
5. [角色资产管理](#5-角色资产管理)
6. [镜头语言规范](#6-镜头语言规范)
7. [分镜关联性管理](#7-分镜关联性管理)
8. [音频层设计规范](#8-音频层设计规范)
9. [叙事节奏管理](#9-叙事节奏管理)
10. [质量评审标准](#10-质量评审标准)
11. [迭代反馈机制](#11-迭代反馈机制)
12. [技术工具栈建议](#12-技术工具栈建议)

---

## 1. 整体生产流程

```
小说原文
  │
  ▼
[阶段一] 高光片段选取
  │  - AI 分析叙事节奏，筛选高光时刻
  │  - 标注片段类型（战斗/情感/成长/反转）
  │
  ▼
[阶段二] 叙事设计
  │  - 确定情感弧线
  │  - 规划节奏曲线（时长分配）
  │  - 设计悬念与留白点
  │
  ▼
[阶段三] 分镜脚本生成
  │  - 套用世界观视觉规范
  │  - 套用角色状态档案
  │  - 生成结构化分镜 JSON
  │
  ▼
[阶段四] 素材生成
  │  - 图像生成（MidJourney / Stable Diffusion）
  │  - 视频生成（Runway / Kling / Sora）
  │  - 特效层叠加
  │
  ▼
[阶段五] 音频制作
  │  - AI 配音 + 情感标注
  │  - 音效匹配
  │  - BGM 编排
  │
  ▼
[阶段六] 后期合成
  │  - 剪辑拼接
  │  - 转场设计
  │  - 色彩分级
  │  - 字幕合成
  │
  ▼
[阶段七] 质量评审 → 迭代
```

---

## 2. 高光片段选取规范

### 2.1 片段类型分类

| 类型 | 定义 | 示例 |
|------|------|------|
| **战斗高光** | 关键战斗转折点，出现新斗技/突破 | 萧炎初次使用三玄变 |
| **情感高潮** | 人物关系转折，情绪爆发点 | 萧炎与萧薰儿重逢 |
| **成长节点** | 境界突破，实力飞跃 | 萧炎突破斗王 |
| **世界观展开** | 重要设定揭露，宏大场景 | 圣域初现 |
| **反转时刻** | 剧情大逆转，出人意料 | 纳戒中的药老现身 |

### 2.2 片段评分标准

AI 选取高光片段时，按以下维度打分（各 0-10 分）：

```json
{
  "scene_score": {
    "dramatic_tension": 8,      // 戏剧张力
    "visual_potential": 9,      // 视觉化潜力（能否转化为震撼画面）
    "emotional_resonance": 7,   // 情感共鸣度
    "narrative_importance": 8,  // 叙事重要性
    "audience_familiarity": 9,  // 粉丝熟知度（经典场景优先）
    "total": 41
  }
}
```

### 2.3 片段信息结构

```json
{
  "scene_id": "DQCK_001",
  "title": "萧炎三年后归来，云岚宗大会",
  "novel_reference": {
    "chapter_start": "第156章",
    "chapter_end": "第162章",
    "key_paragraph": "原文关键段落摘录..."
  },
  "scene_type": ["战斗高光", "情感高潮", "成长节点"],
  "characters_involved": ["萧炎", "云山", "萧薰儿", "纳兰嫣然"],
  "estimated_duration_sec": 180,
  "priority": "S",
  "score": 41
}
```

---

## 3. 分镜脚本输出格式

### 3.1 完整分镜 JSON 结构

每个分镜（Shot）是最小的生产单元，必须包含以下所有字段：

```json
{
  "shot_id": "DQCK_001_S003",
  "scene_id": "DQCK_001",
  "sequence": 3,
  "duration_sec": 4.5,

  "camera": {
    "shot_type": "medium_close_up",
    "angle": "slightly_low",
    "movement": "slow_push_in",
    "focal_length": "85mm_equivalent",
    "depth_of_field": "shallow"
  },

  "composition": {
    "subject_position": "center_slightly_left",
    "rule_of_thirds": true,
    "foreground": "散落的瓦砾，微微颤动",
    "midground": "萧炎站立，斗气缭绕全身",
    "background": "云岚宗广场，远处长老席位",
    "leading_lines": "人群视线汇聚向萧炎"
  },

  "character": {
    "id": "CHAR_XIAO_YAN",
    "state_version": "v3_yilan_period",
    "position": "画面中央偏左，站姿挺拔",
    "action": "缓缓抬起头，眼神从低垂转为直视前方",
    "expression": "隐忍多年后释放的冷然，嘴角微微上扬",
    "emotion_intensity": 8,
    "costume": "青色长袍，轻微战损，右肩有划破痕迹",
    "special_effects_on_character": {
      "dou_qi_color": "#4A90E2",
      "dou_qi_pattern": "细密流动的蓝色斗气丝，贴附皮肤表面",
      "aura_intensity": "medium",
      "particle_effects": "偶有斗气粒子从指尖逸散"
    }
  },

  "environment": {
    "location_id": "LOC_YUNLAN_SQUARE",
    "time_of_day": "morning",
    "weather": "晴，轻风",
    "lighting": {
      "key_light": "右上方斜射阳光，45度角，暖黄色",
      "fill_light": "左侧柔和环境光，冷蓝色",
      "rim_light": "逆光勾勒人物轮廓，强度高",
      "shadow": "长条人物阴影向左延伸，暗示时光流逝"
    },
    "atmosphere": "轻微晨雾残留，空气中有尘埃颗粒被光照射"
  },

  "dialogue": {
    "character": "萧炎",
    "text": "三年了……",
    "delivery": {
      "tone": "低沉，压抑，带着一丝解脱",
      "pace": "extremely_slow",
      "pause_before_sec": 1.5,
      "pause_after_sec": 2.0,
      "volume": "near_whisper",
      "emotion_tag": ["relief", "suppressed_anger", "determination"]
    },
    "subtitle_style": "白字黑边，字体：思源宋体"
  },

  "sound_design": {
    "ambient": "广场人群的屏息声，远处风声",
    "sfx_list": [
      {"time": "0.5s", "sound": "斗气涌动低鸣，从体内向外扩散"},
      {"time": "2.0s", "sound": "轻微的脚步踏地声"}
    ],
    "music": {
      "track_mood": "压抑转爆发前的静默",
      "instrument": "弦乐单音持续，极低音量",
      "intensity": 2
    }
  },

  "transition": {
    "in": "cut_from_previous",
    "out": "slow_dissolve_to_next",
    "notes": "此镜头结束时画面刻意停顿0.5秒再转场，制造窒息感"
  },

  "continuity": {
    "prev_shot_id": "DQCK_001_S002",
    "next_shot_id": "DQCK_001_S004",
    "spatial_relationship": "前一镜头为云山俯视视角，本镜头为萧炎视角，完成视点对切",
    "continuity_notes": "萧炎右手握拳动作需与上一镜头保持一致"
  },

  "generation_prompt": {
    "image_prompt": "A young Chinese cultivator in blue robes, standing in a grand courtyard, early morning light, cinematic composition, anime style, detailed face expression of cold determination...",
    "negative_prompt": "blurry, deformed hands, extra fingers, low quality",
    "reference_assets": ["CHAR_XIAO_YAN_v3.png", "LOC_YUNLAN_SQUARE_ref.png"],
    "style_preset": "donghua_cinematic_v2"
  },

  "qc_checklist": {
    "character_consistency": false,
    "lighting_match": false,
    "action_continuity": false,
    "approved": false
  }
}
```

---

## 4. 世界观视觉规范库 (Visual Bible)

### 4.1 斗气颜色体系

斗气颜色是《斗破苍穹》最核心的视觉语言，必须严格统一。

| 等级 | 颜色描述 | HEX 参考 | 视觉特征 |
|------|---------|----------|---------|
| 斗者 | 淡白色 | `#F5F5F0` | 细薄，贴体，几乎透明 |
| 斗师 | 淡黄色 | `#FFF5CC` | 稳定流动，有轻微光晕 |
| 斗灵 | 橙黄色 | `#FFB830` | 明显光晕，有粒子逸散 |
| 斗王 | 深橙色 | `#FF6B35` | 强烈光芒，带有冲击波纹 |
| 斗皇 | 红橙色 | `#FF4500` | 炽烈，有热浪扭曲效果 |
| 斗宗 | 深红色 | `#CC2200` | 压迫感强，环境受影响 |
| 斗尊 | 深紫红 | `#8B0000` | 空间微微震颤 |
| 斗圣 | 金紫色 | `#7B2FBE` | 金色与紫色交织，神圣感 |
| 斗帝 | 纯金色 | `#FFD700` | 极致辉煌，光芒普照 |

#### 特殊异火视觉规范

```
异火名称：三千焱炎火
颜色：#FF4500（主）+ #FF8C00（副）
形态：如旋转的火焰龙卷，中心极白
粒子：向上飞散的橙红色火星
光照影响：方圆5米内有明显暖色光照反射

异火名称：骨灵冷火
颜色：#00BFFF（主）+ #FFFFFF（副）
形态：冷静的蓝白色火焰，边缘锐利如冰晶
粒子：凝结成微小冰晶后下落
光照影响：冷蓝色光，周围温度感觉极低，地面有轻微白雾

异火名称：颜莲心火
颜色：#9B59B6（主）+ #FF69B4（副）
形态：莲花状，外层花瓣轻柔飘动
粒子：淡紫色莲花瓣形粒子
光照影响：柔和紫光，有神秘感

异火名称：杂色斗气（药老融合后）
颜色：七彩交织，无固定主色
形态：流动性极强，颜色不断变换
```

### 4.2 势力/地点视觉规范

#### 乌坦城 / 萧家（早期）
- **建筑风格**：仿中古中国北方民居，略显朴素，黄土色调
- **主色调**：土黄 `#C8A96E`、暖褐 `#8B5E3C`
- **光线特征**：偏暖，多晴天直射光，少有阴影处理
- **氛围关键词**：市井、烟火气、平凡

#### 云岚宗
- **建筑风格**：高耸山门，飞檐翘角，气势磅礴，带压迫感
- **主色调**：冷灰蓝 `#4A6FA5`、深石灰 `#5A5A5A`、白 `#F0F0F0`
- **光线特征**：多侧光、逆光，常有云雾缭绕，营造威严感
- **氛围关键词**：压迫、权威、等级森严

#### 迦南学院
- **建筑风格**：宏大学府，多石柱，有古典西域风格混合东方元素
- **主色调**：米白 `#F5E6C8`、金色 `#D4A017`、深棕 `#6B4226`
- **光线特征**：明亮，多顶光和散射光，充满活力
- **氛围关键词**：活力、竞争、成长、热血

#### 魂殿
- **建筑风格**：哥特式与东方元素结合，漂浮骷髅装饰，极度阴暗
- **主色调**：深黑 `#1A1A1A`、血红 `#8B0000`、骨白 `#F5F5DC`
- **光线特征**：几乎无自然光，以红色烛火和魂焰照明
- **氛围关键词**：恐惧、神秘、邪恶、强大

### 4.3 整体美术风格定义

```
参考风格：《斗罗大陆》动画 + 《天官赐福》动画的融合
  - 流畅的线条，中国古风气质
  - 战斗场景参考：《鬼灭之刃》的特效层次感
  - 构图参考：韩国工作室 MAPPA 的电影级构图

色彩分级基调：
  - 战斗场景：高对比度，饱和度+20%，强调冷暖对比
  - 日常场景：自然色调，饱和度适中，偏暖
  - 回忆/过去：降低饱和度至60%，轻微泛黄
  - 幻境/斗气空间：饱和度+40%，色调整体偏蓝紫
```

---

## 5. 角色资产管理

### 5.1 角色档案结构

每个角色有一个独立的资产档案，包含所有状态版本：

```json
{
  "char_id": "CHAR_XIAO_YAN",
  "name": "萧炎",
  "versions": [
    {
      "version_id": "v1_teen",
      "age_range": "15-16岁",
      "applicable_chapters": "第1章 - 第50章",
      "description": "少年感明显，五官未完全长开，身材偏瘦",
      "height": "168cm",
      "build": "瘦削，肩膀略窄",
      "face": "少年感，眼神带稚气但有倔强，双眸漆黑",
      "hair": "黑色，略显凌乱，中等长度",
      "costume": {
        "default": "白色粗布长袍，腰间青色布带",
        "formal": "萧家出行装，深蓝色",
        "battle": "白袍轻微战损"
      },
      "dou_qi_color": "#F5F5F0",
      "reference_images": ["xiao_yan_v1_front.png", "xiao_yan_v1_side.png"],
      "key_features": ["左耳佩戴小型圆形玉坠", "右手无名指有一处旧伤疤"]
    },
    {
      "version_id": "v2_post_training",
      "age_range": "18-19岁",
      "applicable_chapters": "第51章 - 第200章",
      "description": "三年苦修后，气质蜕变，由少年转为青年",
      "height": "178cm",
      "build": "精壮，肩宽，肌肉线条明显但不夸张",
      "face": "轮廓更加分明，眼神沉稳冷然，失去稚气",
      "hair": "黑色，束起，鬓角利落",
      "costume": {
        "default": "青色长袍，银色腰带",
        "battle": "青袍战甲，露出前臂，便于施展斗技"
      },
      "dou_qi_color": "#FFB830",
      "reference_images": ["xiao_yan_v2_front.png", "xiao_yan_v2_battle.png"]
    }
  ],

  "consistent_features": {
    "eyes": "漆黑色瞳仁，眼神深邃，这是所有版本的核心特征",
    "skin": "小麦色，因长期修炼和旅行所致",
    "expression_baseline": "平静中带一丝若有若无的疏离"
  },

  "expression_guide": {
    "anger": "眉心微蹙，嘴唇紧抿，眼神锐利如刀",
    "determination": "眼神直视前方，嘴角轻抿，下颌微收",
    "surprise": "眉毛轻扬，眼瞳放大，嘴唇微开",
    "grief": "眼神涣散，嘴角微垂，肩膀略塌",
    "battle_focus": "眼神极度凝聚，瞳孔收缩，嘴角带一丝冷笑"
  },

  "action_guide": {
    "standing_default": "双臂自然下垂，重心偏左腿，头微微抬起",
    "battle_stance": "右脚在前，左脚在后，双手握拳置于腰侧，身体微前倾",
    "casting_skill": "右手先向上延伸汇聚斗气，然后向目标推出，同时腰部发力"
  }
}
```

### 5.2 角色关系图谱

```
萧炎
├── 纳戒（药老 · 药尘）
│     └── 师徒关系，核心导师
├── 萧薰儿
│     └── 青梅竹马，婚约，分离后的重逢线
├── 美杜莎女王
│     └── 由敌转友，暗恋线
├── 云韵（小医仙）
│     └── 同行伙伴，医术辅助
├── 纳兰嫣然
│     └── 早期情感纠葛
├── 萧战（父亲）
│     └── 家族支柱，情感依托
└── 萧家族人
      └── 保护对象，成长动力
```

### 5.3 素材命名规范

```
格式：{CHAR_ID}_{VERSION}_{TYPE}_{ANGLE}_{STATE}.png

示例：
  CHAR_XIAO_YAN_v2_portrait_front_normal.png     // 正面半身像，正常状态
  CHAR_XIAO_YAN_v2_portrait_front_angry.png      // 正面半身像，愤怒状态
  CHAR_XIAO_YAN_v2_fullbody_side_battle.png      // 侧面全身，战斗状态
  LOC_YUNLAN_SQUARE_day_wide.png                  // 云岚广场，白天，全景
  FX_YIHUO_SANQIAN_idle.png                       // 三千焱炎火，待机状态
```

---

## 6. 镜头语言规范

### 6.1 镜头类型定义

| 镜头类型 | 英文 | 适用场景 |
|---------|------|---------|
| 大远景 | Extreme Wide Shot | 世界观展示，宏大场景，孤独感 |
| 远景 | Wide Shot | 战场全貌，多人战斗 |
| 全景 | Full Shot | 人物登场，展示全身姿态 |
| 中景 | Medium Shot | 对话，表情与动作并重 |
| 中近景 | Medium Close-up | 情感场景，表情为主 |
| 近景 | Close-up | 眼神，表情细节，关键道具 |
| 大特写 | Extreme Close-up | 极度情绪，细节强调（眼睛、手、火焰） |

### 6.2 战斗场景镜头语法

战斗场景遵循以下镜头节奏规则：

```
[蓄力/判断阶段]
  → 中景（展示人物全身状态）
  → 中近景（面部表情，展示决心）
  → 大特写（眼神锁定目标）

[出招阶段]
  → 全景（展示动作起势）
  → 特写（关键动作部位，如握拳、脚踏地）
  → 大远景或广角（展示斗技释放的宏大范围）

[命中/交锋阶段]
  → 慢动作特写（瞬间碰撞细节）
  → 快速切换3-5个不同角度的近景（营造混乱感）

[结果/反应阶段]
  → 全景（展示战场结果）
  → 中近景（胜者表情）
  → 中近景（败者反应）
  → 大远景（收场，余韵）
```

### 6.3 情感场景镜头语法

```
[重逢/告白类]
  → 远景建立空间关系（两人距离）
  → 切换双方各自中近景（交替展示表情）
  → 随情绪升温，景别逐渐缩小
  → 高潮时刻：大特写眼神
  → 结束时：拉远至全景或大远景，给空间感

[独白/内心戏]
  → 固定镜头，中近景或近景
  → 轻微慢推（slow push in）强调情绪积累
  → 配合景深变化（背景逐渐虚化）
```

### 6.4 运镜速度规范

| 情绪状态 | 运镜速度 | 剪辑节奏 |
|---------|---------|---------|
| 平静叙事 | 慢速推拉 | 每镜3-6秒 |
| 情绪升温 | 中速推进 | 每镜2-3秒 |
| 战斗高潮 | 快速切换 | 每镜0.5-1.5秒 |
| 震撼时刻 | 突然静止 | 拉长单镜至4-6秒 |
| 极速动作 | 慢动作反差 | 慢动作镜头3-5秒 |

---

## 7. 分镜关联性管理

### 7.1 场景连续性规则

相邻分镜之间需要管理以下连续性维度：

```json
{
  "continuity_dimensions": {
    "spatial": {
      "description": "空间位置连续性",
      "rules": [
        "人物在场景中的相对位置需保持合理",
        "使用 180度规则：对话双方始终在轴线同侧",
        "镜头切换时注意人物朝向不能突然反转"
      ]
    },
    "temporal": {
      "description": "时间连续性",
      "rules": [
        "同一连续动作不能跳接（除非有意制造跳切效果）",
        "同一场景的光线强度不能突变",
        "战斗中人物的战损状态需累积"
      ]
    },
    "action": {
      "description": "动作连续性",
      "rules": [
        "重要动作（如挥拳、施法）需要起始和结束帧对应",
        "服装飘动方向需与风向一致",
        "人物视线方向需与所注视的内容对应"
      ]
    },
    "emotional": {
      "description": "情绪连续性",
      "rules": [
        "情绪变化需要合理过渡，不能无故突变",
        "配乐情绪需配合画面情绪"
      ]
    }
  }
}
```

### 7.2 分镜依赖关系类型

```
类型一：视角对切 (Counter Shot)
  镜头 A：云山俯视萧炎（高角度）
  镜头 B：萧炎仰视云山（低角度）
  → 生成 B 时，必须参考 A 的光线和空间信息

类型二：动作接续 (Action Continuity)
  镜头 A：萧炎右手举起，火焰汇聚
  镜头 B：火焰从手中射出命中目标
  → B 中火焰的颜色、大小必须与 A 完全一致

类型三：场景延伸 (Scene Extension)
  镜头 A：战后广场全貌（废墟、烟尘）
  镜头 B：同一广场另一角度的近景
  → B 必须使用 A 生成的场景作为参考底图

类型四：情绪呼应 (Emotional Echo)
  镜头 A：年轻萧炎被羞辱时低头（过去）
  镜头 B：如今萧炎面对同样场景抬头（现在）
  → B 的构图需刻意模仿 A，形成对比
```

### 7.3 依赖关系标注

```json
{
  "shot_id": "DQCK_001_S008",
  "dependencies": [
    {
      "type": "scene_extension",
      "depends_on": "DQCK_001_S005",
      "dependency_detail": "需使用 S005 生成的广场场景图作为参考，保持背景一致",
      "required_assets": ["DQCK_001_S005_background_ref.png"]
    },
    {
      "type": "action_continuity",
      "depends_on": "DQCK_001_S007",
      "dependency_detail": "S007 中萧炎右臂举起的姿势，本镜头需从该姿势继续",
      "required_assets": ["DQCK_001_S007_last_frame.png"]
    }
  ]
}
```

---

## 8. 音频层设计规范

### 8.1 台词情感标注格式

```json
{
  "dialogue_id": "DQCK_001_D003",
  "character": "萧炎",
  "text": "三年了……那段日子，如今想来，竟是如此清晰。",
  "emotion_tags": ["relief", "melancholy", "determination"],
  "primary_emotion": "melancholy",
  "delivery_params": {
    "tone": "低沉，压抑，带着久违的感慨",
    "pace": "very_slow",
    "volume": "low_normal",
    "pause_positions": [
      {"after_char": "了", "duration_sec": 1.5, "type": "breath"},
      {"after_char": "晰", "duration_sec": 2.0, "type": "emotional"}
    ],
    "emphasis_words": ["三年", "清晰"],
    "voice_texture": "略带沙哑，克制",
    "breath_audibility": "slight"
  },
  "tts_prompt": "用低沉沙哑的男声，极慢语速，带着压抑的情感，在"三年了"之后停顿明显..."
}
```

### 8.2 音效触发规范

```json
{
  "sfx_library": {
    "dou_qi_categories": {
      "charge_up": {
        "description": "斗气汇聚时的低频共鸣声",
        "intensity_range": [1, 10],
        "notes": "intensity 对应斗气等级，斗帝级别需要加低频震动"
      },
      "release": {
        "description": "斗技释放时的爆发音效",
        "variants": ["single_burst", "continuous_stream", "area_explosion"]
      },
      "impact": {
        "description": "斗技命中时的撞击声",
        "variants": ["flesh", "stone", "energy_shield", "air"]
      }
    },
    "environment_categories": {
      "yunlan_sect": ["风声", "远处人群低语", "旗帜飘动声", "石地脚步声"],
      "jia_nan_academy": ["远处喧闹声", "斗气训练声", "钟声"],
      "soul_hall": ["诡异低鸣", "火焰燃烧声", "回响脚步声", "魂力涌动声"]
    }
  }
}
```

### 8.3 BGM 情绪规范

```
情绪区间定义（1-10级）：
  1-2  平静叙事：轻音乐，单一乐器（古筝/笛），无打击
  3-4  情绪酝酿：弦乐进入，节奏开始有律动
  5-6  战斗前奏：鼓点加入，旋律性增强，有紧张感
  7-8  战斗高潮：全乐器爆发，强烈打击乐，旋律激昂
  9-10 史诗时刻：合唱加入，宏大编曲，震撼感

BGM 过渡规则：
  - 情绪变化 ≤ 2级：淡入淡出（2-3秒渐变）
  - 情绪变化 3-4级：重叠切换（前一曲渐出，新曲渐入，重叠2秒）
  - 情绪变化 ≥ 5级（如突然爆发）：允许硬切，但需配合音效遮盖
```

---

## 9. 叙事节奏管理

### 9.1 情感弧线设计

每个视频片段都需要在生产前设计完整的情感弧线：

```
示例：萧炎云岚宗大会片段（3分钟）

时间轴（分:秒）：
0:00 ─────────────────────────────────── 3:00
│                                              │
压 ─── 0:00-0:45 ───> 2  [压抑，回忆开场]      │
抑                                             │
│    0:45-1:30 ───> 4  [人物登场，暗流涌动]     │
提                                             │
升   1:30-1:50 ───> 6  [对峙开始，冲突明显]     │
│                                             │
爆   1:50-2:20 ───> 9  [战斗爆发，最高潮]       │
发                                             │
│    2:20-2:40 ───> 7  [结果揭晓，震撼众人]     │
余                                             │
韵   2:40-3:00 ───> 4  [尾声，余音绕梁]         │
```

### 9.2 悬念设计规则

```
悬念类型一：视觉悬念
  → 先展示结果，再倒叙原因
  示例：先展示云岚宗长老震惊表情，再展示萧炎的斗技

悬念类型二：信息差悬念
  → 观众知道但角色不知道（或反之）
  示例：观众看到纳戒震动，而旁边的人毫不知情

悬念类型三：对比悬念
  → 用过去状态与现在状态形成反差
  示例：快速插入当年被羞辱的片段，再切回当下的强大

留白原则：
  - 每2分钟视频至少有2处刻意留白（画面静止 + 音乐骤降）
  - 留白时长：0.5-2秒
  - 留白后必须有情绪爆发或重要信息揭示
```

### 9.3 时长分配规范

```json
{
  "duration_guidelines": {
    "total_video_target": "2-4分钟（抖音/B站竖屏版）",
    "shot_duration_by_type": {
      "action_shot": "0.5-2秒",
      "dialogue_shot": "2-5秒",
      "establishing_shot": "2-4秒",
      "emotional_closeup": "2-6秒",
      "epic_wide_shot": "3-6秒",
      "slow_motion_key_moment": "2-5秒（原速0.5-1秒）"
    },
    "pacing_ratio": {
      "buildup": "30%",
      "climax": "40%",
      "resolution": "30%"
    }
  }
}
```

---

## 10. 质量评审标准

### 10.1 单镜头评审清单

每个生成的分镜在进入下一流程前，必须通过以下检查：

```
[ ] 角色一致性
    ├── [ ] 人物五官与角色档案对应版本一致
    ├── [ ] 服装颜色和细节正确
    ├── [ ] 斗气颜色符合当前境界设定
    └── [ ] 标志性特征存在（如萧炎的玉坠、疤痕）

[ ] 光线合理性
    ├── [ ] 主光源方向与脚本描述一致
    ├── [ ] 阴影与光源位置逻辑匹配
    └── [ ] 与相邻镜头光线连续（除非刻意切换）

[ ] 构图质量
    ├── [ ] 主体清晰，不被遮挡
    ├── [ ] 符合规定的景别要求
    └── [ ] 无明显的 AI 生成瑕疵（多余手指、变形面部等）

[ ] 动作合理性
    ├── [ ] 人体结构正确，无异常弯折
    ├── [ ] 动作与台词/情绪匹配
    └── [ ] 与上一镜头动作连续

[ ] 世界观准确性
    ├── [ ] 建筑/环境风格符合地点设定
    └── [ ] 无时代错误（现代元素混入古风场景）
```

### 10.2 整体视频评审标准

| 维度 | 评分项 | 满分 |
|------|--------|------|
| 视觉一致性 | 全片人物形象统一程度 | 25 |
| 叙事流畅度 | 观看时是否能顺畅理解剧情 | 20 |
| 情感冲击力 | 高潮时刻是否有震撼感 | 20 |
| 镜头语言 | 运镜、构图是否专业 | 15 |
| 音画同步 | 音效、配乐与画面配合度 | 10 |
| 细节完成度 | 斗气特效、环境细节 | 10 |
| **总分** | | **100** |

**发布标准：≥ 80分**
**内部存档：≥ 65分**
**返工重做：< 65分**

---

## 11. 迭代反馈机制

### 11.1 提示词版本管理

```json
{
  "prompt_template_id": "CHAR_XIAO_YAN_v2_battle_stance",
  "version": "v1.3",
  "created": "2024-01-01",
  "last_updated": "2024-01-15",
  "base_prompt": "A young Chinese male cultivator, approximately 18 years old, athletic build, wearing azure blue robes with silver belt, black hair tied back, determined and cold expression, blue-orange dou qi energy surrounding his body...",
  "style_suffix": "donghua animation style, cinematic lighting, 4K, detailed, flowing fabric",
  "negative_prompt": "extra fingers, deformed face, modern clothing, western style, blurry",
  "performance_history": [
    {
      "version": "v1.0",
      "result_rating": 6.5,
      "issue": "人物面部偏日式，不符合中国古风气质",
      "fix": "增加 'Chinese donghua style, not Japanese anime' 关键词"
    },
    {
      "version": "v1.1",
      "result_rating": 7.2,
      "issue": "斗气颜色不准确，偏绿色",
      "fix": "明确指定 'blue-orange gradient dou qi, hex #4A90E2'"
    },
    {
      "version": "v1.3",
      "result_rating": 8.5,
      "status": "当前最优版本"
    }
  ]
}
```

### 11.2 失败案例归档

```json
{
  "failure_case_id": "FAIL_003",
  "date": "2024-01-10",
  "shot_id": "DQCK_001_S012",
  "issue_type": "character_inconsistency",
  "description": "生成的萧炎眼睛变成了棕色，不符合设定的漆黑色",
  "root_cause": "提示词中 'dark eyes' 被模型理解为 dark brown",
  "fix_applied": "改为 'pitch black eyes, jet black irises, no brown tones'",
  "result": "修复后通过",
  "prevention": "将此经验加入角色提示词模板的固定写法"
}
```

---

## 12. 技术工具栈建议

### 12.1 推荐工具矩阵

| 环节 | 推荐工具 | 备注 |
|------|---------|------|
| 高光选取 | Claude / GPT-4 | 分析叙事节奏，批量处理章节 |
| 分镜脚本生成 | Claude | 结构化 JSON 输出 |
| 人物图像生成 | Stable Diffusion (ComfyUI) | 可控性最高，LoRA 微调保证一致性 |
| 场景图像生成 | MidJourney | 质量高，适合背景和环境 |
| 视频生成 | Kling AI / Runway Gen-3 | 当前国内方向最优选 |
| 特效叠加 | After Effects / DaVinci Resolve | 斗气特效后期叠加 |
| AI 配音 | 微软 Azure TTS / 剪映 AI 配音 | 情感控制较好 |
| 音效 | 淘声网 + ElevenLabs | 音效库 + AI 生成特殊音效 |
| 后期剪辑 | DaVinci Resolve | 色彩分级最专业 |
| 素材管理 | 自建系统 或 Frame.io | 版本管理和协作 |

### 12.2 角色一致性核心方案

```
最重要的技术问题：如何保证全片萧炎的脸一样？

方案：LoRA 微调
  1. 收集 30-50 张高质量萧炎参考图
  2. 在 Stable Diffusion 上训练专属 LoRA 模型
  3. 所有萧炎相关镜头使用该 LoRA，强度 0.7-0.9

方案：IP-Adapter 参考图控制
  1. 每次生成时附上标准参考图
  2. 使用 IP-Adapter 控制人物外观
  3. 适合快速迭代，不需要训练

建议：先用 IP-Adapter 快速验证，稳定后训练 LoRA 提升质量
```

---

## 附录

### A. 快速参考卡

```
生产前必检查：
  ✓ 确认角色当前状态版本
  ✓ 确认场景所在势力的视觉规范
  ✓ 确认前后分镜的连续性依赖
  ✓ 确认当前场景的情感弧线位置

分镜脚本必包含：
  ✓ 镜头类型 + 运镜方式
  ✓ 角色动作 + 表情 + 情绪强度
  ✓ 光线描述（主光/辅光/逆光）
  ✓ 台词 + 情感标注
  ✓ 音效触发点
  ✓ 与前后分镜的关联

发布前必通过：
  ✓ 角色一致性检查
  ✓ 整体评审 ≥ 80 分
  ✓ 音画同步确认
```

### B. 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.0 | 2024-01 | 初始版本 |

---

*本文档为《斗破苍穹》AI 视频系列生产规范，随项目推进持续更新。*
