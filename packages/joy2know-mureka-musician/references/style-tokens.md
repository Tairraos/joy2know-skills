本文由 `@SKILL.md` 第七节路由到此。风格栏的完整写法：路线 A（官方中文叙事式）与路线 B（英文 token 式）、正反例、融合配方。

# 风格栏写法（双路线，≤1000 字）

## 〇、两条路线怎么选

| | **路线 A：官方中文叙事式（默认）** | **路线 B：英文 token 式（备选）** |
|---|---|---|
| 长相 | 六段叙事长文（规则 8），270–430 字 | 七要素逗号关键词，1–2 行 |
| 来源 | **官方 58 个风格模板的写法**（2026-10-16 全量抓取实证，「做同款」直接填这种） | 社区评测 + 早期实测 |
| 适合 | 默认全走这条；细节控制力最强（可写时长、排除清单、和弦、歌词指导） | 用户点名要简洁；整首英文歌；快速迭代 |
| 语言 | 中文骨架 + 英文术语嵌入 | 英文为主 |

**两条路线同一条风格栏内不混用骨架**（英文术语嵌入除外）；判定走哪条看用户需求，没有需求就走 A。

## 一、路线 A：官方中文叙事六段式（骨架细节）

六段顺序与官方句式见 `@SKILL.md` 规则 8 的表格。本节补充**官方模板里验证过的细节规律**（58 样本统计）：

| 规律 | 数据 | 写法含义 |
|---|---|---|
| 否定排除是核心手法 | 「避免」90%、「不要」62% | 每条风格栏至少一段「避免 A、B、C」——排除流派/演奏行为/编曲元素 |
| 「避免爵士/Blues 色彩」 | 53% | 流行向曲目通用排除句，可直接借用 |
| 「时长约三分钟」 | 81% | 时长写进风格栏是官方标配；其他时长同理（「约两分钟」「约四分钟」） |
| 制作质量声明 | 60% | 「达到可正式发行的商业混音标准」——想要精致成品就带上 |
| 显式 BPM | **仅 17%** | 速度形容词（缓慢/中速/慢至中速）是官方主流；BPM 更精准，二者取一 |
| 优先级声明 | 67% | 「优先突出/优先建立/把 X 放在第一优先级」——决定模型注意力分配 |
| 流派 tag 中文可行 | 24% 模板中文开头 | 「中国仙侠流行」「当代 Mandopop」「正统老派 Boom Bap」——tag 语言跟题材走 |
| 人声性别 | 仅 12% 显式写 | 官方多数不写性别（交给界面「人声性别」选择）——写 alt 性别描述是加分不是必须 |
| 普通话 | 40% | 中文歌写「普通话人声」明确语言 |
| 字数 | 平均 347（269–426） | 写够细节即可，不堆满 |

**官方模板的两个「流派 tag 语言」正例：**
- 英文 tag：`Slowcore × Bedroom Emo × Ambient Rock`（通用题材）
- 中文 tag：`中国仙侠流行 × Ancient Chinese Ballad`（东方题材官方直接用中文 tag）

**高级字段式写法（官方 7% 模板，用户懂和声时可用）：**

```text
Deep House，124 BPM，key F minor。人声优先制作：气声女中音……。和声使用循环 minor7 House 和弦，
示例和弦：Fm7, Abmaj7, Dbmaj7, Eb9。Bass：滚动 bassline……。结构：贴近的主歌、更开阔的 hook……
情绪：深夜夜店……。结尾：最终 hook 后短促干净收尾。避免俗套 Big Room drop……
```

**歌词指导可以写进风格栏（官方模板实证）：**「搭配简短英文歌词」「写一段轻松易合唱的副歌，内容围绕……」——
语言与内容方向都能指定，具体歌词仍写在歌词栏。

## 二、路线 B：英文 token 七要素（简洁备选）

### 七要素与顺序

```
[曲风] + [BPM] + [人声] + [核心乐器] + [情绪] + [场景] + [混音]
```

| 要素 | 写法 | 正例 | 反例 |
|---|---|---|---|
| **曲风** | 英文流派词；融合取 2–3 个基色、以一个为主 | `folk blues` / `jazz ballad` / `Mandarin pop` | ✗ 只写「流行」「民谣」——漂移明显 |
| **速度** | BPM 数字（更精准）或速度形容词（官方主流） | `88 BPM` / `BPM 92 to 98` / 速度写「slow & steady」 | ✗ 速度位完全空着（听感随机）；✗ 写 `70-120` 宽区间（等于没写） |
| **人声** | `female vocal` / `male vocal` / `No vocals`，可加质感副词 | `breathy female vocal` / `gritty male vocal` | ✗ 器乐包写任何人声词 |
| **核心乐器** | 写到具体音色与演奏法 | `fingerpicked guitar + harmonica` / `upright bass + brushed drums` | ✗「钢琴伴奏」（太宽）；✗ 堆六七件乐器 |
| **情绪** | 2–3 个**不打架**的收敛词 | `warm and wistful` / `smoky and relaxed` | ✗ 同时写 `healing` 与 `depressing` |
| **场景** | 一句画面感场景（官方模板第三要素） | `late-night kitchen scene` / `rainy window seat` | （说不出可省，其余六项不可省） |
| **混音** | 一句质感 | `intimate room reverb` / `radio-ready production` | （可省） |

**完整正例（中文歌 + 英文 token）：**

```text
Mandarin folk blues, 88 BPM, emotional male vocal, fingerpicked guitar + harmonica + brushed drums,
warm and wistful, late-night kitchen scene, intimate room reverb
```

**纯器乐：** 首句 `No vocals`，全篇无人声词：

```text
No vocals, Ambient Cinematic, 72 BPM, solo grand piano + warm pads + subtle cello,
calm and spacious, wide reverb, seamless loop
```

> ⚠️ 风格里**只写风格，不写歌词**。两栏是独立字段，歌词塞进风格栏会被当风格词处理。
> ⚠️ 不写 Suno 那套 `Mandarin, Standard Mandarin Enunciation` 语言锁——Mureka 的人声语言靠
> **歌词栏的语言声明 + 歌词内容**体现，风格栏只管曲风与人声质感。

## 三、token 正反例速查（路线 B）

| 想要 | 写 | 别写 | 为什么 |
|---|---|---|---|
| 慢爵士 | `Jazz ballad, 72 BPM` | `爵士，慢一点` | 路线 B 是英文 token 式，中文关键词混进来漂移（要中文叙事请整条走路线 A） |
| 蓝调颗粒感人声 | `gritty male vocal` | `有颗粒感的嗓音` | 同上；且风格栏是独立字段不是聊天 |
| 律动感 | `swung drums, walking bass` | `有摇摆感` | 写到**演奏法**，不写形容词 |
| 复古质感 | `warm analog tape saturation` | `复古风` | 「复古」没有信息量 |
| 中文歌 | 曲风带 `Mandarin`（如 `Mandarin folk`） | 风格栏写「中文歌」 | 语言归属靠曲风词 + 歌词语言声明 |

## 四、融合配方（两路线通用；Mureka 官方鼓励风格融合）

**三条纪律：**

1. **基色 ≤3，以一个为主。** 主曲风写具体（`folk blues`），陪衬写特征（`jazz drums` / `bluesy guitar licks`）。
2. **融合写在曲风位，不散落全文。** `jazz folk, 84 BPM, …` 成立；`jazz + folk + rock + lo-fi, …` 不成立。
3. **情绪与配器要跟主曲风走。** 融合不是平均混——`folk blues` 的叙事感还在，蓝调只是和声与乐器的底色。

**本技能三大体裁的两两融合（已验证语义成立的起手式）：**

| 融合 | 起手 token | 听感定位 |
|---|---|---|
| 民谣 × 蓝调 | `folk blues, 80 BPM, fingerpicked guitar + harmonica` | 乡村蓝调，叙事 + 和声张力 |
| 爵士 × 民谣 | `jazz folk, 84 BPM, upright bass + brushed drums + fingerpicked guitar` | 民谣爵士，夜色咖啡馆 |
| 爵士 × 蓝调 | `jazz blues, 92 BPM, swung feel, electric guitar + organ` | 蓝调爵士，酒吧质感 |

**反例：** ✗ `jazz, blues, folk, rock, EDM, classical`——基色堆六个，模型只能自行发挥，结果四不像。
这种「都想一点」的需求，正确做法是问用户**以哪个为主**；答不上来就按默认治愈民谣走并在「假设与待替换」标注。
