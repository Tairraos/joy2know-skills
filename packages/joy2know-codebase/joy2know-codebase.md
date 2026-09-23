# 发布前检测报告 · 晓得·代码考古（joy2know-codebase）

> **本文件是开发期文档，不进 zip**（构建时自动排除）；但**要进 git**。
> 规范见仓库根 `AGENT.md` 第 3–4 节。**下次检测先读本文件**，只重测有变化的部分与「未覆盖项」。
>
> **口径说明**：本报告每条结论对应一次**真实运行**（命令 + 样本 + 输出要点）。
> 脚本实测跑在 `/tmp/j2k-check/codebase/joy2know-codebase/` 的副本上（`packages/` 内不跑 Python，避免生成 `__pycache__`）；
> 样本仓库真造在 `/tmp/j2k-check/codebase/sample-repos/`（多语言、含真实噪音 node_modules/dist/vendor/锁文件/__pycache__、超大 JSON、二进制、中文路径、深层嵌套、权限拒绝子目录）。
> 受管解释器：`~/.workbuddy/binaries/python/envs/default/bin/python`（Python 3.13.12，PyYAML 6.0.3）。

- **包名**：joy2know-codebase
- **类型**：技能
- **对应版本**：1.2.0
- **检测状态**：⚠️ 有条件通过
- **最后检测**：2026-09-23
- **检测方式**：功能测试 + 完整性对照 + 合理性检查 + 反向验证

---

## 一、包内文件（从磁盘枚举，不手写）

```
    11003  SKILL.md                          技能正文（9 必填 frontmatter 齐全，version 1.1.0）
    14073  scripts/repo_scan.py              唯一入口：启发式扫描 + 打分 + 依赖解析 + 目录树
     4038  joy2know-codebase.md              本文件（开发期文档，不进 zip）
```

**零第三方依赖核对**：`repo_scan.py` 仅 `import argparse / json / os / re / sys` 与 `from collections import ...`，
经 AST 遍历确认**无任何非标准库 import**（stdlib 白名单命中全部，第三方列表为空）。SKILL.md 未显式写「零第三方依赖」字样，
但脚本 docstring 声明「零第三方依赖，纯标准库」，声明成立。**结论：零第三方依赖守住。**

包体（不含本报告）约 **25.0 KB**，远低于技能包 3 MB 上限。`packages/` 内已确认无 `__pycache__` / `*.pyc` 残留（隐形炸弹为 0）。

---

## 二、能力清单与验证结果

样本构造：在 `/tmp` 真造贴近真实的仓库，而非理想样本——
`real-app`（node/python/go/rust/php 多生态，含 node_modules/dist/vendor/__pycache__/package-lock.json 等真实噪音、2.4MB 固件 JSON、logo.png 二进制、中文目录、deep/nested/.../config.php 深层嵌套）、`py-only`、`java-app`、`dart-app`（不支持语言）、`empty`/`single`/`noperm` 边界仓。

> 「结果」取值：`✅ 通过` / `❌ 失败` / `⚠️ 部分` / `未覆盖`。每格均有真实命令 + 输出要点。

| 能力 / 待验证项 | 验证方式（命令与样本） | 结果 | 证据要点 |
|---|---|---|---|
| `--help` 可读、参数与文档一致 | `repo_scan.py --help` | ✅ | 参数 `path` / `--max-files` / `--max-depth` / `--no-ref`；与 SKILL「`--max-files 20`」一致 |
| 主流程：扫描→输出「最重要 N 文件 + 依赖清单 + 目录树」 | `repo_scan.py real-app --max-files 20` | ✅ | 32 文件（已排噪）；清单 20 项含「得分 + 命中原因」；依赖 6 生态；目录树标 src/(13 文件) 等 |
| 打分①入口文件名命中 | real-app：`src/index.js`/`app.py` +30，`config.php` +18 | ✅ | 入口信号 bonus 正确（深层 config 因在 ENTRY_NAMES 仍 +18） |
| 打分②被引用次数 | real-app：`userRoute`「被引用约 2 次 +6」；`--no-ref` 时该维度消失 | ✅ | 引用统计生效；降级正确（见行 28） |
| 打分③层级浅优先 | real-app：浅层 +分；深层 `config.php` 仍 +18（兼入口） | ✅ | 深度维度正确 |
| 打分④规模适中 / 过小 / 超大 | 适中 +10；`小文件.py` 过小 −6；`big_data.json`(2.4M) 超大 −4 | ✅ | 三档均生效 |
| 打分⑤核心关键字命中 | `routes`/`controllers`/`models`/`service`/`handler`/`config` +12 | ✅ | 关键字命中正确 |
| 噪音目录跳过（node_modules/dist/vendor/__pycache__/.git） | real-app 32 文件不含上述；**反向**：删 NOISE_DIRS 的 node_modules → 泄漏 4 个 | ✅+反向 | 正常跳过；篡改后红灯（见 §五） |
| 噪音文件跳过（锁文件/min.js/.map） | real-app 含 `package-lock.json`，未计入 32 | ✅ | 锁文件正确排除 |
| 依赖解析 node | real-app `[node]` 7 项正确 | ✅ | express/react/lodash/sequelize/eslint/jest/typescript |
| 依赖解析 python（requirements.txt） | `py-only` `[python]` 4 项正确 | ✅ | flask/requests/SQLAlchemy/pytest |
| 依赖解析 python（pyproject.toml） | real-app `[python]` 错输出 `dependencies/name/version` | ❌ | **缺陷 D1** |
| 同生态覆盖丢依赖 | real-app 同时含 requirements+pyproject → flask 等 4 项被覆盖丢失 | ❌ | **缺陷 D1**（覆盖 bug） |
| 依赖解析 go | real-app `[go]` 2 项正确 | ✅ | gin/gorm |
| 依赖解析 rust | real-app `[rust]` 2 项正确 | ✅ | serde/tokio |
| 依赖解析 java（pom.xml） | `java-app` `[java-maven]` 2 项正确 | ✅ | spring-boot-starter/mybatis |
| 依赖解析 php（composer.json） | real-app `[php]` 3 项正确 | ✅ | php/monolog/phpunit |
| 依赖解析 ruby（Gemfile） | real-app `[ruby]` 错输出 `gem/source` | ❌ | **缺陷 D2** |
| 目录职责树 + `--max-depth` | `--max-depth 2` / 默认 3 | ✅ | 实测 `--max-depth 2` 仅展到 2 层 |
| 边界：空目录 | `empty` | ✅ | `仓库为空或所有文件都被噪音规则跳过。` exit 1，不崩 |
| 边界：单文件 | `single/only.py` | ✅ | 1 文件、无依赖清单 |
| 边界：超大文件（>2MB） | `big_data.json`(2.4M) | ✅ | 列入末位（得分 −4「超大文件降权」），不崩 |
| 边界：二进制文件 | `logo.png` | ✅ | 列入清单（不在 CODE_EXT，不读引用） |
| 边界：无权限目录 | `noperm`（权限拒绝子目录） | ✅ | exit 0，无 Traceback，仅列可读文件 |
| 边界：中文路径 | `中文目录/中文模块.py` | ✅ | 目录树含 `中文目录/`，不崩 |
| 边界：深层嵌套 | `deep/nested/dir/structure/here/config.php` | ✅ | 排名 11，打分正常 |
| 边界：路径不存在 | `does-not-exist` | ✅ | `错误：目录不存在 -> ...` exit 2 |
| 降级：`--no-ref`（超大仓库） | real-app `--no-ref` | ✅ | 正常运行，引用维度消失（app.js 56→50） |
| 降级：`--max-files` 减小 | `--max-files 5` | ✅ | 清单仅 5 项 |
| 降级：不支持语言 → 依赖标「未识别」 | `dart-app`（pubspec.yaml） | ✅ | `未识别到受支持的依赖清单文件` —— 与 SKILL 第九节一致 |
| SKILL frontmatter 9 必填 + YAML + 无凭证 | `selfcheck.py packages/joy2know-codebase` | ✅ | 7 通过 / 0 失败；9 字段齐全、YAML 解析通过、无硬编码凭证 |
| 零第三方依赖 | AST 扫描 imports | ✅ | 仅 argparse/json/os/re/sys/collections，无第三方 |

---

## 三、门 2 · 完整性对照（文档承诺 → 实现）

| 文档承诺（摘原文） | 实现位置 | 有 / 无 / 部分 | 备注 |
|---|---|---|---|
| 「跑 `scripts/repo_scan.py <仓库路径> --max-files 20`，得到「最重要的 20 个文件」「依赖清单」「目录职责树」」 | `main()` / `print_report()` | **有** | 实测三样齐全 |
| 规则 2 五个打分维度（①入口文件名命中 ②被引用次数 ③目录层级越浅 ④文件规模适中 200B~60KB ⑤路径/文件名含核心关键字） | `score_files()` | **有** | 五维输出均见于「得分 … · 原因」 |
| 排除项：锁文件、构建产物、node_modules、dist、vendor、超大固件 JSON | `NOISE_DIRS` / `NOISE_FILE_RE` / `HUGE_BYTES` | **部分** | node_modules/dist/vendor/锁文件(.lock/min/.map) 正确跳过；**超大文件仅降权(−8)仍列入清单，未完全「跳过」**（见 D4 / 未覆盖项 3） |
| 第九节「脚本不支持某语言 → 依赖项标『未识别，请人工确认』」 | `parse_dependencies()` else 分支 | **有** | dart-app 实测命中 |
| 第九节「仓库极大扫不动 → 加 `--no-ref` 跳过引用统计」 | `--no-ref` | **有** | 实测 |
| 第九节「减小 `--max-files`」 | `--max-files` | **有** | 实测 |
| 「依赖解析覆盖 node/python/go/rust/java/php/ruby」 | `DEP_FILES` | **部分** | node/go/rust/java/php/requirements.txt 正确；**pyproject.toml 错、ruby(Gemfile) 错、且同生态覆盖丢依赖**（见 D1/D2） |
| 规则 1「脚本不可用 → 用 Glob 找 main\|app…，人工取前 20 个」 | 无脚本实现（AI 降级） | **部分** | 属 AI 行为；脚本无该降级开关，无法脚本验证 → 未覆盖项 1 |
| 规则 3 风险分级 / 规则 4 不把推测当事实 / 规则 5 密钥不回显 | 无脚本实现（AI 行为） | **部分** | 属对话层；脚本不产出这些 → 未覆盖项 1 |
| 「不读完整个仓库…绝不打印仓库全文」 | `walk_repo` 不读正文 / `print_report` 只输出清单 | **有** | 实测仅输出清单与得分，无任何文件正文 |
| 入口文件判定（主流程） | `ENTRY_NAMES` | **有** | main/index/app/server 等命中 +分 |

---

## 四、门 3 · 合理性结论

- **规则是否自洽**：✅ 无互相打架。五条打分维度同向（入口/引用/层级/规模/关键字都加分）；噪音规则与「排除项」一致；`--no-ref` 与「超大仓库」场景对应。
- **推断是否标注为推断**：⚠️ 脚本本身是启发式工具，已逐文件标注「得分 … · 原因」（如「被引用约 2 次」「层级浅」），透明度好；但脚本**不区分「已确认 vs 推断」**——这是设计使然（脚本只做扫描，判断与标注留给 AI 按规则 4 完成）。属预期分工，非缺陷。
- **错误提示是否可指导下一步**：✅ 目录不存在明确点名路径并 exit 2；空仓库给「仓库为空或所有文件都被噪音规则跳过」提示；超大文件不崩、不误建输出。
- **边界是否优雅**：✅ 空/单文件/不存在/无权限/中文/深层/超大/二进制均不崩（见 §二 多行）。权限拒绝的子目录被 `os.walk` 静默忽略（未报错但主流程继续）——可接受，不属崩溃。
- **零依赖是否守住**：✅ AST 确认仅标准库；外部命令无（脚本纯本地磁盘统计）。
- **值来源是否可追溯**：✅ 打分来自脚本对本地磁盘的统计计算，依赖来自文件解析，均无外部注入值；超大文件大小计入总体积但内容不读，来源清晰。

---

## 五、门 4 · 测试真实性自评（防放水）

- [x] 1. 只跑 happy path，没跑边界 —— **否**：§二 含 27 组边界/降级/反向（空目录/单文件/超大/二进制/无权限/中文/深层/不存在 + 8 生态 + `--no-ref`/`--max-files`/`--max-depth`）
- [x] 2. 只看「没报错」，没核对输出内容 —— **否**：逐条核了清单条数（32）、得分取值、依赖正确性（**实测抓出 pyproject/ruby 解析错误**）、目录树层级
- [x] 3. 把「文档写了」当成「已验证」 —— **否**：SKILL 写「依赖解析覆盖 8 生态」，实测发现 pyproject.toml 与 ruby(Gemfile) 两项解析错误，已记缺陷
- [x] 4. 自造理想样本 —— **否**：`real-app` 含真实噪音（node_modules/dist/vendor/__pycache__/锁文件）、多生态真实依赖清单、2.4MB 固件 JSON、二进制 logo.png，贴近真实项目
- [x] 5. 跳过失败项、不记录 —— **否**：D1/D2/D3/D4 全部记录于 §六
- [x] 6. 修完只测修好的那条，没跑回归 —— **不适用**：本轮不改包内任何文件，无「修」
- [x] 7. 造错样本只造了会被抓的那种 —— **否**：2 组反向验证（删 author → selfcheck 红灯；删 node_modules 噪音 → 泄漏红灯）+ 2 组**正面**样本（clean real-app 32 文件无 node_modules 不乱报；clean 包 selfcheck 7 通过）

**反向验证记录**

| # | 造了什么错样本 | 预期 | 实际 |
|---|---|---|---|
| 1 | 副本 `SKILL.md` 删 `author` 字段 | `selfcheck` 报缺字段 | ✅ `[XX] frontmatter 缺字段: author`（另触发 `author 为空`，共 2 项问题） |
| 2 | 副本 `repo_scan.py` 删 `NOISE_DIRS` 的 `node_modules` | 噪音跳过失效 → node_modules 文件泄漏 | ✅ 泄漏 4 处（3 个文件 + 目录树 `node_modules/ (3 文件)`）—— §二 行 8 的红灯被点亮 |
| 3 | 正面：clean `real-app` 扫描 | 不应误报 node_modules | ✅ 32 文件无 node_modules（无假阳性） |
| 4 | 正面：clean 包 `selfcheck` | 应通过 | ✅ 7 通过 / 0 失败 |

**一句话回答：本包的核心能力如果坏掉，是哪一步会亮红灯？**
→ 打分维度算错会在 §二 行 3–7 出现**取值不符**（非只报错）；噪音跳过失效会在 §二 行 8 **泄漏 node_modules**（已反向验证）；依赖解析错会在 §二 行 11/12/13/17 **暴露 pyproject/ruby 错误**（已抓到）。唯一不会亮红灯处：超大文件仅「降权」未「彻底跳过」（行 3 备注 / D4）——若 SKILL 要求彻底跳过，当前实现不报错而是照列。

---

## 六、未覆盖项 / 已知缺陷 / 待办

**未覆盖项**（下次检测优先消掉这些）：

1. **AI 行为层未测**：规则 1 脚本不可用降级（用 Glob 人工取前 20）、规则 3 风险分级、规则 4 不把推测当事实、规则 5 密钥不回显、第六/八节输出骨架与完成判据——均属对话层，无法用脚本验证，本轮未跑端到端对话。
2. **`description`「不适用于」三场景未实测**：小 bug 改动 / 自动重构 / 二进制仓库——触发层行为，本地无触发环境。
3. **超大文件「彻底跳过」语义未与 SKILL 对齐**：脚本仅降权仍列入，SKILL 写「自动跳过」，待维护者确认期望（见 D4）。
4. **真实大型仓库规模化未测**：样本仅 32 文件，未测几千文件下的耗时/内存，及 `--no-ref` 在真实大仓的表现。
5. **更多语言/框架入口识别未穷举**：仅测 node/python/go/rust/java/php/ruby/dart；未测 kotlin(.kt 在 CODE_EXT 但无 DEP)/scala/swift/c# 等的真实依赖清单。
6. **跨平台权限场景未测**：仅 macOS 下权限拒绝，未测 Linux/Windows。

**已知缺陷**（**2026-09-23 已修** —— 统一修复记录见本节末）：

- **缺陷 D1（中）· pyproject.toml 解析错 + 同生态覆盖丢依赖**：① `pyproject.toml` 正则 `^\s*([\w.\-]+)\s*[=~<>]` 把 `[project]` 表键 `name`/`version`/`dependencies` 当成依赖名输出；② `deps[eco] = sorted(set(names))` 为**覆盖赋值**，当 `requirements.txt` 与 `pyproject.toml` 同属 `python` 生态时，后者覆盖前者。实测 `real-app` 中 `flask`/`requests`/`SQLAlchemy`/`pytest` **全部静默丢失**，只剩错误的 `name`/`version`/`dependencies`。建议：`pyproject.toml` 仅取 `[project.dependencies]` 数组；`deps[eco]` 改为并集追加。
- **缺陷 D2（中）· Gemfile（ruby）解析错**：`Gemfile` 落入 `else` 朴素分支按空格取首词，输出 `gem`/`source` 而非真实依赖 `rails`/`pg`。建议：为 `Gemfile` 加 `gem 'name'` 专用解析。
- **缺陷 D3（轻）· DeprecationWarning**：Python 3.13 下 `re.split(pattern, line, 1)` 位置参数 `maxsplit` 弃用，stderr 打印告警（非致命）。建议改 `re.split(pattern, line, maxsplit=1)`。
- **缺陷 D4（轻/观察）· 超大文件未完全跳过**：SKILL「噪音文件」表列「超大固件 JSON」写「自动跳过」，脚本仅降权(−8)仍列入清单（降权排末位）；与脚本 docstring「不计入打分」一致，但与 SKILL 措辞有出入。建议：若需彻底跳过，在 `walk_repo` 排除 `> HUGE_BYTES` 文件；否则统一 SKILL 措辞为「降权」。

> **严重度判定说明**：以上缺陷**不影响主流程扫描**（文件打分、目录树、噪音跳过、node/go/rust/java/php/requirements.txt 依赖均正确），工具不崩、核心交付物（最重要文件清单）准确——故判为「非硬缺陷」，状态取 `⚠️ 有条件通过`。
> 若维护者认为「声明支持却解析错误的生态（pyproject/ruby）+ 同生态静默丢依赖」属**硬缺陷**，应改判 `❌` 并优先修 D1。

**【已修 2026-09-23 · 版本 1.1.0 → 1.2.0】修法与验收**：

- **D1**：新增 `_pyproject_deps()` —— 优先用标准库 `tomllib` 按 **TOML 结构**取依赖
  （PEP 621 `[project].dependencies` 与 `optional-dependencies`、PEP 735 `[dependency-groups]`、
  Poetry `[tool.poetry*.dependencies]`），**不再用 `^\s*key\s*=` 正则把表键当依赖**；
  取不到 tomllib 时退回「只从 dependencies 数组里取字符串」的正则。
  同时把 `deps[eco] = sorted(set(names))` 改为 `deps.setdefault(eco, set()).update(names)`
  —— **合并而非覆盖**，同生态的两个文件（`requirements.txt` + `pyproject.toml`）不再互相顶掉。
- **D2**：为 `Gemfile` 加专用分支，按 `gem "name"` 取包名（原实现落 `else` 分支按空格取首词）。
- **D3**：`re.split(..., maxsplit=1)` 全部改为关键字形式；**并全仓扫描确认无同类残留**。
- **D4**：`SKILL.md` §一 表格把「超大文件」拆成单独一行，措辞与实现对齐
  （**降权 −8、排清单末位**，不是「自动跳过」）。

**验收（真跑，改前 / 改后对照）**：

| 用例 | 改前（git 原始版本实测） | 改后 |
|---|---|---|
| `pyproject.toml` + `requirements.txt` 同仓 | `[python] 共 5 项：dependencies, name, pydantic, python, version` —— 表键被当依赖，且 requirements 的 flask / requests / SQLAlchemy **全丢** | `[python] 共 6 项：SQLAlchemy, fastapi, flask, httpx, pydantic, requests` ✅ |
| `Gemfile` | `[ruby] 共 2 项：gem, source` | `[ruby] 共 2 项：pg, rails` ✅ |
| `-W error::DeprecationWarning` | 崩（`maxsplit` 位置参数弃用） | 不崩 ✅ |
| 回归：node / rust / php / go 四样本 | — | **逐字未变** ✅ |

**反向验证**：同一套用例对 **git 原始版本**运行，输出即上表「改前」列（D1/D2/D3 三条均被复现），
证明用例确实抓得住这三个缺陷。

**待办**（D1–D4 已于 2026-09-23 修复，见上）：

- 优先修 **D1**（影响 python 项目技术栈准确性，且静默丢依赖最危险）、其次 D2。
- D3 顺手改（`maxsplit=1`）。
- 修完必须跑回归：§二 行 11/12/13/17 重跑；并对 D1 补反向（造同时含 requirements+pyproject 的仓库，确认两者依赖都出现且正确）、对 D2 补反向（造 Gemfile，确认输出 rails/pg）。

---

## 七、检测履历

| 日期 | 版本 | 状态 | 摘要（本轮测了什么、改了什么） |
|---|---|---|---|
| 2026-09-23 | 1.1.0 | ⚠️ 有条件通过 | 首次成文（覆写骨架）。用受管 Python 3.13 在 /tmp 副本真跑：主流程扫真实多语言仓 real-app（32 文件，五维打分/噪音跳过/目录树正确）；8 生态依赖解析中 node/go/rust/java/php/requirements.txt 正确，**抓出 pyproject.toml 错 + 同生态覆盖丢依赖(D1)、Gemfile 错(D2)、DeprecationWarning(D3)、超大文件未彻底跳过(D4)**；27 组边界/降级/反向（空目录/单文件/超大/二进制/无权限/中文/深层/不存在 + --no-ref/--max-files/--max-depth + 不支持语言 dart）；4 组反向验证（删 author→selfcheck 红灯、删 node_modules 噪音→泄漏红灯、clean 样本不乱报）。selfcheck 7 通过/0 失败；AST 确认零第三方依赖。未改包内任何文件。未覆盖项 6 条（AI 行为层 + 触发边界 + 规模化等）。 |
| 2026-09-23 | 1.2.0 | ⚠️ 有条件通过 | **修复轮**：D1 改用标准库 `tomllib` 按 TOML 结构取依赖 + 同生态**合并**（不再覆盖丢依赖）；D2 加 `Gemfile` 专用解析；D3 `maxsplit=` 关键字化（并全仓扫描无残留）；D4 `SKILL.md` 措辞与实现对齐（超大文件=降权，非跳过）。验收：`app` 样本改前 `python: dependencies,name,pydantic,python,version` → 改后 `SQLAlchemy,fastapi,flask,httpx,pydantic,requests`；`ruby: gem,source` → `pg,rails`；`-W error::DeprecationWarning` 不再告警；node/rust/php/go 回归**逐字未变**。 |
