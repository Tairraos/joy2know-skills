本文由 `@SKILL.md` 第九节路由到此。**本文件只讲「多首并列时怎么写 token」**——
单首的基础写法（语言声明句、段落标签、中文补断句）以单曲技能
（`joy2know-musician` / `joy2know-mureka-musician`）为准，本文件不重复。

# 专辑级token 写法：风格栏的组成与差异轴

## 一、风格栏 token 的组成顺序（按此顺序拼，别自己调序）

```
发音方式 / 器乐类型 → 曲风 → 拍号 → BPM → 调式 → 主奏乐器 → 编制 → 音区 → 混音/空间 → 弦乐语气
```

**为什么是这个顺序**：从「谁在说」到「说什么话」再到「怎么说」，前段决定生成器把它归到哪一类，
后段决定细节。拍号与 BPM 放在曲风之后、调式之前，是为了让速度与律动先落定，再叠色彩。

**Mureka 字段说明**：风格栏 ≤1000 字；上面十项全写一般 200–400 字，余量留给曲风细分与场景。

### 1.1 有人声时的完整示例（Mureka 风格栏）

```text
Mandarin folk, 7/8, 84 BPM, D dorian, fingerpicked acoustic guitar + cello, five-piece folk band,
low-mid register, intimate close-mic room reverb, no wall reverb
```

逐段对照：

| 序 | 要素 | 本例 | 说明 |
|---|---|---|---|
| 1 | 发音方式/器乐类型 | （器乐段落可省） | 有人声时这一位写人声类型，如 `emotional male vocal` |
| 2 | 曲风 | `Mandarin folk` | 2–3 个基色，不堆词 |
| 3 | **拍号** | `7/8` | ⭐ 必须进 token（规矩 2） |
| 4 | **BPM** | `84 BPM` | 单个数字；专辑内全不同（规矩 5） |
| 5 | **调式** | `D dorian` | ⭐ 必须进 token（规矩 2） |
| 6 | 主奏乐器 | `fingerpicked acoustic guitar` | 每首不同才好区分（差异轴首选） |
| 7 | 编制 | `five-piece folk band` | 写规模或件数，别只写「乐队」 |
| 8 | 音区 | `low-mid register` | `high / mid / low` 之一或两档 |
| 9 | 混音/空间 | `intimate close-mic room reverb` | 空间感是区分曲目的廉价轴 |
| 10 | 弦乐语气 | `no wall reverb` / `no vibrato` | 只在有弦乐时写 |

### 1.2 纯音乐时的完整示例（Mureka 风格栏，**首句必须是 `No vocals`**）

```text
No vocals, ambient cinematic, 7/8, 68 BPM, D aeolian, solo grand piano + cello + brushed snare,
low register, wide hall reverb with long tail, legato sustain
```

⚠️ **全篇不得出现** `vocal / singer / humming / choir / ooh / chanting` —— 写了等于反向指令。
⚠️ 本首的**音乐流向不靠开关，靠歌词栏的方括号标签**（见 `platform-notes.md` 第三节）。

### 1.3 Suno 的 Style 写法差异

Suno 的 Style 是**九字段一行**，语言与口念在第一字段：

```text
Standard Mandarin Enunciation, Chinese (Mandarin) female vocal, acoustic indie folk in 7/8 at 84 BPM,
D dorian, fingerpicked acoustic guitar lead with cello, five-piece folk band, low-mid register,
intimate close-mic room, legato acoustic
```

⚠️ 这行**不能原样粘进 Mureka 风格栏**（Mureka 风格栏不认 `Standard Mandarin Enunciation`，
会出现语言锁与歌词栏声明句打架）。

## 二、六根差异轴（差异矩阵就按这六根算）

| 轴 | 取值写法 | 对听感的影响 | 好不好换 |
|---|---|---|---|
| **拍号** | `4/4` `3/4` `6/8` `7/8` `5/4` `12/8` | ⭐⭐⭐ 律动骨架 | 好换 |
| **BPM 区间** | 慢 ≤75 / 中 76–100 / 快 ≥101 | ⭐⭐⭐ 整体速度 | 好换（且必须全不同） |
| **调式** | `D dorian` `A aeolian` `G mixolydian` `C major` `E phrygian` | ⭐⭐ 明暗色彩 | 好换 |
| **主奏乐器** | 指弹木吉他 / 大提琴 / 爵士钢琴 / 电吉他 / 萨克斯… | ⭐⭐⭐ 最容易被听出不同 | **最好换，撞车优先改它** |
| **编制规模** | solo / duo / three-piece / five-piece / big band | ⭐⭐ 密度与空间 | 好换 |
| **音区** | `low register` `mid register` `high register` | ⭐⭐ 音域位置 | 好换 |

**撞车时的改法优先级**：主奏乐器 → 音区 → 编制 → 拍号 → 调式 → BPM（**BPM 留着最后改**，
因为它是唯一「必须全不同、且一旦定了很难挪」的轴）。

## 三、差异矩阵怎么填（逐对，不是写一句声明）

以 5 首为例，轴记 `1`=不同、`0`=相同；只列上三角：

| | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| **1** | — | 2 | 1 | 0 | 2 |
| **2** | | — | 1 | 2 | 1 |
| **3** | | | — | 1 | 0 |
| **4** | | | | — | 2 |
| **5** | | | | | — |

**每个数字 = 该对曲目有几根轴相同。**
除「序章 × 收尾」外全部 ≤2；序章 × 收尾是有意呼应，上限 4（这条例外的完整表述见 `SKILL.md` 规矩 6，只写一遍）。
出现 `3` 或 `4`（非序章×收尾对）就必须改其中一首，改完**重算全表**（改一列会牵动其余所有对）。

**本表必须由脚本算出来，不许手写** —— `scripts/album_check.py` 会两两比对并在超标时指名道姓报出是哪两首。

## 四、几组实测过站得住的配对（拿不准时的起点）

| 想做成 | 拍号 | BPM | 调式 | 主奏乐器 | 编制 | 听感 |
|---|---|---|---|---|---|---|
| 序章·把门打开 | 4/4 | 68 | C major | solo grand piano | solo | 亮、干净、留白最多 |
| 主体·向前推但不慌 | 7/8 | 84 | D dorian | fingerpicked guitar | five-piece | 律动有推进感、色调灰里有光 |
| 主体·摇 | 6/8 | 92 | A aeolian | cello | trio | 摇、沉 |
| 主体·亮起来 | 3/4 | 104 | G mixolydian | trumpet + piano | quartet | 明亮、带弹跳 |
| 收尾·呼应序章 | 3/4 | 76 | A aeolian | solo grand piano | solo | 同一件乐器、不同和声 |

⚠️ 上表只是**起点**。序章与收尾这一对是**有意呼应**（同主奏乐器 + 同编制，只换拍号/调式/音区），
所以它们的相同轴是 3 根 —— 落在「≤4」的例外区间内；**其余任何一对都不得超过 2 根**。
直接照抄六首以上的专辑会重新撞车（N > 5 时必须扩轴值池，见第五节）。

## 五、N 首越多，值池越要扩（否则纪律撑不住）

| N | 拍号可用值 | 调式可用值 | 主奏乐器可用值 | 风险 |
|---|---|---|---|---|
| 3–6 | 6 | 5 | 6 | 低，靠编排就撑得住 |
| 7–9 | 8 | 7 | 8 | 中，开始要主动查矩阵 |
| 10–12 | 10 | 8 | 10 | 高，**必须让脚本逐对核对** |
| >12 | — | — | — | ⚠️ **不建议**：值池不够，差异纪律必然破。建议拆成两张专辑，或接受「分辑」结构 |

**值池不够时的正解**：不要为了凑 N 首而放宽「≤2 根轴」——
**宁可拆成两张专辑**（各有自己的锚点与收尾），也不要把 12 首塞成一张。

## 六、纯音乐专辑的标签池（音乐流向怎么排）

只用这一组段名，**按曲目实际需要的流向挑，不必全用**：

```text
Intro → Loop A → Loop B → Loop A2 → Loop C → End
```

| 标签 | 典型用途 | 里面写什么 |
|---|---|---|
| `Intro` | 序章、铺垫 | 独奏、留白、力度渐强 |
| `Loop A` | 主主题 | 主题旋律 + 1 件配器 |
| `Loop B` | 对比段 | 加鼓 / 加低八度 / 转和弦 |
| `Loop A2` | 变奏回归 | 换配器或换力度，保留主题 |
| `Loop C` | 高潮段 | 全奏、叠高八度、点缀 |
| `End` | 收束 | 回到开头和弦与织体、干净切断 |

**禁用**：`Verse` `Chorus` `Bridge` `Pre-Chorus` `Hook` —— 全都携带「有人唱」的语义。

## 七、封面提示词的母题写法（专辑级一致性）

一整套封面的**共用部分**（只写一次，放进每首提示词的公共段）：

```text
共用视觉母题：低饱和冷调（青灰 / 雾蓝 / 米白），颗粒质感胶片颗粒，
主体居中偏左，柔和漫射自然光，1:1 正方形，无文字边框
```

**每首变化的部分**：

```text
意象：<该曲的具体物象>；色调偏移：<同族内的微调>；
封面文字：<曲名>，纤细手写体，<右侧三分之一留白，竖排>
```

⚠️ 留白侧**尽量在整张专辑里交替**（右 → 左 → 右 → 上 → 左 → 上），
这样一整套排开时视觉有节奏，全放同一侧会像复制粘贴。
