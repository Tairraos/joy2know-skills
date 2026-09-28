本文由 `@SKILL.md` 第七节路由到此。只在遇到「模型版本怎么处理 / 调控件 / 排除元素 / 保持同一个人声」时读取。

> **本文只讲两件事：**怎么写提示词、交付时要交代哪几个界面动作 ——
> 不含任何平台侧的账号事务，也不要主动向用户提。

# Suno 控件与版本（v6 世代）

> **两处来源，分开标，别混：**
> - **【官方】** = Suno 官方帮助中心（help.suno.com）与应用内文案，直接引用原文；
> - **【实测】** = 2026-09-25 在一台账号的 `suno.com/create` 里逐控件读出来的现状。
>
> Suno 的界面与型号会变。本文记录的是以上时点的实况；**你手上的版本若与本文不符，
> 以你当前界面的实际表现为准**，并把差异告诉用户。

## 一、模型版本：默认按 `v6-mini` 写，**不要问**

**【实测】型号不在提示词的控制范围内。** 别在 Style 里写「请用 v6」；型号在**界面的选择器里选**。

- **默认按 `v6-mini` 写。** 它是当前所有用户都能选到的型号，按它写不会有人用不上。
- **不要问用户用哪个型号，也不要问账号情况。** 绝大多数产出只是「写提示词」，与型号无关。
- **用户自己提到版本时，按他说的那个版本优化。** 各型号之间**提示词写法几乎一样** ——
  本技能的复合段落标签、行内指令、语言锁通用，**换版本不需要重写结构**；
  差别只在风格描述可以写多细（型号能力越强，越吃得住细粒度指令）。
  用户不提，就按 `v6-mini` 往下走，**不要反问**。
- **不要凭记忆报型号清单。** v6 家族于 2026-09-09 上线，v4.5 / v5 / v5.5 同日全部退役，
  选择器里不再提供旧版。旧作仍可播放与分享，但对它们做续写 / 翻制 / 重制时**跑在 v6 上**。
  **选择器里当前有什么，以用户界面为准**，别背结论。
- **语法与长度限制**（v6 世代，2026-09 实况）：Style 1000 / Lyrics 5000 / Exclude 1000（字符），
  单次最长 8 分钟。

## 二、Custom 模式的控件清单

**【实测】** 位置：Advanced（自定义）模式 → 折叠面板 **More Options**。

> ⚠️ 早期资料把这个面板叫 "Advanced Options"。2026-09-25 实测按钮名是 **More Options**。

| 控件 | 实测形态与默认值 | 作用 |
|---|---|---|
| **Vocal Gender** | `Male` / `Female`，默认不选 | 人声性别。**要与 Style 里的 vocal 描述保持一致** |
| **Duration** | `Custom` / `Auto`，默认 **Auto** | Auto 交给模型定长度；Custom 自填秒数（上下限以你界面为准） |
| **Max Mode** | `Off` / `On`，默认 **Off** | 花更多算力换一致性。官方点名适合：超过两分钟的歌 / 贴近原曲的 cover / 风格迁移 / 全程保持人声与风格一致；**并明确说「短歌与快速试想法，标准模式就够了」** |
| **Weirdness** | 滑杆，默认 **50%** | Safe ↔ Chaos，结果的**常规程度** |
| **Style Influence** | 滑杆，默认 **50%** | Loose ↔ Strong，**贴不贴**你写的 Style |
| **Variety** | 滑杆，默认 **Normal** | **会改写你的 Style 文本**（第三节，本技能红线） |
| **Personalize** | `My Taste` / `Off` / `On`，默认 **Off** | 把你的**口味画像（My Taste）**注入本次生成。**它也会动 Style 文本**，但只在你**点魔杖**时发生 —— 见第三节之二 |
| **Exclude / Exclude Styles** | **本次实测未出现** | 负面提示；见第四节 |

**三个滑杆是三件不同的事** —— 社区常把它们混成一个「创意度」旋钮，于是流传的建议互相矛盾：

| 控件 | 作用对象 | 什么时候动它 |
|---|---|---|
| **Variety** | **你的 Style 文本本身** | 要让标签**逐字生效** → 归 0 |
| **Style Influence** | 对 Style 的**遵从度** | 结果总跑偏 → 往 Strong |
| **Weirdness** | 结果的**常规程度** | 想要意外 → 往 Chaos；**50% 才是基准，不是「关」** |

## 三、Variety：唯一会**在提交时静默**改写你 Style 的控件（本技能红线）

> **措辞修正（2026-09-26）**：本节早先写的是「唯一会改写你 Style 的控件」。
> 核实官方帮助中心后必须加限定词 —— **`Personalize`（My Taste）也会改写 Styles 框里的文本**，
> 只是它**要你主动点魔杖**才发生、当场可见；而 Variety 是**提交时静默发生**、事后读 `metadata.tags` 才查得出。
> 两者都要防，见**第三节之二**。

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

**【实测对照 · 2026-09-26｜同一账号、同一天】** 上面这段官方说法，现在有**行为级**证据了，
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

## 三之二、Personalize（My Taste）：第二个会动 Style 的控件

**【官方原文 · 帮助中心「My Taste」】**：

> *"With Style Augmentation enabled, any time you use the Magic Wand, the resulting style input will reflect your listening and creation habits."*

**中文翻译**：当 Style Augmentation（风格增强）开启时，你每次使用魔杖，最终生成的风格输入都会反映你的收听与创作习惯。

**中文解读**：这句指的是 **Styles 框右上角那支魔杖** —— 点它之后填进 Styles 框的那段文字，不是你写的，
也不是模型凭空写的，而是**从你的口味画像里长出来的**。官方发布说明的说法是 My Taste 会学习
「你反复回到的流派与情绪」（*"Suno learns what you're drawn to: your favorite genres and the moods you keep coming back to"*），
且**面向所有用户开放**。

**【与 Variety 的分工，别混为一谈】**

| | **Variety** | **Personalize（My Taste）** |
|---|---|---|
| 触发方式 | **自动** —— 提交时发生，你不点也在发生 | **手动** —— 只在你点魔杖时发生 |
| 改什么 | 你写的 Style 文本（扩写 / 润色） | **替换 / 扩写** Styles 框里的内容，掺入你的历史口味 |
| 能不能当场察觉 | **不能**（0 报错，只能事后读 `metadata.tags` 比对） | 能（框里的字当场就变了） |
| 要 Style 逐字生效 | **归 0** | **保持 Off，且不要点魔杖** |

**硬性动作：交付给别人用的包、以及将来要复现的包 —— `Personalize` 保持 `Off`，并附一句「不要用魔杖润色这段 Style」。**
风格确实需要扩充时，**由本技能来扩**（可控、可复核、可 diff）；**不要交给魔杖**。

**【未证实，不要当结论讲】** 有第三方资料称 My Taste 还会在「提示词描述不足时」影响默认的流派 / 情绪 /
结构倾向，甚至在没有提示词时也能生成。官方帮助中心我核到的**只有上面那条「魔杖」路径**，
**没有核到「不点魔杖也会偏置」的官方表述**，所以本技能**不把它当事实**。
用户问起时按「官方只说了魔杖那条路」回答。

**两个入口，别只关一个**：`More Options` 里的 `Personalize` 管**本次生成**；账号级总开关在**头像菜单**里
（官方原文：*"My Taste is enabled by default but you can view, edit, or disable My Taste by clicking on your avatar photo"*
→ 中文翻译：My Taste 默认开启，但你可以点头像、从下拉菜单里查看、编辑或关闭它）。
**画像本身是账号级的**，所以「这次关掉」不等于「它不再学习」。

## 四、排除不想要的元素（Exclude）

**【官方原文】**（转述）：Custom 模式下展开选项菜单后，第一项是 Exclude ——
*"Enter any information (instruments, etc) that you do not want in your track"*（填入你不想要的内容，如乐器等）。

**填什么**：写**不想要**的东西（乐器、流派、人声特征），语义等同 negative prompt。

**写法**：【官方】没有给出分隔符或示例 —— 所以**按英文逗号枚举**是稳妥做法，
但**不要向用户声称这是官方规定的语法**。

**【实测】2026-09-25 的 `More Options` 里没有看到该字段**（同一面板里 Vocal Gender、Duration、
Max Mode、Weirdness、Style Influence、Variety、Personalize 都在，唯独没有它）。
这可能是版本灰度，也可能是账号差异 —— **以你界面为准，有就用，没有就走下面第 2 条**。

**本技能最常用的一处**：纯器乐包压不住哼唱时，把 `vocals, singing, humming, vocalizations` 填进 Exclude
（比在 Style 里写否定词可靠）。**没有这个字段时不要卡住**，改走另一条：
① Style 简化到 4–7 个标签（堆太多会互相抵消）；② 全篇不出现任何人声词（**包含语言与发音要求**）；
③ 换更「纯器乐」的流派词（环境 / 氛围 / 后摇比 pop、trap、soul 稳得多）。
并如实告诉用户仍可能出现垫音人声 —— **不要承诺「一定没有人声」**。
（见 `@SKILL.md` 规则 2 的例外段与第九节。）

## 五、人声一致性：Voices 与 Style Persona

- 官方已用 **Voices** 取代原来的 Personas 按钮；但 **Style Persona 仍保留在 Voices 之内**
  （官方原文：*"the Voices button has replaced Personas; however, Style Personas remain within Voices"*）。
- **Style Persona**：捕捉某首歌的整体「氛围 / 风格」，用于后续创作保持一致。
- **Voices**：可把自己的声音（或既有音频的人声特征）用到生成的歌里 ——
  官方原文：*"you can add your own voice into Suno-generated songs"*。

**什么时候该提这件事**：用户说「这几首歌要像同一个人唱的」「音色要和上一首一样」时 ——
这**不是提示词能稳定解决的问题**（同一段 `Soft breathy female vocals` 每次出的音色都会漂）。
正确做法是引导用户用 **Style Persona / Voices** 去锁，并明确讲出
**「人声一致性靠平台功能，不靠提示词」**。**不要**承诺「用同一段 Style 就能保证音色一致」。

## 六、相关能力（回答用户提问时用，与写提示词无关）

| 能力 | 要点 |
|---|---|
| **Extend** | 让歌变长，或给它一个新的结尾 —— 需要更长 BGM 时用 |
| **单次时长** | v6 家族都能单次生成到 8 分钟 |
| **Stems** | Advanced Stem Separation 提供多种拆分模式 |

> 具体能用到哪些、有哪些限制，**以用户当前界面的实际表现为准** ——
> 本技能不描述、也不承诺平台侧的账号能力。
