本文由 `@SKILL.md` 第七节路由到此。风格栏的完整写法：七要素、token 正反例、融合配方。

# 风格栏写法（英文 token，≤1000 字）

## 一、七要素与顺序

```
[曲风] + [BPM] + [人声] + [核心乐器] + [情绪] + [场景] + [混音]
```

| 要素 | 写法 | 正例 | 反例 |
|---|---|---|---|
| **曲风** | 英文流派词；融合取 2–3 个基色、以一个为主 | `folk blues` / `jazz ballad` / `Mandarin pop` | ✗ 只写「流行」「民谣」——漂移明显 |
| **BPM** | 具体数字或窄区间 | `88 BPM` / `BPM 92 to 98` | ✗ 不写速度（听感随机）；✗ 写 `70-120` 宽区间（等于没写） |
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

## 二、token 正反例速查

| 想要 | 写 | 别写 | 为什么 |
|---|---|---|---|
| 慢爵士 | `Jazz ballad, 72 BPM` | `爵士，慢一点` | 中文 token 漂移 |
| 蓝调颗粒感人声 | `gritty male vocal` | `有颗粒感的嗓音` | 同上；且风格栏是独立字段不是聊天 |
| 律动感 | `swung drums, walking bass` | `有摇摆感` | 写到**演奏法**，不写形容词 |
| 复古质感 | `warm analog tape saturation` | `复古风` | 「复古」没有信息量 |
| 中文歌 | 曲风带 `Mandarin`（如 `Mandarin folk`） | 风格栏写「中文歌」 | 语言归属靠曲风词 + 歌词语言声明 |

## 三、融合配方（Mureka 官方鼓励风格融合）

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
