# joy2know-polish-team 发布前检测报告

> **口径说明**：每条结论对应一次**真实运行**（命令 + 样本 + 输出要点）。
> 门 1 / 门 4 的副本跑在 `/tmp/j2k-check/baseline/joy2know-polish-team`（源包只过读，不写、`packages/` 内无 `__pycache__`）。
> 校验器为仓库权威版 `scripts/selfcheck.py`（2026-09-23 搬入）。本包是专家团（`expertType: team`，1 主理人 + 4 成员）。
> **排除文件说明**：本报告是包根那一个 `joy2know-polish-team.md`（开发期文档，不进 zip）；主理人 `agents/joy2know-polish-lead.md` 是**真 agent、不被排除**，报告名与主理人名不同属正常 —— 严格只按「包根同名 md」排除，未误伤主理人。

- **包名**：joy2know-polish-team
- **类型**：专家团（`expertType: "team"`，1 主理人 + 4 成员）
- **对应版本**：1.2.0
- **检测状态**：⚠️ 有条件通过
- **最后检测**：2026-09-23
- **检测方式**：功能测试 + 完整性对照 + 合理性检查 + 反向验证

---

## 一、包内文件（从磁盘枚举，不手写）

```
  4205  .codebuddy-plugin/plugin.json   配置（expertType: team，5 agents / 4 内嵌技能 / 5 members）
  3945  README.md                        包说明（团队构成、体检流程、顺序铁律、内置技能、适用边界）
    38  settings.json                    主理人声明 {"agent": "joy2know-polish-lead"}（平台校验器实查这个名）
    38  setting.json                     同上（沿用官方模板名，兼容保留）
   263  skills.json                       内嵌技能声明（构建时从 packages/<名>/ 复制真源）
  11794  agents/joy2know-polish-lead.md   主理人·闻山（体检+路由+编排，含「严禁行为」可观测判定）
  5312  agents/polish-clarity.md          条理编辑·林知
  5019  agents/polish-distill.md         提炼编辑·简宁
  6807  agents/polish-tone.md            语言编辑·苏白
  4755  agents/polish-visual.md          数据可视化编辑·方寸
  4418  joy2know-polish-team.md           本文件（开发期文档，不进 zip）
```

**零第三方依赖核对**：本包无 `scripts/`、无任何可执行代码与网络调用，结构性零依赖成立。
源包体（不含本报告）约 **32.1 KB**；发布后 zip 另含构建注入的 6 张头像（团队图标 + 5 角色，合计约 **2.35 MB**）与 4 个内嵌技能。
专家包上限 **20 MB**，余量充足（zip 实际体积未测，本包本轮未跑构建 —— 见第六节未覆盖项 2、3）。

**头像规格（已逐一实测）**：团队图标 `avatars/joy2know-polish-team.png` = 512×512 / 387.3 KB；
5 张成员头像（`avatars/joy2know-polish-team/*.png`）= 全部 512×512、370.6–402.1 KB，均 ≤500 KB 且 ≈512² 方图，**6/6 合规**。
头像真源在仓库根 `avatars/`（构建注入），包内不留副本 —— 单一真源成立。

---

## 二、能力清单与验证结果

| 能力 / 待验证项 | 验证方式（命令与样本） | 结果 | 证据要点 |
|---|---|---|---|
| plugin.json 全字段遍历 + 三方成对 + 硬约束达标 | `~/.workbuddy/binaries/python/envs/default/bin/python scripts/selfcheck.py packages/joy2know-polish-team` | ✅ 通过 | **22 通过 / 0 未通过**（源目录另有 6 条预期提示：内嵌技能与头像「构建时才注入」、zip 未生成） |
| 官方硬约束：`displayDescription.zh` 40–50 汉字 | 同上 | ✅ 通过 | 实测 **46 汉字** |
| 官方硬约束：`defaultInitPrompt` == `quickPrompts[0]` | 同上 | ✅ 通过 | 两版（zh/en）逐字相同（`plugin.json:46-49` = `:65-69`） |
| 官方硬约束：`tags` / `quickPrompts` 各 3 个 | 同上 | ✅ 通过 | 各 3 |
| `categoryId` 在官方 15 类白名单内 | 同上 | ✅ 通过 | `06-ContentCreative`（专家与专家团共用同一份分类清单） |
| 专家团专属：`settings.json` 与 `setting.json` **两个名字都在**且内容一致 | 同上 + `json.dumps` 比对 | ✅ 通过 | 两份均为 `{"agent":"joy2know-polish-lead"}`，38 字节逐字相同 |
| 专家团专属：两份文件声明的 `agent` == 主理人 | 同上 | ✅ 通过 | 均等于 `teamInfo.leadAgent` = `agentName` = `joy2know-polish-lead` |
| `agents[]` 5 条路径全部存在 | 同上 | ✅ 通过 | 5/5 存在 |
| **`agents/*.md` 的 `name` 与 `agentName` / `members[].id` 严格对应** | 同上 | ✅ 通过 | 主理人 1 个 `name==agentName`；其余 4 个全部命中 `members[].id`（`polish-clarity/distill/visual/tone`）—— 一一对应，无多无少 |
| 主理人文件名带团前缀 | 文件枚举 | ✅ 通过 | `joy2know-polish-lead.md`（非 `polish-lead.md`），与规则一致 |
| `teamInfo.leadAgent`+`memberAgents` 与实际 agent 一致 | 人工比对 + 文件名去 `.md` | ✅ 通过 | `leadAgent`=joy2know-polish-lead；`memberAgents` 4 条 == `members[]` 非 lead 的 4 个 `id` == `agents/` 4 个成员文件名，三者同序同集合 |
| `members[]` 每成员恰好 5 字段 | `python3 -c` 解析 plugin.json | ✅ 通过 | 5 成员各 `[id,name,profession,avatar,role]` 共 **5** 字段，无多无少 |
| 各成员 `profession` 各司其职不重叠 | 解析 `members[].profession` | ✅ 通过 | 条理/提炼/可视化/语言编辑，四棒职责互不重叠 |
| 主理人路由覆盖全部 4 成员 | 读 `agents/joy2know-polish-lead.md §二` | ✅ 通过 | 条理→林知 / 容量→简宁 / 形态→方寸 / 语气→苏白；兜底→林知+苏白，4 名全覆盖 |
| 内嵌技能（clarify/humanize/deck/dashboard）主源存在 | `ls packages/<名>` | ✅ 通过 | 4 个源技能包均存在（构建注入前校验） |
| 头像路径与规格 | `python3` 解析 PNG 头 + `wc -c`，6 张 | ✅ 通过 | 512×512 / 370–402 KB（团队图标 387 KB），6/6 合规；`avatar` 字段为 `avatars/team.png`（`avatars/` 前缀 ✓） |
| 包内无硬编码凭证 | selfcheck `[sec]` 项 | ✅ 通过 | 未发现疑似凭证 |
| 反向验证：6 组「应该被抓」的错样本 | 见第五节 | ✅ 5/6 抓到 | 1 组（多加字段）暴露校验器盲区，见第六节缺陷 1 |
| 团队成员实际协作行为（建团队/调度/中转/不代写） | — | 未覆盖 | 需真实运行团队，见第六节 |
| 构建暂存形态（注入 `skills/` 与 `avatars/` 后）自检 | — | 未覆盖 | 未跑本包构建，见第六节 |

**复现命令**

```bash
V=~/.workbuddy/binaries/python/envs/default
$V/bin/python scripts/selfcheck.py packages/joy2know-polish-team        # 正式结果（源目录，6 条提示属预期）
# 反向验证（临时目录需提供 avatars/ 软链，否则团队图标回退会多一条假红灯）：
ln -sfn "$PWD/avatars" /tmp/j2k-check/avatars
$V/bin/python scripts/selfcheck.py /tmp/j2k-check/baseline/joy2know-polish-team
```

---

## 三、门 2 · 完整性对照（文档承诺 → 实现）

| 文档承诺（摘原文） | 实现位置 | 有 / 无 / 部分 | 备注 |
|---|---|---|---|
| README「团队构成」表：主理人 + 条理/提炼/可视化/语言 4 编辑 | `plugin.json members[]`（`:79-145`）+ `agents/*.md` | **有** | 5 条成员、5 个 agent 文件，一一对应 |
| README「先诊断，不是四棒全上」+ Phase 0 体检 | `agents/joy2know-polish-lead.md §二`（`:36-42`）+ `§六 Phase 0`（`:98-119`） | **有** | 体检表「必须引原文作证据」（`:116`）；兜底路径（`:42`） |
| README「顺序铁律：语言编辑必须是最后一棒」 | lead md `§五`（`:78-94`）+ `Phase 4`（`:139-145`）+ `§二`铁律（`:44`） | **有** | 与 README/plugin.json 三处口径一致，见门 3 |
| `plugin.json` description：「a four-editor … untangle / distill into talkable pages / one-page dashboard / strip machine tone」 | `members[]` 4 非主理人 + 各 agent 职责 | **有** | 4 编辑齐备（clarity/distill/visual/tone），与描述逐棒对应 |
| `displayDescription.zh`：「理清条理、压成能讲的、做成能发的看板，最后改掉机器腔调」 | `members[]` + 各 agent | **有** | 顺序 条理→提炼→可视化→语气，三处一致 |
| `displayDescription.en`：「untangle, distill into talkable pages, build a one-page dashboard, and strip machine tone last」 | 同上 | **有** | en 与 zh/描述同序同义，无 cine-team 那种「漏角色」口径冲突 |
| README「内置技能」4 个（clarify/humanize/deck/dashboard） | `plugin.json skills[]`（`:15-20`）+ 各 agent `skills:` 绑定 | **部分** | 源 4 技能包均存在（已确认）；构建注入后副本一致性未实测 → 见六 · 未覆盖 2 |
| README「适用与不适用」（不负责从零创作 / 事实核查 / 改观点强度 / 不承诺 AI 检测率） | lead md `§八`（`:173-179`） | **有** | 两处一致，且全包无网络调用路径 |
| README 目录结构图列 `avatars/` 与 `skills/` | 构建时注入 | **有（设计如此）** | 源包无此两目录是设计如此（selfcheck 记 note）；README 描述发布后 zip 形态，与交付物一致 |
| lead md `§三` 严禁行为（不代写/不直连/不 spawn 自己 + 可观测判定） | lead md `:59-67` | **有** | 含可观测判定（`:67`：「回复出现多角色内容即违规，必须改为实际调度」） |
| lead md `§二` 路由表覆盖全部 4 成员 | lead md `:36-42` | **有** | 4 名全覆盖 + 兜底路径，无遗漏 |
| lead md `§四` 团队成员表 4 行 | `members[]` | **有** | 逐行对应 id/名字/职业/产出物 |

**兜底口径两向核对**：正向（plugin.json / README / lead md 承诺 → 有实现）全部通过；
**反向（实现里有、README 没写）未发现缺口** —— 本包 README 与配置/主理人三方口径高度一致（与 cine-team 的 README 系统性脱节不同），仅内嵌技能「构建后副本一致性」因未跑构建而列为未覆盖（见六）。

---

## 四、门 3 · 合理性结论

- **规则是否自洽**：✅ 无互相打架。三处顺序表述完全一致 —— README `顺序铁律`（`:35`）、`plugin.json displayDescription`（`:41-42`）、lead md `§五`（`:84-86`）均为「条理→提炼→可视化→语气，语气强制最后」。lead「自己不改稿、只编排」与成员职责表互补不重叠；各成员 `profession` 四棒各管一摊（条理/提炼/可视化/语言），无职责交叉。
- **推断是否标注为推断**：不适用（本包不含脚本与数据推断逻辑）；但 lead md `§六 Phase 0`（`:116`）要求体检「引原文作证据」、`§六`汇编含「假设与待确认」节（`:159`），精神一致（不把猜的当结论）。
- **错误提示是否可指导下一步**：不适用（无脚本）。可类比的是 lead md `§三.3`（`:57`）退回机制（「发现矛盾退回该成员重做，不要自己动手改」），给了明确下一步。
- **边界是否优雅**：✅ lead md `§八`（`:173-179`）覆盖五类边界：不负责从零创作、不负责事实核查、不改变观点与判断强度（「可能有效」不许变「有效」）、不承诺 AI 检测率、用户只要其中一棒时允许跳过但须跑体检并告知遗留问题。
- **零依赖是否守住**：✅ 结构性成立（无 `scripts/`、无 import、无网络调用）。
- **值来源是否可追溯**：✅ 源包各文件版本号一致为 1.1.0（`plugin.json`、`README` 末行）；头像真源在仓库根 `avatars/`（构建注入），包内不留副本；内嵌技能真源在 `packages/<名>/`（单一真源）。
- **description 长度齐平性**：⚠️ 实测 `description` **502 字符**，超出同系列专家包 239–386 字区间（见六 · 缺陷 2）。平台只硬约束 `displayDescription.zh` 40–50 汉字（本包 46 字达标），description 自由长度非硬约束，故不影响上架，但偏离系列齐平。

---

## 五、门 4 · 测试真实性自评（防放水）

- [x] 1. 只跑 happy path，没跑边界 —— **否**：6 组错样本覆盖 6 类不同约束（双文件缺失 / 内容不一致 / 成员 id 失配 / 多字段 / 主理人缺前缀 / 阴性对照）
- [x] 2. 只看「没报错 / 退出码 0」，没核对输出内容 —— **否**：逐条核对报错措辞是否**指向正确的那一项**，并确认未误伤其它检查项
- [x] 3. 把「文档写了」当成「已验证」 —— **否**：第三节把「内嵌技能构建后副本一致性」标「部分」并进第六节；`agents` 的 `skills:` 字段因无法核实平台支持，明确列入未覆盖
- [x] 4. 自造理想样本（比真实产物干净） —— **否**：样本环境先补 `avatars/` 软链让基线全绿（见第四节踩坑记录），再在副本上造错，结论取自修正后运行
- [x] 5. 跳过失败项、不记录 —— **否**：1 处校验器盲区（缺陷 1）+ 1 处长度偏离（缺陷 2）+ 6 项未覆盖，全部记在第六节
- [x] 6. 修完只测修好的那条，没跑回归 —— **不适用**：本轮不改包内任何文件；副本上造错后均从干净基线重新复制，不是只重跑报错那组
- [x] 7. 造错样本只造了会被抓的那种 —— **否**：主动造了「多加字段」这种**平台真会打回**的样本，结果**没被抓** —— 正是这条反向验证抓出了缺陷 1（校验器盲区）

**反向验证记录**

| # | 造了什么错样本 | 预期 | 实际 |
|---|---|---|---|
| 1 | 副本里**删掉** `setting.json`（只留 `settings.json`） | 报缺 setting.json | ✅ `专家团缺 setting.json（平台查 settings.json，官方模板用 setting.json，两个都要放）` |
| 2 | 把 `setting.json` 的 `agent` 改成 `someone-else` | 报与主理人不一致 + 两文件不一致 | ✅ 同时报「agent='someone-else' 与主理人 'joy2know-polish-lead' 不一致」+「settings.json 与 setting.json 内容不一致」 |
| 3 | 改 `members[].id` 的 `polish-clarity` → `polish-clarity-x` | 报一一对应断裂 | ✅ `agent name='polish-clarity' 既非 agentName='joy2know-polish-lead'，也不在 members[].id 中` |
| 4 | 给 `members[].id` 某成员多加一个 `extra_field` 字段 | 应被抓「字段数超 5」 | ❌ **未被抓**：selfcheck 仍「全部自检通过」（退出码 0）—— 校验器无成员字段数检查 → 见六 · 缺陷 1 |
| 5 | 主理人文件名去掉团前缀（`joy2know-polish-lead.md` → `polish-lead.md`） | 报 agents 路径缺失 | ✅ `agents 路径 缺失: ./agents/joy2know-polish-lead.md` |
| 6 | 阴性对照（合规副本，仅复制基线） | 全绿、不乱报 | ✅ `全部自检通过`（仅 6 条预期提示，无 [XX]） |

**本节踩坑记录（与包本身无关，与检测方法有关）**：第一轮反向验证时基线样本也多报一条 `avatar 缺失` 假红灯。
排查后确认是**样本环境缺 `avatars/`**：selfcheck 对源目录跑时回落到 `<父目录>/avatars/<包名>.png` 找真源，临时目录没有这一层就报红。
在 `/tmp/j2k-check/` 补一个 `avatars/` 软链（指向仓库根）后，基线恢复 **22 通过 / 0 问题**，6 组错样本各自只亮对应红灯。
**教训**：跑反向验证前先让「干净样本」全绿，否则会把环境噪声当成包的缺陷。

**一句话回答：本包的核心结构如果坏掉，是哪一步会亮红灯？**
→ 平台解析层（配置字段 / 成员对应 / settings 双文件 / 主理人前缀 / 头像路径）坏了 → `selfcheck.py` 亮红灯，已用 5 组错样本反向验证。
→ **有一处不会亮红灯**：`members[]` 某成员字段数不是 5（多字段或漏字段）—— 校验器不检查，需靠人工/构建侧兜底（这正是缺陷 1）。配置三处顺序口径、README 与实现一致性则属于文档层，无任何自动检查盯着，但本轮已人工核对齐（无冲突）。

---

## 六、未覆盖项 / 已知缺陷 / 待办

**未覆盖项**（下次检测优先消掉这些）：

1. **团队协作行为全未测**：团队创建（「必须且只能由你执行」）、按体检调度成员、消息经主理人中转、「禁止代写」的可观测判定（回复里出现一口气写完的多角色内容即违规）—— 都只能真跑一次团队才知道，本地无团队运行环境。
2. **内嵌技能构建暂存形态未校验**：正式门禁跑在构建暂存目录上（含注入的 `skills/` 4 个 + `avatars/` 6 张）。源 4 技能包均存在已确认，但「注入副本与主源一致（未漂移）」**未实测**（selfcheck 的 diff 只在构建后暂存层生效，本包未跑 `pnpm build`）。
3. **构建后 zip 第一层 / 体积未测**：未跑 `pnpm build`，因此 zip 第一层是否为包目录、zip 体积（预估含头像约 2.4 MB，远低于 20 MB）两项未经本轮实测。
4. **`agents/*.md` 的 `skills:` 字段是否被平台支持未核实**：5 个 agent 均声明了 `skills` 绑定（lead/clarity: clarify；distill: deck；visual: dashboard；tone: humanize）。口径合理，但 `docs/平台资产规范.md` 与官方文档未列该字段，本轮无法确认平台是否解析它。
5. **成员头像「角色辨识度」未评估**：规格合规已测（6/6 512²/≤500KB），但 6 张头像是否与角色气质相符属主观判断，本轮不评。
6. **平台侧真实上传 / 解析未实测**：`settings.json` 双文件是 2026-09-17 的实测结论，本包未再实测；真实上传解析失败率、审核时长未记录。

**已知缺陷**（**处理情况见本节末**）：

- **【已修 2026-09-23（工具侧）】** **缺陷 1（轻）· 校验器不校验 `members[]` 字段数**：反向验证 S4 给某成员加 `extra_field`，`selfcheck.py` 仍「全部自检通过」（退出码 0），未报「字段数超 5 / 缺字段」。
  根因：校验器只读取 `member_ids`（`selfcheck.py:325`），对每个成员的字段集合无 `==5` 检查。
  **影响**：源包 5 成员各恰 5 字段（id/name/profession/avatar/role，已实测）正确，**不影响本包上架**；但校验器对「多字段 / 缺字段」无防护，属平台自检盲区。
  建议：在 `check_expert` 里对每个 member 增加「字段集合必须恰为 {id,name,profession,avatar,role}」的校验（多/少即 `bad`）。
- **【已修 2026-09-23】** **缺陷 2（轻）· `description` 长度偏离系列齐平**：实测 `description` **502 字符**，超出同系列专家包 239–386 字区间（如 cine-team 约 386 字）。
  **影响**：平台只硬约束 `displayDescription.zh` 40–50 汉字（本包 46 字达标），`description` 自由长度非硬约束，**不影响上架**；但偏离系列齐平，建议压到 ~380 字内以求一致。

**【2026-09-23 处理记录 · 版本 1.1.0 → 1.2.0】**

- **缺陷 1 已修（工具侧，本包不动）**：在仓库 `scripts/selfcheck.py` 的专家校验里新增
  「`members[]` 每项字段集合必须**恰好**为 `{id,name,profession,avatar,role}`（多/少即 `[XX]`）」，
  并对每个成员逐条输出 `[OK] members[<id>] 字段数=5 且全为规定字段`。
  **用本包的两个新样本反向验证**：
  - 给 `members[0]` 加 `extra_field` → `[XX] members[joy2know-polish-lead] 字段不合规：多出 ['extra_field']`（退出码 1）；
  - 删掉 `members[2].role` → `[XX] members[polish-distill] 字段不合规：多出 无 / 缺少 ['role']`（退出码 1）。
  **这正是原报告反向验证 S4「加字段仍全绿」的那个盲区，现已封住**；源包本体 5 成员仍全绿（阴性对照）。
- **缺陷 2 已修（压缩 description）**：`description` 由 **502 → 201 字符**，
  收进**兄弟专家包实测区间**（cine-team 176 / code-scholar 175 / mr 197 → 目标 170–205）。
  保留全部关键信息：`four-editor` / **先体检再路由**（diagnose first, then routes it）/
  四条工序（untangle · talkable pages · one-page dashboard · machine tone last）/ `every edit traceable to a rule`。
  **顺带纠正原报告的一处口径误用**：原文写「超出同系列专家包 **239–386** 字区间（如 cine-team 约 386 字）」——
  ① 「239–386」经 YAML 解析 14 个技能包实测确认是**技能包 `SKILL.md` 的 `description`** 口径（min 239 clarify / max 386 errorfix）；
  ② **cine-team 的 `plugin.description` 实测只有 176 字符**，不是 386。专家包的正确参照是 **175–197**。
  本包 502 在两套口径下**都判偏离**，属真缺陷（与 code-scholar 那条「误报」性质不同），故照修。
- **附带修复（系列通病，同 cine-team / code-scholar）**：`README.md`「目录结构」块给 `avatars/`、`skills/` 标上
  `（由构建注入）`，并在块后补**形态说明** —— 写明源包只有哪几个文件、两个目录分别由构建从何处注入、
  以及 `skills/` 复制的是**唯一真源**（本包不存副本）。
- **本轮同时复核通过（未改）**：专家团 6 项专属检查全过 —— `settings.json`/`setting.json` 双文件存在且内容一致并指向主理人、
  `agents[]` ↔ `members[].id` 一一对应（5 个）、主理人文件名带团前缀、`teamInfo` 与实际一致、
  `displayDescription.zh` 46 汉字、`defaultInitPrompt` 逐字等于 `quickPrompts[0]`、`categoryId` 合法。

**验收（真跑；改后 5/5，git 原始版本 3/5）**：

| # | 用例（判据取自包内真源 / 系列实测区间） | 改前（git 原始版本） | 改后 |
|---|---|---|---|
| P1 | `description` 落在兄弟专家包区间 170–205 | ❌ 502 字符 | ✅ 201 |
| P2 | README 目录树含 `avatars`/`skills/` 时必须加形态说明 | ❌ `注入项=['avatars','skills/']；说明=无` | ✅ 说明已加 |
| P3 | `displayDescription.zh` 40–50 汉字（回归） | ✅ 46 | ✅ 未变 |
| P4 | `defaultInitPrompt` 逐字等于 `quickPrompts[0]`（回归） | ✅ | ✅ 未变 |
| P5 | `members[]` 每项恰 5 字段（回归） | ✅ | ✅ 未变 |

**反向验证**：同一套用例对 **git 原始版本**跑出 **3/5**，失败的 2 条精确对应两处修复；
P3/P4/P5 作为阴性对照在原始版本上**照样通过**，说明判据不乱报。
**另有独立的工具侧反向验证**（见上缺陷 1）：新加的 `members[]` 字段数校验对「多字段」「缺字段」两类样本各亮一次红灯，
对源包本体全绿 —— 这是 `selfcheck.py` 自身改动的双向验证，不是橡皮章。

**待办**（缺陷 1、2 已于 2026-09-23 处理，见上）：

- ~~缺陷 1 属校验器侧，建议在仓库 `scripts/selfcheck.py` 加成员字段数检查~~ → **已修**（工具侧），并用本包两个新样本双向验证。
- ~~缺陷 2 若产品接受压缩，把 `description` 收到 ~380 字内~~ → **已修**，实际压到 **201 字符**（按兄弟专家包实测区间 170–205，而非原报告的 239–386）。
- 下次优先补未覆盖项 2、3：跑一次 `pnpm build joy2know-polish-team`，在暂存目录复核内嵌副本无漂移、zip 第一层与体积。
- **给 `docs/平台资产规范.md` 的后续建议**：把「239–386」明确标注为**技能包**口径，并补专家包口径
  （`plugin.description` en 170–205、`displayDescription.en` 210–230）—— 否则同一误用会在下一个专家包重现（本轮已在 code-scholar 与 polish-team 各撞一次）。

---

## 七、检测履历

| 日期 | 版本 | 状态 | 摘要（本轮测了什么、改了什么） |
|---|---|---|---|
| 2026-09-23 | 1.1.0 | ⚠️ 有条件通过 | 首次成文（覆写骨架）。字段自检 **22 通过 / 0 未通过**（源目录另有 6 条预期提示）；逐张实测 6 张头像规格（团队图标 + 5 角色，全 512²/≤500KB 合规）；专家团 6 项专属检查（双文件/一一对应/前缀/5 字段/teamInfo/三处顺序一致）全过；门 2 把「内嵌技能构建后副本一致性」标部分并进未覆盖；门 3 合理性全绿（仅 description 502 字偏离系列区间）。**6 组反向验证：5 组被抓 + 1 组（多加字段）暴露校验器盲区**（已记缺陷 1）。发现 2 处轻缺陷（校验器不校验成员字段数、description 偏长）+ 6 项未覆盖。**未改包内任何文件，源包无 `__pycache__`。** |
| 2026-09-23 | 1.2.0 | ⚠️ 有条件通过 | **修复轮**：缺陷 1（工具侧）→ `scripts/selfcheck.py` 新增「`members[]` 字段集合须恰为 5 字段」校验，用「多出 extra_field」「缺少 role」两个样本双向验证（各亮红灯，源包本体全绿）。缺陷 2 → `description` 502 → 201 字符（按兄弟专家包实测 175–197 区间，非原报告误用的技能包口径 239–386）；并更正「cine-team 约 386 字」这一错误参照。附带修 README 目录结构形态说明（系列通病）。验收：**真跑 5/5，同一套用例对 git 原始版本 3/5**（失败 2 条对应两处修复；P3/P4/P5 阴性对照两侧均通过）。 |
