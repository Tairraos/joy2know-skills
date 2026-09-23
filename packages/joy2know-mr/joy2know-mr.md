# joy2know-mr 发布前检测报告

- **包名**：joy2know-mr
- **类型**：专家
- **对应版本**：1.2.0
- **检测状态**：⚠️ 有条件通过
- **最后检测**：2026-09-23
- **检测方式**：功能测试 + 完整性对照 + 合理性检查 + 反向验证

> **本文件是开发期文档，不进 zip**（构建时自动排除）；但**要进 git**。
> 规范见仓库根 `AGENT.md` 第 3–4 节。**下次检测先读本文件**，只重测有变化的部分与「未覆盖项」。
>
> **口径说明**：本包是**纯文档专家包**（`.codebuddy-plugin/plugin.json` + `agents/joy2know-mr.md` + `README.md` + `skills.json`），**没有 `scripts/` 目录、没有可执行脚本**。
> 因此「①功能测试」落地为**字段与结构真跑校验**：必须真的运行权威校验器 `scripts/selfcheck.py`，不许读代码推断。
> 校验器在仓库根跑（只读，不 import 包内文件，故 `packages/joy2know-mr` 内无 `__pycache__`）；
> 反向验证的样本全部跑在 `/tmp/j2k-check/mr/` 副本上，绝不改 `packages/` 内任何文件。
> 受管解释器：`/Users/xiaole/.workbuddy/binaries/python/envs/default/bin/python`（Python 3.13.12）。

---

## 一、包内文件（从磁盘枚举，不手写）

```
      1950  .codebuddy-plugin/plugin.json      专家包核心配置（expertType: agent）
      2290  README.md                          对外说明（角色/底线/用法）
      6147  agents/joy2know-mr.md              角色定义（系统提示词，方法论委托给内嵌技能）
       191  skills.json                        声明内嵌技能 joy2know-clarify（构建时注入）
      3931  joy2know-mr.md                      本文件（开发期文档，不进 zip）
```

**零第三方依赖核对**：包内无任何 `scripts/`、无 `.py` 文件、无 `import` 外部包；纯文档 + JSON 配置。
`selfcheck.py` 的 `[sec]` 项扫描未发现硬编码凭证。包体（不含本报告）约 **14.5 KB**，远低于专家包 20 MB 上限。

---

## 二、能力清单与验证结果

> 无脚本可跑，故「能力」= 平台元数据的字段硬约束 + 文档承诺的落地。每一项都是**真跑 selfcheck / 真读副本文档**的证据，不是读代码推断。

| 能力 / 待验证项 | 验证方式（命令与样本） | 结果 | 证据要点 |
|---|---|---|---|
| plugin.json 全字段齐全 | `selfcheck.py packages/joy2know-mr` | ✅ 通过 | 通过 11 项；`[expert] plugin.json 字段遍历完成` |
| displayDescription.zh 汉字 40–50 | 同上（校验器实数字数） | ✅ 通过 | `汉字 48 字（官方要求 40-50）` — 恰好在上限内 |
| defaultInitPrompt == quickPrompts[0]（官方硬约束） | 同上 | ✅ 通过 | `defaultInitPrompt == quickPrompts[0]（官方硬约束）` |
| tags / quickPrompts 各固定 3 | 同上 | ✅ 通过 | `tags 数量=3` / `quickPrompts 数量=3` |
| categoryId 属官方 15 类 | 同上 + 核对白名单 | ✅ 通过 | `categoryId 合法: 06-ContentCreative`（白名单第 55 行确认） |
| author / name / plugin / agentName 一致 | 同上 | ✅ 通过 | `author.name 署名: '晓得乐'`；`name==目录名`、`plugin==name`、`agent name == agentName: joy2know-mr` |
| displayName / profession / displayDescription 中英成对 | 同上 | ✅ 通过 | 三者均为 `{en,zh}` 字典，校验器未报「未中英成对」 |
| agents[] 路径存在且 name 一致 | 同上 | ✅ 通过 | `agents 路径 存在: ./agents/joy2know-mr.md`；`agent name == agentName` |
| 内嵌技能主源存在（构建注入源） | 读 `packages/joy2know-clarify/` | ✅ 通过 | 主源含 `references/chart-selection.md`（11 类图种 §1–§11）+ `references/patterns.md`（26 处改前/改后命中，≥12 组） |
| 仓库根头像存在（构建注入源） | `ls avatars/joy2know-mr.png` | ✅ 通过 | 344 KB PNG，存在；selfcheck 记为「构建时注入」提示（非失败） |
| 无硬编码凭证 | `selfcheck.py` `[sec]` 项 | ✅ 通过 | `包内未发现硬编码凭证` |
| avatar 路径规范（avatars/ 下） | 同上 | ✅ 通过 | `avatar: avatars/expert.png` 以 `avatars/` 开头，校验器未报 |
| 反向验证：删必填字段 → 校验器亮红灯 | `/tmp` 副本删 author/version 各跑一次 | ✅ 通过 | 见第五节表 |
| 反向验证：描述越界 / prompt 不一致 → 亮红灯 | `/tmp` 副本改 displayDescription.zh、改 defaultInitPrompt | ✅ 通过 | 见第五节表 |
| 阴性对照：合规样本不乱报 | `/tmp` 合规副本 | ✅ 通过 | `=== 全部自检通过 ===`（仅 3 条提示，无 `[XX]`） |

---

## 三、门 2 · 完整性对照（文档承诺 → 实现）

> 对照基准：README.md（对外承诺）+ plugin.json（配置承诺）+ agents/joy2know-mr.md（角色实现）。
> 重点抓「文档写了、实现没做」——本包所有承诺均有落地，未见悬空引用。

| 文档承诺（摘原文） | 实现位置 | 有 / 无 / 部分 | 备注 |
|---|---|---|---|
| README「表达条理与可视化专家——让任何回答都有条理、好读」 | agents §一「表达层专家」+ profession.zh | **有** | 角色定位一致 |
| README「三条底线 1：先判级，再回答」 | agents §三 第1步（定级 L1–L4）+ §八「简单说→L1」 | **有** | 落地 |
| README「2：该画才画（11 类图种，每类写清什么时候别画）」 | agents §二 核心能力3「图示决策」+ §三 第4步「判图，对照第四列确认哪些图不该画」；内嵌 clarify `chart-selection.md` 11 类（§1–§11） | **有** | 方法论委托给内嵌技能，主源已验证含 11 类 |
| README「3：图里不编东西（数字/关系/箭头标签溯源，没数据标未提供）」 | agents §六 红线1（禁止编造）/红线2（禁止示意性图表）+ §三 第5步「核对来源」 | **有** | 落地 |
| README「包内容：skills/joy2know-clarify/（SKILL.md + references/chart-selection.md + patterns.md）」 | plugin.json `skills:["./skills/joy2know-clarify"]` + `skills.json` 声明；主源 `packages/joy2know-clarify` 含上述文件 | **有（设计如此）** | 源目录无 `skills/` 正常——构建时从主源复制注入；selfcheck 记为提示而非失败 |
| README「怎么用」6 行表 | agents §八「快捷入口」6 行表（讲/理/画/写/L4/简单说） | **有** | 两表一一对应（类比→机制→边界 等） |
| README「版本 1.1.0 · 作者：晓得乐」 | plugin.json `version` / `author.name` | **有** | 一致 |
| plugin.json `expertType: agent` + `agentName: joy2know-mr` | agents 头 `name: joy2know-mr` + `maxTurns: 100` | **有** | selfcheck 校验 `agent name == agentName` |
| plugin.json `skills:["./skills/joy2know-clarify"]` | agents 头 `skills:[joy2know-clarify]` + §二「以已加载的 joy2know-clarify 技能为准」 | **有** | 声明与委托一致 |
| plugin.json `displayName/profession/displayDescription` 中英成对 | agents 头 `displayName`/`profession` 中英成对 | **有** | `displayDescription` 仅卡面文案字段（plugin.json 持有），agent 不需重复 |
| plugin.json `defaultInitPrompt == quickPrompts[0]` | selfcheck 硬约束校验 | **有** | 实测一致 |
| plugin.json `tags`/`quickPrompts` 各 3 | selfcheck 校验数量 | **有** | 实测各=3 |
| plugin.json `categoryId: 06-ContentCreative` | 官方 15 类白名单 | **有** | 白名单确认 |
| agents §二「五条方法论细节以已加载的 joy2know-clarify 技能为准」 | 内嵌主源 `packages/joy2know-clarify` 存在且含 chart-selection.md / patterns.md | **有** | 委托非悬空——主源真实存在并有内容 |
| agents §六 红线（禁止编造/示意性图表/越界断言/推断当事实） | 与 §四「边界」/§五「自检六问」自洽 | **有** | 无互相打架 |

---

## 四、门 3 · 合理性结论

- **profession 与 displayName 口径**：✅ 配对正确、未放反。约定「卡面主标题取 profession、副标题取 displayName」——`profession.zh = 晓得·表达条理与可视化专家`（角色描述，作主标题合理），`displayName.zh = 晓得乐`（品牌署名，作副标题合理）。二者一个描述角色、一个承载品牌，不冲突。
- **规则自洽**：✅ 无互相打架。§一「不挑领域/不越界」↔ §六 红线4「禁止越界断言」同向；§三 第1步「拿不准就往下取一级」↔ §八「简单说→L1」同向；§六 红线6「用户要一句话就给一句话」↔ §四「短是默认」同向。
- **推断是否标注为推断**：✅ §六 红线5「禁止把推断当事实。推断要写明是推断」；§三 第5步「核对来源」强制每个数字/关系溯源。
- **错误提示是否可指导下一步**：N/A（无脚本）。角色自身的输出约束（§四「边界」段「不确定就直说」「这是合格回答，不是失败回答」）对 AI 行为是「可指导下一步」式的引导。
- **边界是否优雅**：✅ 角色把「【边界】段不能省」「不确定就直说」写成硬性要求；§三 第1步对「简单说/别啰嗦」无条件降级——降级路径（行为层）明确，非脚本崩溃类。
- **零依赖是否守住**：✅ 纯文档包，无 `scripts/`、无第三方包、无网络调用；`[sec]` 无凭证。
- **值来源是否可追溯**：✅ §三 第5步 + §六 红线1「必须来自用户提供、可查证来源，或已明确标注的推断；没有真实数据就不画图表，或改画结构图/关系图」——来源三分式（用户/可查证/推断）显式兜底，无凭空补值。
- **一处轻级命名视角差（非缺陷，待确认）**：agent 正文自称「你是『晓得先生』」、README 标题「晓得先生 · joy2know」，而 `displayName.zh = 晓得乐`（品牌署名，与 `author.name` 同值）。即**对外展示的 persona 名（晓得先生）未进入 `displayName`**。这是「品牌署名 vs 角色 persona」的常见分层，不违反任何硬约束、不影响上架；但若平台卡面要展示「晓得先生」，应把 `displayName.zh` 改为「晓得先生」，或统一 README/agent 自称。见第六节。

---

## 五、门 4 · 测试真实性与反向验证

### 防放水七条自查

- [x] 1. 只跑 happy path，没跑边界 —— **否**：跑了 5 组错样本（删 author/version、描述 30/60 字、prompt 改一字）+ 1 组阴性对照。
- [x] 2. 只看「没报错」，没核对输出内容 —— **否**：核对了 `displayDescription.zh` 实数字数（48）、`defaultInitPrompt==quickPrompts[0]` 逐字相等、tags/quickPrompts 数量=3、categoryId 白名单命中，不是只看退出码。
- [x] 3. 把「文档写了」当成「已验证」 —— **否**：第三节每条承诺都给了实现位置（agents 节号 / plugin.json 字段 / 内嵌主源文件），并实际读了 `packages/joy2know-clarify` 确认「11 类图种」非空悬。
- [x] 4. 自造理想样本 —— **否**：反向样本用真实校验器会抓的形态（删字段、字数越界、首尾 prompt 不一致），非干净样本。
- [x] 5. 跳过失败项、不记录 —— **否**：唯一的轻级问题（命名视角差）记入第六节，未藏。
- [x] 6. 修完只测修好的那条，没跑回归 —— **不适用**：本轮不改包内任何文件，无「修」。
- [x] 7. 造错样本只造了会被抓的那种 —— **否**：下表 6 组含 5 组「应被抓」+ 1 组「应通过」，阴性对照确认合规样本**不乱报**。

### 反向验证记录（全部在 `/tmp/j2k-check/mr/` 副本真跑，未碰 `packages/`）

| # | 造了什么错样本 / 应通过样本 | 预期 | 实际 |
|---|---|---|---|
| 1 | 副本 `plugin.json` 删 `author` 字段 | 报缺 author | ✅ `[XX] [expert] plugin.json 缺字段: author` + `[XX] author 为空（官方必填）` |
| 2 | 副本删 `version` 字段 | 报缺 version | ✅ `[XX] [expert] plugin.json 缺字段: version` |
| 3 | `displayDescription.zh` 改为 30 个汉字 | 报字数越界 | ✅ `[XX] displayDescription.zh 汉字 30 字，超出官方要求 40-50` |
| 4 | `displayDescription.zh` 改为 60 个汉字 | 报字数越界 | ✅ `[XX] displayDescription.zh 汉字 60 字，超出官方要求 40-50` |
| 5 | `defaultInitPrompt.zh` 改一个字（末尾加「吗」） | 报与 quickPrompts[0] 不一致 | ✅ `[XX] defaultInitPrompt={...'帮我把这件事讲明白，先给结论吗'...} 与 quickPrompts[0]={...'帮我把这件事讲明白，先给结论'...} 不一致` |
| 6（阴性） | 合规副本（原文不动） | 全过、不乱报 | ✅ `=== 全部自检通过 ===`，仅 3 条提示（skills 未生成 / 头像构建注入 / 缺 zip），**无 `[XX]`** |

### 一句话回答：本包的核心能力如果坏掉，是哪一步会亮红灯？

→ `plugin.json` 字段级硬约束（缺必填 / `displayDescription.zh` 字数越界 / `defaultInitPrompt≠quickPrompts[0]` / `tags`·`quickPrompts` 非 3 / `categoryId` 非法）坏掉，会在 **`selfcheck.py` 的 `[XX]`** 亮红灯（已用 5 组错样本验证抓得到）。
**但有一处不会亮红灯**：角色**行为层**——人格是否稳定、是否真「先给结论」、图是否真「不编东西」、语气是否克制——selfcheck 完全看不到，只能由真人对练发现（见第六节未覆盖项 1）。

---

## 六、未覆盖项与缺陷

### 未覆盖项（AI 行为层与构建期产物无法机器测，如实列此）

1. **AI 行为层未测**：角色的人格稳定性、是否真「先给结论」、图示决策是否真「该画才画」、图内是否真「不编东西」、语气是否克制——均属对话层，selfcheck 与任何脚本都测不了，需真人对练验证。
2. **内嵌 clarify 技能的实际出图质量未测**：只验证了主源 `packages/joy2know-clarify` 存在且 `chart-selection.md` 含 11 类、`patterns.md` 含改前/改后对照；未实测 AI 真用这些规则产出的 SVG/图是否准确、渲染是否正常。
3. **平台实际渲染卡面未实测**：`profession` 作主标题、`displayName` 作副标题、`avatar` 512×512 的真实展示效果——selfcheck 在源目录以「提示」处理头像/技能注入，未跑 `pnpm build` 注入真实包后校验。
4. **`description`（英）长度未逐一核平台侧上限**：selfcheck 仅查必填字段与 `displayDescription.zh` 字数（40–50），未校验英文 `description` 的平台长度限制（若有）。
5. **未跑 `pnpm build`**：按纪律本检测不执行构建；构建期注入 `skills/` 与 `avatar` 后的 zip 第一层与体积未经本检测校验（selfcheck 记为提示，由 `build.mjs` 另校）。
6. **通用审计脚本 `audit.py` 不存在**：任务提及的 `/tmp/j2k-check/audit.py` 在本机不存在，按纪律未自造，章节连续性/悬空交叉引用/占位符残留的自动化审计未做（人工已通读 README/agent 未见明显悬空引用）。

### 已知缺陷

- **【已复核改判 2026-09-23 · 系口径误读，非缺陷】** 原条目如下（保留原文以便对照）：
  > **缺陷（轻）· 命名视角差**：`displayName.zh = 晓得乐`（品牌署名，与 `author.name` 同值），但 agent 正文自称「你是『晓得先生』」、README 标题「晓得先生 · joy2know」——**对外 persona 名「晓得先生」未进入 `displayName`**。不影响上架、不违反硬约束（profession/displayName 作为主/副标题配对正确）。建议二选一：若卡面要展示「晓得先生」则把 `displayName.zh` 改为「晓得先生」；若「晓得乐」是拟定的品牌展示名，则统一 README/agent 自称。属可选项，非硬缺陷。

**【2026-09-23 处理记录 · 版本 1.1.0 → 1.2.0】**

**先说一件重要的事：本条「缺陷」经复核判定为「口径误读」，不是缺陷 —— 故不改 `displayName`。**

- **改判依据（对着兄弟包实测，不靠推理）**：四个专家/专家团的 `displayName.zh` **全部是「晓得乐」**（4/4），
  而每个包另有**各自的角色代号**：
  | 包 | `displayName.zh` | `profession.zh` | 角色代号（README H1 / agent 自称） |
  |---|---|---|---|
  | code-scholar | 晓得乐 | 晓得·代码考古 | **考古先生** |
  | mr | 晓得乐 | 晓得·表达条理 | **晓得先生** |
  | cine-team | 晓得乐 | 晓得·视频方案团 | 晓得总导演组 |
  | polish-team | 晓得乐 | 晓得·文案打磨团 | 晓得文案打磨团 |

  即「**`displayName` 固定为品牌花名「晓得乐」+ 每包自有角色代号**」是**系列既定设计**，
  mr 的「晓得先生」与 code-scholar 的「考古先生」同构。原报告把它当成「命名视角差」，
  是把**系列惯例**误读成了缺陷。**不改任何命名**（改了反而破坏系列一致性）。
  `displayName` 历史上确曾是「晓得先生」（2026-09-16 按系列铁律统一为「晓得乐」），
  但当时只改了 `plugin.json`，README 与 agent 正文没跟 —— **这才是真问题所在**（见下条）。

**真正改掉的是两处「没跟上」「不合系列写法」的硬伤：**

- **修复 1 · README H1 写法与其余三个专家包不一致**：原 `# 晓得先生 · joy2know`
  → **`# 晓得先生（joy2know-mr）`**。
  其余三个专家包（code-scholar / cine-team / polish-team）的 H1 一律是
  「**`<角色名>（joy2know-<包名>）`**」；mr 用的是「`<角色名> · joy2know`」这一独有写法。
  改为系列写法后，四个包的 H1 结构完全同构。
- **修复 2 · README 目录树列了构建注入的文件而未加注（系列通病，同 cine-team / code-scholar / polish-team）**：
  源包实际只有 `.codebuddy-plugin/plugin.json`、`agents/joy2know-mr.md`、`skills.json`、`README.md` 四类文件，
  README 的目录树却画了 `avatars/expert.png` 与 `skills/joy2know-clarify/`。
  已给这两行标上 `（由构建注入）`，并在块后补「**形态说明**」段 ——
  写明 `avatars/` 由构建从仓库根 `avatars/joy2know-mr.png` 注入、`skills/` 按 `skills.json` 声明的名单
  从 `packages/<技能名>/` 复制**唯一真源**（本包不存副本，避免同一技能两份、改一处漏一处）。

**验收（真跑；改后 7/7，git 原始版本 5/7）**：

| # | 用例（判据取自包内真源 / 系列实测惯例） | 改前（git 原始版本） | 改后 |
|---|---|---|---|
| M1 | README H1 采用系列写法「`<角色名>（joy2know-mr）`」 | ❌ `# 晓得先生 · joy2know` | ✅ `# 晓得先生（joy2know-mr）` |
| M2 | 目录树含 `avatars`/`skills/` 时必须加形态说明 | ❌ `注入项=['avatars','skills/']；说明=无` | ✅ 说明已加（已核实 README 仅 1 个代码块，即目录树，非取错块） |
| M3 | `displayName.zh` 仍为系列统一花名「晓得乐」 | ✅（改判：不得动） | ✅ 未动 |
| M4 | agent 正文保留角色代号「晓得先生」 | ✅（改判：不得被「统一」抹掉） | ✅ 未动 |
| M5 | `displayDescription.zh` 40–50 汉字（回归） | ✅ 48 | ✅ 未变 |
| M6 | `defaultInitPrompt` 逐字等于 `quickPrompts[0]`（回归） | ✅ | ✅ 未变 |
| M7 | README 版本行 == `plugin.json` 的 `version` | ✅ | ✅ 1.2.0 两处一致 |

**反向验证**：同一套用例对 **git 原始版本**跑出 **5/7**，失败的 2 条（M1/M2）精确对应两处修复；
**M3/M4 在两侧都通过，是刻意设计** —— 这两条是「改判的守卫」：
它们把「`displayName` 不许动」「角色代号不许被抹」写成可回归的判据，
防止后来者（或下一个 harness）再照原报告的误判去「统一命名」。
M5/M6/M7 作为回归项两侧均通过，说明判据不乱报。



### 待办（本轮两项修复已完成，见上）

- ~~视品牌决策处理缺陷（轻）：统一 `displayName` 与 persona 命名。~~ → **已改判：不动命名**；真正修掉的是 README H1 写法与目录树形态说明（两处系列偏差）。
- 优先消未覆盖项 1（真人对练验证行为层）+ 未覆盖项 3（构建后卡面渲染实测）。
- 下次检测先补未覆盖项 2、4（出图实测 / 英文 description 长度核平台上限）。
- **本轮顺带纠正一条口径**：未覆盖项 4 说「未校验英文 `description` 的平台长度限制」—— 2026-09-23 已实测出**专家包**的系列区间（`plugin.description` en 175–197、`displayDescription.en` 218–222），本包 197 / 220 **都在区间内**；
  已建议把该口径写进 `docs/平台资产规范.md`（本轮未改该文档，属跨包规范另案处理）。

---

## 七、检测履历

| 日期 | 版本 | 状态 | 摘要（本轮测了什么、改了什么） |
|---|---|---|---|
| 2026-09-23 | 1.1.0 | ⚠️ 有条件通过 | 首次成文（覆写骨架）。纯文档专家包，无脚本，故「功能测试」落地为 selfcheck 真跑：仓库根跑 `selfcheck.py packages/joy2know-mr` → 通过 11 项 / 0 问题 / 3 提示（skills 未生成、头像构建注入、缺 zip，均设计如此）；displayDescription.zh 实计 48 字（40–50 内）、defaultInitPrompt==quickPrompts[0]、tags/quickPrompts 各 3、categoryId 06-ContentCreative 合法。门2：README/plugin.json/agents 每条承诺均落地（含内嵌 clarify 主源验证含 11 类图种 + 改前改后对照），无悬空引用。门3：profession/displayName 口径正确未放反，规则自洽，零依赖守住；记 1 处轻级命名视角差（晓得先生 vs 晓得乐）。门4：副本上 5 组错样本（删 author/version、描述 30/60 字、prompt 改一字）均触发 `[XX]`，阴性对照合规副本全过不乱报。未改包内任何文件、未跑 pnpm build、未造 audit.py。 |
| 2026-09-23 | 1.2.0 | ⚠️ 有条件通过 | **修复轮**：原报「命名视角差」经复核**改判为口径误读**（四个专家包 `displayName.zh` 全为「晓得乐」，各包另有角色代号：考古先生 / 晓得先生 / 总导演组 / 打磨团 —— 系既定设计，**命名未动**，并把「不许动」写成 M3/M4 两条守卫判据）。真正修掉两处系列偏差：① README H1 `晓得先生 · joy2know` → `晓得先生（joy2know-mr）`（对齐其余三个专家包写法）；② README 目录树给 `avatars/`、`skills/` 标「由构建注入」并补「形态说明」段（系列通病）。验收：**真跑 7/7，同一套用例对 git 原始版本 5/7**（失败 M1/M2 对应两处修复；M3/M4 改判守卫两侧均通过）。
| 2026-09-23 | 1.2.0 | ⚠️ 有条件通过 | **改名尝试被平台驳回 → 已回退**：包名 `joy2know-mr` → `joy2know-articulate`（`mr` 是「先生」的角色意象，单看包名看不出能力），8 处联动改完后重传，平台驳回：「包内 name "joy2know-articulate" 与当前资产的 name "joy2know-mr" 不一致：name 是资产的唯一标识，不允许修改。请将 plugin.json 中的 name 改回 "joy2know-mr" 后重新打包上传」。→ **`name` 是平台侧不可变主键**，改名直接掐断「更新」链路 —— 原报告里那条「未实证风险」由此**转为实证**。已把 8 处全部回退（目录 · `plugin.json` 四处 · 角色文件名与 frontmatter `name` · 报告文件名 · 图标名 · 台账 key · 外部引用），全部 `git mv` 去、`git mv` 回，git 历史干净；`plugin.json` 与 `agents/*.md` 已逐字节回到改名前状态。验收：`selfcheck.py packages/joy2know-mr` 通过 11 项 / 0 问题；重建 `dist/joy2know-mr-v1.2.0.zip`。**结论**：本包 `name` 保持 `joy2know-mr` **冻结不动** —— 用户可见的语义名由 `profession`「晓得·表达条理与可视化专家」承担，`name` 不入界面，改名的收益只落在仓库内部，不值当牺牲「更新」链路。已立为 R7。 |
