# joy2know-mureka-musician 发布前检测报告

> **口径说明**：每条结论对应一次**真实运行**（命令 + 样本 + 输出要点）。
> 校验器为仓库权威版 `scripts/selfcheck.py`；平台侧入口判据复刻在 `scripts/platformcheck.py`；
> 合规用词门禁为 `scripts/compliance_wording.py`。
> 本包是技能包：`SKILL.md` + 4 个 `references/` + 1 个只读 JS 脚本（Node 标准库，
> **无网络调用、无写文件、无凭证**）。
> 内容主干 = 仓库根《Mureka音乐人提示词指南.md》（2026-10-14 登录态真机实测）+ 官方 FAQ（2026-10-15 抓取）。

- **包名**：joy2know-mureka-musician
- **类型**：技能（Skill）
- **对应版本**：1.0.0
- **检测状态**：⚠️ 有条件通过
- **最后检测**：2026-10-15
- **检测方式**：功能测试 + 完整性对照 + 合理性检查 + 反向验证

---

## 一、包内文件（从磁盘枚举，不手写）

```
  24665  SKILL.md                              9 必填 frontmatter + 双栏四层 / 路由 / 工作流 / 7 条核心规则 / 交付格式 / 13 条反模式 / 防幻觉 / 完成判据
   4104  references/style-tokens.md            风格栏七要素 · token 正反例 · 融合配方（Mureka 官方鼓励）
   4919  references/mureka-controls.md         实测控件全表 · 参考歌曲与性别冲突 · 交付前必做（必做类，已被 §七 点名）
   5955  references/genre-cookbook.md          爵士 / 蓝调 / 民谣完整配方（BPM / 乐器盘 / 结构 / AAB 句式 / 反模式）
   5506  references/lyrics-craft.md            治愈文风内核 · 中文补断句细则 · 三套预设（晨光 / 夜灯 / 归途）
  15716  scripts/mureka_check.mjs              结构校验器（L/S/T/X 四组检查 + --selftest 21 项内置正反样本）
```

**零第三方依赖核对**：`mureka_check.mjs` 只 `import { readFileSync } from 'node:fs'`，其余为语言内置；
无 `http / urllib / requests / socket / api_key / fetch(`（selfcheck `[sec]` 项实测通过）——
「不接入任何生成接口」的否定式声明核得过。

源包体（六个源文件，**不含本报告**）**60,855 字节 ≈ 59.4 KB**；构建产物 `dist/joy2know-mureka-musician-v1.0.0.zip` 实测 **29,474 字节（28.8 KB）**。技能包上限 **3 MB**，余量约 100 倍。

**描述字段长度（platformcheck 实测）**：`description` **390** 字（系列经验区间 239–390 内，压过两轮：534 → 423 → 390）；
`description_en` **966/1000**；`description_zh` 116 字。

**图标（占位图）**：`avatars/joy2know-mureka-musician.png` = 512×512 / 11.1 KB 占位图（已入 `.placeholders.json` 台账），
**待小乐拍板配色后换真图**（见第六节）。

---

## 二、能力清单与验证结果

| 能力 / 待验证项 | 验证方式（命令与样本） | 结果 | 证据要点 |
|---|---|---|---|
| frontmatter 9 必填 + name==目录名 + @references 引用有效 | `$V/bin/python scripts/selfcheck.py packages/joy2know-mureka-musician` | ✅ 通过 | **全部自检通过**，4 个 @references 逐一验证存在 |
| 描述字段长度（description_en ≤1000） | `$V/bin/python scripts/platformcheck.py --zip dist/…zip` | ✅ 通过 | `description_en=966/1000`，`description=390` |
| 平台入口判据：按 Skill 类型可通过 | 同上 | ✅ 通过 | `Skill ✅ 通过 ← 本包应有的类型`；`Expert ❌`（缺 plugin.json，预期——本包不走专家入口） |
| **校验器 21 项内置自检** | `node scripts/mureka_check.mjs --selftest` | ✅ 通过 | **自检 21 项全部通过**（正常包 / 器乐包 / 循环包 / 8 类 FAIL 反例 / 2 类 WARN / 否定词陷阱回归） |
| **校验器 CLI 文件路径真跑**（正常 / 器乐循环 / 坏样本 / 用法错误） | 见第五节样本表 | ✅ 通过 | 正常包与器乐循环包 `0 FAIL / 0 WARN`（EXIT=0）；坏样本抓出 3 FAIL（EXIT=1）；缺 `--style` 与文件不存在均 EXIT=2 且提示可执行 |
| **反向验证：改坏判据自检必红** | 把 `codePoints(lyrics) > 5000` 改成 `> 50` 后重跑自检 | ✅ 抓到 | **立刻 2 项红灯**（正常有人声包 / 正常器乐包均报 L1）；还原后 21 项回绿 |
| 结构校验器自身的两处误报（真跑抓到，已修） | 见第五节「本节最重要的发现」 | ✅ 已修 | ① `no fade out` 否定声明被当违规；② 按空行分段统计长段误报。修复后补 3 条自检锚点回归 |
| 合规用词门禁 | `$V/bin/python scripts/compliance_wording.py packages/joy2know-mureka-musician` | ✅ 通过 | **通过 4 · 提示 1 · 失败 0**；唯一提示为 `description_zh` 的「生成→音频」已被同字段否定式声明兜住（人工确认：覆盖） |
| R6 跨包审计 | `$V/bin/python scripts/series_audit.py .` | ✅ 通过 | 三类候选（R4 / R2 / R1）**均不含本包**（初检 `--selftest` 未文档化 1 条，已按 R2 补进 §八并复扫归零） |
| 实际粘贴到 Mureka 的生成效果 | — | **未覆盖** | 本报告验的是文本结构与判据，不验生成质量；需真跑生成试听，见第六节 |

**复现命令**

```bash
V=~/.workbuddy/binaries/python/envs/default
$V/bin/python scripts/selfcheck.py packages/joy2know-mureka-musician
node packages/joy2know-mureka-musician/scripts/mureka_check.mjs --selftest
node scripts/build.mjs joy2know-mureka
$V/bin/python scripts/platformcheck.py --zip dist/joy2know-mureka-musician-v1.0.0.zip
$V/bin/python scripts/compliance_wording.py packages/joy2know-mureka-musician
$V/bin/python scripts/series_audit.py .
```

---

## 三、门 2 · 完整性对照（文档承诺 → 实现）

| 文档承诺（摘原文） | 实现位置 | 有 / 无 / 部分 | 备注 |
|---|---|---|---|
| §三 工作流第 6 步「结构校验（必跑）」及 `--instrumental` / `--loop` 开关 | `scripts/mureka_check.mjs` | **有** | 参数逐一实现并实测；`--title` 同样实现并在示例命令中出现 |
| §三 第 6 步「WARN 逐条给出处理说明」 | `report()` 输出 | **有** | WARN 带 `↳` 处理提示行；实测坏样本逐条给出 |
| §四 规则 2「BPM 必给」「融合 ≤3 基色」 | `mureka_check.mjs` S2 + 文档层 | **部分** | BPM 缺失可机检；**基色数量**是语义判断，脚本不查（靠模型执行规则 2）——已在判据边界写明 |
| §四 规则 3 语言声明 / 段落标签 / 重复位置 | `mureka_check.mjs` L2 / L3 / L4 | **有** | L2·L3 FAIL、L4 WARN（重复标注属文意判断，降为 WARN 有意为之） |
| §四 规则 6 器乐四件（No vocals / 无人声词 / 歌词栏留空 / 纯音乐开关） | S4 + X1 | **有** | 「纯音乐开关」是界面动作，落在交付块（mureka-controls.md 第五节），脚本查前两件 |
| §四 规则 7 循环四条（seamless / 无 fade / BPM 写死 / 首尾同源） | S5 | **有** | 前三条机检；「首尾同源」是写法要求（[End] 标签语义），脚本查 fade 与 BPM |
| §七 按需知识四个 @references 路由 | 4 个文件均在，selfcheck 引用验证通过 | **有** | `mureka-controls.md` 的必做类章节「五、交付前必做的界面动作」已被 §七 点名（R4） |
| §八「改判据先过自检」维护纪律 | `--selftest` 21 项 | **有** | R2 初筛曾报该开关未文档化，补文档后复扫归零 |
| 〇 节「不提账号档位 / 订阅 / 额度」 | 全包检索 | **有** | 包内无金币 / 价格 / 套餐 / 订阅字样（FAQ 的 Studio 档位信息已剥离，只留「账号是否可用以界面为准」） |

**兜底口径两向核对**：正向（文档承诺 → 有实现）无缺口；反向（实现里有、文档没写）无缺口——
脚本全部 6 个参数（文件、--style、--title、--instrumental、--loop、--selftest）都已进文档。

---

## 四、门 3 · 合理性结论

- **规则是否自洽**：✅ 无互相打架。规则 1（英文 token）与规则 2（七要素）在 SKILL.md、style-tokens.md、
  genre-cookbook.md 三处口径一致；规则 6 的「No vocals 首句」与校验器 S4 判据一致。
- **推断是否标注为推断**：✅ 界面事实全部标注「2026-10-14/15 实测」来源，并写明「平台界面会随版本变，
  控件以用户当前界面实际表现为准」；官方文档与实测不符处（无时长 / 版本 / 人声参数滑杆）以实测为准并注明纠偏。
- **错误提示是否可指导下一步**：✅ 每条 FAIL/WARN 带 `↳` 修复提示；用法错误（EXIT=2）给完整用法行与原因。
- **边界是否优雅**：✅ 空输入不静默放行（自检含「空输入至少 3 条 FAIL」锚点）；文件读不了、缺参数均为 EXIT=2 人话提示。
- **零依赖是否守住**：✅ 结构性成立——唯一 import 是 `node:fs` 的 `readFileSync`，只读本地文件。
- **值来源可追溯**：✅ 5000/1000/50 三个上限来自 2026-10-14 真机 DOM 的 `maxlength` 实测；
  L5 的「4–6 行」与 S5 的循环约束来自写法规则，定性表述、非平台硬限制，文档已写明。

---

## 五、门 4 · 测试真实性自评（防放水）

- [x] 1. 只跑 happy path，没跑边界 —— **否**：CLI 真跑含坏样本（无声明 / 无 BPM / 无人声声明 → 3 FAIL）与两类用法错误（EXIT=2）
- [x] 2. 只看「没报错 / 退出码 0」，没核对输出内容 —— **否**：逐条核对了 FAIL 的 id 与措辞是否指向正确检查项
- [x] 3. 把「文档写了」当成「已验证」 —— **否**：「实际生成效果」「平台上传」「头像配色」三项明确列入第六节
- [x] 4. 自造理想样本（比真实产物干净） —— **否**：CLI 样本含「无空行分隔的连续段落」这类真实歌词常见形态（正是它暴露了 L5 误报）
- [x] 5. 跳过失败项、不记录 —— **否**：校验器首轮真跑暴露的 2 处误报全部记录在案并当轮修复
- [x] 6. 修完只测修好的那条，没跑回归 —— **否**：两处修复后自检扩到 21 项（新增 3 条回归锚点）并重跑全部 CLI 样本
- [x] 7. 造错样本只造了会被抓的那种 —— **否**：反向验证先让基线全绿，再把阈值改坏确认自检变红；且改坏位置（L1 阈值）让**两个原本全绿的用例**同时红灯，证明不是只抓预设错样本

**反向验证记录**

| # | 造了什么错样本 | 预期 | 实际 |
|---|---|---|---|
| S1 | 正常有人声包（声明 / 标签 / 重复 / 七要素全齐） | 0 FAIL / 0 WARN | ✅ `[OK] 全部检查通过`，EXIT=0 |
| S2 | 中文歌词删语言声明 | L2 FAIL | ✅ 命中，提示给出声明句原文 |
| S3 | 副歌两遍、无重复标注 | L4 WARN | ✅ 命中 |
| S4 | 风格栏删 BPM / 删人声声明 | S2 / S3 FAIL | ✅ 命中 |
| S5 | 器乐包风格栏带 `female vocal` / 缺 `No vocals` | S4 FAIL ×2 | ✅ 均命中（`No vocals` 声明本身不被误报为人声词——`vocalsLeftover` 已剥离否定声明） |
| S6 | 器乐包歌词栏写正文 | X1 FAIL | ✅ 命中 |
| S7 | 循环包带 `fade out` 标签 / BPM 区间 / 缺 seamless | S5 FAIL | ✅ 均命中 |
| S8 | 歌名 51 字 / 风格栏 1100 字 / 歌词 5100 字 | T1 / S1 / L1 FAIL | ✅ 均命中（--selftest 内置） |
| S9 | 阴性对照：`no fade in, no fade out` 声明 | 不触发 fade 检查 | ✅ 初版**误报**，修复后通过并固化成自检锚点 |

**本节最重要的发现：结构校验器首轮 CLI 真跑抓到自身两处误报，已当轮修掉。**

1. **否定声明陷阱**：循环包风格栏写「no fade out」（合规写法）会被旧判据当成违规——与 `No vocals` 同类，
   声明本身含敏感词。已加 `hasFadeOut()` 先剥离 `no fade in / no fade out / without fade` 再查。
2. **分段口径错误**：长段检查最初按空行切分统计，真实歌词常不空行分隔，4 行一节的规范包被误报 9 行。
   已改为按段落标签切节统计（`maxSectionLines()`），声明句独占一节不计数。

> **回归验证**：修复后自检 19 → 21 项（新增「正常包无 L5」「否定声明不触发 fade」锚点），
> 全部 CLI 样本重跑通过；R6 复扫 `mureka` 归零。

**一句话回答：本包的核心结构如果坏掉，是哪一步会亮红灯？**

→ 字段层（frontmatter / 引用 / 凭证）坏了 → `selfcheck.py` 亮红灯。
→ 交付形态层（zip 第一层 / 描述长度 / 入口类型）坏了 → `platformcheck.py --zip` 亮红灯。
→ 判据层（阈值改坏 / 检查项失效 / 误报回潮）坏了 → `mureka_check.mjs --selftest` 亮红灯（21 项）。
→ **有两类不会亮红灯**：歌词与风格的**内容质量**（意象是否成立、融合是否好听）与**平台生成效果**
——前者靠人读，后者要真跑生成试听（见第六节）。

---

## 六、未覆盖项 / 已知缺陷 / 待办

**未覆盖项**（下次检测优先消掉）：

1. **实际生成效果未验证**：本报告验的是文本结构与判据，两栏文本贴进 Mureka 后的实际命中率未测。
   需至少真跑三组（爵士 / 蓝调 / 民谣各一）试听评估。
2. **平台侧真实上传未做**：本包从未提交（① 开发完待提交），入口与类目建议（内容创作 > 文案）均未实证。
   ⚠️ 若被机器判「深度合成 > AI创作」：**先找客服人工复审，别改包**（release.config.json categoryNote 已记）。
3. **头像为占位图**：`avatars/joy2know-mureka-musician.png` 11.1 KB 占位图，配色待小乐拍板后换真图
   （换完重跑构建——技能图标虽不进 zip，但内嵌本技能的专家包会受影响）。
4. **官方 FAQ 的「人声性别偶发不符」问题**（无参考歌曲时也可能出现）已写进 mureka-controls.md，
   但触发条件与频率无法本地验证，只能以官方口径转述。

**已知弱项**（不阻断上架，记在案）：

- **W1 · 融合基色数量（≤3）与「首尾同源」靠模型执行**：语义类判据，脚本不查（部分实现已在门 2 表中注明）。
- **W2 · `description_zh` 116 字**：平台不查中文长度；信息量由 `description`（390 字）承担，无实际风险。

**待办**：

- 换真图 → 重跑构建 → 提交平台（走技能入口；类目按 categoryNote 的顺序处置）。
- 真跑三组生成试听，评估未覆盖项 1。

---

## 七、检测履历

| 日期 | 版本 | 状态 | 摘要（本轮测了什么、改了什么） |
|---|---|---|---|
| 2026-10-15 | 1.0.0 | ⚠️ 有条件通过 | **首次建包 + 首次检测**。新建技能「晓得·Mureka音乐人」：SKILL.md（双栏四层 / 六路路由 / 七条核心规则 / 13 条反模式）+ 4 references（实测控件 / 风格 token / 三体裁配方 / 治愈文风内核）+ `mureka_check.mjs`（结构校验 + 21 项内置自检）。**源目录自检全部通过**；`platformcheck --zip` 判 **Skill ✅**（description_en 966/1000）；**CLI 真跑抓到校验器两处误报**（no fade out 否定声明、按空行分段），当轮修复并补 3 条自检锚点；**反向验证**（改坏 L1 阈值 → 自检立刻 2 项红灯）确认不是橡皮章。description 压两轮（534 → 423 → 390 字）入系列区间。R6 跨包审计初报 `--selftest` 未文档化，按 R2 补进 §八后复扫归零；R1 候选不含本包。合规门禁通过 4 · 提示 1 · 失败 0。6 项未覆盖 + 2 项弱项。 |
