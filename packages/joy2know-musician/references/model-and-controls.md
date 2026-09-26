本文由 `@SKILL.md` 第七节路由到此。只在遇到「换模型 / 调控件 / 排除元素 / 保持同一个人声」时读取。

# Suno 模型与创作控制（v6 世代）

> **两处来源，分开标，别混：**
> - **【官方】** = Suno 官方帮助中心（help.suno.com）与应用内文案，直接引用原文；
> - **【实测】** = 2026-09-25 在一台**免费账号**的 `suno.com/create` 里逐控件读出来的现状。
>
> Suno 的界面与型号会变。本文记录的是以上时点的实况；**你手上的版本若与本文不符，
> 以你当前界面的实际表现为准**，并把差异告诉用户。

## 一、模型：v6 家族三档（v6 之前的型号已全部退役）

**【实测】** 模型选择器（`ALL MODELS`）里只有三档：

| 变体 | 官方定位（原文） | 可用等级 |
|---|---|---|
| **v6** | *"Powerful. Versatile. Refined. Our best model yet."*（强大、全能、精致，目前最好的模型） | **Pro / Premier**（带 `Pro` 角标） |
| **v6-wild** | *"Best for experimental ideas."*（最适合实验性想法） | **Pro / Premier**（带 `Pro` 角标） |
| **v6-mini** | *"A free, more efficient version of premium v6 models."*（v6 付费型号的免费、更高效版本） | **所有用户（含免费）**（无角标） |

- **v6 家族于 2026-09-09 上线，v4.5 / v5 / v5.5 同日全部退役**，选择器里不再提供任何旧版。
  旧作仍可播放与分享，但对它们做续写 / 翻制 / 重制时**跑在 v6 上**。
- **免费账号只能选 v6-mini。** 想知道自己是哪一档，看一眼选择器：带 `Pro` 角标的是付费型号。
- **语法与长度限制没有变**：Style 1000 / Lyrics 5000 / Exclude 1000 / 单次最长 8 分钟。
- **本技能的语法（复合段落标签、行内指令、语言锁）在 v4.5 到 v6 通用** —— 换型号**不需要**重写提示词结构。
- **型号不在提示词的控制范围内。** 别在 Style 里写「请用 v6」；型号在界面右上角的选择器里选。

**对写作的实际含义**：免费用户要面对的是**当前免费档可选的那个型号** —— 2026-09-25 是 `v6-mini`。
所以本技能的默认姿态是「**面向免费档做优化**」，具体四条动作见第四节。
免费档优化**不是**降级写法，而是在免费档的额度与控件限制下把命中率做高。

## 二、Custom 模式的控件清单

**【实测】** 位置：Advanced（自定义）模式 → 折叠面板 **More Options**。

> ⚠️ 早期资料把这个面板叫 "Advanced Options"。2026-09-25 实测按钮名是 **More Options**。

| 控件 | 实测形态与默认值 | 作用 |
|---|---|---|
| **Vocal Gender** | `Male` / `Female`，默认不选 | 人声性别。**要与 Style 里的 vocal 描述保持一致** |
| **Duration** | `Custom` / `Auto`，默认 **Auto** | Auto 交给模型定长度；Custom 自填秒数（上下限以你界面为准） |
| **Max Mode** | `Off` / `On`，默认 **Off** | 花更多算力换一致性；**消耗翻倍**（见第四节） |
| **Weirdness** | 滑杆，默认 **50%** | Safe ↔ Chaos，结果的**常规程度** |
| **Style Influence** | 滑杆，默认 **50%** | Loose ↔ Strong，**贴不贴**你写的 Style |
| **Variety** | 滑杆，默认 **Normal** | **会改写你的 Style 文本**（第三节，本技能红线） |
| **Personalize** | `My Taste` / `Off` / `On`，默认 **Off** | 用你的历史口味做个性化 |
| **Exclude / Exclude Styles** | **本次实测未出现** | 负面提示；见第五节 |

**三个滑杆是三件不同的事** —— 社区常把它们混成一个「创意度」旋钮，于是流传的建议互相矛盾：

| 控件 | 作用对象 | 什么时候动它 |
|---|---|---|
| **Variety** | **你的 Style 文本本身** | 要让标签**逐字生效** → 归 0 |
| **Style Influence** | 对 Style 的**遵从度** | 结果总跑偏 → 往 Strong |
| **Weirdness** | 结果的**常规程度** | 想要意外 → 往 Chaos；**50% 才是基准，不是「关」** |

## 三、Variety：唯一会改写你 Style 的控件（本技能红线）

**【官方原文】**（v6 FAQ）：

> *"The Variety slider is designed to introduce variety in your outputs by **adjusting and updating your style prompts**. If you'd like to retain full control of your style tags, **reduce the Variety slider to 0**."*

**中文翻译**：Variety 滑杆是为了给你的产出引入变化而设计的，它的做法是**调整并更新你的风格提示词**。
如果你希望完整掌控自己的风格标签，请**把 Variety 滑杆调到 0**。

**中文解读**：Variety 不是「给音频加随机性」，它改的是**你写的那段文字**。
非 0 的 Variety 意味着「模型收到的提示词不是你写的那个」。这正是 v6 上线后最常见的抱怨
——「我精心调的 Style 标签好像被无视了」「一句简短 Style 回来变成一大段」——的机制。

**这条为什么对音乐人是致命的。** 本技能把三样关键东西全放在 Style 里：
**语言锁 / 方言防破音指令 / 器乐声明**（规则 2），外加 **BPM 与 `Seamless loop`**（循环路径）。
Variety 默认是 `Normal`，它会**在你提交之后改写这段文本** ——
你写的 `Cantonese, Cantopop, Traditional Cantonese Enunciation` 可能被扩写成别的东西，
而**全程 0 报错**，你只会看到「这首歌好像不太像我要的」。

**【实测对照 · 2026-09-26｜同一账号、同一免费档、同一天】** 上面这段官方说法，现在有**行为级**证据了，
不再只是文档背书。同一类「构造过的」Style 分两次提交，读回 Suno 最终写进 `metadata.tags` 的内容：

| 提交时 Variety | Suno 最终记下的 tags | 判定 |
|---|---|---|
| **`Balanced`**（≠ 0） | **被改写** —— `instrumental only, no vocals` → `instrumental`；`heartwarming, loopable` → `arranged for a seamless loop` | 你写的文本**没有原样到达模型** |
| **`0` / `Off`** | **与提交的 Style 逐字一致**（逐词比对，无一丢失） | **逐字生效** |

两组之间**只有一个变量**（Variety），所以这不是巧合。还要注意 `Balanced` 那组被改掉的恰好是**末几位**
（`no vocals`、`loopable`）—— 也就是最容易被「顺手润色」的短标签，而不是整段消失，
**肉眼几乎看不出来**；只有把 `metadata.tags` 拉出来逐词比对才会发现。
本技能的器乐声明、`Seamless loop`、BPM 恰好都属于这类「短标签」，正是重灾区。

**硬性动作：凡是用本技能产出的包，交付时都带上一句「把 Variety 归 0」。**

- 语言锁 / 方言包 → **必须归 0**
- 器乐与循环包（BPM 与 `Seamless loop` 都写在 Style 里）→ **必须归 0**
- 只有「就是要惊喜、不在乎标签逐字生效」时，才让它留在 Normal 或以上

**另一个坑：不要把滑杆数值写进 Style 文本框。** 那是给模型读的文字，不是控件。
写 `Weirdness: 20%` 不会移动滑杆，反而可能被当成风格描述的一部分。

## 四、免费档怎么优化（本技能的默认姿态）

免费档 == 现在能用 `v6-mini`。优化动作是**四条具体的**，不是「写得简单点」：

1. **Variety 归 0。** 否则语言锁与 BPM 都可能被悄悄改写（第三节）。
2. **别指望 Exclude。** 【实测】2026-09-25 免费账号的 More Options 里**没有**这个字段。
   纯器乐压不住哼唱时，改走另一条：**Style 简化到 4–7 个标签 + 全篇不出现任何人声词 + 换更纯器乐的流派词**
   （环境 / 氛围 / 后摇比 pop、trap、soul 稳得多）。见 `@SKILL.md` 规则 2 的例外段与第九节。
3. **Max Mode 想清楚再开。** 【官方】它「花更多算力把这次生成做对」、**消耗更多积分**；
   官方点名适合：**超过两分钟的歌 / 贴近原曲的 cover / 风格迁移 / 全程保持人声与风格一致**；
   并明确说「**短歌与快速试想法，标准模式就够了**」。
   换算到免费账号：一次生成 2 首共 **10 credits**，开 Max Mode 就是 **20**；免费额度 **50 credits/天**。
4. **额度是硬约束，要留重试预算。** 50 credits/天 ≈ 10 首。
   本技能默认建议「同一版生成 2–3 次挑一次」，循环素材更费（见 `@references/game-bgm-loop.md`）——
   免费用户请把这两件事一起讲清楚，而不是只给提示词。

**还必须如实告诉免费用户的两条账号层限制**（与提示词写得好坏无关）：

- **无商业授权。** 官方明确免费档产出**仅限个人非商业使用**。要用于游戏 BGM、客户交付、任何变现 → 需要 Pro 及以上。
- **下载额度极紧。** 终身仅数次试用下载，且**不按月重置**。生成很多、能留下的很少。

## 五、排除不想要的元素（Exclude）

**【官方原文】**（转述）：Custom 模式下展开选项菜单后，第一项是 Exclude ——
*"Enter any information (instruments, etc) that you do not want in your track"*（填入你不想要的内容，如乐器等）。

**填什么**：写**不想要**的东西（乐器、流派、人声特征），语义等同 negative prompt。

**写法**：【官方】没有给出分隔符或示例 —— 所以**按英文逗号枚举**是稳妥做法，
但**不要向用户声称这是官方规定的语法**。

**【实测】2026-09-25 免费账号的 More Options 里没有看到该字段**（同一面板里 Vocal Gender、Duration、
Max Mode、Weirdness、Style Influence、Variety、Personalize 都在，唯独没有它）。
这可能是账号档位差异或版本灰度 —— **以你界面为准，有就用，没有就走第四节第 2 条的替代路径**。

**本技能最常用的一处**：纯器乐包压不住哼唱时，把 `vocals, singing, humming, vocalizations` 填进 Exclude
（比在 Style 里写否定词可靠）。**没有这个字段时不要卡住**，按第四节第 2 条走，
并如实告诉用户仍可能出现垫音人声 —— **不要承诺「一定没有人声」**。

## 六、人声一致性：Voices 与 Style Persona

- 官方已用 **Voices** 取代原来的 Personas 按钮；但 **Style Persona 仍保留在 Voices 之内**
  （官方原文：*"the Voices button has replaced Personas; however, Style Personas remain within Voices"*）。
- **Style Persona**：捕捉某首歌的整体「氛围 / 风格」，用于后续创作保持一致。
- **Voices**：可把自己的声音（或既有音频的人声特征）用到生成的歌里 ——
  官方原文：*"you can add your own voice into Suno-generated songs"*。

**什么时候该提这件事**：用户说「这几首歌要像同一个人唱的」「音色要和上一首一样」时 ——
这**不是提示词能稳定解决的问题**（同一段 `Soft breathy female vocals` 每次出的音色都会漂）。
正确做法是引导用户用 **Style Persona / Voices** 去锁，并明确讲出
**「人声一致性靠平台功能，不靠提示词」**。**不要**承诺「用同一段 Style 就能保证音色一致」。

## 七、相关能力与账号额度（用于回答用户提问，不是写提示词的事）

| 能力 | 要点 |
|---|---|
| **Extend** | 让歌变长，或给它一个新的结尾 —— 需要更长 BGM 时用 |
| **单次时长** | v6 家族**所有三档**都能单次生成到 8 分钟；免费档的实际体验受额度限制 |
| **Stems** | Advanced Stem Separation 提供多种拆分模式；stem 文件不额外消耗下载额度 |
| **下载格式** | MP3 **所有套餐**都有；WAV 仅 Pro/Premier；MIDI 仅 Premier，且需在 Suno Studio 创建 |
| **生成额度（免费）** | 50 credits/天，约 10 首/天；一次生成 2 首共 10 credits；**Max Mode 翻倍** |
| **下载额度（免费）** | 终身仅数次试用下载；不按月重置；**仅个人非商业** |
| **额度计算规则** | 重下同一首不另计；多格式算一次；失败/中断不计；**未用完不结转** |

> 免费账号的**非商业**限制与**极紧的下载额度**是**账号层面的硬规则**，
> 与提示词写得好不好无关 —— 用户要用于商业项目（游戏、视频、客户交付）时应当如实提醒。
