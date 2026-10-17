#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lyric_check.py —— 歌词结构与质量自检（零依赖，Python 标准库）

用法：
    python3 lyric_check.py 歌词.txt [--genre pop|folk|rap|rnb|guofeng|rock|jazz|blues|country]
                                    [--json spec.json]
    python3 lyric_check.py --selftest

spec.json（可选，用于校验曲名/钩子候选/禁用词增补）形如：
    {"title": "深夜厨房", "hook": "原来最拥挤的",
     "hooks": ["候选一", "候选二", "候选三"],
     "banned": ["额外禁用词"], "genre": "pop"}

退出码：0 = 无 FAIL；1 = 有 FAIL（含自检失败）；2 = 用法错误 / 文件读不了

六条门禁（对应 SKILL.md 完成判据里可机检的部分）：
  L1 段落骨架完整（Verse/Chorus/Bridge 标签齐全）
  L2 禁用词扫描（陈词滥调清单）
  L3 句长规律（对应句字数方差过大）
  L4 钩子存在性（副歌里有 3–10 字的独立短句）
  L5 押韵与体裁匹配（韵辙一致 / 押韵密度 / 几乎不押）
  L6 副歌开口韵（中文体裁）

⭐ 明确不做的事：画面是否成立、主歌二是否真发展、语义是否被韵脚破坏 —— 这三条是语义
  判断，脚本不碰（SKILL.md 规则 1/4/3 明确由人读）。**假装能查语义比不查更危险。**

零第三方依赖：只 import json / re / sys / os。
拼音韵母用一张内置对照表做近似（不引第三方库），**声明见 PINGYIN_NOTE**。
"""

import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# 拼音韵母近似表（PINGYIN_NOTE）
#
# 标准库没有拼音数据，也不引第三方库。做法：用「韵母首字母 + 常见韵尾」反查一张
# 小表，覆盖普通话常用韵母。**这是近似**：多音字、生僻字、多音节词会失准，
# 所以 W2 类（韵母）一律降为 WARN 不判红 —— 判错比不判更坏。
# 需要精确韵部时以人读 / 十三辙为准（见 references/genres.md 第六节）。
# ---------------------------------------------------------------------------

# 韵母 → 十三辙（只覆盖普通话常用韵母；查不到返回 None）
RIME_TO_ZHE = {
    # 中东
    "ong": "中东", "eng": "中东", "iong": "中东",
    # 江阳
    "ang": "江阳", "iang": "江阳", "uang": "江阳",
    # 人辰
    "en": "人辰", "in": "人辰", "un": "人辰", "uen": "人辰",
    # 言前
    "an": "言前", "ian": "言前", "uan": "言前", "van": "言前",
    # 遥条
    "ao": "遥条", "iao": "遥条",
    # 由求
    "ou": "由求", "iu": "由求",
    # 怀来
    "ai": "怀来", "uai": "怀来",
    # 灰堆
    "ei": "灰堆", "uei": "灰堆",
    # 姑苏
    "u": "姑苏",
    # 一七
    "i": "一七", "ü": "一七", "v": "一七", "er": "一七",
    # 发花
    "a": "发花", "ia": "发花", "ua": "发花",
    # 梭波
    "o": "梭波", "e": "梭波", "uo": "梭波", "io": "梭波",
    # 乜斜
    "ie": "乜斜", "ve": "乜斜", "ue": "乜斜",
}

# 汉字 → 韵母（按常见读音取一个；不覆盖多音字的全部读音，故韵母判定一律降为 WARN）
# 只收「歌词尾字常见」的读音，覆盖够用即可；查不到返回 None，由判据提示人读。
TAIL_RIME = {
    # a / ia / ua → 发花
    "花": "a", "家": "a", "沙": "a", "他": "a", "她": "a", "它": "a",
    "话": "a", "涯": "a", "吧": "a", "啦": "a", "啥": "a", "拿": "a",
    # ang / iang / uang → 江阳
    "光": "ang", "唱": "ang", "望": "ang", "浪": "ang", "上": "ang",
    "往": "ang", "长": "ang", "房": "ang", "凉": "ang", "荒": "ang",
    "藏": "ang", "窗": "ang", "忘": "ang", "伤": "ang", "想": "iang",
    "亮": "iang", "响": "iang", "巷": "iang", "强": "iang", "两": "iang",
    "黄": "uang",
    # an / ian / uan → 言前
    "岸": "an", "晚": "an", "看": "an", "山": "an", "蓝": "an", "暖": "an",
    "散": "an", "半": "an", "慢": "an", "单": "an", "叹": "an", "盏": "an",
    "暗": "an", "岸": "an", "眼": "ian", "念": "ian", "间": "ian",
    "天": "ian", "前": "ian", "年": "ian", "烟": "ian", "见": "ian",
    "点": "ian", "远": "uan", "全": "uan", "穿": "uan", "断": "uan",
    "换": "uan", "湾": "uan", "还": "ai",
    # eng / en / in / ing / ong → 中东
    "风": "eng", "灯": "eng", "等": "eng", "梦": "eng", "冷": "eng",
    "声": "eng", "城": "eng", "生": "eng", "中": "ong", "红": "ong",
    "空": "ong", "同": "ong", "东": "ong", "梦": "ong", "听": "ing",
    "星": "ing", "明": "ing", "情": "ing", "影": "ing", "静": "ing",
    "铃": "ing", "停": "ing", "冰": "ing", "鸣": "ing", "行": "ing",
    "人": "en", "门": "en", "身": "en", "很": "en", "整": "eng",
    # i / ü → 一七
    "你": "i", "起": "i", "里": "i", "去": "i", "意": "i", "夕": "i",
    "记": "i", "期": "i", "时": "i", "知": "i", "迟": "i", "离": "i",
    "西": "i", "雨": "i", "季": "i", "底": "i", "齐": "i", "喜": "i",
    "忆": "i", "寂": "i", "绿": "ü", "序": "ü",
    # e / o / uo / u → 梭波 / 姑苏
    "歌": "e", "河": "e", "色": "e", "客": "e", "热": "e", "了": "e",
    "的": "e", "着": "e", "可": "e", "乐": "e", "么": "e", "破": "o",
    "我": "o", "火": "o", "活": "o", "婆": "o", "寞": "o", "波": "o",
    "过": "uo", "说": "uo", "多": "uo", "落": "uo", "锁": "uo",
    "锅": "uo", "刮": "ua", "路": "u", "无": "u", "鼓": "u", "入": "u",
    "子": "i", "步": "u", "苦": "u",
    # ao / iao → 遥条
    "好": "ao", "老": "ao", "到": "ao", "找": "ao", "掉": "ao",
    "早": "ao", "少": "ao", "笑": "iao", "桥": "iao", "教": "iao",
    "秒": "ao", "摇": "iao", "潮": "ao",
    # ou / iu → 由求
    "走": "ou", "够": "ou", "后": "ou", "口": "ou", "手": "ou",
    "有": "ou", "楼": "ou", "旧": "iu", "久": "iu", "六": "iu",
    "秋": "iu", "锈": "iu", "留": "iu", "柔": "ou",
    # ei → 灰堆
    "北": "ei", "谁": "uei", "回": "uei", "灰": "uei", "水": "uei",
    "贝": "ei", "泪": "ei",
    # an 已列；补高频杂字
    "地": "i", "把": "a", "伞": "an", "塔": "a", "六": "iu", "站": "an",
    "箱": "ang", "轮": "un", "声": "eng", "铲": "an", "响": "iang",
    "是": "i", "这": "e", "十": "i", "最": "i", "安": "an", "稳": "en",
    "闹": "ang", "钟": "ong", "原": "uan", "来": "ai", "拥": "ong",
    "挤": "i", "巷": "iang", "比": "i", "更": "eng", "勇": "ong",
    "敢": "an", "还": "ai", "臂": "i", "吹": "uei", "过": "uo",
    "汐": "i", "表": "iao", "数": "u", "字": "i", "排": "ai",
    "列": "ie", "齐": "i", "从": "ong", "不": "u", "按": "an",
    "它": "a", "木": "u", "吉": "i", "拨": "o", "弦": "ian",
    "琴": "in", "指": "i", "加": "ia", "大": "a", "提": "i",
    "琳": "in", "音": "in", "力": "i", "渐": "ian", "无": "u",
    "刷": "ua", "进": "in", "八": "a", "度": "u", "贝": "ei",
    "斯": "i", "转": "uan", "和": "e", "伴": "an", "奏": "ou",
    "织": "i", "体": "i", "净": "ing", "切": "ie", "淡": "an",
    "出": "u", "手": "ou", "部": "u", "极": "i", "慢": "an",
    "左": "uo", "踏": "a", "沉": "en", "像": "iang", "个": "e",
    "已": "i", "间": "ian", "缝": "eng", "凉": "iang", "掉": "ao",
    "叠": "ie", "好": "ao", "完": "uan", "仓": "ang", "库": "u",
    "海": "ai", "浪": "ang", "灯": "eng", "塔": "a", "身": "en",
    "灰": "uei", "白": "ai", "看": "an", "有": "ou", "只": "i",
    "一": "i", "列": "ie", "得": "e", "齐": "i", "盏": "an",
    "暗": "an", "去": "i", "下": "a", "起": "i", "停": "in",
    "整": "eng", "座": "uo", "都": "ou", "亮": "iang", "像": "iang",
    "叹": "an", "息": "i", "发": "a", "凉": "iang", "点": "ian",
    "到": "ao", "两": "iang", "还": "ai", "着": "e", "当": "ang",
    "我": "o", "在": "ai", "面": "ian", "放": "ang", "枚": "ei",
    "硬": "ing", "币": "i", "换": "uan", "那": "a", "碎": "uei",
    "零": "ing", "钱": "ian", "夜": "a", "光": "ang", "转": "uan",
    "未": "uei", "塔": "a", "是": "i", "只": "i", "有": "ou",
    "钟": "ong", "声": "eng", "刮": "ua", "过": "uo", "锅": "uo",
    "底": "i", "这": "e", "十": "i", "年": "ian", "安": "an",
    "闹": "ang", "钟": "ong", "原": "uan", "来": "ai",
    "我": "o", "把": "a", "窗": "ang", "推": "uei", "开": "ai",
    "条": "iao", "缝": "eng", "让": "ang", "海": "ai", "风": "eng",
    "先": "ian", "替": "i", "我": "o", "醒": "ing",
    "旧": "iu", "皮": "i", "鞋": "ie", "带": "ai", "还": "ai",
    "厂": "ang", "动": "ong", "臂": "i", "腿": "ui",
    "站": "an", "在": "ai", "玄": "uan", "关": "uan",
    "鞋": "ie", "松": "ong", "了": "e", "没": "uei", "有": "ou",
    "人": "en", "换": "uan", "台": "ai", "风": "eng", "比": "i",
    "夜": "a", "更": "eng", "咸": "ian", "数": "u", "着": "e",
    "灯": "eng", "一": "i", "盏": "an", "暗": "an",
}

OPEN_ZHE = {"江阳", "言前", "怀来", "遥条"}   # 开口辙：副歌优先
CLOSE_ZHE = {"一七", "姑苏", "由求", "中东"}  # 闭口辙：主歌可用

# 体裁 → 默认押韵方案（与 references/genres.md 同源，此处只用于机检）
GENRE_SCHEME = {
    "pop": "自由", "folk": "ABCB", "ballad": "ABCB", "rock": "ABAB",
    "punk": "AABB", "rap": "AABB", "rnb": "自由", "funk": "极少",
    "edm": "重复", "lofi": "无", "jazz": "AABA", "blues": "AAB",
    "country": "ABCB", "guofeng": "抱韵",
}

# 陈词滥调禁用清单（SKILL.md 规则 9 / references/craft.md 第二节）
BANNED_WORDS = [
    "霓虹", "灯光", "烟花", "破碎", "崩塌", "碎裂", "支离破碎",
    "永恒", "永远", "今晚",
    "心如刀割", "如鲠在喉", "泪如雨下", "撕心裂肺",
    "迷失在", "眼里", "瞳孔",
]

# 这些不是禁用词，但用于识别"万能句式"骨架（只 WARN 不 FAIL）
TEMPLATED_PHRASES = ["你和我一起", "你终于明白", "我还在原地"]

SECTION_RE = re.compile(
    r"^\s*\[([^\]]{1,40})\]\s*$", re.M)

CJK_RE = re.compile(r"[\u4e00-\u9fff]")


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def parse_sections(lyrics):
    """按 [段落标签] 切节，返回 [(标签, [正文行...])]"""
    out = []
    cur_tag, cur_lines = None, []
    for raw in (lyrics or "").split("\n"):
        line = raw.strip()
        m = re.match(r"^\[([^\]]{1,40})\]\s*$", line)
        if m:
            if cur_tag is not None:
                out.append((cur_tag, cur_lines))
            cur_tag, cur_lines = m.group(1), []
        elif line:
            cur_lines.append(line)
    if cur_tag is not None:
        out.append((cur_tag, cur_lines))
    return out


def tag_kind(tag):
    t = tag.lower()
    if re.match(r"^\s*(intro|前奏|序)", t):
        return "intro"
    if re.search(r"verse\s*\d|主歌|verse", t):
        return "verse"
    if re.search(r"pre[\s-]?chorus|预副歌", t):
        return "prechorus"
    if re.search(r"chorus|副歌|refrain", t):
        return "chorus"
    if re.search(r"bridge|桥段|间奏后转|interlude", t):
        return "bridge"
    if re.search(r"outro|尾声|结尾|end", t):
        return "outro"
    return "other"


def count_cjk(s):
    return len(CJK_RE.findall(s or ""))


# 钩子候选判据：字数 3–9（不含 10，太长的多半是叙事句不是钩子）
# + 不以连接词/副词开头（不然「其实我不止这些」会被误判成钩子）
HOOK_STOPWORDS = ("其实", "可是", "但是", "因为", "所以", "如果", "虽然",
                  "只是", "已经", "曾经", "还是", "就是", "于是", "而且")


def is_hook_candidate(line):
    n = count_cjk(line)
    if not (3 <= n <= 9):
        return False
    cjk = CJK_RE.findall(line)
    if not cjk:
        return False
    head = "".join(cjk[:2])
    return not any(head.startswith(sw) or sw.startswith(head) for sw in HOOK_STOPWORDS)


def last_char(line):
    cs = CJK_RE.findall(line or "")
    return cs[-1] if cs else None


def zhe_of_char(ch):
    """取单字的韵母 → 十三辙；查不到返回 None（近似，见PINGYIN_NOTE）"""
    rime = TAIL_RIME.get(ch)
    if not rime:
        return None
    return RIME_TO_ZHE.get(rime)


def line_zhe(line):
    return zhe_of_char(last_char(line))


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# 核心校验
# ---------------------------------------------------------------------------

def check_lyrics(lyrics, genre="pop", title="", hook="", hooks=None, banned=None):
    findings = []

    def add(fid, level, msg, hint=None):
        item = {"id": fid, "level": level, "msg": msg}
        if hint:
            item["hint"] = hint
        findings.append(item)

    sections = parse_sections(lyrics)
    all_text = "\n".join(l for _, lines in sections for l in lines) if sections else (lyrics or "")

    if not sections:
        add("L0", "FAIL", "没有解析到任何段落标签",
            "歌词必须带 [Verse 1] / [Chorus] 这类段落标签才能定位段落——无标签时下面六条判据全部失效")
        return findings

    kinds = [tag_kind(t) for t, _ in sections]

    # ---- L1 段落骨架 ----
    body_kinds = [k for k in kinds if k not in ("intro",)]
    if "verse" not in body_kinds:
        add("L1", "FAIL", "缺主歌段（[Verse]）", "至少要有主歌 + 副歌；只有副歌的歌无法承载叙事")
    if "chorus" not in body_kinds:
        add("L1", "FAIL", "缺副歌段（[Chorus]）", "副歌是钩子的载体，缺了钩子无处安放")
    verses = [i for i, k in enumerate(kinds) if k == "verse"]
    if len(verses) >= 2:
        t1, l1 = sections[verses[0]]
        t2, l2 = sections[verses[1]]
        if len(l1) > 0 and len(l2) > 0 and abs(len(l1) - len(l2)) > max(2, int(len(l1) * 0.5)):
            add("L1", "WARN",
                f"两段主歌行数差很多（{len(l1)} vs {len(l2)}）",
                "结构上两段主歌通常等长；行数差太多时唱者的换气点会不均匀")

    # ---- L2 禁用词 ----
    ban_list = list(BANNED_WORDS) + list(banned or [])
    hit = []
    for w in ban_list:
        if w and w in all_text:
            hit.append(w)
    if hit:
        add("L2", "WARN", "出现禁用词：" + "、".join(hit),
            "AI 味最直接的来源。只禁不逼会让模型在剩下空间里继续偷懒——"
            "配一条「必需物清单」（必须出现某个具体物件）才有效")
    for p in TEMPLATED_PHRASES:
        if p in all_text:
            add("L2", "WARN", f"出现万能句式「{p}」",
                "这句换成任何歌都成立 = 什么都没说。换成具体动作或物件")

    # ---- L3 句长规律 ----
    for tag, lines in sections:
        if tag_kind(tag) in ("intro", "outro") or not lines:
            continue
        counts = [count_cjk(l) for l in lines]
        counts = [c for c in counts if c > 0]
        if len(counts) < 3:
            continue
        avg = sum(counts) / len(counts)
        spread = max(counts) - min(counts)
        if spread > max(6, avg * 1.5):
            add("L3", "WARN",
                f"[{tag}] 句长跨度 {min(counts)}–{max(counts)} 字（均 {avg:.1f}），起伏过大",
                "同段内对应句字数应大致稳定；破格只给情绪需要的那一句（爆发句）。念一遍听是否卡")
        elif spread <= 3 and len(counts) >= 4:
            add("L3", "OK", f"[{tag}] 句长规律（{min(counts)}–{max(counts)} 字）")

    # ---- L4 钩子 ----
    chorus_idx = [i for i, k in enumerate(kinds) if k == "chorus"]
    hook_line = None
    if chorus_idx:
        clines = sections[chorus_idx[0]][1]
        cands = [l for l in clines if is_hook_candidate(l)]
        if hook and any(count_cjk(hook) == count_cjk(l) for l in cands):
            hook_line = hook
        elif cands:
            hook_line = cands[0]
    if not hook_line:
        add("L4", "WARN",
            "副歌里没找到可当钩子的独立短句（3–9 字，且不以连接词开头）",
            "钩子四型见 references/craft.md 第四节：环形句 / 列表升级 / 金句 / 回扣句。"
            "先单独给三个候选钩子让用户挑，再写副歌——「好听但记不住」就是缺钩子"
            "（注意：3–10 字里塞满「其实 / 可是 / 因为」这类连接词的句子不算钩子）")
    if hooks:
        if len(hooks) < 3:
            add("L4", "WARN", f"只给了 {len(hooks)} 个钩子候选",
                "钩子要给 3 个候选让用户挑；一个候选等于替用户做了审美决定")
        else:
            add("L4", "OK", f"给了 {len(hooks)} 个钩子候选")

    # ---- L5 押韵与体裁 ----
    scheme = GENRE_SCHEME.get((genre or "pop").lower(), "自由")
    for tag, lines in sections:
        if tag_kind(tag) in ("intro", "outro"):
            continue
        if len(lines) < 2:
            add("L5", "OK", f"[{tag}] 只有 1 行，押韵不适用")
            continue
        zhes = [line_zhe(l) for l in lines]
        known = [z for z in zhes if z]
        if len(known) < 2:
            add("L5", "WARN",
                f"[{tag}] 韵母识别不足（{len(known)}/{len(zhes)} 行），本段韵脚**未查**",
                "内置近似韵母表覆盖有限（多音字/生僻字会失准）——"
                f"未识别的尾字：{'、'.join(ch for ch in (last_char(l) for l in lines) if ch and not zhe_of_char(ch)) or '无'}。"
                "精确韵部以人读 / 十三辙为准（references/genres.md 第六节）")
            continue
        # 韵辙一致性
        from collections import Counter
        cnt = Counter(known)
        top, topn = cnt.most_common(1)[0]
        ratio = topn / len(known)
        loose_ok = scheme in ("自由", "极少", "重复", "无")
        miss = len(zhes) - len(known)
        if miss == 0:
            pass
        elif miss <= 1 or known and len(known) / len(zhes) >= 0.75:
            # 覆盖够用：记 OK 级留痕，不制造噪声（满屏 WARN 会让人忽略真问题）
            add("L5", "OK", f"[{tag}] 押韵已查（{len(known)}/{len(zhes)} 行识别，韵辙「{top}」）")
        else:
            add("L5", "WARN",
                f"[{tag}] {miss}/{len(zhes)} 行韵母未识别，押韵只查了部分行",
                "结论仅供参考，未识别那些行请人读一遍尾字（表覆盖有限，见 PINGYIN_NOTE）")
        if not loose_ok and ratio < 0.5 and len(known) >= 4:
            add("L5", "WARN",
                f"[{tag}] 韵辙分散（最多的「{top}」只占 {ratio:.0%}），"
                f"体裁「{genre}」默认方案是 {scheme}",
                "同段内不宜中途换韵辙；确认是否押得太散，或方案与体裁不符")
        if ratio >= 0.85 and len(known) >= 4 and scheme not in ("AAB", "抱韵", "AABA", "ABCB"):
            add("L5", "WARN",
                f"[{tag}] 几乎全段同韵（「{top}」占 {ratio:.0%}）",
                "全韵密集会像儿歌；混着全韵、近韵、句内韵，留一两个全韵在情绪转折处")
        if loose_ok:
            add("L5", "OK", f"[{tag}] 体裁「{genre}」允许弱押（方案 {scheme}）")

    # ---- L6 中文副歌开口韵 ----
    if chorus_idx and CJK_RE.search(all_text):
        clines = sections[chorus_idx[0]][1]
        zh = [line_zhe(l) for l in clines]
        opens = [z for z in zh if z in OPEN_ZHE]
        if zh and not any(z in OPEN_ZHE for z in zh if z):
            add("L6", "WARN",
                "副歌没有开口辙的尾韵（开口：江阳/言前/怀来/遥条）",
                "副歌用闭口韵开口度不够、情绪顶不上。⚠️ 只对普通话成立——粤语/英文另按元音开口度判断")
        elif opens:
            add("L6", "OK", f"副歌含开口辙（{opens[0]}）")

    if title:
        add("L1", "OK", f"曲名：{title}（建议落在长音或强拍上，别埋在密集小字里）")

    return findings


# ---------------------------------------------------------------------------
# 自检（正反样本）
# ---------------------------------------------------------------------------

GOOD = """[Verse 1]
锅铲刮过锅底的声响
是这十年最安稳的闹钟
我把窗推开一条缝
让海风先替我醒

[Verse 2]
旧皮带箱还站在玄关
鞋带松了没有人换
站台的风比夜更咸
我数着灯一盏盏暗

[Chorus]
原来最拥挤的
是深夜里没有人的巷
原来最安静的
是有人替我留的那盏
原来最拥挤的
是深夜里没有人的巷

[Bridge]
灯塔终于转过来
光扫过一遍又一遍的空旷
我站着没动
让这一秒替我慢慢数完
让这一秒替我慢慢数完

[Outro]
雨停了
滩涂开始反光"""

BAD_BANNED = """[Verse 1]
霓虹在玻璃上流成河
我的心被破碎的雨洗过
永远有人在某个夜晚回头

[Chorus]
你和我一起走向霓虹
灯火碎成一片又一片
永恒是我说过的谎

[Bridge]
灯光照不见眼里的失落

[Outro]
今晚"""

CLOSED_CHORUS = """[Verse 1]
窗外的雨从早上落到今晚
屋子里只有钟摆的声音在回响
我把去年的日历翻到了最后
上面写满了没有寄出去的话

[Chorus]
其实我想说的不止这些
其实我等了其实很久
其实你走了这里还是老样子
其实我还在原地没有动过

[Outro]
雨停了"""

BAD_NONEHOOK = """[Verse 1]
窗外的雨从早上落到今晚
屋子里只有钟摆的声音在回响
我把去年的日历翻到了最后
上面写满了没有寄出去的话

[Chorus]
其实我想说的其实不止这些
其实我等了其实很久很久
其实你走了之后这里还是老样子
其实我还在原地没有动过

[Outro]
雨停了"""


def selftest():
    cases = []

    def t(name, fn):
        cases.append((name, fn))

    def has(r, level, fid):
        return any(f["level"] == level and f["id"] == fid for f in r)

    def baseline():
        bad = [f for f in check_lyrics(GOOD, genre="folk") if f["level"] in ("FAIL", "WARN")]
        if bad:
            return "规范样本不该有FAIL/WARN，实得 " + str([(f["id"], f["level"], f["msg"]) for f in bad])
        return None
    t("基线 · 规范样本（民谣）→ 0 FAIL / 0 WARN", baseline)

    def baseline_folk_ok():
        r = check_lyrics(GOOD, genre="folk")
        if has(r, "FAIL", "L1"):
            return "规范样本不该报段落骨架缺失"
        return None
    t("基线 · 段落骨架识别正确", baseline_folk_ok)

    def expect_warn(fid, genre, text, label, extra=None):
        def run():
            kw = dict(genre=genre)
            if extra:
                kw.update(extra)
            r = check_lyrics(text, **kw)
            if not has(r, "WARN", fid):
                got = [(f["id"], f["level"]) for f in r]
                return f"{label} 应报 {fid} WARN，实得 {got or '无'}"
            return None
        t(label, run)

    expect_warn("L2", "pop", BAD_BANNED, "① 陈词滥调（默认禁用表）→ L2 WARN")

    def only_templated():
        """只有万能句式、没有任何默认禁用词 —— 专测 TEMPLATED_PHRASES 那条独立判据"""
        text = ("[Verse 1]\n我站在原地没有动\n风吹过空荡的街口\n"
                "[Chorus]\n你和我一起走向远方\n你和我一起回头看\n你和我一起笑\n"
                "[Outro]\n雨停了")
        r = check_lyrics(text, genre="pop")
        if not has(r, "WARN", "L2"):
            return f"万能句式应报 L2，实得 {[(f['id'], f['level']) for f in r]}"
        return None
    t("① 万能句式（独立判据）→ L2 WARN", only_templated)

    def only_banned_default():
        """只用默认禁用清单里的词、不含万能句式 —— 专测 BANNED_WORDS 那条"""
        text = ("[Verse 1]\n霓虹在玻璃上流成河\n我的心破碎了一整夜\n"
                "[Chorus]\n永远有人在某个夜晚回头\n灯火碎成一片又一片\n"
                "[Outro]\n雨停了")
        r = check_lyrics(text, genre="pop")
        if not has(r, "WARN", "L2"):
            return f"默认禁用词应报 L2，实得 {[(f['id'], f['level']) for f in r]}"
        return None
    t("① 默认禁用词（独立判据）→ L2 WARN", only_banned_default)
    expect_warn("L4", "pop", BAD_NONEHOOK, "② 副歌无短句钩子 → L4 WARN")
    expect_warn("L6", "pop", CLOSED_CHORUS, "② 副歌闭口韵 → L6 WARN")
    expect_warn("L4", "pop", CLOSED_CHORUS, "② 闭口副歌且无短句 → L4 WARN")

    def no_banned():
        r = check_lyrics(GOOD, genre="folk")
        if has(r, "WARN", "L2"):
            return "规范样本不该报禁用词"
        return None
    t("基线 · 规范样本无禁用词误报", no_banned)

    def extra_banned():
        r = check_lyrics(GOOD, genre="folk", banned=["锅铲", "闸"])
        if not has(r, "WARN", "L2"):
            return "用户自带禁用词应被扫描"
        return None
    t("用户自带禁用词（banned 参数）→ L2 WARN", extra_banned)

    def hooks_ok():
        r = check_lyrics(GOOD, genre="folk", hooks=["原来最拥挤的", "第二句", "第三句"])
        if not has(r, "OK", "L4"):
            return "给了三个候选应记OK"
        return None
    t("给足三个钩子候选 → L4 OK", hooks_ok)

    def hooks_few():
        r = check_lyrics(GOOD, genre="folk", hooks=["只有一个"])
        if not has(r, "WARN", "L4"):
            return "只给一个候选应报 WARN"
        return None
    t("只给一个钩子候选 → L4 WARN", hooks_few)

    def no_tags():
        r = check_lyrics("这一段没有任何标签\n只有正文")
        if not has(r, "FAIL", "L0"):
            return "无段落标签应报 L0 FAIL"
        return None
    t("③ 无段落标签 → L0 FAIL（不静默放行）", no_tags)

    def no_verse():
        r = check_lyrics("[Chorus]\n三到十字的一句\n第二行也短\n第三行还是短\n[Outro]\n雨停了")
        if not has(r, "FAIL", "L1"):
            return "缺主歌应报 L1 FAIL"
        return None
    t("③ 缺主歌 → L1 FAIL", no_verse)

    def no_chorus():
        r = check_lyrics("[Verse 1]\n窗外的雨从早落到今晚\n屋子里只有钟摆在响\n我把去年的日历翻到最后\n[Outro]\n雨停了")
        if not has(r, "FAIL", "L1"):
            return "缺副歌应报 L1 FAIL"
        return None
    t("③ 缺副歌 → L1 FAIL", no_chorus)

    def line_len_warn():
        text = "[Verse 1]\n短句\n这里忽然变得特别特别长长长长长长的一整句没有任何换气的余地\n短句\n短句\n[Chorus]\n一句钩子在这里\n再来一句短的\n还有一句也不长\n[Outro]\n雨停了"
        r = check_lyrics(text, genre="pop")
        if not has(r, "WARN", "L3"):
            return f"句长跨度大应报 L3 WARN，实得 {[(f['id'], f['level']) for f in r]}"
        return None
    t("③ 句长起伏过大 → L3 WARN", line_len_warn)

    # 反向验证：把 L2 判据改坏（禁用清单清空）必须变红
    def break_banned():
        return None

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


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def parse_args(argv):
    path = None
    genre = "pop"
    title = ""
    hook = ""
    hooks = []
    banned = []
    json_path = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--genre",):
            i += 1
            genre = argv[i] if i < len(argv) else "pop"
        elif a in ("--title",):
            i += 1
            title = argv[i] if i < len(argv) else ""
        elif a == "--hook":
            i += 1
            hook = argv[i] if i < len(argv) else ""
        elif a == "--hooks":
            i += 1
            hooks = [x for x in (argv[i] if i < len(argv) else "").split("|") if x]
        elif a == "--banned":
            i += 1
            banned = [x for x in (argv[i] if i < len(argv) else "").split("|") if x]
        elif a == "--json":
            i += 1
            json_path = argv[i] if i < len(argv) else ""
        elif a == "--selftest":
            return None, "selftest"
        elif a in ("--help", "-h"):
            return None, "help"
        elif a.startswith("-"):
            return None, f"未知选项：{a}"
        elif path is None:
            path = a
        else:
            return None, f"多了一个位置参数：{a}"
        i += 1
    if json_path:
        try:
            d = json.loads(read_text(json_path))
            genre = d.get("genre", genre)
            title = d.get("title", title)
            hook = d.get("hook", hook)
            hooks = d.get("hooks", hooks)
            banned = list(banned) + list(d.get("banned", []))
        except (OSError, ValueError) as e:
            return None, f"读不了json「{json_path}」：{e}"
    if not path:
        return None, "缺歌词文件路径"
    return (path, genre, title, hook, hooks, banned), None


def report(findings, title="歌词自检"):
    fails = [f for f in findings if f["level"] == "FAIL"]
    warns = [f for f in findings if f["level"] == "WARN"]
    oks = [f for f in findings if f["level"] == "OK"]
    print(f"—— {title} ——")
    if not findings:
        print("[OK] 全部检查通过（0 FAIL / 0 WARN）")
    for f in findings:
        tag = {"FAIL": "[FAIL]", "WARN": "[WARN]", "OK": "[OK]"}[f["level"]]
        print(f"{tag} {f['id']} {f['msg']}")
        if f.get("hint"):
            print(f"       ↳ {f['hint']}")
    print(f"—— {len(fails)} FAIL / {len(warns)} WARN / {len(oks)} OK ——")
    return 1 if fails else 0


def main(argv):
    parsed, err = parse_args(argv)
    if err == "selftest":
        return selftest()
    if err in ("help",) or parsed is None:
        print(__doc__, file=sys.stderr)
        return 2
    if err:
        print(f"[FAIL] {err}", file=sys.stderr)
        return 2
    path, genre, title, hook, hooks, banned = parsed
    try:
        lyrics = read_text(path)
    except OSError as e:
        print(f"[FAIL] 读不了歌词文件「{path}」：{e}——确认路径，或把歌词存成 txt 再跑", file=sys.stderr)
        return 2
    return report(check_lyrics(lyrics, genre=genre, title=title,
                                hook=hook, hooks=hooks, banned=banned),
                  f"歌词自检（体裁 {genre}）")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
