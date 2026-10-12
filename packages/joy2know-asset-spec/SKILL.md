---
name: joy2know-asset-spec
display_name: 晓得·资产字段规范
display_name_en: joy2know Asset Spec
description: >-
  WorkBuddy 资产包的字段与结构唯一口径：9 必填 frontmatter、plugin.json 全字段、
  15 类 categoryId、四条平台硬约束、三种体积上限、zip 第一层规则。
  附 fieldcheck.py 离线校验本地包或 zip，零依赖、不联网、不带凭证。
  触发词：SKILL.md 字段、frontmatter 必填、plugin.json、categoryId、专家类目、
  quickPrompts、defaultInitPrompt、包体积上限、zip 第一层、profession 还是 displayName、
  description_en 超长、上传类型选哪个、专家团结构。
  不适用于：内容怎么写、门禁与检测、驳回处置、平台状态。
description_zh: >-
  WorkBuddy 资产包的字段与结构唯一口径：9 必填 frontmatter、plugin.json 全字段、15 类 categoryId、
  四条平台硬约束、三种体积上限、卡片主标题取 profession 的实证坑，
  并附一个不联网、不带凭证的本地字段自检脚本。
description_en: >-
  The single source of truth for WorkBuddy asset package fields and structure: the nine mandatory
  SKILL.md frontmatter fields, every plugin.json field, agent frontmatter, the fifteen official
  categoryIds, four hard platform constraints (displayDescription length, defaultInitPrompt matching
  quickPrompts[0], exactly three tags and quickPrompts, bilingual pairing), three package size limits,
  and the zip layout rule. Documents the empirical finding that the card headline comes from
  profession rather than displayName. Ships fieldcheck.py, an offline field validator that runs
  against a local package directory or zip and needs no network or credentials.
category: capability
version: 1.0.0
author: 晓得乐
---

# 资产字段规范

**只回答一件事：字段叫什么、填什么值、什么会被打回。**
内容怎么写、打包流程、驳回处置都不在这里 —— 它们各自有技能。

> 口径来自平台官方文档 + 官方模板包解剖 + 本机实测。核验日期 **2026-09-13**，
> 四条硬约束与 categoryId 清单于 **2026-10-08** 复核。
> **平台规则会演进，正式提交前以后台实时提示为准。**

---

## 一、先记住这两条最容易翻车的

### 1. 官方字段表是缺的，要照示例代码块写

官方文档同一页里，**字段表与 frontmatter 示例代码块不一致**：`display_name`、`display_name_en`、
`category` 三个字段**表里没列、示例里有**。

实测缺失会**直接解析失败并点名报错**。

→ **照字段表写必失败，照示例写。** 这是本技能存在的第一理由。

### 2. 卡片上那个「名字」是 `profession`，不是 `displayName`

客户端实际渲染：**主标题 = `profession`，副标题 / 作者位 = `displayName`**。

这与官方文档「displayName 是市场展示名称」的说法**相反**（客户端截图实证）。

想让卡片顶着「XX 专家」这样的职业名，话就要写进 `profession`。
`displayName` 是**花名位** —— 可放人名，也可放品牌署名。**弄反了要重新提交审核。**

> 官方另有一句「Team 型 `profession` 须与 `displayName` 一致」，**实测不强制**。
> 万一哪天上传被卡，先把两者改成同一个值试。

---

## 二、技能包（Skill）

### 结构（zip 第一层必须是包目录本身）

```
<包名>/
├── SKILL.md            ← 必需。根级，不能藏在子目录
├── references/         ← 可选。按需加载的深度知识
├── scripts/            ← 可选。可执行脚本
└── templates/          ← 可选。模板文件
```

⚠️ **包根一级子目录仅允许 `references/` `scripts/` `templates/`。**

### SKILL.md frontmatter —— 9 个必填

```yaml
---
name: kebab-case-name          # 仅小写字母、数字、连字符；须与目录名一致
display_name: 中文展示名         # ★ 官方字段表未列，缺了报解析失败
display_name_en: English Name  # ★ 官方字段表未列，缺了报解析失败
description: 用途 + 触发词 + 不适用范围    # 这就是分发渠道
description_zh: 简短中文介绍
description_en: A brief English introduction   # ⚠️ ≤ 1000 字符，超了报解析失败
category: capability           # ★ 官方字段表未列，缺了报解析失败
version: 1.0.0
author: 署名
---
```

**可选字段**：`allowed-tools`（逗号分隔白名单）、`disable-model-invocation: true`（只能手动调用）、
`user-invocable: false`（隐藏菜单）。

**已知 `category` 取值**：`writing`（官方示例值）、`search`、`capability`。
取值不合规可在后台下拉里改，不影响功能。
⚠️ 这是**技能内部类型**，与发布时的**市场类目**是两回事 —— 市场类目不在包里。

### `description` 是产品本身

- 技能靠 `description` 匹配触发，**`name` 不参与触发**。改 `name` 对触发零影响，改 `description` 才是改产品。
- 触发词要写全（含同义口语），并明确写**不适用于**什么 —— 后者能防误触发。
- **长度跟系列齐平**：经验区间 240–390 字。新手容易一次写到 600+ 字（把「适用范围 + 不适用 + 触发词 + 边界」全塞进去），
  **超标近一倍会稀释触发权重**。写完横向量一遍，超了就压。
- **反直觉的取舍：`display_name` 越泛，`description` 越难压。**
  名字宽而能力窄时，边界全靠 description 承担，字数必然膨胀 —— **遇到这种落差，先改窄名字**，比在 description 里堆边界划算。

---

## 三、专家包（Expert）与专家团（Expert Team）

### 结构

```
<包名>/
├── .codebuddy-plugin/plugin.json   ← 必需。专家包入口
├── agents/<专家名>.md              ← 必需，agent 定义即系统提示词
├── skills/<技能名>/SKILL.md        ← 内嵌技能（由构建从源包复制）
├── avatars/expert.png              ← 头像 512×512 PNG
└── README.md
```

### plugin.json 全字段

```json
{
  "name": "包名",
  "version": "1.0.0",
  "description": "英文一句话定位",
  "author": { "name": "署名" },
  "agents": ["./agents/xxx.md"],
  "skills": ["./skills/xxx"],
  "expertType": "agent",
  "agentName": "xxx",
  "displayName":    { "en": "...", "zh": "..." },
  "profession":     { "en": "...", "zh": "..." },
  "displayDescription": { "en": "...", "zh": "..." },
  "avatar": "avatars/expert.png",
  "categoryId": "02-Engineering",
  "defaultInitPrompt": { "en": "...", "zh": "..." },
  "plugin": "包名",
  "tags": [ { "en": "...", "zh": "..." } ],
  "quickPrompts": [ { "en": "...", "zh": "..." } ]
}
```

`expertType: "team"` 时另有 `teamInfo`（`leadAgent` + `memberAgents[]`）与 `members[]`。
`members[]` 每项**只有五个字段**：`id` / `name` / `profession` / `avatar` / `role`。
**`agents[]` 的文件名去掉 `.md` 后须与 `members[].id` 严格一一对应。**

⚠️ **`name` 是平台侧不可变主键** —— 改名会被驳回。已提交的包一律别改名。

### 平台硬约束（不满足会被打回）

| 约束 | 口径 |
|---|---|
| `displayDescription.zh` | **40–50 汉字**（官方口径，模板自己超标，自检按官方） |
| `defaultInitPrompt` | 必须与 `quickPrompts[0]` **逐字一致** |
| `tags` / `quickPrompts` | 固定各 **3 个** |
| `displayName` / `profession` / `displayDescription` | **必须中英成对** |
| `categoryId` | 必须命中官方 15 类（见下），专家与专家团**共用同一份清单** |
| `avatar` | 必须是 `avatars/` 下的相对路径，且该文件为合法 PNG 512×512 / ≤500KB |
| `plugin` | 与 `name` 一致；`name` 与目录名一致 |

### `categoryId` 官方 15 类（`01`~`15`）

| | | | |
|---|---|---|---|
| `01-ProductDesign` 产品设计 | `02-Engineering` 技术工程 | `03-GameSpatial` 游戏空间 | `04-DataAI` 数据智能 |
| `05-MarketingGrowth` 营销增长 | `06-ContentCreative` 内容创作 | `07-SalesCommerce` 销售商务 | `08-FinanceInvestment` 金融投资 |
| `09-OperationsHR` 运营人力 | `10-ProjectQuality` 项目质量 | `11-SecurityCompliance` 法务安全 | `12-IndustryConsultant` 行业顾问 |
| `13-TencentZone` 腾讯专家 | `14-WorldWise` 全球发展 | `15-Education` 教育 | |

⚠️ **不存在 `00-ExpertTeam` 这类「专家团专属分类」。** 曾填进去被平台直接打回。
**专家团页面本身没有分类表**（清单在专家页，全平台共用）—— 找不到不等于不用管；两个团选同一类目是允许的。

### agent frontmatter

```yaml
---
name: xxx                    # 单专家须与 plugin.json 的 agentName 一致；团成员须等于 members[].id
description: 一句话说明
displayName:  { en: "...", zh: "..." }
profession:   { en: "...", zh: "..." }
maxTurns: 100
skills: [xxx]
---
```

**`maxTurns` 的配比是有意义的机制约束**：专家团里主理人给大（如 150）、成员给小（如 30）——
成员轮次少，就不会越权乱跑。

### 专家团三个专属要点

1. **根目录要同时放 `settings.json` 和 `setting.json`**（内容一致，一行 `{ "agent": "主理人name" }`）。
   平台校验器**实查 `settings.json`**，而官方模板用的是**无 s 的** —— 官方自己不一致，**两个都放最稳**。
2. **主理人的 agent 文件名必须带团前缀**（如 `xxx-lead`），不可用通用 `team-lead`。
3. 专家团**无独立发布入口**（与专家共用「发布管理 → 专家」页，平台读 `expertType: "team"`）。
   成员**不能单独开场**、**不能自嵌技能**。

---

## 四、体积上限

| 对象 | 上限 | 谁会真的撑爆包 |
|---|---|---|
| 技能包 | **3 MB** | 二进制资源 |
| 专家 / 专家团包 | **20 MB** | 头像图片 |
| 单张头像 | **500 KB / 512×512** | — |

纯文本 + 合规头像的完整包通常只有 100–600 KB。
⚠️ **连锁效应**：一个**技能**图标超限，会让**所有内嵌它的专家包**打包失败
（图标会复制成 `skills/<技能名>/icon.png` 一起受 500KB 校验）。
**尺寸不符只告警，体积超限才失败。**

⚠️ **zip 第一层必须是包目录**，不能是包目录里的内容。

---

## 五、上传类型必须与包类型一致

平台**按「类型」挑校验器**：

| 类型 | 校验器找什么 |
|---|---|
| Skill | `<包名>/SKILL.md` |
| Expert | `<包名>/.codebuddy-plugin/plugin.json` |
| Connector | `connector-meta.json` +（`mcp.json` \| `cli.json`） |

专家包的 SKILL.md 内嵌在 `skills/<技能名>/`，**按技能口径查永远查不到根级 SKILL.md**，
于是报「未找到 SKILL.md，请确保该路径文件存在」。

⚠️ **100% 是入口选错，不是包坏了。** 先换上传类型，别改包。

---

## 六、自检脚本

本技能自带 `scripts/fieldcheck.py`，**不联网、不带凭证、零第三方依赖**。

```bash
# 查本地包目录（技能包或专家包都能查，它自己识别）
python3 scripts/fieldcheck.py --dir path/to/包目录

# 查 zip 产物（一次一个）
python3 scripts/fieldcheck.py --zip dist/包名-v1.0.0.zip

# 自检：反向验证这个校验器本身有没有判别力
python3 scripts/fieldcheck.py --selftest
```

**退出码**：0 = 全过；1 = 有硬缺陷；2 = 用法错或认不出包类型。
「什么都没查出来」会**报错并返回非 0** —— 不给绿，因为认不出包比报错危险得多。

### ⚠️ `--selftest` 不是走过场，它抓出过 3 个真 bug

自检里有一组**篡改判据本身**的用例：把类目清单改窄、把长度上限放宽、
从必填清单里拿掉一项 —— 断言目标文案必须跟着翻转。
**没有这组，判据可能压根没在查那个东西，而基线照样全绿。**

实测在开发这个脚本时，自检先后抓出三个真缺陷：

| 缺陷 | 症状 |
|---|---|
| `lstrip("./")` 误伤 | `.codebuddy-plugin/x` 被剥成 `codebuddy-plugin/x` |
| 无条件补 `.md` 后缀 | 真实包里出现「agents 引用找不到」的假红灯 |
| zip 目录条目未分离 | 正确的 zip 被判成「第一层有 3 个并列条目」 |

完整留痕见 @references/validator-pitfalls.md（九条失效形态，含「基线全绿 ≠ 判据正确」）。
⚠️ references 是**按需加载**的 —— 正文里只用普通文字提到它，模型不会去读；必须写 `@references/<文件名>`。

⚠️ **基线全绿不等于判据正确** —— 它只能证明「没有样本触到它」。
实测就有一版判据把「专家包允许 `assets/`」错写成违规，
而 28 个已上架包**基线照样全绿**（没有一个在用 `assets/`）。
**改判据后必须跑 `--selftest` + 造正反样本。**

---

## 七、包根子目录白名单：技能包与专家包**不同**

⚠️ **这两份清单不一样，别合并成一份**：

| | 技能包 | 专家 / 专家团包 |
|---|---|---|
| 允许 | `references/` `scripts/` `templates/` | 以上 **+ `agents/` `avatars/` `assets/` `.codebuddy-plugin/`** |
| 说明 | 平台只认这三个 | **实测允许 `assets/`**（有在架包这么用），比技能包宽松 |

把技能包口径错套到专家包上，会让一个合法的专家包被判违规。

---

## 八、本技能的边界

- **只管字段与结构**。内容怎么写 → 「技能包组装」；打包与门禁 → 「资产包门禁」；
  驳回怎么处置 → 「发布与驳回」；平台状态怎么读 → 「资产状态追踪」。
- **平台规则会变**。本技能核验日期写在开头，正式提交前以后台实时提示为准。
  遇到与本文件不符的实测结果，**以实测为准并更新本文件** —— 口径漂移比缺一条更贵。
