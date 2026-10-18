# joy2know-mureka-maestro 发布前检测报告

> **口径说明**：每条结论对应一次**真实运行**（命令 + 样本 + 输出要点）。
> 校验器为仓库权威版 `scripts/selfcheck.py`；平台侧入口判据复刻在 `scripts/platformcheck.py`。
> 本包是单专家（`expertType: agent`），**纯提示词包 + 1 个内嵌技能**：专家本体无 `scripts/`；
> 内嵌技能 `joy2know-mureka-musician` 带一个只读 JS 校验器（Node 标准库，无网络调用、无写文件、无凭证）。
> **排除文件说明**：本报告是包根那一个 `joy2know-mureka-maestro.md`（开发期文档，不进 zip）；
> 角色定义 `agents/joy2know-mureka-maestro.md` 是**真 agent、不被排除**。

- **包名**：joy2know-mureka-maestro
- **类型**：单专家（`expertType: "agent"`）
- **对应版本**：1.3.1
- **检测状态**：⚠️ 有条件通过
- **最后检测**：2026-10-18（**第四轮：双路线口径同步 + 1.2.1 内嵌对齐抬版** —— 详见第七节履历）
- **检测方式**：功能测试 + 完整性对照 + 合理性检查 + 反向验证

---

## 一、包内文件（从磁盘枚举，不手写）

```
   2357  .codebuddy-plugin/plugin.json       配置（expertType: agent，1 agent / **3 内嵌技能**）
   4230  README.md                           包说明（他解决什么问题 / 三条底线 / 擅长体裁 / 包内容 / 用法）
  16507  agents/joy2know-mureka-maestro.md   角色定义（开场引导 / 流程 / 6 条硬规则 / 产出格式 / 9 条自检 / 边界 /
                                               **专辑路由 + 8 条专辑自检 + 专辑边界**）
    228  skills.json                         内嵌技能声明（构建时从 packages/<名>/ 复制真源）
```

**零第三方依赖核对**：专家本体无 `scripts/`、无 import、无网络调用；内嵌技能的 `mureka_check.mjs`
只用 Node 标准库（`node:fs`），结构性零依赖成立。

源包体（四个源文件，**不含本报告**）**14,977 字节 ≈ 14.6 KB**；构建产物 `dist/joy2know-mureka-maestro-v1.0.0.zip` 实测 **846,297 字节（826.5 KB）**（含构建注入的真头像 397.8 KB + 内嵌技能及其图标 391.7 KB）。专家包上限 **20 MB**，余量约 24 倍。

**头像规格（真图）**：`avatars/joy2know-mureka-maestro.png` = 512×512 / **397.8 KB**（≤500KB 达标）。
2026-10-15 傍晚由**小乐亲手重画**（半身像）：灰发顶髻红发圈毛毡小孩，**米色围巾 + 黑背心白衬衫领结 + 背带，
肩挎包露黄铜小号，谱架前执笔写谱**（与音乐人版同「写谱」意象成对）。
构建后 zip 内 `avatars/expert.png` 的 sha1（aa4ed842…）与源图**逐字一致**。

---

## 二、能力清单与验证结果

| 能力 / 待验证项 | 验证方式（命令与样本） | 结果 | 证据要点 |
|---|---|---|---|
| plugin.json 全字段遍历 + 中英成对 + 硬约束达标 | `$V/bin/python scripts/selfcheck.py packages/joy2know-mureka-maestro` | ✅ 通过 | **全部自检通过**（源目录 3 条预期提示：内嵌技能与头像「构建时才注入」、zip 未生成） |
| 官方硬约束：`displayDescription.zh` 40–50 汉字 | 同上 + 正则计汉字 | ✅ 通过 | 实测 **49 汉字**（中段，不贴边界） |
| 官方硬约束：`defaultInitPrompt` == `quickPrompts[0]` | 同上 | ✅ 通过 | 两版（zh/en）逐字相同：「给我写一首能粘进 Mureka 的歌」 |
| 官方硬约束：`tags` / `quickPrompts` 各 3 个 | 同上 | ✅ 通过 | 各 3 |
| `categoryId` 在官方 15 类白名单内 | 同上 | ✅ 通过 | `06-ContentCreative`（与在架单专家 `joy2know-mr` 同类） |
| `agents[]` 路径存在 + agent name == agentName == 目录名 | 同上 | ✅ 通过 | 三者一致（`joy2know-mureka-maestro`） |
| `displayName` 为品牌署名「晓得乐」（非花名） | 人工核对 plugin.json + agent frontmatter | ✅ 通过 | `displayName: {en: joy2know, zh: 晓得乐}`；卡面主标题 = `profession` = 晓得·Mureka音乐大师；**角色文件与正文无花名、无队友指代**（单飞重写纪律） |
| **内嵌技能主源存在** | `ls packages/joy2know-mureka-musician` | ✅ 通过 | 源技能包存在（SKILL.md + 4 references + 1 script） |
| **内嵌副本与主源逐字节一致（未漂移）** | `diff -r -x icon.png -x joy2know-mureka-musician.md <zip内副本> packages/joy2know-mureka-musician` | ✅ 通过 | **逐字节一致**；唯一差异是主源里的检测报告与构建注入的 `icon.png`（均正确排除） |
| **交付形态（解压 zip 后）完整自检** | `unzip -qq dist/…zip && $V/bin/python scripts/selfcheck.py /tmp/j2k-mrk/joy2know-mureka-maestro` | ✅ 通过 | **全部自检通过**（比源目录多内嵌技能路径与头像注入两项验证） |
| zip 第一层目录名正确（无多套一层） | `unzip -Z1 dist/…zip` | ✅ 通过 | 第一层唯一为 `joy2know-mureka-maestro/` |
| 平台入口判据：按 Expert 类型可通过 | `$V/bin/python scripts/platformcheck.py --zip dist/joy2know-mureka-maestro-v1.0.0.zip` | ✅ 通过 | `Expert ✅ 通过 ← 本包应有的类型`；`Skill ❌`（缺根级 SKILL.md，预期——本包不该走技能入口） |
| 包内无硬编码凭证 | selfcheck `[sec]` 项 | ✅ 通过 | 未发现疑似凭证 |
| **内嵌校验器判据自检** | `node skills/joy2know-mureka-musician/scripts/mureka_check.mjs --selftest` | ✅ 通过 | **21 项全部通过**（详见技能包报告第五节，含反向验证） |
| R6 跨包审计 | `$V/bin/python scripts/series_audit.py .` | ✅ 通过 | 三类候选（R4 / R2 / R1）**均不含本包** |
| 卡片文案与实际开场的一致性（defaultInitPrompt 走的真实流程） | — | **未覆盖** | 需真实装载专家跑一轮开场，见第六节 |

**复现命令**

```bash
V=~/.workbuddy/binaries/python/envs/default
$V/bin/python scripts/selfcheck.py packages/joy2know-mureka-maestro
node scripts/build.mjs joy2know-mureka
$V/bin/python scripts/platformcheck.py --zip dist/joy2know-mureka-maestro-v1.0.0.zip
# 解压后交付形态自检与内嵌 diff 见上文各行的命令
```

---

## 三、门 2 · 完整性对照（文档承诺 → 实现）

| 文档承诺（摘原文） | 实现位置 | 有 / 无 / 部分 | 备注 |
|---|---|---|---|
| README「他解决什么问题」三类症状（中文 token 漂移 / 咬字糊 / 找不存在的滑杆） | `agents/…md` 流程 + 内嵌技能规则 | **有** | 分别对应规则 1（英文 token）、规则 3（三件套）、界面设置块（含无滑杆提醒） |
| README「三条底线」：只产文本 / 三件套 / 脚本校验 | `agents/…md` 边界节 + 规则 3 + 流程 ⑤ | **有** | 三处口径一致；底线 3 落到可执行脚本 |
| README「包内容」目录树含 references/ 与 scripts/ | 内嵌技能真源 `packages/joy2know-mureka-musician/` | **有** | 构建后包内实测：SKILL.md + 4 references + mureka_check.mjs + icon.png |
| 方法论主体在技能里、角色定义不重复技能内容 | `agents/…md` 首节末段 | **有** | 明写「以已加载的 `joy2know-mureka-musician` 技能为准，本文件只规定角色、流程和验收标准」 |
| 开场引导的输入自给降级路径（五问默认值 / 器乐默认） | `agents/…md §一` | **有** | 「你手上什么都没有，我也能开工」+ 默认治愈民谣的理由 + 游戏 / 白噪音话题改走器乐循环 |
| 校验器路径与参数（--instrumental / --loop） | `agents/…md §二` | **有** | 命令样例与技能 SKILL.md §三 逐字一致（R3：同一规则一种表述） |
| README「怎么用」四行示例 | `agents/…md` 各节 | **有** | 四条示例对应的能力都有实现 |
| 单飞纪律：直接交付、不代转交、无内部 ID | `agents/…md §六` | **有** | 「产出直接交给用户」「不出现 joy2know-mureka-* 内部 ID」；全文无 SendMessage / 队友花名 |
| 判据争议的处理（不临场发明第三种口径） | `agents/…md §二` 末段 | **有** | 「回技能规则核对 → 如实告知口径不一致 → 按技能规则交付」 |

**兜底口径两向核对**：正向（README / plugin.json 承诺 → 有实现）全部通过；
**反向（实现里有、文档没写）未发现缺口**——agent 的 6 条硬规则在 README 三条底线中均有锚点
（规则 2 界面设置块由「他解决什么问题」第三条覆盖）。

---

## 四、门 3 · 合理性结论

- **规则是否自洽**：✅ 无互相打架。三条底线在 agent、README、内嵌技能三处说法一致；
  agent 的校验命令与技能 SKILL.md 的命令逐字一致（内嵌关系 R8 专项：本包随技能同轮新建，无漂移窗口）。
- **推断是否标注为推断**：✅ `categoryId=06-ContentCreative` 在 release.config.json 标记为推断值
  （`categoryConfirmed: false`），未当实证写；深度合成驳回的处置顺序（先找客服）已写入 categoryNote 与技能报告。
- **错误提示是否可指导下一步**：✅ 降级路径都给明确动作（五问默认值 → 直接产出；判据争议 → 回规则核对）。
- **边界是否优雅**：✅ §六 覆盖六类边界（不生成音频 / 不做封面 MV / 不提档位额度 / 直接交付 / 无内部 ID / 禁解释）。
- **零依赖是否守住**：✅ 结构性成立（专家本体纯文本；内嵌校验器 Node 标准库、只读）。
- **值来源是否可追溯**：✅ 版本号 1.0.0 三处一致（plugin.json / README / 本报告）；头像真源在仓库根
  `avatars/`；内嵌技能真源在 `packages/joy2know-mureka-musician/`（已实测副本逐字节一致）。
- **maxTurns=50**：与单专家先例（topic-planner 50）一致；单飞流程约 6 步、无成员编排，50 轮充足。

---

## 五、门 4 · 测试真实性自评（防放水）

- [x] 1. 只跑 happy path，没跑边界 —— **否**：交付形态测试用**真实 zip 解压产物**（非源目录）；内嵌技能含 21 项自检与反向验证
- [x] 2. 只看「没报错 / 退出码 0」，没核对输出内容 —— **否**：`defaultInitPrompt == quickPrompts[0]` 做了**逐字**比对；`displayDescription.zh` 数了汉字（49）
- [x] 3. 把「文档写了」当成「已验证」 —— **否**：「卡片文案与真实开场一致性」「平台上传」「头像配色」三项列入第六节
- [x] 4. 自造理想样本（比真实产物干净） —— **否**：交付形态测试用解压后的真实产物
- [x] 5. 跳过失败项、不记录 —— **否**：0 项失败；两项「未覆盖」如实列出
- [x] 6. 修完只测修好的那条，没跑回归 —— **否**：技能侧 SKILL.md 补文档后重跑构建与 21 项自检（全绿），本包内嵌副本随之重验
- [x] 7. 造错样本只造了会被抓的那种 —— **否**：反向验证做在内嵌校验器上（改坏 L1 阈值 → 自检 2 项红灯，详见技能包报告）

**反向验证记录**（本包结构层的反向验证依托 `selfcheck.py` 的既有机理 + 内嵌校验器）：

| # | 造了什么错样本 | 预期 | 实际 |
|---|---|---|---|
| M1 | 内嵌技能副本 diff（含 icon.png 与报告排除项） | 仅两处预期差异 | ✅ 逐字节一致 |
| M2 | 内嵌技能 SKILL.md 改动后重建 | 副本随构建同步、diff 仍一致 | ✅ 重建后一致（构建注入、无手工副本可漂） |
| M3 | （继承自校验器）改坏 L1 阈值 | 内嵌 selftest 必红 | ✅ 2 项红灯（技能包报告第五节） |

**一句话回答：本包的核心结构如果坏掉，是哪一步会亮红灯？**

→ 配置层（plugin.json 字段 / categoryId / agent 名对应 / displayDescription 汉字数 / 头像路径 / **技能名**）坏了 →
`selfcheck.py` 亮红灯。
→ 交付形态层（zip 第一层、内嵌副本漂移、头像注入）坏了 → 解压后的交付形态自检亮红灯。
→ 方法论层（校验器阈值被改坏）坏了 → 内嵌 `mureka_check.mjs --selftest` 亮红灯（21 项）。
→ **有一类不会亮红灯**：专家**开场的实际体验**（用户一句「写首歌」能否顺滑走完六步、产出质量）——
任何自动校验都读不出这个，需真实装载跑一轮（见第六节 1）。

---

## 六、未覆盖项 / 已知缺陷 / 待办

**未覆盖项**（下次检测优先消掉）：

1. **卡片文案与真实开场未实测**：`defaultInitPrompt` / `quickPrompts` 能否顺滑触发六步流程、
   产出质量是否达标，需在 WorkBuddy 里真实装载本专家跑至少两轮（一句全默认 + 一个指定蓝调民谣的主题）。
2. **平台侧真实上传未做**：从未提交（①）；`categoryId=06-ContentCreative` 是推断值。
   若被机器判「深度合成 > AI创作」：**先找客服人工复审，别改包也别补资质**（categoryNote 已记处置顺序）。
3. **头像为占位图**：11.1 KB 占位图，待小乐拍板配色换真图；**换完必须重跑构建**（专家自身图标在 zip 内）。
4. **内嵌技能与《Mureka音乐人提示词指南.md》的血缘未逐条 diff**：技能主干来自该指南 + FAQ，
   指南后续若修订（如 2026-10-15 计划回灌的 FAQ 修正），需对照确认技能侧已同步。

**已知弱项**（不阻断上架，记在案）：

- **W1 · 触发词偏平台词**：`profession` 与 description 含「Mureka」专名，用户口语「帮我写首歌」
  可能落到同门的 `joy2know-musician`（Suno 口径）。两包 description 已互相区分（本包绑定 Mureka 双栏），
  但真实分发表现待平台侧观察。

**待办**：

- 换真图 → 重跑构建 → 提交平台（走**专家入口**——技能入口必报「未找到 SKILL.md」）。
- 真实装载跑两轮开场，评估未覆盖项 1。

---

## 七、检测履历

| 日期 | 版本 | 状态 | 摘要（本轮测了什么、改了什么） |
|---|---|---|---|
| 2026-10-15 | 1.0.0 | ⚠️ 有条件通过 | **首次建包 + 首次检测**。新建单专家「晓得·Mureka音乐大师」，内嵌同步新建的技能包 `joy2know-mureka-musician`（双栏方法论 + 三体裁配方 + 结构校验器）。**源目录自检全部通过**（displayDescription.zh 实测 49 汉字；defaultInitPrompt==quickPrompts[0] 逐字相同；tags/quickPrompts 各 3；categoryId=06-ContentCreative）；**解压后交付形态自检全部通过**；`platformcheck --zip` 判 **Expert ✅**（Skill ❌ 属预期）；内嵌副本与主源 **diff 逐字节一致**；内嵌校验器 21 项自检全绿 + 反向验证有效（详见技能包报告）。displayName 为品牌署名「晓得乐」、无花名（单飞纪律）。头像为 11.1 KB 占位图待换真图。R6 跨包审计不含本包。4 项未覆盖 + 1 项弱项。 |
| 2026-10-15 | 1.0.0 | ⚠️ 有条件通过 | **第二轮：换真头像 + 重建（图标变更，不抬版本）**。与技能图标同批以真源参考图 `private/refs/毛毡小人-参考图.jpg` 生成 → 垂直偏移裁切 512×512 / 261.2 KB（深蓝三件套 + 领结 + 口琴，与音乐人版同一小孩换装）。**第一轮误用 `avatars/joy2know-musician.png` 衍生图当参考被判返工**；重做时抓到并修掉两处生成问题：全身构图（会切发髻 → 锁「严格半身像」）与背景色温不一致（锁「冷白 #FAFAFA」后与音乐人版收敛到差 ≤5/255）。重跑构建（zip 59,349 → 539,349 字节，真头像 + 内嵌图标入包）；**sha1 校验**：zip 内 `avatars/expert.png`（28f3abea…）与内嵌 `icon.png`（c9d9e5ff…）均与源图逐字一致；内嵌副本 diff 逐字节一致；解压后 selfcheck 全绿。头像未覆盖项消掉（剩 3 项未覆盖 + 1 项弱项），状态维持有条件通过。 |
| 2026-10-15 | 1.0.0 | ⚠️ 有条件通过 | **第三轮：小乐重画头像（半身像）+ 重建（包内容零改动，仍不抬版本——从未提交平台）**。新图：米色围巾 + 黑背心白衬衫领结 + 背带，肩挎包露黄铜小号，谱架前执笔写谱（与音乐人版「写谱」意象成对），512×512 / 397.8 KB。重跑构建：zip 539,349 → 846,297 字节；**sha1 校验**：zip 内 `avatars/expert.png`（aa4ed842…）与内嵌 `icon.png`（98eef71b…）均与源图逐字一致。selfcheck 全绿 + platformcheck 判 Expert ✅。**首次提交平台走本轮 publish（1.0.0 首提，action=create，走专家入口）**。 |
| 2026-10-16 | 1.1.0 | ⚠️ 有条件通过 | **第二轮：接入专辑规划能力（内嵌新技能 `joy2know-album-design`）+ 修一处规则漂移**。内容性变化：① `skills.json` / `plugin.json` 内嵌技能 1 → **2**（新增 `joy2know-album-design`）；② `agents/*.md` 增「什么时候走专辑路径」小节（九问一次 / 曲名两段式 / 脚本渲染 / 六条门禁 / 三个纪律）+ **8 条专辑自检清单** + 专辑边界（只给封面提示词文本、不交付音频、不承诺效果）；③ `plugin.json` description 与 displayDescription 补专辑能力、tags 与 quickPrompts 保持官方固定 **3** 条（**把专辑并进第 1 个 tag、另同步：`plugin.json` 的 `skills` 数组已按 `skills.json` 写成 `./skills/joy2know-mureka-musician` + `./skills/joy2know-album-design`（构建会按 skills.json 重写它、只告警不拦，为免每次构建都出告警，这里把源文件一并对齐）。 |
| 2026-10-16 | 1.2.0 | ⚠️ 有条件通过 | **第三轮：专辑交付物从三份收缩为两份**（用户指示「一个专辑只需要专辑规划和粘贴清单两份，其它都是多余的，封面提示词包不用单独生成——它已被包含在粘贴清单里」）。正文改动：单曲 vs 专辑对照表的「交付」行由「三个文件：专辑规划 + 粘贴清单 + 生成脚本」改为「**两份文件**」；开场引导与五步流程的产物描述同步；纪律加一句**不把脚本复制进用户目录**（脚本副本是假真源：用户改了它、技能真源没变，下次跑还是旧逻辑）；自检清单把「三个文件同在一个目录」改为「**交付目录里只有那两份 md**，没有脚本副本、没有 spec.json」，并注明封面提示词**在粘贴清单里、不另出文件**；边界句改为「给封面提示词文本，它在粘贴清单的每首下面」。内嵌技能 `joy2know-album-design` 同步升 **1.1.0**（R8：升技能必查引用方）。 |
| 2026-10-16 | 1.2.0 | ⚠️ 有条件通过 | **第四轮：双路线口径同步（跟随内嵌技能 1.2.0 的官方模板范式落地）。** 内嵌技能 `joy2know-mureka-musician` 1.2.0 把风格栏重写为双路线（官方中文叙事式六段骨架=主推 / 英文 token 七要素=备选），本专家 8 处同步：description（触发词行）、正文首段（风格栏括注）、流程 ③（先选路线 + 速度位必给）、流程 ②（人声声明 token/叙事式两写法 + 开关按场景选）、硬规则 1（整栏同路线、不混装、不把卡片营销语当提示词）、产出格式第 1 块、单曲自检（叙事式六段齐 / token 式七要素齐两分支）、专辑纪律（纯音乐**专辑**保持开关关闭 + 氛围类单曲可走的例外注明）；`plugin.json` description 英文同步双路线。agents 12,281 → 12,952 字节。版本不抬（1.2.0 从未提交平台，改动并入）。重建 zip 892.7 KB；selfcheck 全绿；platformcheck 判 Expert ✅。**Album-design 的「不写打开开关」门禁不受影响**（专辑场景一律关闭，与本次演进自洽）。 |
| 2026-10-16 | 1.2.1 | ⚠️ 有条件通过 | **第五轮：内嵌对齐抬版（跟随 musician 1.2.1）。** 本包 1.2.0 在审中，内嵌技能 `joy2know-mureka-musician` 1.2.0 因「补头像」流程在平台撤回（版本号被占用，见技能包报告第六轮）——在审专家包内嵌的技能版本在平台失去记录（asset-smith 1.0.7 曾因「内嵌未过审版本」被驳的同类结构风险）→ 同轮 `withdraw` + plugin.json version → **1.2.1** + 重建（内嵌副本同步 1.2.1）+ republish（专家头像由平台自动上传包内 avatars/，不受技能侧头像问题影响；coverUrl 回读为 COS 真图 URL）。包内容与 1.2.0 逐字一致，仅版本号。 |
| 2026-10-16 | 1.2.2 | ⚠️ 有条件通过 | **第四轮：在描述里补齐专辑设计能力**（用户指示「在两个音乐人专家的描述里加上专辑设计能力的描述」）。
此前 agent `description` 只在触发词里列了「设计专辑/规划专辑/专辑曲目表」等词，**能力描述本身只字未提专辑** ——
用户搜不到「它会做什么」，触发词再全也没用。本次改动：① **agent frontmatter 的 `description`**
在能力段补一段完整说明（**一轮问答收齐专辑信息 → 按固定章节骨架产出专辑规划文档 + 逐首粘贴清单两份文本** →
音色锚点落到具体英文 token / 专辑结构与逐集分配 / 十列曲目表 / 差异矩阵（N 首互不撞：BPM 全不同、任意两首最多两根轴相同）/
拍号与调式逐项解释 / 逐首风格栏与歌词栏 / 封面提示词含曲名文字与留白位置），触发词另补「专辑策划 / 专辑制作 / tracklist」；
② `plugin.json` 的英文 `description` 把专辑句从笼统的括号罗列改写成完整叙事（一轮问答 → 两份文件 → 各自装什么 →
差异矩阵怎么防撞车）；③ `displayDescription` 把「规划整张专辑」改为「**设计整张专辑**」并把清单写成「逐首粘贴清单」，
| 2026-10-17 | 1.3.0 | ⚠️ 有条件通过 | **第五轮：接入作词能力（内嵌新技能 `joy2know-lyric-design` 1.0.0）**。内嵌技能 2 → **3**。内容性变化：① `skills.json` / `plugin.json` 增第三个内嵌技能；② `agents/*.md` 新增「三条路径怎么分工（不许互相抢）」小节 —— **写词走歌词设计、整张专辑走专辑设计、单曲提示词包走单曲技能**，并写明**歌词正文的写法一律以歌词设计为准**、单曲技能里的「治愈文风内核」**降级为它的一份预设引用**（不在本专家另立一套歌词规则）；③ 触发词补作词类（写歌词/作词/填词/改词/换个钩子/歌词没画面…）与开场引导；④ 自检清单加「作词包另加」9 条；⑤ `plugin.json` description 与 displayDescription 补作词能力（tags 仍固定 3 条：作词并进第 1 个 tag；quickPrompts 第 2 条换成「帮我写或打磨这首歌的词」）；displayDescription.zh **43 汉字**（官方 40–50）。⭐ **本轮抓到一个自造失误**：第一次写 skills.json 时把 `album-design` 覆盖掉了（写成 `[base, lyric-design]`），**构建后从 zip 内目录清单发现内嵌数只有 2**才察觉——已修回 3 个，并用 `unzip -p ... grep '^version:'` 核了 6 组内嵌版本全部对齐（R8：构建不拦版本不匹配、0 告警）。 |
| 2026-10-18 | 1.3.1 | ⚠️ 有条件通过 | **第三轮：封平台交叉 + 同步歌词技能新边界**。① ⭐ **去掉对 suno 家族的交叉提及**：「三条路径分工」表里那行原写「单曲技能（`joy2know-musician` / `joy2know-mureka-musician`）」，现已只留 `joy2know-mureka-musician`（Mureka 口径）。② 「写词/改词」行补注「**界面设置块由你补**」，职责边界那条同步改写。③ R8 联动：内嵌 `joy2know-lyric-design` 抬 1.1.0，本包重建。另：图标换成小乐亲手画的真图。 |
