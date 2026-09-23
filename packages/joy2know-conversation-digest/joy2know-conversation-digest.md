# 发布前检测报告 · 晓得·对话归纳（joy2know-conversation-digest）

> **本文件是开发期文档，不进 zip**（构建时自动排除）；但**要进 git**。
> 规范见仓库根 `AGENT.md` 第 3–4 节。**下次检测先读本文件**，只重测有变化的部分与「未覆盖项」。
>
> **口径说明**：每条结论对应一次**真实运行**（命令 + 样本 + 输出要点）。
> 脚本实测跑在 `/tmp/j2k-check/conversation-digest/` 的副本上（`packages/` 内不留 `__pycache__`）；
> `--list` / `--workspace` 涉及 `~/.workbuddy/projects` 的部分，用**独立 `HOME` + 合成 jsonl** 验证，
> **全程未读取真实用户的 `~/.workbuddy/projects` 数据**（隐私纪律）。

- **对应版本**：1.2.0
- **检测状态**：⚠️ 有条件通过
- **最后检测**：2026-09-23
- **检测方式**：功能测试 + 完整性对照 + 合理性检查 + 反向验证

---

## 一、包内文件（从磁盘枚举，不手写）

```
     15921  SKILL.md                          技能正文（9 必填 frontmatter 齐全，version 1.1.0）
     14261  scripts/extract_flow.py           唯一入口：--list / --project / --workspace 提取
      5306  references/storage-schema.md     存储结构、记录字段、解析坑（配置，给 AI 读）
      4750  references/deliverable-spec.md    交付文档骨架/视觉/校验（配置，给 AI 读）
      4521  joy2know-conversation-digest.md   本文件（开发期文档，不进 zip）
```

**零第三方依赖核对**：`extract_flow.py` 只 `import argparse / collections / datetime / glob / json / os / re / sys`
（全标准库），无任何第三方包；不联网、不写回 `~/.workbuddy`。SKILL.md 未显式声明「零第三方依赖」，
但实现确实守住（门 3 亦核）。包体（不含本报告）约 **42 KB**，远低于技能包 3 MB 上限。

---

## 二、能力清单与验证结果

样本构造：按 `storage-schema.md` 描述，**自造**小规模但结构真实的 `.jsonl`（多轮 user/assistant、
`function_call` 写文件、`reasoning`、`ai-title`、中文与英文混排、`deploy.sh` 长行、`继续` 辅助轮、空行、
重复注入的相同 prompt、非法 JSON 行、缺字段、非法 UTF-8 字节）。全部落在 `/tmp/j2k-check/data/` 与隔离 `HOME`，
未碰真实数据。

| 能力 / 待验证项 | 验证方式（命令与样本） | 结果 | 证据要点 |
|---|---|---|---|
| 入口可达、`--help` 一致 | `extract_flow.py --help` | ✅ 通过 | 列 `--list/--workspace/--project/--out/--sessions/--preview` |
| 主流程：产四类文件 | `--project <dir> --out /tmp/flow` | ✅ 通过 | 写出 `manifest.json` `users.md` `answers.md` `products.txt` 四样齐全 |
| 提问剥 `<user_query>` 壳 + 去重 + 剔辅助轮 | 同上，核 `raw/dedup/effective` | ✅ 通过 | 会话 A：原始 **4** → 去重 **3** → 实质 **2**（重复 prompt 去重、`继续` 作 aux 剔除，与 §5.2 口径一致） |
| 回答提取（`output_text`/`text`） | 会话 A assistant 用 `output_text` | ✅ 通过 | `answer_blocks=1`；`--preview 0` 时 `len=539` 不截断 |
| 产物识别 `function_call` + 保序去重 + 次数 + 操作类型 | 会话 A 调 Write 后 Edit 同文件 | ✅ 通过 | `deploy.sh`：`calls=2 ops=[Edit,Write]`，首现顺序保序 |
| `--list` 列空间与对话 | 隔离 `HOME` + `workspace-display-names.json` | ✅ 通过 | 输出「显示名→路径→id→时间→提问 N→产物 N→KB」 |
| `--workspace` 映射 + 多目录合并 | 造同前缀两 project 目录 | ✅ 通过 | 报「对应 2 个会话目录，将合并」；`session_count=4`、`project_dirs` 含两份 |
| 边界：空文件（0 字节） | `--project <含 empty.jsonl>` | ✅ 通过 | `实质提问 0｜唯一产物 0`，EXIT 0，不崩 |
| 边界：仅 1 条消息 | 会话 B | ✅ 通过 | 正常出 1 条提问、0 产物 |
| 边界：`--sessions` 过滤 | `--sessions aaaa1111` | ✅ 通过 | 仅 1 个对话 |
| 边界：`--preview 0` 不截断 | 同上 | ✅ 通过 | `len=539`（全量） |
| 边界：目录不存在（反向） | `--project /tmp/j2k-check/nope-dir` | ✅ 通过 | `目录不存在：…`，EXIT 1 |
| 边界：`--workspace` 映射不到 | `--workspace <不存在空间>` | ✅ 通过 | `找不到与空间对应的会话目录…先跑 --list`，EXIT 1 |
| 边界：project 目录无 jsonl | `--project <空目录>` | ✅ 通过 | `未找到 .jsonl 文件…`，EXIT 1 |
| 边界：非法 JSON 行 | 会话 C 混 `{bad}` 行 | ✅ 通过 | 坏行被跳过不崩；合法行仍解析（C 得 1 产物） |
| 边界：缺字段 `function_call` | 会话 C 的 Write 无 timestamp/cwd | ✅ 通过 | 仍按 `arguments.file_path` 识别 `ok.md` |
| 边界：非法 UTF-8 字节 | 含 `\xff\xfe` 的 jsonl | ✅ 通过 | `errors="replace"` 打开，EXIT 0 不崩 |
| 降级：缺 `workspace-display-names.json` | 隔离 `HOME` 删该文件再 `--list` | ✅ 通过 | 显示名退化为「（无显示名）」，其余正常，EXIT 0 |
| 降级：缺 `workbuddy.db` | 全程未建 db 仍 `--list` 通 | ✅ 通过 | `--list` 根本不打开 db（见门 2「部分」项） |
| frontmatter 9 必填 + 引用落地 + 无凭证 | `selfcheck.py packages/joy2know-conversation-digest` | ✅ 通过 | 通过 8 项 / 0 未通过；两条 `@references/*` 有效；无硬编码凭证 |

---

## 三、门 2 · 完整性对照（文档承诺 → 实现）

| 文档承诺（摘原文） | 实现位置 | 有 / 无 / 部分 | 备注 |
|---|---|---|---|
| 「`extract_flow.py --list`：每个空间的显示名 → 真实路径 → 对话 ID / 时间范围 / 提问条数」 | `cmd_list()` | **有** | 实测输出四要素齐全 |
| 「`--workspace` 自动映射到对应的 project 目录」 | `resolve_project`→`project_dirs_for_workspace` | **有** | 同前缀多目录合并已实测 |
| 「产出四类文件：`manifest.json` / `users.md` / `answers.md` / `products.txt`」 | `main()` 写盘 | **有** | 四样齐全，已核对 |
| 「空间显示名 → `workspace-display-names.json` 取 `workspaces.<path>.displayName`」 | `load_workspace_names()` | **有** | 实测显示名正确解析 |
| 「工具调用是 `function_call`，不是 `tool_call`」 | 仅匹配 `type=="function_call"` | **有** | 产物只来自 function_call |
| 「提问 `message&&role==user` → `content[].input_text` → 剥 `<user_query>` 壳」 | `extract()` + `strip_user_context` | **有** | 实测剥壳后计数正确 |
| 「回答 `output_text`（也可能是 `text`）」 | `extract()` assistant 分支 | **有** | `output_text`/`text` 均识别 |
| 「产物识别 `name in (Write,Edit,MultiEdit,CreateFile)` + `file_path or path`」 | `extract()` function_call 分支 | **有** | 实测 deploy.sh 归属正确 |
| 「提问计数三层：原始 / 去重 / 实质（剔辅助轮）」 | `raw_user_count`/`dedup_user_count`/`effective_user_count` | **有** | manifest 三字段齐全，与 §5.2 口径一致 |
| 「产物首次出现顺序去重 + 次数 + 操作类型」 | `prod_order`/`prod_count`/`prod_ops` | **有** | `calls=2 ops=[Edit,Write]` |
| 「路径映射：`/` 全换成 `-`」 | `project_dirs_for_workspace` 的 `dashes` | **有** | `/Users/you/Desktop/myproj`→`Users-you-Desktop-myproj` 命中 |
| §4.1「空间包含哪些会话 → `workbuddy.db` → 表 `sessions` → 字段 `cwd`」 | **无脚本实现**：`--list`/`--workspace` 均从 **jsonl 记录的 `cwd` 字段**分组，**从未打开 `workbuddy.db`** | **部分** | 功能等价（都按 `cwd` 分组），但文档把来源归因给 db，实现根本不读 db → 见六·未覆盖项 3 |
| `references/deliverable-spec.md` 六节骨架 / HTML 视觉 / 三层校验 | 脚本**不产出交付文档**，由 AI 在对话层完成 | **部分** | 脚本职责外的 AI 行为，无法用脚本验证 → 见六·未覆盖项 2 |
| §九 降级「记录缺失或损坏时如实说明哪几个对话读不到」 | 坏行/缺字段被跳过（不崩），但**无显式「读不到」提示** | **部分** | `cmd_list` 全空时报「没找到任何 .jsonl」，单行损坏静默跳过 → 见六·观察 1 |

---

## 四、门 3 · 合理性结论

- **规则是否自洽**：✅ 无互相打架。§4.4「产物只认 `function_call`」与 §六.1「产物归属只认记录不认叙述」同一取向；
  §5.2 三层计数口径与脚本 `raw/dedup/effective` 字段逐项对应；`function_call`≠`tool_call` 在 SKILL 与脚本一致。
- **推断是否标注为推断**：✅ 本脚本不做启发式猜测——`cwd` 直接取自记录、计数来自去重逻辑，无任何「推断值」混入输出。
  `workspace_display_name` 缺失时显式落 `null`（不是补默认值），符合「值来源可追溯」。
- **错误提示是否可指导下一步**：✅ 目录不存在点名路径；project 空目录 / workspace 映射不到都提示「先跑 `--list` 看看有哪些空间」；
  均为「发生了什么 + 怎么办」。
- **边界是否优雅**：✅ 空文件 / 单条 / 坏 JSON 行 / 非法 UTF-8 / 缺字段均不崩不静默退出；
  坏路径场景 EXIT 1 且给提示。唯一观察：坏 `arguments` 的 `function_call` 被静默丢弃（无警告）→ 见六·观察 1。
- **零依赖是否守住**：✅ `import` 仅标准库，无第三方包；不联网、不写 `~/.workbuddy`。
- **值来源是否可追溯**：✅ 产物路径来自真实的 `function_call` 调用（功能真实来源），计数来自记录；无编造值。
  时间来自 `timestamp`（毫秒）经 `fromtimestamp(ts/1000)`，与 storage-schema「时间戳是毫秒」一致。

---

## 五、门 4 · 测试真实性自评（防放水）

- [x] 1. 只跑 happy path，没跑边界 —— **否**：11 组边界（空文件/单条/过滤/预览/四目录类报错/非法JSON行/缺字段/编码异常）
- [x] 2. 只看「没报错」，没核对输出内容 —— **否**：逐条核对 `raw/dedup/effective` 三层计数、`ops` 顺序、`answer_blocks`、`session_count`、多目录合并
- [x] 3. 把「文档写了」当成「已验证」 —— **否**：门 2 把「`workbuddy.db` 来源」「deliverable-spec 六节」标成「部分」并进未覆盖项
- [x] 4. 自造理想样本 —— **否**：样本含重复注入 prompt、`继续` 辅助轮、中英混排、长行、非法 JSON 行、缺字段、非法 UTF-8，贴近真实脏数据形态
- [x] 5. 跳过失败项、不记录 —— **否**：1 处观察 + 6 项未覆盖全部记在第六节
- [x] 6. 修完只测修好的那条，没跑回归 —— **不适用**：本轮不改包内任何文件，主流程全量跑过（无「修」）
- [x] 7. 造错样本只造了会被抓的那种 —— **否**：4 组反向验证见下，含 selfcheck 与脚本两个层面

**反向验证记录**

| # | 造了什么错样本 | 预期 | 实际 |
|---|---|---|---|
| 1 | 副本 SKILL.md **删掉**必填 `author` 字段 | `selfcheck` 报「缺字段」 | ✅ 报 `[XX] frontmatter 缺字段: author`（EXIT 1） |
| 2 | 再把 `name` 改成 `wrong-name` | 报 name 与目录不一致 | ✅ 报 `name 字段 'wrong-name' 与目录名 'conversation-digest' 不一致`（注：此条 name 不一致是 `/tmp` 副本目录名所致，真实包目录为 `joy2know-conversation-digest` 已核对一致） |
| 3 | `--project` 指向不存在目录 | 应报错非静默 | ✅ `目录不存在：…` EXIT 1 |
| 4 | `function_call` 的 `arguments` 为非法 JSON | 不应计入产物、不崩 | ✅ `写文件调用 0`，产物清单显「无写文件记录」，EXIT 0（降级非崩溃） |

**一句话回答：本包的核心能力如果坏掉，是哪一步会亮红灯？**
→ 提问/产物计数错、去重失效，会在第二节 `raw/dedup/effective` 与 `products.txt` 出现**取值不符**（不是只报错）；
路径映射错会在 `--workspace` 处亮红灯（多目录合并提示）；selfcheck 缺字段会在 `[XX] frontmatter 缺字段` 亮红灯（已反向验证）。
**唯一不会亮红灯的盲区**：坏 `arguments` 的 `function_call` 被静默丢弃（观察 1）—— 用户可能漏看一次真实写文件。

---

## 六、未覆盖项 / 已知缺陷 / 待办

**未覆盖项**（下次检测优先消掉这些）：

1. **真实 `~/.workbuddy/projects` 数据未读**（隐私纪律）：`--list` / `--project` 对真实会话目录的端到端表现未实测，
   仅用隔离 `HOME` + 合成 jsonl 验证逻辑正确性。真实的 `workbuddy.db` / `workspace-display-names.json` 协同未碰。
2. **`deliverable-spec.md` 是 AI 对话层行为**：六节骨架、HTML 视觉系统、三层英文引用、HTML 标签平衡校验、md5/`diff -r` 归档校验，
   脚本均不产出，属 AI 在对话里完成 —— 未跑过一次真实端到端归纳对话。
3. ~~**`workbuddy.db` 路径未实测且脚本根本不读它**~~ **【已消 2026-09-23】**：已按「改文档」对齐 —— SKILL §4.1 与开头数据源句改为如实描述（读 jsonl 的 `cwd` 分组、不打开 db），storage-schema 加注。**db 本身仍未实测（脚本不读它，属设计如此）**，如需交叉核对功能再单独测。
4. **大规模/多空间会话未测**：样本 3–4 个对话、KB 级；未测几十对话、大 jsonl 下的耗时与 `manifest.json` 体积。
5. **`pnpm build` 未跑**（纪律禁止 AI 执行）：构建期暂存目录上的 `selfcheck` 与体积校验未实测。
6. **`description`「不适用于」边界未实测**：非 WorkBuddy 对话（ChatGPT/微信/录音/PDF 文本等）的拦截属触发层，本地无触发环境。

**已知缺陷 / 观察**（**消解情况见本节末「修复记录」**）：

- **【已修 2026-09-23】** **观察 1（轻）· 坏 `arguments` 的 `function_call` 被静默丢弃**：`extract()` 里 `json.loads(arguments)` 失败时 `args={}`，
  该写文件调用不计入 `products`，且**无任何 stderr 警告**（storage-schema 坑 #7 只覆盖「整行坏 JSON」，未覆盖「行合法但 arguments 坏」）。
  属防御性降级、不崩，但可能让用户漏看一次真实写文件。建议：`arguments` 解析失败时记一条 `警告：以下写文件调用参数无法解析，已跳过：<name>`。
  非硬缺陷，不影响正常路径。

> **严重度判定说明**：以上均为非硬缺陷 / 文档偏差，正常路径全绿、包可上传 —— 故判 `⚠️ 有条件通过`。
> 若维护者认为「观察 1 的静默丢弃」或「未覆盖项 3 的 db 归因偏差」属硬缺陷，应改判 `❌` 并优先修。

**【已修 2026-09-23 · 版本 1.1.0 → 1.2.0】修法与验收**：

- **观察 1 已修（R1 留痕）**：`extract()` 在 `json.loads(arguments)` 失败时不再静默吞掉，改为把该调用记入 `skipped_writes`
  （含工具名、时间戳、原因、原始串前 120 字）；`manifest.json` 每会话新增 `skipped_writes`、顶层新增 `totals.skipped_writes`
  与 `bad_lines`；`main()` 与 `--list` 收尾时在 **stderr 打警告并写明影响**（「这些写文件动作不会出现在 products.txt 里，
  产物清单可能少项」），`--list` 另在对应对话行尾标 `⚠跳过写文件 N`。
  同时把 `iter_records` 静默跳过的**坏行**也按「文件 + 行号」去重计数（多遍读取不会重复计数），进 `bad_lines` 并报警 ——
  原文 `storage-schema` 坑 #7 只覆盖「整行坏 JSON」，本次让它从「文档里写了」变成「真的会报」。
- **未覆盖项 3 已消（文档归因对齐，选「改文档」而非「补 db 读取」）**：功能等价的前提下，改动更小、风险更低。
  `SKILL.md` §4.1 与开头「数据源」句改为**如实描述脚本行为**（读 jsonl 记录里的 `cwd` 分组，**不打开 `workbuddy.db`**），
  并注明客户端界面另用 `sessions.cwd` 分组、db 可作交叉核对；`references/storage-schema.md` 的 `sessions` 表加一条
  「**`scripts/extract_flow.py` 不读这张表**」的注，避免后来者再照文档误判。

**验收（真跑；改后 22/22，git 原始版本 11/22）**：

| # | 用例 | 改前（git 原始版本实测） | 改后 |
|---|---|---|---|
| C1 | 干净会话（`--sessions aaaa0001`，阴性对照） | ✅ 无警告 | ✅ 无警告（`skipped_writes=[]`、`bad_lines=0`） |
| C2 | 脏会话（1 行坏 JSON + 1 条 `arguments` 坏） | ❌ **`stderr=''` 完全静默**；manifest 无 `skipped_writes`/`bad_lines` | ✅ 两条警告齐全；`skipped_writes` 精确记 1 条含原因；`bad_lines≥1` |
| C2b | 警告所言是否属实 | — | ✅ 被丢弃的 `BROKEN-but-real.html` **确实**不在 `products.txt`；正常的 `dashboard.html`/`deck.md` 仍在 |
| C3 | `--list` | ❌ 无警告、无标记 | ✅ stderr 警告 + 行尾 `⚠跳过写文件` |
| C4 | `--workspace` 路径解析（回归） | ✅ | ✅ 未变 |
| C5 | 提问去重/剥壳/产物合并计数（回归） | ✅ | ✅ 逐项未变 |

**反向验证**：同一套用例对 **git 原始版本**跑出 **11/22**，失败的 11 条全部落在「留痕」与「归因」两处修复
（`skipped_writes` 缺失、`bad_lines=None`、`stderr=''`、无 ⚠ 标记）；C1/C3 退出码/C4/C5 计数等回归项在原始版本上**照样通过**
—— 用例抓得住缺陷、也不乱报。测试全程使用**自造假 HOME 与合成 jsonl**，未读写真实 `~/.workbuddy`。

**补充修复 2026-09-23 · 系列级扫描新发现（R4）**：

- §七「按需知识」原先只列了两条 references 文件名，**未点名任何「必做类」章节**。
  仓库新增的跨包审计脚本 `scripts/series_audit.py`【A】段把它扫了出来（与 db 归因那处同批）。
  已按 **R4** 拆成四条，点名：`deliverable-spec.md` **§三「写完必做的两道校验」—— 交付前必跑**、
  `storage-schema.md` **§四「坑清单（按踩坑频率排序）」—— 写解析逻辑前必读**；
  其余章节（`storage-schema` §一~§三/§五、`deliverable-spec` §一/§二/§四）列为参考类。
  **这处不是文档好不好看的问题**：本仓库的 SKILL「文档」是给模型读的程序，路由没点到「必跑」章节，
  模型就不会去跑那两道校验 —— 属会改变行为的功能缺口。审计【A】段对本品**已清空**。
  版本沿用 1.2.0（与本轮其余修复同批，不另起一版）。

**待办**（观察 1 与未覆盖项 3、以及本轮 R4 补章均已于 2026-09-23 处理，见上）：

- ~~优先补观察 1 的 stderr 警告；顺手把 §4.1 的 db 归因偏差在 SKILL 与 storage-schema 对齐。~~ → **已完成**。
- 下次检测先补未覆盖项 1、2、4（用真实/更大样本跑 `--list` 与一次端到端归纳）。
- 修完必须跑回归：本报告第二节全部用例重跑一遍，并对观察 1 补一组反向验证（造 `arguments` 坏的 `function_call`，确认新警告真的出现）。

---

## 七、检测履历

| 日期 | 版本 | 状态 | 摘要（本轮测了什么、改了什么） |
|---|---|---|---|
| 2026-09-23 | 1.1.0 | ⚠️ 有条件通过 | 首次成文（覆写骨架）。`selfcheck.py` 8 通过 / 0 未通过。在 `/tmp` 副本真跑 `extract_flow.py`：主流程四类产物齐全；提问三层计数（A：原始4→去重3→实质2）、回答提取、产物保序去重（deploy.sh calls=2 ops=[Edit,Write]）均核对正确；11 组边界（空文件/单条/过滤/预览/四目录类报错/非法JSON行/缺字段/编码异常）+ 2 条降级（缺 names 文件、缺 db）+ `--workspace` 多目录合并（4 会话）实测；4 组反向验证（删 frontmatter 字段、坏 name、目录不存在、坏 arguments）。发现 1 处轻观察（坏 arguments 静默丢弃）+ 1 处文档归因偏差（§4.1 db 来源 vs 实现用 jsonl cwd）+ 6 项未覆盖（含真实数据未读、deliverable-spec AI 行为未实测）。**未改包内任何文件。** |
| 2026-09-23 | 1.2.0 | ⚠️ 有条件通过 | **修复轮**：观察 1 → `extract()` 记录 `skipped_writes`（含原因与原始串），manifest 加 `skipped_writes`/`totals.skipped_writes`/`bad_lines`，`main()` 与 `--list` 在 stderr 报警并写明影响、`--list` 行尾标 `⚠跳过写文件 N`；`iter_records` 的坏行按「文件+行号」去重计数。未覆盖项 3 → 按「改文档」对齐 §4.1 数据来源（jsonl `cwd` 分组、不读 db），storage-schema 加注。验收：**真跑 22/22，同一套用例对 git 原始版本 11/22**（失败 11 条全为留痕/归因项；C1/C4/C5 等回归项两侧均通过）。全程用假 HOME，未碰真实数据。 |
| 2026-09-23 | 1.2.0 | ⚠️ 有条件通过 | **同批补修（系列级扫描新发现 · R4）**：§七 路由原未点名任何必做类章节 → 拆四条，点名 `deliverable-spec.md` §三（交付前必跑的校验）与 `storage-schema.md` §四（坑清单，写解析逻辑前必读），其余列参考类。`series_audit.py`【A】段对本品已清空。版本与之同批，不另起一版。 |
