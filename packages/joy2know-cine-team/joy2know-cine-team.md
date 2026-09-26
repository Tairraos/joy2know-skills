# 发布前检测报告 · 晓得·AI 视频生产团队（joy2know-cine-team）

> **本文件是开发期文档，不进 zip**（构建时自动排除）；但**要进 git**。
> 规范见仓库根 `AGENT.md` 第 3–4 节。**下次检测先读本文件**，只重测有变化的部分与「未覆盖项」。
>
> **口径说明**：本报告每条结论对应一次**真实运行**（命令 + 样本 + 输出要点）。
> 反向验证的错样本跑在 `/tmp/j2k-check/cine-team/` 的副本上（`packages/` 内不留 `__pycache__`）。
> **注意**：该临时目录必须同时放一份 `avatars/`（本仓库真源），否则会因找不到
> `avatars/joy2know-cine-team.png` 报一条**假红灯** —— 见第四节的踩坑记录。
>
> **本轮（v1.5.0）为「内嵌联动升级轮」**：本包内嵌 `joy2know-musician`，
> 该技能本轮把 Suno v6 世代的**实测控件现状**（免费档只可选 `v6-mini`、`Variety` 默认 Normal
> 且**会改写 Style**）写进了正文与校验脚本。按本仓库的**内嵌联动铁律**，本包必须同轮跟进 ——
> 本轮实际改动 **3 处**：① `agents/cine-music.md` **正文口径同步**（这是「两层过期」的
> 第 ② 层，最容易漏且自检查不到）；② `plugin.json` 版本；③ 包内 `README.md` 版本行。
> 全部经过**产物内逐字节核对**（见第二节「构建暂存形态」一行的实测证据）。

- **包名**：joy2know-cine-team
- **类型**：专家团（`expertType: "team"`，1 主理人 + 6 成员）
- **对应版本**：1.5.0
- **检测状态**：⚠️ 有条件通过
- **最后检测**：2026-09-26（同日随内嵌技能 `joy2know-musician` 的描述修正**同轮重建**，包内文本一字未动）
- **检测方式**：功能测试 + 完整性对照 + 合理性检查 + 反向验证 + 上传预检

---

## 一、包内文件（从磁盘枚举，不手写）

```
    4482  .codebuddy-plugin/plugin.json   配置（expertType: team，7 agents / 3 内嵌技能 / 7 members）
    2976  README.md                        包说明（团队构成、工作流程、内置技能、适用边界）
      36  settings.json                    主理人声明 {"agent": "joy2know-cine-lead"}（平台校验器实查这个名）
      36  setting.json                     同上（沿用官方模板名，兼容保留）
     245  skills.json                       内嵌技能声明（构建时从 packages/<名>/ 复制真源）
    8922  agents/joy2know-cine-lead.md      主理人·雷导（SOP 编排，含「严禁行为」可观测判定）
    3217  agents/cine-narrative.md          编导·诺拉
    3736  agents/cine-shot.md               分镜师·尚恩
    4522  agents/cine-prompt.md             提示词工程师·珀西
    5306  agents/cine-consistency.md        一致性管理员·柯拉
    3885  agents/cine-post.md               后期顾问·奥托
    9974  agents/cine-music.md              音乐人·小音（1.5.0 轮：同步「More Options + Variety 归 0 + 第 4 段设置块」）
    38736  joy2know-cine-team.md             本文件（开发期文档，不进 zip）
```

**零第三方依赖核对**：本包无 `scripts/`、无任何可执行代码与网络调用。
源包体（不含本报告）**47,337 字节 ≈ 46.2 KB**；发布后 zip 另含构建注入的 8 张头像与 3 个内嵌技能。
**1.5.0 轮已实测产物**：`dist/joy2know-cine-team-v1.5.0.zip` = **4286.7 KB**（专家团上限 20 MB，余量充足），
第一层为 `joy2know-cine-team/`，内嵌 `joy2know-musician` 读到 **1.5.0**，
且内嵌的 `references/model-and-controls.md` 与 `scripts/suno_check.py` **与源包逐字节一致**（见第 2.4 节）。

**头像规格（8 张，已逐一实测）**：团队图标 + 7 名成员头像全部 **512×512、377–410 KB**，
均 ≤500 KB 且 ≈512² 方图，**8/8 合规**。

---

## 二、能力清单与验证结果

| 能力 / 待验证项 | 验证方式（命令与样本） | 结果 | 证据要点 |
|---|---|---|---|
| plugin.json 15 字段齐全 + JSON 可解析 | `$V/bin/python scripts/selfcheck.py packages/joy2know-cine-team` | ✅ 通过 | **1.5.0 轮复跑：通过 35 项 / 0 未通过**（对源目录跑，另有 5 条**提示**：内嵌技能与头像「构建时才注入」、zip 未生成）。<br>⚠️ **本行数字在 1.4.0 轮修正过一次**：初稿沿抄了 1.1.0 时代的「26 项」（校验器在 1.3.0 轮扩过判据、已变 35 项）—— 属**照抄旧结论**，真跑后改正；1.5.0 轮复跑确认仍是 35 项 |
| 官方硬约束：`displayDescription.zh` 40–50 汉字 | 同上 | ✅ 通过 | 实测 **48 汉字**（脚本判定落在 40–50 内；注意该检查**只管 zh，不管 en**，见「四」与第五节盲区说明） |
| 官方硬约束：`defaultInitPrompt` == `quickPrompts[0]` | 同上 | ✅ 通过 | 两版（zh/en）逐字相同 |
| 官方硬约束：`tags` / `quickPrompts` 各 3 个 | 同上 | ✅ 通过 | 各 3 |
| `categoryId` 在官方 15 类白名单内 | 同上 | ✅ 通过 | `06-ContentCreative`（专家与专家团共用同一份分类清单） |
| 专家团专属：`settings.json` 与 `setting.json` **两个名字都在**且内容一致 | 同上 | ✅ 通过 | 两份均为 `{"agent": "joy2know-cine-lead"}`，`json.dumps` 比对完全相同 |
| 专家团专属：两份文件声明的 `agent` == 主理人 | 同上 | ✅ 通过 | 均等于 `teamInfo.leadAgent` = `agentName` = `joy2know-cine-lead` |
| `agents[]` 7 条路径全部存在 | 同上 | ✅ 通过 | 7/7 存在 |
| **`agents/*.md` 的 `name` 与 `agentName` / `members[].id` 严格对应** | 同上 | ✅ 通过 | 主理人 1 个 `name == agentName`；其余 6 个全部命中 `members[].id`（`cine-narrative`/`cine-shot`/`cine-prompt`/`cine-consistency`/`cine-post`/`cine-music`）—— **一一对应，无多无少** |
| `teamInfo.memberAgents` 与 `members[]`（除主理人）是否一致 | 人工逐条比对 + `agents[]` 文件名去 `.md` | ✅ 通过 | `memberAgents` 6 条 == `members[]` 中 6 个非 lead 项的 `id` == `agents/` 6 个成员文件名，三者同序同集合 |
| 主理人文件名带团前缀 | 文件枚举 | ✅ 通过 | `joy2know-cine-lead.md`（非 `cine-lead.md`），与规则一致 |
| 头像路径与规格 | `sips -g pixelWidth -g pixelHeight` + `wc -c`，8 张 | ✅ 通过 | 512×512 / 377–410 KB，8/8 合规；`avatar` 字段为 `avatars/team.png`（`avatars/` 前缀 ✓） |
| 图标台账（全仓 30 张） | `python3 scripts/placeholders.py --check` | ✅ 通过 | 「缺 0 · 仍是占位图 0 · 已换成真图 30」 |
| 包内无硬编码凭证 | selfcheck `[sec]` 项 | ✅ 通过 | 未发现疑似凭证 |
| 反向验证：10 组「应该被抓」的错样本 | 见第五节 | ✅ 通过 | **10/10 全部被抓**，且每组只亮**对应那一条**（未误伤其它检查项） |
| 团队成员的实际协作行为（建团队 / 调度 / 中转 / 不代写） | — | 未覆盖 | 需真实运行团队，见第六节 |
| 构建暂存形态（注入 `skills/` 与 `avatars/` 后） | `build.mjs joy2know-cine-team` + 解包实测 | ✅ 通过（1.5.0 轮复测） | zip **4286.7 KB**；第一层仅 `joy2know-cine-team/`；`settings.json`+`setting.json` 均在；内嵌 `musician` 读到 **`version: 1.5.0`**；且**内嵌 `references/model-and-controls.md` 与 `scripts/suno_check.py` 均与源包 `diff` 逐字节一致**（本轮三处改动里最容易被「构建读实时源、清单显示新版」掩盖的一环，实测排除） |
| 成员文件 ↔ 被内嵌技能真源的口径一致 | `crosscheck.py`（读技能 `SKILL.md` / 脚本 `--help` / 包内 json） | ⚠️ **连续第二轮降级为手工核对** | 1.3.0 轮 22/22（改前 13/22）；**1.4.0 轮脚本已随 `/tmp` 清理消失、未入库，无法重跑** —— 1.4.0 与 1.5.0 两轮只能逐条手工比对。1.5.0 轮比对四处：「人声锁三处」「**More Options 位置 + Exclude 可能缺席**」「必留段落」「版本号 1.5.0」，结论一致；**待办升级为 P1：校验器必须入库**（连着两轮替它手工兜底，说明它不是一次性工具） |
| 上传预检：产物走哪个上传入口 | `platformcheck.py --zip dist/joy2know-cine-team-v1.5.0.zip` | ✅ 通过（1.4.0 轮新增，1.5.0 轮复跑） | 按 **Expert** 类型上传通过；预检同时报出按 **Skill** 上传会失败（超 3 MB + 缺根级 `SKILL.md`）、按 **BuddyApp** 上传会因 `file_too_large`（上限 3 MB）失败 —— **这正是历史上真实踩过的「入口选错」坑**，现在上传前就能判出来 |

**复现命令**

```bash
V=~/.workbuddy/binaries/python/envs/default
$V/bin/python scripts/selfcheck.py packages/joy2know-cine-team        # 正式结果（源目录，5 条提示属预期）
python3 scripts/placeholders.py --check                               # 图标台账
# 反向验证（临时目录必须同时提供 avatars/，否则会多一条假红灯）：
ln -sfn "$PWD/avatars" /tmp/j2k-check/cine-team/avatars
$V/bin/python scripts/selfcheck.py /tmp/j2k-check/cine-team/v1/joy2know-cine-team
# 1.3.0 轮新增：跨文件口径对照（判据全部取自包内/技能真源，不靠人工读）
$V/bin/python /tmp/j2k-check/cine-team-v130/crosscheck.py "$PWD"
$V/bin/python /tmp/j2k-check/cine-team-v130/crosscheck.py "$PWD" --tamper stale-rule|loop-sections|flag
$V/bin/python /tmp/j2k-check/cine-team-v130/crosscheck.py /tmp/j2k-check/cine-team-v130/baseline-repo  # 改前对照
```

### 1.3.0 轮新增验证（跨文件口径对照 · 门 2 的强化）

**背景**：本包的音乐人成员 `agents/cine-music.md` 是 `joy2know-musician` 技能在团队里的「使用说明书」。
技能在 1.3.0 轮修掉了「任何歌都要求三处语言锁」这条**反向指令**（改判为： Style 第一位是「人声锁」，
有人声写语言、无人声声明不唱），并新增纯器乐 / 循环 BGM 路径。**成员文件若不同步，团队会照旧指令人做错事。**
本轮新增 22 条**跨文件对照**判据（`crosscheck.py`），判据源自三份真源：技能 `SKILL.md`、技能校验器
`suno_check.py`、本包 `plugin.json` / `skills.json` / `agents/`，**不写死人工结论**。

| 组 | 判据（22 条） | 结果 |
|---|---|---|
| 旧口径已清除（X1–X5） | 无「任何歌都要语言锁」残留；人声锁按有无声分流；红灯须给出 `--instrumental` 出口且禁止「硬填语言锁消红灯」（X3 是与技能真源的同表述核对） | ✅ 5/5 |
| 循环路径三处口径同一个集合（X6–X10） | 脚本 `REQUIRED_SECTIONS_LOOP` == `{Intro, End}` 且与技能 §十表格、cine-music 的循环例外**三方同集合** | ✅ 5/5 |
| 开关真实存在（X11） | cine-music 引用的每个 `--flag` 都必须在 `suno_check.py --help` 里找得到（**真跑 `--help` 比对**） | ✅ 4/4 全部存在 |
| 循环硬约束同步（X12–X13） | 禁淡出 / 锁死 BPM / 首尾同源 / 不承诺直出 —— 技能四条 + 成员同步 | ✅ 2/2 |
| 偏离留痕制度（X14–X15） | 技能「补全与规则偏离都必须标注」↔ 成员给出同一句式 | ✅ 2/2 |
| 版本与结构（X16–X20） | `plugin.json`=1.3.0、README 版本行=1.3.0、`skills.json` 与 `plugin.json skills[]` 同集合同序、`agents/*.md`↔`members[].id` 一一对应、`teamInfo.memberAgents` 一致 | ✅ 6/6 |

**对照组（改前 / 改后，同一套 22 条）**：改前（git 原始 1.2.0 版 cine-team）**13/22**，
红的 9 条**逐条对应本轮改掉的东西**（旧反向指令、无人声锁、无循环例外、无禁淡出同步、无偏离句式、版本 1.2.0 ×2、无「循环走器乐」的判据）；
未改动的 13 条在**两版都绿**（阴性对照，说明判据不靠版本号蒙对）。

**反向验证（3 组篡改，各只打中对应那一条）**：

| # | 篡改 | 预期 | 实际 |
|---|---|---|---|
| 1 | 把旧反向指令句塞回 cine-music | X1 红 | ✅ 仅 X1 红（21/22） |
| 2 | 把技能 §十「循环必留段 = Intro + End」改回 Chorus/Outro | X7 红 | ✅ 仅 X7 红（21/22） |
| 3 | 把 `suno_check.py` 的 `--loop` 改名 | X11 红 | ✅ 仅 X11 红（21/22） |

**本轮验证方法自身的一次修正（记下来，正是门 4 第 7 条要防的）**：
X7 最初写成 `has(SKILL, "| 必留段落（§三.4）", "| Intro + End |")` —— **两段式字符串匹配，不锚定到具体那一行**。
篡改 2 因此**没能打中**（技能别处还有一行也含 `| Intro + End |`，把它喂绿了）。改为**锚定整行**后，篡改 2 才准确变红。
**教训：断言范围必须等于实测范围**——「文档里有这串字」不等于「这一条规则写对了」。

### 1.5.0 轮新增验证（内嵌联动 · 成员正文口径同步）

**为什么本轮必须动本包**：`joy2know-musician` 升到 1.5.0，而本包 `skills.json` 与 `plugin.json` 都内嵌了它。
按仓库铁律，**升内嵌技能必须查「谁内嵌了它」**，并防**两层过期**：
① 包版本号没抬（构建会重建产物，但清单会显示新版、旧 zip 里其实是旧版 —— 且 **0 告警**）；
② **成员正文复述了被引用技能的规则，技能改了而正文没跟** —— 这一层**自检看不出来**（自检不看正文语义）。

**第 ② 层过期本轮真的发生了**：`agents/cine-music.md` 第 73–76 行仍写着
「官方位置：Custom 模式 → **Advanced Options** → 菜单第一项」，而实测按钮名已是 **More Options**，
且该字段**在免费账号里根本没有**；同时成员正文**全篇没有 Variety** ——
而 Variety 恰恰是唯一会改写 Style 的控件。不同步的后果很具体：
**团队会继续按旧口径，指令人去一个不存在的字段里填负面提示。**

| # | 同步点 | 改前 | 改后 | 真源 |
|---|---|---|---|---|
| S1 | Exclude 位置 | `Advanced Options → 菜单第一项` | `More Options`（Advanced 模式的折叠面板），**并注明可能因档位 / 版本灰度缺席** | 界面实测 2026-09-25 |
| S2 | 降级路径结构 | 单条（就是填 Exclude） | **两条、按可靠性排序**：① 填 Exclude；② 无该字段时简化 Style + 全篇无人声词 + 换更纯器乐的流派 | 承接 S1 的实测 |
| S3 | Variety | **全文未提** | 新增「配套动作（必写）：提醒用户把 `Variety` 归 0」，并附官方原文 | help.suno.com v6 FAQ 原文 |
| S4 | 输出形态 | 三段（标题 / Style / Lyrics）+ 用途建议 | **加第 4 段「粘贴前设置」**（Variety 归 0 必写）+ 免费档三条限制提示 | 承接 S3 |
| S5 | 版本落点 | `plugin.json` 1.4.0；README 版本行 1.4.0 | 两处同升 **1.5.0**（README 版本行正是 1.4.0 轮踩过坑的落点，本轮**先查后改**） | 本轮改动 |

| # | 验什么 | 命令 | 结果 | 证据要点 |
|---|---|---|---|---|
| T1 | 内嵌技能版本真的进了产物 | `unzip -p dist/…v1.5.0.zip joy2know-cine-team/skills/joy2know-musician/SKILL.md \| grep -m1 '^version:'` | ✅ | 输出 `version: 1.5.0` —— 读的是**产物里的副本**，不是源目录 |
| T2 | 内嵌 reference 未漂移 | `unzip -p … references/model-and-controls.md` → 与源文件 `diff` | ✅ | **逐字节一致** |
| T3 | 内嵌脚本未漂移 | `unzip -p … scripts/suno_check.py` → 与源文件 `diff` | ✅ | **逐字节一致** |
| T4 | 成员正文新版真的入包 | `unzip -p … agents/cine-music.md \| grep -c "More Options"` | ✅ | 计数 = 1；**旧包里跑这条会是 0** —— 因此这条判据本身是双相的，不是「有就算过」 |
| T5 | 版本落点无遗漏 | 逐个查 `plugin.json` / `README.md` / `settings.json` / `setting.json` / `skills.json` | ✅ | 版本号只落在 `plugin.json` 与包内 `README.md` 两处，两处都已升 |

**用例集总账（1.5.0 轮）：5/5 同步点 + 5/5 验证项，全绿。**

**本轮新踩的坑（记下来防再犯）**：用检索工具查 `1.4.0` 时，**`.codebuddy-plugin/plugin.json` 没有出现在结果里**
—— 因为该工具**默认跳过隐藏文件与隐藏目录**。差一点据此判定「版本号只落在 README 一处」。
→ **凡查「版本号有哪些落点」，必须显式包含点开头的目录**，并用 `ls -a` 核对目录清单，**不能只信一次检索的结果**。

---

## 三、门 2 · 完整性对照（文档承诺 → 实现）

| 文档承诺（摘原文） | 实现位置 | 有 / 无 / 部分 | 备注 |
|---|---|---|---|
| `plugin.json` description：「a **six-role** AI video production team … a ready-to-paste **Suno** theme song」 | `members[]` 6 个非主理人角色 + `agents/cine-music.md` | **有** | 6 个专业角色齐备，音乐人确实产出 Suno 歌曲包 |
| `displayDescription.zh`：「编导、分镜、提示词、一致性、**音乐**、后期**六角色**协作…」 | `members[]` | **有** | 与 description、lead agent 正文一致 |
| `displayDescription.en`：「**Five** roles … story structure, shot list, model-ready prompts, consistency anchors and post-production notes」 | `members[]`（实为 6 个专业角色） | **部分** | **只列 5 项、漏掉音乐角色**，且与自家 `description` 的「six-role」冲突 → 见第六节缺陷 2 |
| `README.md` 首段：「**五个**专业角色按 SOP 依次产出」 | `members[]` 6 个专业角色 | **部分** | README 停留在加音乐人之前的版本 → 见第六节缺陷 1 |
| `README.md`「团队构成」表 | `members[]` 7 条 | **部分** | 表里**只有 6 行，缺「音乐人 小音」**（`小音`/`Melody` 在 README 中出现 **0** 次） |
| `README.md`「工作流程」Phase 0–6 | `agents/joy2know-cine-lead.md` §四 SOP | **部分** | README 缺 **Phase 4.5（主题曲与配乐）**；lead agent 里是有的 |
| `README.md`「内置技能」两项 | `plugin.json` 的 `skills[]`（3 项） | **部分** | README 只列 storyboard + character，**缺 `joy2know-musician`**；目录结构注释同样写「内置：分镜工 + 角色档案」 |
| `README.md` 目录结构图列出 `avatars/` 与 `skills/` | 构建时注入 | **有**（不是缺陷） | 源包里没有这两个目录是**设计如此**；README 描述的是**发布后的 zip 形态**，与交付物一致 —— 特意记下，免得下次误判 |
| lead agent §三 团队成员表 6 行 | `members[]` 6 个非主理人 | **有** | 逐行与 `plugin.json` 的 id / 名字 / 职业 / 产出物对应 |
| lead agent §四 SOP：Phase 0（含 5 项默认值）→ 1 → 2（与 1 并行）→ 3 → 4 → 4.5（与 4 并行）→ 5 → 6 | 各 `agents/*.md` 职责分工 | **有** | Phase 4.5 明确写了「用户没要歌时跳过，不要自作主张加一首歌」 |
| lead agent §六「不负责实际调用视频生成接口」 | README「适用与不适用」同口径 | **有** | 两处一致，且全包无网络调用路径 |
| lead agent §七 完成判据：必选五份产出 + 可选歌曲包 + 汇编进 `分镜包.md` | §四 Phase 6 的 `分镜包.md` 骨架 | **有** | 骨架七节与 Phase 产出逐节对应 |

**兜底口径两向核对**（文档写了的能力实现里必须有 / 实现里有的文档里必须写）：
正向（plugin.json / lead agent 承诺 → 有实现）全部通过；
**反向（实现里有、README 里没写）发现 3 处**：音乐人成员、Phase 4.5、内嵌技能 `joy2know-musician` ——
这三处全部源于「README 没跟着 v1.1.0 一起更新」，同一根因。

**1.3.0 轮补充的第三向核对（实现 ↔ 被内嵌技能的真源）**：本轮把「成员文件写的东西」与
「`joy2know-musician` 技能真源写的东西」逐条对照（22 条，见第二节），**结论是两处不同步已修好**：

| 成员文件原先的写法（git 原始版） | 技能真源 1.3.0 的写法 | 处理 |
|---|---|---|
| 「**规则 3：语言锁三处齐全**」+「任何一首歌都…」 | Style 第一位是**人声锁**：有人声写语言、无人声声明 `Instrumental, No vocals` 且不写 `[Language:]`/`[Accent:]` | 成员文件改写为同一口径，并补「器乐包硬填语言锁会诱导哼唱」的反例 |
| 只提「歌曲包」，无器乐 / 循环路径 | D / E 路径 + §十 场景配方（循环四条硬约束） | 成员文件补器乐包产出形态、`--instrumental`/`--loop`、循环必留段例外 |
| 无「有意偏离要写明」 | §六 规则 2「补全与规则偏离都必须标注」 | 成员文件的输出纪律补同款句式（例：`偏离规则 3：本段无人声…`） |
| 未提脚本参数 | 校验器新增 `--style` / `--instrumental` / `--loop` | 成员文件规则 5 写全四个参数，并点明 `--style` 不能省（否则器乐声明与 BPM 查不出来） |

**同根因提示**：这三轮（1.1.0 缺音乐人 → 1.2.0 补 README → 1.3.0 对齐技能口径）暴露的是**同一类风险**：
**包内「引用外部技能」的文档，会在被引用技能升级时静默过期**，而现有校验器一条都盯不住。
本轮用 `crosscheck.py` 把它变成了可回归的判据（判据读真源，不写死）。

---

## 四、门 3 · 合理性结论

- **规则是否自洽**：⚠️ **发现一处**（`plugin.json` 内部）：顶层 `description` 说 `six-role`
  并点名 Suno 主题曲，`displayDescription.en` 却说 `Five roles` 且五项里没有音乐 —— 同一份配置里两个口径。
  其余无冲突：主理人「自己不写」与成员职责表互补而非重叠；Phase 2「不能省、不能排在最后」与
  §六「用户只要一份产出时允许跳过无关阶段，但锚点阶段不可跳过」是同一取向（一致地强调锚点必做）。
- **推断是否标注为推断**：不适用（本包不含脚本与数据推断逻辑），但 lead agent §七 要求交付里单列
  「假设与待确认」一节、明确「哪些是按默认值假设的」→ 精神一致。
- **错误提示是否可指导下一步**：不适用（无脚本）。可类比的是 lead agent 的退回机制
  （「发现矛盾时**退回该成员重做**，不要自己动手改」），给了明确下一步。
- **边界是否优雅**：✅ lead agent §六 覆盖三种边界：用户只要部分产出（可跳过无关阶段、锚点不可跳）、
  随机性（要求「首镜先生成 2–3 个候选再定」，不许承诺必成）、版权（提醒授权、不主动写入）；
  §四 Phase 0 另有「禁止连环追问、用户没答就按默认值走并标注假设」。
- **零依赖是否守住**：✅ 结构性成立（无 `scripts/`、无 import、无网络调用）。
- **值来源是否可追溯**：✅ 源包体各文件版本号一致为 **1.5.0**（`plugin.json`、包内 `README.md` 的「## 版本」行）；
  头像真源在仓库根 `avatars/`（构建注入），包内不留副本 —— 单一真源成立。
  （1.4.0 轮实测抓到过一次不一致：`plugin.json` 已升 1.4.0，而 `README.md` 版本行仍停在 `1.3.0 · 作者：晓得乐` ——
  上一轮只改了 `plugin.json`，当时记为本包缺陷 3。1.5.0 轮**先查后改**，两处同步升到 1.5.0，
  并顺带查清「版本号到底有几个落点」= 只有这两处。
  ⚠️ **查的过程中踩到一个坑**：检索工具**默认跳过 `.codebuddy-plugin/` 这类点开头的目录**，
  第一次查 `1.4.0` 时 `plugin.json` 没出现在结果里 —— 险些据此判定「只有 README 一处」。已写入坑记录。）
- **1.3.0 轮复核**：上轮那条 `description` 与 `displayDescription.en` 的口径冲突**已于 1.2.0 轮消除**，
  本轮重扫未见新增冲突。本轮的改动面是「成员文件 ↔ 内嵌技能真源」，**未触碰任何跨成员职责边界**：
  小音仍只出提示词包与插入点建议，转场卡点 / 混音 / 交付规格仍归奥托（Phase 4.5 与 §七 两处同口径）。
  器乐 BGM 的引入**没有制造新的重叠** —— 它落在小音原有职责内（多了一条产出形态），不是新角色。
- **1.4.0 轮复核**：本轮改动面为「`agents/cine-music.md` 补 Exclude 位置 + `plugin.json` 版本 + `README.md` 版本行」，
  同样**未触碰成员职责边界**（Exclude 是「压不住哼唱」降级路径上多一条可操作项，仍属小音的提示词职责）。
  重扫 `description` / `displayDescription.en` / `displayDescription.zh` 三处，**未见新增口径冲突**。
  但**校验强度本轮降级**：上一轮那套 22 条跨文件口径对照（`crosscheck.py`）是一次性工具、未入库，
  `/tmp` 目录已随系统清理消失，本轮**无法原样重跑**，只能降级为手工逐条比对（见第七节 1.4.0 行末尾的如实记录）。
- **1.5.0 轮复核**：本轮改动面为「`agents/cine-music.md` 正文口径同步（Exclude 位置 / 两条降级路径 / Variety 配套动作 /
  输出第 4 段）+ `plugin.json` 版本 + 包内 `README.md` 版本行」，**未触碰任何成员职责边界** ——
  Variety 是「怎么把提示词兑现成生成设置」，Exclude 是「压不住哼唱时的退路」，
  两者都落在小音原有的提示词职责内，没有把奥托的后期活儿（裁切 / 对齐循环点 / 响度）拉进来。
  重扫 `description` / `displayDescription.en` / `displayDescription.zh` 三处，**未见新增口径冲突**。
  **校验强度仍是手工级**：`crosscheck.py` 连续第二轮无法重跑（未入库），
  两轮都为它手工兜底 —— 已把「校验器入库」从待办升为 **P1**：
  **一个需要连着两轮人工替代的检查器，就已经不是一次性工具了。**

**本节额外记录一条踩坑（与包本身无关，与检测方法有关）**：
第一轮反向验证时，基线样本也报了一条 `[XX] [expert] avatar 缺失: avatars/team.png`。
排查后确认是**我的样本环境缺 `avatars/`**：`selfcheck.py` 对源目录跑时会回落到
`<父目录>/avatars/<包名>.png` 找真源，临时目录没有这一层就报红。在临时目录补一个 `avatars/` 软链后，
基线恢复为 **26 通过 / 0 问题**，10 组错样本各自只亮对应红灯。
**教训：跑反向验证前先让「干净样本」全绿，否则会把环境噪声当成包的缺陷**（这正是门 4 第 4 条要防的
「自造样本比真实产物脏/干净」的反面——样本环境不对，结论一样不可信）。

---

## 五、门 4 · 测试真实性自评（防放水）

- [x] 1. 只跑 happy path，没跑边界 —— **否**：10 组错样本覆盖 10 类不同约束（成员名 / settings 缺失 /
      主理人不符 / 两文件不一致 / 描述字数 / 初始提示词不等 / tags 数量 / 非法分类 / agents 路径 / 头像前缀）
- [x] 2. 只看「没报错 / 退出码 0」，没核对输出内容 —— **否**：逐条核对了报错措辞是否**指向正确的那一项**，
      并确认未误伤其它检查项
- [x] 3. 把「文档写了」当成「已验证」 —— **否**：第三节把 3 处 README 缺口标「部分」并进第六节；
      `agents` 的 `skills:` 字段因无法核实平台支持，明确列入未覆盖
- [x] 4. 自造理想样本（比真实产物干净） —— **部分修正**：首次样本**比真实环境更脏**（缺 avatars），
      已在补全环境后重跑全部样本；最终结论取自修正后的运行
- [x] 5. 跳过失败项、不记录 —— **否**：2 处配置/文档缺陷 + 3 处 README 缺口 + 8 项未覆盖，全部记在第六节
- [x] 6. 修完只测修好的那条，没跑回归 —— **不适用**：本轮不改包内任何文件；补 avatars 后**重跑了基线 + 全部 10 组**，
      不是只重跑报错那组
- [x] 7. 造错样本只造了会被抓的那种 —— **否**：主动造了三类**平台真会打回**的样本
      （非法 `categoryId`、缺 `settings.json`、`defaultInitPrompt` 与 `quickPrompts[0]` 不等），这三条正是历史上真实踩过的坑

**反向验证记录**

| # | 造了什么错样本 | 预期 | 实际 |
|---|---|---|---|
| 1 | `agents/cine-shot.md` 的 `name` 改成 `cine-wrong` | 报「既非 agentName 也不在 members[].id」 | ✅ 精确报出该条 |
| 2 | 删掉 `settings.json`（只留 `setting.json`） | 报缺 settings.json | ✅ `专家团缺 settings.json（平台查 settings.json，官方模板用 setting.json，两个都要放）` |
| 3 | `settings.json` 的 `agent` 改成 `someone-else` | 报与主理人不一致 | ✅ 同时报出「与主理人不一致」+「两文件内容不一致」两条 |
| 4 | `setting.json` 内容与 `settings.json` 不同 | 报两文件不一致 | ✅ 只报该条，未误伤 agent 声明检查 |
| 5 | `displayDescription.zh` 压到 5 汉字 | 报超出 40–50 | ✅ `汉字 5 字，超出官方要求 40-50` |
| 6 | `defaultInitPrompt` 改成与 `quickPrompts[0]` 不同 | 报二者不一致 | ✅ 报错里**同时打印了两个值**，可直接改 |
| 7 | `tags` 删到 2 个 | 报数量应为 3 | ✅ `tags 数量=2（官方固定 3）` |
| 8 | `categoryId` 改成 `00-ExpertTeam`（历史上误填过的值） | 报不在合法列表 | ✅ `不在合法分类列表中: '00-ExpertTeam'` |
| 9 | `agents[]` 追加一条不存在的路径 | 报路径缺失 | ✅ `agents 路径 缺失: ./agents/does-not-exist.md` |
| 10 | `avatar` 去掉 `avatars/` 前缀 | 报应为 avatars/ 下相对路径 | ✅ 同时报出「前缀不对」与「文件缺失」 |

**一句话回答：本包的核心能力如果坏掉，是哪一步会亮红灯？**
→ 平台解析层（配置字段 / 成员对应 / settings 双文件 / 头像路径）坏了 → `selfcheck.py` 亮红灯，
已用 10 组错样本反向验证（含 3 类历史真实踩过的坑）。
→ **有两处不会亮红灯**：① `displayDescription.en` 与 `description`/`zh` 的口径冲突 ——
自检只校验 zh 的字数，**不校验 en 的内容是否漏角色**；② README 与配置的口径脱节 ——
README 是包内文档，没有任何自动检查盯着它。这两处正是本轮找出缺陷 1、2 的地方。

**1.3.0 轮补充（同一问题的第三面）**：
→ **第三处也不会亮红灯：成员文件与被内嵌技能的口径脱节。** `selfcheck.py` 只查字段与结构，
**完全不看成员文件正文说了什么**。技能升到 1.3.0 后，cine-music 仍写着旧口径，
自检照样全绿（这正是本轮开工时的状态）。本轮补的 `crosscheck.py` 把这一面也纳入可回归判据（22 条）。
→ 本轮的 7 条自查逐条过：① 错样本覆盖 3 类篡改 + 一个完整旧版对照（不是只跑 happy path）；
② 不只核退出码，逐条核了「是哪一条变红、其余是否被误伤」；③ 未把「文档写了」当已验证 ——
判据全部读真源（技能 SKILL.md / 脚本 `--help` / plugin.json / skills.json），不是写死字符串；
④ 样本环境已按上轮教训先备好 `avatars/`，干净样本先全绿；⑤ 全部未覆盖项与 1 处方法学失误都记在案；
⑥ 改后**重跑了全部 22 条 + 3 组篡改 + 改前对照**，不是只重跑改红的那条；
⑦ 造错样本**刻意造了「只改一处」的三种**（塞旧句、只改技能文档不改脚本、只改脚本开关名），
并且**第一次篡改 2 没能打中时没有放过它** —— 追下去发现是判据本身不锚定行（见第二节末）。

---

## 六、未覆盖项 / 已知缺陷 / 待办

**未覆盖项**（下次检测优先消掉这些）：

1. **团队协作行为全未测**：团队创建（「必须且只能由你执行」）、按 SOP 调度成员、消息经主理人中转、
   「禁止代写」的可观测判定（回复里出现一口气写完的多角色内容即违规）—— 这些都只能真跑一次团队才知道，
   本地无团队运行环境。
2. **`agents/*.md` 的 `skills:` 字段是否被平台支持未核实**：4 个 agent 声明了 `skills` 绑定
   （lead: storyboard+character；cine-prompt: storyboard；cine-consistency: character；cine-music: musician）。
   口径合理，但 `docs/平台资产规范.md` 与官方文档未列该字段，**本轮无法核实平台是否解析它**。
3. **Phase 0 的对话行为未测**：「只问一次、每项给默认值、禁止连环追问」属对话层行为。
4. **内外嵌技能联调未测**：本团队生产的分镜包/角色卡，是否能被 `joy2know-storyboard` 的 `manifest.json`
   与 `joy2know-asset-ledger` 的 `--characters` / `--storyboard` 正确接续，尚未端到端联调。
5. ~~**构建暂存形态未校验**~~ → **1.3.0 轮已消**：跑了 `build.mjs joy2know-cine-team`，
   `dist/joy2know-cine-team-v1.3.0.zip` **4275.7 KB**；解包实测**第一层只有 `joy2know-cine-team/`**、
   根目录 `settings.json` 与 `setting.json` 都在、内嵌 `skills/joy2know-musician/SKILL.md` 读到
   **`version: 1.3.0`** 且新增的 `references/game-bgm-loop.md`（10226 字节）与新版 `scripts/suno_check.py`（18045 字节）
   **确实进了 zip** —— 内嵌副本未漂移。（旧 `cine-team-v1.2.0.zip` 已由构建自动清理，避免「旧产物嵌旧技能」继续存在。）
   - **仍未覆盖**：内嵌技能的「副本字节一致性」未逐字节比对 —— 本轮用**版本号 + 两个关键文件的存在与体积**证明副本是新的，
     没有对 3 个内嵌技能逐文件 `cmp` 全量比对（构建工具的复制逻辑本身也未审）。下次若构建工具改动，建议补一次逐文件校验。
6. **平台侧真实上传未做**：`settings.json` 双文件是 2026-09-17 的实测结论，本包未再实测；
   真实上传解析失败率、审核时长未记录。
7. **`profession` 与 `displayName` 的取值口径未在平台侧复核**：按仓库既有实证（卡片上的「名字」是
   `profession`）填写，本包未再复核。
8. **成员头像的「角色辨识度」未评估**：规格合规已测，但 8 张头像是否与角色气质相符属主观判断，本轮不评。

**已知缺陷**（**消解情况见本节末「修复记录」**）：

- **【已修 2026-09-23】** **缺陷 1（中）· README 未随 v1.1.0 的音乐人角色更新，共 4 处漏项（同一根因）。**
  ① 首段「**五个**专业角色」→ 实为 6 个；② 「团队构成」表缺「音乐人 小音」一整行；
  ③ 「工作流程」缺 `Phase 4.5 主题曲与配乐`；④ 「内置技能」缺 `joy2know-musician`。
  建议：按 `plugin.json` + `agents/joy2know-cine-lead.md` 重写 README 的四处。
  **影响**：README 是包内唯一面向人的说明，用户读完会以为团队只有 5 个角色、不会唱歌 —— 与产品实际能力不符。
- **【已修 2026-09-23】** **缺陷 2（轻）· `plugin.json` 内部口径冲突**：顶层 `description`（en）=「a **six-role** … a ready-to-paste
  **Suno** theme song」，而 `displayDescription.en` =「**Five** roles …」且五项里**没有音乐**。
  `displayDescription.zh` 是对的（六角色、含音乐）。建议把 en 版补成六项并保持与 zh 同义。
  **影响**：英文市场的专家卡片简介会漏报「能出主题曲」这一卖点。

- **【已修 2026-09-25 · v1.3.0 → v1.4.0】** **缺陷 3（轻）· 版本号多落点只改了一处，README 掉队**：
  1.4.0 轮把 `plugin.json` 的 `version` 升到 1.4.0，**却漏了包内 `README.md` 的「## 版本」行**
  （仍是 `1.3.0 · 作者：晓得乐`）。危害有三层：
  ① **违反本包自己在 §四 声明的不变量**（「源包体各文件版本号一致」）——
  **声明了不变量却不设检查，等于没有**；② 平台/用户看包时**两个版本号并存**，无法判断哪个是真的；
  ③ 上一轮（1.3.0）修的 `crosscheck.py` 里 **X17 就有一条「README 版本行 == plugin.json 版本」**，
  正因为那个脚本**没有入库**，这条判据本轮**没能自动拦住** —— 缺陷 3 是「工具不入库」的直接代价。
  **已修**：`README.md` 版本行改为 `1.4.0 · 作者：晓得乐`；并把「README 版本行」写进本轮验收的逐条比对清单。
  **性质判定**：属**非阻断性**（不影响平台解析与功能），但它是「跨文件口径脱节」这一类风险的**第三次出现**
  （1.1.0 成员表脱节 → 1.3.0 成员正文脱节 → 1.4.0 版本号脱节），**同一根因**，改判为**本包的头号系统性风险**。

**【已修 2026-09-23 · 版本 1.1.0 → 1.2.0】修法**：

- **缺陷 1 已修（README 四处漏项，同一根因 = 加音乐人角色时 README 没跟）**：
  ① 首段「**五个**专业角色」→「**六个**」；
  ② 「团队构成」表补一行「音乐人 | 小音 Melody | 主题曲 / 插曲 / 配乐方向，按 Suno 语法写歌 | 歌曲包 + 插入点建议」；
  ③ 「工作流程」在 Phase 4 与 Phase 5 之间补「**Phase 4.5 主题曲与配乐（小音，与 Phase 4 可并行；用户要歌时才做，不主动加歌）**」
  —— 与主理人 md 的 Phase 列表逐条对齐；
  ④ 「内置技能」补「**joy2know-musician（晓得·音乐人）**」，与 `skills.json` 的三项一致；
  另同步目录结构注释的 skills 行（分镜工 + 角色档案 + 音乐人）。
- **缺陷 2 已修**：`displayDescription.en` 由「**Five** roles …（五项里没有音乐）」改为
  「**Six** roles … and a **ready-to-paste theme song**」—— 与顶层 `description(en)` 的「six-role … Suno theme song」
  和 `displayDescription.zh` 的「六角色…主题曲」对齐，英文卡面不再漏报「能出主题曲」。

**验收（真跑；改后 9/9，git 原始版本 3/9）**：
校验器判据**全部取自包内真源**（`plugin.json` 的 `members[]`/`teamInfo`、`skills.json`、主理人 md 的 Phase 列表），不靠人工读。

| # | 用例 | 改前（git 原始版本） | 改后 |
|---|---|---|---|
| D1a | README「N 个专业角色」== 成员角色数（6） | ❌ README 写「五个」 | ✅「六个」 |
| D1b | README 团队构成表含全部成员角色名 | ❌ 缺「小音」 | ✅ 齐 |
| D1c | README 工作流程含主理人 md 全部 Phase | ❌ 缺 `Phase 4.5` | ✅ 8 个 Phase 齐 |
| D1d | README 内置技能列出 `skills.json` 全部技能 | ❌ 缺 `joy2know-musician` | ✅ 三项齐 |
| D2a | 顶层 description(en) 角色数 == 实际 | ✅（原本就是 six-role） | ✅ |
| D2b | `displayDescription.en` 角色数 == 实际 | ❌ Five ≠ 6 | ✅ Six |
| D2c | `displayDescription.zh` 角色数 == 实际（回归） | ✅ | ✅ |
| D2d | 顶层提到主题曲时 en 简介也必须提到 | ❌ 顶层有 Suno、en 简介无 | ✅ 两处都有 |
| D2e | `displayDescription.zh` 汉字数 40–50（回归） | ✅ 48 | ✅ |

**反向验证**：同一套用例对 **git 原始版本**跑出 **3/9**，失败的 6 条逐条对应两处缺陷原文
（D1a/b/c/d 属缺陷 1 的四个漏项，D2b/d 属缺陷 2）；D2a/D2c/D2e 作为阴性对照在原始版本上**照样通过**，说明判据不乱报。

**待办**（缺陷 1、2 已于 2026-09-23 修复，见上）：

- ~~修缺陷 1 后，README 的四处要与 `plugin.json` 逐条对齐。~~ → **已修**，且改用**自动校验器**核对（判据取自 `plugin.json`/`skills.json`/主理人 md，而非人工读），避免下次加角色再脱节。
- ~~修缺陷 2 后人工确认两版语义一致~~ → 已由校验器 D2d 固化：**「顶层提到主题曲时 en 简介也必须提到」成为可回归的判据**。
- 下次优先补未覆盖项 5：跑一次 `pnpm build joy2know-cine-team`，在暂存目录上复核内嵌副本无漂移与 zip 体积。
- **本轮暴露的自检盲区仍在**：`selfcheck.py` 不校验 `displayDescription.en` 的内容（只查 zh 字数）—— 建议后续给校验器补一条「en/zh 角色数一致性」检查；本轮先把该判据留在本报告的验收表里。

---

## 七、检测履历

| 日期 | 版本 | 状态 | 摘要（本轮测了什么、改了什么） |
|---|---|---|---|
| 2026-09-23 | 1.1.0 | ⚠️ 有条件通过 | 首次成文（覆写骨架）。字段自检 **26 通过 / 0 未通过**（源目录另有 5 条预期提示）；另人工核 `agents[]` ↔ `members[].id` ↔ `teamInfo.memberAgents` 三方一一对应、settings 双文件、Suno 角色是否真在内，逐张实测 8 张头像规格（512²/377–410 KB 全合规）与全仓图标台账（30/30 真图）。**10 组反向验证全抓**且未误伤。发现 1 处配置内部口径冲突（en 版漏音乐角色）+ 1 处 README 系统性脱节（4 个漏项）+ 8 项未覆盖。**未改包内任何文件。** |
| 2026-09-23 | 1.2.0 | ⚠️ 有条件通过 | **修复轮**：缺陷 1 → README 四处补齐（五个→六个、补音乐人整行、补 Phase 4.5、补内置技能 joy2know-musician、同步目录结构注释）；缺陷 2 → `displayDescription.en` 由 Five 改 Six 并补「ready-to-paste theme song」，与顶层 description 及 zh 简介对齐。验收：**真跑 9/9，同一套用例对 git 原始版本 3/9**；判据取自 `plugin.json`/`skills.json`/主理人 md 而非人工读，可长期回归。另记录 1 处**校验器盲区**（selfcheck 不查 en 简介内容），已在报告待办中留痕。 |
| 2026-09-25 | 1.3.0 | ⚠️ 有条件通过 | **联动升级轮**：内嵌的 `joy2know-musician` 升到 1.3.0（修掉「任何歌都要求三处语言锁」这条**反向指令**，改判为「人声锁」并新增纯器乐 / 循环 BGM 路径），本包**必须同步**否则团队会照旧指令人硬填语言锁。改 4 处：`agents/cine-music.md`（重写，人声/器乐分流 + 拒绝「用错换绿」）、`agents/joy2know-cine-lead.md`（成员表、信息收集第 5 问、Phase 4.5、汇编骨架第五节）、`README.md`（成员表、Phase 4.5、内置技能）、版本 1.2.0→1.3.0。验收：字段自检 **35 通过 / 0 未通过**（源目录 5 条预期提示）；新增 **22 条跨文件口径对照全部通过**（判据读技能真源，不写死）；**同一套对 git 原始版跑出 13/22**，红的 9 条逐条对应本轮改动；**3 组篡改反向验证各只打中对应那一条**；构建产物 `dist/joy2know-cine-team-v1.3.0.zip` 4275.7 KB，实测第一层、settings 双文件、内嵌 musician=1.3.0、新增 `game-bgm-loop.md` 已入包。**方法学失误 1 处已记**：X7 判据初版未锚定行，导致篡改 2 假绿，已改并复验。 |
| 2026-09-25 | 1.4.0 | ⚠️ 有条件通过 | **内嵌技能再升级（联动）**：内嵌的 `joy2know-musician` 1.3.0 → **1.4.0**。该版做了两件事 —— ① 依 help.suno.com 官方原文新增 `references/model-and-controls.md`（模型选型 v6 / v6-wild / v6-mini 与免费账号边界、Creative Sliders、**Exclude 的确切位置 = Custom → Advanced Options 菜单首项**、Voices 已取代 Personas）；② 修掉缺陷：器乐包的必留段落此前**只对 `--loop` 放宽**，致按文档写的合规非循环器乐包被判 2 error。本包据此改 3 处：`agents/cine-music.md`（把 Exclude 位置补进「压不住哼唱」的降级路径，与内嵌真源同一表述）、`.codebuddy-plugin/plugin.json`（版本 1.3.0→1.4.0）、`README.md`（**版本行 1.3.0→1.4.0 —— 上一轮漏改，本轮复检抓到并记为缺陷 3**）。验收：`selfcheck` 对本包 **通过 35 项 / 0 未通过**（源目录 5 条预期提示，与 1.3.0 轮持平；**初稿误抄 1.1.0 时代的「26 项」，本轮真跑改正 —— 记为本轮第 2 处「照抄旧结论」**）；以 `grep -E` 逐条比对本包成员文件与技能真源在「人声锁 / Exclude 位置 / 必留段落」三处、以及 **`plugin.json` 与 `README.md` 版本行的一致性**，**结论一致**；构建产物 `dist/joy2know-cine-team-v1.4.0.zip`，实测第一层、`settings.json`+`setting.json` 双文件、**内嵌 musician = 1.4.0**、新增 `model-and-controls.md` 已入包。**方法学退步如实记录**：上一轮那套 22 条跨文件口径对照脚本（`crosscheck.py`）是**一次性工具、未入库**，本轮无法原样重跑，只能降级为手工逐条核对；**而缺陷 3（README 版本行）恰恰就是那条被判据 X17 覆盖、却因脚本未入库而失守的项** —— 已列入待办：把该类校验器入库，否则每轮都要重写（这正是本仓库「换个目录也能跑」那条经验的镜像：**工具不入库 = 每轮从零开始**）。**另注**：v1.4.0 轮的 `crosscheck.py` 与 `/tmp/j2k-check/cine-team-v130/` 均已随 `/tmp` 清理消失，本行是本轮唯一的实测记录。 |
| 2026-09-25 | 1.5.0 | ⚠️ 有条件通过 | **内嵌技能再升级（联动）**：内嵌的 `joy2know-musician` 1.4.0 → **1.5.0**。该版把 Suno v6 世代的**实测控件现状**写进正文与脚本 —— ① 免费档实际只可选 `v6-mini`（**v4.5 / v5 / v5.5 已于 2026-09-09 全部退役**，此前的「免费 = v4.5」认知作废）；② 新增 `Variety`：官方 v6 FAQ 原文说它 *"adjusting and updating your style prompts"*，即**会改写你写的 Style**，而语言锁 / BPM / `Seamless loop` 全在 Style 里 —— 因此定为红线动作「交付必带 Variety 归 0」；③ `Exclude` 位置实测为 **More Options**（非 Advanced Options）且**免费账号里没有该字段**，降级路径因此从一条改为两条。本包据此改 **3 处**：`agents/cine-music.md`（**正文口径同步** —— S1 Exclude 位置、S2 两条降级路径、S3 Variety 配套动作、S4 输出加第 4 段「粘贴前设置」）、`.codebuddy-plugin/plugin.json`（版本 1.4.0→1.5.0）、包内 `README.md`（版本行 1.4.0→1.5.0）。验收：`selfcheck` **通过 35 项 / 0 未通过**（源目录 5 条预期提示，与 1.4.0 轮持平）；**产物内逐字节核对** —— `unzip -p` 读内嵌 `SKILL.md` 得 `version: 1.5.0`，内嵌 `references/model-and-controls.md` 与 `scripts/suno_check.py` 与源包 `diff` **均逐字节一致**，内嵌 `agents/cine-music.md` 含「More Options」计数 1（**旧包跑这条会是 0，故判据双向可判**）；构建产物 `dist/joy2know-cine-team-v1.5.0.zip` = **4286.7 KB**，第一层仅 `joy2know-cine-team/`，`settings.json`+`setting.json` 均在；`platformcheck.py --zip` 按 **Expert** 通过（并报出按 Skill / BuddyApp 上传必失败）。**本轮最关键的一条**：`agents/cine-music.md` 的「两层过期第 ② 层」**真的发生了** —— 它仍写着旧位置 `Advanced Options`、且全篇没有 Variety，而**自检完全看不见正文语义**；这也再次印证「内嵌联动必须查正文，不能只查版本号」。**方法学仍退步**：`crosscheck.py` 连续第二轮未入库、无法重跑，只能手工比对四处（人声锁 / More Options + Exclude 缺席 / 必留段落 / 版本 1.5.0），结论一致 —— 「校验器入库」已升为 **P1**。**新踩的坑**：检索工具默认跳过 `.codebuddy-plugin/` 这类点开头目录，查版本落点时险些漏判。 |
| 2026-09-26 | 1.5.0 | ⚠️ 有条件通过 | **随内嵌技能的描述修正同轮重建，版本号不抬**：`joy2know-musician` 的 `description_en` 被平台驳回（`解析失败：` / `Skill 英文描述：当前 1096 字符，上限 1000 字符`），该技能压到 **916 字符**后**同名重传**（不抬版本 —— 上传即被拒 = 平台侧从未存在过该版本，与「换入口重传不抬版本」同口径）。**本包内嵌它，因此带着同一份超限文件**：预检器对专家包的内嵌技能给出 ⚠️ 提示（「平台是否校验专家包里的内嵌技能」**未实证**，故不计入 pass/fail）。本轮**只重建、未改包内任何文本** —— `plugin.json` / `README.md` / `agents/*` 一字未动，版本仍 1.5.0。验收：`platformcheck.py` 扫全量 18 个产物**全绿**；`unzip -p dist/joy2know-cine-team-v1.5.0.zip joy2know-cine-team/skills/joy2know-musician/SKILL.md` 与 `dist/joy2know-musician-v1.5.0.zip` 内的同一文件**逐字节一致**（描述均 916 字符）。**本轮顺带补上一类可回归门禁**：`platformcheck.py` 新增 `DESC_LIMITS` 描述长度判据（`--selftest` 13 项 → **19 项**，含 1000 字符**边界**用例）—— 这是第一条同时覆盖「技能包自身」与「专家包内嵌技能」的描述长度检查。 |
