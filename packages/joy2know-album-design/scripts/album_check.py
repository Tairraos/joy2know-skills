#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
album_check.py —— 专辑规划自检（零依赖，Python 标准库）

用法：
    python3 album_check.py <spec.json>
    python3 album_check.py <spec.json> --md-dir <目录>     # 连渲染出来的两份 md 一起查
    python3 album_check.py --selftest                      # 内置正反样本

spec.json 由 build_album.py --export-spec 产出（唯一真源在 build_album.py 的 ALBUM 里）。

六条门禁（对应 SKILL.md 第十节）：
  ① 章节编号和顺序对得上        ② N 首 BPM 全不同
  ③ 任意两首相同轴 ≤ 2      ④ 每首风格栏都含拍号和调式 token
  ⑤ 纯音乐专辑：歌词栏无方括号外文字、无 Verse/Chorus/Bridge、无人声词、
     且**不得让用户打开「纯音乐」开关**
  ⑥ 封面提示词每首都含曲名文字与留白位置

退出码：0 = 无 FAIL；1 = 有 FAIL（含自检失败）；2 = 用法错误 / 文件读不了
纪律：WARN 不影响退出码，但逐条打印（不允许静默）；每条错误必须给出下一步动作。
"""

import json
import os
import re
import sys

# ---------- 常量 ----------

REQUIRED_CHAPTERS = [
    "0 结论先行",
    "1 设计取舍",
    "2 平台粘帖提示词和配置参数要点",
    "3 音色口径",
    "4 专辑结构",
    "5 曲目表",
    "6 差异矩阵",
    "7 ★ 拍号与调式",
    "8 逐首提示词",
    "附 校验记录",
]

REQUIRED_TRACK_COLUMNS = [
    "no", "title", "duration", "bpm", "meter", "mode",
    "lead", "ensemble", "register", "mood",
]

MODE_WORDS = [
    "major", "minor", "dorian", "aeolian", "mixolydian", "phrygian",
    "lydian", "locrian", "ionian", "harmonic minor", "melodic minor",
]

# 六根差异轴
AXES = ["meter", "mode", "lead", "ensemble", "register", "bpmZone"]

BPM_SLOW_MAX = 75
BPM_MID_MAX = 100

VOCAL_FORBIDDEN = r"vocal|singer|humming|hum\b|chant|ooh|aah|choir|人声|歌声|哼唱|哼鸣"
VOCAL_TAG_FORBIDDEN = r"verse|chorus|bridge|pre-?chorus|hook"
SWITCH_FORBIDDEN = r"打开\s*纯音乐|开启\s*纯音乐|勾选\s*纯音乐|打开\s*instrumental\s*开关"

# ★ 唯一一条有名有姓的例外：序章 × 收尾是**有意呼应**（同一件乐器、不同和声），
# 所以这两首允许的相同轴上限比其他任何一对宽。其余所有曲目对一律 ≤2。
# 这条例外写在SKILL.md 第五节与 album-tokens.md 第三节，只表述一次。
ECHO_MAX_SAME_AXES = 4


# ---------- 工具 ----------

def bpm_zone(bpm):
    try:
        b = int(bpm)
    except (TypeError, ValueError):
        return "?"
    if b <= BPM_SLOW_MAX:
        return "slow"
    if b <= BPM_MID_MAX:
        return "mid"
    return "fast"


def norm(s):
    """归一化：去首尾空白 + 压掉内部多余空白（英文 token 比对用）"""
    return re.sub(r"\s+", " ", str(s or "").strip())


def lower(s):
    return norm(s).lower()


def mode_token(mode):
    """从 'C major' / 'D harmonic minor' 里取出调式词本身"""
    m = lower(mode)
    for w in ("harmonic minor", "melodic minor"):
        if w in m:
            return w
    for w in MODE_WORDS:
        if re.search(r"\b" + re.escape(w) + r"\b", m):
            return w
    return None


def strip_vocal_declarations(text):
    """先剥掉 No vocals / Instrumental 这两个器乐声明词再查人声词——
    否则声明本身会被误报（'no vocals' 里含 'vocal'）。"""
    return re.sub(r"\bno\s+vocals?\b", "", text or "", flags=re.I)\
        .replace("Instrumental", "").replace("instrumental", "")


def tag_lines(lyrics):
    out = []
    for raw in (lyrics or "").split("\n"):
        t = raw.strip()
        if t.startswith("[") and t.endswith("]"):
            out.append(t)
    return out


def outside_bracket_lines(lyrics):
    out = []
    for raw in (lyrics or "").split("\n"):
        t = raw.strip()
        if t and not (t.startswith("[") and t.endswith("]")):
            out.append(t)
    return out


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---------- 核心校验 ----------

def check_spec(spec):
    """按 spec（六条门禁）校验，返回 findings 列表。
    finding = {id, level, msg, hint?}"""
    F = []

    def add(fid, level, msg, hint=None):
        item = {"id": fid, "level": level, "msg": msg}
        if hint:
            item["hint"] = hint
        F.append(item)

    tracks = spec.get("tracks") or []
    instrumental = bool(spec.get("instrumental"))
    n = len(tracks)

    # ---- ① 章节编号和顺序 ----
    if not tracks:
        add("A0", "FAIL", "spec 里没有 tracks",
            "spec 是 build_album.py --export-spec 产出的；先在 build_album.py 的 ALBUM 里填 tracks 再导出")
        return F

    if n < 2:
        add("A1", "WARN", f"只有 {n} 首",
            "单首不构成专辑（单首要交给单曲技能）。N 建议 3–12，超过 12 差异纪律必然破")

    # 章节比对：以「逐项比对」为准，不以列表整体相等为准——
    # 合法的章节标题允许带「—— 说明」后缀（如「5 曲目表 —— 序号/曲名/…」），
    # 拿整体相等当闸门会把这些合法写法误判成「整体不符」（2026-10-16 实测踩到）。
    chapters = spec.get("chapters") or []
    first_diff = None
    for i, want in enumerate(REQUIRED_CHAPTERS):
        got = chapters[i] if i < len(chapters) else "（缺）"
        if norm(got).split("——")[0].strip() != want:
            first_diff = f"第 {i + 1} 项应为「{want}」，实得「{got}」"
            break
    if first_diff:
        add("A1", "FAIL", "主文档章节编号或顺序不对：" + first_diff,
            "按 SKILL.md 第七节的骨架逐项对齐：0…8 + 附 校验记录，一章不少、顺序不变")
    elif len(chapters) > len(REQUIRED_CHAPTERS):
        add("A1", "WARN", f"章节列表有 {len(chapters)} 项，多于骨架的 {len(REQUIRED_CHAPTERS)} 项",
            "骨架外的额外章节会打乱「一章不少、顺序不变」的契约，确认是有意为之")
    if "校验记录" not in " ".join(chapters):
        add("A1", "FAIL", "章节列表末尾缺「附 校验记录」", "校验记录是交付的一部分，不是可选附录")

    # ---- 曲目表列齐全 ----
    for t in tracks:
        missing = [c for c in REQUIRED_TRACK_COLUMNS if norm(t.get(c)) in ("", "?", "待定")]
        if missing:
            add("A2", "FAIL",
                f"第 {t.get('no', '?')} 首「{t.get('title', '?')}」曲目表缺列：{', '.join(missing)}",
                "曲目表十列必须齐全：序号/曲名/时长/BPM/拍号/调式/主奏乐器/编制/音区/情绪")

    # ---- ② N 首 BPM 全不同 ----
    seen = {}
    for t in tracks:
        b = t.get("bpm")
        try:
            bi = int(b)
        except (TypeError, ValueError):
            add("B1", "FAIL", f"第 {t.get('no', '?')} 首 BPM 不可解析：{b!r}",
                "BPM 必须是具体整数；不许写区间（区间会让循环点落在小节中间）")
            continue
        if bi in seen:
            add("B1", "FAIL",
                f"BPM 撞车：第 {seen[bi]} 首与第 {t.get('no', '?')} 首都是 {bi} BPM",
                "规矩 5：N 首 BPM 必须全不同。改其中一首（改最后一首，别的轴先留着）")
        else:
            seen[bi] = t.get("no", "?")
    zones = {bpm_zone(t.get("bpm")) for t in tracks} - {"?"}
    if len(zones) < 3 and n >= 3:
        add("B2", "WARN", f"BPM 只落在 {len(zones)} 个速度区（{', '.join(sorted(zones))}），建议 ≥3",
            f"慢 ≤{BPM_SLOW_MAX} / 中 {BPM_SLOW_MAX + 1}–{BPM_MID_MAX} / 快 ≥{BPM_MID_MAX + 1}；"
            "全集落在同一区会听不出起伏")

    # ---- ③ 任意两首相同轴 ≤ 2 ----
    def axis_val(t, ax):
        if ax == "bpmZone":
            return bpm_zone(t.get("bpm"))
        return norm(t.get(ax))

    for i in range(n):
        for j in range(i + 1, n):
            ti, tj = tracks[i], tracks[j]
            same = [ax for ax in AXES if axis_val(ti, ax) == axis_val(tj, ax)]
            roles = {norm(ti.get("role")), norm(tj.get("role"))}
            is_echo = roles == {"序章", "收尾"}
            limit = ECHO_MAX_SAME_AXES if is_echo else 2
            note = "（序章 × 收尾，有意呼应，例外上限 4）" if is_echo else ""
            if len(same) > limit:
                add("C1", "FAIL",
                    f"第 {ti.get('no')} 首「{ti.get('title')}」与第 {tj.get('no')} 首"
                    f"「{tj.get('title')}」有 {len(same)} 根轴相同：{', '.join(same)}{note}",
                    f"规矩 6：任意两首最多 {limit} 根轴相同。"
                    "改法优先级 主奏乐器 → 音区 → 编制 → 拍号 → 调式 → BPM；改完必须重算全表")
            elif is_echo and len(same) >= 3:
                add("C2", "WARN",
                    f"序章「{ti.get('title')}」与收尾「{tj.get('title')}」相同轴达 {len(same)} 根："
                    f"{', '.join(same)}",
                    "呼应过头就听不出「同一张专辑的两个极端」了。建议收到 3 根以内："
                    "至少让音区或拍号分开一档")

    # ---- ④ 每首风格栏都含拍号和调式 token ----
    for t in tracks:
        style = norm(t.get("style"))
        meter = norm(t.get("meter"))
        if meter and meter not in style:
            add("D1", "FAIL",
                f"第 {t.get('no')} 首「{t.get('title')}」风格栏里没有拍号 token「{meter}」",
                "规矩 2：拍号必须写进风格栏，只写在表格里是**名义轴**、生成时不生效")
        mt = mode_token(t.get("mode"))
        if mt and mt not in style.lower():
            add("D1", "FAIL",
                f"第 {t.get('no')} 首「{t.get('title')}」风格栏里没有调式 token「{mt}」",
                f"规矩 2：调式必须写进风格栏。本专辑标称 {t.get('mode')}，风格栏却没有「{mt}」")
        if not re.search(r"\b\d{2,3}\s*BPM\b|\bBPM\s*\d{2,3}\b", style, re.I):
            add("D2", "FAIL", f"第 {t.get('no')} 首风格栏没有 BPM 数字",
                "写具体数字（专辑内全不同）；不要写区间")
        if len(style) > 1000:
            add("D2", "FAIL", f"第 {t.get('no')} 首风格栏 {len(style)} 字，超过 1000",
                "并句删冗词，别删信息块（拍号/调式/BPM 是必留块）")

        # ---- ⑤ 纯音乐专辑的纪律 ----
        if instrumental:
            stripped = strip_vocal_declarations(style)
            m = re.search(VOCAL_FORBIDDEN, stripped, re.I)
            if m:
                add("E1", "FAIL",
                    f"第 {t.get('no')} 首器乐风格栏出现人声词「{m.group(0)}」",
                    "规矩 3：全篇不得出现 vocal/singer/humming/choir/ooh —— 写了等于反向指令，"
                    "模型会用哼唱把人声补回来")
            if not re.match(r"^\s*no\s+vocals?\b", style, re.I):
                add("E1", "FAIL",
                    f"第 {t.get('no')} 首器乐风格栏首句不是 No vocals",
                    "首句必须写 No vocals（或 Instrumental）")
            out = outside_bracket_lines(t.get("lyrics"))
            if out:
                add("E2", "FAIL",
                    f"第 {t.get('no')} 首歌词栏方括号外有内容（首处：「{out[0][:20]}」）",
                    "规矩 3：纯音乐包方括号外一个字不留——不留标题行、不留空行占位")
            for tag in tag_lines(t.get("lyrics")):
                bad = re.search(VOCAL_TAG_FORBIDDEN, tag, re.I)
                if bad:
                    add("E3", "FAIL",
                        f"第 {t.get('no')} 首段落标签出现「{bad.group(0)}」（{tag[:24]}）",
                        "纯音乐禁用 Verse/Chorus/Bridge/Pre-Chorus/Hook，改用 "
                        "Intro → Loop A → Loop B → Loop A2 → Loop C → End")
            tags = tag_lines(t.get("lyrics"))
            if tags:
                first = re.sub(r"^\[|\].*$", "", tags[0]).strip()
                if not re.match(r"intro\b", first, re.I):
                    add("E3", "WARN", f"第 {t.get('no')} 首第一个段落标签是「{first}」，建议从 Intro 起",
                        "纯音乐段名池：Intro → Loop A → Loop B → Loop A2 → Loop C → End")

        # ---- ⑥ 封面提示词 ----
        cover = norm(t.get("cover"))
        title = norm(t.get("title"))
        if not cover:
            add("F1", "FAIL", f"第 {t.get('no')} 首没有封面提示词",
                "规矩 7：每首必附封面提示词")
        else:
            if f"封面文字：{title}" not in cover:
                add("F1", "FAIL",
                    f"第 {t.get('no')} 首封面提示词没有逐字点名「封面文字：{title}」",
                    "规矩 7：封面提示词必须点名曲名文字，且与曲目表逐字一致（用户拿到图才知道要加什么字）")
            if not re.search(r"手写|handwriting|script|handwritten", cover, re.I):
                add("F1", "FAIL", f"第 {t.get('no')} 首封面提示词没指定字体（要「纤细手写体」）",
                    "补「纤细手写体」；不指定字体用户得自己找字")
            if not re.search(r"留白|negative space|留|blank", cover, re.I):
                add("F1", "FAIL", f"第 {t.get('no')} 首封面提示词没指定留白位置",
                    "写清哪一侧留白放字，如「右侧三分之一留白，竖排」")
            if not re.search(r"左侧|右侧|上方|下方|左|右|上|下|留白", cover):
                add("F2", "WARN", f"第 {t.get('no')} 首封面留白侧写得含糊",
                    "写「左侧/右侧/上方/下方」之一；整张专辑留白侧交替排更有节奏")

    # ---- 纯音乐：不得让用户打开「纯音乐」开关（全 spec 扫） ----
    if instrumental:
        advice = norm(spec.get("instrumentalSwitchAdvice"))
        if not advice:
            add("E4", "FAIL", "spec 缺 instrumentalSwitchAdvice",
                "纯音乐专辑必须在该字段写明「保持关闭」，并解释歌词栏标签怎么控制音乐流向")
        elif re.search(SWITCH_FORBIDDEN, advice):
            add("E4", "FAIL",
                "instrumentalSwitchAdvice 里出现了「打开纯音乐开关」的指示",
                "⚠️ Mureka 实测：打开「纯音乐」开关后**歌词栏被锁死**，方括号编曲标签贴不进去。"
                "正确做法：开关保持关，靠风格栏首句 No vocals + 歌词栏方括号标签控制音乐流向")
        elif not re.search(r"关闭|不开|保持关|不要开|别开", advice):
            add("E4", "WARN", "instrumentalSwitchAdvice 没明确说开关怎么处理",
                "写「保持关闭」并说明靠歌词栏标签控流向，别让执行者自己去猜")

    return F


def check_rendered(md_dir, spec):
    """连渲染出来的两份 md 一起查：文件在不在、粘贴清单有没有把三段包进 code tag"""
    F = []

    def add(fid, level, msg, hint=None):
        item = {"id": fid, "level": level, "msg": msg}
        if hint:
            item["hint"] = hint
        F.append(item)

    style_label = norm(spec.get("styleLabel")) or "风格版"
    album = norm(spec.get("album"))
    plan = os.path.join(md_dir, f"{album}-专辑规划-{style_label}.md")
    paste = os.path.join(md_dir, f"{album}-粘贴清单-{style_label}.md")

    # ★ 交付只有**两份** md。产物目录里不允许再出现脚本副本或 spec.json ——
    #   脚本副本是有害的：用户改了副本、技能里的真源没变，下次跑还是旧逻辑，
    #   等于凭空多一个会漂移的「假真源」。spec 是中间校验数据，用户不需要它。
    for p, what in ((plan, "专辑规划"), (paste, "粘贴清单")):
        if not os.path.isfile(p):
            add("G1", "FAIL", f"{what}不存在：{os.path.basename(p)}",
                "两份产物必须同在一个目录；跑 build_album.py --outdir 生成")

    # 封面提示词不是第三份文件——它就在粘贴清单的每首下面，单独成文件反而会与清单不一致
    for p, what in ((plan, "专辑规划"), (paste, "粘贴清单")):
        if not os.path.isfile(p):
            continue
        txt = read_text(p)
        if "封面提示词" not in txt:
            add("G1", "FAIL", f"{what}里没有「封面提示词」段",
                "封面提示词是粘贴清单每首的一部分，不是独立文件——确认没把它拆成第三份")

    # 多余产物检测：本目录只应有两份 md
    if os.path.isdir(md_dir):
        expected = {os.path.basename(plan), os.path.basename(paste)}
        extra = []
        for name in sorted(os.listdir(md_dir)):
            full = os.path.join(md_dir, name)
            if not os.path.isfile(full):
                continue
            if name in expected:
                continue
            if name in ("album-spec.json", "build_album.py", "album_check.py") or name.endswith(".json"):
                extra.append(name)
        if extra:
            add("G7", "FAIL", "产物目录里有多余文件：" + "、".join(extra),
                "交付只有专辑规划与粘贴清单两份 md。脚本与 spec 不进交付目录——"
                "脚本副本会让用户改到「假真源」，下次跑还是旧逻辑")

    if os.path.isfile(plan):
        txt = read_text(plan)
        idx = []
        for ch in REQUIRED_CHAPTERS:
            num = ch.split(" ")[0]
            m = re.search(r"^#{1,4}\s*" + re.escape(num) + r"[、\.．\s]", txt, re.M)
            idx.append(m.start() if m else -1)
        missing = [REQUIRED_CHAPTERS[i] for i, v in enumerate(idx) if v < 0]
        if missing:
            add("G2", "FAIL", "主文档缺章节：" + "、".join(missing),
                "骨架必须 0…8 + 附 校验记录，一章不少")
        present = [(REQUIRED_CHAPTERS[i], idx[i]) for i in range(len(idx)) if idx[i] >= 0]
        for (c1, p1), (c2, p2) in zip(present, present[1:]):
            if p1 > p2:
                add("G2", "FAIL", f"主文档章节顺序错了：{c1} 出现在 {c2} 之后",
                    "编号与顺序必须一致")
                break
        # 曲目表十列表头
        head = re.search(r"^\|\s*序号.*\|.*$", txt, re.M)
        if not head:
            add("G3", "FAIL", "主文档里找不到曲目表表头（应以「| 序号 |」开头）",
                "第 5 章要有一张表看全：序号/曲名/时长/BPM/拍号/调式/主奏乐器/编制/音区/情绪")
        else:
            for col in ("曲名", "时长", "BPM", "拍号", "调式", "主奏乐器", "编制", "音区", "情绪"):
                if col not in head.group(0):
                    add("G3", "FAIL", f"曲目表缺「{col}」列",
                        "十列齐全：序号/曲名/时长/BPM/拍号/调式/主奏乐器/编制/音区/情绪")
        # 附校验记录必须真有内容（不许空着充数）
        tail = txt.split("校验记录")[-1]
        if not re.search(r"[0-9]", tail):
            add("G4", "FAIL", "「附 校验记录」是空的",
                "校验记录要写实际跑出来的结论与数字，空附录等于没检")

    if os.path.isfile(paste):
        txt = read_text(paste)
        blocks = re.findall(r"```[a-z]*\n(.*?)```", txt, re.S)
        if not blocks:
            add("G5", "FAIL", "粘贴清单里没有 code tag 包裹的文本块",
                "每首的段落都要包在 code tag 内，方便用户一键复制")
        for t in spec.get("tracks", []):
            title = norm(t.get("title"))
            style = norm(t.get("style"))
            if style and style not in norm(txt):
                add("G5", "FAIL",
                    f"粘贴清单里找不到第 {t.get('no')} 首的风格栏全文",
                    "粘贴清单必须逐字含风格栏全文；两份文档都由 build_album.py 渲染，不许手写")

        # 段号必须连续（两平台段数不同：Suno 三段、Mureka 两段）。
        # 曾出现过「1｜标题 → 3｜歌词栏」跳号—— 用户按序号找会找错段。
        expect_seg = 3 if norm(spec.get("platform")) == "suno" else 2
        for chunk in txt.split("\n## 第 ")[1:]:
            nos = [int(x) for x in re.findall(r"\*\*(\d+)｜", chunk)]
            if not nos:
                continue
            if nos != list(range(1, len(nos) + 1)):
                add("G6", "FAIL",
                    f"第 {chunk.split(' 首')[0]} 首的段号不连续：{nos}",
                    f"本平台每首应有 {expect_seg} 段，段号必须 1..{expect_seg} 连续")
            elif len(nos) != expect_seg:
                add("G6", "FAIL",
                    f"第 {chunk.split(' 首')[0]} 首有 {len(nos)} 段，应为 {expect_seg} 段"
                    f"（platform={spec.get('platform')}）",
                    "Suno 三段（标题 / Style / Lyrics）、Mureka 两段（风格栏 / 歌词栏），别串")

    return F


# ---------- 报告 ----------

def report(findings, title="专辑规划自检"):
    fails = [f for f in findings if f["level"] == "FAIL"]
    warns = [f for f in findings if f["level"] == "WARN"]
    print(f"—— {title} ——")
    if not findings:
        print("[OK] 六条门禁全部通过（0 FAIL / 0 WARN）")
    for f in findings:
        tag = "[FAIL]" if f["level"] == "FAIL" else "[WARN]"
        print(f"{tag} {f['id']} {f['msg']}")
        if f.get("hint"):
            print(f"       ↳ {f['hint']}")
    print(f"—— {len(fails)} FAIL / {len(warns)} WARN ——")
    return 1 if fails else 0


# ---------- 自检（正反样本）----------

def _good_spec():
    return {
        "album": "潮汐备忘录",
        "styleLabel": "Mureka 英文 token 版",
        "purpose": "个人发行",
        "theme": "一个人与海的时间",
        "anchor": "极简编制、留白优先、低动态",
        "sound": "安静、留白多、不煽情",
        "instrumental": True,
        "instrumentalSwitchAdvice": "保持关闭：靠风格栏首句 No vocals 与歌词栏方括号标签控制音乐流向",
        "chapters": list(REQUIRED_CHAPTERS),
        "tracks": [
            {
                "no": 1, "title": "灯塔", "role": "序章",
                "duration": "2:10", "bpm": 68, "meter": "4/4", "mode": "C major",
                "lead": "solo grand piano", "ensemble": "solo", "register": "low register",
                "mood": "亮、干净",
                "style": "No vocals, ambient cinematic, 4/4, 68 BPM, C major, solo grand piano, "
                         "solo, low register, wide hall reverb with long tail",
                "lyrics": "[Intro – 独奏钢琴，单音，留白 8 小节]\n[End – 回到开头的和弦与织体，干净切断]",
                "cover": "意象：海边灯塔；共用视觉母题：低饱和冷调；封面文字：灯塔，纤细手写体，右侧三分之一留白，竖排",
            },
            {
                "no": 2, "title": "潮汐表", "role": "主体A",
                "duration": "3:40", "bpm": 84, "meter": "7/8", "mode": "D dorian",
                "lead": "fingerpicked acoustic guitar", "ensemble": "five-piece band",
                "register": "mid register", "mood": "推进、灰里有光",
                "style": "No vocals, acoustic indie folk, 7/8, 84 BPM, D dorian, "
                         "fingerpicked acoustic guitar, five-piece band, mid register, close-mic room reverb",
                "lyrics": "[Intro – 木吉他单音]\n[Loop A – 加入大提琴长音]\n"
                          "[Loop B – 刷鼓进，加入低八度贝斯]\n"
                          "[End – 回到开头的和弦与织体，干净切断]",
                "cover": "意象：潮汐表刻度；封面文字：潮汐表，纤细手写体，左侧三分之一留白，竖排",
            },
            {
                "no": 3, "title": "旧船厂", "role": "主体B",
                "duration": "3:05", "bpm": 104, "meter": "6/8", "mode": "G mixolydian",
                "lead": "muted trumpet", "ensemble": "quartet", "register": "high register",
                "mood": "明亮、带弹跳",
                "style": "No vocals, cinematic jazz, 6/8, 104 BPM, G mixolydian, muted trumpet lead, "
                         "quartet, high register, bright hall with medium decay",
                "lyrics": "[Intro – 小号闷音单音]\n[Loop A – 加入钢琴切音]\n"
                          "[Loop C – 全奏，弦乐叠高八度，铜管一记点缀后收]\n"
                          "[End – 回到开头的和弦与织体，干净切断]",
                "cover": "意象：锈迹斑斑的船厂吊臂；封面文字：旧船厂，纤细手写体，上方留白，横排",
            },
            {
                "no": 4, "title": "六楼的灯", "role": "收尾",
                "duration": "2:50", "bpm": 76, "meter": "3/4", "mode": "A aeolian",
                "lead": "solo grand piano", "ensemble": "solo", "register": "high register",
                "mood": "沉、静",
                "style": "No vocals, minimal piano ambient, 3/4, 76 BPM, A aeolian, "
                         "solo grand piano, solo, high register, dry room with long decay",
                "lyrics": "[Intro – 单音，右手高音声部]\n[End – 回到开头的和弦与织体，干净切断]",
                "cover": "意象：夜里六楼亮着的窗；封面文字：六楼的灯，纤细手写体，左侧三分之一留白，竖排",
            },
        ],
    }


def selftest():
    """内置正反样本：规范 spec 必须全绿，每条门禁各造一个错样本必须变红。
    判据改坏而自检不红 = 门禁变橡皮章，所以这里逐条覆盖。"""
    cases = []

    def t(name, fn):
        cases.append((name, fn))

    def has(findings, level, fid):
        return any(f["level"] == level and f["id"] == fid for f in findings)

    def mutate(fn):
        """造错样本：改一份好 spec，返回 (spec, 是否被抓到)"""
        s = _good_spec()
        fn(s)
        return has(check_spec(s), "FAIL", "MUT")

    def expect_fail(label, fid, fn):
        """期望某个门禁 id 被触发"""
        def run():
            s = _good_spec()
            fn(s)
            got = [f["id"] for f in check_spec(s) if f["level"] == "FAIL"]
            if fid not in got:
                return f"应报 {fid}，实得 {got or '无FAIL'}"
            return None
        t(label, run)

    # ---------- 基线：规范样本必须全绿（先让基线全绿再逐个造错） ----------
    def baseline():
        bad = [f for f in check_spec(_good_spec()) if f["level"] in ("FAIL", "WARN")]
        if bad:
            return "规范样本不该有FAIL/WARN，实得 " + str([(f["id"], f["level"], f["msg"]) for f in bad])
        return None
    t("基线 · 规范专辑 spec → 0 FAIL / 0 WARN", baseline)

    def baseline_no_false_positive():
        bad = has(check_spec(_good_spec()), "FAIL", "C1")
        if bad:
            return "序章×收尾 是有意呼应，不该报撞车"
        return None
    t("基线 · 序章与收尾同编制（有意呼应）不误报", baseline_no_false_positive)

    def baseline_no_vocal_false_positive():
        if has(check_spec(_good_spec()), "FAIL", "E1"):
            return "'No vocals' 声明本身被误报成人声词"
        return None
    t("基线 · No vocals 声明本身不误报人声词", baseline_no_vocal_false_positive)

    # ---------- 反样本：逐条门禁 ----------
    expect_fail("① 缺「5 曲目表」章节 → A1", "A1",
                lambda s: s.__setitem__("chapters", [c for c in s["chapters"] if "曲目表" not in c]))
    expect_fail("① 章节顺序颠倒 → A1", "A1",
                lambda s: s["chapters"].__setitem__(4, "6 差异矩阵"))
    expect_fail("① 缺「附 校验记录」→ A1", "A1",
                lambda s: s.__setitem__("chapters", [c for c in s["chapters"] if "校验记录" not in c]))

    expect_fail("② BPM 撞车 → B1", "B1",
                lambda s: s["tracks"][1].__setitem__("bpm", 68))
    expect_fail("② BPM 写成区间 → B1", "B1",
                lambda s: s["tracks"][0].__setitem__("bpm", "70 to 80"))

    expect_fail("③ 四根轴相同 → C1", "C1",
                lambda s: s["tracks"][1].update({"meter": "4/4", "lead": "solo grand piano",
                                                  "ensemble": "solo", "register": "low register"}))

    def echo_beyond_limit():
        """序章 × 收尾 的例外上限是 4：超过 4 仍必须红（例外不是免检）"""
        s = _good_spec()
        s["tracks"][3].update({"meter": s["tracks"][0]["meter"],
                               "ensemble": s["tracks"][0]["ensemble"],
                               "mode": s["tracks"][0]["mode"],
                               "register": s["tracks"][0]["register"],
                               "lead": s["tracks"][0]["lead"]})
        got = [f["id"] for f in check_spec(s) if f["level"] == "FAIL" and f["id"] == "C1"]
        if not got:
            return "序章×收尾 相同轴达5 根，超过例外上限 4，应报 C1"
        return None
    t("③ 序章×收尾 超过例外上限 → C1（例外不是免检）", echo_beyond_limit)

    expect_fail("④ 拍号只在表格不在风格栏 → D1", "D1",
                lambda s: s["tracks"][1].__setitem__(
                    "style", s["tracks"][1]["style"].replace("7/8, ", "")))
    expect_fail("④ 调式只在表格不在风格栏 → D1", "D1",
                lambda s: s["tracks"][1].__setitem__(
                    "style", s["tracks"][1]["style"].replace("D dorian, ", "")))
    expect_fail("④ 风格栏无 BPM → D2", "D2",
                lambda s: s["tracks"][0].__setitem__(
                    "style", s["tracks"][0]["style"].replace("68 BPM, ", "")))
    expect_fail("④ 风格栏超 1000 字 → D2", "D2",
                lambda s: s["tracks"][0].__setitem__("style", s["tracks"][0]["style"] + " warm " * 200))

    expect_fail("⑤ 器乐风格栏混入 female vocal → E1", "E1",
                lambda s: s["tracks"][0].__setitem__("style", s["tracks"][0]["style"] + ", soft female vocal"))
    expect_fail("⑤ 器乐首句不是 No vocals → E1", "E1",
                lambda s: s["tracks"][0].__setitem__(
                    "style", s["tracks"][0]["style"].replace("No vocals, ", "")))
    expect_fail("⑤ 歌词栏方括号外有文字 → E2", "E2",
                lambda s: s["tracks"][1].__setitem__("lyrics", s["tracks"][1]["lyrics"] + "\n潮汐表"))
    expect_fail("⑤ 段落标签用 Chorus → E3", "E3",
                lambda s: s["tracks"][1].__setitem__("lyrics", "[Intro – 木吉他]\n[Chorus – 全奏]"))
    expect_fail("⑤ 指示用户打开纯音乐开关 → E4", "E4",
                lambda s: s.__setitem__("instrumentalSwitchAdvice", "打开纯音乐开关，歌词栏留空"))
    expect_fail("⑤ 缺 instrumentalSwitchAdvice → E4", "E4",
                lambda s: s.pop("instrumentalSwitchAdvice"))

    expect_fail("⑥ 封面没点名曲名 → F1", "F1",
                lambda s: s["tracks"][0].__setitem__(
                    "cover", "意象：海边灯塔；低饱和冷调，纤细手写体，右侧三分之一留白"))
    expect_fail("⑥ 封面没写留白位置 → F1", "F1",
                lambda s: s["tracks"][0].__setitem__(
                    "cover", "意象：海边灯塔；封面文字：灯塔，纤细手写体，1:1 正方形"))
    expect_fail("⑥ 封面没指定字体 → F1", "F1",
                lambda s: s["tracks"][0].__setitem__(
                    "cover", "意象：海边灯塔；封面文字：灯塔，右侧三分之一留白，竖排"))
    expect_fail("⑥ 封面提示词整段缺 → F1", "F1",
                lambda s: s["tracks"][2].__setitem__("cover", ""))

    expect_fail("曲目表缺「音区」→ A2", "A2",
                lambda s: s["tracks"][0].__setitem__("register", ""))
    expect_fail("曲目表缺「情绪」→ A2", "A2",
                lambda s: s["tracks"][1].__setitem__("mood", "待定"))
    expect_fail("空 tracks → A0（不静默放行）", "A0",
                lambda s: s.__setitem__("tracks", []))

    def missing_dir():
        got = [f["id"] for f in check_rendered("/nonexistent-dir-xyz", _good_spec())
               if f["level"] == "FAIL"]
        if "G1" not in got:
            return f"缺目录应报 G1（两份产物都要在），实得 {got or '无FAIL'}"
        return None
    t("两份产物缺一 → G1", missing_dir)

    def extra_artifact():
        """产物目录里不该有脚本副本 / spec.json —— 脚本副本是有害的「假真源」"""
        import shutil
        import tempfile
        d = tempfile.mkdtemp(prefix="album-extra-")
        try:
            with open(os.path.join(d, "build_album.py"), "w", encoding="utf-8") as f:
                f.write("# 用户改坏的副本\n")
            got = [f["id"] for f in check_rendered(d, _good_spec()) if f["level"] == "FAIL"]
            if "G7" not in got:
                return f"目录里有脚本副本应报 G7，实得 {got or '无FAIL'}"
            return None
        finally:
            shutil.rmtree(d, ignore_errors=True)
    t("产物目录混入脚本副本 → G7（多余产物）", extra_artifact)

    def extra_spec():
        import shutil
        import tempfile
        d = tempfile.mkdtemp(prefix="album-spec-")
        try:
            with open(os.path.join(d, "album-spec.json"), "w", encoding="utf-8") as f:
                f.write("{}")
            got = [f["id"] for f in check_rendered(d, _good_spec()) if f["level"] == "FAIL"]
            if "G7" not in got:
                return f"目录里有 spec.json 应报 G7（spec 是中间数据，不进交付），实得 {got or '无FAIL'}"
            return None
        finally:
            shutil.rmtree(d, ignore_errors=True)
    t("产物目录混入 spec.json → G7", extra_spec)

    def only_two_files_ok():
        """正向对照：只有两份 md 的目录不该报 G7"""
        import shutil
        import tempfile
        d = tempfile.mkdtemp(prefix="album-ok-")
        try:
            sp = _good_spec()
            for fn in (f"{sp['album']}-专辑规划-{sp['styleLabel']}.md",
                       f"{sp['album']}-粘贴清单-{sp['styleLabel']}.md"):
                with open(os.path.join(d, fn), "w", encoding="utf-8") as f:
                    f.write("占位")
            got = [f["id"] for f in check_rendered(d, sp) if f["id"] == "G7"]
            if got:
                return f"只有两份 md 时不该报 G7，实得 {got}"
            return None
        finally:
            shutil.rmtree(d, ignore_errors=True)
    t("基线 · 只有两份 md → 不报 G7", only_two_files_ok)

    # ---------- 跑 ----------
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

def parse_args(argv):
    """返回 (spec路径, md目录或None)。--md-dir 的值必须被吃掉，不能当成位置参数
    （2026-10-16 真跑渲染时踩到：`spec --md-dir 目录` 会因参数个数变成 3 而报用法错误）。"""
    spec_path = None
    md_dir = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--md-dir":
            i += 1
            if i >= len(argv):
                raise ValueError("--md-dir 后面缺目录名")
            md_dir = argv[i]
        elif a.startswith("--md-dir="):
            md_dir = a.split("=", 1)[1]
        elif a.startswith("-"):
            raise ValueError(f"未知选项：{a}")
        elif spec_path is None:
            spec_path = a
        else:
            raise ValueError(f"多了一个位置参数：{a}（只能给一个 spec 文件）")
        i += 1
    if not spec_path:
        raise ValueError("缺 spec 文件路径")
    return spec_path, md_dir


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 2
    try:
        spec_path, md_dir = parse_args(argv)
    except ValueError as e:
        print(f"[FAIL] {e}", file=sys.stderr)
        print("用法：python3 album_check.py <spec.json> [--md-dir <目录>]", file=sys.stderr)
        print("      python3 album_check.py --selftest", file=sys.stderr)
        return 2

    try:
        spec = json.loads(read_text(spec_path))
    except OSError as e:
        print(f"[FAIL] 读不了 spec「{spec_path}」：{e}——"
              "先用 build_album.py --export-spec 产出 spec.json", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"[FAIL] spec 不是合法 JSON：{e}", file=sys.stderr)
        return 2

    findings = check_spec(spec)
    if md_dir is not None:
        if not os.path.isdir(md_dir):
            print(f"[FAIL] --md-dir 指向的目录不存在：{md_dir}", file=sys.stderr)
            return 2
        findings += check_rendered(md_dir, spec)
    return report(findings)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
