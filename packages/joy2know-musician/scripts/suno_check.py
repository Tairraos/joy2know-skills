#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
晓得·音乐人 —— Suno 歌曲包结构校验

用途：把「写得好不好」里能机器判断的那部分先捞出来。
     它只做结构检查，不评价文风——文风好不好由人和耳朵判断。

检查项：
  1. 是否写了 [Language:] / [Accent:]（**器乐模式下反过来**：写了才提示删）
  2. 段落标签是否为复合结构（至少含一项描述）
  3. 必留段落是否齐全（默认 Intro / Chorus / Outro / End；**器乐包与 --loop 均放宽为 Intro / End**）
  4. 括号是否配对（圆括号 与 (— —) 两种）
  5. 标签里是否混入了中文（会被当人声唱出）
  6. Style 首字段：有人声看语言锁，器乐看是否有 `instrumental, no vocals` 声明
  7. 方言模式：特征字密度 / 普通话虚词污染 / 入声风险字
  8. 器乐模式（--instrumental）：方括号外有无会被唱出来的文字、有无残留的人声类行内指令；必留段落放宽为 Intro + End
  9. 循环模式（--loop）：有无 fade out、BPM 是否写死、必留段落是否合规
 10. 控件提醒：Style 是「构造过的」时，提示把 Suno 界面上的 Variety 归 0（v6 起该控件
     会改写 Style 文本，且静默发生）——这一项只出「信息」，不算错误也不算警告

用法：
    python3 suno_check.py <歌词文件> [--dialect cantonese] [--style "Style 文本"]
    python3 suno_check.py <歌词文件> --instrumental            # 纯器乐包
    python3 suno_check.py <歌词文件> --instrumental --loop     # 器乐 + 循环素材
    python3 suno_check.py <歌词文件> --json                    # 机器可读输出

退出码：0 = 无错误（可能有警告）；1 = 有错误；2 = 文件读不了
"""

import argparse
import json
import re
import sys

# ---------- 规则数据 ----------

REQUIRED_SECTIONS = ["Intro", "Chorus", "Outro", "End"]

# 器乐 / 循环包放宽后的必留段：循环素材本来就没有 Chorus，也不该有渐弱的 Outro。
REQUIRED_SECTIONS_LOOP = ["Intro", "End"]

# 器乐声明的写法（Style 里至少要命中一个）
INSTRUMENTAL_RE = r"instrumental|no\s+vocals?|without\s+vocals?|no\s+singing|no\s+voice"

# 人声描述词：出现在器乐包的 Style 里就是与 `No vocals` 打架
VOCAL_DESC_RE = (r"\b(female|male|breathy|whispered|whisper|layered|smooth|husky|airy|"
                 r"raspy|child|duet|choir|gospel)\s+(vocals?|voice)")

# 粤语强特征字（卡死语系用）
CANTONESE_MARKERS = list("嘅咗嗰啲唔冇系哋佢边点咩而阵仲喎啩嘞呢睇瞓攞揸企")

# 一旦出现在粤语歌词里就是语系污染。
# 注：只收「粤语里根本不会这么说」的词，不收「時候」这类两地都用的词（粤语也说「呢個時候」），
#     否则会把合规粤语歌词误报成污染。
# 简繁成对列出：粤语常用繁体书写，只收简体会**静默漏报**（2026-09-23 修复）。
MANDARIN_LEAKS = [
    "的时候", "的時候",
    "我们", "我們",
    "什么", "什麼",
    "了吗", "了嗎",
    "这儿", "這兒",
    "那儿", "那兒",
    "有没有", "有沒有",
    "觉得好", "覺得好",
    "一样的", "一樣的",
    "是的",           # 简繁同形
    "不了",           # 简繁同形
    "是不是",         # 简繁同形
]

# 入声/爆破风险字（长音易破）
# 注：必须是「粤语里也能用更平顺的说法替代」的字。像「食」「十」「八」这类高频生活字
#     虽然也是入声，但替代成本高、误报烦人，不列入——规则自相矛盾比没规则更糟。
CANTONESE_RISKY = list("不白哭失湿速急出黑拍血识百七")

# 已内置特征字表的方言 → 其特征字集合
DIALECT_MARKERS = {
    "cantonese": CANTONESE_MARKERS,
}

# 已识别但尚未内置特征字表的方言：传这些值不会因 argparse 直接报错，
# 而是照常做结构与污染检查、跳过「特征字密度」这一项并提示补充。
# （原实现 choices 只放 DIALECT_MARKERS 的 key，导致下游「未内置字表」分支**永远不可达**，2026-09-23 修复。）
KNOWN_UNMAPPED_DIALECTS = [
    "hakka",          # 客家话
    "hokkien",        # 闽南语
    "teochew",        # 潮州话
    "sichuanese",     # 四川话
    "shanghainese",   # 上海话
    "northeastern",   # 东北话
]


def is_cjk(ch):
    o = ord(ch)
    return 0x4E00 <= o <= 0x9FFF


def has_cjk(s):
    return any(is_cjk(c) for c in s)


def parse_sections(text):
    """返回 [(段落名, 标签原文, 行号)]"""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^\s*\[([^\]]+)\]\s*$", line)
        if m:
            out.append((m.group(1).strip(), m.group(0).strip(), i))
    return out


def section_name(tag):
    """从 'Verse 1 – Half-whispered, Intimate' 里取出 'Verse 1'"""
    for sep in ("–", "-", "—"):
        if sep in tag:
            return tag.split(sep)[0].strip()
    return tag.strip()


def check(text, dialect, style, instrumental=False, loop=False):
    errors, warns, info = [], [], []
    lines = text.splitlines()

    # 1. 人声锁。
    #    有人声路径 = 语言锁（必须写）；器乐路径 = 同一位置声明「不唱」，
    #    此时 [Language:]/[Accent:] 反而是有害的（会在 Style 之外再宣告一次"有人声"）。
    lang = re.search(r"\[Language:\s*([^\]]+)\]", text)
    accent = re.search(r"\[Accent:\s*([^\]]+)\]", text)
    if instrumental:
        if lang or accent:
            warns.append(
                "[Language:]/[Accent:] 出现在纯器乐包里 —— 语言与发音要求等于宣告"
                "「这首有人声」，会诱导出哼唱与无词垫音，建议删掉这两行")
        else:
            info.append("未写 [Language:]/[Accent:]（器乐包应当如此）")
    else:
        if not lang:
            errors.append("缺少 [Language: XXX]，Suno 无法锁定语言"
                          "（若这是纯器乐包，请加 --instrumental 重跑）")
        if not accent:
            errors.append("缺少 [Accent: XXX]，方言歌没有这一行必跑偏"
                          "（若这是纯器乐包，请加 --instrumental 重跑）")
    if lang:
        info.append(f"语言 = {lang.group(1).strip()}")
        if re.search(r"\bChinese\b", lang.group(1), re.I) and not re.search(
                r"Mandarin|Cantonese|Hokkien|Wu|Hakka", lang.group(1), re.I):
            errors.append("[Language] 只写了 Chinese，会被默认成普通话——请写具体语言")

    # 2. Style 首字段（有人声 = 语言锁；器乐 = 器乐声明）
    if style:
        first = style.split(",")[0].strip()
        info.append(f"Style 首字段 = {first}")
        if instrumental:
            if not re.search(INSTRUMENTAL_RE, style, re.I):
                errors.append(
                    "声明为纯器乐，但 Style 里找不到 instrumental / no vocals —— "
                    "这是唯一能压住人声的字段，且必须写在最前")
            elif not re.search(INSTRUMENTAL_RE, first, re.I):
                warns.append(
                    f"Style 首字段是「{first}」，器乐声明不在最前 —— "
                    f"靠后的声明压不住流派自带的人声联想，建议挪到第一位")
            bad = re.search(VOCAL_DESC_RE, style, re.I)
            if bad:
                errors.append(
                    f"Style 里的人声描述「{bad.group(0)}」与 No vocals 直接打架，"
                    f"模型会挑一个执行 —— 器乐包请删掉一切人声描述词")
        elif re.search(r"\bChinese\b", first, re.I) and not re.search(
                r"Mandarin|Cantonese|Hokkien|Wu|Hakka", first, re.I):
            errors.append("Style 首字段只写了 Chinese，方言会被打回普通话")

    # 2b. 控件提醒（v6 起）：Style 一旦是「构造过的」，Variety 就必须归 0。
    #     官方原文（v6 FAQ）：Variety「is designed to introduce variety in your outputs by
    #     adjusting and updating your style prompts ... If you'd like to retain full control
    #     of your style tags, reduce the Variety slider to 0.」
    #     → 非 0 时模型收到的 Style 不是你写的那份：语言锁会被扩写、BPM 与 seamless loop
    #       可能被改掉，而这一步**不报任何错**（静默失效）。所以在这里主动提醒，不留给运气。
    if style and re.search(
            r"enunciation|instrumental|no\s+vocals?|\d{2,3}\s*bpm|seamless\s+loop",
            style, re.I):
        info.append(
            "Style 是「构造过的」（含语言锁 / 器乐声明 / BPM / 无缝循环 任一）—— "
            "粘贴前请把 Suno 界面上 More Options 里的 Variety 归 0，"
            "否则它会在提交前改写这段 Style，而这些设置恰恰要靠它保留")

    # 3. 段落标签
    secs = parse_sections(text)
    if not secs:
        errors.append("没有找到任何 [段落标签]")
    for name, raw, ln in secs:
        base = section_name(name)
        compound = any(sep in name for sep in ("–", "-", "—")) or "," in name
        # [End] 与 [Language]/[Accent] 不要求复合；
        # 但循环包的收尾方式必须交代清楚，裸 [End] 说明没写怎么接回开头。
        if base.lower() == "end":
            if loop and not compound:
                warns.append(
                    f"第 {ln} 行 [End] 是裸标签 —— 循环包要在这里交代收尾方式"
                    f"（如 `[End – Return to opening chord and texture, Clean cut, No fade out]`）")
            continue
        if re.match(r"^(Language|Accent)\s*:", name, re.I):
            continue
        if not compound:
            warns.append(f"第 {ln} 行 [{base}] 是裸标签，没给编曲与演唱指令——AI 会自由发挥")
        if has_cjk(name):
            errors.append(f"第 {ln} 行标签含中文「{name}」，会被当人声唱出——标签一律用英文")

    # 4. 必留段落（器乐包与循环素材都放宽为 Intro + End：
    #    器乐里没有「副歌」这个概念，循环素材也不该有渐弱的 Outro）
    relaxed = loop or instrumental
    required = REQUIRED_SECTIONS_LOOP if relaxed else REQUIRED_SECTIONS
    bases = [section_name(s[0]).lower() for s in secs]
    for req in required:
        if req.lower() not in bases:
            errors.append(f"缺少必留段落 [{req}]")
    if loop:
        info.append("循环模式：必留段落放宽为 Intro + End（不要求 Chorus / Outro）")
    elif instrumental:
        info.append("纯器乐：必留段落放宽为 Intro + End（器乐无副歌，也不该有渐弱的 Outro）")

    # 5. 括号配对
    for i, line in enumerate(lines, 1):
        if line.count("(") != line.count(")"):
            warns.append(f"第 {i} 行圆括号不配对：{line.strip()[:40]}")
        if "(—" in line and "—)" not in line:
            warns.append(f"第 {i} 行 (— 音效括号未闭合：{line.strip()[:40]}")

    # 6. 器乐模式专项：方括号外不许有内容，人声类行内指令要清掉
    if instrumental:
        stray = []
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if not s:
                continue
            residual = re.sub(r"\([^()]*\)", "", s)             # 去掉行内指令
            residual = re.sub(r"\[[^\[\]]*\]", "", residual)    # 去掉段落标签
            if residual.strip():
                stray.append((i, s[:40]))
        if stray:
            errors.append(
                f"声明为纯器乐，但方括号外有 {len(stray)} 行文字会被当作歌词唱出来"
                f"（首个在第 {stray[0][0]} 行：{stray[0][1]}）—— 器乐包方括号外必须留空")
        vocal_cues = []
        for i, line in enumerate(lines, 1):
            for m in re.finditer(r"\(([^()]*)\)", line):
                if "—" not in m.group(1):
                    vocal_cues.append((i, m.group(0)))
        if vocal_cues:
            warns.append(
                f"第 {vocal_cues[0][0]} 行 {vocal_cues[0][1]} 是人声类行内指令的写法"
                f"（规则 5：非人声音效应写成 (—...—)），器乐包里可能被当作和声或垫音")

    # 7. 循环模式专项：禁淡出、锁死 BPM
    #    注意先剔掉「No fade out / No fade in」这类**否定写法** —— 它们正是规范要求写的，
    #    若直接搜 "fade out" 会把合规的收尾标签判成违规（文档要求这么写、脚本却报错）。
    def _wants_fade(s):
        return bool(re.search(r"fade[ -]?out|fading",
                              re.sub(r"no\s+fade[ -]?(out|in)", "", s, flags=re.I), re.I))

    if loop:
        faded = [(ln, raw) for name, raw, ln in secs if _wants_fade(raw)]
        if faded:
            errors.append(
                f"第 {faded[0][0]} 行写了 fade out（{faded[0][1]}）—— 循环素材不能淡出，"
                f"否则每圈之间出现音量豁口；收尾请改成回到开头的和弦与织体、干净切断")
        if style:
            if _wants_fade(style):
                errors.append("Style 里写了 fade out —— 循环素材不能淡出，请改成 `No fade out`")
            if not re.search(r"seamless\s+loop|loop", style, re.I):
                warns.append("循环包建议在 Style 里写 `Seamless loop, No fade in, No fade out`")
            if not re.search(r"\d{2,3}\s*bpm", style, re.I):
                errors.append(
                    "循环包必须在 Style 里写死 BPM 数字（如 `84 BPM`）—— BPM 不锁死，"
                    "输出会漂移、循环点落在小节中间，怎么剪都有断层")
        else:
            info.append("未提供 --style，跳过器乐声明与 BPM 检查（这两项依赖 Style 文本）")

    # 8. 方言检查
    if dialect:
        markers = DIALECT_MARKERS.get(dialect)
        body = "\n".join(
            l for l in lines if not re.match(r"^\s*\[", l))          # 排除标签行
        if markers is None:
            warns.append(
                f"未内置 {dialect} 的特征字表，跳过「特征字密度」检查"
                f"（结构与普通话污染检查照常执行；可在脚本 DIALECT_MARKERS 中补充字表）")
        else:
            cjk_chars = [c for c in body if is_cjk(c)]
            if not cjk_chars:
                warns.append("歌词正文里没有中文字符，方言检查跳过")
            else:
                hit = sum(1 for c in cjk_chars if c in markers)
                density = hit / len(cjk_chars)
                info.append(f"{dialect} 特征字密度 = {density:.1%}（{hit}/{len(cjk_chars)} 汉字）")
                if density < 0.03:
                    errors.append(
                        f"特征字密度仅 {density:.1%}，语系没锁死——"
                        f"请通篇使用「{'、'.join(markers[:8])}」等强特征字")
                elif density < 0.06:
                    warns.append(f"特征字密度 {density:.1%} 偏低，仍有跑偏风险，建议加强")
                risky_hit = sorted({c for c in cjk_chars if c in CANTONESE_RISKY})
                if risky_hit:
                    warns.append(
                        f"命中入声/爆破风险字：{'、'.join(risky_hit)} —— "
                        f"换平顺字或用 (ah)/(oh...) 做声调补偿")
        # 污染检查与特征字表无关：任何方言都不该混入普通话虚词，
        # 所以放在 markers 分支之外 —— 未内置字表的方言同样要查（否则又是一处静默跳过）。
        for leak in MANDARIN_LEAKS:
            if leak in body:
                warns.append(f"混入普通话表达「{leak}」，会造成语系污染")
        if style and "Smooth vocals" not in style and "Polished production" not in style:
            warns.append("方言歌建议在 Style 中加 `Smooth vocals, Polished production` 防破音")
        if style and re.search(r"distorted|bitcrushed", style, re.I):
            errors.append("Style 含 distorted/bitcrushed，与方言平滑人声冲突，必破音")

    # 9. 看起来像器乐包却没声明 → 显式提醒（不静默、也不替用户猜）
    if not instrumental:
        lyric_lines = []
        for line in lines:
            s = line.strip()
            if not s or re.match(r"^\s*\[", s):
                continue
            if re.sub(r"\([^()]*\)", "", s).strip():
                lyric_lines.append(s)
        if not lyric_lines:
            warns.append(
                "方括号外没有任何内容，看起来是纯器乐包 —— 若确实无人声，请加 --instrumental "
                "重跑（当前按有人声规则检查，上面关于 [Language:]/[Accent:] 的错误不适用）；"
                "若只是漏填语言锁，请补上")

    return errors, warns, info


def main():
    ap = argparse.ArgumentParser(description="Suno 歌曲包结构校验")
    ap.add_argument("file", help="歌词文件（纯文本）")
    ap.add_argument("--dialect", choices=list(DIALECT_MARKERS) + KNOWN_UNMAPPED_DIALECTS,
                    help="方言模式（已内置特征字表的：cantonese；其余已知方言会跳过字表检查）")
    ap.add_argument("--style", help="Style 文本（用于检查语言锁与冲突指令）")
    ap.add_argument("--instrumental", action="store_true",
                    help="纯器乐包：不要求 [Language:]/[Accent:]，改为检查器乐声明、"
                         "方括号外有无歌词、有无残留人声描述；必留段落放宽为 Intro + End")
    ap.add_argument("--loop", action="store_true",
                    help="循环素材：在器乐放宽的基础上，另检查 fade out 与 BPM 是否锁死")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    try:
        text = open(args.file, encoding="utf-8").read()
    except UnicodeDecodeError as e:
        print(f"[读取失败] {args.file}: 不是 UTF-8 文本（{e.reason}，位置 {e.start}）。"
              f"请转存为 UTF-8 后重试。", file=sys.stderr)
        sys.exit(2)
    except OSError as e:
        print(f"[读取失败] {args.file}: {e}", file=sys.stderr)
        sys.exit(2)

    errors, warns, info = check(text, args.dialect, args.style,
                                instrumental=args.instrumental, loop=args.loop)

    if args.json:
        print(json.dumps({"errors": errors, "warnings": warns, "info": info},
                         ensure_ascii=False, indent=2))
        sys.exit(1 if errors else 0)

    tags = []
    if args.dialect:
        tags.append(f"方言: {args.dialect}")
    if args.instrumental:
        tags.append("纯器乐")
    if args.loop:
        tags.append("循环")
    print(f"校验：{args.file}" + (f"  [{', '.join(tags)}]" if tags else ""))
    if info:
        print("\n信息")
        for i in info:
            print(f"  · {i}")
    print(f"\n错误 {len(errors)} 项")
    for e in errors:
        print(f"  [XX] {e}")
    if not errors:
        print("  无")
    print(f"\n警告 {len(warns)} 项")
    for w in warns:
        print(f"  [!!] {w}")
    if not warns:
        print("  无")

    print("\n注：本脚本只做结构检查，不评价文风。歌词好不好，还得你自己听。")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
