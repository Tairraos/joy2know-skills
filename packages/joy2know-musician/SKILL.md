---
name: joy2know-musician
display_name: 晓得·音乐人
display_name_en: joy2know Musician
description: >-
  用 Suno 的高阶语法（v4.5–v6 通用）写可直接粘贴的歌曲包：复合段落标签、行内指令、声场控制、Style 语言锁，
  默认输出治愈、有画面感、带人生哲理的作品；用户指定任何风格、语言或方言（含粤语）时按同一套技巧适配，
  并用「词汇锁 + 协音字 + 声调补偿」解决方言发音撕裂、破音、跑偏；
  纯器乐与循环路径另有一套写法，用于压制人声幻觉、锁死 BPM、让首尾同源，服务游戏 BGM 与背景垫乐。
  触发词：写首歌、做音乐、Suno、写歌词、配乐、主题曲、BGM、写一段旋律、治愈系歌曲、粤语歌、
  方言歌、suno prompt、write a song、song lyrics、music prompt、Suno style、
  纯音乐、不要人声、无人声、不做人声、器乐、instrumental、游戏 BGM、游戏背景音乐、无缝循环、
  循环素材、背景音乐、垫乐、氛围音乐、白噪音、专注音乐、冥想音乐、片头音乐、stinger。
  不适用于：实际调用音乐生成接口（本技能只产出可粘贴的提示词包）；需要真实乐谱或 MIDI；
  要求保证生成结果与你想象完全一致（AI 音乐有随机性，本技能提高命中率而非消除随机）；
  要求交付已剪好、开箱即无缝的音频文件（本技能给循环友好的写法与后期处理清单，裁切与交叉淡化仍要在你自己的编辑器里做）。
description_zh: >-
  用 Suno 高阶语法产出可直接粘贴的歌曲包，默认治愈风格，支持指定风格与方言并做防跑偏处理；
  纯器乐与循环素材另有压制人声幻觉、锁死 BPM、首尾同源的写法。
description_en: >-
  Write ready-to-paste Suno song packs (v4.5–v6) using advanced syntax: compound section tags, inline cues,
  stereo-field control and a Style language lock. Defaults to a healing, imagery-rich, philosophical style;
  adapts to any genre, language or dialect (including Cantonese) the user names, using word-locks and
  tonal compensation to stop AI from drifting, cracking or breaking on pronunciation. Also covers the
  instrumental and loop-ready paths used for game BGM and background beds: how to suppress phantom
  humming and wordless vocals, lock the BPM, and match a loop's tail back to its head. Outputs prompts
  only — it does not call any music generation API, cannot guarantee identical results, and does not
  deliver an already-spliced seamless audio file (trimming and crossfading still happen in your editor).
category: writing
version: 1.4.0
author: 晓得乐
---

# 晓得 · 音乐人

> 把「一段想法」变成「一份能直接粘进 Suno 的歌曲包」——标题 + Style + 带完整结构标签的歌词。
> 你不是在写歌词，你是在做**声音设计**：每一段标签都是给 AI 的编曲指令。

## 一、先分清（这四层混在一起，生成必崩）

| 层 | 是什么 | 写在哪 | 语言 |
|---|---|---|---|
| **Style（风格锁）** | 整首歌的全局设定：语言、唱法、乐器、情绪、速度 | 独立一段，最前面 | 全英文 |
| **段落标签** | 每一段的编曲与演唱指令 | 歌词里 `[...]` 包裹 | 英文 |
| **行内指令** | 单句内的和声、采样、音效 | 歌词里 `(...)` 包裹 | 英文 |
| **歌词正文** | 人声实际唱的内容 | 标签下方 | 目标语言（中文/粤语/英文…） |

**最常见的失败：** 把编曲指令写进歌词正文，或把歌词写进 Style。Suno 会把它们都当成人声唱出来，或者干脆忽略你的编曲意图。

**纯器乐包少一层：** 上表第三行往下的「歌词正文」这一层**不存在** —— 方括号标签之外必须留空，圆括号指令也只保留非人声的那一类。
器乐包里 Style 与段落标签承担全部控制职责，`(—音效—)` 的权重相应上升；而 `(和声)` / `(sample: "…")` / `(ooh)` 这类
**人声**行内指令要全部拿掉 —— 它们正是「明明说了不要人声、却听到哼唱」的来源。走 D / E 路径时见第十节。

## 二、判定与路由

| 情形 | 判定信号 | 走哪条 |
|---|---|---|
| **A. 默认治愈** | 用户只说「写首歌」，没指定风格 | 走治愈配方（`@references/healing-style.md`），无需追问风格 |
| **B. 指定风格** | 给了流派、参考歌手、情绪 | 保留治愈的**文风底色**（画面感 + 人生哲理），换掉音乐外壳 |
| **C. 方言路径** | 粤语、闽南语、四川话等 | 语言锁 + 词汇锁 + 协音字，见第四节规则 3，跑 `@references/cantonese-lock.md` |
| **D. 纯器乐** | 「不要人声」「只要 BGM」「纯音乐」「不做人声」 | 走器乐路径：Style 首位写器乐声明、标签全英文、**方括号外留空**。写法见第十节 |
| **E. 循环 / 游戏 BGM** | 「游戏 BGM」「无缝循环」「循环素材」「要能一直放下去」 | 走 D 路径 + 循环约束（禁淡出、锁死 BPM、首尾同源）。见第十节 |

**D 与 E 的关系：** E 是 D 的加强版 —— 循环素材默认也走纯器乐（带人声的循环听两遍就腻）。
用户偏要「带人声的循环曲」时，人声部分照普通路径写，循环那几条约束照旧套用。

**信息收集：** 首次交互用简洁列表问五件事——①主题 ②风格 ③参考 ④内容方向 ⑤人声偏好（要人声 / 纯器乐 / 不指定）。
**但只问一次**，且每项都给默认值，用户不答就按默认值往下走（见第九节降级）。

**降级判定：** 用户说「随便写一首」「你看着办」→ 全部走默认值，直接产出，不追问。

## 三、工作流

1. **收信息。** 五问一次 + 默认值。交互满 3 次信息仍不全时，说明缺什么、获得许可后由你补全剩余项。
2. **定人声锁（Style 第一字段）。** 有人声：目标语言写进 Style 的**第一个字段**，并在歌词最前写
   `[Language: XXX]` 与 `[Accent: XXX]`；方言必须连带写明具体语系（见规则 2）。
   **纯器乐（D / E 路径）：这一位改写 `Instrumental, No vocals`，并且不写 `[Language:]` / `[Accent:]`** —— 理由见规则 2 的例外段。
   **用户要求「多首歌保持同一个人声」时**：这不是提示词能解决的事 —— 同一段 Style 每次生成的音色都会漂。
   应引导他用平台的 Style Persona / Voices 去锁，并明说「一致靠平台功能、不靠提示词」（见 `@references/model-and-controls.md` 第四节）。
3. **组装 Style。** 有人声按九字段顺序：`Language, Accent, Genre, Vocal description, Instruments, Mood, Tempo, Atmosphere, Production style`；
   器乐包把前两位合成一位 `Instrumental, No vocals`，再把 `Vocal description` 换成演奏主体（如 `Solo grand piano`）。
   写完附一行中文翻译（「**歌曲风格：** …」）。
4. **搭段落骨架。** 有人声的完整顺序：`[Intro] → [Verse 1] → [Pre-Chorus] → [Chorus] → [Verse 2] → [Instrumental Break] → [Bridge] → [Chorus] → [Outro] → [End]`。
   **用户要求精简时可砍段，但 `[Intro]`、`[Chorus]`、`[Outro]`、`[End]` 不可省。**
   **纯器乐 / 循环包例外：** 必留段放宽为 `[Intro]` + `[End]` —— 循环素材本来就没有 Chorus，也不该有淡出的 Outro。
5. **填正文。** 有人声包按第四节的创作标准写：主歌写实、副歌造张力、意象做重组（详见规则 4–6）。
   **器乐包跳过本步** —— 方括号外留空，编曲全靠段落标签交代；也不要拿标题行、空歌词行去占位（一样会被唱出来）。
6. **方言自检（仅 C 路径）。** 跑 `scripts/suno_check.py --dialect cantonese` 检查特征字密度、风险字与普通话污染。
   其他方言（客家/闽南/潮州/四川/上海/东北话）可传对应的 `--dialect` 值：脚本会照常做结构检查与
   **普通话污染检查**，只跳过「特征字密度」一项并提示字表待补 —— 不要因为「密度查不了」就连污染也不查。
7. **结构校验。** 跑 `scripts/suno_check.py <歌词文件> --style "<Style 全文>"`；**器乐包加 `--instrumental`，循环素材再加 `--loop`**，按报告修掉结构问题。
   **`--style` 别省** —— 器乐声明到没到位、BPM 有没有锁死、方言的防破音指令加没加，这三项只有拿到 Style 文本才查得出来。
8. **纯净输出。** 收齐信息后**严禁解释**，直接输出三段（见第五节）。

## 四、核心规则

**规则 1：所有控制指令必须用英文，歌词正文用目标语言（红线）**

- 触发条件：写 Style、段落标签、行内指令。
- 硬性动作：段落标签、括号内描述、Style 全部英文；歌词正文用目标语言。
- 正例：✓ `[Verse 1 – Half-whispered, Intimate]` + 下方中文歌词
- 反例：✗ `[第一段 – 低声呢喃]`（Suno 会把中文标签当歌词唱出来）
- 降级路径：用户要求全中文标签时，明确说明「中文标签会被当人声唱出，建议保留英文」后仍按用户要求做，并在产出中标注风险。
- **本条优先于其他所有表达偏好。**

**规则 2：Style 第一位必须是「人声锁」，且不能写宽泛词**

- 触发条件：填 Style 第一字段，以及歌词开头的 `[Language:]` / `[Accent:]`。
- 硬性动作（有人声）：Style 第一个字段写具体语言与语系；方言要写成 `Cantonese, Cantopop, Traditional Cantonese Enunciation` 这样的三层。**禁止**只写 `Chinese`（会被默认成普通话）。
- 正例：✓ `Cantonese, Cantopop, Traditional Cantonese Enunciation, ...`
- 反例：✗ `Chinese, pop, ...`（用户要粤语，结果出普通话）
- 降级路径：用户没指定语言时，默认 `Mandarin, Standard Mandarin Enunciation`，并在产出里标注可替换。

**例外 · 纯器乐路径（D / E）：第一位改成 `Instrumental, No vocals`，并且不写 `[Language:]` / `[Accent:]`。**

这一位的作用**始终是「约束人声」**，位置不变、职责不变，只是取值随「这首有没有人声」而变：
有人声时它指定**唱什么语言**，无人声时它声明**根本不唱**。

- 正例：✓ `Instrumental, No vocals, Ambient, Solo grand piano + warm pads, Calm, 72 BPM, ...`
- 反例：✗ 器乐包写 `Mandarin, Standard Mandarin Enunciation, ...` —— Style 里出现语言与发音要求，
  等于告诉模型「这首有人声」，它就会用**哼唱、ooh/ahh 垫音、无词人声**把这一层补上。
  你以为在关人声，实际是在下反向指令。
- 反例：✗ 器乐包 Style 里还留着 `Soft breathy female vocals` 这类人声描述 —— 与 `No vocals` 直接打架，
  模型会挑一个执行，挑错就是一段无词人声。器乐包里描述人声的词**一个都不留**。
- 降级路径：**压住了唱词、却没压住哼唱**时，把 `vocals, singing, humming, vocalizations` 这类词放进平台的
  **排除 / 负面提示字段（Exclude）**——它比在 Style 里写否定词可靠。
  **该字段的位置（2026-09 核实的官方文档）**：Custom 模式 → **Advanced Options（高级选项）** →
  菜单**第一项**即 Exclude；语义等同 negative prompt。
  字段是否提供、叫什么名字仍以你当前 Suno 版本的实际界面为准（本技能不写死版本差异）；
  **官方未给分隔符示例 —— 按英文逗号枚举是稳妥做法，但别向用户声称这是官方规定的语法**。
  没有这个字段时，靠「简化 Style + 全篇不出现任何人声词」把概率压到最低，
  并如实告诉用户仍有可能出现垫音人声 —— **不要承诺「一定没有人声」**。

**规则 3：方言必须彻底本土化 + 防破音（C 路径专属）**

- 触发条件：目标语言是方言（粤语等）。
- 硬性动作：① 歌词用高频强特征方言字彻底卡死普通话音轨（粤语用「嘅、咗、嗰、唔、系、呢」等）；② 规避易在采样拉扯中产生电流破音、增益过载的字眼，改用发音相近的平顺字；③ Style 中标明 `Smooth vocals, Polished production`，**禁用**可能产生高频冲突的杂音指令（如 `bitcrushed`、`distorted`）。
- 正例：✓ 粤语歌词通篇用「我哋、嗰阵、唔会」，Style 带 `Smooth vocals, Polished production`
- 反例：✗ 粤语歌词里混「的、了、是」（语系污染，AI 会在两种发音间拉扯）
- 反例：✗ 粤语歌同时要 `distorted` + 大量爆破音字（必破音）
- 降级路径：必须保留某种会破音的字（如歌词关键字）时，用行内 `(ah)` / `(oh...)` 做声调补偿，并在 Style 里保留 `Smooth vocals`。

**规则 4：段落标签必须是复合结构**

- 触发条件：写任何一个段落标签。
- 硬性动作：格式 `[段落 – 情绪描述 + 演唱风格 + 声场/乐器指令]`，至少含段落名 + 一项描述。
- 正例：✓ `[Chorus – Grand and anthemic, Layered vocals, Wide stereo]`
- 反例：✗ `[Chorus]`（Suno 拿不到编曲意图，只能自由发挥）
- 降级路径：无，这是本技能的核心价值之一。

**规则 5：两种括号代表两种东西，不许混用**

- 触发条件：写行内指令。
- 硬性动作：`(文字)` = 背景采样、和声、重复回响（人声相关）；`(—文字—)` = 非人类音效（如 `(—static crackle—)`、`(—heartbeat—)`）。
- 正例：✓ `(—wind howling—)` / `(和声)` / `(sample: "一句话") [whispered]`
- 反例：✗ 用 `(—和声—)` 表示人声和声（会被识别为音效）
- 降级路径：不确定时优先用 `(文字)`，并在文末说明该处意图。

**规则 6：默认治愈文风，用户指定风格时只换外壳**

- 触发条件：写歌词正文。
- 硬性动作：核心文风默认**治愈、有画面感、带人生哲理**。创作技法：
  - 主歌（Verse）：用**具体写实动词**代替抒情，靠生活细节铺陈
  - 意象：用「具象名词 + 抽象动词」重组（如「思念生锈」）
  - 副歌（Chorus）：用**矛盾修辞**制造张力（如「拥挤的孤独」）
  - 语气：善用语气词增加倾诉感
  - 韵律：主歌偏**闭口韵**（细腻），副歌偏**开口韵**（高亢）
- 正例：✓「锅铲刮过锅底的声响 / 是这十年最安稳的闹钟」（写实动词 + 生活细节）
- 反例：✗「我好想你 / 我真的好想你」（纯抒情，无画面）
- 降级路径：用户指定其他风格（如摇滚、电子）时，**音乐外壳全换，但保留画面感与具体性**——不要把「换风格」理解成「可以写空泛」。

**规则 7：不编造用户没给的事实**

- 触发条件：歌词中出现具名实体、真实事件、真实地点。
- 硬性动作：只用用户提供的信息。需要补全的生活细节可以用，**但涉实名、品牌、具体事件的一律不编**。
- 正例：✓ 用户说「写给父亲的歌」→ 写「旧皮鞋、烟盒、凌晨的车站」这类通用细节
- 反例：✗ 用户说「写给父亲的歌」→ 写成「1998 年你带我去的那个天安门」（编造具体事件）
- 降级路径：确实需要具体锚点时，写 `[待替换：你与父亲的真实地点]` 占位并列出清单。

## 五、输出格式

```text
### 1. 标题
标题 (语言)

### 2. Style (Suno Optimized)
Mandarin, Standard Mandarin Enunciation, Acoustic Indie Folk, Soft breathy female vocals,
Fingerpicked acoustic guitar + warm piano + light strings, Healing and nostalgic, 76 BPM,
Intimate room reverb with morning-light warmth, Polished analog production

**歌曲风格：** 治愈系 acoustic 民谣，气声女声，木吉他指弹配暖钢琴与轻弦乐，76 BPM，温暖怀旧

### 3. Lyrics (Suno Structure)
[Language: Mandarin]
[Accent: Standard Mandarin]
[Intro – Muted piano loop, soft static crackle, distant rain]
(—wind chimes—)
(sample: "食咗饭未") [whispered]
[Verse 1 – Half-whispered, Intimate, Close-mic]
……
[Chorus – Grand and anthemic, Layered vocals, Wide stereo]
……
[Outro – Fade out with echoing solo piano]
[End]
```

器乐 / 循环包（D / E 路径）长这样 —— **没有 `[Language:]` / `[Accent:]` 两行，方括号外不留一个字**：

```text
### 1. 标题
标题 (Instrumental)

### 2. Style (Suno Optimized)
Instrumental, No vocals, Ambient Cinematic, Solo grand piano + warm pads + subtle cello,
Calm and spacious, 72 BPM, Wide reverb, Seamless loop, No fade in, No fade out,
Consistent dynamics, Polished production

**歌曲风格：** 纯器乐环境音乐，独奏钢琴配暖垫与轻大提琴，72 BPM，宽混响，无缝循环、不淡入不淡出

### 3. Lyrics (Suno Structure) —— 只有标签，方括号外一律留空
[Intro – Solo piano, Sparse, Wide reverb]
(—room tone—)
[Loop A – Steady arpeggio, No percussion, Consistent dynamics, Seamless loop point]
[Loop B – Add warm pads, Build without peak, Wide stereo]
[End – Return to opening chord and texture, Clean cut, No fade out]
```

三处与有人声版的差别，不要漏：**①** Style 首位是器乐声明而不是语言锁；**②** 标题后的括号标注是 `(Instrumental)`
而不是语言；**③** 结尾段是「回到开头的和弦与织体 + 干净切断」，**不是** `[Outro – Fade out ...]`。

**反模式禁止清单：**

| # | 反模式 | 为什么禁 |
|---|---|---|
| 1 | 收齐信息后还在解释创作思路 | 用户要的是可直接粘贴的文本，规则要求纯净输出 |
| 2 | 段落标签只写段落名 | 等于放弃编曲控制权 |
| 3 | 中文写段落标签 | 会被当人声唱出来 |
| 4 | Style 里只写 `Chinese` | 方言会被打回普通话 |
| 5 | 粤语歌词混普通话虚词 | 语系污染，发音撕裂 |
| 6 | 为了「有风格」堆砌 `distorted` `bitcrushed` | 与方言/治愈需求冲突，必破音 |
| 7 | 副歌也用闭口韵 | 唱不上去，情绪出不来 |
| 8 | 输出完不跑结构校验 | 缺 `[End]`、括号不配对这类错误肉眼很难发现 |
| 9 | 器乐包里填语言锁（`Mandarin, Standard Mandarin Enunciation`） | 等于告诉模型「这首有人声」，诱导出哼唱与无词垫音 |
| 10 | 循环素材里写 `Fade out`、把收尾做成渐弱 | 尾部渐弱让循环点接不上，听第二遍就露馅 |
| 11 | 承诺「这条提示词能直接出无缝循环」 | Suno 出的是素材，无缝靠裁到整数小节 + 交叉淡化，拍胸脯就是不诚实 |

## 六、防幻觉（硬约束，优先级最高）

**本节优先于以上所有格式与文风要求。**

1. **不承诺生成结果。** AI 音乐有随机性。**禁止**说「按这个一定能出你想要的效果」，改为「建议同一版生成 2–3 次挑一次」。
2. **信息补全与规则偏离，都必须标注。** 分两类写清：
   - **补全的** —— 你替用户定的主题、风格、人声偏好，在文末「假设与待替换」里逐条列出，**禁止**把补全当成用户说的；
   - **偏离的** —— 你**有意不按本技能某条规则执行**时，写明「偏离了哪一条 + 为什么」，例：
     `偏离规则 2：本曲无人声，故未写语言锁，Style 首位改为 Instrumental, No vocals`。
     偏离本身可以发生，但**不许悄悄发生** —— 没声明的偏离，读起来和失误没有区别。
3. **不编造参考歌手的具体作品。** 提到参考时只写风格特征，**禁止**编造某歌手某年某专辑。
4. **不编造技术参数。** Suno 的具体限制（时长上限、标签支持范围）会随版本变，不确定就写「以你当前 Suno 版本的实际表现为准」。
5. **不确定就直说不确定。** 「这个方言我没有把握，建议先生成一句试听再决定整首」是合格输出。

## 七、按需知识

只在遇到对应问题时读取：

- 完整语法手册（复合标签、行内指令、采样模拟、演唱与混音控制词表）→ `@references/suno-syntax.md`
- 默认治愈风格的完整配方（乐器、速度、和声走向、文风参数）→ `@references/healing-style.md`
- 粤语等方言的词汇锁、风险字表、声调补偿写法 → `@references/cantonese-lock.md`
- 纯器乐 / 游戏 BGM / 无缝循环的完整配方（编制、动态分层、循环点做法、后期与响度、可复制模板）→ `@references/game-bgm-loop.md`
- **模型怎么选（v6 / v6-wild / v6-mini）、滑杆怎么调（Weirdness / Style Influence）、Exclude 填在哪、怎么让多首歌人声一致** → `@references/model-and-controls.md`

## 八、完成判据

**算做完（有人声包）：** 标题 + Style（九字段齐全且人声锁在最前）+ 歌词（含 `[Language:]`/`[Accent:]`、段落标签全部复合、以 `[End]` 结尾）+ 结构校验通过 + 文末列出「假设与待替换」。

**算做完（器乐 / 循环包）：** 标题（括注 `(Instrumental)`）+ Style（首位 `Instrumental, No vocals`、**不含** `[Language:]`/`[Accent:]`、Style 里没有任何人声描述词，循环包还要写死 BPM 与 `Seamless loop, No fade in, No fade out`）+ 段落标签（方括号外留空、以 `[End – …]` 收束、**处处无 fade out**）+ 结构校验通过 + 文末列出「假设与待替换」（含本次的规则偏离）。

**不自动做：** 不自动调用音乐生成接口；不自动开始做封面与 MV；不自动把歌词翻译成其他语言（用户要求才做）；
不自动替用户剪音频、对齐循环点（本技能产出提示词包与后期清单，动手在用户的编辑器里）。

## 九、降级与跨轮次

- **信息不全时的唯一降级路径：** 假设 + 就地标注 + 继续。问满 3 次仍缺，说明缺什么并获得许可后自行补全，**禁止**连环追问，也**禁止**交白卷。
- **用户说「你看着办」：** 全部走默认值（治愈配方、普通话、气声女声、76 BPM），直接产出。
  **但若整轮话题是游戏、视频、播客、展厅、专注或白噪音**，默认改走器乐 + 循环路径（第十节）—— 不要自作主张递上一段带人声的「歌」。
- **器乐包仍听到哼唱：** 这不是「再生成一次就好」的问题，按顺序做三件事 ——
  ① Style 里删掉一切人声词（**包含语言与发音要求**），并简化到 4–7 个标签（堆太多会互相抵消）；
  ② 若平台有排除 / 负面字段，把 `vocals, singing, humming, vocalizations` 全塞进去；
  ③ 换更「纯器乐」的流派词（环境 / 氛围 / 后摇比 pop、trap、soul 稳得多）。
  三件做完还是出，就如实告诉用户并建议换方向，**不要反复烧额度**。
- **用户要的其实是「一段能循环的文件」：** 先讲清交付边界 —— 本技能给的是**提示词包 + 后期处理清单**；
  裁到整数小节、标 loop point、接缝交叉淡化要在他的编辑器里做。愿意的话把操作步骤一并给出（见 `@references/game-bgm-loop.md`）。
- **目标模型不是 Suno：** 语法需按目标平台调整；明确告知「这套标签语法是 Suno 的，换平台要改写成该平台的格式」，不要原样照搬。
- **用户嫌太长：** 有人声包可砍到 `Intro + Verse + Chorus + Outro + End`，但保留全部标签语法。
  **器乐 / 循环包不适用这条** —— 它们本来就不长，要砍的是段落数而不是循环结构，砍掉了就接不回开头。
- **跨轮次：** 用户说「副歌再燃一点」「换成粤语」时，只改对应部分，**不要整首重写**——重写的代价是前面调好的段落也要重调。

## 十、场景配方：纯器乐与循环 BGM

> 走 D / E 路径（§二）时读本节。本节只放**路由信号 + 冲突裁决 + 速查**；
> 论证在规则 2 的例外段里，配方细节在 `@references/game-bgm-loop.md`（两处不再各写一份）。

**什么人会走到这里：** 游戏 BGM、视频 / 播客的垫乐、展厅与空间环境音、专注与白噪音、冥想、
App 与提示音、片头片尾的短音乐（Stinger）。

### 三处冲突的裁决（本节核心）

| 冲突点 | 有人声路径 | 器乐 / 循环路径 | 一句话理由 |
|---|---|---|---|
| Style 第一位（规则 2） | `Mandarin, Standard Mandarin Enunciation` | `Instrumental, No vocals`；**不写** `[Language:]` / `[Accent:]` | 语言与发音要求本身就在宣告「这首有人声」，模型会用哼唱、ooh/ahh 把这层补上 |
| 是否要好听抓耳 | 副歌要抓耳、要有起伏 | 要**平**：不押强钩子、动态稳定 | 循环素材会被听几十遍，抓耳在第 3 遍就变成烦人 |
| 必留段落（§三.4） | Intro / Chorus / Outro / End | Intro + End | 循环素材没有 Chorus，也不该有渐弱的 Outro |

### 循环素材的四条硬约束

1. **禁淡出。** Style 写 `Seamless loop, No fade in, No fade out`；段落标签里**不许**出现 `Fade out` / `fading`。
2. **BPM 必须写死具体数字。** 这是与有人声路径最大的不同 —— 那边是「必须给具体 BPM」，
   这里是**硬要求**：BPM 不锁死，循环点会落在小节中间，怎么剪都有断层。
3. **首尾同源。** 尾段要「回到开头的和弦与织体、干净切断」，写成
   `[End – Return to opening chord and texture, Clean cut, No fade out]`，而不是 `[Outro – Fade out ...]`。
4. **不承诺 Suno 直出无缝。** 生成物是**素材**：真正的无缝靠裁到整数小节、在拍点标 loop point、
   接缝处交叉淡化 —— 都在你的编辑器里做。说「这条提示词能直接出无缝循环」就是不诚实。

### 与默认治愈配方的差异

| 项 | 有人声歌 | 器乐 / BGM |
|---|---|---|
| 默认 BPM | 72–84 | 68–92（Ambient 类可到 60–75） |
| 首位字段 | 语言锁三层 | `Instrumental, No vocals` |
| 人声描述 | `Soft breathy female vocals` | 换成演奏主体，如 `Solo grand piano` |
| 必留段落 | Intro / Chorus / Outro / End | Intro + End |
| 目标时长 | 2–4 分钟 | 30 秒–2 分钟的可循环核心段（需要更长用 Extend 续接） |
| 生成预算 | 2–3 次挑一版 | **3–5 次**（循环点对齐的成功率明显更低，先留出额度） |

### 游戏子场景速查

| 场景 | 编制与情绪 | 参考 BPM |
|---|---|---|
| 主菜单 | 主题动机完整出现一次，克制不抢戏 | 70–90 |
| 探索 / 日常 | 稀疏、留白多、不押节奏 | 70–90 |
| 战斗 | 节奏驱动、低音推进、动态抬升 | 110–140 |
| 危机 / Boss | 和声密度高，加铜管或失真吉他 | 120–150 |
| 胜利 / 结算 | 明亮、短促、**要**明确的终止感（这一条是 Stinger，**不循环**） | 100–130 |
| 悲伤 / 结局 | 单乐器、长音、慢 | 55–75 |

**动态分层的常规做法：** 同一场景做 2–4 个**同 BPM 同调性**的强度层（氛围床 → 加节奏 → 战斗全奏 → Boss 叠加），
由引擎按玩家状态切换。层与层必须同 BPM 同调，否则交叉淡化会露馅。
做法是从**同一版 Style 出发**用 Extend / Remix 逐层加浓，**不要另起一版 Style** —— 那是"两首不同的曲子"，不是两层。

**要展开的（编制、循环点与后期步骤、Stinger、响度与格式、可复制模板、失败模式）→ `@references/game-bgm-loop.md`。**
