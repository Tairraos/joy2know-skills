本文由 `@SKILL.md` 第七节路由到此。只在遇到「换模型 / 调风格强度 / 排除某类元素 / 保持同一个人声」时读取。

# Suno 模型与创作控制（v6 时代）

> ⚠️ Suno 的界面与型号会变。本文记录的是 **2026-09-25 从官方帮助中心（help.suno.com）核实的原话**；
> 你手上的版本若与本文不符，**以你当前界面的实际表现为准**，并把差异告诉用户。

## 一、模型怎么选

官方当前是 **v6 世代**，三个变体：

| 变体 | 官方定位（原文） | 可用等级 |
|---|---|---|
| **v6** | *"Our most advanced model… stronger control and precision when you want your idea to come through clearly."*（最先进；想把想法准确呈现时，控制力与精确度最强） | Pro / Premier |
| **v6-wild** | *"Built for experimentation… takes your ideas in less predictable directions."*（为实验而生，走向更难预测） | Pro / Premier |
| **v6-mini** | *"A faster, more efficient way to create with the v6 generation experience… brings improved music generation to the Free plan."*（更快更省，**把 v6 体验带到了免费方案**） | **所有用户（含免费）** |

**官方建议**（原文）：*"Start with v6 when you want the most control over your result, or try v6-wild when you're looking for a creative surprise."*
→ 要**可控**用 v6；要**惊喜**用 v6-wild。

**写作时的实际含义：**

- **免费账号只能用 v6-mini** —— 别在提示词里写「请用 v6 旗舰模型」，模型**不在提示词的控制范围内**，是界面上选的。
- 模型选择**不写进 Style**，也不靠提示词切换；在网页右上角的模型选择器里选。
- 时长：模型已从 30 秒短片发展到**最长约 8 分钟**；但免费账号的单次时长与额度另有限制（见第五节）。
- 本技能的语法（复合段落标签、行内指令、语言锁）**在 v4.5 到 v6 通用** —— 换模型**不需要**改写提示词结构。

## 二、两个（有时三个）滑杆：Creative Sliders

**位置**：Custom（自定义）模式的创作面板。
官方原文：*"Want to add some flavor to your tracks? Try Creative Sliders while making music in Custom mode."*

| 滑杆 | 范围 | 含义 |
|---|---|---|
| **Weirdness** | **Safe ↔ Chaos** | 官方原文：*"goes from Safe to Chaos, where **50% is the 'normal' expected result**"* —— **50% 是「正常预期结果」的基准点** |
| **Style Influence** | **Loose ↔ Strong** | 官方原文：*"lets you choose how close you stay to your style input from Loose to Strong"* —— 越靠 Strong，越贴合你写的 Style |
| **Audio Influence** | 官方未说明 | **仅在使用 Audio Upload（上传音频）时出现**：*"If you're using an Audio Upload, you'll also get a third slider"* |

**官方没有给出默认值与推荐调节值** —— **不要编造具体数值**。可以给的判断依据是：

- 希望「语言锁 / 方言锁」被严格执行 → **Style Influence 往 Strong 走**（Loose 会让它漂）
- 结果总「不够像想要的」→ 先调 Style Influence，再考虑改 Style 文本
- 结果总「太怪、唱腔跑偏」→ Weirdness 往 Safe 调（低于 50%）
- 想要意外惊喜 → Weirdness 往 Chaos 调（高于 50%），但**方言包与循环素材不要这么干**

## 三、排除不想要的元素（Exclude）

**位置（官方原文）**：Custom 模式 → **Advanced Options（高级选项）** → 菜单**第一项**就是 Exclude。
> *"Click on Advanced Options to open a menu that starts with Exclude"*
> *"Enter any information (instruments, etc) that you do not want in your track"*

**填什么**：写**不想要**的内容（乐器、流派、人声特征等），语义等同于 negative prompt
（官方该文的关键词标签里就包含 "negative prompt"）。

**官方原文没有给出分隔符或写法示例** —— 所以：**按英文逗号分隔枚举**是稳妥做法，
但**不要向用户声称这是官方规定的语法**。

**本技能最常用的一处**：纯器乐包压不住哼唱时，把 `vocals, singing, humming, vocalizations`
填进 Exclude（比在 Style 里写否定词可靠）。见 `@SKILL.md` 规则 2 的例外段。

## 四、人声一致性：Voices 与 Style Persona

- 官方已用 **Voices** 取代原来的 Personas 按钮；但 **Style Persona 仍保留在 Voices 之内**
  （官方原文：*"the Voices button has replaced Personas; however, Style Personas remain within Voices"*）。
- **Style Persona**：捕捉某首歌的整体「氛围 / 风格」，用于后续创作保持一致。
- **Voices**：可把自己的声音（或既有音频的人声特征）用到生成的歌里 ——
  官方原文：*"you can add your own voice into Suno-generated songs"*。

**什么时候该提这件事**：用户说「这几首歌要像同一个人唱的」「音色要和上一首一样」时 ——
这**不是提示词能稳定解决的问题**（同一段 `Soft breathy female vocals` 每次出的音色都会漂）。
正确做法是引导用户用 **Style Persona / Voices** 去锁，并明确讲出
**「人声一致性靠平台功能，不靠提示词」**。**不要**承诺「用同一段 Style 就能保证音色一致」。

## 五、相关能力与账号额度（用于回答用户提问，不是写提示词的事）

| 能力 | 官方要点 |
|---|---|
| **Extend** | 让歌变长，或给它一个新的结尾 —— 需要更长 BGM 时用 |
| **Stems** | Advanced Stem Separation 提供三种拆分模式；**stem 文件不额外消耗下载额度**（`Does not count as additional downloads beyond the song itself`） |
| **下载格式** | MP3 **所有套餐**都有（Web 与移动端）；WAV 仅 Pro/Premier；MIDI 仅 Premier，且需在 Suno Studio 创建 |
| **生成额度（免费）** | 50 credits/天，约 10 首/天 |
| **下载额度（免费）** | **终身最多 7 次**试用下载；`Trial downloads do not reset each month`；`for personal, non-commercial use only` |
| **额度计算规则** | 重下同一首不另计；多格式算一次；失败/中断不计；**未用完不结转** |

> 免费账号的**非商业**限制与「终身 7 次下载」是**账号层面的硬规则**，
> 与提示词写得好不好无关 —— 用户要用于商业项目（游戏、视频、客户交付）时应当如实提醒。
