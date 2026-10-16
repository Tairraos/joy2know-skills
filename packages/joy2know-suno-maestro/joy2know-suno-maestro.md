# joy2know-suno-maestro 发布前检测报告

> **口径说明**：每条结论对应一次**真实运行**（命令 + 样本 + 输出要点）。
> 校验器为仓库权威版 `scripts/selfcheck.py`；平台侧入口判据复刻在 `scripts/platformcheck.py`；
> 合规用词门禁为 `scripts/compliance_wording.py`。
> 本包是单专家（`expertType: agent`），**纯提示词包 + 2 个内嵌技能**：专家本体无 `scripts/`；
> 内嵌技能 `joy2know-musician`（Suno 口径，平台在架 1.6.1）自带只读 Python 校验器，
> `joy2know-album-design`（专辑层，2026-10-16 新增内嵌）自带只读 Python 校验器与渲染脚本——
> 两者均无网络调用、无凭证。
> **排除文件说明**：本报告是包根那一个 `joy2know-suno-maestro.md`（开发期文档，不进 zip）；
> 角色定义 `agents/joy2know-suno-maestro.md` 是**真 agent、不被排除**。

- **包名**：joy2know-suno-maestro
- **类型**：单专家（`expertType: "agent"`）
- **对应版本**：1.2.0
- **检测状态**：⚠️ 有条件通过
- **最后检测**：2026-10-16
- **检测方式**：功能测试 + 完整性对照 + 合理性检查 + 反向验证

---

## 一、包内文件（从磁盘枚举，不手写）

```
   2360  .codebuddy-plugin/plugin.json       配置（expertType: agent，1 agent / **2 内嵌技能**）
   4408  README.md                           包说明（他解决什么问题 / 三条底线 / 擅长体裁 / 包内容 / 用法）
  12376  agents/joy2know-suno-maestro.md     角色定义（开场引导 / 流程 / 6 条硬规则 / 产出格式 / 10 条自检 / 边界 /
                                               **专辑路由 + 8 条专辑自检 + 专辑边界**）
    221  skills.json                         内嵌技能声明（构建时从 packages/<名>/ 复制真源）
```

**零第三方依赖核对**：专家本体无 `scripts/`、无 import、无网络调用；内嵌技能的 `suno_check.py`
只用 Python 标准库（argparse / re / sys），结构性零依赖成立（该脚本随内嵌技能 1.6.1 整包带入，
其自身零依赖已在技能包 1.6.1 检测中核过）。

源包体（四个源文件，**不含本报告**）约 15.0 KB；构建产物 `dist/joy2know-suno-maestro-v1.0.1.zip`
实测 **800,720 字节（782.0 KB）**（含构建注入的专家头像 + 内嵌技能及其图标）。专家包上限 **20 MB**，余量约 50 倍。

**头像（真图）**：`avatars/joy2know-suno-maestro.png` = 512×512 / 395,597 字节（386.3 KB），**10-15 晚小乐自画真图**
（半身像：灰发小马尾 + 深蓝毛毡马甲白衬衫领结，书桌前执羽毛笔写谱，与 mureka 系列同「写谱」意象），
替换当日占位图 10.7 KB；`.placeholders.json` 台账条目已同步清空；四角采样背景冷白系（右下角桌面木色入画，
属画面元素非背景违规）。换图后已重跑构建（专家图标在 zip 内）。

**描述字段硬约束实测**：`displayDescription.zh` **49 汉字**（40–50 内，中段）；
`defaultInitPrompt` **逐字等于** `quickPrompts[0]`（zh/en 双语核过）；`tags` / `quickPrompts` **各 3**；
`categoryId` = `06-ContentCreative`（与同门 `joy2know-mureka-maestro` 同类）。

---

## 二、能力清单与验证结果

| 能力 / 待验证项 | 验证方式（命令与样本） | 结果 | 证据要点 |
|---|---|---|---|
| plugin.json 全字段遍历 + 中英成对 + 硬约束达标 | `$V/bin/python scripts/selfcheck.py packages/joy2know-suno-maestro` | ✅ 通过 | **全部自检通过**（源目录 3 条预期提示：内嵌技能与头像「构建时才注入」、zip 未生成） |
| `displayDescription.zh` 40–50 汉字 | 正则计汉字（`\u4e00-\u9fff`） | ✅ 通过 | 实测 **49** 汉字（Suno / Style 英文词不计），不贴边界 |
| `defaultInitPrompt` == `quickPrompts[0]` | JSON 解析后 `==` 比对 | ✅ 通过 | 两版（zh/en）逐字相同：「给我写一首能粘进 Suno 的歌」 |
| `tags` / `quickPrompts` 各 3 | JSON 长度 | ✅ 通过 | 各 3 |
| `categoryId` 在官方 16 类白名单内 | 同上 | ✅ 通过 | `06-ContentCreative`（与 `mureka-maestro` 同类） |
| `agents[]` 路径存在 + agent name == agentName == 目录名 | selfcheck | ✅ 通过 | 三者一致（`joy2know-suno-maestro`） |
| `displayName` 为品牌署名「晓得乐」（非花名） | 人工核对 plugin.json + agent frontmatter | ✅ 通过 | 卡面主标题 = `profession` = 晓得·Suno音乐大师；**角色文件与正文无花名、无队友指代**（单飞重写纪律） |
| **内嵌技能主源存在且为平台已过审版本** | `grep version packages/joy2know-musician/SKILL.md` + `ow.mjs state` | ✅ 通过 | 源 1.6.1 = 平台 ③ published 1.6.1（os_9de09c09ff62aea4）——**内嵌已过审版本**（asset-smith 1.0.7 因内嵌未过审版本被驳的疑点，本包结构性避开） |
| **内嵌副本与主源逐字节一致（未漂移）** | `diff -r -x icon.png -x joy2know-musician.md <zip内副本> packages/joy2know-musician` | ✅ 通过 | **逐字节一致**；唯一差异是主源里的检测报告与构建注入的 `icon.png`（均正确排除） |
| **内嵌 icon sha1 与源图一致** | `unzip -p …icon.png \| shasum` vs `shasum avatars/joy2know-musician.png` | ✅ 通过 | 双方 `61f10e18…` 逐字一致 |
| 内嵌技能版本核对（zip 内） | `unzip -p …SKILL.md \| grep version` | ✅ 通过 | `version: 1.6.1`（随源） |
| **交付形态（解压 zip 后）完整自检** | `unzip -qq dist/…zip && selfcheck /tmp/j2k-suno/joy2know-suno-maestro` | ✅ 通过 | **全部自检通过**（比源目录多内嵌技能路径与头像注入两项验证） |
| zip 第一层目录名正确（无多套一层） | 构建校验 + 解压核对 | ✅ 通过 | 第一层唯一为 `joy2know-suno-maestro/` |
| 平台入口判据：按 Expert 类型可通过 | `$V/bin/python scripts/platformcheck.py --zip dist/joy2know-suno-maestro-v1.0.0.zip` | ✅ 通过 | `Expert ✅ 通过 ← 本包应有的类型`；`Skill ❌`（缺根级 SKILL.md，预期） |
| 包内无硬编码凭证 | selfcheck `[sec]` 项 | ✅ 通过 | 未发现疑似凭证 |
| **内嵌校验器判据自检（借内嵌技能既有判据）** | `python3 /tmp/j2k-suno/.../scripts/suno_check.py --help`（可执行性） | ✅ 通过 | 用法输出完整（--dialect 七种 / --style / --instrumental / --loop / --json）；判据自检与反向验证详见 `joy2know-musician` 技能包 1.6.1 检测（内嵌的是同一份文件） |
| 合规用词门禁 | `$V/bin/python scripts/compliance_wording.py packages/joy2know-suno-maestro` | ✅ 通过 | 构建输出「合规用词：通过，4 处提示（已有否定式声明兜住）」——4 处提示与 musician / mureka-maestro 同族（description 的「生成」语义已被否定式声明覆盖） |
| R6 跨包审计 | `$V/bin/python scripts/series_audit.py .` | （待跑，见第六节） | 新包首轮未跑，下次检测补 |
| 卡片文案与实际开场的一致性（defaultInitPrompt 走的真实流程） | — | **未覆盖** | 需真实装载专家跑一轮开场，见第六节 |

**复现命令**

```bash
V=~/.workbuddy/binaries/python/envs/default
$V/bin/python scripts/selfcheck.py packages/joy2know-suno-maestro
node scripts/build.mjs joy2know-suno-maestro
$V/bin/python scripts/platformcheck.py --zip dist/joy2know-suno-maestro-v1.0.0.zip
# 解压后交付形态自检与内嵌 diff 见上文各行的命令
```

---

## 三、门 2 · 完整性对照（文档承诺 → 实现）

| 文档承诺（摘原文） | 实现位置 | 有 / 无 / 部分 | 备注 |
|---|---|---|---|
| README「他解决什么问题」四类症状（语言口音不锁 / 段落重复不标 / 人声幻觉与淡出 / Variety 改写 Style） | `agents/…md` 流程 + 内嵌技能规则 | **有** | 分别对应规则 2（人声锁）、段落骨架、器乐路径、界面动作块（Variety 归 0） |
| README「三条底线」：只产文本 / 人声锁第一字段 / 脚本校验 | `agents/…md` 边界节 + 规则 2 + 流程⑥ | **有** | 三处口径一致；底线 3 落到可执行脚本 |
| README「包内容」目录树含 references/ 与 scripts/ | 内嵌技能真源 `packages/joy2know-musician/` | **有** | 构建后包内实测：SKILL.md + 5 references + suno_check.py + icon.png，与树一致 |
| 方法论主体在技能里、角色定义不重复技能内容 | `agents/…md` 首节末段 | **有** | 明写「以已加载的 `joy2know-musician` 技能为准，本文件只规定角色、流程和验收标准」 |
| 开场引导的输入自给降级路径（五问默认值 / 器乐默认） | `agents/…md §一` | **有** | 「你手上什么都没有，我也能开工」+ 默认落点治愈中文歌 + 游戏/白噪音话题改走纯器乐循环；默认值细节指向技能（不复制，防漂移） |
| 校验器路径与参数（--instrumental / --loop / --dialect） | `agents/…md §二` | **有** | 命令样例与技能 SKILL.md §三 逐字同源（R3：同一规则一种表述） |
| README「怎么用」五行示例 | `agents/…md` 各节 | **有** | 五条示例对应的能力都有实现 |
| 单飞纪律：直接交付、不代转交、无内部 ID | `agents/…md §六` | **有** | 「产出直接交给用户」「不出现 joy2know-* 内部 ID」；全文无 SendMessage / 队友花名 |
| 判据争议的处理（不临场发明第三种口径） | `agents/…md §二` 末段 | **有** | 「回技能规则核对 → 如实告知口径不一致 → 按技能规则交付」 |

**兜底口径两向核对**：正向（README / plugin.json 承诺 → 有实现）全部通过；
**反向（实现里有、文档没写）未发现缺口**——agent 的 6 条硬规则在 README 三条底线与技能规则中均有锚点。

---

## 四、门 3 · 合理性结论

- **规则是否自洽**：✅ 无互相打架。三条底线在 agent、README、内嵌技能三处说法一致；
  agent 的校验命令与技能 SKILL.md 的命令同源（内嵌关系 R8 专项：内嵌 1.6.1 与平台在架版本一致，无漂移窗口）。
- **推断是否标注为推断**：✅ `categoryId=06-ContentCreative` 在 release.config.json 标记为推断值
  （`categoryConfirmed: false`），未当实证写；深度合成驳回的处置顺序（先找客服）已写入 categoryNote。
- **错误提示是否可指导下一步**：✅ 降级路径都给明确动作（五问默认值 → 直接产出；判据争议 → 回规则核对）。
- **边界是否优雅**：✅ §六 覆盖六类边界（不生成音频 / 不做封面 MV / 不提额度 / 直接交付 / 无内部 ID / 禁解释）。
- **零依赖是否守住**：✅ 结构性成立（专家本体纯文本；内嵌校验器 Python 标准库、只读）。
- **值来源是否可追溯**：✅ 版本号 1.0.1 两处一致（plugin.json / README）；头像真源在仓库根 `avatars/`；
  内嵌技能真源在 `packages/joy2know-musician/`（已实测副本逐字节一致）。
- **maxTurns=50**：与单专家先例（topic-planner / mureka-maestro 均 50）一致；单飞流程约 7 步、无成员编排，50 轮充足。

---

## 五、门 4 · 测试真实性自评（防放水）

- [x] 1. 只跑 happy path，没跑边界 —— **否**：交付形态测试用**真实 zip 解压产物**（非源目录）；
      内嵌技能含方言 / 器乐 / 循环多路径（其判据自检与反向验证详见 musician 1.6.1 检测，内嵌同一份文件）
- [x] 2. 只看「没报错 / 退出码 0」，没核对输出内容 —— **否**：`defaultInitPrompt == quickPrompts[0]` 做了**逐字**比对；
      `displayDescription.zh` 数了汉字（49）；内嵌版本与 icon sha1 逐字核对
- [x] 3. 把「文档写了」当成「已验证」 —— **否**：「卡片文案与真实开场一致性」「平台上传」「头像配色」列入第六节
- [x] 4. 自造理想样本（比真实产物干净） —— **否**：交付形态测试用解压后的真实产物
- [x] 5. 跳过失败项、不记录 —— **否**：0 项失败；未覆盖项如实列出
- [x] 6. 修完只测修好的那条，没跑回归 —— **不适用**：本轮为新建包，无修复项；内嵌技能随 1.6.1 带全量回归
- [x] 7. 造错样本只造了会被抓的那种 —— **部分继承**：本包结构层依托 `selfcheck.py` 既有机理；
      判据层反向验证继承自内嵌技能（musician 1.6.1 检测记录在案），本轮未重复造

**反向验证记录**（结构层依托 selfcheck 机理 + 内嵌技能既有验证）：

| # | 造了什么错样本 | 预期 | 实际 |
|---|---|---|---|
| S1 | 内嵌技能副本 diff（含 icon.png 与报告排除项） | 仅两处预期差异 | ✅ 逐字节一致 |
| S2 | 内嵌 icon sha1 与源图比对 | 逐字一致 | ✅ `61f10e18…` 一致 |
| S3 | （继承自内嵌技能）suno_check 的结构判据与方言自检 | 详见 musician 1.6.1 检测 | ✅ 同一份文件，判据未在本包改动 |

**一句话回答：本包的核心结构如果坏掉，是哪一步会亮红灯？**

→ 配置层（plugin.json 字段 / categoryId / agent 名对应 / displayDescription 汉字数 / 头像路径 / **技能名**）坏了 →
`selfcheck.py` 亮红灯。
→ 交付形态层（zip 第一层、内嵌副本漂移、头像注入）坏了 → 解压后的交付形态自检亮红灯。
→ 方法论层（校验器判据被改坏）坏了 → 内嵌 `suno_check.py` 的判据与技能包检测联动（同一份文件，改包必同步技能包报告）。
→ **有一类不会亮红灯**：专家**开场的实际体验**（用户一句「写首歌」能否顺滑走完流程、产出质量）——
任何自动校验都读不出这个，需真实装载跑一轮（见第六节 1）。

---

## 六、未覆盖项 / 已知缺陷 / 待办

**未覆盖项**（下次检测优先消掉）：

1. **卡片文案与真实开场未实测**：`defaultInitPrompt` / `quickPrompts` 能否顺滑触发流程、
   产出质量是否达标，需在 WorkBuddy 里真实装载本专家跑至少两轮（一句全默认 + 一个指定粤语主题）。
2. **平台侧真实上传未做**：从未提交（①）；`categoryId=06-ContentCreative` 是推断值。
   若被机器判「深度合成 > AI创作」：**先找客服人工复审，别改包也别补资质**（categoryNote 已记处置顺序）。
3. **头像为占位图**：10.7 KB 占位图，**用户（小乐）宣布自己画**；换真图后**必须重跑构建**（专家图标在 zip 内）
   且重新提交——按 asset-smith 1.0.7 教训，**先等本包首提审核结果再换图重发更稳**（避免内嵌版本联动疑点重演）。
4. **R6 跨包审计未跑**（新包首轮遗漏），下次检测补跑 `$V/bin/python scripts/series_audit.py .`。

**已知弱项**（不阻断上架，记在案）：

- **W1 · 触发词偏平台词**：`profession` 与 description 含「Suno」专名，用户口语「帮我写首歌」
  可能落到同门 `joy2know-mureka-musician`（Mureka 口径）或被本技能吸走。三包 description 已互相区分
  （本包绑定 Suno 三段结构 + 方言），但真实分发表现待平台侧观察。
- **W2 · 内嵌技能为「在架技能」的版本联动**：`joy2know-musician` 后续升级（1.6.2+）时，
  本包若不跟着重建，zip 内副本将过期（构建不拦版本不匹配、0 告警）——升 musician 必查内嵌方
  （`grep -rl joy2know-musician packages/*/skills.json`）。

**待办**：

- 提交平台（走**专家入口**——技能入口必报「未找到 SKILL.md」；market=06-ContentCreative + service=tools:office）。
- 真实装载跑两轮开场，评估未覆盖项 1。
- 头像真图完成后重建重提。

---

## 七、检测履历

| 日期 | 版本 | 状态 | 摘要（本轮测了什么、改了什么） |
|---|---|---|---|
| 2026-10-15 | 1.0.0 | ⚠️ 有条件通过 | **首次建包 + 首次检测**。新建单专家「晓得·Suno音乐大师」，内嵌在架技能包 `joy2know-musician` 1.6.1（Suno 三段方法论 + 方言防破音 + 结构校验器）。**源目录与解压交付形态自检全部通过**（displayDescription.zh 实测 49 汉字；defaultInitPrompt==quickPrompts[0] 逐字相同；tags/quickPrompts 各 3；categoryId=06-ContentCreative）；`platformcheck --zip` 判 **Expert ✅**（Skill ❌ 属预期）；内嵌副本与主源 **diff 逐字节一致**、内嵌 icon sha1 与源图一致、内嵌版本 1.6.1 与平台在架一致（结构性避开 asset-smith 1.0.7 内嵌未过审版本的驳回疑点）。displayName 为品牌署名「晓得乐」、无花名（单飞纪律）。头像为 10.7 KB 占位图（用户自画）。R6 审计未跑（已列未覆盖项）。4 项未覆盖 + 2 项弱项。 |
| 2026-10-15 | 1.0.1 | ✅ 通过 | **换头像重提**。内容性变化仅 2 处：① 专家头像 10.7 KB 占位图 → **386.3 KB 小乐自画真图**（半身像：灰发小马尾红发圈 + 深蓝毛毡马甲白衬衫领结，书桌前执羽毛笔写谱，与 mureka 系列同「写谱」意象；四角采样冷白系）；② 版本行 plugin.json / README 1.0.0→1.0.1（1.0.0 已提交成功版本号被占用，按判据抬版）。重建 zip **800,720 字节（782.0 KB）**；zip 内 `avatars/expert.png` sha1 与源图**逐字一致**（c0c900eb…）；内嵌 musician 1.6.1 与图标未动。源目录 selfcheck 全绿 + 解压形态 selfcheck 全绿 + `platformcheck --zip` **Expert ✅**。`.placeholders.json` 占位台账条目同步清空。 |
| 2026-10-16 | 1.1.0 | ⚠️ 有条件通过 | **第二轮：接入专辑规划能力（内嵌新技能 `joy2know-album-design`）**。内容性变化：① `skills.json` / `plugin.json` 内嵌技能 1 → **2**（新增 `joy2know-album-design`）；② `agents/*.md` 增「什么时候走专辑路径」小节（单曲 vs 专辑对照表 / 五步流程 / 两个纪律：不手改 md、平台字段以 Suno 身份为准）+ **8 条专辑自检清单** + 专辑边界（只给封面提示词文本、不交付音频、不承诺效果）；③ `plugin.json` description 与 displayDescription 补专辑能力；tags 与 quickPrompts 保持官方固定 **3** 条（**把专辑并进第 1 个 tag、用专辑入口替换第 3 个 quickPrompt，不新增第 4 条**—— 初版曾直接 append 导致构建报「tags=4 / quickPrompts=4 超官方固定 3」，已改）；displayDescription.zh 压到 **41 汉字**（官方要求 40–50；初版超限构建报错，已压）。**Suno 侧的专辑纪律特别注明**：`Suno 面板没有「纯音乐」开关`（那条只适用于 Mureka，实测打开会锁死歌词栏），器乐靠 Style 前两字段 `Instrumental, No vocals` 声明——避免把 Mureka 口径误搬过来。内嵌 `joy2know-musician` 保持 1.6.1 未动（本轮未改该技能）。构建后 expert 自检全绿、zip 内 `skills/joy2know-album-design/` 已注入。 |另同步：`plugin.json` 的 `skills` 数组已按 `skills.json` 写成 `./skills/joy2know-musician` + `./skills/joy2know-album-design`（构建会按 skills.json 重写它、只告警不拦，为免每次构建都出告警，这里把源文件一并对齐——**同一份声明只留 skills.json 一个真源，plugin.json 那份由构建同步**）。 |
| 2026-10-16 | 1.2.0 | ⚠️ 有条件通过 | **第三轮：专辑交付物从三份收缩为两份**（用户指示「一个专辑只需要专辑规划和粘贴清单两份，其它都是多余的，封面提示词包不用单独生成——它已被包含在粘贴清单里」）。正文改动：单曲 vs 专辑对照表的「交付」行由「三个文件：专辑规划 + 粘贴清单 + 生成脚本」改为「**两份文件**」；开场引导与五步流程的产物描述同步；纪律加一句**不把脚本复制进用户目录**（脚本副本是假真源：用户改了它、技能真源没变，下次跑还是旧逻辑）；自检清单把「三个文件同在一个目录」改为「**交付目录里只有那两份 md**，没有脚本副本、没有 spec.json」，并注明封面提示词**在粘贴清单里、不另出文件**；边界句改为「给封面提示词文本，它在粘贴清单的每首下面」。内嵌技能 `joy2know-album-design` 同步升 **1.1.0**（R8：升技能必查引用方）。 |
