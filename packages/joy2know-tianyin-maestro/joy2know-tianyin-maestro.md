# joy2know-tianyin-maestro 发布前检测报告

> **口径说明**：每条结论对应一次**真实运行**（命令 + 样本 + 输出要点）。
> 校验器为仓库权威版 `scripts/selfcheck.py`；平台侧入口判据复刻在 `scripts/platformcheck.py`。
> 本包是单专家（`expertType: agent`），**纯提示词包 + 3 个内嵌技能**：专家本体无 `scripts/`；
> 内嵌技能各带只读校验器（`tianyin_check.mjs` = Node 标准库；`album_check.py` / `lyric_check.py` = Python 标准库），
> 均无网络调用、无写文件、无凭证。
> **排除文件说明**：本报告是包根那一个 `joy2know-tianyin-maestro.md`（开发期文档，不进 zip）；
> 角色定义 `agents/joy2know-tianyin-maestro.md` 是**真 agent、不被排除**。

- **包名**：joy2know-tianyin-maestro
- **类型**：单专家（`expertType: "agent"`）
- **对应版本**：1.0.0
- **检测状态**：⚠️ 有条件通过
- **最后检测**：2026-10-18（**首次建包 + 首次检测** —— 详见第七节履历）
- **检测方式**：功能测试 + 完整性对照 + 合理性检查 + 反向验证

---

## 一、包内文件（从磁盘枚举，不手写）

```
   2559  .codebuddy-plugin/plugin.json       配置（expertType: agent，1 agent / **3 内嵌技能**）
  17529  agents/joy2know-tianyin-maestro.md  角色定义（开场引导 / 六步流程 / 专辑路径与三纪律 /
                                              三条路径分工 / 6 条硬规则 / 产出格式 / 三套自检清单 / 边界）
    258  skills.json                         内嵌技能声明（构建时从 packages/<名>/ 复制真源）
   5594  README.md                           包说明（他解决什么问题 / 三条底线 / 三条路径 / 包内容 / 用法）
```

**零第三方依赖核对**：专家本体无 `scripts/`、无 import、无网络调用；内嵌技能的三个校验器
（`tianyin_check.mjs` / `album_check.py` / `lyric_check.py`）分别只用 Node 标准库（`node:fs`）与
Python 标准库，结构性零依赖成立。

源包体（四个源文件，**不含本报告**）**25,940 字节 ≈ 25.3 KB**。

**头像规格（占位图）**：`avatars/joy2know-tianyin-maestro.png` = 512×512 / **10.1 KB 占位图**
（placeholders.py 生成，sha1 已记台账）—— 按 2026-10-18 新立铁律 14（真实头像才能打包和发布），
本包**未构建 zip、未提交平台**，待小乐画真头像；换真图后**必须重跑构建**（专家自身图标进 zip）。

---

## 二、能力清单与验证结果

| 能力 / 待验证项 | 验证方式（命令与样本） | 结果 | 证据要点 |
|---|---|---|---|
| plugin.json 全字段遍历 + 中英成对 + 硬约束达标 | `$V/bin/python scripts/selfcheck.py packages/joy2know-tianyin-maestro` | ✅ 通过 | **通过 11 项**（源目录 5 条预期提示：3 内嵌技能与头像「构建时才注入」、zip 未生成） |
| 官方硬约束：`displayDescription.zh` 40–50 汉字 | 同上 + 正则计汉字 | ✅ 通过 | 实测 **48 汉字**（中段，不贴边界；初稿 51 超限 1，已删「与控件」三字回到区间） |
| 官方硬约束：`defaultInitPrompt` == `quickPrompts[0]` | 同上 | ✅ 通过 | 两版（zh/en）逐字相同：「给我写一首能粘进网易天音的歌」 |
| 官方硬约束：`tags` / `quickPrompts` 各 3 个 | 同上 | ✅ 通过 | 各 3 |
| `categoryId` 在官方类目白名单内 | 同上 | ✅ 通过 | `06-ContentCreative`（与在架单专家同类；**推断值**，见第四节） |
| `agents[]` 路径存在 + agent name == agentName == 目录名 | 同上 | ✅ 通过 | 三者一致（`joy2know-tianyin-maestro`） |
| `displayName` 为品牌署名「晓得乐」（非花名） | 人工核对 plugin.json + agent frontmatter | ✅ 通过 | `displayName: {en: joy2know, zh: 晓得乐}`；卡面主标题 = `profession` = 晓得·天音音乐大师；**角色文件与正文无花名、无队友指代**（单飞重写纪律） |
| **内嵌技能主源存在** | `ls packages/<三个技能名>` | ✅ 通过 | 三技能源包均在（tianyin-musician 1.0.0 · album-design 1.1.0 · lyric-design 1.0.0） |
| 合规用词门禁 | `python3 scripts/compliance_wording.py packages/joy2know-tianyin-maestro` | ✅ 通过 | **通过 7 · 提示 0 · 失败 0**；plugin.json 英文 description 仅命中非媒体产物词（doc / document / list / plan） |
| R6 跨包审计 | `python3 scripts/series_audit.py .` | ✅ 通过 | 全仓 24 条历史候选**均不含本包**（grep 零命中） |
| **内嵌校验器判据自检（继承）** | `node packages/joy2know-tianyin-musician/scripts/tianyin_check.mjs --selftest` | ✅ 通过 | **24 项全部通过** + 反向验证 7/7（详见技能包报告第五节） |
| **内嵌副本与主源逐字节一致（未漂移）** | — | **未覆盖** | 遵守铁律 14 未构建 zip，无 zip 内副本可 diff；头像就绪重建后补，见第六节 |
| **交付形态（解压 zip 后）完整自检** | — | **未覆盖** | 同上：无 zip 可解压 |
| zip 第一层目录名正确 | — | **未覆盖** | 同上 |
| 平台入口判据：按 Expert 类型可通过 | — | **未覆盖** | `platformcheck --zip` 需 zip；铁律 14 拦下打包，见第六节 |
| 包内无硬编码凭证 | selfcheck `[sec]` 项 | ✅ 通过 | 未发现疑似凭证 |
| 卡片文案与实际开场的一致性（defaultInitPrompt 走的真实流程） | — | **未覆盖** | 需真实装载专家跑一轮开场，见第六节 |

**复现命令**

```bash
V=~/.workbuddy/binaries/python/envs/default
$V/bin/python scripts/selfcheck.py packages/joy2know-tianyin-maestro
$V/bin/python scripts/compliance_wording.py packages/joy2know-tianyin-maestro
$V/bin/python scripts/series_audit.py .
node packages/joy2know-tianyin-musician/scripts/tianyin_check.mjs --selftest
# platformcheck --zip 与解压自检：铁律 14 拦下（无真头像不打包），头像就绪后补
```

---

## 三、门 2 · 完整性对照（文档承诺 → 实现）

| 文档承诺（摘原文） | 实现位置 | 有 / 无 / 部分 | 备注 |
|---|---|---|---|
| README「他解决什么问题」四类症状（歌词写进灵感框 / 三处打架 / 纯音乐开关找不到 / 中文歌词跑结构） | `agents/…md` 流程 + 内嵌技能规则 | **有** | 分别对应硬规则 1（模式不混装）、技能规则 3（三处一致）、技能规则 5 + 专辑纪律（纯音乐只在简易模式）、技能规则 4（三件套） |
| README「三条底线」：只产文本 / 控件块不许省 / 脚本校验 | `agents/…md` 硬规则 2 + §六 边界 + 流程 ⑤ | **有** | 三处口径一致；底线 3 落到可执行脚本 |
| README「三条路径」表（单曲 / 作词 / 专辑各走各的技能） | `agents/…md` §二「三条路径怎么分工」 | **有** | 含职责边界：歌词正文以 lyric-design 为准、界面设置块以单曲技能为准、三路径可串但各用各的技能 |
| README「包内容」目录树含 references/ 与 scripts/ | 内嵌技能真源 `packages/joy2know-tianyin-musician/` | **有** | 源包实测：SKILL.md + 4 references + tianyin_check.mjs |
| 方法论主体在技能里、角色定义不重复技能内容 | `agents/…md` 首节末段 | **有** | 明写「以已加载的 `joy2know-tianyin-musician` 技能为准，本文件只规定角色、流程和验收标准」 |
| 开场引导的输入自给降级路径（五问默认值 / 纯音乐默认） | `agents/…md` §一 | **有** | 「你手上什么都没有，我也能开工」+ 默认值理由 + 游戏 / 白噪音话题改走纯音乐 |
| 校验器路径与参数（--mode / --style / --title / --singer / --tag） | `agents/…md` §二 | **有** | 命令样例与技能 SKILL.md §三 逐字一致（R3：同一规则一种表述） |
| 专辑路径三纪律（不手改 / 不写打开纯音乐开关 / 平台字段以天音为准） | `agents/…md` §二 专辑小节 | **有** | 第三条写明 album-design 按它的 F 路线改写字段，不混入 Mureka / Suno 口径 |
| README「怎么用」六行示例 | `agents/…md` 各节 | **有** | 六条示例对应的能力都有实现 |
| 单飞纪律：直接交付、不代转交、无内部 ID | `agents/…md` §六 | **有** | 「产出直接交给用户」「不出现 joy2know-tianyin-* 内部 ID」；全文无 SendMessage / 队友花名 |
| 判据争议的处理（不临场发明第三种口径） | `agents/…md` §二 末段 | **有** | 「回技能规则核对 → 如实告知口径不一致 → 按技能规则交付」 |

**兜底口径两向核对**：正向（README / plugin.json 承诺 → 有实现）全部通过；
**反向（实现里有、文档没写）未发现缺口**——agent 的 6 条硬规则在 README 三条底线与路径表中均有锚点
（硬规则 2 控件块由底线 2 覆盖；硬规则 4–6 由「他解决什么问题」与边界节覆盖）。

---

## 四、门 3 · 合理性结论

- **规则是否自洽**：✅ 无互相打架。纯音乐口径三处一致（技能规则 5：简易开关 / 高级描述 + 歌词栏留空；
  专家专辑纪律：专辑不写「打开纯音乐开关」）；三条路径的职责边界与 mureka / suno 两位大师同构
  （本包随技能同轮新建，无漂移窗口）。
- **推断是否标注为推断**：✅ `categoryId=06-ContentCreative` 在 release.config.json 标记为推断值
  （`categoryConfirmed: false`），未当实证写；深度合成驳回的处置顺序（先找客服）已按铁律 11 记入 AGENT.md。
- **错误提示是否可指导下一步**：✅ 降级路径都给明确动作（五问默认值 → 直接产出；判据争议 → 回规则核对）。
- **边界是否优雅**：✅ §六 覆盖八类边界（不生成音频 / 不做封面 MV / 不交付音频 / 不提账号权益 /
  换平台要改写 / 直接交付 / 无内部 ID / 禁解释）。
- **零依赖是否守住**：✅ 结构性成立（专家本体纯文本；内嵌校验器 Node / Python 标准库、只读）。
- **值来源是否可追溯**：✅ 版本号 1.0.0 三处一致（plugin.json / README / 本报告）；头像真源在仓库根
  `avatars/`（占位图已记 sha1 台账）；内嵌技能真源在 `packages/<技能名>/`。
- **maxTurns=50**：与单专家先例（mureka-maestro 50 / topic-planner 50）一致；单飞流程约 6 步、无成员编排，50 轮充足。
- **内嵌三技能均为 ① 态（未上架）**：专家本身也是 ①，随包进 zip 无平台记录错位风险；
  若后续某技能单独上架抬版，按铁律 9-R8 查引用方（`grep -rl "<技能名>" packages/*/skills.json`）对齐。

---

## 五、门 4 · 测试真实性自评（防放水）

- [x] 1. 只跑 happy path，没跑边界 —— **否**：合规门禁覆盖全部 7 个对外字段；selfcheck 覆盖 11 项字段硬约束
- [x] 2. 只看「没报错 / 退出码 0」，没核对输出内容 —— **否**：`defaultInitPrompt == quickPrompts[0]` 做了**逐字**比对；`displayDescription.zh` 数了汉字（48，且抓到初稿 51 超限）
- [x] 3. 把「文档写了」当成「已验证」 —— **否**：「内嵌副本 diff」「解压自检」「平台上传」「头像配色」「真实开场」五项列入第六节
- [x] 4. 自造理想样本（比真实产物干净） —— **否**：selfcheck / compliance 跑的是磁盘真实源文件
- [x] 5. 跳过失败项、不记录 —— **否**：0 项失败；selfcheck 首轮报的「avatar 缺失」已当轮补占位图复检归零，未覆盖项 5 条全部列出
- [x] 6. 修完只测修好的那条，没跑回归 —— **否**：补占位图后重跑 selfcheck 全量 11 项；displayDescription 改字后重数汉字
- [x] 7. 造错样本只造了会被抓的那种 —— **否**：反向验证依托 selfcheck 既有机理（改动字段 → 报错）与内嵌校验器的 7 个变异（改坏判据必红，详见技能包报告第五节）

**反向验证记录**（本包结构层的反向验证依托 `selfcheck.py` 的既有机理 + 内嵌校验器）：

| # | 造了什么错样本 | 预期 | 实际 |
|---|---|---|---|
| M1 | selfcheck 首轮：专家 avatar 缺失 | 报 `[XX] avatar 缺失` | ✅ 报出；补占位图后复检归零（11 项全过） |
| M2 | displayDescription.zh 初稿 51 汉字 | 超 40–50 上限 | ✅ 自检当场报错（`汉字 51 字`）；删 3 字回 48 复绿 |
| M3 | （继承自校验器）改坏 tianyin_check 判据 ×7 | 内嵌 selftest 必红 | ✅ 7/7 立刻红灯（技能包报告第五节） |

**一句话回答：本包的核心结构如果坏掉，是哪一步会亮红灯？**

→ 配置层（plugin.json 字段 / categoryId / agent 名对应 / displayDescription 汉字数 / 头像路径 / **技能名**）坏了 →
`selfcheck.py` 亮红灯。
→ 判据层（内嵌校验器阈值被改坏）坏了 → `tianyin_check.mjs --selftest` 亮红灯（24 项）。
→ 交付形态层（zip 第一层 / 内嵌副本漂移 / 头像注入）坏了 → 解压后的交付形态自检亮红灯（**本轮未跑**，见第六节）。
→ **有一类不会亮红灯**：专家**开场的实际体验**（用户一句「写首歌」能否顺滑走完六步、控件配得准不准）——
任何自动校验都读不出这个，需真实装载跑一轮（见第六节 2）。

---

## 六、未覆盖项 / 已知缺陷 / 待办

**未覆盖项**（下次检测优先消掉）：

1. **未构建 zip，交付形态层全未测**：按 2026-10-18 新立铁律 14（真实头像才能打包和发布），
   本包无真头像 → 不打包。连带未做：`platformcheck.py --zip`（预期判 `Expert ✅` / `Skill ❌`）、
   解压后自检、zip 第一层校验、内嵌副本与主源 diff（含 icon.png 注入校验）。
   `avatars/joy2know-tianyin-maestro.png` 换真图后**一次性补齐**。
2. **卡片文案与真实开场未实测**：`defaultInitPrompt` / `quickPrompts` 能否顺滑触发六步流程、
   控件配得准不准，需在 WorkBuddy 里真实装载本专家跑至少两轮（一句全默认 + 一个指定标签的主题）。
3. **平台侧真实上传未做**：从未提交（①）；`categoryId=06-ContentCreative` 是推断值。
   若被机器判「深度合成 > AI创作」：**先找客服人工复审，别改包也别补资质**（铁律 11）。
4. **头像为占位图**：10.1 KB，待小乐画真图；**换完必须重跑构建**（专家自身图标在 zip 内）。
5. **内嵌技能专辑字段的天音适配只在 agent 层声明**：album-design 的 F 路线「按目标平台改写」
   由本专家的专辑纪律承接，但「天音字段下的专辑粘贴清单长什么样」没有真实样例验证过——
   需在真实装载后跑一张小天音专辑确认两份 md 的字段口径站得住。

**已知弱项**（不阻断上架，记在案）：

- **W1 · 语义类判据靠模型执行**：规则 2 控件块齐不齐、规则 4 不编造，脚本不查（部分实现已在门 2 表中注明）。
- **W2 · 触发词偏平台词**：`profession` 与 description 含「网易天音」专名，用户口语「帮我写首歌」
  可能落到同门的 Suno / Mureka 大师。三包 description 已互相区分（各绑各的平台输入结构），
  真实分发表现待平台侧观察。

**待办**：

- 小乐画 `avatars/joy2know-tianyin-maestro.png`（512×512 真头像）→ 重跑构建 →
  `platformcheck --zip` + 解压自检 + 内嵌 diff → 按**专家入口**提交平台（技能入口必报「未找到 SKILL.md」）。
- 真实装载跑两轮开场，评估未覆盖项 2；跑一张小天音专辑，评估未覆盖项 5。

---

## 七、检测履历

| 日期 | 版本 | 状态 | 摘要（本轮测了什么、改了什么） |
|---|---|---|---|
| 2026-10-18 | 1.0.0 | ⚠️ 有条件通过 | **首次建包 + 首次检测**。新建单专家「晓得·天音音乐大师」，内嵌同步新建的技能包 `joy2know-tianyin-musician`（两种模式方法论 + 18 标签 × 18 歌手适配 + 结构校验器）+ `joy2know-album-design` 1.1.0 + `joy2know-lyric-design` 1.0.0。**源目录自检通过 11 项**（displayDescription.zh 实测 48 汉字——初稿 51 超限 1，当轮删「与控件」三字回区间；defaultInitPrompt==quickPrompts[0] 逐字相同；tags/quickPrompts 各 3；categoryId=06-ContentCreative；agent 名三处一致）；**selfcheck 首轮报 avatar 缺失**，补两张占位图（placeholders.py，sha1 入台账）后复检归零；合规门禁**通过 7 · 提示 0 · 失败 0**；R6 全仓审计 24 条历史候选**零命中本包**；内嵌校验器继承技能包报告证据（24 项自检 + 反向验证 7/7）。⭐ **遵守铁律 14：无真头像不打包** —— 未构建 zip，交付形态层五项（platformcheck / 解压自检 / zip 第一层 / 内嵌 diff / 头像注入校验）与真实开场、平台上传记入未覆盖项，共 5 项未覆盖 + 2 项弱项。 |
