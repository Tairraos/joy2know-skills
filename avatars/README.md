# 图标统一管理

**所有图标只放这里，包里不放。** 打包时 `pnpm build` 会按名字自动找到并注入。

## 三类图标，三种放法

| 归属 | 放法 | 构建时去向 |
|---|---|---|
| **专家 / 专家团自身** | `avatars/<包名>.png` | 写到该包 `plugin.json` 里 `avatar` 字段指定的位置（如专家团的 `avatars/team.png`） |
| **专家团成员** | `avatars/<包名>/<文件名>.png` | 按**文件名**逐个写入包的 `avatars/` |
| **技能** | `avatars/<技能名>.png` | ①独立技能包**不进包**（官方技能包没有图标槽位，该图用于后台发布技能时上传）②被内嵌进专家包时复制为 `skills/<技能名>/icon.png` |

三条硬约束：

- **包名 / 技能名必须与 `plugin.json` 的 `name`、`SKILL.md` 的 `name` 逐字一致**，否则找不到。
- 专家团成员的文件名**必须与** `plugin.json` 的 `members[].avatar` 逐字对应。
- 专家 / 专家团**自身图标不能缺** —— 缺了上传会失败（构建会告警）。

## 规格

| 项 | 要求 |
|---|---|
| 尺寸 | **512 × 512**（正方形） |
| 格式 | PNG（推荐）或 JPG |
| 体积 | 单张 **≤ 500KB** |

尺寸或格式不符 → 打包时**告警**；体积超限 → 打包时**报错**。

## 全量清单（30 张 · 含道具方向）

> **统一形象**：同一个灰发小马尾毛毡小孩换装 —— 浅色背景、暖调、手持一件一眼看得懂职能的道具。
> 「道具方向」一列可直接当生图提示词用。**实时状态以 `python3 scripts/placeholders.py --check` 为准**，本表不写死。
>
> **状态（2026-09-17）**：30 张**全部已是真图**，无占位图残留；全部 512×512、单张 ≤500KB，规格体检零不合规。

### 一、技能图标 14 张 → `avatars/<技能名>.png`

| 文件名 | 中文名 | 功能 | 道具方向 |
|---|---|---|---|
| `joy2know-clarify.png` | 晓得·讲明白 | 结论先行、分层展开，该配图时主动配图 | 木教鞭 + 一块绿板书（板上是「主题 → 步骤 → 总结」） |
| `joy2know-design-tokens.png` | 晓得·设计解剖 | 设计参考解剖成 Token，再按 token 生成页面代码 | 「DESIGN」卫衣 + 手持平板（屏上色卡 / 描点） |
| `joy2know-storyboard.png` | 晓得·分镜工 | 白模视频切镜头、抽首帧，出提示词包 | 分镜格纸 + 铅笔（**别用场记板**，那是 cine-lead 的） |
| `joy2know-character.png` | 晓得·角色档案 | 角色卡 + 锚点短语锁定跨图一致性 | 角色立卡（正 / 侧两张同一人）+ 档案夹 |
| `joy2know-asset-ledger.png` | 晓得·素材台账 | 素材建可检索台账，按创作意图找图 | 翻开的台账本 + 一排带色标签的素材缩略卡 |
| `joy2know-codebase.png` | 晓得·代码考古 | 陌生仓库半小时出架构、入口、风险 | 探险帽 + 笔记本电脑（**无放大镜** —— 这是与下一行 `code-scholar` 唯一的区分点） |
| `joy2know-logdetective.png` | 晓得·日志侦探 | 日志聚成错误模式、时间线、根因假设 | 放大镜 + 一台屏幕显示日志折线的显示器（现图） |
| `joy2know-errorfix.png` | 晓得·报错翻译官 | 报错翻成人话 + 修复步骤 | 铅笔 + 夹纸板（板上红字报错划掉、下写人话）（现图） |
| `joy2know-cmdforge.png` | 晓得·命令制造局 | 自然语言 → 正则 / 命令 / SQL | 铁匠围裙 + 铁锤敲铁砧，铁砧上压着一条命令行 |
| `joy2know-dashboard.png` | 晓得·一页看懂 | Excel → 可交互单文件 HTML 看板 | 一块竖屏，屏上柱状 + 折线 + 环形图 |
| `joy2know-deck.png` | 晓得·讲得清 | 长报告 → 15 页 PPT 结构 + 口播稿 | 翻页笔 + 一叠编号讲稿卡 |
| `joy2know-musician.png` | 晓得·音乐人 | Suno 高阶语法出歌曲包 | 小提琴（现图）。**与 cine-music 的木吉他要有区分** |
| `joy2know-conversation-digest.png` | 晓得·对话归纳 | 对话还原成「我问了什么 / 怎么答 / 产出哪些文件」 | 手持一张发光蓝色卡片（现图） |
| `joy2know-humanize.png` | 晓得·凡人腔调 | 只改命中处、其余逐字保留，门禁校验 | 红笔（校对笔）+ 改稿样张：机器腔那句划掉、旁写人话 |

### 二、专家 / 专家团自身 4 张 → `avatars/<包名>.png`

| 文件名 | 中文名（卡面主标题） | 功能 | 道具方向 |
|---|---|---|---|
| `joy2know-mr.png` | 晓得·表达条理与可视化专家 | 结论先行、分层展开，该配图配图、不该画忍住 | 米色西装 + 圆框眼镜（扶眼镜）。现图**没有手持道具**，要加可补一支笔或图板 |
| `joy2know-code-scholar.png` | 晓得·代码考古学家 | 架构地图 + 「哪里能动、哪里是雷区」 | 探险帽 + 卡其探险装 + 笔记本电脑 + **放大镜**（现图） |
| `joy2know-cine-team.png` | 晓得·AI 视频生产团队 | 六工位协作，把创意变成能开拍的分镜包 | 一手平板（流程表）+ 一手分工清单 + 腰间工具袋（现图） |
| `joy2know-polish-team.png` | 晓得·文案打磨团 | 先体检再分棒，把写好的稿子打磨到能交付 | 砂光块 / 抛光布 + 一页稿纸（左机器腔、右人话） |

### 三、专家团成员 12 张 → `avatars/<包名>/<文件名>.png`

**文件名必须与 `plugin.json` 的 `members[].avatar` 逐字对应。**

| 文件名 | 角色 | 所属团 / 分工 | 道具方向 |
|---|---|---|---|
| `cine-lead.png` | 雷导 | cine-team · 主理人 / 总导演 | 场记板 + 扩音器（现图） |
| `cine-narrative.png` | 诺拉 | cine-team · 编导 | 剧本本 + 铅笔（现图） |
| `cine-shot.png` | 尚恩 | cine-team · 分镜师 | 分镜本（格纸）+ 彩笔（现图） |
| `cine-prompt.png` | 珀西 | cine-team · 提示词工程师 | 提示词卡 + 发光键盘（现图） |
| `cine-consistency.png` | 柯拉 | cine-team · 一致性管理员 | 平板（两张同角色卡）+ 清单 + 腰间色卡（现图） |
| `cine-post.png` | 奥托 | cine-team · 后期顾问 | 平板（剪辑时间线）+ 耳机（现图） |
| `cine-music.png` | 小音 | cine-team · 音乐人 | 木吉他（现图） |
| `polish-lead.png` | 闻山 | polish-team · 主理人 / 总编审 | 复审印章 + 核查清单（现图） |
| `polish-clarity.png` | 林知 | polish-team · 条理编辑 | 积木 / 拼图块（只挪位置，不改措辞） |
| `polish-distill.png` | 简宁 | polish-team · 提炼编辑 | 剪刀 + 一沓稿纸（把长的剪短） |
| `polish-visual.png` | 方寸 | polish-team · 数据可视化编辑 | 平板显示图表（现图） |
| `polish-tone.png` | 苏白 | polish-team · 语言编辑 | 铅笔 + 写满批注的台词本（现图，道具方向与『只扫命中处』一致） |

> 技能图标**不进 zip**（官方技能包没有图标槽位），是后台发布技能时上传用的，缺了不影响打包。
> 放好同名文件、跑一次 `pnpm build` 即生效。

## 缺图了怎么办

```bash
python3 scripts/placeholders.py --check   # 缺哪些 · 哪些还是占位图 · 哪些已换成真图
python3 scripts/placeholders.py           # 补齐缺失的（绝不覆盖已有文件）
python3 scripts/placeholders.py --redo    # 重画占位图（你换好的真图不动）
python3 scripts/placeholders.py --plain   # 画纯图形占位，不印名字
```

**占位图长什么样**：512×512、几 KB，浅灰相框 + 太阳 + 山形，底部印「谁 · 待替换」——
比如 `polish-lead.png` 上写着「闻山 / 主理人·总编审 · 待替换」。
文件名只说得出 `polish-lead`，图上那句才说得清该画谁。

有真图了**直接覆盖同名文件**即可，不用改任何配置，换完跑一次 `pnpm build`。
脚本只补不覆盖，你换好的图不会被碰。

**「还剩几张没换」是怎么算出来的**：脚本每次生成都会把该文件的 sha1 记进
`avatars/.placeholders.json`；`--check` 拿当前文件和台账逐张比对 ——
不靠文件名猜，也不怕你重命名或换后缀。条目不会因为替换而消失，
所以这个数字会一路跟着你做完最后一张。

## 检查

```bash
pnpm run list                              # 每个包的图标是否就位、内嵌技能图标是否齐
python3 scripts/placeholders.py --check    # 图标台账：缺图 / 占位图 / 真图
pnpm build                                 # 打包时逐个校验尺寸与体积
```

> `pnpm run list` 要带上 `run` —— 裸写 `pnpm list` 会被 pnpm 自带的「列依赖」命令截走。
