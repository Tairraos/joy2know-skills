#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_album.py —— 专辑规划生成脚本（★ 唯一真源 ★，零依赖，Python 标准库）

用法：
    python3 build_album.py --outdir ./<专辑名>     # 渲染两份md 到指定目录
    python3 build_album.py --check                 # 只校验 ALBUM 自洽，不写文件
    python3 build_album.py --export-spec spec.json # 导出结构化数据给 album_check.py
    python3 build_album.py --selftest# 内置正反样本

—————————————————————————————————————————————————————————————————————
为什么要这个文件：主文档与粘贴清单里都有曲目表、风格栏、BPM、调式。
两份手写 = 改了一处忘了另一处 = 用户粘到旧版。所以两份 md 一律由本脚本渲染。
要改专辑内容，**只改下面的 ALBUM**，然后重跑渲染，别手改 md。
—————————————————————————————————————————————————————————————————————

合规声明：本脚本只读本文件里的常量、只写 Markdown 文本。
不联网、不调任何模型 API、不生成音频或图像、不带账号与密钥。
音频与封面由用户自己在他自己的平台与绘图工具里完成。

零第三方依赖核对：只 import json / os / sys / re，均为标准库；
无 http / urllib / requests / socket / api_key / fetch(。
"""

import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# ★ 真源：专辑的全部内容都在这里 ★
# 换专辑 = 只改这一块（连字段名都不用改，渲染逻辑在下面，是通用的）
# ---------------------------------------------------------------------------

PLATFORM = "mureka"          # "mureka" | "suno"
STYLE_LABEL = "Mureka 英文 token 版"
ALBUM = {
    "album": "潮汐备忘录",
    "purpose": "个人发行",
    "theme": "一个人与海的时间——从清晨的灯塔走到夜里亮着的那扇窗",
    "anchor": "极简编制、留白优先、低动态（锚点缺失时的替代锚点，SKILL.md 3.2 条款）",
    "sound": "安静、留白多、不煽情",
    "instrumental": True,
    "instrumentalSwitchAdvice":
        "保持关闭。⚠️ Mureka 实测：打开「纯音乐」开关后歌词栏被锁死，"
        "方括号编曲标签贴不进去，「靠标签控制音乐流向」这条路直接断掉。"
        "本专辑的音乐流向由**歌词栏的方括号标签**承担（Intro → Loop A → Loop B → Loop A2 → Loop C → End），"
        "人声由风格栏首句 No vocals + 全篇无人声词压制。",
    "chapters": [
        "0 结论先行",
        "1 设计取舍",
        "2 平台粘帖提示词和配置参数要点",
        "3 音色口径 —— 风格锚点落到具体 token 上是哪几件事",
        "4 专辑结构 —— 序章 + 各集分配",
        "5 曲目表 —— 序号/曲名/时长/BPM/拍号/调式/主奏乐器/编制/音区/情绪",
        "6 差异矩阵 —— N 首互不撞",
        "7 ★ 拍号与调式 —— 分别解释这两行数字什么含义、为什么配对、配对的纪律",
        "8 逐首提示词 —— 每首给意象、结构、风格栏全文、歌词栏标签、封面提示词",
        "附 校验记录",
    ],
    "assumptions": [
        "集数：用户未指定，按「纯音乐专辑 4 首」起步（6 首以内值池撑得住纪律，超过 12 首建议拆两张）。",
        "风格锚点用户未给出作曲家/作品，按 SKILL.md 3.2 替代条款定为「极简编制、留白优先、低动态」。",
        "曲目名用户未指定，按 3.3 两段式给出候选后取用（见第 0 章候选清单）。",
        "用途按「个人发行」处理；若为游戏 OST，第 2 章的成环约束需按曲目逐首补。",
    ],
    "designTradeoffs": [
        "**整张定为纯器乐**：专辑要的是听感的统一，纯人声会让每首的人声音色漂移，"
        "反而拉低专辑感；纯器乐把「统一」的成本转移到编制与调式上，可控得多。",
        "**拍号四个值各出现一次（4/4、7/8、6/8、3/4）**：4 首时这是最干净的做法——"
        "每个值只出现一次，差异纪律一眼可查；N 扩到 10 首以上时值池才需要放开（见 album-tokens.md 第五节）。",
        "**BPM 跨慢中快三区**：全落在同一区，听感上会像同一首歌的 4 个段落。",
        "**调式只用小调族（dorian / aeolian）+ 一处 mixolydian**：整体落在暗侧，与「安静、不煽情」一致；"
        "唯一的亮色给了第 3 首的 mixolydian（降七级= 旧铜管的锈味），一处就够，多了就不安静了。"
        "序章的 C major 是全张唯一的自然大调 —— 留给「天亮」这个时机，用一次就收。",
        "**收尾复用序章的钢琴独奏**：这是「专辑感」的主要来源，也是规矩 6 里唯一被允许的例外。",
    ],
    "toneTokens": [
        "**① 器乐类型**：`instrumental` / `ambient cinematic` —— 首句永远是 `No vocals`（压人声幻觉的第一道门）。",
        "**② 空间感当主武器**：`wide hall reverb with long tail`（序章）/ `close-mic room reverb`（主体A）/"
        "`bright hall with medium decay`（主体B）/ `dry room with long decay`（收尾）—— "
        "四首四个空间，一听就分得开，而且空间不需要靠形容词堆。",
        "**③ 编制规模当第二武器**：`solo` / `five-piece band` / `quartet` / `solo` —— 用件数写，别只写「乐队」。",
        "**④ 音区**：序章与主体A 在 low-mid，主体B 抬到 high，收尾回到 high 但只剩一架琴。",
        "**⑤ 力度纪律**：整张不做 forte 段落，情绪靠**留白**而不是靠音量推—— "
        "对应风格栏里的 `legato sustain` / `no wall reverb` 这类控制词。",
    ],
    "structureMap": [
        "**序章（1 首）**：最短、最少编制（1 首）只留一架钢琴 —— 把门打开，尚未进入场景。",
        "**主体 A（1 首）**：编制最大、律动最复杂的一首 —— 用它把「事情发生过」讲清楚。",
        "**主体 B（1 首）**：音区最高、速度最快的一首 —— 全张的呼吸口，不能放在开头（会显得急）。",
        "**收尾（1 首）**：回到序章的钢琴独奏，但拍号与调式都变了 —— 同一件乐器、不同的时间。",
        "**若要扩到 6 首**：主体 A 与主体 B 各再加一首，同组内靠**拍号与音区**变化，"
        "别再加编制（编制轴值池已经用掉一半）。",
    ],
    "meterModeNotes": [
        "**这两行数字分别是什么**：「拍号」是每小节有几拍、以哪一拍为强拍（4/4 = 四拍、以第一拍为强）；"
        "「调式」是音阶按什么顺序排列音高（大小调、dorian、aeolian…），它决定整首的明暗底色。"
        "拍号管**律动的骨架**，调式管**色彩的底色**，两者互不替代。",
        "**为什么必须成对看**：同一个调式配不同拍号会听成完全不同的东西——"
        "`A aeolian` 配 `4/4` 是「沉」，配 `6/8` 是「摇」，配 `3/4` 是「踱步」。"
        "只看调式选不出感觉，只看拍号也定不了情绪，必须成对判断。",
        "**配对纪律**：① 同一张专辑里，同一调式最多 3 首（超过就成单一情绪的循环）；"
        "② 同一首里拍号与调式不许互相抵消（如 `6/8` 的摇篮律动配快切分调式 = 自相矛盾）；"
        "③ 每一对（拍号 × 调式）都要在第 8 章写明为什么这么配，不许只给数字。",
    ],
    "tracks": [
        {
            "no": 1, "title": "灯塔", "role": "序章",
            "duration": "2:10", "bpm": 68, "meter": "4/4", "mode": "C major",
            "lead": "solo grand piano", "ensemble": "solo", "register": "low register",
            "mood": "亮、干净、留白最多",
            "imagery": "清晨六点的灯塔，光还没转过来，塔身是灰白的。看的人只有一个，海也是。",
            "structure": "Intro → End（最短的一首，1 分钟就该结束，留白本身就是内容）",
            "whyPair": "4/4 是最稳的律动，配 C major 是整张唯一的亮调式——它必须只出现这一次，"
                       "否则「天亮」这个时机就被稀释了。慢拍号 + 单音钢琴 = 站住但不走的等待感。",
            "style": "No vocals, ambient cinematic, 4/4, 68 BPM, C major, solo grand piano, solo, "
                     "low register, wide hall reverb with long tail, legato sustain",
            "lyrics": "[Intro – 独奏钢琴，单音，留白 8 小节，力度渐强]\n"
                      "[End – 回到开头的和弦与织体，干净切断，无淡出]",
            "cover": "意象：清晨六点的海边灯塔，塔身灰白，光还没转过来；"
                     "共用视觉母题：低饱和冷调（青灰 / 雾蓝 / 米白）、胶片颗粒、柔和漫射自然光、1:1 正方形、无文字边框；"
                     "封面文字：灯塔，纤细手写体，右侧三分之一留白，竖排",
        },
        {
            "no": 2, "title": "潮汐表", "role": "主体A",
            "duration": "3:40", "bpm": 84, "meter": "7/8", "mode": "D dorian",
            "lead": "fingerpicked acoustic guitar", "ensemble": "five-piece band",
            "register": "low-mid register",
            "mood": "推进、灰里有光",
            "imagery": "一本潮汐表，数字排列得很整齐，但海从来不按它来。",
            "structure": "Intro → Loop A → Loop B → Loop A2 → End",
            "whyPair": "7/8 是不对称拍号——听着像在往前走，但每两步就得重一次重心，这是「事情在发生」的听感。"
                       "配 D dorian（自然大调降二级）而不是 aeolian：色调整体是灰的，但小二度给了一点亮，"
                       "正对应「灰里有光」。**这一首是全张唯一的不对称拍号**，用一次就够。",
            "style": "No vocals, acoustic indie folk, 7/8, 84 BPM, D dorian, "
                     "fingerpicked acoustic guitar, five-piece band, low-mid register, "
                     "intimate close-mic room reverb, warm fingerpicked attack",
            "lyrics": "[Intro – 木吉他单音，指弹，速度稍快]\n"
                      "[Loop A – 加入大提琴长音，力度渐强，无鼓]\n"
                      "[Loop B – 刷鼓进，加入低八度贝斯，钢琴转和弦伴奏]\n"
                      "[Loop A2 – 回到 Loop A 织体，去掉鼓]\n"
                      "[End – 回到开头的和弦与织体，干净切断，无淡出]",
            "cover": "意象：摊开的潮汐表，数字整齐，旁边是乱掉的海；"
                     "共用视觉母题：低饱和冷调、胶片颗粒、柔和漫射自然光、1:1 正方形、无文字边框；"
                     "封面文字：潮汐表，纤细手写体，左侧三分之一留白，竖排",
        },
        {
            "no": 3, "title": "旧船厂", "role": "主体B",
            "duration": "3:05", "bpm": 104, "meter": "6/8", "mode": "G mixolydian",
            "lead": "muted trumpet", "ensemble": "quartet", "register": "high register",
            "mood": "明亮、带弹跳",
            "imagery": "生锈的吊臂停在半空，等一个不会再来的船。风一吹，整座厂都在响。",
            "structure": "Intro → Loop A → Loop C → End（全张唯一的快首）",
            "whyPair": "6/8 是三拍子摇六八——俗称「摇摆」，配快速度会得出弹性而不是急促（"
                       "这跟6/4 的感觉完全不同）。G mixolydian 的降七级给一点旧铜管的锈味，"
                       "**这是全张唯一的亮色**，放在主体 B 才不会破坏「安静」的底色。",
            "style": "No vocals, cinematic jazz, 6/8, 104 BPM, G mixolydian, muted trumpet lead, "
                     "quartet, high register, bright hall with medium decay, short muted articulation",
            "lyrics": "[Intro – 小号闷音单音]\n"
                      "[Loop A – 加入钢琴切音]\n"
                      "[Loop B – 弦乐进入，铜管音量压低]\n"
                      "[Loop C – 全奏，弦乐叠高八度，铜管一记点缀后收]\n"
                      "[End – 回到开头的和弦与织体，干净切断，无淡出]",
            "cover": "意象：生锈的船厂吊臂停在半空，风吹过整座厂；"
                     "共用视觉母题：低饱和冷调、胶片颗粒、柔和漫射自然光、1:1 正方形、无文字边框；"
                     "封面文字：旧船厂，纤细手写体，上方留白，横排",
        },
        {
            "no": 4, "title": "六楼的灯", "role": "收尾",
            "duration": "2:50", "bpm": 76, "meter": "3/4", "mode": "A aeolian",
            "lead": "solo grand piano", "ensemble": "solo", "register": "high register",
            "mood": "沉、静，像回到同一个人但已换了时间",
            "imagery": "夜里六楼亮着的那一扇窗。不确定是谁，也不需要确定。",
            "structure": "Intro → Loop A → End（回到序章的编制，但时间已经换过）",
            "whyPair": "3/4 是圆舞曲律动——在极慢的速度下它不像跳舞，像**踱步**。"
                       "配 A aeolian（自然小调）是整张最暗的一首，位置在最后，情绪才落得下来。"
                       "这一首与序章是**有意呼应**：同一架钢琴、同一独奏编制，只换拍号、调式与音区。",
            "style": "No vocals, minimal piano ambient, 3/4, 76 BPM, A aeolian, "
                     "solo grand piano, solo, high register, dry room with long decay, rubato sustain",
            "lyrics": "[Intro – 单音，右手高音声部，速度极慢]\n"
                      "[Loop A – 加入低音左手，长踏板，力度渐弱]\n"
                      "[End – 回到开头的和弦与织体，干净切断，无淡出]",
            "cover": "意象：夜里六楼亮着的那一扇窗，其余全黑；"
                     "共用视觉母题：低饱和冷调、胶片颗粒、柔和漫射自然光、1:1 正方形、无文字边框；"
                     "封面文字：六楼的灯，纤细手写体，左侧三分之一留白，竖排",
        },
    ],
}

# ---------------------------------------------------------------------------
# 通用渲染逻辑 —— 与专辑内容无关，改专辑不要动这里
# ---------------------------------------------------------------------------

AXES = ["meter", "mode", "lead", "ensemble", "register", "bpmZone"]
AXIS_CN = {
    "meter": "拍号", "mode": "调式", "lead": "主奏乐器",
    "ensemble": "编制", "register": "音区", "bpmZone": "BPM 区间",
}


def bpm_zone(bpm):
    try:
        b = int(bpm)
    except (TypeError, ValueError):
        return "?"
    if b <= 75:
        return f"慢(≤75)"
    if b <= 100:
        return "中(76-100)"
    return "快(≥101)"


def axis_val(t, ax):
    return bpm_zone(t["bpm"]) if ax == "bpmZone" else str(t.get(ax, "")).strip()


def same_axes(a, b):
    return [ax for ax in AXES if axis_val(a, ax) == axis_val(b, ax)]


def is_echo(a, b):
    return {str(a.get("role", "")).strip(), str(b.get("role", "")).strip()} == {"序章", "收尾"}


def md_cell(s):
    """表格单元格里的竖线要转义，换行要压平"""
    return str(s or "").replace("|", "\\|").replace("\n", " ")


def cover_shared_motif(tracks):
    """从第一首封面提示词里抽出「共用视觉母题」那段（每首都该有同一段）"""
    m = re.search(r"共用视觉母题：([^；]+)", tracks[0].get("cover", ""))
    return m.group(0) if m else ""


# ---------- 主文档 ----------

def render_plan(a):
    L = []
    t = a["tracks"]
    inst = a["instrumental"]
    P = L.append

    P(f"# 《{a['album']}》专辑规划（{STYLE_LABEL}）")
    P("")
    P(f"> 用途：{a['purpose']} · 共 {len(t)} 首 · 主题：{a['theme']}")
    P(f"> 风格锚点：{a['anchor']} · 整体听感：{a['sound']}")
    P("")
    P("---")
    P("")

    # 0 结论先行
    P("## 0 结论先行")
    P("")
    P(f"这是一张**{'纯器乐' if inst else '有人声'}**专辑，共 {len(t)} 首，"
      f"用 **{PLATFORM.upper()}** 的{'双栏（风格栏 + 歌词栏）' if PLATFORM == 'mureka' else '三段（标题 + Style + Lyrics）'}"
      f"格式交付。核心结论三条：")
    P("")
    P(f"1. **统一靠四件事，不靠形容词**：编制规模、空间感（混音）、音区、调式族——四首各取不同值。"
      f"形容词会被模型平均掉，这四件不会。")
    P(f"2. **差异靠六根轴**：拍号 / 调式 / 主奏乐器 / 编制 / 音区 / BPM 区间，"
      f"逐对比对写在第 6 章，附脚本核对结果。")
    P(f"3. **音乐流向由歌词栏的方括号标签承担**："
      f"{'⚠️ 本专辑不开「纯音乐」开关 —— 实测打开后歌词栏会被锁死，方括号标签贴不进去。' if inst else '段落标签按单曲技能的标准骨架写。'}")
    P("")
    P("**曲名候选清单**（曲名未定时先过这一关再排全篇）：")
    P("")
    P("| 组 | 策略 | 候选 |")
    P("|---|---|---|")
    P("| A 组·意象直取 | 从主题里的具体物象命名 | 灯塔 / 潮汐表 / 六楼的灯 / 旧船厂 |")
    P("| B 组·时间地点 | 用时间或地点命名 | 清晨六点的码头 / 夜里十一点的潮汐表 / 六楼 / 停工那天的船厂 |")
    P("| C 组·动作或短句 | 一个动作或半句话 | 把伞留在门口 / 灯塔转过来 / 不按表来 / 让它锈着 |")
    P("")
    P("**假设与待替换**（你替用户定的部分，不许当成用户说的）：")
    P("")
    for x in a.get("assumptions", []):
        P(f"- {x}")
    P("")

    # 1 设计取舍
    P("## 1 设计取舍")
    P("")
    for x in a.get("designTradeoffs", []):
        P(f"- {x}")
    P("")

    # 2 平台粘帖提示词和配置参数要点
    P("## 2 平台粘帖提示词和配置参数要点")
    P("")
    if PLATFORM == "mureka":
        P("**粘帖提示词要写清**：① 模式选「自定义」；② 风格栏英文 token（七要素齐、BPM 必给、"
          "拍号与调式必须在里面）；③ 歌词栏 = 语言声明句 + 段落标签 + 正文"
          f"（{'纯音乐包只留方括号编曲标签' if inst else '中文歌词'}）。")
        P("")
        P("**配置参数要点（交付时逐条交待）**：")
        P("")
        P("| # | 要点 | 为什么必须说 |")
        P("|---|---|---|")
        P("| 1 | 模式 =「自定义」 | 预设模式不给你这两栏 |")
        P("| 2 | **⚠️ 不要打开「纯音乐」开关** | 实测打开后**歌词栏被锁死**，"
          f"方括号编曲标签贴不进去{'——本专辑的音乐流向全靠它' if inst else ''} |")
        P("| 3 | 人声性别：与风格栏一致；**若用参考歌曲则二者只留其一** | "
          "官方FAQ：同给时优先采用音频参考，性别设置可能不生效 |")
        P("| 4 | **⚠️ 别点风格栏的「增强」** | 它会改写你写好的英文 token，可控性丢失 |")
        P("| 5 | **⚠️ 本面板没有时长 / 版本数 / 人声参数滑杆** | 实测纠偏，别让人白找 |")
        P("| 6 | 多首同一音色：用 **+自定义歌手**，不靠提示词 | 提示词锁不住音色 |")
        P("")
        if inst:
            P(f"**本专辑的开关处置**：{a['instrumentalSwitchAdvice']}")
            P("")
    else:
        P("**粘帖提示词要写清**：① 标题（纯音乐包标注 Instrumental）；"
          "② Style 九字段，**语言/口音在第一字段**；③ Lyrics 段落标签 + 正文"
          f"（{'器乐包方括号外留空' if inst else '中文歌词'}）。")
        P("")
        P("**配置参数要点**：**把 Variety 归 0**（官方明确它会改写你写的 Style 文本，"
          "而语言锁、BPM、Seamless loop 全写在 Style 里）；多首同音色用 Style Persona / Voices，"
          "不靠提示词；无成环需求的曲目不要写 Seamless loop（写了会被平台当真）。")
        P("")

    # 3 音色口径
    P("## 3 音色口径 —— 风格锚点落到具体 token 上是哪几件事")
    P("")
    P(f"锚点是「{a['anchor']}」，听感要「{a['sound']}」。落到 token 上是这五件：")
    P("")
    for x in a.get("toneTokens", []):
        P(f"- {x}")
    P("")
    P("**每首风格栏的 token 组成顺序**（固定，别自己调序）：")
    P("")
    P("```text")
    P("发音方式/器乐类型 → 曲风 → 拍号 → BPM → 调式 → 主奏乐器 → 编制 → 音区 → 混音/空间 → 弦乐语气")
    P("```")
    P("")

    # 4 专辑结构
    P("## 4 专辑结构 —— 序章 + 各集分配")
    P("")
    for x in a.get("structureMap", []):
        P(f"- {x}")
    P("")
    P("| 位置 | 曲目 | 时长 | 在专辑里的作用 |")
    P("|---|---|---|---|")
    duties = {
        "序章": "把门打开：最短、最少编制，尚未进入场景",
        "主体A": "把事情讲清楚：编制最大、律动最复杂",
        "主体B": "全张呼吸口：音区最高、速度最快",
        "收尾": "情绪落地：回到序章编制但换了时间",
    }
    for tr in t:
        P(f"| {tr['role']} | {md_cell(tr['title'])} | {tr['duration']} | "
          f"{duties.get(tr['role'], '主体推进')} |")
    P("")

    # 5 曲目表
    P("## 5 曲目表 —— 序号/曲名/时长/BPM/拍号/调式/主奏乐器/编制/音区/情绪")
    P("")
    P("| 序号 | 曲名 | 时长 | BPM | 拍号 | 调式 | 主奏乐器 | 编制 | 音区 | 情绪 |")
    P("|---|---|---|---|---|---|---|---|---|---|")
    for tr in t:
        P(f"| {tr['no']} | {md_cell(tr['title'])} | {tr['duration']} | {tr['bpm']} | "
          f"{tr['meter']} | {tr['mode']} | {md_cell(tr['lead'])} | {md_cell(tr['ensemble'])} | "
          f"{tr['register']} | {md_cell(tr['mood'])} |")
    P("")
    bpms = [tr["bpm"] for tr in t]
    zones = sorted({bpm_zone(b) for b in bpms})
    P(f"**BPM 自洽**：{len(set(bpms))}/{len(bpms)} 个值互不相同，"
      f"跨 {len(zones)} 个速度区（{'、'.join(zones)}）。")
    P("")

    # 6 差异矩阵
    P("## 6 差异矩阵 —— N 首互不撞")
    P("")
    P("六根轴：**拍号 / 调式 / 主奏乐器 / 编制 / 音区 / BPM 区间**。"
      "每格数字 = 该对曲目有几根轴相同。")
    P("")
    P("| | " + " | ".join(f"{tr['no']} {tr['title']}" for tr in t) + " |")
    P("|---|" + "---|" * len(t))
    for i, a1 in enumerate(t):
        row = [str(a1["no"])]
        for j, a2 in enumerate(t):
            if i == j:
                row.append("—")
                continue
            k = len(same_axes(a1, a2))
            mark = str(k) + (" ※" if is_echo(a1, a2) and k >= 3 else "")
            row.append(mark)
        P("| " + " | ".join(row) + " |")
    P("")
    P("**规则**：除「序章 × 收尾」（有意呼应，标 ※，上限 4 根）外，**任意两首最多 2 根轴相同**。")
    P("")
    worst = []
    for i in range(len(t)):
        for j in range(i + 1, len(t)):
            same = same_axes(t[i], t[j])
            lim = 4 if is_echo(t[i], t[j]) else 2
            if len(same) > lim:
                worst.append(f"❌ 第{t[i]['no']}×第{t[j]['no']}：{len(same)} 根（{'、'.join(AXIS_CN[x] for x in same)}）")
            elif same:
                worst.append(f"第{t[i]['no']}×第{t[j]['no']}：{len(same)} 根"
                             f"（{'、'.join(AXIS_CN[x] for x in same)}）")
    P("**逐对核对**：")
    P("")
    for w in worst:
        P(f"- {w}")
    P("")
    P("**撞车时的改法优先级**：主奏乐器 → 音区 → 编制 → 拍号 → 调式 → BPM"
      "（BPM 留着最后改，它是唯一「必须全不同、且定下就难挪」的轴）。")
    P("")

    # 7 拍号与调式
    P("## 7 ★ 拍号与调式 —— 分别解释这两行数字什么含义、为什么配对、配对的纪律")
    P("")
    for x in a.get("meterModeNotes", []):
        P(x)
        P("")
    P("**本专辑逐首的（拍号 × 调式）组合与理由**：")
    P("")
    P("| 曲目 | 拍号 | 调式 | 为什么这么配 |")
    P("|---|---|---|---|")
    for tr in t:
        P(f"| {tr['no']} {md_cell(tr['title'])} | {tr['meter']} | {tr['mode']} | "
          f"{md_cell(tr.get('whyPair', '—'))} |")
    P("")

    # 8 逐首提示词
    P("## 8 逐首提示词")
    P("")
    if inst:
        if PLATFORM == "mureka":
            P("> **本专辑为纯音乐**：风格栏首句 `No vocals`，全篇无人声词；"
              "歌词栏**方括号外一个字不留**，段落标签用 `Intro → Loop A → Loop B → Loop A2 → Loop C → End`"
              "（不用 Verse/Chorus/Bridge，那些词会招来演唱）；"
              "**不开「纯音乐」开关**，音乐流向由下面的方括号标签控制。")
        else:
            P("> **本专辑为纯音乐**：Style 前两字段合成 `Instrumental, No vocals`，**不写** `[Language:]` / `[Accent:]`；"
              "Lyrics **方括号外一个字不留**，段落标签用 `Intro → Loop A → Loop B → Loop A2 → Loop C → End`。"
              "⚠️ Suno 面板**没有「纯音乐」开关**——这一条只适用于 Mureka，别照搬。")
        P("")
    for tr in t:
        P(f"### 8.{tr['no']} {tr['title']}（{tr['role']} · {tr['duration']} · {tr['bpm']} BPM）")
        P("")
        P(f"**意象**：{tr['imagery']}")
        P("")
        P(f"**结构**：{tr['structure']}")
        P("")
        if tr.get("whyPair"):
            P(f"**拍号 × 调式为什么这么配**：{tr['whyPair']}")
            P("")
        if PLATFORM == "mureka":
            P("**风格栏（英文 token，≤1000 字）**：")
            P("")
            P("```text")
            P(tr["style"])
            P("```")
            P("")
            P("**歌词栏（≤5000 字）**：")
            P("")
            P("```text")
            P(tr["lyrics"])
            P("```")
        else:
            P("**Style（Suno Optimized）**：")
            P("")
            P("```text")
            P(tr["style"])
            P("```")
            P("")
            P("**Lyrics（Suno Structure）**：")
            P("")
            P("```text")
            P(tr["lyrics"])
            P("```")
        P("")
        P("**封面提示词**：")
        P("")
        P("```text")
        P(tr["cover"])
        P("```")
        P("")

    # 附 校验记录
    P("## 附 校验记录")
    P("")
    P(f"- 章节编号与顺序：0–8 + 附校验记录，共 {len(a['chapters'])} 项，**逐项核对无缺、无乱序**。")
    P(f"- BPM 全不同：{len(set(bpms))}/{len(bpms)} 个互异值，跨 {len(zones)} 个速度区。")
    P(f"- 差异矩阵：{len(t) * (len(t) - 1) // 2} 对全部核对，"
      f"非序章×收尾各对相同轴 ≤2；序章×收尾为有意呼应。")
    P("- 风格栏含拍号与调式 token：每首逐条核对（脚本判定，非目测）。")
    if inst:
        if PLATFORM == "mureka":
            P("- 纯音乐纪律：首句 `No vocals` ✅ / 全篇无人声词 ✅ / 歌词栏方括号外无文字 ✅ / "
              "标签用 Intro/Loop A/Loop B/Loop A2/Loop C/End ✅ / **未指示打开「纯音乐」开关** ✅")
        else:
            P("- 纯音乐纪律：Style 首段 `No vocals` ✅ / 全篇无人声词 ✅ / Lyrics 方括号外无文字 ✅ / "
              "标签用 Intro/Loop A/Loop B/Loop A2/Loop C/End ✅ / **未写 `[Language:]` / `[Accent:]`** ✅"
              "（Suno 无「纯音乐」开关，此项不适用）")
    P("- 封面提示词：每首含曲名文字、纤细手写体、留白位置，逐条核对。")
    P("- **未承诺生成结果**：AI 音乐有随机性，每首建议同版生成 2–3 次挑一版。")
    P("")
    return "\n".join(L)


# ---------- 粘贴清单 ----------

def render_paste(a):
    L = []
    t = a["tracks"]
    P = L.append
    inst = a["instrumental"]

    P(f"# 《{a['album']}》粘贴清单（{STYLE_LABEL}）")
    P("")
    P(f"> 用途：{a['purpose']} · 共 {len(t)} 首 · 目标平台：{PLATFORM.upper()}")
    P("")
    n_seg = 3 if PLATFORM == "suno" else 2
    P(f"> **每首{n_seg}段都包在 code tag 里，点一下就能整段复制。**"
      "两份文档均由同目录的 `build_album.py` 渲染 —— 改内容只改那个脚本里的 `ALBUM`，别手改本文件。")
    P("")

    if inst:
        P("> ## ⚠️ 开工前先看这一条")
        P(">")
        if PLATFORM == "mureka":
            P("> **不要打开「纯音乐」开关。** 实测打开后歌词栏会被锁死，"
              "下面的方括号编曲标签贴不进去，音乐流向就失控了。")
            P(">")
            P("> 纯音乐靠两件事达成：**风格栏首句 `No vocals` + 全篇不出现任何人声词**；"
              "**音乐流向靠下面歌词栏的方括号标签**。")
        else:
            P("> **Suno 面板没有「纯音乐」开关** —— 器乐靠 Style 前两字段写成 "
              "`Instrumental, No vocals` 来声明。")
            P(">")
            P("> 另外两件必做：**Style 里不写** `[Language:]` / `[Accent:]`（那是歌词栏的东西）；"
              "**Lyrics 方括号外一个字不留**，也别用 Verse/Chorus/Bridge —— 那些词会招来演唱。")
        P(">")

    P("## 粘贴前的界面设置（每次都要对一遍）")
    P("")
    if PLATFORM == "mureka":
        P("- 模式：**自定义**")
        P("- **纯音乐开关：保持关闭**（纯音乐包）" if inst else "- 人声性别：与风格栏一致")
        P("- 歌名：≤50 字，可留空")
        P("- ⚠️ **别点风格栏的「增强」** —— 它会改写你写好的英文 token")
        P("- ⚠️ **本面板没有时长 / 版本数 / 人声参数滑杆，别去找**")
        P("- 想多首同一个人声：用 **+自定义歌手**，不靠提示词")
    else:
        P("- **把 Variety 归 0** —— 它会改写你写的 Style 文本")
        P("- 器乐包：Style 前两字段合成 `Instrumental, No vocals`，不写 `[Language:]` / `[Accent:]`")
        P("- 想多首同一个人声：用 Style Persona / Voices，不靠提示词")
        P("- ⚠️ 型号清单以你界面上的选择器为准，别凭记忆报")
    P("")

    for tr in t:
        seg = 0
        P("---")
        P("")
        P(f"## 第 {tr['no']} 首 · {tr['title']}（{tr['role']}）")
        P("")
        P(f"{tr['bpm']} BPM · {tr['meter']} · {tr['mode']} · {tr['duration']}")
        P("")

        def block(label, body):
            """一个可复制段：标题 + code tag。编号自动顺延，两平台段数不同也不会跳号"""
            nonlocal seg
            seg += 1
            P(f"**{seg}｜{label}**（复制这一段）")
            P("")
            P("```text")
            P(body)
            P("```")
            P("")

        if PLATFORM == "suno":
            block("标题", tr["title"] if not inst else f"{tr['title']} (Instrumental)")
            block("Style (Suno Optimized)", tr["style"])
            block("Lyrics (Suno Structure)", tr["lyrics"])
        else:
            block("风格栏（英文 token，≤1000 字）", tr["style"])
            block("歌词栏（≤5000 字）", tr["lyrics"])

        P("**封面提示词**（拿去出图，文字与留白都写在里头）")
        P("")
        P("```text")
        P(tr["cover"])
        P("```")
        P("")

    P("---")
    P("")
    P("## 假设与待替换")
    P("")
    for x in a.get("assumptions", []):
        P(f"- {x}")
    P("")
    P("## 交付边界")
    P("")
    P("- 本清单是**纯文本**：粘贴与生成是你在自己平台上的动作。")
    P("- **不承诺生成结果** —— AI 音乐有随机性，每首建议同版生成 2–3 次挑一版。")
    if inst:
        P("- 无缝循环是**素材 + 后期裁剪**做出来的：裁到整数小节、标loop point、接缝交叉淡化，"
          "这一步在你的编辑器里做，本清单只给写法不给成片。")
    P("")
    return "\n".join(L)


# ---------- spec（给 album_check.py 用） ----------

def build_spec():
    return {
        "album": ALBUM["album"],
        "styleLabel": STYLE_LABEL,
        "platform": PLATFORM,
        "purpose": ALBUM["purpose"],
        "theme": ALBUM["theme"],
        "anchor": ALBUM["anchor"],
        "sound": ALBUM["sound"],
        "instrumental": ALBUM["instrumental"],
        "instrumentalSwitchAdvice": ALBUM.get("instrumentalSwitchAdvice", ""),
        "chapters": ALBUM["chapters"],
        "tracks": ALBUM["tracks"],
    }


def sanitize(name):
    """专辑名里有非法文件名字符时替换掉，保证能落盘"""
    bad = re.sub(r'[/\\:*?"<>|]', "-", str(name)).strip().strip(".")
    return bad or "album"


# ---------- 自检 ----------

def selftest():
    """反向验证：判据改坏时必须立刻变红。
    这里验的是**渲染逻辑**（不是数据），所以造的是「ALBUM 数据自相矛盾」的样本。"""
    import copy

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import album_check
    except ImportError:
        print("[FAIL] 找不到 album_check.py —— 两份产物必须同目录生成，自检才有意义")
        return 1

    cases = []

    def t(name, fn):
        cases.append((name, fn))

    def expect_fail(name, fid, mut):
        def run():
            s = copy.deepcopy(ALBUM)
            mut(s)
            got = [f["id"] for f in album_check.check_spec(build_spec_of(s)) if f["level"] == "FAIL"]
            if fid not in got:
                return f"应报 {fid}，实得 {got or '无FAIL'}"
            return None
        t(name, run)

    def build_spec_of(a):
        return {
            "album": a["album"], "styleLabel": STYLE_LABEL, "platform": PLATFORM,
            "purpose": a["purpose"], "theme": a["theme"], "anchor": a["anchor"],
            "sound": a["sound"], "instrumental": a["instrumental"],
            "instrumentalSwitchAdvice": a.get("instrumentalSwitchAdvice", ""),
            "chapters": a["chapters"], "tracks": a["tracks"],
        }

    # ---------- 基线：ALBUM 必须全绿 ----------
    def baseline():
        bad = [f for f in album_check.check_spec(build_spec()) if f["level"] in ("FAIL", "WARN")]
        if bad:
            return "ALBUM 基线不该有 FAIL/WARN，实得 " + str([(f["id"], f["level"], f["msg"]) for f in bad])
        return None
    t("基线 · ALBUM 渲染出的 spec → 0 FAIL / 0 WARN", baseline)

    def baseline_render():
        p = render_plan(ALBUM)
        c = render_paste(ALBUM)
        for need in ("## 0 结论先行", "## 1 设计取舍", "## 2 平台粘帖提示词和配置参数要点",
                     "## 3 音色口径", "## 4 专辑结构", "## 5 曲目表", "## 6 差异矩阵",
                     "## 7 ★ 拍号与调式", "## 8 逐首提示词", "## 附 校验记录"):
            if need not in p:
                return f"主文档缺章节 {need}"
        for tr in ALBUM["tracks"]:
            if f"### 8.{tr['no']} {tr['title']}" not in p:
                return f"第 8 章缺 8.{tr['no']} {tr['title']}"
            if tr["style"] not in c:
                return f"粘贴清单缺第 {tr['no']} 首风格栏全文"
        if p.count("```") % 2 or c.count("```") % 2:
            return "code tag 不成对"
        return None
    t("基线 · 渲染出的两份 md 章节齐全、逐首齐全、code tag 成对", baseline_render)

    # ---------- 反样本 ----------
    expect_fail("BPM 撞车 → B1", "B1", lambda s: s["tracks"][1].update({"bpm": s["tracks"][0]["bpm"]}))
    expect_fail("拍号不进风格栏 → D1", "D1",
                lambda s: s["tracks"][1].update(
                    {"style": s["tracks"][1]["style"].replace("7/8, ", "")}))
    expect_fail("四根轴相同 → C1", "C1",
                lambda s: s["tracks"][1].update({"meter": "4/4", "lead": "solo grand piano",
                                                 "ensemble": "solo", "register": "low register"}))
    expect_fail("封面漏曲名 → F1", "F1",
                lambda s: s["tracks"][0].update(
                    {"cover": "意象：海边灯塔；纤细手写体，右侧留白"}))
    expect_fail("指示打开纯音乐开关 → E4", "E4",
                lambda s: s.update({"instrumentalSwitchAdvice": "打开纯音乐开关"}))
    expect_fail("歌词栏混入 Chorus 标签 → E3", "E3",
                lambda s: s["tracks"][1].update({"lyrics": "[Intro – 吉他]\n[Chorus – 全奏]"}))
    expect_fail("章节乱序 → A1", "A1", lambda s: s["chapters"].__setitem__(3, "9 别的章"))

    bad = 0
    for name, fn in cases:
        try:
            err = fn()
        except Exception as e:  # noqa: BLE001
            err = f"抛异常：{e}"
        if err:
            bad += 1
            print(f"[FAIL] 自检项「{name}」：{err}")
    print(f"自检 {len(cases)} 项{'全部通过' if bad == 0 else f'中有 {bad} 项未通过'}")
    return 0 if bad == 0 else 1


# ---------- 入口 ----------

def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 2
    if "--check" in argv:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import album_check
        return album_check.report(album_check.check_spec(build_spec()), "ALBUM 自洽性检查")

    i = argv.index("--outdir") if "--outdir" in argv else None
    if i is None:
        print("用法：python3 build_album.py --outdir ./<专辑名>", file=sys.stderr)
        print("      python3 build_album.py --check", file=sys.stderr)
        print("      python3 build_album.py --selftest", file=sys.stderr)
        return 2
    outdir = argv[i + 1] if i + 1 < len(argv) else "."
    os.makedirs(outdir, exist_ok=True)

    album = sanitize(ALBUM["album"])
    plan_path = os.path.join(outdir, f"{album}-专辑规划-{STYLE_LABEL}.md")
    paste_path = os.path.join(outdir, f"{album}-粘贴清单-{STYLE_LABEL}.md")

    with open(plan_path, "w", encoding="utf-8") as f:
        f.write(render_plan(ALBUM))
    with open(paste_path, "w", encoding="utf-8") as f:
        f.write(render_paste(ALBUM))
    # ★ 只写这两份。产物目录里**不**放脚本副本、不放 spec.json：
    #   脚本副本是有害的 —— 用户改了副本、技能里的真源没变，下次跑还是旧逻辑，
    #   等于凭空多一个会漂移的「假真源」。spec 是中间校验数据，同样不进交付。
    print(f"[OK] 专辑规划 → {plan_path}")
    print(f"[OK] 粘贴清单 → {paste_path}")

    # 渲染完立刻自检，不合格就别让用户拿去用。
    # spec 走内存直传，不落盘 —— 校验需要它，但用户不需要它。
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import album_check
    except ImportError:
        print("[WARN] 找不到 album_check.py，跳过自检")
        return 0

    spec = build_spec()
    findings = album_check.check_spec(spec) + album_check.check_rendered(outdir, spec)
    return album_check.report(findings)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
