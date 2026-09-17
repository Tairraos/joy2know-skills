本文由 `@SKILL.md` 第七节路由到此。只在「要写具体标签但不确定怎么写」时读取。

# Suno 高阶指令语法手册

## 一、复合段落标签

**格式：** `[段落名 – 情绪描述, 演唱风格, 声场/乐器指令]`

三个部分用英文逗号分隔，至少要有段落名 + 一项描述。

| 部分 | 作用 | 常用词 |
|---|---|---|
| 段落名 | 告诉 AI 这是歌的哪一段 | Intro / Verse 1 / Pre-Chorus / Chorus / Verse 2 / Instrumental Break / Bridge / Outro / End |
| 情绪描述 | 定这一段要什么情绪 | Intimate / Grand and anthemic / Melancholic / Tender / Tense / Triumphant |
| 演唱风格 | 定人声怎么唱 | Half-whispered / Belted / Breathy / Smooth vocals / Clear enunciation / Layered vocals |
| 声场与乐器 | 定编曲与空间 | Panning left / Wide stereo / Close-mic / No percussion / Rising strings / Solo piano |

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

## 四、多语系 / 方言强锁

**三处都要锁，缺一不可：**

1. **Style 第一个字段** —— 写三层：`语言, 语系分支, 发音要求`
   - 粤语：`Cantonese, Cantopop, Traditional Cantonese Enunciation`
   - 普通话：`Mandarin, Standard Mandarin Enunciation`
   - 台语：`Taiwanese Hokkien, Traditional Hokkien Enunciation`
2. **歌词最前两行** —— `[Language: XXX]` 与 `[Accent: XXX]`
3. **歌词正文** —— 用本土特征字彻底卡死语系（见 `@references/cantonese-lock.md`）

**禁止：** 只写 `Chinese`。它会被默认成普通话，方言需求直接失效。

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
