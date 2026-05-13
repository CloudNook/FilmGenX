/**
 * 示例 SKILL.md 模板，对应 supervisor sub-agent。
 *
 * 仓库 canonical 版本在 ``docs/skills/examples/*.md``，这份是前端 "新建 Skill" 对话框
 * 的内置快速模板，方便 admin 一键插入起点内容。两份内容应保持同步：
 * 修改其中一份后，把改动同步到另一份（diff 区域很小，按需手工对齐即可）。
 */

export interface SkillSample {
  /** 显示名（dropdown 用） */
  label: string;
  /** sub-agent 归属，仅做展示 */
  targetAgent: string;
  /** 完整 SKILL.md 文本（包含 frontmatter 和 body） */
  markdown: string;
}

const NARRATIVE_STRUCTURE = `---
name: narrative-structure
description: Use when designing story outlines, defining logline / characters / key_arcs, or evaluating narrative pacing. Provides industry-grade story structure systems (Three-Act / Save the Cat 15 beats / Hero's Journey 12 steps / Pixar Story Spine), want-vs-need character arc framework, inciting-incident timing rules, logline 4-element formula, and short-form (≤3min) scaling rules.
target_agents: [outline_agent]
tags: [storytelling, structure, three-act, save-the-cat, hero-journey, character-arc]
author: filmgenx
---

# 剧情结构与叙事工程（Narrative Structure）

业内 story consultant / 编剧顾问的核心命题：**让一个故事在任何长度下都有戏剧能量曲线、主角有 want vs need、配角有功能**。这不是"会讲故事"的问题，是结构工程。本 skill 给 outline_agent 在出 \`\`OutlineOutput\`\` 时一套系统化判断工具：三幕节奏分布、Save the Cat 15 节拍模板、Hero's Journey 12 步、Pixar Story Spine 公式、want vs need 弧线框架、logline 4 要素、以及短剧（≤3 分钟）的缩放规则。

## 核心信条 / 第一原理

业内编剧大师（Robert McKee / Blake Snyder / Joseph Campbell / William Goldman）都遵守的几条铁律：

1. **三幕不是格式问题，是能量分布问题**：Act 1（建置）≈ 25%、Act 2（对抗）≈ 50%、Act 3（解决）≈ 25%。明显失衡 = 节奏崩。短剧按比例缩放但**节拍数不变**——可以削细节，不能削节拍。
2. **Inciting incident 在前 10-15% 必须落地**：观众的耐心窗口是有限的。60 秒短剧里 6-9 秒就必须钩；超过 15% 没钩 = 观众划走。
3. **主角必须有 want vs need 双层欲望**：want（外在目标）推情节，need（内在缺失）决定弧光。只有 want = 流水账；只有 need = 文艺片观众不耐。
4. **每个配角承担功能**：推动 / 对抗 / 反衬 / 见证。功能模糊 = 工具人，砍掉。"群像"≠ "角色多"，"群像" = "每个角色都有功能"。
5. **主题通过情节展开，不在 summary 宣讲**：写"本作探讨自我认同" = 失败。写"主角在追求复仇时发现自己变成了曾经痛恨的人" = 成功——主题是后果，不是宣言。
6. **logline 是制片人的 30 秒决策依据**：4 要素必齐——主角身份 + 外在欲望 + 核心对抗 + 独特风险。模糊形容词（"惊心动魄""扣人心弦"）= 没信息量，扣分。

## 术语词汇表（业内必备）

| 术语 | 含义 | 通用误用纠正 |
|---|---|---|
| **Inciting Incident** | 激励事件，打破主角日常 | 不是"第一个事件"——是**改变主角生活轨迹**的事件 |
| **Plot Point 1 (PP1)** | 第一转折点，主角主动承诺 | 不是"事件发生"——是**主角的决定** |
| **Midpoint (MP)** | 中点反转 | 不是"剧情过半"——是 **fake victory 或 fake defeat**，认知质变 |
| **Plot Point 2 (PP2)** | 第二转折点 | 通常与 All Is Lost 重叠 |
| **All Is Lost / Soul's Dark Night** | 灵魂黑夜 | 主角最接近放弃的时刻 |
| **Climax** | 高潮 | 主角弧线 + 外部目标**双完成** |
| **Denouement / Aftermath** | 落幕 | 不是"结局"——是结局**之后**的新平衡 |
| **Want** | 外在欲望，可被夺走 | 推情节 |
| **Need** | 内在缺失，主角自己不知道 | 决定弧光 |
| **Theme** | 主题 | 通过情节落点浮现，不在台词宣讲 |
| **Setup / Payoff** | 铺垫 / 兑现 | 第一幕埋的钩子，第三幕必须兑现 |
| **Foil character** | 反衬角色 | 用对比凸显主角某个维度 |
| **Cold Open** | 冷开场 | 长片常用——一段紧张场景后才打 title |
| **B-story** | 副线 | 情感线 / 友谊线 / 师徒线，平衡主线压力 |
| **Logline** | 一句话故事 | 25-40 字 4 要素：主角 + 欲望 + 对抗 + 风险 |
| **Save the Cat moment** | 让观众喜欢主角的时刻 | Blake Snyder 命名——开场让主角做件好事 |

## 结构系统配方表（4 套主流模板）

不同题材有自己适用的结构系统——挑一套作为"骨架"，再填具体情节。

### 1. Save the Cat 15 节拍（Blake Snyder，商业类型片最常用）

适合：商业大片 / 类型片 / 偶像剧 / 短视频改编。节奏精确到百分比位置。

| 节拍 | 位置 % | 功能 |
|---|---|---|
| **Opening Image** | 0-1% | 起手画面，与 Final Image 对照 |
| **Theme Stated** | 5% | 配角说出主题，主角不接受 |
| **Setup** | 1-10% | 介绍主角日常 + 缺失 |
| **Catalyst** | 12% | 激励事件 |
| **Debate** | 12-25% | 主角抗拒 |
| **Break Into Two** | 25% | PP1：进入新世界 |
| **B Story** | 30% | 副线登场 |
| **Fun and Games** | 30-55% | "趣味与挑战"段落，节奏放松 |
| **Midpoint** | 50% | Fake Victory 或 Fake Defeat |
| **Bad Guys Close In** | 55-75% | 反派加压 |
| **All Is Lost** | 75% | 主角最低谷 |
| **Dark Night of the Soul** | 75-80% | 灵魂黑夜，主角顿悟 |
| **Break Into Three** | 80% | PP2：找到方法 |
| **Finale** | 80-99% | 高潮 + 最终对抗 |
| **Final Image** | 99-100% | 与 Opening Image 形成镜像 |

### 2. Hero's Journey 12 步（Joseph Campbell / Christopher Vogler）

适合：奇幻 / 玄幻 / 冒险 / 成长故事。强调"主角离开舒适圈 → 蜕变 → 归来"。

| 步骤 | 阶段 | 功能 |
|---|---|---|
| **Ordinary World** | 离开 | 主角日常 |
| **Call to Adventure** | 离开 | 激励事件 |
| **Refusal of the Call** | 离开 | 主角抗拒 |
| **Meeting the Mentor** | 离开 | 导师出现（Yoda / Dumbledore / 药老） |
| **Crossing the Threshold** | 启程 | 进入新世界（PP1） |
| **Tests, Allies, Enemies** | 启程 | 试炼 + 结交盟友 + 树敌 |
| **Approach to the Inmost Cave** | 启程 | 接近核心试炼 |
| **The Ordeal** | 启程 | 重大试炼 / Midpoint |
| **Reward** | 启程 | 获得宝物 / 力量 |
| **The Road Back** | 归来 | 退路被切 / 反派最终加压 |
| **Resurrection** | 归来 | 高潮 / 主角重生 |
| **Return with the Elixir** | 归来 | 带着改变归来 |

### 3. Pixar Story Spine（Pixar 官方公开公式）

适合：短片 / 短剧 / 高节奏故事。Pixar 内部用了 20 年的公式：

\`\`\`
Once upon a time, ___.
Every day, ___.
One day, ___.                   ← Inciting Incident
Because of that, ___.            ← 因果链 1
Because of that, ___.            ← 因果链 2
Because of that, ___.            ← 因果链 3
Until finally, ___.              ← Climax
And ever since then, ___.        ← New Equilibrium
\`\`\`

**关键**：每个 "Because of that" 必须是**直接因果**——前一个事件导致后一个，不是时间顺序的并列。

### 4. 三幕（Aristotle / Robert McKee，所有结构的母体）

最通用的母模板。所有上述模板都是它的细化。

| 幕 | 占比 | 关键节拍 |
|---|---|---|
| **Act 1 - Setup** | 25% | Opening Image / Setup / Inciting Incident / Debate / PP1 |
| **Act 2A - Fun & Games** | 25% | Crossing Threshold / B-Story / Tests / Midpoint |
| **Act 2B - Bad Guys Close In** | 25% | Reversal / All Is Lost / Dark Night |
| **Act 3 - Resolution** | 25% | PP2 / Finale / Climax / Final Image |

## 短剧（≤3 分钟）缩放规则

短剧不是"砍掉中间"，是**按比例缩放**节拍位置，**节拍数不变**：

| 节拍 | 30 秒 | 60 秒 | 90 秒 | 3 分钟 |
|---|---|---|---|---|
| Opening Image | 0-1s | 0-3s | 0-5s | 0-10s |
| **Inciting Incident** | **3-5s** | **6-9s** | **10-15s** | **20-30s** |
| PP1 (Break Into Two) | 7-8s | 15s | 22-25s | 45s |
| Midpoint | 15s | 30s | 45s | 90s |
| All Is Lost | 22-23s | 45s | 65-70s | 135s |
| Climax | 27s | 55s | 80s | 165s |
| Final Image | 29-30s | 58-60s | 88-90s | 175-180s |

**短剧的硬约束**：6-9 秒必须钩到（60 秒版）。任何 setup 在前 10% 必须给出"日常被打破"的信号——否则观众划走。

## Want vs Need 框架

每个真正立得住的主角背两层欲望：

| 维度 | Want（外在欲望） | Need（内在缺失） |
|---|---|---|
| 性质 | 可被夺走、可达成、可放弃 | 主角自己不知道或拒绝承认 |
| 推动 | 推情节 | 决定弧光 |
| 例（萧炎） | 复仇 + 退婚 + 找回家族荣耀 | 接受过去的失败、学会信任伙伴 |
| 例（Walter White） | 攒钱给家人 | 满足自己的支配欲 |
| 例（Frodo） | 把魔戒带到末日山 | 不被权力诱惑 |

判断主角是否成立：能不能用一句话回答"他想要什么，但他真正缺什么"？答不上来 = 主角不立。

## Character Arc 3 种走向（Christopher Vogler 框架）

每个主角必须挑一种 arc 走向：

### Positive Arc（正向弧线 / 成长）

\`\`\`
主角持有错误信念 → 在追求 want 中被逐渐击碎 → 接受真相 (need) → 行动改变 → 战胜反派
\`\`\`

- 适合：英雄之旅 / 成长故事 / 商业大片
- 例：Luke Skywalker / Harry Potter / 萧炎 / 千寻

### Flat Arc（平面弧线 / 立场坚守）

\`\`\`
主角已持有真理 (need 已具备) → 用真理改变世界 → 让反派 / 盟友最终认同
\`\`\`

- 适合：偶像剧 / 奇幻原型 / 动漫主角 / 经典英雄
- 例：Captain America / Superman / Indiana Jones / 大圣

### Negative Arc（负向弧线 / 走向毁灭）

\`\`\`
主角持有错误信念 → 拒绝真相 → 拥抱谎言 → 走向毁灭
\`\`\`

- 适合：悲剧 / 犯罪片 / 反英雄 / 心理惊悚
- 例：Walter White / Michael Corleone / Anakin Skywalker / Macbeth

## 配角功能性 4 类

每个配角必须承担**至少一种**功能——功能模糊砍掉：

| 功能 | 含义 | 典型 |
|---|---|---|
| **Driver（推动）** | 制造剧情拐点 | 导师 / 委托人 / 信使 |
| **Antagonist（对抗）** | 制造障碍 | 反派 / 内部矛盾 / 制度压力 |
| **Foil（反衬）** | 用对比凸显主角某维度 | 同伴 / 镜像角色 / 竞争对手 |
| **Witness（见证）** | 观察并放大主角的变化 | 朋友 / 旁观者 / 副驾驶 |

例（《指环王》Frodo 团队）：Gandalf = Driver、Sauron = Antagonist、Sam = Foil（衬托 Frodo 的脆弱）、Aragorn = 多功能（Driver + Witness）。

## Logline 心法（25-40 字 4 要素公式）

写到让一个不认识你的制片人 30 秒内决定要不要看下去：

\`\`\`
[主角身份] + [外在欲望] + [核心对抗] + [独特风险]
\`\`\`

| 例 | 拆解 |
|---|---|
| "被废柴标签压了三年的萧炎，在斗气大陆复活药老的灵魂、向悔婚的纳兰嫣然讨回三年前那场约定" | 主角=被废柴标签压三年的萧炎 / 欲望=复活药老 + 讨回约定 / 对抗=悔婚的纳兰嫣然 / 风险=三年前的尊严 |
| "一个化学老师被诊断癌症晚期，决定靠制毒养活家人，却在地下世界一步步变成自己最痛恨的人" | 主角=化学老师 / 欲望=养活家人 / 对抗=地下世界 / 风险=变成自己痛恨的人 |
| "九岁的男孩被困在 Ghibli 异世界，必须在三天内救出被变成猪的父母，否则永远留在那里" | 主角=九岁男孩 / 欲望=救父母 / 对抗=Ghibli 异世界规则 / 风险=三天 + 永远留下 |

**反例**：

- ❌ "一个落魄少年踏上扣人心弦的修仙之旅"（含模糊形容词，4 要素全缺）
- ❌ "讲述了主角如何战胜反派的故事"（语义空，没有具体信息）

## 反例 / 陷阱

### ❌ 反例 1：Inciting Incident 太晚

60 秒短剧里，30 秒才发生激励事件——观众早就划走了。

**正例**：60 秒短剧的 Inciting Incident 必须在 6-9 秒落地（10-15% 位置）。

### ❌ 反例 2：主角没 Need

\`\`\`
"主角想要救出公主，最终成功了"
\`\`\`

**后果**：只有 want 没有 need，结局只能"赢了"，没有"长大了"——观众感觉空。

**正例**：

\`\`\`
"主角想要救出公主（want），但他真正缺的是承认自己的恐惧（need）。
旅程中他必须先面对自己的怯懦，才能真正解救公主。"
\`\`\`

### ❌ 反例 3：Midpoint 没反转

\`\`\`
"第二幕中段：主角继续追击反派"
\`\`\`

**后果**：没有认知质变 / fake victory / fake defeat → 二幕松散。

**正例**：

\`\`\`
"第二幕中段：主角发现一直追击的反派其实是自己失踪多年的兄长（fake victory：
找到亲人；fake defeat：必须杀亲人才能完成任务）"
\`\`\`

### ❌ 反例 4：高潮靠外部力量解决

\`\`\`
"反派被神兵天降的盟友击败"
\`\`\`

**后果**：主角弧线没完成 → 观众感觉欺骗 / Deus ex machina。

**正例**：主角必须**亲自**用整个故事学到的东西击败反派（即使盟友辅助）。

### ❌ 反例 5：主题宣讲

\`\`\`
"summary: 本作探讨了自我认同、亲情、与时代变迁的关系。"
\`\`\`

**后果**：主题悬空——summary 写了，但情节里看不到落点。

**正例**：主题**通过情节展开**：

\`\`\`
"summary: 一个青年返乡参加爷爷葬礼，在整理遗物时发现爷爷年轻时曾是地下反抗组织
成员。在与现实生活的功利父亲的争吵中，他逐渐重新理解'家族'的意义。"
\`\`\`

主题（自我认同 / 亲情 / 时代）全在情节里，没一个字宣讲。

### ❌ 反例 6：logline 含模糊形容词

\`\`\`
"一个落魄少年踏上扣人心弦的修仙之旅"
\`\`\`

**正例**：

\`\`\`
"被废柴标签压了三年的萧炎，在斗气大陆复活药老的灵魂、向悔婚的纳兰嫣然讨回
三年前那场约定"
\`\`\`

### ❌ 反例 7：配角是工具人

剧本里 5 个配角，砍掉任意一个不影响剧情 → 配角没功能。

**正例**：每个配角对应 Driver / Antagonist / Foil / Witness 中至少一种功能。

## 何时加载附加资料

按以下规则**按需**触发工具调用：

- 想用 Save the Cat 完整 15 节拍模板写大纲 → 加载 @ref:save-the-cat-15-beats
- 想用 Hero's Journey 完整 12 步写大纲（适合奇幻 / 玄幻题材） → 加载 @ref:hero-journey-12-steps
- 想看 Character Arc 三种走向的完整对照（含每幕的具体心理变化） → 加载 @ref:character-arc-frameworks
- 短剧（≤3 分钟）的节拍缩放具体到秒 → 加载 @ref:short-form-pacing-table

## reference: save-the-cat-15-beats

Blake Snyder 完整 15 节拍模板（每节拍含 position % + 功能 + 经典案例 + 短剧缩放版）。

### 1. Opening Image（0-1%）

起手画面。一张图能传达全片基调。必须与 Final Image 形成镜像（开场颓废→结尾振作 / 开场孤独→结尾团圆）。

短剧（60s）：0-1s。

### 2. Theme Stated（5%）

配角用一句话说出主题，主角**不接受 / 反驳 / 嘲笑**。例：母亲对孩子说"你最大的问题是你怕自己输"——主角嗤之以鼻。这句话会在 Climax 时回响。

短剧（60s）：3s。

### 3. Setup（1-10%）

介绍主角的"日常"——同时埋下他缺什么。例：Walter White 第一集开场，灰头土脸地教高中化学（专业被低估 = need：被认可）。

短剧（60s）：0-6s。

### 4. Catalyst（12%）

激励事件。打破主角日常的具体事件。**外部触发**，不是主角主动。

短剧（60s）：6-8s。

### 5. Debate（12-25%）

主角抗拒新方向。问"我能行吗？""值得吗？""真的要去吗？"

短剧（60s）：8-15s。

### 6. Break Into Two / PP1（25%）

主角**主动**承诺。这是主角的决定，不是被动接受。

短剧（60s）：15s。

### 7. B Story（30%）

副线登场。通常是爱情 / 友谊 / 师徒线。用来在主线压力下给观众喘息。

短剧（60s）：18s。

### 8. Fun and Games（30-55%）

"承诺前提的兑现"。这段是观众买票的原因——电影海报上的画面都在这里。节奏可以松。

短剧（60s）：18-33s。

### 9. Midpoint（50%）

Fake Victory 或 Fake Defeat。看似主角赢了 / 失败了，但其实情况要恶化 / 反转。**认知质变发生**——主角开始意识到内心的 need。

短剧（60s）：30s。

### 10. Bad Guys Close In（55-75%）

反派加压。外部威胁升级 + 内部团队瓦解。压力 max。

短剧（60s）：33-45s。

### 11. All Is Lost（75%）

主角最低谷。失去 want + 失去盟友 + 看似无望。通常伴随"死亡气息"（死人 / 失去亲人 / 自己濒死）。

短剧（60s）：45s。

### 12. Dark Night of the Soul（75-80%）

灵魂黑夜。主角独处、思考、顿悟——重新接触 Theme Stated 那句话。

短剧（60s）：45-48s。

### 13. Break Into Three / PP2（80%）

主角找到方法 / 决定回去战斗。need 已经被承认，want 重新被定义。

短剧（60s）：48s。

### 14. Finale（80-99%）

高潮 + 最终对抗。主角**亲自**用整个故事学到的东西击败反派。

短剧（60s）：48-58s。

### 15. Final Image（99-100%）

落幕画面。与 Opening Image 形成镜像——展示主角已经改变。

短剧（60s）：58-60s。

## reference: hero-journey-12-steps

Christopher Vogler 完整 12 步（基于 Joseph Campbell）。适合奇幻 / 玄幻 / 冒险题材。

### 1. Ordinary World（日常世界）

主角的舒适圈。例：Luke 在 Tatooine 农场、Frodo 在 Shire、萧炎在乌坦城。

### 2. Call to Adventure（冒险召唤）

激励事件。R2-D2 带来信息、Gandalf 来访、家族危机。

### 3. Refusal of the Call（拒绝召唤）

主角抗拒。Luke 不愿离开叔叔、Frodo 想把魔戒留下、萧炎质疑能否复出。

### 4. Meeting the Mentor（遇见导师）

导师出现，给予指引或宝物。Obi-Wan / Gandalf / 药老 / Mr. Miyagi。

### 5. Crossing the Threshold（跨越门槛 / PP1）

主角进入新世界。Luke 离开 Tatooine、Frodo 离开 Shire、萧炎离开家族。

### 6. Tests, Allies, Enemies（试炼 / 盟友 / 敌人）

进入新世界后的初步适应。结交盟友（Han Solo / Sam / 林动），树敌（Vader / Saruman / 纳兰嫣然）。

### 7. Approach to the Inmost Cave（接近核心）

接近最大试炼。死星 / 末日山 / 加玛帝国宫殿。

### 8. The Ordeal（重大试炼 / Midpoint）

主角面对生死时刻。Luke 在死星垃圾压缩机、Frodo 被 Shelob 蛰、萧炎与师叔的生死对决。

### 9. Reward（奖励）

获得宝物 / 力量 / 真相。星图 / 戒指持续 / 新功法。

### 10. The Road Back（归路 / PP2）

退路被切 + 反派最终加压。死星追击 / Mordor 围困 / 加玛帝国全面追杀。

### 11. Resurrection（重生 / Climax）

主角"死而复生"。心理上或字面上的死亡 → 重生 → 成为完全体。Luke 关闭瞄准器用 Force / Frodo 抵抗魔戒诱惑 / 萧炎觉醒帝炎之力。

### 12. Return with the Elixir（带着宝物归来）

带着改变归来。新的能力 / 新的真相 / 新的家族。

## reference: character-arc-frameworks

完整 3 种 Character Arc 的对照表。

### Positive Arc（成长 / 觉醒）

| 幕 | 主角心理状态 | 外部表现 |
|---|---|---|
| Act 1 | 持错误信念（lie），追求 want | 拒绝改变 |
| Act 2A | want 在 lie 框架下推进 | 表面成功，内核失败 |
| Midpoint | lie 第一次被挑战 | 开始怀疑自己 |
| Act 2B | lie vs need 内部冲突 | 行为开始分裂 |
| All Is Lost | lie 完全崩塌 | 失去一切 |
| Act 3 | 接受 need（truth） | 行动改变，整合外内 |
| Climax | 用 truth 击败反派 | want + need 双完成 |

代表作：Luke Skywalker / Harry Potter / 萧炎 / Walter White（前期）

### Flat Arc（立场坚守 / 改变世界）

| 幕 | 主角心理状态 | 外部表现 |
|---|---|---|
| Act 1 | 已持 truth | 不被理解 / 不被信 |
| Act 2A | 试图用 truth 影响他人 | 部分人接受 / 部分人拒绝 |
| Midpoint | truth 受到最强考验 | 主角必须坚持 |
| Act 2B | 反派用 lie 压制 | 主角动摇但不放弃 |
| All Is Lost | truth 似乎失败 | 但仍坚守 |
| Act 3 | 用 truth 行动 | 让世界（或反派）认同 |
| Climax | truth 胜利 | 世界改变 |

代表作：Captain America / Superman / Indiana Jones / Mr. Miyagi

### Negative Arc（走向毁灭）

| 幕 | 主角心理状态 | 外部表现 |
|---|---|---|
| Act 1 | 持 lie | 与 truth 隔绝 |
| Act 2A | 在 lie 框架下追求 want | 表面成功 |
| Midpoint | truth 出现机会 | 主角拒绝 |
| Act 2B | 拥抱更深的 lie | 行为越来越极端 |
| All Is Lost | 失去 truth 最后机会 | 走向自毁 |
| Act 3 | 完全拥抱 lie | 毁灭 |
| Climax | 自我毁灭 / 道德破产 | want 实现但代价巨大 |

代表作：Macbeth / Walter White（后期）/ Anakin Skywalker / Michael Corleone

## reference: short-form-pacing-table

短剧（≤3 分钟）的节拍位置秒数表。Save the Cat 15 节拍按短剧时长缩放：

| 节拍 | 30s | 45s | 60s | 75s | 90s | 120s | 150s | 180s |
|---|---|---|---|---|---|---|---|---|
| Opening Image | 0-0.3s | 0-0.5s | 0-1s | 0-1s | 0-1s | 0-2s | 0-2s | 0-3s |
| Theme Stated | 1.5s | 2s | 3s | 4s | 5s | 6s | 8s | 9s |
| Setup | 0-3s | 0-5s | 0-6s | 0-8s | 0-9s | 0-12s | 0-15s | 0-18s |
| **Catalyst (Inciting)** | **3-5s** | **5-7s** | **6-9s** | **8-11s** | **10-15s** | **14-20s** | **17-25s** | **20-30s** |
| Debate | 5-7s | 7-11s | 9-15s | 11-19s | 15-22s | 20-30s | 25-37s | 30-45s |
| **Break Into Two (PP1)** | **7.5s** | **11s** | **15s** | **19s** | **22s** | **30s** | **37s** | **45s** |
| B Story | 9s | 13s | 18s | 22.5s | 27s | 36s | 45s | 54s |
| Fun and Games | 9-16s | 13-25s | 18-33s | 22-41s | 27-49s | 36-66s | 45-82s | 54-99s |
| **Midpoint** | **15s** | **22s** | **30s** | **37s** | **45s** | **60s** | **75s** | **90s** |
| Bad Guys Close In | 16-22s | 25-33s | 33-45s | 41-56s | 49-67s | 66-90s | 82-112s | 99-135s |
| **All Is Lost** | **22s** | **33s** | **45s** | **56s** | **67s** | **90s** | **112s** | **135s** |
| Dark Night | 22-24s | 33-36s | 45-48s | 56-60s | 67-72s | 90-96s | 112-120s | 135-144s |
| **Break Into Three (PP2)** | **24s** | **36s** | **48s** | **60s** | **72s** | **96s** | **120s** | **144s** |
| Finale | 24-29s | 36-44s | 48-58s | 60-73s | 72-88s | 96-117s | 120-146s | 144-176s |
| Final Image | 29-30s | 44-45s | 58-60s | 73-75s | 88-90s | 117-120s | 146-150s | 176-180s |

**关键铁律**：
- **Inciting Incident（Catalyst）必须在 10-15% 位置**——观众的钩子窗口
- **Midpoint 必须在 50% 位置**——节奏锚点
- **Climax 必须在 80-95% 位置**——给落幕留空间
- 短剧（≤30s）允许压缩 Setup / Debate / Fun and Games，**但 Inciting / Midpoint / Climax 三个锚点位置不可妥协**
`;

const DIALOGUE_CRAFT = `---
name: dialogue-craft
description: Use when writing scene dialogue, designing scene structure (5-piece test), or evaluating script craft. Provides subtext techniques (8 methods), character voice differentiation tests, on-the-nose pitfall library, 5-piece scene test (why / in-beat / conflict / turn / out-beat), parenthetical discipline, scene heading spec, and master-anchored dialogue styles (Sorkin walk-and-talk / Mamet staccato / Tarantino monologue / Kaufman meta).
target_agents: [script_agent]
tags: [dialogue, scriptwriting, subtext, voice, scene-structure, screenwriting]
author: filmgenx
---

# 对白工艺与场景写作（Dialogue Craft）

业内编剧（William Goldman / Aaron Sorkin / David Mamet / Charlie Kaufman / Robert McKee）的核心命题：**让每一句台词都服务角色塑造、推进冲突、或埋伏后续情节——没一句是"自然对话"**。本 skill 给 script_agent 写场景时一套系统化工具：场景 5 件套结构、潜台词 8 种手法、对白角色化测试、parenthetical 纪律、scene heading 行业规范，以及大师风格锚点。

## 核心信条 / 第一原理

业内编剧大师都遵守的几条铁律：

1. **拍得出 vs 拍不出**：剧本是给摄影机和演员看的指令。"她内心挣扎" = 拍不出，必须改成动作（"她攥紧手机，三次想拨号都按到一半就退出"）。所有"心理 / 抽象 / 状态"必须转化为镜头能捕捉的外部信号。
2. **对白角色化是分水岭**：把所有人对白互换位置——**没有任何违和感** = 角色化失败。盲读测试是基本功。
3. **每场戏都要回答 5 个问题**：why（存在理由）/ in-beat（开场情绪）/ conflict（冲突核心）/ turn（场内转折）/ out-beat（收尾状态）。少一件 = 过渡场，砍掉或合并。
4. **Show, don't tell**：信息通过冲突 / 动作 / 反应释放，不通过角色互相讲对方已知的事释放。"As you know, Bob..." = 信息倾倒，业内最大忌讳。
5. **潜台词驱动意义**：角色说 A 实指 B。"我没事" + 攥拳 = 我有事。直白宣告 = 没戏可拍。
6. **Parenthetical 是不信任演员的标志**：(angry) (crying) (softly) 演员能从台词推断的情绪一律不写。

## 术语词汇表（业内必备）

| 术语 | 含义 | 通用误用纠正 |
|---|---|---|
| **Subtext** | 潜台词，说 A 实指 B | 不是"暗示"——是**台面 vs 心里**的精确错位 |
| **On-the-nose** | 直白如鼻头一样明显 | 业内最大对白忌讳——把心理活动直说 |
| **Exposition** | 说明性信息释放 | 不可避免，但必须**通过冲突包装** |
| **Beat** | 戏剧节拍 / 情绪转折点 | 一场戏典型 3-5 beats，beats 间是 micro-shifts |
| **Walla** | 背景闲聊声 / 群众杂音 | 写 \`\`(walla)\`\` 表示背景声场 |
| **OS** | Off Screen，画面外但同场景 | 角色不在画面但在场 |
| **VO** | Voice Over，画外音 | 旁白 / 内心独白 / 电话另一端 |
| **Slug line / Scene Heading** | 场景头 | \`\`INT. LOCATION - TIME\`\` |
| **Action line** | 动作描写 | 只写镜头看得见的 |
| **Parenthetical** | 表演提示 \`\`(angry)\`\` | **克制使用** |
| **Wryly** | 一种特殊 parenthetical | 反讽 / 内心相反语气 |
| **CONT'D** | 同角色连续台词 | 中间被 action line 打断 |
| **MORE** | 台词跨页 | 行业格式标记 |
| **Cold open** | 冷开场 | 不打片头直接进戏，HBO 模式 |
| **5 件套** | scene 必备 5 要素 | why / in-beat / conflict / turn / out-beat |

## 场景 5 件套测试（每场戏必过）

一场合格的戏必须能回答这 5 个问题。少一件 = 大概率是过渡场。

| 件 | 问题 | 例（《教父》开场，殡仪馆主求 Vito 复仇） |
|---|---|---|
| **1. Why（存在理由）** | 这场戏推进了哪个 key_arc？砍掉它，剧情塌不塌？ | 介绍 Vito 的权威 + 立"Family is everything"主题 |
| **2. In-beat（开场情绪）** | 进入时角色处于什么情绪？观众看到什么画面？ | Bonasera 卑微请求，Vito 漠然听完 |
| **3. Conflict（冲突核心）** | 场内的张力来源？外部冲突还是内部冲突？ | 价值观冲突——Bonasera 要的是钱 / Vito 要的是 respect |
| **4. Turn（场内转折）** | 场内有没有信息 / 情绪 / 处境的小翻转？ | Vito 拒绝纯交易，但 Bonasera 跪下、亲手吻 ring → 关系反转 |
| **5. Out-beat（收尾状态）** | 以什么状态收尾？留白 / 推到下场 / 反差 cut？ | Vito 派 Tom 安排"after the funeral"——直接推到下一场暗杀 |

**5 件全有 → 这场是肉戏**。少一件 → 高概率是过渡场，考虑合并。

## 角色化对白测试（互换违和测试）

最简单的角色化测试：**把所有人对白互换位置**——如果没违和感，角色化失败。

角色化稳定要在三层都立得住：

| 层 | 测试 | 例 |
|---|---|---|
| **词汇层** | 选词反映身份 | 江湖人不说"原来如此"，他说"我懂了"；学者不说"卧槽"，她说"这就有意思了" |
| **节奏层** | 句长 / 停顿 / 抢话 | 急躁的人句短抢话；老成的人句长停顿用比喻 |
| **价值观层** | 面对同一信息反应不同 | 同一个坏消息——务实者问"下一步怎么办"，理想主义者问"这怎么可能" |

价值观层最难也最值钱——这一层做到位，角色互换必违和。

## 潜台词 8 种手法（业内经典）

潜台词不是"暗示"，是**精确的台面 vs 心里错位**。8 种业内常用手法：

### 1. Deflection（偏移）

角色不直接回答，转移话题或反问。

\`\`\`
A: 你昨晚在哪里？
B: 你今天的咖啡又没加糖吧。
\`\`\`
潜台词：B 在隐瞒，但不愿正面对抗。

### 2. Hyper-politeness（过度礼貌）

强调礼节往往暗示敌意 / 距离。

\`\`\`
"如果不太麻烦您的话，能否劳驾把那份文件递给我。"
\`\`\`
潜台词：愤怒被压抑成形式礼仪。

### 3. Silence（沉默 / Beat）

没有回答 = 最强的回答。剧本里写 \`\`(beat)\`\` 或 \`\`(...)\`\` 让演员表演。

\`\`\`
A: 你还爱我吗？
B: (beat)
B: ...我去做晚饭了。
\`\`\`

### 4. Displacement（第三方代言）

角色通过谈第三人谈自己。

\`\`\`
"我隔壁那个女人啊，她丈夫一直骗她。她明明知道，但就是不肯走。"
\`\`\`
潜台词：说话者在说自己。

### 5. Wryly（反讽 / 言不由衷）

字面意思与真实意思相反，靠语境揭示。

\`\`\`
(他拿到 90 分，妈妈说)
妈：真行啊你。
(她接过满分卷子，丈夫递过来花)
妻：谢谢，真是惊喜。
\`\`\`

### 6. Overlap（抢话 / 打断）

\`\`\`
A: 我觉得我们应该——
B: ——不应该。
A: ——你都没听我说完！
B: 不用听。
\`\`\`
潜台词：B 不愿与 A 平等对话 / B 已下定决心。

### 7. Repetition（重复词）

同一个词反复出现 = 心结。

\`\`\`
A: 你父亲怎么样了？
B: 他还好。
A: 他真的还好？
B: 他还好。我说了，他还好。
\`\`\`
潜台词："还好"重复 4 次 = 一点都不好。

### 8. Specific Detail（具体细节）

通过反常具体的细节传情绪——大事用小细节包装。

\`\`\`
(妻子刚得知丈夫出轨)
妻：番茄炒蛋的鸡蛋你要打几个？
夫：随便。
妻：上次你说三个。
夫：那就三个。
妻：上次是三个。
\`\`\`
潜台词：妻子心碎，但用细节平静地凝视。

## 对白节奏的大师风格（4 大流派）

业内有 4 种典型对白节奏，按你的题材选一种作为锚：

### Sorkin Style（Aaron Sorkin / 节奏快、长句、Walk-and-talk）

- **特征**：长句、信息密度高、辞藻华丽、节奏快、信任观众智商
- **句长**：通常 15-30 字
- **机位**：常配 walk-and-talk 跟拍
- **代表**：《The West Wing》《The Social Network》《A Few Good Men》
- **适合**：政治剧 / 法庭戏 / 高智商对峙 / 行业剧

\`\`\`
"You want answers?"
"I think I'm entitled."
"You want answers?"
"I want the truth!"
"You can't handle the truth!"
\`\`\`

### Mamet Style（David Mamet / 短促、爆破、Staccato）

- **特征**：短句、断片、重复、底层粗粝感
- **句长**：通常 3-8 字，常被打断
- **代表**：《Glengarry Glen Ross》《American Buffalo》《House of Games》
- **适合**：底层 / 黑帮 / 商场 / 高压谈判 / 罪案剧

\`\`\`
A: Where's the meeting?
B: The meeting?
A: The meeting.
B: Tomorrow.
A: Tomorrow when?
B: Tomorrow tomorrow.
\`\`\`

### Tarantino Style（Quentin Tarantino / 长 Monologue、流行文化、看似离题）

- **特征**：长独白、流行文化引用、看似离题实则伏笔、对峙前的废话
- **代表**：《Pulp Fiction》《Inglourious Basterds》《Reservoir Dogs》
- **适合**：黑色喜剧 / 类型混搭 / 长场对峙 / 风格化罪案

### Kaufman Style（Charlie Kaufman / 元叙事、心理化）

- **特征**：自指 / 元叙事 / 内心活动外化为台词 / 现实与潜意识混合
- **代表**：《Being John Malkovich》《Eternal Sunshine》《Synecdoche, NY》
- **适合**：文艺 / 心理 / 实验性叙事

## Scene Heading（场景头）行业规范

标准格式（严格遵守，全片同名地点字符串一致）：

\`\`\`
{SPACE} {LOCATION} - {TIME_OF_DAY}

INT. 咖啡馆 - 日
EXT. 云岚宗山门 - 夜
INT./EXT. 出租车 - 日 - 行驶中
\`\`\`

**SPACE 类型**：
- \`\`INT.\`\` = Interior（室内）
- \`\`EXT.\`\` = Exterior（室外）
- \`\`INT./EXT.\`\` = 混合（车内向外拍 / 阳台 / 门厅）

**TIME_OF_DAY 业内通用词**：
- \`\`DAY\`\` / \`\`NIGHT\`\` / \`\`DAWN\`\` / \`\`DUSK\`\`
- \`\`MORNING\`\` / \`\`AFTERNOON\`\` / \`\`EVENING\`\`
- \`\`CONTINUOUS\`\` = 紧接前场连续动作
- \`\`LATER\`\` = 同地点稍后
- \`\`MOMENTS LATER\`\` = 同地点几分钟后
- \`\`SAME\`\` = 同时刻不同地点

**铁律**：同一物理地点跨场出现时，LOCATION 字符串**一字不差**——"云岚宗广场" ≠ "云岚宗·广场" ≠ "云岚宗 广场"。下游 scene_ref_agent 按 location 去重出图，拼写漂移 = 多出场景图浪费额度。

## Parenthetical 纪律

(angry) (crying) (softly) 这种表演提示——演员能从台词推断的情绪**不写**。只在以下 3 种情况写：

### 1. 与字面意思相反的潜台词

\`\`\`
A
(嘲讽)
你真行啊。
\`\`\`

### 2. 关键动作伴随的语调变化

\`\`\`
A
(放下笔)
我不会签的。
\`\`\`

### 3. 容易被误读的语义分叉

\`\`\`
A
(认真)
我不是开玩笑的。
\`\`\`

**业内反例**：

\`\`\`
A
(angry)
I hate you!
\`\`\`

→ 演员看到 "I hate you" 自然就会演愤怒。写 (angry) = 不信任演员。

## "拍得出"测试（所有描写都过这一关）

| 写法 | 测试 | 结论 |
|---|---|---|
| "她内心挣扎" | 镜头能拍到吗？ | ❌ 拍不出 |
| "她攥紧手机，三次想拨号都按到一半就退出" | 镜头能拍到吗？ | ✅ 可拍 |
| "他陷入回忆" | 镜头能拍到吗？ | ❌ 拍不出 |
| "他翻开抽屉，那张老照片还在" | 镜头能拍到吗？ | ✅ 可拍 |
| "气氛变得紧张" | 镜头能拍到吗？ | ❌ 拍不出 |
| "桌上的酒杯停在半空，没人动筷" | 镜头能拍到吗？ | ✅ 可拍 |

**所有"心理 / 抽象 / 状态"都要转化为镜头能捕捉的外部信号**。这是剧本第一性原理。

## 决策树：你最常遇到的分叉

- **对白还是动作传递信息** → 优先动作；动作做不到时再上对白；对白做不到时才用旁白（短片基本不用旁白）
- **长场（>2 页）还是切短场** → 紧张戏 / 信息高密度戏切短场链；抒情戏 / 关系戏可以走长场单镜
- **闪回放不放** → 只在"现在的角色行动需要这段过去信息支撑"时放；其他时候用一个细节（道具 / 一句话）暗示就够
- **同一信息要不要重复释放** → 重要信息至少 setup + payoff 两次；setup 时不显眼，payoff 时观众恍然大悟
- **场太多** → key_arc 1 通常 1-2 场，key_arc 2-3 各 2-3 场，高潮 1-2 场。超出就压缩或合并

## 反例 / 陷阱

### ❌ 反例 1：信息倾倒式对话（"As you know, Bob..."）

\`\`\`
A: 你知道我父亲三年前死了吗？
B: 嗯，我们一起参加的葬礼。
\`\`\`

**后果**：两个角色互相讲对方早知道的事 → 纯为观众解释 → 业内最大忌讳。

**正例**：信息**通过冲突释放**——

\`\`\`
A：(打开抽屉，发现父亲的怀表)
B：你已经三年没碰这个了。
A：(把怀表放回去) 关你什么事。
\`\`\`

（父亲三年前死了的信息通过怀表 + 三年的台词带出来，而非直说。）

### ❌ 反例 2：On-the-nose（直白如鼻头）

\`\`\`
A: 我心里很难过，因为我害怕失去你。
\`\`\`

**后果**：把心理活动直说 → 没戏可拍。

**正例**：

\`\`\`
A: (看着她整理行李) 你的红色羊毛衫忘了。
B: 我不冷。
A: ...还是带上吧。
\`\`\`

（害怕失去通过"还是带上吧"和细节传递。）

### ❌ 反例 3：角色互换无违和

剧本写了 5 个角色对白，把任意两个角色的台词位置互换 → 戏不变 → 角色化失败。

**正例**：每个角色在词汇 / 节奏 / 价值观三层都立得住——互换必违和。

### ❌ 反例 4：滥用 parenthetical

\`\`\`
A
(angrily)
I hate you!

B
(sadly)
Don't say that.

A
(crying)
But it's true!
\`\`\`

**后果**：演员能从台词推断的情绪全被写出来 → 不信任演员。

**正例**：删掉所有不必要的 parenthetical，只在反讽 / 关键动作 / 易误读时保留。

### ❌ 反例 5：场景头漂移

剧本里同一地点写法不一致：
- Scene 3: "云岚宗广场"
- Scene 7: "云岚宗·广场"
- Scene 12: "云岚宗 广场"

**后果**：scene_ref_agent 当成 3 个不同 location → 多出 3 套场景图 → 浪费额度 + 全片场景撕裂。

**正例**：全片同名 LOCATION 字符串**一字不差**。

### ❌ 反例 6：场景没存在理由

\`\`\`
SCENE 5
INT. 咖啡馆 - 日
A 和 B 喝咖啡，聊昨天的天气。
\`\`\`

**后果**：砍掉这场，剧情不塌 → 过渡场。

**正例**：每场必须能回答 5 件套——why / in-beat / conflict / turn / out-beat。

### ❌ 反例 7：超长独白无戏剧理由

主角连讲 6 行台词解释自己的过去 → 信息倾倒。

**正例**：长独白只在 3 种情况合理：
1. 演讲 / 庭审 / 公开发言（场合本身合理化）
2. 自白 / 临终告解（情绪 max 时刻）
3. 对峙中一方占绝对优势压制另一方（Tarantino style）

### ❌ 反例 8：心理活动外化为旁白

\`\`\`
VO: 我感到害怕，但我必须坚强。
\`\`\`

**后果**：旁白讲心理 = 偷懒。短片基本不用旁白。

**正例**：用动作表达——\`\`(她深吸一口气，三次想转身都强迫自己向前走)\`\`

## 何时加载附加资料

- 想看 8 种潜台词的完整范例库（含影视片段引用） → 加载 @ref:subtext-techniques
- 不确定 scene heading 格式 / 时间词 / OS / VO / CONT'D / MORE 等专业标记 → 加载 @ref:scene-format-spec
- 4 种大师对白风格的细化（Sorkin / Mamet / Tarantino / Kaufman 各自具体节奏特征） → 加载 @ref:dialogue-master-styles
- 不同 emotion 怎么通过具体细节传递（业内 "specific detail" 库） → 加载 @ref:specific-detail-cookbook

## reference: subtext-techniques

完整 8 种潜台词手法 + 影视片段引用 + 适用场景。

### 1. Deflection（偏移 / 转移话题）

**手法**：角色不正面回答，反问 / 转移 / 谈别的。

**适用**：隐瞒、不愿对抗、关系僵化。

**例**（《Mad Men》）：
\`\`\`
Betty: Where were you last night?
Don: I don't know what you're talking about.
Betty: That's not an answer.
Don: It's the only one I have.
\`\`\`

### 2. Hyper-politeness（过度礼貌）

**手法**：用过度的礼仪表达敌意 / 距离。

**适用**：上下级冲突、家庭冷战、敌意被压抑的场合。

**例**（《Downton Abbey》）：
\`\`\`
Lady Mary：(冷冷地) 谢谢您的关心，Lord Grantham.
\`\`\`

### 3. Silence / Beat（沉默）

**手法**：没有回答 = 最强的回答。\`\`(beat)\`\` 或 \`\`(...)\`\` 让演员演。

**适用**：背叛揭露、求婚被拒、谎言被戳穿。

**例**（《Breaking Bad》）：
\`\`\`
Skyler: You're a drug dealer?
Walter: (beat)
Walter: Skyler...
\`\`\`

### 4. Displacement（第三方代言）

**手法**：通过谈第三人谈自己。

**适用**：自我难以面对的事 / 防御机制 / 自我投射。

**例**：
\`\`\`
A: 我有个朋友啊，他老婆每天加班到深夜，他怀疑她出轨，又不敢问。你说他该怎么办？
\`\`\`

### 5. Wryly / Verbal Irony（反讽）

**手法**：字面意思与真实意思相反。

**适用**：被动攻击 / 自嘲 / 嘲讽。

**例**：
\`\`\`
妈：你拿了 90 分啊，真行。
\`\`\`

### 6. Overlap / Interruption（抢话 / 打断）

**手法**：角色互相打断、抢话。

**适用**：争吵、不耐烦、权力压制、亲密关系（爱情戏的"互相完句"也算）。

**例**（《His Girl Friday》Howard Hawks 标志手法）：
\`\`\`
A: I think we should——
B: ——don't think.
A: ——you haven't even let me——
B: I don't need to.
\`\`\`

### 7. Repetition（重复词）

**手法**：同一个词反复出现 = 心结所在。

**适用**：心理创伤、强迫思维、被遮掩的真相。

**例**：
\`\`\`
A: 他没事吧？
B: 他没事。
A: 真的没事？
B: 我说了，他没事。他没事。
\`\`\`

### 8. Specific Detail（具体细节）

**手法**：大事用小细节包装。表面平静、细节中传爆炸性情绪。

**适用**：丧亲、出轨、绝症、巨变后的"震后平静"。

**例**：
\`\`\`
(妻子刚得知丈夫出轨)
妻：番茄炒蛋的鸡蛋你要打几个？
夫：随便。
妻：上次你说三个。
夫：那就三个。
妻：上次是三个。
\`\`\`

## reference: scene-format-spec

完整 scene heading 行业规范 + 所有专业标记。

### 场景头格式

\`\`\`
{SPACE} {LOCATION} - {TIME_OF_DAY}
\`\`\`

**SPACE**：
- \`\`INT.\`\` = Interior 室内
- \`\`EXT.\`\` = Exterior 室外
- \`\`INT./EXT.\`\` = 混合（车内向外、阳台、门廊）

**TIME_OF_DAY**：
- \`\`DAY\`\` / \`\`NIGHT\`\` / \`\`DAWN\`\`（黎明）/ \`\`DUSK\`\`（黄昏）
- \`\`MORNING\`\` / \`\`AFTERNOON\`\` / \`\`EVENING\`\`
- \`\`CONTINUOUS\`\` 紧接前场连续动作
- \`\`LATER\`\` / \`\`MOMENTS LATER\`\` 同地稍后
- \`\`SAME\`\` 同时刻不同地点

### 角色台词标记

| 标记 | 含义 | 示例 |
|---|---|---|
| **OS (Off Screen)** | 画面外但同场景（隔壁房间 / 浴室） | \`\`MOTHER (O.S.)\`\` |
| **VO (Voice Over)** | 画外音（旁白 / 电话另一端 / 内心独白） | \`\`NARRATOR (V.O.)\`\` |
| **CONT'D** | 同角色连续台词被 action line 打断后继续 | \`\`JOHN (CONT'D)\`\` |
| **MORE** | 台词跨页 | 页底 \`\`(MORE)\`\` |
| **PRELAP** | 下一场声音先进入本场 | 用作转场 |
| **INTERCUT** | 两场来回剪辑（电话对话） | \`\`INTERCUT - PHONE CONVERSATION\`\` |

### 标准剧本格式估算

- 1 页剧本 ≈ 1 分钟成片（业内通用估算）
- 行动描写 ≈ 4-6 行 / 页
- 对白 ≈ 占页面 2/3 时 ≈ 1 分钟
- 闪回 / 蒙太奇 / 序列单独标记

## reference: dialogue-master-styles

4 种大师对白风格的细化对照。

### Sorkin Style（节奏快、长句、辞藻华丽）

| 维度 | 特征 |
|---|---|
| 句长 | 15-30 字 |
| 信息密度 | 极高（一句话多个信息点） |
| 机位 | walk-and-talk 跟拍 |
| 词汇 | 知识精英化、含专业术语 |
| 反讽 | 高频，常用 wryly |

### Mamet Style（短促、爆破、底层）

| 维度 | 特征 |
|---|---|
| 句长 | 3-8 字 |
| 信息密度 | 通过**重复 / 沉默 / 中断**释放 |
| 机位 | 长镜单机、紧密 |
| 词汇 | 底层粗粝、脏话 |
| 反讽 | 通过 staccato 节奏 |

### Tarantino Style（长 monologue、流行文化）

| 维度 | 特征 |
|---|---|
| 句长 | Monologue 段 100-300 字 |
| 信息密度 | 表面看似离题，实则伏笔 |
| 机位 | 长镜 / 圆桌 / 静止 |
| 词汇 | 流行文化引用、低俗与高雅混合 |
| 反讽 | 整段对话都是反讽 |

### Kaufman Style（元叙事、心理化）

| 维度 | 特征 |
|---|---|
| 句长 | 中等，但思维跳跃 |
| 信息密度 | 现实与潜意识混合 |
| 机位 | 主观视角、镜面、不寻常构图 |
| 词汇 | 自指、哲学概念、内心活动外化 |
| 反讽 | 元层（角色意识到自己在剧本里） |

## reference: specific-detail-cookbook

不同 emotion 通过具体细节传递的范例库。

### 悲伤 / 失去

- 触摸亡者还在用的物品
- 抚摸宠物
- 准备一份多余的饭菜
- 看到老照片不说话

### 愤怒 / 压抑

- 攥拳指节发白
- 慢慢放下手中物品
- 过度专注地切菜 / 写字
- 用力关门后立刻放轻

### 害怕 / 紧张

- 手指反复摩擦衣角
- 站立时重心反复转移
- 反复看时间但没看进去
- 喝水却不咽

### 撒谎 / 隐瞒

- 触摸脸 / 耳朵 / 颈侧
- 视线先飘后定
- 笑容比正常慢半拍
- 答非所问后回答原题

### 求而不得

- 视线停留在对方背影
- 拨号到一半挂掉
- 写完信不寄
- 路过门前不进去

### 大事化小（震后平静）

- 关心日常琐事（晚饭 / 天气 / 衣服）
- 把已经写好的便条擦了又写
- 整理已经整齐的桌面
- 复述对方刚说过的话
`;

const CINEMATIC_COMPOSITION = `---
name: cinematic-composition
description: Use when designing storyboards, choosing shot types, designing camera movement, or evaluating shot composition. Provides 7 shot sizes (EWS/WS/MWS/MS/MCU/CU/ECU) with precise definitions, 14 camera movement vocabulary (dolly vs zoom vs pan vs truck), 180° rule + crossing-the-line timing, composition 5-piece set (rule of thirds / leading lines / depth / negative space / axis), shot pattern templates (OTS four-step / push-in to revelation / pull-out to despair), rhythm sequencing rules, transition selection logic, all anchored to master directors (Spielberg / Kubrick / Hitchcock / Deakins).
target_agents: [storyboard_agent]
tags: [cinematography, composition, shot-language, camera-movement, storyboard]
author: filmgenx
---

# 镜头语言与构图（Cinematic Composition）

业内 cinematographer / storyboard artist 的核心命题：**让每个镜头通过景别、构图、运动精确表达情绪与节奏**——剧本告诉你"演什么"，镜头决定"怎么拍"。本 skill 给 storyboard_agent 一套系统化工具：7 种标准景别 + 14 种运镜精确术语 + 180° rule 与跨轴时机 + 构图 5 件套 + shot pattern 模板（Spielberg 三步登顶 / Hitchcock push-in / OTS 四步切）+ 节奏数列分析 + transition 选择逻辑。

## 核心信条 / 第一原理

业内 cinematographer（Roger Deakins / Hoyte van Hoytema / Christopher Doyle / Bradford Young）都遵守的几条铁律：

1. **景别变化服务情绪强度**，不是为了变而变。MS → CU → ECU 三步登顶（Spielberg 公式）产生冲击；同景别五连 = 死板
2. **运动设计与情绪匹配**：紧张戏不用慢摇 / 抒情戏不用急摇 / 高潮前要有静止积累——节奏脱节会撕裂情绪
3. **180° rule 是观众的空间感锚**：跨轴只在主观视点切换 / 信息密度需要时才用；纯为变化跨轴 = 观众迷失
4. **节奏靠数列体现**：把镜头 duration 列成数列——\`\`2, 5, 1.5, 4, 2\`\` 有节奏；\`\`3, 3, 3, 3, 3\`\` 死板。把 shot_size 列成序列——\`\`MS, CU, MS, ECU, WS\`\` 有梯度；\`\`MS, MS, MS, MS\`\` 死板
5. **构图 5 件套是底线**：三分法 / 引导线 / 留白 / 纵深 / 轴线——每个镜头都要至少用 2 个
6. **transition 默认 cut**：dissolve / match-cut / smash / fade 都是带语义的，90% 用 cut；带语义的 transition 用多 = 过度修辞

## 术语词汇表（业内必备）

| 术语 | 含义 | 通用误用纠正 |
|---|---|---|
| **Shot size** | 景别 | 业内用缩写：EWS / WS / MWS / MS / MCU / CU / ECU |
| **Establishing shot** | 开场全景 | 通常 WS 或 EWS，交代空间关系 |
| **Master shot** | 涵盖整场戏的主要镜头 | 通常 MS / WS，作为剪辑参考 |
| **OTS (Over-the-Shoulder)** | 过肩镜头 | 双人对话标配，从一方肩后拍另一方 |
| **POV (Point of View)** | 主观镜头 | 用角色视角拍，代入感强 |
| **Insert** | 插入镜头 | 关键道具 / 细节的特写 |
| **Two-shot** | 双人镜头 | 两个角色同框 |
| **Cutaway** | 切出镜头 | 主线之外的相关画面 |
| **Reaction shot** | 反应镜头 | 拍人物对刚发生的事的反应 |
| **Match cut** | 匹配剪辑 | 前后镜头视觉元素匹配（《2001》骨头→空间站） |
| **Smash cut** | 撞切 | 强反差直切，情绪冲击 |
| **Dolly** | 机座物理位移（轨道车） | ≠ zoom，纵深感真实变化 |
| **Zoom** | 焦距变化，机座不动 | 光学放大，无纵深变化 |
| **Pan / Tilt** | 三脚架原地左右 / 上下转 | 机座不动 |
| **Truck / Pedestal** | 机座侧向 / 升降位移 | 比 pan / tilt 更难 |
| **Push-in** | dolly + zoom 联用 | Hitchcock 的 "Vertigo effect" |
| **Crane** | 大幅度高度变化 | 史诗感 / establishing |
| **Steadicam** | 稳定器跟拍 | 流畅、沉浸感 |
| **Handheld** | 摄影师手持 | 5% 抖动，紧张感 |
| **Rack focus** | 焦平面切换 | 视觉焦点切换技法 |
| **Axis of action / 180° line** | 动作轴线 | 镜头切换不应跨过 |
| **Eyeline match** | 视线匹配 | A 看 B，B 也看 A，方向对得上 |
| **Match on action** | 动作匹配 | cut 前后动作连贯（举手→挥下） |
| **Jump cut** | 跳切 | 故意的连续性破坏 |

## 7 种标准景别（精确定义 + 适用情境）

业内通用 7 级景别（按主体在画面中占比）：

| 缩写 | 全称 | 中文 | 主体占比 | 戏剧表达 | 适用 |
|---|---|---|---|---|---|
| **EWS** | Extreme Wide Shot | 大远景 | < 10% | 史诗感、孤立、压倒性 | Establishing shot / 高潮收尾 / 渺小感 |
| **WS** | Wide Shot | 远景 | 10-30% | 全身 + 周围环境关系 | Master shot / 主角与场景关系 |
| **MWS** | Medium Wide Shot | 中全景 | 30-50% | 全身 + 部分环境 | 群体戏 / 角色出场 |
| **MS** | Medium Shot | 中景 | 50-70%（腰以上） | 半身，对话基础景别 | 对话戏 / 主戏 |
| **MCU** | Medium Close-up | 中近景 | 70-85%（胸以上） | 主角焦点 + 微表情可见 | 关键对话 / 思考状态 |
| **CU** | Close-up | 特写 | 85-100%（脸部） | 强烈情绪 / 真相揭示 | 关键情绪 / 决定时刻 |
| **ECU** | Extreme Close-up | 大特写 | 100%+（局部） | 极端情绪 / 关键细节 | 眼睛 / 手 / 关键道具 |

**特殊镜头类型**（不在 7 级序列里，但常用）：

| 类型 | 含义 | 用在哪 |
|---|---|---|
| **OTS** | Over-the-Shoulder | 双人对话，从一方肩后拍另一方 |
| **POV** | Point of View | 主观视角，代入感强 |
| **Insert** | 插入镜头 | 关键道具 / 文字 / 细节 |
| **Reaction shot** | 反应镜头 | 切到听者的反应 |
| **Cutaway** | 切出镜头 | 主线外的相关画面 |
| **Two-shot** | 双人镜头 | 两人同框 |
| **Crowd shot** | 群众镜头 | 群戏 / 战场 |

## 14 种 Camera Movement 精确术语

非专业 prompt 写"镜头移动"——模型 / 摄影师随机选。专业术语：

| 术语 | 物理动作 | 视觉效果 | 用在哪 |
|---|---|---|---|
| **Static** | 完全不动 | 稳定、聚焦 | 对话戏 / 仪式感 / 关键宣布 |
| **Pan-left / Pan-right** | 三脚架原地左右转 | 横扫、跟随横向运动 | 全景过渡 / 横向追逐 |
| **Tilt-up / Tilt-down** | 三脚架原地上下转 | 揭示高度 / 强调对比 | 主角看天 / 揭示巨物 |
| **Dolly-in** | 机座前推（轨道车） | 物理靠近 + 纵深变化 | 进入空间 / 情绪推进 |
| **Dolly-out** | 机座后退 | 物理远离 + 纵深变化 | 离开 / 揭示孤立 |
| **Truck-left / Truck-right** | 机座侧向平移 | 平行跟随 | 侧面跟跑 / 看穿过物体 |
| **Pedestal-up / Pedestal-down** | 机座升降 | 改变拍摄高度 | 起立 / 蹲下视角 |
| **Push-in** | dolly + zoom 联用 | 强烈聚焦、心理推进 | 情绪到顶 / 角色顿悟 |
| **Pull-out** | 反向 push | 揭示更大语境、失重 | 高潮后收束 / 反转后退步 |
| **Zoom-in / Zoom-out** | 焦距变，机座不动 | 光学放大 / 缩小 | 监视感 / 电视感（少用） |
| **Crane-up / Crane-down** | 机座大幅垂直高度变化 | 史诗感 / 上帝视角 | establishing / 高潮收尾 |
| **Handheld** | 摄影师手持，5% 抖动 | 真实感 / 紧迫感 | 战斗 / 追逐 / 心理失序 |
| **Steadicam** | 稳定器跟拍 | 流畅沉浸 | 一镜到底跟人 |
| **Rack focus** | 焦平面切换 | 视觉焦点切换 | 揭示前后景关系 |

**关键区分**：

- **Dolly vs Zoom**：dolly 物理位移（透视变化，纵深感真实）；zoom 焦距变（图像光学拉伸，纵深不变）。专业镜头大多用 dolly——zoom 看着廉价
- **Push-in = Dolly + Zoom 联用**：Hitchcock《Vertigo（迷魂记）》发明，纵深和焦距同步反向变化制造心理推进感（"Vertigo effect"）
- **Pan vs Truck**：pan 原地转头（视点变了）；truck 整个机座侧向位移（位置变了）。truck 更难也更沉浸（《Children of Men》大量长镜 truck）
- **Tilt vs Pedestal**：tilt 原地仰俯（视点变了）；pedestal 机座升降（位置变了）

## 构图 5 件套（每个镜头至少用 2 个）

业内构图基本功：

### 1. Rule of Thirds（三分法）

把画面按 1/3 划分，主体放在 vertical line × horizontal line 的**交点**。

四个交点的语义：
- **左上 / 右上**：威胁感 / 上方权威
- **左下**：弱势 / 被压迫
- **右下**：失败 / 倒地（业内"弱势角点"）
- **右上**：胜利 / 主导（业内"强势角点"——通常给主角的 establishing shot）

### 2. Leading Lines（引导线）

用环境线条（建筑边缘 / 地平线 / 道路 / 肢体 / 视线）引导观众视线到主体。

- ✅ 街道消失线指向远处主体
- ✅ 角色伸出的手指向关键道具
- ✅ 楼梯扶手把视线引到楼梯顶端
- ❌ 引导线指向画面外或无关元素 = 浪费

### 3. Depth（纵深 / 三层结构）

每个镜头至少 2 层（前景 + 后景），最好 3 层（前景 + 中景 + 背景）：

- **前景层**：靠近镜头的元素（可虚化）
- **中景层**：主体所在层
- **背景层**：远处环境

例（《1917》Roger Deakins）：每个镜头都有 3 层，靠这层次结构让长镜不平。

### 4. Negative Space（留白 / 负空间）

主体周围留出"呼吸空间"，反映心理状态：

- **留白在主体"想去的方向"前面**：表示主动 / 前进
- **留白在主体身后**：表示被追逐 / 后悔
- **主体被挤到画面边缘 + 大量留白在另一侧**：表示孤立 / 隔阂
- **画面满 / 无留白**：视觉疲劳，避免

### 5. Axis of Action（180° 轴线）

两个对话角色之间有一条隐形的"动作轴线"。所有镜头机位**在轴线同侧**——这样观众感觉 A 永远在 B 的左 / 右。

- ✅ 跨轴的合理场景：主观视点切换 / 信息密度需要 / 心理混乱
- ❌ 纯为变化跨轴 = 观众迷失方向

## 镜头节奏（Rhythm）—— Storyboard 与"切镜头工"的分水岭

每场戏的镜头序列应该有**呼吸**——长短交替、动静交替、景别梯度。

### 节奏数列分析

把所有镜头的 duration_seconds 列成数列。判断：

- ✅ \`\`2, 5, 1.5, 4, 2\`\` — 有节奏起伏
- ❌ \`\`3, 3, 3, 3, 3\`\` — 死板的拍子
- ❌ \`\`8, 7, 9, 8, 7\`\` — 全长镜，缺紧凑感
- ❌ \`\`1, 1.5, 1.2, 1, 1.5\`\` — 全短切，疲劳

### 景别序列分析

把所有镜头的 shot_size 列成序列：

- ✅ \`\`MS, CU, MS, ECU, WS\`\` — 有梯度变化
- ❌ \`\`MS, MS, MS, MS, MS\`\` — 死板
- ✅ \`\`WS, MS, CU, ECU, CU, MS, WS\`\` — 经典"放大-收回"曲线

### 不同戏类的节奏配方

| 戏类 | 节奏 | 景别 | 镜头数 |
|---|---|---|---|
| **战斗 / 追逐** | 短切链（1-2.5s）穿插一个长镜（4-6s）收尾 | MS → CU → ECU 快速登顶 | 8-15 镜 / 分钟 |
| **对话 / 关系** | 长镜（4-8s）为主，偶尔切 CU 强调反应 | MS / OTS / MCU 来回 | 4-8 镜 / 分钟 |
| **高潮** | 短切积累张力 → 一个长 ECU 推到顶 → 一个 WS 拉出收尾 | 短切 + ECU 收 + WS 出 | 6-10 镜 / 分钟 |
| **抒情 / 留白** | 长镜（6-12s）为主，几乎不切 | WS / MS 静止 | 2-3 镜 / 分钟 |
| **悬念铺垫** | 静止长镜 + push-in 慢推 | MS → MCU → CU 慢推 | 3-5 镜 / 分钟 |

## 全局时间轴（**给视频生成模型用的核心数据**）

业内分镜师除了出 shot list，还要给一份**全片时间轴表**——每个 shot 标定在整片中的绝对秒数位置。这不是"传统电影制作的可选项"，**在 AI 视频生成里是必需项**：

- AI 视频生成模型（Seedance / Runway / Pika）一次只能生成 4-15 秒短片
- 60 秒短剧会被拆成 4-8 个**独立调用**——每次调用模型完全没有上下文记忆
- 只有"我在整片的第 X-Y 秒、前面发生了什么、上一镜结尾是什么状态"这三层信息能让模型理解上下文
- 缺失这层信息 → 人物漂移（每镜五官不一样）、剧情断裂、动作不连贯

### 时间轴累加规则

每个 shot 必须填：

| 字段 | 含义 |
|---|---|
| \`\`duration_seconds\`\` | 本镜时长（4-15 秒，受 Seedance 硬限） |
| \`\`time_start_seconds\`\` | 本镜在整片的**绝对起始秒**（从 0 累加） |
| \`\`time_end_seconds\`\` | 本镜在整片的**绝对结束秒**（= time_start + duration） |
| \`\`total_duration_seconds\`\` | 整片总时长（顶层字段，= 最后一镜 time_end） |

累加铁律：

\`\`\`
shot[1].time_start = 0
shot[N].time_start = shot[N-1].time_end       （N ≥ 2，无空隙、无重叠）
shot[N].time_end   = shot[N].time_start + shot[N].duration_seconds
total_duration     = shot[last].time_end
\`\`\`

### 时间轴示例（60 秒短剧，8 镜）

\`\`\`
shot 1: duration=3,  time_start=0,   time_end=3      宗门广场远景，主角背身
shot 2: duration=5,  time_start=3,   time_end=8      纳兰嫣然出现近景
shot 3: duration=4,  time_start=8,   time_end=12     主角低头握拳
shot 4: duration=8,  time_start=12,  time_end=20     主角抬头宣告（高潮起手）
shot 5: duration=15, time_start=20,  time_end=35     长镜战斗
shot 6: duration=10, time_start=35,  time_end=45     战斗高潮
shot 7: duration=10, time_start=45,  time_end=55     收尾
shot 8: duration=5,  time_start=55,  time_end=60     落幕
total_duration_seconds: 60
\`\`\`

### 单镜不能超过 15 秒（硬限）

storyboard 设计时如果想要一个 18 秒长镜——**拆成两镜**（如 9 + 9 / 8 + 10），各自标独立的 time_start/end，下游会用 recap + continuity 把它们拼起来看似一镜。

### 跨场（scene boundary）的时间处理

跨场不影响时间轴——继续累加，但在分镜表里**标明 scene_number 切换**。下游 video_prompt_agent 会在 continuity_from_previous 里显式说明"跨场转入"。

## Shot Pattern 经典模板（业内通用）

### 1. OTS Four-Step（对话戏标准切法）

\`\`\`
Shot 1: WS establishing — 交代两人空间关系
Shot 2: OTS over A's shoulder onto B (MS) — B 说话
Shot 3: OTS over B's shoulder onto A (MS) — A 反应
Shot 4: 关键台词时切 CU — 单方面强调
\`\`\`

简单对话 4-6 镜，复杂关系 8-12 镜。

### 2. Three-Step Escalation（Spielberg 三步登顶 / 情绪登顶）

\`\`\`
Shot 1: MS (建立角色与环境)
Shot 2: MCU 或 CU (推到表情)
Shot 3: ECU (情绪顶点 / 关键道具)
\`\`\`

适合：决定时刻 / 揭示真相 / 战斗起势。

### 3. Push-in to Revelation（Hitchcock / 顿悟时刻）

\`\`\`
Shot 1: MS static, 2s
Shot 2: 缓慢 push-in 从 MS 到 CU, 3-4s
Shot 3: hold on CU, 主角眼神聚焦, 2s
\`\`\`

适合：角色顿悟 / 看见真相 / 决心时刻。

### 4. Pull-out to Despair（高潮后失重）

\`\`\`
Shot 1: ECU 主角面部, 2s
Shot 2: 缓慢 pull-out, 揭示主角周围一片废墟, 4s
Shot 3: WS 主角在画面正中渺小, 2s
\`\`\`

适合：失败后 / 高潮后 / 反转后。

### 5. Match Cut（视觉延续转场）

前后镜头视觉元素匹配，跨时空连接。经典例：

- 《2001》原始人骨头扔向天空 → 切到太空站
- 《Lawrence of Arabia》Lawrence 吹熄火柴 → 切到沙漠日出

### 6. Smash Cut（强反差直切）

前后镜头声画反差极大，制造冲击。例：宁静对话 → 突然爆炸。

### 7. Eyeline Match（视线匹配）

\`\`\`
Shot 1: 角色 A 看向画面左侧 (off-screen)
Shot 2: 切到 A 看到的画面 (POV 或非 POV)
\`\`\`

A 的视线方向必须与 Shot 2 的位置对得上。

## Transition（转场）选择

**默认 cut**（90%）。其他 transition 都带语义，慎用：

| Transition | 含义 | 适用 |
|---|---|---|
| **Cut** | 直切，无意义 | 默认 90%，节奏型 |
| **Dissolve / Cross-fade** | 时间跳跃 / 空间过渡 / 梦境进入 | 蒙太奇 / 时间流逝 |
| **Match cut** | 视觉延续连接 | 跨时空、跨题材连接 |
| **Smash cut** | 反差冲击 | 喜剧 / 惊悚 / 情绪转折 |
| **Fade in / Fade out** | 段落分隔 | 开场 / 结尾 / 章节切换 |
| **Whip pan** | 急摇模糊转场 | 动作戏过渡 / 时空跳跃 |
| **L cut / J cut** | 声画错位 | 对话剪辑、情绪先行 |
| **Iris** | 圆圈淡入淡出 | 复古 / 致敬默片 |

**业内铁律**：短切 1 秒配 dissolve = 矛盾（动作没切完就溶了）。duration 与 transition 必须自洽。

## 决策树：你最常遇到的分叉

- **对话戏切几个镜头**：基础切法 establishing WS → 主角 OTS / MCU → 对方 OTS / MCU → reaction CU 来回。简单 4-6 镜，复杂 8-12 镜
- **动作戏切多细**：动作起点 MS → 关键动作 CU/ECU → 落点 MS/WS。一个动作 3-5 镜
- **transition 怎么选**：默认 \`\`cut\`\`；时空跳跃用 \`\`dissolve\`\`；视觉延续用 \`\`match-cut\`\`；情绪冲击用 \`\`smash\`\`。**90% 用 cut**
- **跨轴**：只在主观视点切换 / 信息密度需要 / 心理混乱时跨。纯为变化跨 = 迷失
- **要不要用 handheld**：紧张戏 / 战斗 / 追逐 / 主观视角；但要写明"5% subtle shake"防过晃
- **storyboard duration 区间**：4-15 秒（Seedance 限制），快切优先 5，长镜 8-10，特殊高潮 15

## 反例 / 陷阱

### ❌ 反例 1：全片同一景别

\`\`\`
Shot 1: MS
Shot 2: MS
Shot 3: MS
Shot 4: MS
...
\`\`\`

**后果**：节奏死板，观众疲劳。

**正例**：景别有梯度——\`\`WS, MS, CU, MS, ECU, MS\`\`

### ❌ 反例 2：运动与情绪不匹配

紧张战斗戏用慢摇 / 静止 → 情绪没积累；抒情戏用 handheld / 急摇 → 撕裂温柔感。

**正例**：
- 紧张 → 短切 / handheld / 快推
- 抒情 → 长镜 / static / 缓慢 dolly

### ❌ 反例 3：composition_notes 空话

\`\`\`
"画面好看 / 构图丰富 / 有美感"
\`\`\`

**后果**：分镜师没设计，模型 / 摄影师随机选。

**正例**：

\`\`\`
"主体放右三分点，光从画面 left 45° 打入，背景用虚化路人形成纵深，
留白在主体面对方向"
\`\`\`

### ❌ 反例 4：duration 全部相同

\`\`\`
Shot 1: 3s
Shot 2: 3s
Shot 3: 3s
Shot 4: 3s
Shot 5: 3s
\`\`\`

**后果**：节奏死板。

**正例**：有起伏——\`\`2, 5, 1.5, 4, 2\`\`

### ❌ 反例 5：跨轴无理由

对话戏 Shot 2 主角在左 / 对手在右，Shot 3 突然主角在右 / 对手在左 → 观众迷失。

**正例**：除非有 reaction shot 或主观视点切换，否则保持同侧。

### ❌ 反例 6：duration 与 transition 矛盾

\`\`\`
Shot 5: duration 1s, transition_to_next: dissolve
\`\`\`

**后果**：动作没切完就溶了 = 不连贯。

**正例**：短切配 cut；dissolve 配长镜（4s+）。

### ❌ 反例 7：镜头描写复述剧本台词

\`\`\`
visual_description: "主角说：'我不会放弃。' 然后转身离开。"
\`\`\`

**后果**：分镜写的是"怎么拍"，不是"演什么"——重复剧本。

**正例**：

\`\`\`
visual_description: "主角站在画面右三分点，背对镜头侧脸特写下颌；
光从画面左 45° 打入暖橙色 rim；远景宗门殿宇虚化作纵深。"
\`\`\`

### ❌ 反例 8：忽略画面留白

主体在画面正中，四周塞满建筑 / 道具 → 没呼吸空间 → 视觉疲劳。

**正例**：用留白反映心理状态——孤独感留白在主体周围，前进感留白在主体面前。

## 何时加载附加资料

- 想看 7 种景别完整 cookbook（含每种的电影摄影器材选择 / 镜头焦距） → 加载 @ref:shot-types-cheatsheet
- 想看 14 种 camera movement 完整对照表 + 各导演风格用法 → 加载 @ref:camera-movement-guide
- 想看经典 shot pattern 完整模板库（OTS / 三步登顶 / push-in / pull-out / match cut / smash cut / eyeline match） → 加载 @ref:shot-pattern-templates
- 想看大师导演分镜风格（Spielberg / Kubrick / Hitchcock / Scorsese / Deakins） → 加载 @ref:master-director-styles

## reference: shot-types-cheatsheet

完整 10 种镜头类型对照表 + 焦距推荐。

| 缩写 | 全称 | 中文 | 主体占比 | 推荐焦段 | 戏剧表达 | 经典代表 |
|---|---|---|---|---|---|---|
| **EWS** | Extreme Wide Shot | 大远景 | < 10% | 16-24mm | 史诗感、孤立、压倒性 | 《Lawrence of Arabia》沙漠 |
| **WS** | Wide Shot | 远景 | 10-30% | 24-35mm | 全身 + 周围环境 | 《1917》战壕全景 |
| **MWS** | Medium Wide Shot | 中全景 | 30-50% | 35mm | 全身 + 部分环境 | 群体戏标配 |
| **MS** | Medium Shot | 中景 | 50-70% | 35-50mm | 半身，对话基础 | 大部分对话戏 |
| **MCU** | Medium Close-up | 中近景 | 70-85% | 50-85mm | 主角焦点 + 微表情 | 《The Godfather》对话 |
| **CU** | Close-up | 特写 | 85-100% | 85-135mm | 强烈情绪 / 真相揭示 | 《Lord of the Rings》Frodo |
| **ECU** | Extreme Close-up | 大特写 | 100%+ | 100-200mm Macro | 极端情绪 / 关键细节 | 《Once Upon a Time in the West》眼睛 |
| **OTS** | Over-the-Shoulder | 过肩 | - | 50-85mm | 双人对话标配 | 几乎所有对话戏 |
| **POV** | Point of View | 主观 | - | 视角自然 | 角色视角，代入感 | 《Hardcore Henry》整片 POV |
| **Insert** | Insert | 插入镜头 | 100%（道具） | 85-135mm Macro | 关键道具 / 文字特写 | 揭示线索的关键镜头 |

## reference: camera-movement-guide

完整 14 种 camera movement 对照表 + 大师用法。

### Static（静止）

- **物理**：完全不动
- **戏剧**：稳定、聚焦观察
- **大师用法**：Kubrick《Barry Lyndon》全片大量 static + 缓慢 zoom-out

### Pan / Tilt

- **物理**：三脚架原地转
- **戏剧**：跟随 / 揭示
- **大师用法**：Spielberg《Jurassic Park》tilt-up 揭示恐龙

### Dolly

- **物理**：机座物理位移（轨道车 / dolly track）
- **戏剧**：纵深感真实变化
- **大师用法**：Scorsese《Goodfellas》Copacabana 长镜 dolly

### Push-in（Vertigo Effect）

- **物理**：dolly + zoom 联用，纵深与焦距同步反向
- **戏剧**：心理推进、空间扭曲
- **发明者**：Hitchcock《Vertigo》
- **现代用法**：Spielberg《Jaws》Brody 看到鲨鱼

### Pull-out

- **物理**：反向 push
- **戏剧**：揭示更大语境、失重
- **经典用法**：《Lord of the Rings》from Frodo's face → all of Middle Earth

### Truck

- **物理**：机座侧向平移
- **戏剧**：平行跟随、保持距离
- **大师用法**：Cuarón《Children of Men》长镜 truck 跟跑

### Crane

- **物理**：机座大幅垂直高度变化
- **戏剧**：史诗感、上帝视角
- **大师用法**：《Gone with the Wind》crane-up 揭示战场尸体

### Handheld

- **物理**：摄影师手持，5% 抖动
- **戏剧**：真实感、紧迫感
- **大师用法**：Paul Greengrass《Bourne》全片 handheld

### Steadicam

- **物理**：稳定器跟拍
- **戏剧**：流畅沉浸
- **大师用法**：Kubrick《Shining》Danny 三轮车长镜

### Rack Focus

- **物理**：焦平面切换，机座不动
- **戏剧**：视觉焦点切换
- **大师用法**：Welles《Citizen Kane》前后景关系揭示

## reference: shot-pattern-templates

经典 shot pattern 完整模板库。

### 1. OTS Four-Step（对话戏标准）

\`\`\`
Shot 1: WS / MWS establishing — 交代两人空间关系 (3-4s)
Shot 2: OTS over A's shoulder onto B (MS) — B 说话 (2-3s)
Shot 3: OTS over B's shoulder onto A (MS) — A 反应 (2-3s)
Shot 4: 关键台词时切 CU — 单方面强调 (1-2s)
\`\`\`

简单对话 4-6 镜，复杂关系戏 8-12 镜。

### 2. Three-Step Escalation（Spielberg 三步登顶）

\`\`\`
Shot 1: MS (建立角色与环境) — 2-3s
Shot 2: MCU 或 CU (推到表情) — 1.5-2s
Shot 3: ECU (情绪顶点 / 关键道具) — 1-1.5s
\`\`\`

适合：决定时刻 / 揭示真相 / 战斗起势。

### 3. Push-in to Revelation（Hitchcock / 顿悟）

\`\`\`
Shot 1: MS static — 2s
Shot 2: 缓慢 push-in 从 MS 到 CU — 3-4s
Shot 3: hold on CU, 眼神聚焦 — 2s
\`\`\`

适合：角色顿悟 / 看见真相 / 决心。

### 4. Pull-out to Despair（高潮后失重）

\`\`\`
Shot 1: ECU 主角面部 — 2s
Shot 2: 缓慢 pull-out, 揭示废墟 — 4s
Shot 3: WS 主角在画面正中渺小 — 3s
\`\`\`

适合：失败后 / 高潮后 / 反转后。

### 5. Vertigo Push-Pull（晕眩效果）

\`\`\`
Shot: dolly-in + zoom-out 同步反向，纵深扭曲 — 2-3s
\`\`\`

适合：主角失去现实感 / 恐惧到顶 / 心理失序。

### 6. Match on Action（动作匹配剪辑）

\`\`\`
Shot 1: 主角举手到肩高 (1.5s)
[Cut on action: 手到肩高的同一瞬间]
Shot 2: 主角手举到头顶 (1.5s)
\`\`\`

适合：动作连贯剪辑，让动作看起来比实际更快。

### 7. Eyeline Match（视线 + POV）

\`\`\`
Shot 1: A 看向画面左侧 (off-screen)
Shot 2: A 看到的画面（POV 或非 POV）
\`\`\`

适合：揭示 A 看到什么 / 主观视角。

### 8. Establishing → Master → Coverage（标准场景拆法）

\`\`\`
Shot 1: WS establishing — 交代空间 (4s)
Shot 2: MS master shot — 整场戏的主要镜头 (5-8s)
Shots 3-N: coverage — 各种 OTS / CU / reaction (2-4s each)
\`\`\`

适合：所有常规对话戏 / 关系戏。

## reference: master-director-styles

大师导演的镜头风格锚点 + 代表作。

### Steven Spielberg

- **特征**：三步登顶（MS → CU → ECU 快速放大）+ 主体永远 right-third
- **节奏**：明快、商业、易懂
- **代表**：《Jurassic Park》《Saving Private Ryan》《E.T.》

### Stanley Kubrick

- **特征**：单点透视（Kubrick stare）+ 对称构图 + 缓慢 zoom-out
- **节奏**：极慢、冷峻、几何
- **代表**：《2001》《The Shining》《Barry Lyndon》

### Alfred Hitchcock

- **特征**：Push-in（Vertigo effect）+ POV 切换 + 悬念铺垫
- **节奏**：缓慢累积 + 突发冲击
- **代表**：《Vertigo》《Psycho》《Rear Window》

### Martin Scorsese

- **特征**：长镜 + Steadicam + 旁白 + freeze frame
- **节奏**：高密度、长场景
- **代表**：《Goodfellas》《Taxi Driver》《Casino》

### Wes Anderson

- **特征**：对称构图 + 平面调度 + whip pan + 鲜艳色彩
- **节奏**：精确、卡通化
- **代表**：《Grand Budapest Hotel》《Royal Tenenbaums》《Moonrise Kingdom》

### Roger Deakins（DP）

- **特征**：单光源 + 高反差 + atmospheric perspective + 三层纵深
- **节奏**：缓慢、绘画感
- **代表**：《1917》《Blade Runner 2049》《Skyfall》《Sicario》

### Hoyte van Hoytema（DP）

- **特征**：自然光 + 大画幅（70mm IMAX）+ 长镜
- **节奏**：沉浸、宏大
- **代表**：《Interstellar》《Dunkirk》《Oppenheimer》

### Christopher Doyle（DP）

- **特征**：手持 + 高饱和 + 动态构图 + 慢门拖影
- **节奏**：迷乱、感官
- **代表**：《Chungking Express》《In the Mood for Love》《Hero》
`;

const VISUAL_STYLE_ANCHORS = `---
name: visual-style-anchors
description: Use when establishing project's global visual identity from outline + storyboard. Defines art_genre × lighting × palette decision matrix with master anchors (Makoto Shinkai / Studio Ghibli / Pixar / Trigger / Roger Deakins / Wong Kar-wai), 60/30/10 palette ratio, color theory (complementary / analogous / triadic / split-complementary), color temperature × mood mapping, composition style × genre matching, chiaroscuro vs high-key vs low-key, negative_anchor patterns, and 8-field VisualStyleGuide cookbook.
target_agents: [visual_style_agent]
tags: [visual-direction, art-genre, color-theory, lighting, composition, master-anchors]
author: filmgenx
---

# 视觉锚点设计（Visual Style Direction）

业内 visual director / 美术指导的核心命题：**把整片视觉决定权一次性收敛**——为 character_ref / scene_ref / video_prompt 三个下游环节定义一份**全局视觉先验**，让它们消费同一份语言、不撞风格。本 skill 给 visual_style_agent 输出 \`\`VisualStyleGuide\`\` 时的 art_genre × lighting × palette 决策矩阵、大师锚点表、60/30/10 配色公式、色彩学原理（互补 / 类似 / 三分 / 分裂互补）、色温情绪映射、8 字段 cookbook。

## 核心信条 / 第一原理

业内 visual director（Hoyte van Hoytema / Roger Deakins / Christopher Doyle / 美工指导们）都遵守的几条铁律：

1. **视觉锚点不是"挑好看"，是收敛决策权**：8 个字段必须围绕同一个 mood 互相印证。出现矛盾立刻改——不要"两个都好看就都留"
2. **大师锚点是信息密度的捷径**：写 "in the style of Roger Deakins《1917》cinematography" 比 "电影感强" 信息密度高 10 倍
3. **60/30/10 是色彩配比铁律**：主色 60% / 副色 30% / 强调色 10%。违反 = 画面发花（平均分配）或发闷（同色系堆叠）
4. **art_genre 与 lighting 必须自洽**：pixar_3d + noir 高反差 = 矛盾；ghibli + cyberpunk 霓虹 = 矛盾
5. **色温混合最多 2 种**：3200K (warm) + 5600K (neutral) 或 5600K + 8000K (cool)。三种混 = 廉价滤镜
6. **可执行 > 文采**：所有字段值必须能直接喂给图像 / 视频模型——"暗黑、压抑、史诗级"是文学，"key:fill 1:8 + 3200K + 45° camera-left + venetian blind shadow" 是配方
7. **negative_anchor 不能留空**：下游模型必跑偏——必须挡常见误区（手 / 文字 / 多重曝光 / 风格混入）

## 术语词汇表

| 术语 | 含义 | 通用误用纠正 |
|---|---|---|
| **Color palette** | 配色方案 | 含主色 / 副色 / 强调色 三层结构 |
| **60/30/10** | 业内配色比例 | 主 60% + 副 30% + 强调 10% |
| **Complementary** | 互补色（对色相环 180°） | 红绿 / 蓝橙 / 黄紫 |
| **Analogous** | 类似色（色相环相邻） | 红橙黄 / 蓝紫青 |
| **Triadic** | 三分色（色相环 120°等距） | 红蓝黄 / 橙绿紫 |
| **Split-complementary** | 分裂互补 | 主色 + 主色互补色相邻两色 |
| **Teal-and-orange** | 青橙互补 | 业内最流行的电影配色 |
| **Desaturation** | 去饱和度 | 0.0 = 满饱和，1.0 = 黑白 |
| **Chiaroscuro** | 明暗对比 | Caravaggio 风格，黑底 + 一束光 |
| **High key** | 高调（亮、低对比） | Pixar / 喜剧 / 治愈系 |
| **Low key** | 低调（暗、高对比） | Noir / 悬疑 / 战斗 |
| **Color temperature** | 色温（K） | 3200K 暖 / 5600K 中性 / 8000K+ 冷 |
| **Color script** | Pixar 公司标准工作流 | 每个 scene 在情绪曲线中的色温位置 |
| **Mood board** | 情绪板 | 设计阶段的视觉参考集合 |
| **Negative anchor** | 全局负面 prompt | 挡常见误生成项 |

## 8 字段决策顺序（不可倒着想）

视觉风格不是 8 字段并列填空，是**有因果顺序**：

1. **art_genre** —— 全片美术大类。从题材 + preference.genre 反推
2. **overall_mood** —— 一句话整体基调。和 genre 自洽
3. **color_palette** —— primary / secondary / accent / desaturation（60/30/10）
4. **lighting_style** —— key / fill / practical / time_of_day（含 motivation）
5. **composition_style** —— framing / depth / rule_of_thirds 策略
6. **character_art_style** —— proportions / linework / expression
7. **scene_art_style** —— architecture / environment_detail / weather_atmosphere
8. **negative_anchor** —— 全局负面 prompt

## 8 种主流 Art Genre × 大师锚点

每种 art_genre 都有自己的"父类"——大师 / 工作室 / 流派。写 prompt 时引用这些锚点比"anime 风格"信息密度高 10 倍。

### 1. anime（动画）

- **典型题材**：玄幻 / 修仙 / 战斗番 / 校园
- **大师锚点**：Makoto Shinkai《Your Name》/ Studio Trigger / Kyoto Animation / MAPPA / Madhouse / Production I.G
- **prompt 关键词**：\`\`"anime cel-shading, in the style of Makoto Shinkai / Studio Trigger hybrid"\`\`
- **典型 lighting**：rim light 必有 + cel 2-tone 阴影
- **典型 palette**：饱和色 + accent 高亮（异火 / 灵气）

### 2. photorealistic / film

- **典型题材**：现代都市 / 纪实 / 明星广告 / 电影
- **大师锚点**：Roger Deakins《1917》/ Hoyte van Hoytema《Interstellar》/ Bradford Young《Selma》/ Emmanuel Lubezki《Birdman》
- **prompt 关键词**：\`\`"cinematic photorealistic, shot on Arri Alexa, in the style of Roger Deakins"\`\`
- **典型 lighting**：motivated practical + 1:4 key:fill
- **典型 palette**：低饱和 + teal-and-orange

### 3. pixar_3d / Disney

- **典型题材**：合家欢 / 儿童向 / 温情科幻 / 喜剧
- **大师锚点**：Pixar《Toy Story》《Coco》《Up》/ Disney《Frozen》《Moana》
- **prompt 关键词**：\`\`"Pixar-style 3D animation, subsurface scattering skin, warm rim light"\`\`
- **典型 lighting**：high key + 1:2 soft fill + 多源
- **典型 palette**：高饱和暖色 + 互补冷色 accent

### 4. ghibli / watercolor

- **典型题材**：治愈 / 自然 / 日常奇幻 / 诗意
- **大师锚点**：Studio Ghibli《Spirited Away》《Howl's Moving Castle》《Princess Mononoke》/ 水彩派
- **prompt 关键词**：\`\`"Studio Ghibli aesthetic, soft watercolor painterly background, atmospheric perspective"\`\`
- **典型 lighting**：natural soft light + atmospheric haze
- **典型 palette**：大地色系 + 暖色调

### 5. cyberpunk

- **典型题材**：未来都市 / AI 反乌托邦 / 霓虹夜景
- **大师锚点**：Blade Runner / Blade Runner 2049 (Deakins) / Ghost in the Shell / Akira
- **prompt 关键词**：\`\`"cyberpunk aesthetic, neon-soaked, in the style of Blade Runner 2049 / Ghost in the Shell"\`\`
- **典型 lighting**：multi-color practicals (cyan + magenta) + 1:8 contrast
- **典型 palette**：teal-and-magenta / 湿地面反光

### 6. noir / neo-noir

- **典型题材**：黑色悬疑 / 侦探片 / 高反差对话
- **大师锚点**：Citizen Kane / Blade Runner / The Lighthouse / Sin City / Chinatown
- **prompt 关键词**：\`\`"film noir, low key chiaroscuro, venetian blind shadows, monochrome with single red accent"\`\`
- **典型 lighting**：硬光 1:8~1:16 + 单光源
- **典型 palette**：低饱和单色调（cool blue 或 warm sepia）

### 7. wong-kar-wai / 王家卫风格

- **典型题材**：都市孤独 / 爱情 / 怀旧
- **大师锚点**：Christopher Doyle（DP）《重庆森林》《花样年华》/ 王家卫《2046》
- **prompt 关键词**：\`\`"Wong Kar-wai aesthetic, in the style of Christopher Doyle, slow motion, saturated reds and greens, neon reflections"\`\`
- **典型 lighting**：practical neon + slow shutter trails
- **典型 palette**：饱和红绿 + 黑色阴影

### 8. ink-painting / 中国水墨

- **典型题材**：武侠 / 仙侠 / 古风
- **大师锚点**：徐悲鸿 / 张大千 / 《Hero》(Christopher Doyle DP) / 《卧虎藏龙》
- **prompt 关键词**：\`\`"Chinese ink painting style, traditional brushwork, restrained color palette, in the style of Hero (2002)"\`\`
- **典型 lighting**：高对比 + 大面积留白
- **典型 palette**：墨黑 + 朱红 accent + 米白底

## 色彩学（4 种色彩组合理论）

业内调色师都基于色环（color wheel）选配色：

### 1. Complementary（互补色）— 张力最强

- 色相环对面 180°
- 经典组合：**Teal & Orange**（业内最流行）/ Red & Green / Blue & Yellow
- 适合：高张力戏 / 商业大片 / 战斗戏
- 代表：Michael Bay《Transformers》/ 大部分好莱坞商业片

### 2. Analogous（类似色）— 和谐温馨

- 色相环相邻 30°-60°
- 经典组合：**Red-Orange-Yellow**（暖系）/ Blue-Green-Cyan（冷系）
- 适合：治愈戏 / 抒情戏 / 日常戏
- 代表：Ghibli / Pixar 温馨场景

### 3. Triadic（三分色）— 活泼动感

- 色相环 120° 等距 3 点
- 经典组合：Red + Blue + Yellow / Orange + Green + Purple
- 适合：童话 / 喜剧 / Pixar
- 代表：Pixar《Inside Out》/ Wes Anderson 风格

### 4. Split-Complementary（分裂互补）— 高级感

- 主色 + 主色互补色相邻两色
- 经典组合：Red + Blue-Green + Yellow-Green
- 适合：精致剧情片 / 文艺片
- 代表：Wes Anderson / 各类艺术电影

## 60/30/10 配色公式 + 实际 hex 配方

业内通用配色比例：

\`\`\`
60% Primary   - 主色，决定画面情绪
30% Secondary - 副色，与主色形成对比或补充
10% Accent    - 强调色，给特效 / 关键道具点睛
\`\`\`

按 genre 的配方：

| Genre | Primary 60% (hex 例) | Secondary 30% | Accent 10% | Desaturation |
|---|---|---|---|---|
| **Anime 玄幻战斗** | \`\`#2C1810\`\` 深沉红棕 | \`\`#1A3A5C\`\` 冷蓝暗影 | \`\`#D4AF37\`\` 灵气金 | 0.2 |
| **Anime 治愈系** | \`\`#F4D5C0\`\` 暖粉米 | \`\`#A8C8E0\`\` 浅蓝 | \`\`#E89B95\`\` 樱粉 | 0.3 |
| **Photorealistic 都市** | \`\`#3A3530\`\` 暖灰棕 | \`\`#4A6B8A\`\` 冷蓝天 | \`\`#E8A45C\`\` 暖橙街灯 | 0.4 |
| **Pixar 3D** | \`\`#E8943A\`\` 高饱和橙 | \`\`#3D8B95\`\` 互补青 | \`\`#FFEC52\`\` 鲜亮黄 | 0.1 |
| **Ghibli** | \`\`#7BA05B\`\` 草绿 | \`\`#5A8AC4\`\` 天蓝 | \`\`#C84E3E\`\` 红屋顶 | 0.4 |
| **Cyberpunk** | \`\`#1A1430\`\` 深紫黑 | \`\`#E94560\`\` 霓虹粉 | \`\`#00D9FF\`\` 电光青 | 0.2 |
| **Noir** | \`\`#1A1A1A\`\` 近黑 | \`\`#5A5A5A\`\` 烟灰 | \`\`#B83C2C\`\` 单一红 | 0.85 |
| **Watercolor** | \`\`#E8DBC0\`\` 米色 | \`\`#7AAEC4\`\` 浅水蓝 | \`\`#C84E3E\`\` 朱砂 | 0.5 |
| **Wong Kar-wai** | \`\`#8B0F0F\`\` 饱和红 | \`\`#2D5F2D\`\` 饱和绿 | \`\`#FFD700\`\` 暖黄 | 0.0 |
| **Ink Painting** | \`\`#F4ECD8\`\` 米白宣纸 | \`\`#1A1A1A\`\` 墨黑 | \`\`#B83C2C\`\` 朱砂红 | 0.6 |

**铁律**：
- accent 必须**单一色**——红就只用红、金就只用金。多个 accent = 画面"脏"
- primary + secondary 不能同色系（都冷或都暖 = 没张力，画面发闷）
- desaturation 偏离类型规律要有理由

## Lighting × Mood 矩阵

| Mood | key:fill ratio | 色温 | 方向 | 推荐 genre |
|---|---|---|---|---|
| **温馨亲密** | 1:2 soft | 3200K | front-left 45° | Ghibli / Pixar / 治愈 |
| **史诗壮丽** | 1:4 | 5600K | low-angle backlight | 武侠 / 玄幻 / 战争 |
| **悬疑紧张** | 1:8 hard | 5500K | side 90° | Noir / 侦探 / 惊悚 |
| **绝望压抑** | 1:16 | 8000K | 顶光 overhead | Black film / 悲剧 |
| **浪漫梦幻** | 1:2 soft | 3200K + 6500K | golden + blue mix | 文艺爱情 / 怀旧 |
| **酷感未来** | 1:6 mixed | cyan + magenta | multi-color practicals | Cyberpunk / 科幻 |
| **明媚阳光** | 1:2 soft | 5600K | high-angle 45° | 喜剧 / 青春 / 治愈 |

## Composition Style × Genre Matching

composition_style **必须与 storyboard 的镜头表对齐**——storyboard 全是手持，这里不能写"严谨三分对称"。

| Genre | framing | depth | composition |
|---|---|---|---|
| **Anime** | 动态构图、低视角仰拍 | 中等纵深 | 三分法 + 引导线 |
| **Photorealistic** | 严谨三分 + 留白 | 三层纵深 | 三分 + rule of thirds 严守 |
| **Pixar** | 居中构图 + 视觉焦点明确 | 三层 + 强烈纵深 | 三分 + 圆形构图 |
| **Ghibli** | 自然构图 + 大量留白 | 浅纵深 | 三分 + atmospheric perspective |
| **Cyberpunk** | 不对称构图 + 倾斜机位 | 多层叠加 | 引导线 + 镜面反射 |
| **Noir** | 严谨构图 + 大反差 | 浅纵深 + chiaroscuro | 单一焦点 + 大面积阴影 |
| **Wong Kar-wai** | 不规则构图 + 镜面 / 玻璃反射 | 浅纵深 + 慢门 | 框中框 + 视线阻断 |

## Color Script（Pixar 公开工作流）

Pixar 内部 20 年标准：**为整片每个 scene 在情绪曲线中的位置标定色温**。

例（《Inside Out》Color Script 简化版）：

| Scene 类型 | 主导色温 | 饱和度 | 情绪 |
|---|---|---|---|
| 开场（Joy 主导） | 暖黄橙 3200K | 0.85 | 明亮欢快 |
| 引入 Sadness | 冷蓝 8000K | 0.6 | 忧郁 |
| Headquarters 失控 | 多色混乱 | 0.5 | 焦虑 |
| Bing Bong 失落 | 紫蓝 7000K | 0.4 | 失落 |
| 高潮（接受 Sadness） | 温暖冷暖平衡 | 0.7 | 释然 |
| 结尾（Joy + Sadness 协作） | 平衡 5600K | 0.8 | 平静 |

写 visual_style 时建议**为全片定一个 color script 走向**——开场冷 → 中段暖 / 开场暖 → 中段冷 → 结尾平衡——让色温讲故事。

## Negative Anchor 三层挡板

每个 visual_style 的 negative_anchor 都要叠加 3 层：

### 第 1 层：art_genre 反向挡板

- anime → \`\`photorealistic, real photo, realistic skin pores, 3D render\`\`
- photorealistic → \`\`anime, cartoon, illustration, cel-shading, painterly\`\`
- pixar_3d → \`\`flat shading, anime, 2D illustration, watercolor\`\`
- noir → \`\`saturated colors, bright lighting, anime\`\`
- cyberpunk → \`\`daylight outdoor, rural, warm wood texture, no neon\`\`
- ghibli → \`\`harsh shadows, metallic textures, cyberpunk neon, gritty\`\`
- watercolor → \`\`sharp digital lines, metallic, neon, photorealistic\`\`

### 第 2 层：图像通用挡板

\`\`\`
deformed, extra limbs, missing fingers, blurry face, low quality,
jpeg artifacts, text, watermark, signature, ugly, disfigured, mutated
\`\`\`

### 第 3 层：剧情专属挡板

- 古风 / 历史 → \`\`no modern objects, no cars, no electronics, no plastic, no neon\`\`
- 都市 / 现代 → \`\`no antique, no traditional architecture, no swords\`\`
- 玄幻 → \`\`no modern weapons (no guns), no urban infrastructure\`\`

## 反例 / 陷阱

### ❌ 反例 1：风格分裂

\`\`\`
art_genre: pixar_3d
lighting: noir 高反差硬光 1:16
\`\`\`

**后果**：Pixar 是 high key + 软光，noir 是 low key + 硬光——直接矛盾。

**正例**：

\`\`\`
art_genre: pixar_3d
lighting: high key, soft 1:2 fill, multiple sources, warm 5600K + 3200K practicals
\`\`\`

### ❌ 反例 2：palette 同色系堆叠

\`\`\`
primary: 冷蓝 #4A6B8A
secondary: 冷青 #5A8AB0
accent: 浅蓝 #7AAEC4
\`\`\`

**后果**：三色都冷 → 画面发闷，没张力。

**正例**：teal-and-orange 互补：

\`\`\`
primary: 冷蓝青 #2D5F75 (60%)
secondary: 暖橙棕 #C8742A (30%)
accent: 鲜亮金 #FFD700 (10%)
\`\`\`

### ❌ 反例 3：空话描述

\`\`\`
overall_mood: "暗黑、压抑、史诗级"
lighting: "光照很美，气氛肃穆"
\`\`\`

**后果**：下游模型读不懂——文学描述 ≠ 可执行 prompt。

**正例**：

\`\`\`
overall_mood: "industrial gothic dread, oppressive atmospheric weight"
lighting: "low key 1:8, single hard 5500K key from upper-side at 60°,
          motivated practical bare incandescent bulbs, deep shadows"
\`\`\`

### ❌ 反例 4：negative_anchor 留空

\`\`\`
negative_anchor: ""
\`\`\`

**后果**：下游必跑偏——anime 项目出 photorealistic 图、写实项目出 cartoon。

**正例**：3 层挡板叠加（见上）。

### ❌ 反例 5：与 storyboard 撕裂

storyboard 全是手持镜头，visual_style 写：

\`\`\`
composition: "严谨三分对称、静止机位为主"
\`\`\`

**后果**：上游劳动浪费——分镜白做。

**正例**：

\`\`\`
composition: "dynamic framing, off-center subject placement,
              tolerant of 5% handheld shake, leading lines guide despite motion"
\`\`\`

### ❌ 反例 6：直接复述剧情

\`\`\`
overall_mood: "展现主角的内心挣扎与成长"
\`\`\`

**后果**：剧情 ≠ 视觉。visual_style 应该回答"画面看起来什么样"，不是"故事讲什么"。

**正例**：

\`\`\`
overall_mood: "muted earthtones suggesting weariness, occasional warm highlights
              hinting at hope, low contrast indicates emotional flatness"
\`\`\`

### ❌ 反例 7：art_genre 与题材脱节

武侠玄幻题材选 cyberpunk → 题材撕裂。

**正例**：武侠玄幻 → anime / ghibli / ink-painting；现代都市 → photorealistic / noir / cyberpunk；治愈日常 → ghibli / pixar / watercolor。

## 何时加载附加资料

- 想看 8 种 art_genre 完整决策树（含子流派 / 大师锚点 / 边界判断） → 加载 @ref:art-genre-decision-tree
- 想看 10 种 genre 的完整 hex 配方表 + 60/30/10 实例 → 加载 @ref:color-palette-recipes
- 想看完整 lighting cookbook（key / fill / practical / time_of_day 4 维 + 配方） → 加载 @ref:lighting-style-cookbook
- 想看大师 / 工作室 / DP 的风格锚点完整库 → 加载 @ref:master-anchor-library
- 想看色彩学完整体系（色相环 / 互补 / 类似 / 三分 / 分裂互补 + 影视案例） → 加载 @ref:color-theory-system

## reference: art-genre-decision-tree

7 个预设 art_genre 的分边界、典型场景、负面提示词模板：

### anime
- **典型**：玄幻 / 修仙 / 战斗番。中日韩动漫审美。
- **关键词**：cel shading、saturated colors、dynamic poses、speed lines。
- **负面**：no realistic skin pores、no photorealistic、no western fantasy。
- **不要选**：硬科幻、严肃悬疑。

### photorealistic
- **典型**：现代都市剧、纪实风短片、明星广告。
- **关键词**：high detail、true-to-life lighting、natural skin texture、35mm grain。
- **负面**：no anime、no cartoon、no toon shading。
- **不要选**：玄幻、奇幻。会让"飞剑斗法"看起来像 cosplay 翻车现场。

### pixar_3d
- **典型**：合家欢、儿童向、温情科幻。
- **关键词**：subsurface scattering skin、stylized proportions、warm rim light。
- **负面**：no photorealistic、no horror、no excessive grime。
- **不要选**：暗黑战斗（出戏）、严肃武侠。

### ghibli
- **典型**：自然 / 治愈 / 日常奇幻。东方风景 + 慢节奏。
- **关键词**：painterly background、soft watercolor textures、lush nature、whimsical creatures。
- **负面**：no harsh shadows、no metallic textures、no cyberpunk neon。
- **不要选**：高对抗动作戏。

### cyberpunk
- **典型**：未来都市、AI 反乌托邦、霓虹夜景。
- **关键词**：neon signs、rain-slick streets、teal-and-orange palette、holographic UI。
- **负面**：no daylight outdoor、no rural、no warm wood texture。
- **不要选**：温馨家庭剧、田园风。

### noir
- **典型**：黑色悬疑、侦探片、高反差对话戏。
- **关键词**：venetian blind shadows、low-key lighting、monochrome with red accent、smoky interior。
- **负面**：no bright sunlight、no saturated colors、no anime。
- **不要选**：动作番、轻喜剧。

### watercolor
- **典型**：诗意散文、童话、回忆段落。
- **关键词**：visible brushstrokes、wet edges、soft saturation、paper texture。
- **负面**：no sharp digital lines、no metallic、no neon。
- **不要选**：硬科幻、激烈战斗。

### 决策路径

1. outline 题材是现代 / 写实 → photorealistic 或 noir（看是否暗黑）
2. outline 题材是奇幻 / 玄幻 / 修仙 → anime（动作戏多） / ghibli（治愈） / pixar_3d（合家欢）
3. outline 题材是科幻 → cyberpunk（未来都市暗调） / photorealistic（硬科幻）/ pixar_3d（轻科幻）
4. outline 题材是诗意 / 回忆 / 心理 → watercolor / ghibli
5. 实在不匹配预设 → custom，但必须在 negative_anchor 写得极其详细，否则下游必跑偏

## reference: color-palette-recipes

按 art_genre 给的标准色彩配方（primary / secondary / accent / desaturation）：

| genre | primary | secondary | accent | desaturation |
| --- | --- | --- | --- | --- |
| anime（玄幻战斗） | 深红 + 橙黄（斗气） | 冷蓝（冰系阴影） | 金紫（异火 / 异能） | 0.2 |
| anime（治愈） | 暖粉 + 米白 | 浅蓝 | 樱粉 | 0.3 |
| photorealistic（都市） | 中性灰 + 棕 | 冷蓝（窗外天空） | 暖橙（人造光源） | 0.3 |
| pixar_3d | 高饱和暖色（橙 / 黄） | 互补冷色（青 / 紫） | 鲜亮 accent | 0.0 |
| ghibli | 草绿 + 天蓝 | 米白 + 木棕 | 红屋顶 / 黄花 | 0.4 |
| cyberpunk | 深蓝 + 紫黑 | 霓虹粉 / 青 | 酸黄 / 电光蓝 | 0.2 |
| noir | 几乎黑白 | 深棕 / 烟灰 | **单一红** 点睛 | 0.85 |
| watercolor | 柔米色 + 浅水蓝 | 苔绿 / 暖灰 | 朱砂红 / 藏青 | 0.5 |

### 配方规则

- primary 占画面 60%，secondary 30%，accent 10%。
- accent 必须是**单一**色：红就只用红，金就只用金。多个 accent 会让画面"脏"。
- desaturation 0 = 纯饱和（pixar / 童话），0.2-0.4 = 主流叙事，0.5-0.7 = 文艺 / 回忆，0.85+ = noir / 黑白。
- 同色系不能进 primary + secondary：都冷或都暖会让画面没张力。

## reference: lighting-style-cookbook

把光照写得"可执行"的 4 个维度模板：

### key_light（主光）

- 硬光（hard）：太阳直射 / 顶灯。强阴影边缘。**用于**：noir、cyberpunk 夜戏、戏剧性时刻。
- 柔光（soft）：散射 / 反射。无明显阴影。**用于**：ghibli、pixar、对话日常戏。
- 边缘光（rim）：背光勾边。**用于**：anime 战斗 high-key、photorealistic 人物特写。

### fill_light（补光）

- 低 fill（fill ratio 1:8 ~ 1:16）= 高反差，暗部沉。noir / cyberpunk / 严肃戏。
- 中 fill（1:4 ~ 1:8）= 主流叙事。photorealistic / pixar 日常。
- 高 fill（1:2 ~ 1:4）= 平光，温馨柔和。ghibli / watercolor / 治愈戏。

### practical_sources（场景灯）

- 实用光源（屏幕 / 灯具 / 蜡烛 / 火焰）必须在 prompt 里**写明位置和颜色**。否则下游 SD 会自动加，但位置不可控。
- cyberpunk 必须有：霓虹招牌 / 全息屏 / 街灯。
- noir 必须有：百叶窗光 / 烟雾 / 单点台灯。
- ghibli 必须有：户外日光 / 室内炉火（暖橙）。

### default_time_of_day

- magic hour（金时刻 / 日落前 1h）：万能选项，最讨巧。
- noon：硬影子，戏剧性强。
- night：逼着你思考 practical_sources。
- 全片**只定一个 default**，例外镜头单独讨论。

### 完整示例（cyberpunk 短剧）

\`\`\`
key: hard rim light from neon sign, magenta + cyan
fill: 1:8 ratio, deep shadows in lower half
practical: rooftop hologram display (cyan), street lamps (warm sodium yellow), wet asphalt reflection
default_time_of_day: night, post-rain
\`\`\`

下游 SD / Gemini 拿到这一段直接能吃，不用再脑补。
`;

const CHARACTER_DESIGN = `---
name: character-design
description: Use when designing character reference packs (base appearance + three-view + expression / clothing / accessory variants) so every downstream shot can render the same character without drift. Provides industry workflow (silhouette test → block-in → detail → variants), 7 art-genre proportion recipes, palette ratio 60/30/10, iconography rules, expression cookbook, and consistency lighting rules.
target_agents: [character_ref_agent]
tags: [character-design, reference-image, prompt-engineering]
author: filmgenx
---

# 角色形象设计（Character Design）

业内角色设计的核心命题：**让一个角色在 1000 个镜头里都长一个样**。这不是"画得好看"的问题，是 production pipeline 的一致性工程。本 skill 给 character_ref_agent 在出 \`\`CharacterRefSet\`\` 时的 silhouette test 工作流、palette ratio 配方、art_genre × 比例的查找表、表情 cookbook、以及锁角色一致性的 lighting 铁律。

## 核心信条 / 第一原理

业内 character designer（CD）都遵守的几条铁律——它们是后续所有配方的源头：

1. **Silhouette test 是辨识度的第一道筛子**：角色拍成纯黑剪影应能一眼认出。认不出 → 轮廓辨识度不够，调整发型 / 武器 / 服装轮廓。每个出场角色都过这一关。
2. **base_prompt 是 anatomical bible，不是 hero shot**：只描述"这个生物长什么样"，**绝不**描述"这个生物正在做什么"。表情 / 动作 / 视角 / 情绪光照 = 变体的工作，不是 base 的工作。
3. **60/30/10 palette ratio**：主色 60% / 副色 30% / 强调色 10%。违反这个比例 → 画面发花（三色平均分配）或发闷（同色系堆叠）。Pixar / 吉卜力 / Trigger 都用这个。
4. **Iconography hook 是观众记忆点**：每个角色必须有 1 个 visual hook——独特配饰 / 标志色 / 不对称特征。让读者一眼记住"哦那个戴红围巾的"。
5. **Lighting consistency 锁 i2i**：三视图 + 所有变体都用**同一方向 key light**（默认 \`\`front-left 45° soft\`\`）。i2i 时 key 方向变 = 阴影漂移 = 五官看起来像不同人。
6. **Construction-first**：先轮廓 → 大色块 → 细节，永远不要从五官开始画起。skeleton → silhouette → block-in → detail。

## 术语词汇表（你必须知道的行业名词）

| 术语 | 含义 | 通用误用纠正 |
|---|---|---|
| **Silhouette** | 角色的纯轮廓剪影 | ≠ "外形"——是去除内部细节后**只剩**轮廓 |
| **Block-in** | 用大色块定 palette 与比例 | ≠ "草稿"——是已经定调的 color study，不是线稿 |
| **Anatomical bible** | 角色的"长什么样"基准描述 | 一些团队叫 "model sheet"——同义 |
| **Iconography hook** | 角色的视觉记忆符号 | 不是"配饰"——是 set against 全片的辨识标记（红围巾 / 独眼 / 不对称发辫） |
| **Key light** | 主光，定义主体形状 | ≠ "最亮的光"——key 不一定最亮，rim 可以更亮 |
| **Three-view** | 正面 + 3/4 侧 + 背面 | 行业有 "reference sheet" / "model sheet" 别名 |
| **T-pose / A-pose** | 双臂水平展开 / 略下垂的 neutral pose | hero pose 是"摆 pose"——禁用于 reference sheet |
| **i2i denoising** | image-to-image 的相似度控制 | 0.3 几乎不变 / 0.7 变体 / 0.9 失控 |
| **Cel-shading** | 硬边 2-tone 阴影，无渐变 | anime 标志手法——和 PBR 写实渲染相反 |
| **Headcount proportion** | 头身比，单位 "头" | 写实 7.5-8 头身、moe 4-5 头身、ghibli 6-7 头身 |

## 工作流：silhouette → block-in → detail → variants

业内成熟 character design pipeline 的标准 4 步，跳步必翻车：

### Step 1: Silhouette test（剪影测试）

把角色画成纯黑剪影——能一眼认出来吗？认不出 → 轮廓辨识度不够。调整：
- 发型（蘑菇头 / 长发飞舞 / 寸头）
- 武器轮廓（剑 / 锤 / 弓 / 法杖）
- 服装外形（披风 / 高领 / 不对称下摆）
- iconography hook（独特配饰）

**产出**：一句话描述"这个角色的剪影长什么样"，作为后续 base_prompt 的"骨架"。

### Step 2: Block-in（粗块定型）

用大色块定 **palette ratio 60/30/10**：
- 主色 60%：服装 + 大面积配饰
- 副色 30%：内衬 + 武器 + 头发
- 强调色 10%：emblem / 法器灵光 / 唯一的红配饰

**产出**：一组 hex 颜色对照（如萧炎：\`\`#2C1810 / #6B3410 / #D4AF37\`\`），后续 prompt 里都用这套色。

### Step 3: Detail pass（细节钉死）

- 五官：眼形 / 鼻型 / 嘴型 / 眉型（用业内术语：almond eyes / aquiline nose / cupid bow lips）
- iconography：每个角色 1 个独特视觉符号（钉死它，所有变体都保留）
- micro-detail anchor：模型容易抓住的"小钩子"（左眼下方一道浅疤 / 右耳唯一耳钉 / 左手缠红绳）

**产出**：完整的 base_prompt。

### Step 4: Variants（变体）

基于三视图走 i2i：
- 表情变体：denoising 0.3-0.5（只改表情，五官 / 发型 / 服装稳定）
- 服装变体：denoising 0.6-0.7（换戏服，五官稳定）
- 战斗姿态变体：denoising 0.7-0.8（动作改变，但角色仍可识别）
- 永远不超过 0.85（开始失控）

## base_prompt 标准结构（anatomically neutral）

业内通用词序——前 80% 权重词在前：

\`\`\`
{age + gender}, {body type with 头身比},
{hairstyle + color}, {eye color and shape},
{core outfit + signature material}, {iconography hook},
{art_genre style anchor + studio reference}
\`\`\`

例（萧炎，玄幻战斗番）：

\`\`\`
young adult male, 7.5-head proportion lean athletic build,
long black hair tied high in topknot, sharp almond dark eyes,
dark crimson long robe with black trim, geometric flame embroidery on collar,
massive black greatsword "Heavy Xuan Ruler" wrapped in chains on back,
anime cel-shading style, in the style of Studio Trigger / MAPPA hybrid
\`\`\`

**注意**：
- 写 \`\`7.5-head proportion\`\` 而不是 \`\`slim\`\`——精确数字模型更稳
- 用工作室作为风格锚（\`\`Studio Trigger / MAPPA hybrid\`\`）—— 比 \`\`anime 风格\`\` 信息密度高 10 倍
- 含 iconography hook（"Heavy Xuan Ruler" 是萧炎的视觉标志）

**禁止**在 base_prompt 出现：表情（angry / smile）/ 动作（standing / running）/ 视角（front view / 3/4）/ 情绪光照。

## 三视图模板：neutral pose + consistent lighting

三视图（reference sheet / model sheet）是**最重要的一张图**——所有变体都靠它做 i2i 参考。

\`\`\`
{base_prompt},
three-view character sheet, T-pose front + 3/4 side + back view,
neutral expression, neutral pose, full body shown,
plain white background,
even soft key light from front-left 45°, low 1:2 fill ratio,
character design reference sheet style,
{art_genre style anchor}
\`\`\`

关键参数：
- \`\`aspect_ratio="9:16"\`\`（人物竖图）
- \`\`name\`\` 参数填角色姓名（前端 asset library 标题）
- **lighting consistency 铁律**：三视图所有变体都用 \`\`front-left 45° soft light\`\`——主光方向不变，i2i 变体才不会漂

**不要写**：hero pose / dynamic pose / action pose——那是 key art 不是 reference sheet。

## negative_prompt：三层挡板

每个角色的 negative_prompt 都要叠加 3 层：

### 第 1 层：跨片性别 / 年龄防御（按角色类型选）

| 角色类型 | negative 必含 |
|---|---|
| 男主 / 男配 | \`\`female, woman, child, makeup, breasts, lipstick\`\` |
| 女主 / 女配 | \`\`male, man, child, beard, mustache, broad shoulders\`\` |
| 成年角色 | \`\`child, kid, baby, teenager, infant\`\` |
| 老年角色 | \`\`young, teenager, infant, smooth skin\`\` |
| 凡人角色（玄幻题材） | \`\`glowing eyes, magical aura, fantasy effects, halo\`\` |

### 第 2 层：art_genre 挡板

- anime 角色 → \`\`photorealistic, real photo, realistic skin pores, 3D render\`\`
- photorealistic → \`\`anime, cartoon, illustration, cel-shading, painterly\`\`
- pixar_3d → \`\`flat shading, anime, 2D illustration, watercolor\`\`
- noir → \`\`saturated colors, bright lighting, anime\`\`

### 第 3 层：图像通用挡板（所有 t2i 都带）

\`\`\`
deformed, extra limbs, missing fingers, blurry face, low quality,
jpeg artifacts, text, watermark, signature, ugly, disfigured, mutated
\`\`\`

漏一层就可能整张图作废——尤其是性别 / 年龄项。

## 反例 / 陷阱（**仔细读**）

### ❌ 反例 1：base_prompt 含动作 / 表情

\`\`\`
"萧炎, 黑发, 怒目而视, 挥舞玄重尺, 战斗姿态"
\`\`\`

**后果**：违反 anatomical bible 原则。i2i 出 smile 变体时，模型困惑——三视图本身就是怒目，怎么变 smile？要么变不出来，要么五官漂移。

**正例**：

\`\`\`
"young adult male, 7.5-head lean athletic, long black hair topknot,
sharp dark eyes, neutral expression, dark crimson robe with flame embroidery,
massive greatsword on back, anime cel-shading"
\`\`\`

### ❌ 反例 2：palette ratio 失控（三色平均）

\`\`\`
"red robe, blue cape, yellow belt, green boots, purple gloves"
\`\`\`

**后果**：5 色平均分配，违反 60/30/10。画面发花，记忆点全无，silhouette test 也过不了。

**正例**：

\`\`\`
"dark crimson robe (60%), black trim and gloves (30%), gold flame emblem accent (10%),
restrained palette, high color hierarchy"
\`\`\`

### ❌ 反例 3：lighting consistency 违反

三视图 front 用 \`\`key from left\`\`，i2i 表情变体用 \`\`key from right\`\` → 模型不知道哪边是受光面，每张变体阴影方向随机变，角色看起来像不同时段拍的不同人。

**正例**：所有三视图 + 所有变体都钉死 \`\`even soft key light from front-left 45°\`\`。

### ❌ 反例 4：缺 iconography hook

\`\`\`
"young woman, brown hair, brown eyes, common villager outfit"
\`\`\`

**后果**：没有视觉记忆点。观众过 5 个镜头就忘了她长什么样，silhouette test 必失败。

**正例**：

\`\`\`
"young woman, brown hair with single white streak at left temple,
brown eyes, common villager outfit, signature red wool scarf around neck,
asymmetric leather satchel on right hip"
\`\`\`

（白发束 + 红围巾 + 不对称包带 = 3 个 hook，叠加形成强辨识。）

### ❌ 反例 5：accessories 埋进 base_prompt

\`\`\`
"warrior with sword and shield and bow and quiver and helmet and gauntlets"
\`\`\`

**后果**：prompt 一长就被模型压缩——sword 可能没了、shield 形状变了。

**正例**：accessories 单独列字段，i2i 时用 prompt weighting 加权：

\`\`\`
base: "warrior in plate armor"
accessories field: ["longsword", "kite shield", "longbow", "leather quiver", "open-face helmet"]
i2i prompt: "warrior wielding (longsword:1.3) and (kite shield:1.2)"
\`\`\`

### ❌ 反例 6：name 漂移

outline 写 "陆沉"，character_ref 写 "陆沉君" 或 "陆沉道长" → 下游 character.<name> KV 索引断链，video_prompt 找不到这个角色。

**正例**：name 字段一字不差对齐 outline.characters.name。

## 何时加载附加资料

按以下规则**按需**触发工具调用（先口头说明，紧接着同一轮调用，不要分两轮）：

- 不熟悉某 art_genre 的角色画风约定（少年漫 vs 少女漫 vs seinen 头身比 / 描边粗细 / 表情夸张度） → 加载 @ref:art-genre-character-proportions
- 要为某个特定情绪挑表情 prompt 片段 → 加载 @ref:expression-prompt-cookbook
- 服装 / 配件 / 防具该列什么粒度拿不准 → 加载 @ref:clothing-and-accessories-checklist
- 配色想做高级感的撞色 / 不熟悉 60-30-10 怎么落地到 hex → 加载 @skill:visual-style-anchors#color-palette-recipes
- 想给角色加 cinematic lighting 但不确定选哪种光位（Rembrandt / loop / split / butterfly / rim） → 加载 @skill:lighting-cookbook

## reference: expression-prompt-cookbook

5 种核心表情的 prompt 片段（中文 + 英文 anime tag），可直接拼到角色变体里：

### determined（决心 / 战斗前）

\`\`\`
中文: 紧抿嘴角, 瞳孔聚焦, 微皱眉, 下颌微抬, 眼神锐利
英文 tag: serious face, focused eyes, slight frown, tight lips, intense gaze
\`\`\`

适用：战斗前夜、做出决定、面对反派。

### angry（愤怒 / 仇恨）

\`\`\`
中文: 眉心紧锁, 咬牙切齿, 瞳孔放大, 青筋微现, 嘴角下扯
英文 tag: angry expression, gritted teeth, furrowed brow, dilated pupils, snarling
\`\`\`

适用：受辱、仇恨爆发、被背叛。

### sad（悲伤 / 失落）

\`\`\`
中文: 眉尾下垂, 眼神空洞, 唇角下拉, 眼眶微红, 头微低
英文 tag: sad face, downturned mouth, teary eyes, drooping eyebrows, downward gaze
\`\`\`

适用：失去亲人、求而不得、回忆旧伤。

### surprised（惊讶 / 震惊）

\`\`\`
中文: 瞳孔瞪大, 嘴微张, 眉毛抬高, 头部微后仰, 表情僵住
英文 tag: shocked face, wide eyes, open mouth, raised eyebrows, surprised expression
\`\`\`

适用：突发事件、意外发现、剧情反转。

### smile（微笑 / 胜利）

\`\`\`
中文: 嘴角上扬, 眼神柔和, 微眯眼, 下颌微抬, 神情释然
英文 tag: gentle smile, soft eyes, slight smirk, relaxed face, content expression
\`\`\`

适用：胜利、释然、温情时刻。

### 反派专用：cold_smile（冷笑 / 优越）

\`\`\`
中文: 嘴角单边上扬, 眼神锐利, 下巴微抬, 冷漠的笑意
英文 tag: smirk, cold smile, raised chin, disdainful eyes, condescending expression
\`\`\`

适用：反派出场、傲慢宣言、阴谋得逞。

## reference: art-genre-character-proportions

不同 art_genre 对角色 proportion / linework 的要求：

### anime（玄幻战斗番）

- proportion: 7-7.5 头身（少年）/ 8-8.5 头身（成年战士）；夸张瞳孔（占脸 1/4）
- linework: clean cel shading，硬边阴影 2-3 层，无柔光过渡
- 标准 prompt 关键词: \`\`anime style, cel shaded, sharp linework, large expressive eyes, dynamic poses\`\`

### photorealistic（都市 / 写实）

- proportion: 真人 7.5-8 头身，正常脸部比例
- linework: 无明显线条，靠光影建模
- 标准 prompt 关键词: \`\`photorealistic, true-to-life proportions, natural skin texture, 35mm, sharp focus, soft natural lighting\`\`
- 注意: 慎写"细致 hair strands"，否则容易翻车

### pixar_3d（合家欢 / 温情）

- proportion: 矮胖化（5-6 头身），眼睛 + 头部放大
- linework: subsurface scattering，rim light 突出
- 标准 prompt 关键词: \`\`pixar 3d animation style, stylized proportions, large head, expressive face, subsurface scattering, warm lighting\`\`

### ghibli（治愈 / 自然）

- proportion: 7-7.5 头身，柔和五官
- linework: painterly background + 简洁人物线条，水彩感
- 标准 prompt 关键词: \`\`ghibli studio style, soft watercolor, painterly, gentle expression, lush environment\`\`

### cyberpunk（未来 / 暗调）

- proportion: 真人比例 + cybernetic 改造件
- linework: neon rim light，潮湿表面
- 标准 prompt 关键词: \`\`cyberpunk style, neon rim lighting, cybernetic implants, holographic UI elements, rain-slick reflections\`\`

### noir（黑色悬疑）

- proportion: 真人 8 头身
- linework: 硬光 + 大面积阴影 + 单一红色 accent
- 标准 prompt 关键词: \`\`film noir, monochrome with red accent, harsh shadows, low-key lighting, smoky interior, venetian blind shadows\`\`

### watercolor（诗意 / 文艺）

- proportion: 7-7.5 头身，柔化轮廓
- linework: visible brushstrokes，wet edges
- 标准 prompt 关键词: \`\`watercolor illustration, visible brushstrokes, soft saturation, paper texture, dreamy atmosphere\`\`

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
`;

const SCENE_DESIGN = `---
name: scene-design
description: Use when designing scene reference packs (production design 4 layers + environmental storytelling + time variants + focal length intent). Provides industry PD methodology (architecture / dressing / props / atmosphere), Time-of-Day Continuity rules, Lighting Motivation 4 types, focal length intent matrix, environment-prompt-cookbook by genre, and lighting recipes ready to splice.
target_agents: [scene_ref_agent]
tags: [scene-design, production-design, environment, reference-image, prompt-engineering]
author: filmgenx
---

# 场景设计（Production Design）

业内 production designer（PD）的核心命题：**让一个 location 在所有镜头里都长一个样、并能用环境讲故事**。这不是"画得好看"的问题，是 production pipeline 的一致性 + storytelling 工程。本 skill 给 scene_ref_agent 在出 \`\`SceneRefSet\`\` 时的 PD 4 层心智模型、environmental storytelling 套路、focal length intent 决策、time-of-day continuity 铁律，以及按 genre 分类的 prompt cookbook。

## 核心信条 / 第一原理

业内 PD / 美术指导都遵守的几条铁律：

1. **Production Design 拆 4 层**：Architecture（建筑骨架）/ Dressing（装饰陈设）/ Props（关键道具）/ Atmosphere（大气）。**每层分开写**，堆在一句里下游 prompt 无结构。
2. **环境必须讲故事（environmental storytelling）**：场景不是"漂亮背景"，是叙事载体。同一座宗门可以是"刚建成 / 鼎盛期 / 败落后 / 战后焦土" 4 种状态——读 outline 决定哪个。
3. **光必须有动机（lighting motivation）**：画面里观众应能识别光源（natural / practical / motivated artificial / magical）。无动机的光让画面假。
4. **Scale reference 是空间感的钥匙**：场景图必须给一个已知尺寸物（人形 / 门 / 椅 / 灯柱）暗示空间大小。缺尺度参照 = 后续镜头里人物大小拍错。
5. **Time-of-Day Continuity**：同一 location 的所有变体里，太阳 / 月亮方位应一致（除非剧情跨日）。违反 → i2i 出来"同一个地方"看起来像不同位置。
6. **Focal length intent**：基础图按什么焦段画——24mm wide 强调空间 / 35mm 自然 / 50mm 标准 / 85mm 长焦压缩。这是 PD 与摄影指导对话时定的。

## 术语词汇表（PD 必备）

| 术语 | 含义 | 通用误用纠正 |
|---|---|---|
| **Architecture** | 建筑骨架：年代 + 流派 + 结构 | 不是"建筑外观"——是结构特征（明清木骨架 / Gothic 飞扶壁 / Brutalist 清水混凝土） |
| **Dressing** | 装饰陈设：墙面 / 地面 / 家具 / 挂件 | 可移除的层——PD 经常借此讲故事 |
| **Props** | 关键道具：镜头会聚焦的物件 | 单独列——埋在描述里模型容易漏 |
| **Atmosphere** | 大气：雾 / 雨 / 尘 / 烟 / 灰 / 雪 | 定"呼吸感"——这层缺了画面像 vacuum 抽干 |
| **Establishing shot** | 开场全景，交代空间关系 | 通常 24mm wide / high-angle，每个 location 至少一张 |
| **Detail shot** | 局部 focal point | establishing 之后的特写，揭示道具 / 文字 / 痕迹 |
| **Scale reference** | 尺度参照物 | 人形（≈1.7m）/ 门（≈2m）/ 椅（≈0.5m）/ 灯柱（≈3m） |
| **Lighting motivation** | 光的合理化来源 | natural / practical / motivated artificial / magical |
| **Practical light** | 画面里可见的人造光（灯笼 / 烛 / 屏幕） | 不是"装饰"——是 motivation 的载体，电影质感来源 |
| **Color script** | 整片每个 location 的色温位置 | Pixar 标准工作流——每场戏在情绪曲线里的色彩位置 |
| **Environmental storytelling** | 用环境讲故事 | 痕迹 / 磨损 / 灰尘 / 蛛网揭示时间与人物 |

## Production Design 4 层心智模型

PD 看场景按 4 层分解，你描述时也按这个分层：

### Layer 1 — Architecture（建筑骨架）

**精确到**：年代 + 流派 + 结构。

- ✅ "明清官式木骨架 + 抬梁式 + 重檐歇山顶 + 朱红柱"
- ✅ "Gothic Revival 1890 + 飞扶壁 + 尖券窗 + 砂岩外墙"
- ✅ "Brutalist 1970 + 清水混凝土 + 大悬挑结构 + 几何窗洞"
- ❌ "古建筑"（年代 / 流派模糊，模型瞎画）

### Layer 2 — Dressing（装饰陈设）

**讲故事最重要的一层**：墙面 / 地面 / 家具 / 挂件——可移除的细节。

例（同一座宗门大殿）：
- 鼎盛期："朱漆木柱包浆温润，青砖地被千万脚磨出 polished sheen，香烛常燃熏黑椽木，墙上挂列祖列宗画像"
- 败落后："木柱开裂朱漆斑驳，神像金漆脱落，地上灰尘踩出一条小径，廊下蛛网密布"

### Layer 3 — Props（关键道具）

**单独列出**——埋在描述里模型容易漏：

- "祭坛上的青铜鼎 + 鼎内未燃尽的檀香"
- "案头的玉印 + 红泥印盒"
- "墙角的兵器架 + 上头一柄缺角铁刀"

### Layer 4 — Atmosphere（大气）

**定呼吸感**：雾 / 雨 / 尘 / 烟 / 灰 / 雪。

例：
- "晨雾从地面 1m 漂浮，体积光从窗棂打入切片状"
- "檀香烟柱垂直向上 2m 后散开"
- "暴雨雨幕灰白，地面镜面反光，雾气朦胧"

**4 层分开写**——堆成一句话 = 下游 prompt 拼装无结构。

## Environmental Storytelling（用环境讲故事）

PD 的看家本领。同一座建筑可以是 4 种状态——读 outline + script 决定哪个：

| 状态 | 视觉信号 | 适用情境 |
|---|---|---|
| **刚建成** | 新木柱、油漆未干、地砖未磨损、神像金漆崭新 | 创立期 / 主角刚到 / 欣欣向荣 |
| **鼎盛期** | 木柱包浆温润、地砖 polished sheen、香烛常燃熏黑椽木 | 主线开始 / 黄金时代 |
| **败落后** | 朱漆斑驳、神像金漆脱落、灰尘小径、廊下蛛网 | 主角离开数年 / 衰落剧情 |
| **战后焦土** | 椽木烧焦倒塌、神像被斩半、地砖崩裂血迹未干 | 高潮战后 / 废墟揭示 |

不要默认画"完好"——读剧情决定状态。

## Focal Length Intent（焦段意图）

每个 location 基础图按什么焦段画——PD 在和摄影指导对话时定的：

| 焦段 | 视觉效果 | 用在哪 | prompt 关键词 |
|---|---|---|---|
| **24mm wide** | 空间压迫、纵深拉长、近大远小 | 宏大场景 / establishing shot / 角色与环境关系 | \`\`shot on 24mm wide-angle lens, deep perspective\`\` |
| **35mm** | 接近人眼自然视角 | 日常场景 / 室内 / 全景人物 | \`\`shot on 35mm, natural human field of view\`\` |
| **50mm normal** | 比例真实、空间真实 | 主角 establishing / 中景对话场地 | \`\`shot on 50mm normal lens, natural proportions\`\` |
| **85mm tele** | 背景压缩、虚化强、孤立主体 | 情感时刻 / 主角特写背景 | \`\`shot on 85mm telephoto, compressed background, shallow depth of field\`\` |

基础图通常 **24mm wide** 或 **35mm**——交代空间关系。下游 video_prompt 镜头里再用其他焦段拍人。

## Lighting Motivation 4 类

写 lighting 字段时**先确定光源类型**，再描述方向 / 色温 / 强度：

| 类型 | 含义 | 例子 |
|---|---|---|
| **Natural** | 自然光（窗 / 门 / 天井） | "正午阳光从天井垂直洒下，5600K 硬光" |
| **Practical** | 景内可见人造光 | "廊下油灯昏黄，2700K 暖橙" |
| **Motivated artificial** | 能合理化的人造光 | "剧情有月光，所以画面有冷蓝顶光" |
| **Magical** | 题材允许的非现实光源 | "剑气发光 / 阵法蓝光 / 灵气漂浮" |

**正例**：

\`\`\`
"正午阳光从天井垂直洒下（natural，5600K 硬光），廊下油灯昏黄常燃（practical，
2700K 暖橙），形成冷暖对比，明暗 ratio 1:6"
\`\`\`

**反例**：

\`\`\`
"光照柔和，气氛肃穆"  ← 模型不知道光从哪来
\`\`\`

## Scale Reference（尺度参照）

场景图必须给一个**已知尺寸物**让观众判断空间：

- 人形剪影（最直接，≈1.7m）
- 已知道具：门 ≈2m / 椅 ≈0.5m / 灯柱 ≈3m
- 比例对比组：巨门 + 小小一个人 = 宏大感

prompt 写法：

\`\`\`
"... ancient sect courtyard, towering 8-meter bronze bell at center,
small monk silhouette walking past at left foreground for scale reference"
\`\`\`

## time_variants 的边界（按剧情反推，不凑数）

每个 location **最多 3 个时段变体**，按以下优先级挑：

1. 剧情明确出现的时段（剧本写"日落决斗"）→ 必出
2. 戏剧反差大的时段（同地场白天 / 夜晚两次出现）→ 必出
3. 气氛抓手的时段（cyberpunk 必夜、ghibli 必日）→ 必出

剧情里只在一个时段出现，**不凑变体**——单一变体就够。

每个 variant 的 value 只写**该时段下变化的部分**（光照 / 氛围 / 颜色），**不重复 architecture**：

\`\`\`python
time_variants = {
    "day":   "顶光强烈，白玉反光刺眼，5600K 暖橙调",
    "night": "月光冷光（8000K），practicals 灯笼暖橙（2700K），远景灯火",
    "rain":  "雨幕灰白，地面镜面反光，雾气，整体降饱和到 0.4"
}
\`\`\`

## Time-of-Day Continuity 铁律

同一 location 的所有变体里，**太阳 / 月亮方位应一致**（除非剧情跨日）：

- day variant：阳光从东南方 / 西南方
- dusk variant：太阳应在同一方向（西方）
- night variant：月亮在天，但方位与日 variant 的太阳轨迹合理

违反 → i2i 出来"同一个地方"看起来像不同位置，全片场景撕裂。

## color_restrictions（喂给图像模型的英文标签）

**用 SD-style 英文标签**，不是中文长句：

| 题材 | color_restrictions |
|---|---|
| anime 玄幻 | \`\`saturated reds and golds with cool blue accents, 0.6 saturation\`\` |
| photorealistic 都市 | \`\`muted greys and browns, cold blue sky, warm orange streetlights, 0.4 saturation\`\` |
| pixar_3d | \`\`high saturation warm orange and yellow with cool teal accents, 0.85 saturation\`\` |
| ghibli | \`\`soft greens and blues, cream whites, occasional warm reds, 0.5 saturation\`\` |
| cyberpunk | \`\`deep blue and magenta neon, teal-and-orange complementary, electric blue accents\`\` |
| noir | \`\`monochrome black and grey with single red accent, harsh shadows, 0.1 saturation\`\` |
| watercolor | \`\`soft pastels, watercolor washes, muted palette, 0.35 saturation\`\` |

## mood_keywords（中文短词列表，给 video_prompt 看的）

3-6 个中文短词：

\`\`\`python
["废墟感", "压抑", "肃杀", "孤立", "庄严"]
["温馨", "亲密", "怀旧", "柔软", "日常"]
["冷峻", "未来感", "潮湿", "霓虹", "疏离"]
\`\`\`

不写句子（"主角在这里发现真相" = 情节，不是 mood）。

## negative_prompt：场景专属挡板

按场景类型 + 题材双层叠加：

### 第 1 层：场景类型挡板

| 场景类型 | negative 必含 |
|---|---|
| 室内 | \`\`no outdoor, no sky, no horizon, no daylight from outside\`\` |
| 室外开阔 | \`\`no ceiling, no walls, no enclosed space\`\` |
| 室外建筑环绕 | \`\`no isolated structure, no empty plain\`\` |
| 黑夜 | \`\`no daytime, no bright sunlight, no clear blue sky\`\` |
| 白天 | \`\`no nighttime, no neon, no artificial bright lights\`\` |
| 自然环境 | \`\`no concrete buildings, no urban infrastructure\`\` |
| 城市 | \`\`no rural, no wilderness, no isolated landscape\`\` |

### 第 2 层：题材挡板

- 古风 / 历史 → \`\`no modern objects, no cars, no electronics, no plastic, no neon\`\`
- 都市 / 现代 → \`\`no antique, no traditional architecture, no swords\`\`
- 梦境 / 异空间 → \`\`photorealistic, mundane, ordinary\`\` （反向挡板）

## reference_image_count 分配

每个 location **最少 2 张**：

- 1 张 establishing shot（24mm wide，交代空间关系，含 scale reference）
- 1 张 detail shot 或 副 time_variant

最多 3 张。**不要每个 time_variant 都出**——下游 video_prompt 会按文字提示融合时段，参考图给"建筑骨架"就够。

## 反例 / 陷阱

### ❌ 反例 1：4 层堆成一句话

\`\`\`
"古代宗门大殿，肃杀压抑，月光照进来"
\`\`\`

**后果**：architecture / dressing / props / atmosphere 全混。模型抓不住主导特征。

**正例**：

\`\`\`
[architecture]: 明清官式木骨架，抬梁式，重檐歇山顶，朱红柱
[dressing]: 朱漆斑驳，地砖磨损出 polished sheen，墙上列祖列宗画像（败落状态）
[props]: 案头玉印、墙角缺角铁刀、祭坛青铜鼎
[atmosphere]: 月光冷蓝（8000K natural）从天井斜入，烛火暖橙（2700K practical），
              地面 1m 处有薄雾，体积光切片状
\`\`\`

### ❌ 反例 2：缺 environmental storytelling

\`\`\`
"宗门大殿，雄伟壮观"
\`\`\`

**后果**：场景看不出剧情状态——是繁盛还是废墟？读者无法理解戏。

**正例**：

\`\`\`
"宗门大殿（败落 30 年状态），朱漆斑驳露木胎，神像金漆脱落，
地上灰尘踩出一条小径只剩一条，廊下蛛网，香炉空了无烟"
\`\`\`

### ❌ 反例 3：lighting 无动机

\`\`\`
"光照柔和，营造神秘氛围"
\`\`\`

**后果**：模型不知道光从哪来，每张图光照随机摆，三视图各张光不一致。

**正例**：

\`\`\`
"motivated soft natural light from skylight at upper-right 45°,
warm 3200K with cool 6500K ambient fill, 1:3 key:fill ratio,
practical candles on altar adding warm 2700K accent points"
\`\`\`

### ❌ 反例 4：缺 scale reference

\`\`\`
"巨大的宫殿，金碧辉煌"
\`\`\`

**后果**：观众判断不出空间大小——是 5 米高还是 50 米高？后续镜头里人物大小拍错。

**正例**：

\`\`\`
"towering palace hall, 15-meter ceiling, small human silhouette walking
through doorway at left foreground for scale reference, dramatic vertical
perspective emphasized"
\`\`\`

### ❌ 反例 5：time-of-day continuity 违反

day variant 太阳在西，night variant 月亮也在西，dusk variant 太阳在东——位置漂移。

**正例**：所有 variant 都钉死"光源 / 主光在右上 45°"，只改色温与强度。

### ❌ 反例 6：同一物理空间拆成多个 SceneRef

剧本写"云岚宗"和"云岚宗大殿"——这是不同物理空间（一个是整个宗门 / 一个是大殿），拆是对的。但"云岚宗广场（NIGHT）"和"云岚宗广场（DAY）"是同一物理空间，**必须合并**+ 两个 time_variants。

## 何时加载附加资料

按以下规则**按需**触发工具调用（先口头说明，紧接着同一轮调用）：

- 不熟悉某个建筑流派的精确特征（明清官式 / Gothic Revival / Brutalist / 部落原始） → 加载 @ref:environment-prompt-cookbook
- 时段 / 天气的具体光照配方（golden hour / blue hour / overcast / stormy） → 加载 @ref:time-of-day-lighting-recipes
- 选光照配方拿不准（chiaroscuro / high-key / motivated practical 怎么布） → 加载 @skill:lighting-cookbook
- 色彩组合不知道选互补还是类似色 → 加载 @skill:visual-style-anchors#color-palette-recipes
- prompt 词序权重 / aspect ratio × composition / 风格触发词怎么写 → 加载 @skill:image-prompt-engineering

## reference: environment-prompt-cookbook

按场景类型给的标准 prompt 配方：

### 玄幻宗门（仙侠 / 修仙）

\`\`\`
architecture: 巨型石阶 / 白玉广场 / 飞檐殿宇 / 古铜钟 / 灵气云雾
atmosphere: 庄严 / 肃杀 / 上古遗留 / 仙气缭绕
lighting: 清晨薄雾 + 顶光散射 / 黄昏霞光 / 月华笼罩
props: 青铜钟 / 古旗帜 / 门派牌匾 / 镇宗石碑
英文 tag: ancient sect courtyard, white jade plaza, towering stone steps, mountain backdrop, mystical mist
负面: no modern building, no concrete, no urban
\`\`\`

### 都市街景（现代 / 都市剧）

\`\`\`
architecture: 高楼大厦 / 街道 / 红绿灯 / 玻璃幕墙 / 招牌
atmosphere: 繁忙 / 冷漠 / 都市疏离 / 节奏感
lighting: 正午硬光 / 夜晚霓虹 / 黄昏街灯
props: 出租车 / 便利店招牌 / 公交站 / 路人
英文 tag: modern city street, glass skyscrapers, neon signs, urban realistic, rain-slick asphalt
负面: no rural, no wilderness, no fantasy elements
\`\`\`

### 末日 / 废墟

\`\`\`
architecture: 倒塌建筑 / 锈蚀金属 / 杂草丛生 / 弃车
atmosphere: 死寂 / 绝望 / 末世 / 寂寥
lighting: 暗沉灰蓝 / 偶尔斜射光柱 / 黄昏沙尘
props: 废弃汽车 / 破碎招牌 / 杂草藤蔓 / 残骸
英文 tag: post-apocalyptic ruins, abandoned cityscape, overgrown vegetation, rusted metal, debris
负面: no clean modern building, no people, no daily life
\`\`\`

### 室内对话（家 / 办公室 / 咖啡厅）

\`\`\`
architecture: 桌椅 / 窗 / 地板 / 墙面装饰
atmosphere: 私密 / 日常 / 温暖 / 紧绷（视情境而定）
lighting: 实用光源（台灯 / 窗户日光）+ 柔光
props: 茶杯 / 笔记本 / 装饰画 / 植物 / 抱枕
英文 tag: cozy interior, soft natural window light, wooden floor, intimate atmosphere
负面: no outdoor, no sky, no horizon
\`\`\`

### 自然 / 田园

\`\`\`
architecture: 山 / 河 / 树林 / 田野 / 小路
atmosphere: 宁静 / 治愈 / 自然 / 季节感
lighting: 清晨薄雾 / 正午斑驳树影 / 黄昏暖光
props: 野花 / 溪水 / 石头 / 木桥
英文 tag: lush natural landscape, dappled sunlight through leaves, peaceful atmosphere, painterly
负面: no urban, no concrete, no neon
\`\`\`

### 战斗场（决斗台 / 修罗场）

\`\`\`
architecture: 开阔平台 / 残骸地形 / 围观看台 / 高空场地
atmosphere: 紧张 / 杀气 / 史诗感 / 万人屏息
lighting: 戏剧性硬光 / 风沙效果 / 仰角顶光
props: 武器残骸 / 战旗 / 血迹 / 裂痕
英文 tag: dramatic battlefield, dust and debris, low-angle shot, cinematic lighting
负面: no peaceful, no warm, no ordinary daily scene
\`\`\`

## reference: time-of-day-lighting-recipes

5 种核心时段的光照模板（直接拼到 prompt 里）：

### dawn（黎明）

\`\`\`
柔和 backlight 从地平线来, 蓝紫色天空过渡到暖粉, 雾气未散, 主体剪影清晰
英文 tag: soft golden hour backlight, dawn mist, purple-pink sky gradient, silhouettes
适用: 决心 / 重生 / 新开始的情绪
\`\`\`

### day（正午）

\`\`\`
顶光强烈, 短阴影硬, 高对比, 蓝天明亮
英文 tag: harsh midday sunlight, sharp shadows, high contrast, clear blue sky
适用: 戏剧性时刻 / 揭示真相 / 公开对峙
\`\`\`

### golden_hour（黄金时刻 / 日落前 1h）

\`\`\`
低角度暖橙光, 长阴影, 全场镀金, 浪漫感
英文 tag: warm golden hour light, long shadows, magic hour glow, romantic atmosphere
适用: 抒情 / 离别 / 反思 / 万能选项
\`\`\`

### dusk（黄昏 / 日落后）

\`\`\`
紫蓝色天空, 实用光源点亮, 远景轮廓模糊, 神秘感
英文 tag: blue hour twilight, purple-blue sky, practical lights starting to glow, mysterious
适用: 转折 / 悬疑 / 剧情进入下半段
\`\`\`

### night（黑夜）

\`\`\`
月光冷蓝, 实用光源（街灯 / 窗光 / 火光）作主光, 阴影深邃
英文 tag: moonlit night, cool blue ambient, warm practical lights, deep shadows
适用: 阴谋 / 战斗高潮 / 内心独白 / cyberpunk 默认
\`\`\`

### rain（雨景，可叠加在任意时段）

\`\`\`
雨幕灰白, 地面镜面反光, 雾气朦胧, 降饱和
英文 tag: rain-soaked atmosphere, wet reflective surfaces, atmospheric fog, desaturated
适用: 悲伤 / 转折 / 净化 / noir 必备
\`\`\`
`;

const VIDEO_PROMPT_ENGINEERING = `---
name: video-prompt-engineering
description: Use when translating storyboard shots into Seedance reference-to-video motion prompts. Provides the "图片信息 > 文字" core信条, 13 precise camera movement terms (dolly vs zoom vs pan vs truck), Motion Timing Notation syntax (0-1s / 1-3s / 3-5s), Subject Motion Vocabulary (anticipation / follow-through / micro-expression / weight shift), Continuity Rules 5-piece set, **full-film timeline + recap_previous + continuity_from_previous three-context system** (Seedance is stateless per call; you must manually inject context every shot to prevent character drift in multi-segment videos), Seedance parameter constraints, and per-genre motion templates.
target_agents: [video_prompt_agent]
tags: [video-prompt, seedance, reference-to-video, prompt-engineering, cinematography]
author: filmgenx
---

# 视频镜头 prompt 工程（Industry-Standard Motion Prompt）

业内 1st AD / 镜头组的核心命题：**让 Seedance reference-to-video 按 storyboard 设计意图执行运动**。这不是"写得详细就行"，是要用**行业精确术语 + 分秒级时间轴 + 与参考图分工**——参考图锁静态信息（角色长相 / 场景细节），文字只描述图片无法表达的动态信息（运镜 / 动作 / 节奏 / 起手）。

## 核心信条 / 第一原理

业内做视频生成 prompt 的几条铁律：

1. **图片信息 > 文字**：参考图已经定义了"长什么样"（发型 / 五官 / 服装 / 场景 / 光照）。**文字不要、也不应该**重复这些。文字的职责只有：图片无法表达的**动态信息**。
2. **运镜术语必须精确**：dolly ≠ zoom ≠ pan ≠ truck。模糊词"镜头移动"会让 Seedance 随机选——专业镜头按精确术语写。
3. **Motion Timing Notation 是节奏语言**：用 \`\`0-1s / 1-3s / 3-5s\`\` 这种分秒区间，不写 "slowly" / "then" 这种模糊词。Seedance 按时间段执行，节奏点精确可控。
4. **Subject motion 也有专业词汇**：anticipation / follow-through / micro-expression / weight shift——比"做动作"信息密度高 10 倍。
5. **Continuity 5 件套**：与上一镜的轴线 / eyeline / 主体位置 / 动作匹配 / 光照衔接——剪辑师能不能拼起来全靠这 5 件。
6. **"画面起手"必须锁定**：第 0 秒构图（景别 + 主体位置 + 光影起点）= 模型的"种子"——不锁，运动方向乱来。

## 术语词汇表（业内必备）

| 术语 | 含义 | 通用误用纠正 |
|---|---|---|
| **dolly** | 机座**物理位移**（轨道车），纵深感真实变化 | ≠ zoom——zoom 是光学焦距变 |
| **zoom** | 焦距变，机座不动，图像被光学拉伸 | 看着廉价，专业镜头少用 |
| **pan** | 三脚架上**原地左右转**，机座不动 | ≠ truck（truck 是机座侧向位移） |
| **tilt** | 三脚架上**原地上下转**，机座不动 | ≠ pedestal（pedestal 是机座升降） |
| **truck** | 机座**侧向位移**（平推） | 比 pan 更难，但效果更"沉浸" |
| **pedestal** | 机座**垂直升降** | ≠ crane（crane 是大幅度高度变化） |
| **push-in** | dolly + zoom 联用，纵深与焦距同步 | Hitchcock 的"Vertigo effect" |
| **pull-out** | 反向 push，揭示更大语境 | 高潮后收束 / 失重感 |
| **crane** | 机座大幅度高度变化 | 用于 establishing / 史诗感 |
| **handheld** | 摄影师手持，**organic 抖动** | ≠ shaky—— handheld 是有节奏的 5% 抖动 |
| **steadicam** | 稳定器跟拍，流畅大幅位移 | 一镜到底跟人 |
| **rack focus** | 焦平面切换，机座不动 | 视觉焦点切换技法 |
| **anticipation** | 动作前的微反向（蓄力） | 让动作有起势 |
| **follow-through** | 动作后的余韵（惯性） | 让动作有收势 |
| **micro-expression** | 0.5 秒级表情变化 | 比"表情"信息密度高 |
| **weight shift** | 重心转移 | 让角色"活着"的关键 |

## Camera Movement 精确词汇表

非专业 prompt 写"镜头移动"——模型随机选。专业 prompt 用精确词：

| 术语 | 物理动作 | 视觉效果 | 用在哪 | Seedance prompt 关键词 |
|---|---|---|---|---|
| **static** | 完全不动 | 稳定、聚焦观察 | 对话戏 / 关键宣布前的停顿 | \`\`static camera, no movement\`\` |
| **pan-left / pan-right** | 三脚架原地左右转 | 横扫风景 / 跟随横向运动 | 全景过渡 / 横向追逐 | \`\`smooth pan-right following subject\`\` |
| **tilt-up / tilt-down** | 三脚架原地上下转 | 揭示高度 / 强调对比 | 主角看向天 / 揭示巨物 | \`\`slow tilt-up revealing tower height\`\` |
| **dolly-in** | 机座前推（轨道车） | 物理靠近 + 纵深变化 | 进入空间 / 情绪推进 | \`\`slow dolly-in 0.4x speed, depth perspective\`\` |
| **dolly-out** | 机座后退 | 物理远离 + 纵深变化 | 离开 / 揭示孤立 | \`\`slow dolly-out, retreating perspective\`\` |
| **truck-left / truck-right** | 机座侧向平移 | 平行跟随、保持距离 | 侧面跟跑 / 看穿过物体 | \`\`smooth truck-right tracking subject sideways\`\` |
| **pedestal-up / pedestal-down** | 机座升降 | 改变拍摄高度 | 起立 / 蹲下视角 | \`\`pedestal-up rising from low to eye-level\`\` |
| **push-in** | dolly + zoom 联用 | 强烈聚焦感、心理推进 | 情绪推到顶 / 角色顿悟 | \`\`Hitchcock-style push-in, dolly + zoom synchronized\`\` |
| **pull-out** | 反向 push | 揭示更大语境、失重感 | 高潮后收束 / 反转后退步 | \`\`reverse push-out, sudden depth pull\`\` |
| **zoom-in / zoom-out** | 焦距变，机座不动 | 光学放大 / 缩小，无纵深变化 | 监视感 / 卫星视角；少用 | \`\`optical zoom-in, no camera movement\`\` |
| **crane-up / crane-down** | 机座垂直大幅高度变化 | 史诗感 / 上帝视角 | establishing / 高潮收尾 | \`\`crane-up revealing the entire courtyard\`\` |
| **handheld** | 摄影师手持，5% 抖动 | 真实感 / 紧迫感 | 战斗 / 追逐 / 心理失序 | \`\`handheld camera with 5% subtle shake, organic breathing\`\` |
| **steadicam** | 稳定器跟拍 | 流畅沉浸 | 长镜跟人 | \`\`smooth steadicam following subject, fluid motion\`\` |
| **rack focus** | 焦平面切换 | 视觉焦点切换 | 揭示前后景关系 | \`\`rack focus from foreground to subject at 2s\`\` |

**关键区分**：
- **dolly vs zoom**：dolly 物理位移（纵深感真实变化）；zoom 焦距变（图像被光学拉伸，纵深不变）。专业镜头大多用 dolly
- **push-in = dolly + zoom 联用**：Hitchcock《迷魂记》发明的 Vertigo effect，纵深和焦距同步反向变化制造心理推进感
- **pan vs truck**：pan 原地转头；truck 整个机座侧向位移。truck 更难也更沉浸

## Motion Timing Notation（分秒级时间轴语法）

业内 1st AD 拆镜头按秒数走，你的 prompt 也按这个语法：

\`\`\`
0-1s: <起手状态：构图 + 主体位置 + 光影起点>
1-3s: <运动 + 节奏>
3-5s: <落点状态：构图 + 主体动作收尾>
\`\`\`

例（5 秒镜头）：

\`\`\`
0-1s: static, framing 主角右三分位置 medium-shot, golden-hour 主光从画面 left 45° 打入,
      主角侧脸特写下颌, 玄重尺扛在右肩
1-3s: slow push-in 0.4x speed, 主角缓慢转头面向镜头,
      焦平面从前景柱础移到主角面部 (rack focus)
3-5s: hold on close-up, 主角眼神锁定镜头, 嘴角微抿,
      风吹起发丝, 体积光在背后扩散
\`\`\`

写法注意：
- 时间段用 \`\`0-1s\`\` / \`\`1-3s\`\` 这种**区间**，不要 \`\`at 1 second\`\` 这种点
- 速度用 \`\`0.3x / 0.5x / 1.0x / 1.5x\`\` 这种**倍速**，不写 "slowly"
- 一个镜头**最多 3-4 个时间段**——再多模型抓不住节奏

## Subject Motion Vocabulary（角色动作专业词汇）

角色动作不要写"走过来挥剑"——专业词汇：

| 概念 | 含义 | prompt 示例 |
|---|---|---|
| **anticipation** | 动作前的微反向（蓄力） | "举刀前手腕先 micro-pullback 5cm" |
| **follow-through** | 动作后的余韵（惯性） | "挥剑落下后，身体继续微前倾 1 frame" |
| **micro-expression** | 0.5 秒级表情变化 | "眼神先聚焦, 眉头微皱, 0.3s 后嘴角下沉" |
| **weight shift** | 重心转移 | "重心从右脚移向左脚, 肩部随之微转" |
| **eye-line shift** | 眼神方向变化 | "视线从远处建筑滑回主角自己手中物件" |
| **breath cycle** | 呼吸起伏（静态镜头里加生气） | "胸口轻微 1Hz 起伏, 模拟呼吸感" |
| **subtle sway** | 轻微摆动 | "长袍在风中 0.5Hz subtle sway" |
| **gaze locking** | 眼神锁定 | "gaze locks onto camera at 2.5s" |

这些词汇 Seedance 能直接理解——比"做动作"信息密度高 10 倍。

## 整片时间轴与连贯性（**核心难点，仔细读**）

Seedance 一次最多出 15 秒，60 秒短剧会被拆成 4-8 个独立视频。**每个 generate_video 调用 Seedance 都是冷启动**——它不知道当前在整片的哪个时间点、前一镜发生了什么、上一镜结尾画面里主角在哪、什么情绪。

**这是人物漂移 / 剧情断裂的根源**。下游 video_prompt_agent 的工作是在每个 prompt 里**手动注入三层上下文**，让独立视频拼起来像一部连贯的片子。

### 三个上下文字段（VideoPrompt schema 字段）

| 字段 | 必填条件 | 内容 |
|---|---|---|
| \`\`time_start_seconds\`\` | 所有镜 | 本镜在整片的**绝对起始秒**（与 storyboard.shots[i].time_start_seconds 一致） |
| \`\`time_end_seconds\`\` | 所有镜 | 本镜在整片的**绝对结束秒**（= time_start + duration） |
| \`\`recap_previous\`\` | 除第 1 镜 | 前面剧情 1-2 句 ≤80 字，让 Seedance 理解"主角现在为什么这样" |
| \`\`continuity_from_previous\`\` | 除第 1 镜 | 与上一镜的视觉衔接：主体位置 / 动作落点 / 情绪 / 光照方向 |

### motion_description 开头三件套（**实际写进 prompt 的格式**）

光填字段不够——Seedance 读的是 prompt 文本，必须把这三个信息**塞进 motion_description 开头三段头**：

\`\`\`
[TIME: 整片第 10-15s（共 60s）]
[RECAP: 萧炎在云岚宗广场被纳兰嫣然嘲讽，黑炎在指间凝聚]
[CONTINUITY: 上一镜萧炎右掌微抬黑炎初现；本镜衔接掌心黑炎已成球，
纳兰嫣然在画面右三分位惊退半步，光照仍为黄昏侧逆主光从画面左 45°]

0-1.5s: low-angle medium shot, 萧炎在画面左三分位, 长袍黑炎纹路随风微动,
       黑炎球悬于右掌上方 30cm 缓慢自转, 边缘暗红熔岩纹流转; 纳兰嫣然在画面
       右三分位, micro-expression 眉头紧锁瞳孔放大, 长剑斜指地面.
1.5-3s: slow dolly-in 0.5x toward 萧炎, weight shift 重心移向右脚, 黑炎球
       突然胀大至篮球大小 (anticipation 蓄势), 衣袖被气浪吹起; 焦点 rack focus
       从黑炎球缓慢拉到萧炎眼神, 瞳孔聚焦如刀.
3-5s: 萧炎右臂猛然下劈 (follow-through 余韵衣袂残影), 黑炎球化为环形冲击波
       向画面右侧辐射, 地面青砖龟裂飞溅; 纳兰嫣然 weight shift 后撤一步举剑
       格挡, 剑身青芒颤动.
voiced lines:
- 萧炎: "你说什么？" (压低嗓音、咬字, 0.8s 长度)
- 环境: 黑炎自燃噗噗声、地面碎裂轰隆、衣袂猎猎
\`\`\`

字段填了又在 motion 里重复——**不冗余**。字段是给 reviewer / 审稿用的结构化记录；motion_description 才是真正喂给 Seedance 的文本。两套并存。

### 三层信息源严格分工（**避免与参考图冲突**）

你的输入有三层信息源，**职责完全不重叠**——搞混就会和参考图打架，Seedance 必崩。

| 信息源 | 含什么 | 用法 |
|---|---|---|
| **① 参考图（asset_codes）** | 角色外观（发型/五官/服装/iconography）、场景结构、基础光照、配色 | 不进 prompt 文本，传给 \`generate_video(asset_codes=[...])\` 即可 |
| **② 项目 KV（character.\*/scene.\*/style.\*）** | 上述参考图的文字描述版（appearance / base_prompt / clothing_detail / atmosphere ...）| **只用来做三件事**：(a) 选哪张参考图变体；(b) 写 continuity_from_previous 衔接；(c) 推断未覆盖角色 / 场景的合理外观（罕见）|
| **③ motion_description** | 动作时序、运镜、节奏、micro-expression、台词、环境响应 | 工具自动加别名头，只写动态信息 |

**KV 不是 motion 的抄写源**——它存在是为了让你选对参考图、写对衔接，不是让你把 \`character.萧炎.appearance\` 里的"青年男子，黑发束起，玄铁色长袍"复制到 motion_description 里。

### 三类参考图冲突（踩了画面必崩）

| 冲突类型 | 例子 | 后果 |
|---|---|---|
| **冗余型** | motion 写"萧炎穿玄铁色长袍，黑发束起" | 参考图已有，浪费 prompt 预算 + 模型注意力分散 |
| **矛盾型** | 参考图选 angry 变体，motion 写"萧炎温柔微笑" | Seedance 不知道听谁的，五官扭曲 / 表情漂移 |
| **凭空型** | motion 写"萧炎左手戴红玉佩"（参考图无、KV 无）| 强行生成 → 与参考图风格断裂 / 道具突兀 |

### 文字职责清单

| ✅ 文字必须写 | ❌ 文字禁止写（参考图已有） |
|---|---|
| 运镜（dolly-in / pan / push-in ...）| 角色发型 / 发色 / 五官形状 |
| 时间分段（0-1s / 1-3s 各做什么）| 角色基本服装（玄铁色长袍 / 战斗服等）|
| micro-expression（瞬时变化）| 角色配饰静态（红玉佩等，除非有变化）|
| weight shift / anticipation / follow-through | 场景建筑结构（飞檐殿宇等）|
| 环境响应（衣袂 / 尘 / 光斑 / 雾气）| 场景基础光照（黄昏侧逆等基础描述）|
| 台词（含语气 / 长度）| 整片色调（teal-orange / 低饱和等，visual_style 锁定）|
| CONTINUITY 衔接（**这里允许提光照 / 主体位置作为衔接信号**）| 任何参考图能用 1 张静态图表达的细节 |

### 怎么避免冲突

- **想描述外观？先看参考图能不能表达** —— 能 → 用参考图（挑变体或重出）；不能 → 也别在 motion 里硬塞，跟 character_ref_agent 提一次让它补
- **想描述瞬时变化？这才是 motion 的职责** —— 表情从平静→愤怒、衣袂随风扬起、黑炎从指尖凝聚成球 ... 参考图表达不了的动态信息
- **同样写"光照"** —— 参考图已有的"黄昏侧逆主光"motion 里**不重复**；但 continuity_from_previous 里写"光照延续黄昏侧逆"是**衔接信号**，不算冗余
- **简单记法**：参考图能用 1 张静态图表达的，文字不要再写；只描述"这张图动起来会发生什么"

### 别名约定（**禁止重复别名映射段**）

你**直接用中文名**写角色 / 场景（"萧炎"、"纳兰嫣然"、"云岚宗广场"）——\`generate_video\` 工具会**自动**在 prompt 头部前置一行：

\`\`\`
素材引用：萧炎=@图片1，纳兰嫣然=@图片2，云岚宗广场=@图片3

[TIME: ...]
[RECAP: ...]
... 你的 motion_description 主体 ...
\`\`\`

Seedance 据此把中文名桥接到对应参考图。

**禁止**在你写的 motion_description 里再加这种段：

❌ \`\`[Character Reference] 萧炎=@图片1, 纳兰嫣然=@图片2\`\`
❌ \`\`[Scene Reference] 云岚宗广场=@图片3\`\`
❌ \`\`@图片1=萧炎，@图片2=纳兰嫣然\`\`（任何形式的别名映射）

这些是**重复 + 浪费 prompt 预算**——工具已经在头部加过了。你 prompt 正文里写"萧炎挥剑刺向纳兰嫣然"就够了。

### 质量门槛：什么样的 motion_description 才算"专业级"

业内 Seedance prompt 工程的经验值：

| 维度 | 不及格 | 及格 | 专业级 |
|---|---|---|---|
| **总长度** | < 80 字 | 80-150 字 | **150-300 字** |
| **时间分段数** | 1-2 段 | 2-3 段 | **3-5 段** |
| **专业动作词** | 0 个 | 1-2 个 | **≥ 4 个** |
| **构图细节** | "中景" | "中景 + 三分位" | **景别 + 主体位置 + 焦段 + 光照方向**齐全 |
| **环境互动** | 无 | "风吹起" | **多层环境响应**（衣袂 / 头发 / 尘土 / 光斑 / 雾气至少 2 层） |
| **台词与音轨** | 缺 | 单纯写台词 | **台词 + 语气 + 长度 + 环境音清单** |

每个镜头**至少到"及格"线**，重点镜头（高潮 / 决定性镜头）必须"专业级"。低于"及格"= Seedance 出片必然崩。

### 不及格反例（真实 Agent 产出，质量崩）

\`\`\`
[TIME: 10-12s] [RECAP: 萧炎暴力压制纳兰] [CONTINUITY: 特写后双方拉开;本镜全景对冲]
[Character Reference] 萧炎=@图片1, 纳兰嫣然=@图片2 [Scene Reference] 云岚宗广场=@图片3
[Visual Style] Teal-orange clash, wide depth. [Technical Notes] WS, pull-out.
[Action] 0-2s: 两人借力向两侧拉开. 纳兰在右长剑指天聚起刺眼青芒.
        2-5s: 萧炎在左跃起挥出黑红满月焰浪, 两股能量向画面中央极速对冲.
[Audio] 高频能量尖啸. 台词:"破！"
\`\`\`

诊断：

1. ❌ 重复别名段（\`[Character Reference]\` / \`[Scene Reference]\`）—— 工具已经在头部自动加了
2. ❌ 总长仅 ~80 字，Action 段只有 2 个时间点（0-2s / 2-5s）—— 粒度过粗
3. ❌ 0 个专业动作词（anticipation / follow-through / weight shift 全无）
4. ❌ \`RECAP: 萧炎暴力压制纳兰\` 6 字 —— 上下文太薄
5. ❌ \`[Visual Style]\` 段重复（visual_style_agent 已锁定，参考图也含）—— 浪费 prompt
6. ❌ \`[Technical Notes]\` 段冗余（aspect_ratio / quality 走字段，运镜应融入 Action 时间段）
7. ❌ 台词只有 "破！" 没有语气 / 长度 / 环境音清单

### 衔接清单（每镜对上一镜检查 6 项）

写 continuity_from_previous 时**逐项检查**：

1. **主体位置接续**：上一镜主角在画面右三分位 → 本镜起手时主角仍在右三分（除非有明确切换设计）
2. **动作落点接续**：上一镜结尾握拳 → 本镜起手仍是握拳（再展开新动作）
3. **情绪连续**：上一镜怒 → 本镜起手仍是怒（不能突然变笑）
4. **光照方向接续**：同场戏光源方向一致（黄昏侧逆光别下镜变正面顶光）
5. **服装 / 道具状态接续**：上一镜剑出鞘 → 本镜剑在手里（不能突然回鞘）
6. **眼神方向接续**（eyeline match）：上一镜看右 → 本镜如切到他看到的画面，从他视点出发

### 跨场切换（scene 边界）

如果当前镜头跨入新 scene（time-of-day 变了、location 变了），continuity_from_previous 显式标注：

\`\`\`
[CONTINUITY: 跨场转入。上一镜在云岚宗广场夜景结尾主角离开画面右侧；
本镜场景切到清晨山道，主体新构图：主角在画面左三分位行走，
光照转为晨雾漫散]
\`\`\`

跨场允许，但**必须显式说明**——不要让 Seedance 突然换地方却不告诉它"这是有意的"。

### 按 time_start 升序逐镜调用 generate_video

严禁**乱序 / 并行**调用 generate_video。必须：

1. 先调 shot 1（time_start=0）→ 拿到 vid-xxxxxxxx-1
2. 再调 shot 2（time_start=3）→ 此时可以引用"上一镜实际生成了 vid-xxxxxxxx-1，结尾画面是 ..."写 continuity
3. ...
4. 最后调 shot 8

为什么按顺序？因为后面镜的 recap / continuity 依赖前一镜实际的产出——如果先调 shot 5 你不知道 shot 4 拍成什么样了，continuity 就只能凭想象写。

## Continuity Rules（连贯性 5 件套）

每个镜头必须考虑与**上一镜**的衔接：

1. **轴线一致（180° rule）**：除非主观视点切换，否则保持同一条 axis-of-action。prompt 里给主体相对位置（"主角左侧、对手右侧"）
2. **eyeline match**：A 看 B，B 也看 A，眼神方向必须对得上。prompt 写明角色看向哪边
3. **match on action**：动作起点 cut 到动作落点——cut 前 0.5s 主角抬手，cut 后 0.5s 手举到顶。prompt 给"动作的什么阶段"
4. **主体位置稳定**：cut 前后主体大致在画面同一区域（除非有意做 jump cut）
5. **lighting continuity**：同一场戏不同镜头光照方向一致（除非时间跨越）

写 prompt 时**主动提及**这些点，否则 Seedance 各拍各的，剪辑师拼起来动作不连贯。

## "画面起手"为什么关键

Seedance 虽然有参考图保证角色 / 场景一致性，但**镜头起手的构图 / 景别 / 主体位置 / 光影起点**得靠 prompt 写明，否则模型自由发挥起手画面，会和你预期的镜头语言对不上。

正确做法：**前 1-2 句明确锁定起手构图**：

\`\`\`
0-1s: {景别（medium-shot / wide / close-up）} + {主体在画面中位置（左三分 / 居中 / 右三分）}
      + {光影方向（主光从 left 45°）} + {关键道具位置},  ← "种子"
1-3s: {运动开始 + 节奏 + 速度倍率},                       ← "运动"
3-5s: {落点状态 + 表情 / 微动作收尾}                       ← "收尾"
\`\`\`

**不要复述参考图里能看到的细节**（服装 / 长相 / 场景结构）——浪费 prompt 预算，反而干扰模型。

## Seedance 参数规则（硬约束）

| 参数 | 允许值 | 备注 |
|---|---|---|
| \`\`duration_seconds\`\` | **4-15 整数** | 越界 Seedance 直接拒绝 |
| \`\`aspect_ratio\`\` | \`\`16:9\`\` / \`\`9:16\`\` / \`\`1:1\`\` / \`\`4:3\`\` / \`\`3:4\`\` / \`\`21:9\`\` | 必须与对应 storyboard.shot 一致 |
| \`\`asset_codes\`\` | **必填**，从 character.* / scene.* 取 | 参考图保证一致性；不能为空 |
| \`\`generate_audio\`\` | **传 True**（默认） | 开启对白 / 环境音；字幕规则见下方"声音/字幕"段 |
| \`\`quality\`\` | \`\`std\`\` / \`\`hq\`\` | std=720p, hq=1080p; hq 额度贵 |

### duration 选择规则

storyboard.duration_seconds 是设计意图，video_prompt.duration 是 Seedance 实际生成时长——两者不必完全一致：

| storyboard.duration_seconds | video_prompt.duration | 理由 |
|---|---|---|
| 1-3 秒（快切） | 5 | Seedance 最短 4 秒；统一取 5 后剪辑时再裁短 |
| 4-6 秒 | 5 | 直接对齐 |
| 7-10 秒 | 8-10 | 长镜要求 |
| 11-15 秒 | 12-15 | 极少数特殊高潮 |
| > 15 秒 | 拆分成多段 | 单个镜头超过 Seedance 限制 |

### quality 分配（额度有限）

短剧（60 秒）按这个比例分配：

| 镜头类型 | quality | 占比 |
|---|---|---|
| 高潮 / 转场 / 情感顶点 | hq | 20-30% |
| 关键叙事 / 角色 close-up 运动 | hq | 视情况 |
| 常规过场 / 简单运镜 | std | 60-70% |

**不要全 hq**——60 秒短剧 12-15 个 video shot 全 hq 会爆额度。

## 声音 / 字幕规则（**容易踩坑，仔细读**）

FilmGenX 产出的视频会进入后期人工剪辑——**音视频可剥离**（mute 一下就拿到纯画面），但**字幕一旦烧进画面就盖在像素上、无法移除**。所以约束**非对称**：

### 声音层（默认开启，允许出）

- \`\`generate_audio\`\` **传 True**（默认值，不要改成 False）
- 角色对白 / 人声**需要**——剧本里有台词的镜头，在 motion_description 里**写明角色说什么**，让 Seedance 同步出对白音轨
- 环境音 / 动作音允许（风声 / 雨声 / 脚步 / 武器碰撞 / 火焰嘶嘶 / 衣物摩擦）
- **BGM / 配乐留给后期**：Seedance 生成的 BGM 通常廉价不可控；prompt 里**不要主动要求 BGM / 配乐 / 鼓点**，让 Seedance 默认只出人声 + 环境音

### 视觉文字层（绝对禁止，烧进像素就报废）

motion_description **禁止**出现任何"画面文字层"指令：

- 字幕（subtitle / caption / 台词字幕条）
- 标题卡 / 片头字（title card / opening title / chapter title）
- 文字水印 / Logo / 角标
- 强调文字 / 弹幕 / 文字标注 / 文字特效

即使台词需要呈现，**字幕也不烧进视频**——后期剪辑会单独贴字幕轨道。你的工作是让对白通过**音轨**传达。

⚠️ **场景内的自然文字 ≠ 字幕**：招牌 / 横幅 / 书页 / 手机屏幕显示的字 —— 这些是**画面内容**本身，允许保留；字幕指的是"叠加在画面上的解说层"。

### 简单记法

> 声音可剥离 → **允许**生成（generate_audio=True）
> 字幕烧像素 → **禁止**生成

## 反例 / 陷阱（**仔细读**）

### ❌ 反例 1：重复参考图静态信息

\`\`\`
"主角穿着玄铁色长袍，黑发束起，背着玄重尺，在云岚宗广场静静站立，
然后慢慢转身……"
\`\`\`

**后果**：参考图里已经有了服装 / 长相 / 场景——前半段全是浪费 prompt 预算。模型反而被干扰。

**正例**：

\`\`\`
0-1s: static, medium-shot, subject right-third position, golden-hour key light from left 45°
1-3s: slow rotation 0.5x, weight shift from right to left foot, gaze lifting
3-5s: hold on close-up, gaze locks camera, micro-expression: jaw tightens
\`\`\`

### ❌ 反例 2：用模糊词

\`\`\`
"镜头移动，然后角色做动作"
\`\`\`

**后果**：模型不知道 dolly 还是 zoom 还是 pan，随机选——拍出来运镜不一致。

**正例**：用精确术语（参考上面的 13 个 camera movement 表）+ 时间区间 + 速度倍率。

### ❌ 反例 3：缺 Timing Notation

\`\`\`
"主角先静止，然后转身，最后停在表情上"
\`\`\`

**后果**："先 / 然后 / 最后"是模糊节奏点，Seedance 不知道每段几秒。

**正例**：

\`\`\`
0-2s: static, medium-shot
2-4s: 180° turn, 0.6x speed, weight shift mid-turn
4-5s: hold on close-up, gaze locked
\`\`\`

### ❌ 反例 4：subject motion 写"做动作"

\`\`\`
"主角挥剑攻击"
\`\`\`

**后果**：没 anticipation（蓄力）/ follow-through（余韵）/ weight shift（重心）——动作生硬。

**正例**：

\`\`\`
0-0.5s: anticipation, micro-pullback of sword arm
0.5-1.5s: forward swing 1.2x speed, motion-blur trail on blade
1.5-2s: follow-through, body weight continues forward, blade arrests at full extension
2-3s: gaze locks on target, breath cycle visible
\`\`\`

### ❌ 反例 5：违反 Continuity

上一镜主角在画面**左侧**面对**右侧**反派，本镜主角突然出现在**右侧** → 跨轴 = 观众迷失。

**正例**：prompt 里写明 "subject remains on screen-left, opponent on screen-right, maintaining 180° rule from previous shot"。

### ❌ 反例 6：把字幕烧进画面

\`\`\`
"画面下方出现字幕'萧炎登场'，右上角浮现 logo"
\`\`\`

**后果**：Seedance 真的会把字幕和 logo 烧进画面像素 → 字幕无法剥离 → 整段镜头报废。

**正例**：

\`\`\`
0-2s: static medium-shot, 主角侧脸特写, golden-hour 主光
2-4s: slow push-in 0.5x, 主角缓慢转身面向镜头
4-5s: hold on close-up
voiced line: "我萧炎回来了。" (角色对白通过音轨传达，不烧字幕)
\`\`\`

generate_audio=True，对白进音轨；后期剪辑会单独贴字幕轨道。

### ❌ 反例 7：主动要求 BGM

\`\`\`
"伴随激昂配乐，节奏感强烈的鼓点，随节拍切镜"
\`\`\`

**后果**：Seedance 生成的 BGM 风格廉价不可控；"随节拍切镜"会让模型按音乐决定运动方向。

**正例**：

\`\`\`
0-2s: static medium-shot
2-4s: dolly-in 0.5x
4-5s: hold on close-up
ambient: 风声、衣物摆动音 (环境音允许，BGM 留给后期人工配乐)
\`\`\`

## 何时加载附加资料

按以下规则**按需**触发工具调用：

- 想用 Seedance-tested 的精确运镜关键词（哪些 Seedance 表现稳定 / 哪些不稳定） → 加载 @ref:seedance-camera-motion-cheatsheet
- 镜头节奏拆分（5 秒 / 10 秒不同类型如何分时间段） → 加载 @ref:motion-pacing-templates
- 经典镜头模板（OTS 对话四步切 / push-in to revelation / Hitchcock Vertigo effect） → 加载 @skill:cinematic-composition#shot-pattern-templates
- 不熟悉某个运镜术语的物理执行（push-in 标准速度 / dolly track 配什么焦距） → 加载 @skill:cinematic-composition
- 镜头里需要复杂的角色 micro-expression / 身体语言 → 加载 @ref:subject-motion-vocabulary

## 常见运镜模板

### static（静止 / 标准对话）

\`\`\`
镜头静止保持 medium shot 不动, 不推不拉不摇.
适用: 对话戏, 仪式感, 抒情戏长镜.
\`\`\`

### pan（横摇 / 跟随）

\`\`\`
镜头以中速 pan {左→右 / 右→左}, 跟随主体平移, 揭示空间.
适用: 揭示场景, 角色行走, 空间过渡.
\`\`\`

### tilt（俯仰摇）

\`\`\`
镜头以缓慢 tilt {上→下 / 下→上}, 揭示高度差.
适用: 展现建筑高度, 权力关系仰拍, 揭示天空 / 地面.
\`\`\`

### dolly_in（推进）

\`\`\`
镜头以中速 dolly in 推进, 从 long shot 推到 medium close-up, 介入角色情绪.
适用: 情绪升级, 决心时刻, 揭示真相前的预备.
\`\`\`

### dolly_out（拉远）

\`\`\`
镜头以缓慢 dolly out 拉远, 从 close-up 拉到 long shot, 角色逐渐渺小.
适用: 离别, 揭示孤立, 结尾场景.
\`\`\`

### whip_pan（急摇）

\`\`\`
镜头以极快 whip pan 切换, 用动作模糊连接两个画面.
适用: 转场, 时空跳跃, 动作戏过渡.
\`\`\`

### handheld（手持）

\`\`\`
镜头以手持轻微抖动跟随主体, 真实感, 紧张感.
适用: 紧张戏, 第一人称感, 现实主义.
\`\`\`

### crane（升降）

\`\`\`
镜头从低位 crane up 升起, 揭示全景或转换视角.
适用: 开场, 结尾, 仪式感时刻.
\`\`\`

### zoom_in（变焦推近）

\`\`\`
镜头 zoom in (不是物理移动), 突出心理变化或细节.
适用: 心理戏, 特定道具特写, 复古电视感.
注意: 慎用. 现代电影感少用.
\`\`\`

## 常见角色动作模板

### 战斗动作

\`\`\`
主角举武器, 蓄力 1 秒, 挥下时武器尾随光迹, 击中目标产生粒子爆发.
英文 tag: character raises weapon, charges energy 1 sec, swings down with motion blur trail, particle explosion on impact
\`\`\`

### 释放招式 / 异能

\`\`\`
主角双手聚气, 手心光球渐大, 双色异火融合, 释放冲击波.
英文 tag: character channels energy, palm glows brighter, two-color flames merge, releases shockwave
\`\`\`

### 转身 / 揭示表情

\`\`\`
主角缓慢转身, 头先转, 身体跟随, 表情从平静过渡到 determined, 视线锁定.
英文 tag: character slowly turns around, head first, body follows, expression transitions from calm to determined, locked gaze
\`\`\`

### 行走 / 离开

\`\`\`
主角缓慢迈步前进, 步速节奏稳定, 长袍 / 头发飘动.
英文 tag: character walks forward at steady pace, robes / hair flowing, determined posture
\`\`\`

### 摔倒 / 受击

\`\`\`
主角被击中, 身体后仰, 武器脱手飞出, 着地腾起尘土.
英文 tag: character takes hit, body recoils backward, weapon flies out of grip, dust kicks up on impact
\`\`\`

### 抒情 / 静默

\`\`\`
主角静止, 仅风吹动头发 / 衣物, 眼神缓慢眨动, 微表情变化.
英文 tag: character stands still, hair / clothes drift in wind, slow blink, subtle facial micro-expression shift
\`\`\`

## 反例

- motion_description 写"角色移动"——通用描述, 模型乱画
- duration_seconds 越界（不在 4-15）——Seedance 拒绝
- aspect_ratio 与 storyboard.shot 不一致——画面拉伸
- 漏写画面起手——起手构图全靠模型自由发挥
- 全部 quality=hq——额度爆掉
- 把参考图能看到的细节（服装 / 场景结构）整段复述进 prompt——重复信息, 浪费 prompt 长度
- asset_codes 列表为空——Seedance reference-to-video 直接拒绝

## 工作流（强调先口头说明再调用工具）

每次准备调 \`\`load_skill_reference\`\` / \`\`generate_video\`\`：
1. 本轮先口头说明意图 + 理由
2. 下一轮才调工具

例：
> "我打算只对镜头 7（佛怒火莲释放）和镜头 12（决战收尾）做 generate_video 验证。这两镜是高潮 + 收尾, 运动复杂, 担心 prompt 写得不够具体. 下一步先用镜头 7 跑一次（duration=5, quality=hq）, 看异火融合的运动是否到位, 不到位再调整 prompt 重跑."

## reference: seedance-camera-motion-cheatsheet

Seedance 2.0 reference-to-video 实测表现的运镜关键词（中英对照 + 稳定性评级）：

| 中文 | 英文 prompt 关键词 | Seedance 表现 | 备注 |
| --- | --- | --- | --- |
| 静止 | \`\`static camera, no movement\`\` | ⭐⭐⭐⭐⭐ 稳定 | 完全可控，常用 |
| 缓慢推进 | \`\`slow dolly-in 0.4x, depth perspective\`\` | ⭐⭐⭐⭐⭐ 稳定 | 写明速度倍率更稳 |
| 缓慢拉远 | \`\`slow dolly-out 0.4x, retreating depth\`\` | ⭐⭐⭐⭐⭐ 稳定 | 同上 |
| 横移跟随 | \`\`smooth pan-right following subject, 0.6x speed\`\` | ⭐⭐⭐⭐ 较稳定 | 跟随时主体位置要写明 |
| 侧向跟随 | \`\`truck-right tracking subject sideways\`\` | ⭐⭐⭐ 中等 | 比 pan 难，但更沉浸 |
| 仰角推进 | \`\`low-angle dolly-in 0.5x, looking up\`\` | ⭐⭐⭐⭐⭐ 稳定 | 角度 + 运动一起写更稳 |
| 俯角拉远 | \`\`overhead pull-out, bird's eye perspective\`\` | ⭐⭐⭐⭐ 较稳定 | 高度变化大时易抖 |
| 手持跟拍 | \`\`handheld camera with 5% subtle shake\`\` | ⭐⭐⭐⭐ 较稳定 | 写明抖动幅度防过晃 |
| Push-in | \`\`Hitchcock push-in, dolly + zoom synchronized\`\` | ⭐⭐⭐ 中等 | 描述 Vertigo effect 更清晰 |
| Rack focus | \`\`rack focus from foreground to subject at 2s\`\` | ⭐⭐⭐ 中等 | 必须写明焦平面切换时机 |
| 升降镜 | \`\`crane-up 1.0x, revealing courtyard\`\` | ⭐⭐⭐⭐ 较稳定 | 写明终点构图更稳 |
| 急速横摇 | \`\`whip pan transition, 2x speed\`\` | ⭐⭐ 不稳定 | 常被忽略，慎用 |
| 360 环绕 | \`\`orbit around subject, full 360°\`\` | ⭐⭐ 不稳定 | 主体容易变形，避免 |
| 急速变焦 | \`\`fast zoom-in / zoom-out\`\` | ⭐⭐ 不稳定 | 看着廉价，专业镜头慎用 |

**Seedance 的稳定运动公式**：
- ✅ 单一明确运动 + 速度倍率 + 起止状态
- ✅ 与 timing notation 配对（"0-1s static, 1-3s slow dolly-in 0.4x"）
- ❌ 多个运动串联（dolly + tilt 同时 / 一镜内两次方向切换）—— Seedance 容易"做一半"
- ❌ 模糊速度词（"quickly" / "slowly"）—— 用 0.3x / 0.5x / 1.0x / 1.5x 倍率

**Seedance 不擅长**：
- 复杂复合运镜（dolly + tilt 同时）
- 一镜内超过 2 个方向切换
- 360 环绕（主体变形）
- 急速变焦（结果模糊）

## reference: subject-motion-vocabulary

角色动作的专业词汇——比"做动作"信息密度高 10 倍。

### 动作起势 / 收势

| 概念 | 含义 | prompt 示例 |
|---|---|---|
| **anticipation** | 动作前的微反向（蓄力） | "举刀前手腕先 micro-pullback 5cm at 0-0.3s" |
| **follow-through** | 动作后的余韵（惯性） | "挥剑落下后, 身体微前倾 1 frame, 长袍延迟摆动 0.2s" |
| **overshoot** | 超出目标后回弹 | "拳头挥到目标后 overshoot 10cm 再回弹" |
| **secondary motion** | 次要部位的延迟运动 | "头发 / 长袍 / 飘带 secondary motion delayed by 0.3s" |

### 微表情 / 眼神

| 概念 | 含义 | prompt 示例 |
|---|---|---|
| **micro-expression** | 0.5 秒级表情变化 | "eye narrowing → brow micro-tense → lip corner drops, 0.4s cycle" |
| **eye-line shift** | 眼神方向变化 | "gaze drifts from distant tower to subject's own hands over 1s" |
| **gaze locking** | 眼神锁定 | "gaze locks onto camera at 2.5s with breath catch" |
| **blink cycle** | 眨眼节奏（静态镜头加生气） | "slow blink at 1.5s, conveys exhaustion" |

### 身体语言

| 概念 | 含义 | prompt 示例 |
|---|---|---|
| **weight shift** | 重心转移 | "weight shifts from right foot to left, shoulders follow 0.2s later" |
| **posture collapse** | 姿态崩塌（失败 / 绝望） | "shoulders drop, spine curves, knees soften over 1s" |
| **breath cycle** | 呼吸起伏 | "chest 1Hz subtle rise-fall, modeling breathing tension" |
| **micro-tremor** | 微颤抖（恐惧 / 愤怒 / 寒冷） | "hand 8Hz micro-tremor visible at fingertips" |
| **subtle sway** | 轻微摆动 | "robe 0.5Hz subtle sway from passing wind" |

### 行走 / 移动

| 概念 | 含义 | prompt 示例 |
|---|---|---|
| **gait rhythm** | 步态节奏 | "steady 1.2s/step gait, determined posture" |
| **footfall weight** | 踩地分量感 | "heavy footfall, slight dust kick-up on each step" |
| **glide vs march** | 飘移 vs 行军 | "glides forward (no apparent footfall) — vs — marches with deliberate weight" |

这些词汇 Seedance 能直接消费——比"做动作"信息密度高 10 倍。

## reference: motion-pacing-templates

5 种常见镜头节奏模板，按 5 秒和 10 秒拆解：

### 5 秒爆发型（动作戏）

\`\`\`
0-1秒: 静止建立 (起手画面)
1-3秒: 主动作执行 (挥武器 / 释放招式 / 转身)
3-5秒: 余波 + 表情 (击中后烟尘 / 表情切换 / 武器停顿)
\`\`\`

### 5 秒抒情型（情绪戏）

\`\`\`
0-2秒: 静止微动 (风吹头发 / 缓慢眨眼)
2-4秒: 表情过渡 (平静→悲伤 / 决心→释然)
4-5秒: 微表情定格 (眼角泪光 / 嘴角微扬)
\`\`\`

### 5 秒推镜型（情绪升级）

\`\`\`
0-1秒: long shot 静止
1-4秒: 缓慢 dolly in 到 medium close-up
4-5秒: 停在 close-up 的表情
\`\`\`

### 10 秒长镜型（仪式感）

\`\`\`
0-2秒: 起手画面建立
2-4秒: 角色动作起步
4-6秒: 主动作展开 (招式 / 对峙 / 行走)
6-8秒: 高潮点 (击中 / 决断 / 揭示)
8-10秒: 收尾 (余波 / 镜头停顿 / 转场预备)
\`\`\`

### 10 秒揭示型（开场 / 结尾）

\`\`\`
0-2秒: 局部细节特写
2-5秒: crane / zoom out 揭示更大场景
5-8秒: 角色出现 / 走入画面
8-10秒: 全景定格
\`\`\`


## 成片拼接（concat_videos）—— 最后一步出整片

Seedance 单段 4-15 秒，60 秒短剧会被拆 4-8 段独立生成。所有分段都返回 vid- 后，**必须用 \`concat_videos\` 工具按 storyboard.time_start 升序拼成完整片**——否则剪辑师拿到的是一堆碎片，不是成片。

### 工具签名

\`\`\`
concat_videos(
  asset_codes: list[str],     # 按播放顺序排好的 vid- 列表（≥ 2 段）
  name: str,                  # 必填，前端 asset library 卡片标题
  description: Optional[str], # 给成品 asset 的描述
  tags: Optional[list[str]],  # 新 asset 的标签
) -> {
  success, asset_code,        # 新分配的 vid-<uuid>（成片 code）
  asset_id, url,
  total_duration_seconds,
  segment_count,
  aspect_ratio,
  source_codes,
}
\`\`\`

### 调用时机

**Wrap 阶段，所有 generate_video 都已返回 vid 后**：

1. 在内存里维护 \`shot_number → vid-<uuid>\` 映射（**别忘了——Seedance 异步出片，返回顺序不一定是调用顺序**）
2. 按 storyboard.time_start 升序排好 vid 列表
3. 一次调用 concat_videos，传入有序列表

### 调用示例

\`\`\`
# 假设 storyboard 是 60 秒短剧 8 个 shot，每个 shot 都 generate_video 出了 vid
# 在内存里记下：
shot_to_vid = {
  1: "vid-abc1",  # storyboard.shots[0].time_start = 0
  2: "vid-def2",  # time_start = 3
  3: "vid-ghi3",  # time_start = 8
  4: "vid-jkl4",  # time_start = 12
  5: "vid-mno5",  # time_start = 20
  6: "vid-pqr6",  # time_start = 35
  7: "vid-stu7",  # time_start = 45
  8: "vid-vwx8",  # time_start = 55
}

# 按 time_start 升序排好
ordered_vids = [shot_to_vid[i] for i in range(1, 9)]

# 调一次 concat_videos
concat_videos(
  asset_codes=ordered_vids,
  name="云岚宗短剧·完整 60s",
  description="由 8 个分镜拼接，总时长 60s",
  tags=["final-cut", "ep1"]
)
# → {success: True, asset_code: "vid-finalcut", total_duration_seconds: 60,
#    segment_count: 8, aspect_ratio: "16:9", source_codes: [...]}
\`\`\`

### 校验（工具会拒，你别误用）

| 错误码 | 触发条件 |
|---|---|
| ASSET_CODES_TOO_FEW | 少于 2 段（单段不需要拼） |
| ASSET_CODES_NOT_FOUND | 列表里有 code 不在本 project 的 assets 表 |
| ASSET_NOT_VIDEO | 有 code 是 image 类型（图片混进来了） |
| ASPECT_RATIO_MISMATCH | 分段画幅不一致（16:9 + 9:16 混入）——必须先重出统一画幅 |
| FFMPEG_FAILED | 服务器 ffmpeg 异常或源视频编码差异 |

### 工作原理

- 工具内部用 ffmpeg concat demuxer
- 默认走 \`-c copy\`（零损失零编码，前提是所有 Seedance 出片编码参数一致——通常满足）
- copy 失败自动 fallback 到 \`-c:v libx264 -c:a aac\` 重编码
- 产物落 assets 表，标 \`generator=concat_videos\` + \`tags=[concat, segments:N]\`——后期在 asset library 里能识别

### 反例 / 陷阱

❌ **按 generate_video 返回先后传 asset_codes**——Seedance 异步出片，先返回的不一定是 shot 1
✅ **按 storyboard.time_start 升序传**——这是唯一正确的顺序

❌ **混入图片 asset_code（img- 前缀）**——concat_videos 只接受 video，会被拒
✅ **只传 vid- 前缀的 video asset_code**

❌ **画幅不一致还想拼**——某段是 9:16 其它是 16:9，拼出来 90% 是畸形
✅ **先重出不一致的镜头到统一 aspect_ratio**，再拼

❌ **只有 1 段还调 concat_videos**——工具会拒（ASSET_CODES_TOO_FEW）
✅ **单段直接用，跳过拼接步骤**

❌ **拼完忘了把成片 asset_code 告诉用户**——拼接成果应该体现在 wrap 阶段的输出
✅ **拿到 vid-finalcut 后，明确告知"成片 asset_code 是 vid-finalcut，时长 60s"**
`;


const SEEDANCE_PROMPT_GUIDE = `---
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

\`\`\`
[Subject 主体]: 谁 / 什么。锁定角色五官 / 服装 / 物体材质（这部分主要靠参考图，文字补关键差异）
[Action 动作]:  做什么。肢体 / 表情 / 物体运动的连贯序列（强调"自然 / 缓慢 / 流畅"）
[Camera 运镜]: 镜头怎么动。用官方词汇（dolly in / pull back / orbit / pan / handheld / static…），同时指明景别
[Scene 场景]:  在哪里 + 光影。光源方向 / 行为（薄雾 / 雨 / 尘埃）/ 色调
[Style 风格]:  品质锚定 + 风格关键词（"4K, cinematic, UE5 render, no flicker"）
\`\`\`

把这五段串成一句中文流畅文字（不是字段化），约 80-180 字。

## 时间戳分镜模板（4-15 秒视频）

短于 5 秒可以省略时间戳直接写一段；5 秒以上**强烈推荐用时间戳分镜**，把视频拆成 2-3 段递进的画面，模型对节奏的控制力大幅提升：

\`\`\`
[5 秒, 史诗写实风格] 主角持剑站在悬崖边背身远眺，剑刃微闪寒光，山风吹起战袍下摆。
0-2 秒：static 长镜，主角剪影占画面右 1/3，远景云海翻涌。
2-4 秒：缓慢 dolly in 推进至 medium shot，主角缓慢转身，表情从平静转为 determined。
4-5 秒：停顿在主角侧脸特写，右手缓慢握紧剑柄。
光影：黄昏侧逆光，金红色调，远景薄雾扩散。
约束：no flicker, no face distortion, no extra characters, no text overlay.
\`\`\`

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

例：\`\`黄昏侧逆光（光源），远景薄雾扩散（行为），金红色调主导（色调）\`\`

## 风格 / 品质锚定词

每条 prompt 尾部加品质锚定，比写 "电影感" 这种空词有效得多：

\`\`\`
4K, cinematic, UE5 render, high detail, sharp focus, stable framing, no flicker, no blur
\`\`\`

按题材换：
- 写实电影：\`\`cinematic, anamorphic lens, film grain, Roger Deakins style\`\`
- 动漫：\`\`anime style, Makoto Shinkai, vibrant colors, clean lineart\`\`
- 国风武侠：\`\`Chinese ink painting style, mist, traditional brushwork\`\`
- 赛博朋克：\`\`cyberpunk neon, blade runner aesthetic, rainy night, holographic UI\`\`

## 负面约束（防崩坏关键）

Seedance 不接受独立 negative_prompt 字段，所以负面约束**直接拼在 prompt 末尾**作为一段：

\`\`\`
约束：no face distortion, no flicker, no character drift, no extra characters,
no sudden color shift, no text/subtitle/logo/watermark, no shaky cam,
no rapid scene change.
\`\`\`

按场景额外加：
- 室内 → \`\`no outdoor sky, no daylight from outside\`\`
- 单人镜 → \`\`no crowd, no background people\`\`
- 远景 → \`\`no close-up face details, no extreme details\`\`

## 与参考图配合

Seedance reference-to-video 通过 \`\`asset_codes\`\` 接受参考图：

\`\`\`
generate_video(
  prompt="...",
  asset_codes=[character.主角.three_view_asset_code, scene.云岚宗广场.reference_asset_codes[0]],
  duration=8,
  aspect_ratio="16:9",
)
\`\`\`

**参考图能确定的事**（服装 / 长相 / 场景结构 / 全片色调）→ **不在 prompt 里复述**。
**prompt 唯一的职责**：描述动作 + 运镜 + 节奏 + 情绪变化 + 光影变化。

参考图最多 9 张；通常 1-3 张够用：1 张主角三视图 + 1 张场景主 angle。

### Seedance 官方参考图引用语法：\`\`@图片N\`\`

**在 prompt 里精确指代某张参考图，用 \`\`@图片N\`\`**（N = 1, 2, ..., 9）。
编号按 \`\`asset_codes\`\` 数组顺序，**1-indexed**：

| asset_codes 位置 | prompt 中的引用 |
| --- | --- |
| asset_codes[0] | \`\`@图片1\`\` |
| asset_codes[1] | \`\`@图片2\`\` |
| ... | ... |
| asset_codes[8] | \`\`@图片9\`\` |

**示例**（主角 + 场景两张参考图）：

\`\`\`
generate_video(
  prompt="@图片1 持剑立于 @图片2 描绘的悬崖边背身远眺，山风吹动战袍下摆。
          0-2 秒：static long shot；2-4 秒：缓慢 dolly in 推到 medium close-up，
          @图片1 缓慢转身，表情从平静转为 determined。
          光影：黄昏侧逆光，金红色调。",
  asset_codes=["img-xiaoyan-3view", "img-yunlan-cliff"],   # ← img-xiaoyan-3view 是 @图片1
  duration=5,
  aspect_ratio="16:9",
)
\`\`\`

工具会**预校验**：prompt 里 \`\`@图片N\`\` 编号必须在 \`\`1..len(asset_codes)\`\` 范围内，
越界（如只传 2 张但写 \`\`@图片3\`\`）直接 fail-fast 返 \`\`VIDEO_PROMPT_REF_OUT_OF_RANGE\`\`，
不会浪费配额打 Seedance。

工具返回的 \`\`image_refs\`\` 字段会回显当前映射：
\`\`{"@图片1": "img-xiaoyan-3view", "@图片2": "img-yunlan-cliff"}\`\`，
你可以复核 Seedance 看到的编号与你的意图是否一致。

**何时该用 \`\`@图片N\`\` vs 自然语言**：

- 多张参考图 + 需要精确指明"哪个角色做什么动作 / 哪个场景作背景" → 用 \`\`@图片N\`\`
- 单张参考图，prompt 不会混淆 → 自然语言描述即可
- 参考图职责本身就含糊（如纯风格参考）→ 不用引用，让模型自行融合

### 自动别名注入：你写中文名，工具帮你桥接到 @图片N

工具会在内部反查 memory KV——如果某个 \`\`asset_code\`\` 在 \`\`character.<name>\`\` 或
\`\`scene.<name>\`\` 的 KV 里出现过，**工具会自动在 prompt 头部前置一行别名表**：

\`\`\`
素材引用：萧炎=@图片1，云岚宗广场=@图片2

(你写的 prompt 原文)
\`\`\`

这样你 prompt 正文里直接用中文名就行（\`\`萧炎冲向云岚宗广场\`\`），Seedance 看到别名行后
就知道"萧炎"对应 @图片1。返回值的 \`\`name_refs\`\` 字段会回显反查到的映射，方便核对。

**两种写法可以混用**：

\`\`\`
generate_video(
  prompt="萧炎在云岚宗广场中央，缓推到 @图片1 侧脸特写。光影：黄昏侧逆光。",
  asset_codes=["img-xy", "img-yl"],   # img-xy 在 character.萧炎 KV 里
  ...
)
# 实际送到 Seedance 的 prompt:
# "素材引用：萧炎=@图片1，云岚宗广场=@图片2\n\n萧炎在云岚宗广场中央，缓推到 @图片1 侧脸特写。..."
\`\`\`

**反查失败的情况**：asset_code 不在 KV 里（如 workspace 调试台直接 \`\`generate_image\`\` 出
的临时图）→ \`\`name_refs\`\` 为空，工具不会前置别名行；你只能用 \`\`@图片N\`\` 显式索引。

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

每次调 \`\`generate_video\`\` 之前：
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

\`\`\`
史诗写实风格，主角持剑站在悬崖边背身远眺，山风吹动战袍下摆。
0-2 秒：static 长镜，主角剪影占画面右 1/3，远景云海翻涌。
2-4 秒：缓慢 dolly in 推进至 medium shot，主角缓慢转身，
表情从平静转为 determined。
4-5 秒：停顿在主角侧脸特写，右手缓慢握紧剑柄。
光影：黄昏侧逆光，金红色调，远景薄雾扩散。
约束：4K, cinematic, UE5, no flicker, no face distortion, no text overlay.
\`\`\`

### 2. 对话双人（8 秒，中景对话）

\`\`\`
赛博朋克写实风，A 和 B 在霓虹雨夜街角对峙。
0-3 秒：static medium shot，OTS 视角从 A 肩头看 B，B 表情凝重缓慢说话。
3-6 秒：缓慢 pan 转到 B 的正反打，B 抬头反问，眼神锐利。
6-8 秒：crane up 升镜略仰，揭示 B 身后远处霓虹招牌。
光影：紫红色霓虹主光 + 蓝色雨夜冷调，水面反光，雨水缓慢落下。
约束：cinematic, anamorphic lens, no character drift, no extra people, no text.
\`\`\`

### 3. 高潮战斗（10 秒，单人爆发）

\`\`\`
史诗奇幻风，主角站在战场中央，双手凝聚异火。
0-3 秒：medium shot static，主角双手缓慢抬起，掌心红蓝双色火焰旋转融合。
3-6 秒：dolly in 缓推到 medium close-up，火焰加速旋转，主角眼神聚焦。
6-9 秒：火焰爆发瞬间——orbit 镜头快速环绕主角 1/4 圈，揭示火焰膨胀。
9-10 秒：拉远到 wide shot，火焰冲天，主角剪影。
光影：火焰自发光主导，冷蓝环境光对比，地面尘埃飞舞。
约束：UE5 render, no flicker, no rapid scene change, no text overlay,
no shaky cam, 4K detail.
\`\`\`

### 4. 静谧抒情（6 秒，空镜过场）

\`\`\`
日系治愈风，清晨田野，麦穗在微风中摇曳。
0-2 秒：static low angle close-up，麦穗占画面前景，远景模糊。
2-4 秒：缓慢 truck right 横移跟随风的方向。
4-6 秒：rack focus 焦点从前景麦穗虚化到远景日出。
光影：晨光侧逆光，金色高光，薄雾弥散，全片低饱和怀旧色。
约束：anime style, Makoto Shinkai aesthetic, soft focus, no flicker, no text.
\`\`\`

### 5. 揭示式开场（12 秒，建立世界）

\`\`\`
中国传统水墨风，悬浮的仙山远景，云雾环绕。
0-4 秒：static wide shot，仙山占画面中央，云雾从下方缓慢上升。
4-8 秒：缓慢 dolly in 推进，揭示山顶古亭轮廓。
8-12 秒：tilt down 缓慢下摇，最终落在亭中持剑的主角剪影。
光影：晨曦侧光，墨色与朱红对比，远景留白，水墨笔触可见。
约束：Chinese ink painting style, traditional brushwork, no flicker,
no character drift, stable framing, 4K.
\`\`\`
`;


const LIGHTING_COOKBOOK = `---
name: lighting-cookbook
description: Use when designing lighting language for a character / scene reference image, or when describing time-of-day / weather / dramatic mood in a video prompt. Provides classic light positions (Rembrandt / loop / split / butterfly / rim / three-point), time-of-day color temperature recipes (3200K / 5600K / 8000K), and genre-specific lighting formulas (noir 1:8 / Pixar 1:2 / anime cel-shading) with prompt fragments ready to splice.
target_agents: [character_ref_agent, scene_ref_agent, video_prompt_agent, visual_style_agent]
tags: [lighting, cinematography, prompt-engineering, visual-style]
author: filmgenx
---

# 灯光配方手册（Lighting Cookbook）

下游 character_ref / scene_ref / video_prompt / visual_style 写灯光描述时经常陷入"光照柔和、气氛肃穆"这种空话。本 skill 给一套业内通用的灯光配方——精确到色温 (K)、光比 (key:fill ratio)、方向 (degrees)、prompt 片段——让 agent 写出来的 prompt 模型能直接执行。

源头思想来自 ASC（American Society of Cinematographers）的工作流：每个镜头先定**光源动机**（motivation），再定 key / fill / rim 三层，最后定**色温 + 强度 + 方向**。

## 核心信条 / 第一原理

1. **光必须有动机（motivation）**：画面里观众应能识别光源——窗 / 灯 / 火 / 雷 / 屏幕 / 月。无动机的光让画面假
2. **三色温度规则**：3200K (warm tungsten) / 5600K (neutral daylight) / 8000K+ (cool blue twilight)——一个镜头里**最多混两种色温**，混三种以上观众解读为"廉价滤镜"
3. **1:N ratio 决定戏剧性**：1:1 平光、1:2 自然柔和、1:4 戏剧温和、1:8 强烈戏剧、1:16 黑色电影。Roger Deakins《1917》大多 1:2~1:4，《银翼杀手 2049》大多 1:8~1:16
4. **三层光是底线**：key (主光，定形) + fill (补光，控反差) + rim/back (轮廓光，分离主体与背景)。缺 rim 主体糊进背景，缺 fill 反差太大像监控
5. **lighting consistency 锁角色一致性**：同一角色的三视图 + 所有变体都用**同方向 key light**，i2i 变体才不会"看起来像不同时段拍的"

## 术语词汇表

| 术语 | 含义 | 通用误用纠正 |
|---|---|---|
| **Key light** | 主光，定义主体形状 | ≠ "最亮的光"——key 不一定最亮 |
| **Fill light** | 补光，填阴影、控反差 | fill 不一定是光源——反光板 / 墙反射都算 |
| **Rim / Back light** | 轮廓光，从主体后方打 | rim 是侧后 45°；back 是正后 180°；hair light 是头顶后方 |
| **Practical** | 画面里看得到的人造光 | 不是"装饰"——是 motivation 的载体 |
| **Motivated light** | 能合理化的光源 | 玄幻题材高频用——剧情说有火就有暖光 |
| **Lighting ratio** | key 强度 : fill 强度（1:4 = key 是 fill 的 4 倍） | 不是"亮暗对比度"——是两个光源的物理强度比 |
| **Chiaroscuro** | 高对比明暗，Caravaggio / Rembrandt 风格 | 不是"黑底亮主体"——是一束光在黑暗里雕出体积 |
| **High key** | 整体亮、低对比、柔光 | Pixar / 治愈系 / 喜剧 |
| **Low key** | 整体暗、高对比、硬光 | Noir / 悬疑 / 战斗 |
| **Hard light** | 锐利阴影、清晰边缘 | 点光源 + 小面积；正午阳光、裸灯 |
| **Soft light** | 柔和阴影、模糊边缘 | 大面积漫射；阴天、柔光箱、墙反射 |
| **Color temperature** | 光的颜色，单位 Kelvin | 3200K 暖橙、5600K 中性白、8000K+ 冷蓝 |
| **Golden hour** | 日出后 / 日落前 30-60 分钟 | 不是"傍晚"——具体时段、光质独特 |
| **Blue hour** | 日落后 / 日出前 20-30 分钟 | 太阳下，天有冷蓝余光 |

## 经典光位配方（Classic Lighting Setups）

按"key light 与主体的相对角度"分。每种光位有自己的戏剧表达。

### 1. Rembrandt Lighting（伦勃朗光）

- **角度**：key 45° 侧前方，主体面部背光一侧颧骨下出现**倒三角形高光**
- **戏剧表达**：内省、严肃、人物有重量感——经典肖像光
- **prompt 片段**：\`\`"Rembrandt lighting, key light 45° camera-left from front, small inverted triangle highlight on shadow-side cheek under the eye, low fill, soft shadow"\`\`
- **用在哪**：严肃角色三视图 / 反派立绘 / 关键情绪 close-up

### 2. Loop Lighting（环形光）

- **角度**：key 30-45° 侧前方，鼻翼阴影**不接**到嘴角（环形悬空）
- **戏剧表达**：自然、亲切、最常用——证件照、日常对话戏
- **prompt 片段**：\`\`"loop lighting, key light 30° camera-left and slightly above, nose shadow loops to cheek but does not touch lip"\`\`
- **用在哪**：常规对话戏 / 主角日常 establishing

### 3. Split Lighting（侧光 / 半阴半阳）

- **角度**：key 90° 正侧方，半边脸亮、半边脸暗，**明暗中线竖直穿过鼻梁**
- **戏剧表达**：分裂、矛盾、双面性——心理戏 / 反派揭面 / 高潮决断
- **prompt 片段**：\`\`"split lighting, hard key light 90° side, half face brightly lit, other half in deep shadow, clear vertical division along nose bridge"\`\`
- **用在哪**：角色内心矛盾 / 反派揭露真面目

### 4. Butterfly / Paramount Lighting（蝶光）

- **角度**：key 正前上方 45°，鼻下出现**蝴蝶形阴影**
- **戏剧表达**：明媚、华丽——好莱坞黄金时代女星标准光
- **prompt 片段**：\`\`"butterfly lighting, key light directly above and slightly in front, distinctive small butterfly-shaped shadow under nose, glamour portrait look"\`\`
- **用在哪**：女主美化镜头 / 杂志风 close-up

### 5. Rim / Back Light Only（逆光剪影）

- **角度**：key 在主体后方，正面几乎无光
- **戏剧表达**：神秘、登场、危险——反派出场 / 决斗起手
- **prompt 片段**：\`\`"strong rim light from behind, character mostly in silhouette, glowing edge around hair and shoulders, atmospheric haze catches the backlight"\`\`
- **用在哪**：反派出场 / 决斗高潮 / 剪影叙事

### 6. Three-Point Lighting（三点光，工作室标准）

- **配置**：key 45° 侧前 + fill 45° 对侧 (1:2~1:4 ratio) + rim/back 后上 45°
- **戏剧表达**：标准、安全、商业感——访谈 / 产品拍摄 / 教学
- **prompt 片段**：\`\`"three-point lighting setup, key light 45° front-left, fill light 45° front-right at half intensity (1:2 ratio), back rim light 45° behind separating subject from background"\`\`
- **用在哪**：常规对话戏 / 不知道用啥光位时的 safe default

## Time-of-Day 配方表

| 时段 | 色温 (K) | 方向 | 强度 | 阴影 | 大气 | prompt 片段 |
|---|---|---|---|---|---|---|
| **Golden Hour** | 3200K | 低 15° 侧逆 | 中 | 长而柔、暖橙 | 颗粒、薄雾 | \`\`"golden hour, warm 3200K key light from low 15° back-side, long soft amber shadows, atmospheric haze"\`\` |
| **Blue Hour** | 8000K | 漫散无方向 | 弱 | 几乎无 | 冷蓝余光 | \`\`"blue hour twilight, cool 8000K ambient sky light, diffuse soft shadow, magic hour mood"\`\` |
| **Noon Harsh** | 5600K | 垂直 90° | 强 | 短、硬、深 | 透明 | \`\`"high noon, harsh 5600K overhead sunlight, short hard black shadows, high contrast"\`\` |
| **Overcast** | 5500K | 漫散无方向 | 弱 | 几乎无 | 灰白 | \`\`"overcast soft daylight, 5500K diffused sky light, no clear shadows, low contrast"\`\` |
| **Dusk** | 4500K → 6500K | 漫散 + 残余地平线 | 中 → 弱 | 模糊、长 | 温度过渡 | \`\`"dusk transitioning from warm 4500K sun glow to cool 6500K sky"\`\` |
| **Dawn** | 4500K → 5500K | 漫散 + 地平线起 | 弱 → 中 | 模糊、长 | 晨雾 | \`\`"dawn, soft 4500K sunrise glow rising from horizon, ground-level mist"\`\` |
| **Night - Moonlit** | 8000K + practicals | 顶部漫散 + 局部暖 | 弱 + 强 practical | 深、模糊 | 蓝灰 | \`\`"moonlit night, cool 8000K moonlight, warm 2700K practical lanterns scattered, strong cool-warm contrast"\`\` |
| **Night - Urban** | mixed practicals | 多源混合 | 局部强 | 多重 | neon glow | \`\`"urban night, mixed practical lighting from neon signs and street lamps, multi-colored ambient glow"\`\` |
| **Stormy** | 5500K + 雷电 | 顶部漫散 + 瞬时硬光 | 弱 + 极强瞬时 | 模糊 + 锐 | 雨雾 | \`\`"stormy weather, 5500K diffused stormy daylight, occasional sharp lightning flash, wet atmospheric haze"\`\` |

## 流派配方表（Genre-Specific Lighting Formulas）

### Anime（动画）

- **典型**：cel-shading 2-tone（光面 / 暗面分离，无渐变）
- **key:fill**：1:2 ~ 1:4
- **rim light**：**必有**——anime 角色离不开 rim 分离背景
- **practicals**：高频用（灯笼 / 火焰 / 魔法光球）
- **prompt 片段**：\`\`"anime cel-shading lighting, clear 2-tone separation of lit and shadow areas, soft 1:2 key:fill ratio, strong rim light from behind, vibrant colors"\`\`
- **代表**：Studio Trigger / Kyoto Animation / Madhouse

### Photorealistic / Film（实拍电影）

- **典型**：三点光 + practicals
- **key:fill**：1:4 ~ 1:8（戏剧）/ 1:2（柔和）
- **rim light**：subtle，靠 fill + back combined
- **practicals**：必有 motivated（窗 / 灯 / 火）
- **prompt 片段**：\`\`"cinematic film lighting, motivated key from window 45° camera-left, 1:4 key:fill ratio, subtle rim from window edge, warm practical lamps in background, shot on Arri Alexa"\`\`
- **代表**：Roger Deakins / Hoyte van Hoytema / Bradford Young

### Noir（黑色电影）

- **典型**：low key + 硬光 + chiaroscuro
- **key:fill**：1:8 ~ 1:16（极高对比）
- **rim light**：常用百叶窗 venetian blind 投影
- **色温**：低饱和单色调（cool blue 或 warm sepia）
- **prompt 片段**：\`\`"film noir lighting, low key chiaroscuro, hard 1:8 key:fill ratio, single source key from upper-side casting dramatic shadows, venetian blind slat shadow patterns, desaturated cool palette"\`\`
- **代表**：Citizen Kane / Blade Runner / The Lighthouse

### Pixar / Disney 3D

- **典型**：high key + 多源软光 + practicals
- **key:fill**：1:2（柔和）
- **rim light**：subtle，多为环境光
- **色温**：饱和、温暖、对比中等
- **prompt 片段**：\`\`"Pixar-style 3D lighting, high key with 1:2 soft fill ratio, multiple soft sources, warm saturated colors, subtle rim light, no harsh shadows, optimistic mood"\`\`
- **代表**：Toy Story / Coco / Up

### Ghibli / Watercolor

- **典型**：natural light + atmospheric perspective
- **key:fill**：1:2 ~ 1:3（柔和）
- **rim light**：靠天空漫射，无明显 rim
- **色温**：自然、大地色系
- **prompt 片段**：\`\`"Ghibli-style natural lighting, soft 1:2 fill from open sky, atmospheric perspective with hazy distant elements, warm earth tones, painterly soft shadows"\`\`
- **代表**：Studio Ghibli（Spirited Away / Howl's Moving Castle）

### Cyberpunk

- **典型**：multi-color practicals（cyan + magenta + amber）+ 湿地面反光
- **key:fill**：1:8（高对比、低饱和环境 + 高饱和 practicals）
- **rim light**：常用 neon 边缘
- **色温**：极端混合（冷主调 + 暖局部）
- **prompt 片段**：\`\`"cyberpunk neon lighting, mixed cyan and magenta practicals, 1:8 contrast ratio, wet reflective surfaces, atmospheric haze with light beams"\`\`
- **代表**：Blade Runner / Ghost in the Shell

## Lighting Consistency 铁律（角色一致性的关键）

同一角色的三视图 + 所有变体 i2i，**key light 方向必须一致**——否则下游 i2i 出来五官的阴影漂移，看起来像不同时段拍的不同人。

- 三视图（front + side + back）默认 \`\`front-left 45° soft light\`\`
- 表情变体（angry / smile / 等）i2i 时**不改 key 方向**
- 服装变体 / 战斗姿态 i2i 时**也保持同 key 方向**

只有在做"特定场景下的角色镜头"时（如角色 close-up 在战火中），才按场景的 motivated light 调整方向——但那是 video_prompt 阶段的事，不是 character_ref 阶段。

## 反例 / 陷阱

### ❌ 反例 1：无 motivation 的光

\`\`\`
"光照柔和，气氛肃穆"
\`\`\`

**后果**：模型不知道光从哪来，每张图光照随机摆，三视图各张光不一致。

**正例**：

\`\`\`
"motivated soft key light from upper-right window at 45°, 5500K natural daylight,
1:3 key:fill ratio, soft shadow fall-off"
\`\`\`

### ❌ 反例 2：色温混乱

\`\`\`
"warm golden sunlight + cool blue moonlight + magenta neon"
\`\`\`

**后果**：三种色温在一镜里，模型解读为"廉价滤镜"，画面发腻。

**正例**：

\`\`\`
"warm 3200K golden sunlight as key, cool 6500K skylight as fill, two-temperature contrast"
\`\`\`

### ❌ 反例 3：缺 rim light

\`\`\`
"key light from front, fill from side"
\`\`\`

**后果**：anime 风格里没 rim = 角色边缘融化进背景，立体感丢失。

**正例**：

\`\`\`
"key 45° front-left, fill 45° front-right at half intensity (1:2),
strong rim light from upper-back at 45°, clear separation between subject and background"
\`\`\`

### ❌ 反例 4：lighting consistency 违反

三视图 front 用 \`\`key from left\`\`，side view 用 \`\`key from right\`\` → 模型不知道哪边受光，i2i 表情变体阴影方向随机变。

**正例**：所有三视图 + 所有变体钉死 \`\`soft front-left 45° key\`\`，方向永不变。

## 何时加载附加资料

- 完整 12 时段配方（含 mid-morning / late-afternoon / pre-dawn / post-dusk 过渡） → 加载 @ref:time-of-day-recipes
- 8 种经典光位完整 cookbook（含 broad / short lighting 等） → 加载 @ref:classic-light-positions
- 10 种流派速查表（含具体导演 / 摄影师锚点） → 加载 @ref:genre-lighting-cheatsheet

## reference: time-of-day-recipes

<完整 12 个时段配方表，含 prompt 片段 + 适用场景 + 色温过渡曲线。比主体的简表多包括
mid-morning / late-afternoon / pre-dawn / post-dusk 等过渡时段。由 admin 按需扩展。>

## reference: classic-light-positions

<完整 8 种经典光位（Rembrandt / loop / split / butterfly / broad / short / rim / silhouette），
每种含 prompt 片段 + 代表电影 + 示意图描述。由 admin 按需扩展。>

## reference: genre-lighting-cheatsheet

<10 种流派的灯光速查表，含具体导演 / 摄影师 / 工作室引用作为风格锚点。由 admin 按需扩展。>
`;

export const SKILL_SAMPLES: SkillSample[] = [
  {
    label: 'narrative-structure（剧情结构 / outline_agent）',
    targetAgent: 'outline_agent',
    markdown: NARRATIVE_STRUCTURE,
  },
  {
    label: 'dialogue-craft（剧本 / 对白工艺 / script_agent）',
    targetAgent: 'script_agent',
    markdown: DIALOGUE_CRAFT,
  },
  {
    label: 'cinematic-composition（镜头语言 / storyboard_agent）',
    targetAgent: 'storyboard_agent',
    markdown: CINEMATIC_COMPOSITION,
  },
  {
    label: 'visual-style-anchors（视觉风格 / visual_style_agent）',
    targetAgent: 'visual_style_agent',
    markdown: VISUAL_STYLE_ANCHORS,
  },
  {
    label: 'character-design（角色设计 / character_ref_agent）',
    targetAgent: 'character_ref_agent',
    markdown: CHARACTER_DESIGN,
  },
  {
    label: 'scene-design（场景 / production design / scene_ref_agent）',
    targetAgent: 'scene_ref_agent',
    markdown: SCENE_DESIGN,
  },
  {
    label: 'video-prompt-engineering（视频 prompt 工程 / video_prompt_agent）',
    targetAgent: 'video_prompt_agent',
    markdown: VIDEO_PROMPT_ENGINEERING,
  },
  {
    label: 'seedance-prompt-guide（Seedance 官方指南 + 相机四维 / video_prompt_agent）',
    targetAgent: 'video_prompt_agent',
    markdown: SEEDANCE_PROMPT_GUIDE,
  },
  {
    label: 'lighting-cookbook（灯光配方手册 / 多 agent 共用）',
    targetAgent: 'character_ref / scene_ref / video_prompt / visual_style',
    markdown: LIGHTING_COOKBOOK,
  },
];
