#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
晓得·音乐人 —— Suno 歌曲包结构校验

用途：把「写得好不好」里能机器判断的那部分先捞出来。
     它只做结构检查，不评价文风——文风好不好由人和耳朵判断。

检查项：
  1. 是否写了 [Language:] / [Accent:]
  2. 段落标签是否为复合结构（至少含一项描述）
  3. 必留段落是否齐全（Intro / Chorus / Outro / End）
  4. 括号是否配对（圆括号 与 (— —) 两种）
  5. 标签里是否混入了中文（会被当人声唱出）
  6. Style 是否写在最前、语言锁是否到位（--style 指定 Style 行时）
  7. 方言模式：特征字密度 / 普通话虚词污染 / 入声风险字

用法：
    python3 suno_check.py <歌词文件> [--dialect cantonese] [--style "Style 文本"]
    python3 suno_check.py <歌词文件> --json      # 机器可读输出

退出码：0 = 无错误（可能有警告）；1 = 有错误；2 = 文件读不了
"""

import argparse
import json
import re
import sys

# ---------- 规则数据 ----------

REQUIRED_SECTIONS = ["Intro", "Chorus", "Outro", "End"]

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


def check(text, dialect, style):
    errors, warns, info = [], [], []
    lines = text.splitlines()

    # 1. 语言锁
    lang = re.search(r"\[Language:\s*([^\]]+)\]", text)
    accent = re.search(r"\[Accent:\s*([^\]]+)\]", text)
    if not lang:
        errors.append("缺少 [Language: XXX]，Suno 无法锁定语言")
    if not accent:
        errors.append("缺少 [Accent: XXX]，方言歌没有这一行必跑偏")
    if lang:
        info.append(f"语言 = {lang.group(1).strip()}")
        if re.search(r"\bChinese\b", lang.group(1), re.I) and not re.search(
                r"Mandarin|Cantonese|Hokkien|Wu|Hakka", lang.group(1), re.I):
            errors.append("[Language] 只写了 Chinese，会被默认成普通话——请写具体语言")

    # 2. Style 语言锁
    if style:
        first = style.split(",")[0].strip()
        info.append(f"Style 首字段 = {first}")
        if re.search(r"\bChinese\b", first, re.I) and not re.search(
                r"Mandarin|Cantonese|Hokkien|Wu|Hakka", first, re.I):
            errors.append("Style 首字段只写了 Chinese，方言会被打回普通话")

    # 3. 段落标签
    secs = parse_sections(text)
    if not secs:
        errors.append("没有找到任何 [段落标签]")
    for name, raw, ln in secs:
        base = section_name(name)
        compound = any(sep in name for sep in ("–", "-", "—")) or "," in name
        # [End] 与 [Language]/[Accent] 不要求复合
        if base.lower() == "end":
            continue
        if re.match(r"^(Language|Accent)\s*:", name, re.I):
            continue
        if not compound:
            warns.append(f"第 {ln} 行 [{base}] 是裸标签，没给编曲与演唱指令——AI 会自由发挥")
        if has_cjk(name):
            errors.append(f"第 {ln} 行标签含中文「{name}」，会被当人声唱出——标签一律用英文")

    # 4. 必留段落
    bases = [section_name(s[0]).lower() for s in secs]
    for req in REQUIRED_SECTIONS:
        if req.lower() not in bases:
            errors.append(f"缺少必留段落 [{req}]")

    # 5. 括号配对
    for i, line in enumerate(lines, 1):
        if line.count("(") != line.count(")"):
            warns.append(f"第 {i} 行圆括号不配对：{line.strip()[:40]}")
        if "(—" in line and "—)" not in line:
            warns.append(f"第 {i} 行 (— 音效括号未闭合：{line.strip()[:40]}")

    # 6. 方言检查
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

    return errors, warns, info


def main():
    ap = argparse.ArgumentParser(description="Suno 歌曲包结构校验")
    ap.add_argument("file", help="歌词文件（纯文本）")
    ap.add_argument("--dialect", choices=list(DIALECT_MARKERS) + KNOWN_UNMAPPED_DIALECTS,
                    help="方言模式（已内置特征字表的：cantonese；其余已知方言会跳过字表检查）")
    ap.add_argument("--style", help="Style 文本（用于检查语言锁与冲突指令）")
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

    errors, warns, info = check(text, args.dialect, args.style)

    if args.json:
        print(json.dumps({"errors": errors, "warnings": warns, "info": info},
                         ensure_ascii=False, indent=2))
        sys.exit(1 if errors else 0)

    print(f"校验：{args.file}" + (f"  [方言: {args.dialect}]" if args.dialect else ""))
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
