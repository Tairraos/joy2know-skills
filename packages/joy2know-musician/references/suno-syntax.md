本文由 `@SKILL.md` 第七节路由到此。只在「要写具体标签但不确定怎么写」时读取。

# Suno 高阶指令语法手册

## 一、复合段落标签

**格式：** `[段落名 – 情绪描述, 演唱风格, 声场/乐器指令]`

三个部分用英文逗号分隔，至少要有段落名 + 一项描述。

| 部分 | 作用 | 常用词 |
|---|---|---|
| 段落名 | 告诉 AI 这是歌的哪一段 | Intro / Verse 1 / Pre-Chorus / Chorus / Verse 2 / Instrumental Break / Bridge / Outro / End |
| 段落名（器乐 / 循环用） | 没人声时改按**编曲功能**命名 | Intro / Loop A / Loop B / Build / Climax / Resolve / Break / Solo / Loop End / End |
| 情绪描述 | 定这一段要什么情绪 | Intimate / Grand and anthemic / Melancholic / Tender / Tense / Triumphant |
| 演唱风格 | 定人声怎么唱 | Half-whispered / Belted / Breathy / Smooth vocals / Clear enunciation / Layered vocals |
| 声场与乐器 | 定编曲与空间 | Panning left / Wide stereo / Close-mic / No percussion / Rising strings / Solo piano |

**器乐包用功能性段落名。** 没有人声时，`Verse` / `Chorus` 这类「给谁唱」的命名失去意义，
改用编曲功能命名：`[Loop A]`、`[Build]`、`[Climax]`、`[Resolve]`、`[Break]`、`[Solo]`。
循环包的首尾要**同名同源**（`[Loop Start]` 与 `[Loop End]` 的织体与和弦一致，接缝才听不出来）。
「演唱风格」一栏在器乐包里整列不用 —— 它不是"留空"，是**不存在**。

**例子：**
```
[Verse 1 – Broken Flow, Half-whispered, Panning left]
[Pre-Chorus – Build-up with rising strings, tense]
[Chorus – Grand and anthemic, Layered vocals, Wide stereo]
[Instrumental Break – Muted trumpet solo over brushed drums]
[Bridge – Dramatic shift, No percussion, Bare vocals]
[Outro – Fade out with echoing solo piano]
```

**段落顺序（完整版）：**
`[Intro] → [Verse 1] → [Pre-Chorus] → [Chorus] → [Verse 2] → [Instrumental Break] → [Bridge] → [Chorus] → [Outro] → [End]`

精简时保留 `[Intro]`、`[Chorus]`、`[Outro]`、`[End]` 四段，其余可砍。

## 二、行内指令（两种括号，含义不同）

| 写法 | 含义 | 例子 |
|---|---|---|
| `(文字)` | 背景采样、和声、重复回响（**人声相关**） | `(和声)`、`(repeat)`、`(echo)` |
| `(—文字—)` | 非人类音效 | `(—static crackle—)`、`(—heartbeat—)`、`(—wind howling—)` |

**采样模拟：** `(sample: "一句话") [whispered]` —— 引号内写对应语言的语录，后面跟处理方式。

**声调补偿：** 遇到 AI 容易唱破的字，在字后或字前加 `(ah)` / `(oh...)`，把音高垫平。

## 三、控制词表

**演唱控制**
```
[abrupt silence]        突然静默
[pitch-shifted down]    降调
[distorted]             失真（方言/治愈慎用）
[bitcrushed]            位深压缩（方言/治愈慎用）
[Smooth vocals]         平滑人声
[Clear enunciation]     咬字清晰
[Layered vocals]        叠唱
[Half-whispered]        半气声
```

**节奏与混音**
```
[chopped and screwed]   慢速 chop
[repeated erratically]  不规则重复
[No distortion]         无失真（用于抵消前文的失真倾向）
[Wide stereo]           宽声场
[Panning left / right]  左右声像
[Close-mic]             近场拾音
```

**冲突提示：** `distorted` / `bitcrushed` 与 `Smooth vocals, Polished production` 互斥。方言歌和治愈歌一律选后者，并显式写 `[No distortion]`。

**器乐与循环（D / E 路径专用）**
```
instrumental, no vocals   纯器乐声明（写在 Style 第一位）
Seamless loop             无缝循环
No fade in / No fade out  不淡入 / 不淡出（循环素材必写）
Consistent dynamics       动态稳定（循环素材要平，不要大起伏）
Clean cut                 干净切断
No percussion             无打击乐
Sustained pad             持续铺底
```

## 四、多语系 / 方言强锁

**三处都要锁，缺一不可：**

1. **Style 第一个字段** —— 写三层：`语言, 语系分支, 发音要求`
   - 粤语：`Cantonese, Cantopop, Traditional Cantonese Enunciation`
   - 普通话：`Mandarin, Standard Mandarin Enunciation`
   - 台语：`Taiwanese Hokkien, Traditional Hokkien Enunciation`
2. **歌词最前两行** —— `[Language: XXX]` 与 `[Accent: XXX]`
3. **歌词正文** —— 用本土特征字彻底卡死语系（见 `@references/cantonese-lock.md`）

**禁止：** 只写 `Chinese`。它会被默认成普通话，方言需求直接失效。

**纯器乐包例外：** 本节的三处锁**全部不适用**。没有人声就没有语言要锁 ——
Style 第一位改写成 `Instrumental, No vocals`，歌词开头**不写** `[Language:]` / `[Accent:]`
（不是留空占位，是根本不该有这两行，方括号外的一切都会被尝试唱出来）。
理由是这两行本身就在宣告「这首有人声」，详见 `@SKILL.md` 规则 2 的例外段。

## 五、Style 九字段顺序

```
Language, Accent, Genre, Vocal description, Instruments, Mood, Tempo, Atmosphere, Production style
```

| 字段 | 写法要点 |
|---|---|
| Language | 具体语言名，**放最前** |
| Accent | 发音要求，如 `Traditional Cantonese Enunciation` |
| Genre | 流派，可叠加（如 `Acoustic Indie Folk`） |
| Vocal description | 人声性别与唱法（如 `Soft breathy female vocals`） |
| Instruments | 用 `+` 连接，主次分明 |
| Mood | 情绪，2–3 个词 |
| Tempo | 必须给具体 BPM 数字 |
| Atmosphere | 空间与氛围（如 `Intimate room reverb`） |
| Production style | 制作质感（如 `Polished analog production`） |

**纯器乐包的写法：** 第 1、2 位（`Language` / `Accent`）合成一位 `Instrumental, No vocals`；
第 4 位 `Vocal description` 换成演奏主体（如 `Solo grand piano`），其余各项照旧。
逐字段的对照表与理由见 `@references/game-bgm-loop.md` 第三节。

## 六、常见错误

| 错误 | 后果 | 改法 |
|---|---|---|
| 段落标签只写 `[Chorus]` | AI 自由发挥编曲 | 补成复合标签 |
| 用中文写标签 | 中文被当人声唱出 | 标签一律英文 |
| Style 里写 `Chinese` | 方言被打回普通话 | 写具体语言三层锁 |
| 粤语歌词混「的/了/是」 | 语系污染，发音撕裂 | 换成「嘅/咗/系」 |
| 全篇一个唱法 | 没有起伏 | 主副歌用不同演唱风格 |
| 忘记 `[End]` | 结尾可能不完整 | 末尾固定加 |
| 括号不配对 | 解析错乱 | 用 `scripts/suno_check.py` 查 |
| 副歌闭口韵 | 唱不上去，情绪出不来 | 副歌改开口韵 |
| 器乐包填语言锁 | 诱导出哼唱与无词垫音 | 首位改 `Instrumental, No vocals`，删掉 `[Language:]` / `[Accent:]` |
| 器乐包 Style 里留着人声描述 | 与 `No vocals` 打架，模型挑一个执行 | 人声词一个不留，`Vocal description` 换成演奏主体 |
| 循环包写 `Fade out` | 循环点接不上，每圈一个音量豁口 | 收尾改成回到开头的和弦与织体、干净切断 |
| 循环包不写 BPM | 输出漂移，循环点落在小节中间 | Style 里写死数字 BPM |
