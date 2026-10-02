# joy2know-topic-planner 发布前检测报告

> **口径说明**：每条结论对应一次**真实运行**（命令 + 样本 + 输出要点）。
> 校验器为仓库权威版 `scripts/selfcheck.py`；平台侧入口判据复刻在 `scripts/platformcheck.py`。
> 本包是单专家（`expertType: agent`），**纯提示词包 + 1 个内嵌技能**：专家本体无 `scripts/`；
> 内嵌技能 `joy2know-viral-topic` 带**两个只读 Python 脚本**（打分器与判据自检），**无网络调用、无写文件、无凭证**。
> **排除文件说明**：本报告是包根那一个 `joy2know-topic-planner.md`（开发期文档，不进 zip）；
> 角色定义 `agents/joy2know-topic-planner.md` 是**真 agent、不被排除**。

- **包名**：joy2know-topic-planner
- **类型**：单专家（`expertType: "agent"`）
- **对应版本**：1.0.0
- **检测状态**：⚠️ 有条件通过
- **最后检测**：2026-09-30
- **检测方式**：功能测试 + 完整性对照 + 合理性检查 + 反向验证

---

## 一、包内文件（从磁盘枚举，不手写）

```
   2307  .codebuddy-plugin/plugin.json              配置（expertType: agent，1 agent / 1 内嵌技能）
   3421  README.md                                   包说明（他解决什么问题 / 三条底线 / 包内容 / 用法）
   7728  agents/joy2know-topic-planner.md            角色定义（开场引导 / 流程 / 7 条硬规则 / 产出格式 / 10 条自检 / 边界）
    195  skills.json                                 内嵌技能声明（构建时从 packages/<名>/ 复制真源）
```

**零第三方依赖核对**：专家本体无 `scripts/`、无 import、无网络调用；内嵌技能的 `score.py` / `selftest.py`
只用 Python 标准库（`argparse` / `json` / `sys` / `os` / `re`），结构性零依赖成立。

源包体（不含本报告）**5,912 字节 ≈ 5.8 KB**；构建产物 `dist/joy2know-topic-planner-v1.0.0.zip` 实测 **898.3 KB**
（含构建注入的头像与内嵌技能 `joy2know-viral-topic`）。专家包上限 **20 MB**，余量约 23 倍。

**头像规格（已实测）**：`avatars/joy2know-topic-planner.png` = 512×512 / **443.7 KB**，**已是真图、尺寸与格式合规**。

---

## 二、能力清单与验证结果

| 能力 / 待验证项 | 验证方式（命令与样本） | 结果 | 证据要点 |
|---|---|---|---|
| plugin.json 全字段遍历 + 中英成对 + 硬约束达标 | `$V/bin/python scripts/selfcheck.py packages/joy2know-topic-planner` | ✅ 通过 | **通过 11 项 / 0 问题**（源目录另有 3 条预期提示：内嵌技能与头像「构建时才注入」、zip 未生成） |
| 官方硬约束：`displayDescription.zh` 40–50 汉字 | 同上 + 正则计汉字 | ✅ 通过 | 实测 **48 汉字**（中段，不贴边界） |
| 官方硬约束：`defaultInitPrompt` == `quickPrompts[0]` | 同上 | ✅ 通过 | 两版（zh/en）逐字相同 |
| 官方硬约束：`tags` / `quickPrompts` 各 3 个 | 同上 | ✅ 通过 | 各 3 |
| `categoryId` 在官方 15 类白名单内 | 同上 | ✅ 通过 | `05-MarketingGrowth` |
| `agents[]` 路径存在 | 同上 | ✅ 通过 | 1/1 存在 |
| `agents/*.md` 的 `name` == `agentName` == 目录名 | 同上 + 构造错样本反向验证 | ✅ 通过 | 三者一致（错样本 s3 已确认这条会亮红灯） |
| **内嵌技能主源存在** | `ls packages/joy2know-viral-topic` | ✅ 通过 | 源技能包存在（SKILL.md + 2 references + 2 scripts） |
| **内嵌副本与主源逐字节一致（未漂移）** | `diff -r -x icon.png -x joy2know-viral-topic.md <zip内副本> packages/joy2know-viral-topic` | ✅ 通过 | **逐字节一致**；唯一差异是主源里的检测报告与构建注入的 `icon.png`（均正确排除） |
| **交付形态（解压 zip 后）完整自检** | `unzip -qq dist/…zip && $V/bin/python scripts/selfcheck.py /tmp/j2k-solo/joy2know-topic-planner` | ✅ 通过 | **通过 14 项 / 0 问题** —— 比源目录多 3 项（内嵌技能路径、头像注入生效） |
| zip 第一层目录名正确（无多套一层） | `unzip -Z1 dist/…zip \| head -1` | ✅ 通过 | 第一层唯一为 `joy2know-topic-planner/` |
| 平台入口判据：按 Expert 类型可通过 | `$V/bin/python scripts/platformcheck.py --zip dist/joy2know-topic-planner-v1.0.0.zip` | ✅ 通过 | `Expert ✅ 通过`；`Skill ❌`（缺根级 `SKILL.md`，预期 —— 本包不该走技能入口） |
| 包内无硬编码凭证 | selfcheck `[sec]` 项 | ✅ 通过 | 未发现疑似凭证 |
| **内嵌打分器判据自检**（阈值边界 / 阻断 / 告警 / 文档锚点） | `$V/bin/python skills/joy2know-viral-topic/scripts/selftest.py`（构建后路径） | ✅ 通过 | **32 项通过 / 0 失败**；含 9 条阈值边界两侧、4 条阻断正例、5 条阻断反例、3 条告警反例、4 条输入校验、3 条文档锚点 |
| **打分器把坏阈值抓出来**（防橡皮章） | 把 `score.py` 的 `(35, "重点做")` 改成 `(30, …)` 后重跑 selftest | ✅ 抓到 | **立刻 3 项红灯**：`边界 34 分 判成 重点做，应为 合格`、`边界 30 分 …应为 合格`、`例三 31 分…文档写「合格」，脚本判「重点做」`；恢复后回到 32 通过 |
| 反向验证：9 组「应该被抓」的错样本 + 2 组阴性对照 | 见第五节 | ✅ 9/9 抓到 + 对照全绿 | 每组只亮对应红灯，未误伤其他检查项 |
| 选题实际质量（分数是否给对了、Top 3 选得对不对） | — | 未覆盖 | 需真实跑一轮选题，见第六节 |
| 平台侧真实上传 / 审核 | — | 未覆盖 | 从未提交，见第六节 |

**复现命令**

```bash
V=~/.workbuddy/binaries/python/envs/default
$V/bin/python scripts/selfcheck.py packages/joy2know-topic-planner       # 源目录：11 通过 / 0 问题 / 3 提示
$V/bin/python packages/joy2know-viral-topic/scripts/selftest.py          # 判据自检：32 通过 / 0 失败
node scripts/build.mjs joy2know-topic-planner                            # 构建
$V/bin/python scripts/platformcheck.py --zip dist/joy2know-topic-planner-v1.0.0.zip
zsh /tmp/solo-revcheck.sh                                                # 反向验证 9 组 + 2 对照
```

---

## 三、门 2 · 完整性对照（文档承诺 → 实现）

| 文档承诺（摘原文） | 实现位置 | 有 / 无 / 部分 | 备注 |
|---|---|---|---|
| README「他解决什么问题」四条症状 | `agents/…md §三` 硬规则 | **有** | 每条症状都对应一条硬规则 |
| README「三条底线」：先筛后打 / ⑥⑧ 是分界线 / 分数由脚本算 | `agents/…md §二` + 内嵌技能 `SKILL.md §五` + `score.py` | **有** | 三处口径一致；底线 3 落到可执行脚本 |
| README「包内容」目录树含 `references/` 与 `scripts/` | 内嵌技能真源 `packages/joy2know-viral-topic/` | **有** | 构建后包内实测：SKILL.md + method.md + examples.md + score.py + selftest.py + icon.png |
| 方法论主体在技能里、角色定义不重复技能内容 | `agents/…md §二` 末段 | **有** | 明写「以已加载的 `joy2know-viral-topic` 技能为准，本文件只规定角色、流程和验收标准」 |
| 12 条心法 / 4 基因 / 8 维打分 / 6 形态 | 内嵌技能 `SKILL.md §三–§六` | **有** | 四张表齐全；⑥⑧ 在 `SKILL.md`、`method.md`、`score.py` 三处都标了「分界线」 |
| 「淘汰区不许空」这条反注水硬规则 | `agents/…md §三 规则 3` + `§五` 自检第 6 条 | **有** | 规则与自检双向锁定 |
| 开场引导里的输入自给降级路径 | `agents/…md §一` | **有** | 「你手上什么都没有，我也能开工」+ 三问逼出原料 + 占位原料标 `【假设-需验证】` |
| README「怎么用」四行示例 | `agents/…md` 各节 | **有** | 四条示例对应的能力都有实现 |
| README 目录结构图列 `avatars/` 与 `skills/` | 构建时注入 | **有（设计如此）** | 源包无此两目录；README 已写明形态说明与注入来源 |

**兜底口径两向核对**：正向（README / plugin.json 承诺 → 有实现）全部通过；
**反向（实现里有、文档没写）未发现缺口** —— agent 的 7 条硬规则中，规则 7（分数不能手改）未在 README 单独列，
但它是底线 3 的直接展开，属覆盖范围。

---

## 四、门 3 · 合理性结论

- **规则是否自洽**：✅ 无互相打架。三条底线（先筛后打 / ⑥⑧ 分界线 / 脚本算分）在 agent、SKILL.md、score.py 三处说法一致。
  边界成对写清 —— agent 规则 6 写「你只到选题 + 标题方向为止」，与相邻环节（文案）的界线用对方的活来解释。
- **推断是否标注为推断**：✅ 三处强制 —— agent 规则 4（热点标时效、数据指出处）、规则 5（无关话题进「池外建议」）、
  §五 自检第 10 条（引用都要指出处）。
- **错误提示是否可指导下一步**：✅ 降级路径都给了明确动作（原料不合格 → 退回补齐；缺热点数据 → 换常青角度；
  只有一条候选 → 写「无横向比较」而不给排名）。
- **边界是否优雅**：✅ §六 覆盖五类边界（不做定位 / 不写文案 / 不预测播放量 / 不承诺爆款 / 不代人转交）。
- **零依赖是否守住**：✅ 结构性成立。内嵌脚本只用标准库，且**只读**（不写任何文件）。
- **值来源是否可追溯**：✅ 版本号 1.0.0 三处一致（plugin.json / README / 本报告）；头像真源在仓库根 `avatars/`；
  内嵌技能真源在 `packages/joy2know-viral-topic/`（已实测副本逐字节一致）。
- **⚠️ 阈值 35/30/24 的来源**：来自选题方法论（对标公开的爆款选题方法后做的**推广化改造**），
  **不是**平台规则或行业实测值。它已硬编码进 `score.py` 并在 `SKILL.md` 写明「改阈值 = 改判据，要连 selftest 一起改」，
  属本包**最需要在使用中校准的数字**（见第六节弱项 W1）。

---

## 五、门 4 · 测试真实性自评（防放水）

- [x] 1. 只跑 happy path，没跑边界 —— **否**：判据自检本身含 9 条阈值边界两侧用例；反向验证 9 组覆盖 9 类不同约束
- [x] 2. 只看「没报错 / 退出码 0」，没核对输出内容 —— **否**：逐条核对**报错措辞是否指向正确的那一项**，并确认未误伤其它项
- [x] 3. 把「文档写了」当成「已验证」 —— **否**：把「选题实际质量」「平台真实上传」「阈值无行业出处」三项明确列入第六节
- [x] 4. 自造理想样本（比真实产物干净） —— **否**：交付形态测试用的是**真实 zip 解压产物**，不是源目录
- [x] 5. 跳过失败项、不记录 —— **否**：0 项失败；但**本轮改了校验器本身**，两处修改与验证过程全部记在下文，不掩盖
- [x] 6. 修完只测修好的那条，没跑回归 —— **否**：两处修改后跑了**全仓 26 个包**的源目录自检（0 红灯）+ 重跑全部反向验证样本
- [x] 7. 造错样本只造了会被抓的那种 —— **否**：9 组里有 2 组**最初没被抓到**（见下），正是它们暴露了校验器的真实缺陷

**反向验证记录**

| # | 造了什么错样本 | 预期 | 实际（原文要点） |
|---|---|---|---|
| S0 | 阴性对照（仅复制干净副本） | 全绿、不乱报 | ✅ `=== 全部自检通过 ===`（0 问题） |
| S1 | 删掉 plugin.json 的 `avatar` 字段 | 报缺字段 | ✅ `[expert] avatar 字段缺失或为空（官方必填…）` —— **首轮未抓到，修完才亮**（见下） |
| S2 | `categoryId` 改成 `99-NoSuchCategory` | 报不在白名单 | ✅ `categoryId 不在合法分类列表中: '99-NoSuchCategory'` |
| S3 | agent frontmatter 的 `name` 改成 `totally-different-name` | 报名称不一致 | ✅ `agent name='totally-different-name' 既非 agentName…也不在 members[].id 中` |
| S4 | `skills` 路径改成 `./skills/joy2know-does-not-exist` | 报技能名错 | ✅ `skills 声明了 …但真源 packages/joy2know-does-not-exist/SKILL.md 不存在` —— **首轮未抓到，修完才亮**（见下） |
| S5 | `displayDescription.zh` 加长到 60 汉字 | 报汉字数越界 | ✅ `displayDescription.zh 汉字 60 字，超出官方要求 40-50` |
| S6 | `agents[0]` 路径改成 `./agents/not-there.md` | 报路径缺失 | ✅ `agents 路径 缺失: ./agents/not-there.md` |
| S7 | plugin.json 的 `name` 改成 `some-other-package` | 报目录名不一致 | ✅ `plugin.name 'some-other-package' 与目录名 'joy2know-topic-planner' 不一致` |
| S8 | **把 `score.py` 的阈值 35 改成 30** | 判据自检必须红灯 | ✅ 立刻 3 项红灯（边界 34/30 + 文档锚点例三）；恢复后 32 通过 |
| T0 | 技能包阴性对照 | 全绿 | ✅ 0 问题 |
| T1 | 技能 SKILL.md 删掉 `category` | 报缺必填字段 | ✅ `[skill] frontmatter 缺字段: category` |
| T2 | 技能 SKILL.md 删掉 `author` | 报缺 author | ✅ `frontmatter 缺字段: author` + `author 为空（官方必填：合作方名称）` |
| T3 | 技能 SKILL.md 的 `name` 改成别的 | 报与目录名不一致 | ✅ `[skill] name 字段 'joy2know-something-else' 与目录名 'joy2know-viral-topic' 不一致` |

**本节最重要的发现：反向验证抓到了校验器自己的两个真缺陷，已当轮修掉。**

1. **`avatar` 字段缺失会让自检崩溃**（不是报错，是**崩**）。
   旧代码 `av = os.path.join(root, pj.get("avatar", ""))` —— 字段为空时拼出的是**目录**，
   下一行 `open(av, "rb")` 抛 `IsADirectoryError`，**整份报告被中断吞掉**。
   使用者看到的是 traceback，而不是「缺字段 avatar」+ 其余检查结果 —— 这比漏检更坏：**它把已查出的问题一起藏了**。
   已改为：字段为空直接 `bad()`，且用 `os.path.isfile()` 而非 `exists()` 判存在。

2. **`skills` 里把技能名拼错，在源目录模式下被静默放过**。
   源目录里内嵌技能不存在属正常（构建时才注入），但旧判据把「还没构建」与「名字写错了」一视同仁记成提示 ——
   拼错技能名要等到构建才暴露。已改为**回真源看一眼**（`packages/<技能名>/SKILL.md`）来区分两者。

> **回归验证**：两处修改后对**全仓 26 个包**重跑源目录自检 —— **红灯合计 0**，未误伤任何既有包。

**另一条方法教训（与包无关，与检测方法有关）**：新增的「回真源」判据与既有的头像回退判据共用同一个假设 ——
**base 的父目录就是仓库根**。拿副本目录做反向验证时，副本根下要同时备好 `avatars/` 与 `packages/` 两个软链，
否则基线也会红（本轮第一遍就是这样假红的）。该假设已就地写进 `selfcheck.py` 注释。

**一句话回答：本包的核心结构如果坏掉，是哪一步会亮红灯？**

→ 平台解析层（配置字段 / categoryId / agent 名对应 / 描述字数 / 头像路径 / **技能名**）坏了 → `selfcheck.py` 亮红灯。
→ 交付形态层（zip 第一层、内嵌副本漂移、头像注入）坏了 → 解压后的交付形态自检亮红灯（14 项）。
→ 方法论层（阈值被改坏、告警规则失效、文档与脚本漂移）坏了 → `selftest.py` 亮红灯（32 项，含**文档锚点一致性**）。
→ **有一类不会亮红灯**：选题的**实际质量**（分数给得对不对、Top 3 选得对不对、12 条心法的判定是否合理）——
  任何自动校验都读不出这个。这是本包最大的未覆盖面（见第六节 1）。

---

## 六、未覆盖项 / 已知缺陷 / 待办

**未覆盖项**（下次检测优先消掉这些）：

1. **选题实际质量未评估**：本轮只验了结构与判据（表格齐备、脚本可跑、边界正确），
   不验**内容质量**（8 维分数给得对不对、Top 3 是否真是最优、12 条心法判定是否贴合真实场景）。
   需真实跑一轮完整选题才能评估。
2. **平台侧真实上传 / 解析 / 审核未实测**：`categoryId` 白名单、专家入口判据是历史实测结论，本包未再实测。
3. **`categoryId` 取 `05-MarketingGrowth` 是推断值**：按「解决推广选题问题」的实质选定，平台是否认可**未经实证**。
4. **专家包内嵌技能是否被平台解析未核实**：`skills: ["./skills/joy2know-viral-topic"]` 与 agent frontmatter 的
   `skills: [joy2know-viral-topic]` 口径合理，但**官方文档未列 `skills:` 字段**，无法确认平台是否解析它。
5. **内嵌技能与「爆款炼金师」的方法论血缘未做逐条比对**：本技能方法论是对同类公开方法的**推广化改造**
   （把传播锚点/参与门槛两维换成 ⑥卖点承载 / ⑧转化承接），改造点是自创的，但上游方法的覆盖范围未逐条 diff。

**已知弱项**（不阻断上架，记在案）：

- **W1 · 阈值 35/30/24 无行业出处**：来自方法论自定，非平台规则或行业实测。已硬编码进 `score.py` 并说明「改阈值 = 改判据」。
  真实使用若干轮后应据实际表现复核这三个数。
- **W2 · 平台标题字数上限无出处**：agent 未给字数表（那是文案环节的），本包不涉及。
- **W3 · `references/method.md` 的「虚高信号」是经验判断**：例如「给 5 分却只说得出『挺有共鸣的』」——
  这类判据的价值在于可比性，不在精确性，已在文件内定性表述。

**待办**：

- 出真头像 → 覆盖同名文件 → 重跑 `node scripts/build.mjs joy2know-topic-planner`。
- 真跑一轮完整选题（含淘汰区与 Top 3），评估未覆盖项 1。
- 首次提交后回填 `release.config.json` 的 `submitted`，并在 `发布清单.md` 追加一行。

---

## 七、检测履历

| 日期 | 版本 | 状态 | 摘要（本轮测了什么、改了什么） |
|---|---|---|---|
| 2026-10-02 | 1.0.0 | ⚠️ 有条件通过 | **图标换真图 + 体积回填（不抬版本）**。`avatars/joy2know-topic-planner.png` 由占位图（16 KB）换成真图（**443.7 KB**，512×512）。重建后产物由 51.4 KB 涨到 **898.3 KB**（余量约 23 倍），源包体 5,923 → **5,912 字节**（`displayName` 由花名「霍燃」改「晓得乐」所致）。第六节未覆盖项 5 已闭环删除，后续编号顺延。本包从未提交，版本号不动。 |
| 2026-09-30 | 1.0.0 | ⚠️ 有条件通过 | **首次建包 + 首次检测**。新建单专家「晓得·爆款选题策划专家」，内嵌同步新建的技能包 `joy2know-viral-topic`（12 心法 / 4 基因 / 8 维打分卡 / 6 形态 + 打分器 + 判据自检）。**源目录自检 11 通过 / 0 问题 / 3 提示**；**解压后交付形态自检 14 通过 / 0 问题**；`platformcheck --zip` 判 **Expert ✅ 通过**（Skill ❌ 属预期）；内嵌副本与主源 **diff 逐字节一致**；`displayDescription.zh` 实测 **48 汉字**；头像 512×512 / 16 KB（占位图）。**判据自检 32 项全过**，并实测「把阈值 35 改成 30 → 立刻 3 项红灯」确认它不是橡皮章。**反向验证 9 组错样本 + 2 组阴性对照全部符合预期**；其中 2 组最初未被抓到，**暴露并修掉了 `selfcheck.py` 的两个真缺陷**（avatar 字段缺失导致崩溃、skills 技能名拼错被静默放过），修后对全仓 26 个包跑回归 **0 红灯**。发现 6 项未覆盖 + 3 项弱项。 |
| 2026-10-02 | 1.0.0 | ⚠️ 有条件通过 | **卡面署名修正（不抬版本）**：`displayName` 由花名「霍燃」改为品牌署名「晓得乐」（`en: joy2know`），与在架专家（`code-scholar` / `mr`）的既定口径对齐；agent 前置描述、正文标题、README、本报告内的花名一并去除，**花名仅保留在 `joy2know-promo-team` 的成员位**。本包平台侧从未提交，故版本号不动。 |
