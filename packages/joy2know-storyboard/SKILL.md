---
name: joy2know-storyboard
display_name: 晓得·分镜工
display_name_en: joy2know Storyboard
description: >-
  把一段白模（灰模）动画视频自动切成镜头、抽每镜首帧，并按目标视频生成模型（Seedance / Runway / Kling / Sora 等）
  的提示词语法产出可直接使用的分镜提示词包，解决「手工写分镜、镜头不连贯、角色一致性反复救火、首帧对不上、时长超模型上限」的卡点。
  触发词：分镜、切镜头、抽首帧、白模转提示词、视频生成提示词、分镜提示词包、按模型写 prompt、镜头切片、
  storyboard、shot split、first frame、video prompt、Seedance prompt、Runway prompt、Kling prompt。
  不适用于：已有成品视频要二创剪辑（本技能只处理白模/灰模到生成提示词这一段）；纯文本脚本还没渲染成视频；
  只想要一句笼统的「帮我写个视频」而不提供任何参考画面。
description_zh: 把白模视频切成镜头、抽首帧，按目标模型语法产出分镜提示词包。
description_en: >-
  Take a blockout/greymesh animation video, auto-split it into shots, extract each shot's first frame, and
  generate a ready-to-use storyboard prompt pack written in the target video model's syntax (Seedance, Runway,
  Kling, Sora, etc.). It removes the manual pain of shot writing, character-consistency firefighting, mismatched
  first frames, and over-limit durations. Requires a rendered blockout video as input; not for editing finished
  footage or writing prompts with no visual reference.
category: capability
version: 1.2.0
author: 晓得乐
---

# 晓得 · 分镜工

> 把「一段白模视频」变成「按目标模型语法写好的分镜提示词包 + 每镜首帧图」。
> 切片与首帧交给脚本，提示词语法交给配置，你只需确认镜头与连续性。

## 一、先分清（不做这一步后面全错）

| 概念 | 判定标准 | 处理方式 |
|---|---|---|
| **白模 / 灰模** | 无材质、无灯光、纯色块或线框的渲染预览 | 本技能的输入，据此切镜与取首帧 |
| **镜头（shot）** | 一次连续拍摄，中间不切 | 切片的产物，一个镜头一份提示词 |
| **镜头切换点（cut）** | 画面场景变化超过阈值的那一帧 | 切片依据，由 `select='gt(scene,0.3)'` 检测 |
| **语义内容** | 谁、在哪、做什么——与模型无关 | 由你写，所有模型共用 |
| **提示词语法** | 各模型对运镜/时长/结构的写法——各不相同 | **不得硬编码**，按 `@references/model-syntax.md` 取模板 |

**最容易犯的错：** 把某一家的提示词语法写死进流程。模型半年一迭代，写死的语法立刻作废——所以语法必须活在配置文件里。

## 二、判定与路由

| 情形 | 判定信号 | 走哪条 |
|---|---|---|
| **A. 有白模 mp4** | 用户给了视频文件 | 完整流程：切片 → 抽首帧 → 选语法 → 出提示词包 |
| **B. 只有首帧图** | 没有视频，只有若干张图 | 跳过切片，直接按图写提示词（缺运镜时长，标「未提供」） |
| **C. 已有分镜片段** | 用户已切好镜头，只要提示词 | 只做「选语法 + 写提示词」，不重切 |
| **D. 只要语法模板** | 「先给我 Runway 的提示词格式」 | 走到第四节即停，不碰视频 |

**降级判定：** 单镜头短视频、用户明确说「随便切一刀就行」→ 走 A 的简化版：只抽首帧 + 出一条提示词，不做镜头连续性比对。

## 三、工作流

1. **先验 ffmpeg。** 运行脚本前先确认 `ffmpeg` 与 `ffprobe` 在 PATH；缺失按第六节降级并给安装提示。
2. **切片 + 抽首帧。** 执行 `python scripts/split_shots.py <视频路径> --output-dir shots --scene-thresh 0.3`。脚本产出：每个镜头的片段 `shot_001.mp4`、首帧 `shot_001_firstframe.png`、清单 `shots/manifest.json`。
3. **读清单。** 从 `manifest.json` 取每个镜头的起止时间、时长、首帧路径，作为写提示词的依据。
   **先看来源标记**：`duration_source` 为 `ffprobe` 时 `duration` 是实测值，可直接引用；
   为 `inferred` 时说明 ffprobe 没取到时长，`duration` 为 `null`、`duration_used` 是按切换点推断的切分依据 ——
   此时**不得把该时长当实测值写进提示词**，须标 `[推断]`（详见规则 6）。
4. **选目标模型语法。** 用户指定模型后，读 `@references/model-syntax.md` 取对应模板与**时长上限**；未指定时默认追问一次，给 Seedance 作默认。
5. **确认连续锚点。** 跨镜头时，角色外观、服装、场景用上一镜已锁定的锚点描述（连续性锁机制见同品牌的「晓得·角色档案」技能，本技能只负责把它接进分镜提示词）。
6. **写提示词包。** 每个镜头按模板填语义内容 + 运镜（术语见 `@references/shot-language.md`）+ 时长（≤ 上限），输出 `shots/prompts.md`。
7. **回报。** 列镜头数、各镜时长是否越限、哪些首帧需要人工核对，**以及哪些片段 `clip` 为 `null`**
   （`clip_error` 里写了失败原因）—— 片段缺失属于必须告知用户的事实，不得因为「首帧抽到了」就略过。

## 四、核心规则

**规则 1：ffmpeg 不存在，禁止假装能切（红线）**

- 触发条件：任何要调用切片/抽帧的步骤。
- 硬性动作：脚本启动先 `shutil.which('ffmpeg')` 与 `ffprobe`；**缺失必须立即报错并给出安装命令**，不得用占位文件糊弄。
- 正例：✓ 报 `ffmpeg 未找到：macOS 用 brew install ffmpeg，Ubuntu 用 apt install ffmpeg，Windows 用 scoop install ffmpeg`，并停止后续步骤。
- 反例：✗ 「已为你切好 5 个镜头」——实际什么都没做，用户 downstream 全崩。
- 降级路径：环境确实无法装 ffmpeg → 明确告知用户改为手动放首帧图，走 B 路径，脚本不参与。

**规则 2：语法从配置取，不得写死（红线）**

- 触发条件：写任何一条提示词正文。
- 硬性动作：模型语法**必须**来自 `@references/model-syntax.md` 的对应模板。本文件里**禁止**出现某一家的完整语法样板。
- 正例：✓ `目标模型 Runway → 取 model-syntax.md 的 [Runway] 模板，结构：镜头描述, 运镜, 时长, 风格尾缀`。
- 反例：✗ 在 SKILL.md 里把「Runway 要写 image motion: ...」整段硬编码——Sora 用户直接拿到错误格式。
- 降级路径：配置文件里没有用户说的模型 → 先标「未收录该模型语法」，按通用语义结构输出并提示补充配置。

**规则 3：首帧与镜头必须一一对应**

- 触发条件：产出首帧图与提示词时。
- 硬性动作：每个镜头的首帧文件名必须带同一序号（`shot_001_firstframe.png` ↔ `shot_001` 的提示词），**禁止**错配或混用。
- 正例：✓ 提示词里写明「首帧：shots/shot_003_firstframe.png」，与该镜片段同序号。
- 反例：✗ 第 3 镜的提示词贴了第 1 镜的首帧——生成出来角色位置对不上。
- 降级路径：某镜首帧抽取失败（黑屏/模糊）→ 该镜标「首帧未采信」，提示用户手补。

**规则 4：时长不得超过目标模型上限**

- 触发条件：填每条提示词的时长字段。
- 硬性动作：时长必须 ≤ `@references/model-syntax.md` 中该模型的 `max_duration`。超限**必须**提示并建议拆镜或截短。
- 正例：✓ 「本镜 6s，Runway 上限 10s，通过。」
- 反例：✗ 写了 16s 丢给上限 10s 的模型——直接报错浪费生成额度。
- 降级路径：单镜过长且不愿拆 → 明确标「超出上限，已建议拆分，未自动改动」。

**规则 5：运镜用标准术语，不写感受词**

- 触发条件：描述镜头运动时。
- 硬性动作：运镜与景别**必须**用 `@references/shot-language.md` 的中英术语，如 `push-in / 推`、`medium shot / 中景`。
- 正例：✓ 「camera: slow push-in; shot size: close-up」。
- 反例：✗ 「镜头很有张力地靠近」——模型读不懂「张力」。
- 降级路径：用户只给感受词 → 翻译为标准术语，标注「推断为 push-in」。

## 五、输出格式

**分镜提示词包（`shots/prompts.md`）骨架：**

```markdown
# 分镜提示词包 · 目标模型：<Runway>
> 首帧与片段见 shots/，清单见 shots/manifest.json

## shot_001
- 首帧：shots/shot_001_firstframe.png
- 时长：3s（上限 10s）
- 景别/运镜：close-up / slow push-in
- 锚点：pale blue chunky knit wool sweater（角色锁）
- 提示词：<按 model-syntax.md 的 Runway 模板全文>

## shot_002
...
```

**反模式禁止清单：**

| # | 反模式 | 为什么禁 |
|---|---|---|
| 1 | 把模型语法写死进 SKILL.md | 模型迭代即作废，这是本技能死穴 |
| 2 | 首帧与提示词序号错配 | 生成出来角色位置全乱 |
| 3 | 时长超模型上限还发出去 | 直接报错烧钱 |
| 4 | 运镜写感受词不写术语 | 模型无法执行 |
| 5 | 跨镜重复粘贴大段角色描述 | 长且互相干扰，应改用锚点 |
| 6 | ffmpeg 缺失仍谎称切好 | 下游全崩，最恶劣 |

## 六、防幻觉（硬约束，优先级最高）

**本节优先于以上所有格式与流程要求。**

1. **ffmpeg 在不在，据实说。** 检测到缺失就报缺失并给安装命令，禁止假装成功。
2. **镜头数、时长来自脚本输出。** 必须引用 `manifest.json` 的真实数值；禁止估「大概 5 个镜头」。
3. **目标模型未指定就说未指定。** 不默认替用户拍板某家模型；追问一次后给默认值并标注「默认 Seedance，请确认」。
4. **配置里没有的模型语法，标未收录。** 不凭记忆编一段「该模型格式」。
5. **三种来源分清：** 用户给定 / 脚本测得（附 `manifest.json` 字段）/ 我推断（标 [推断]）。
6. **首帧抽失败就标失败。** 不拿别的镜头的图顶替。

## 七、按需知识

只在遇到对应问题时读取：

- 各模型提示词语法对照、时长上限、配置式模板 → `@references/model-syntax.md`
- 景别 / 运镜标准中英术语与用法 → `@references/shot-language.md`

## 八、完成判据

**算做完：** `shots/` 下有每个镜头的片段与首帧、`manifest.json` 完整、每条提示词按目标模型语法写出且时长未越限、已回报越限与未采信项。

**不自动做：** 不自动调用视频生成模型出片；不自动把提示词发到任何平台；不自动改写用户原始白模。

## 九、降级与跨轮次

- **ffmpeg 缺失：** 给安装命令并停手；用户改用手放首帧则走 B 路径。
- **无视频只有图：** 跳过切片，按图写提示词，运镜时长标「未提供」。
- **信息不全的唯一降级：** 假设 + 就地标注 + 继续（最多追问一次，给默认值）；既不连环追问也不交白卷。
- **跨轮次：** 用户说「再加几镜」时，先读已有 `manifest.json` 与 `prompts.md` 续编，不重切已完成的镜头。
