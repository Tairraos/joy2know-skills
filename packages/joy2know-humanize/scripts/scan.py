#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""晓得·凡人腔调 —— 命中定位（只读，不改稿）。

    python3 scan.py <稿件.md>                扫描并输出命中清单
    python3 scan.py <稿件.md> --triage       只输出豁免区地图
    python3 scan.py <稿件.md> --audit 20     随机抽 20 条命中，连上下文一起打印
    python3 scan.py --render                 由 rules.py 重生成 references/ 下两份文档
    python3 scan.py <稿件.md> --json         机器可读输出

设计取舍
--------------------------------------------------------------
1. 本脚本只读。它把「哪一句命中了哪条规则」变成可核对的清单，
   改不改、怎么改仍由人和模型决定。
2. 命中不等于必改。--audit 就是为此存在的：先看命中实例长什么样，再决定动不动手。
   算子的覆盖范围总会比规则名宽一点，只看频率数字是发现不了的。
3. 豁免区先于命中判定。代码块、引用、表格、列表、标题不进扫描，
   正文里的问句、引语段落也跳过——省掉的不是工作量，是误改。
"""

import argparse
import io
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rules as R  # noqa: E402

# ------------------------------------------------------------------ 行分类

KIND_BODY = "body"
KIND_HEADING = "heading"
KIND_TABLE = "table"
KIND_LIST = "list"
KIND_QUOTE = "quote"
KIND_FENCE = "fence"
KIND_FRONTMATTER = "frontmatter"
KIND_IMAGE = "image"
KIND_BLANK = "blank"

LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S")
HEADING_RE = re.compile(r"^#{1,6}\s+\S")
BOLD_HEADING_RE = re.compile(r"^\s*\*\*[^*\n]+\*\*\s*$")   # 独立成行的加粗文本＝小标题
FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")
IMAGE_RE = re.compile(r"^\s*(?:!\[|\[[^\]]*\]\()")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def classify(text):
    """把稿件切成带类型的行。返回 [(lineno, kind, raw)]，lineno 从 1 开始。"""
    lines = text.split("\n")
    out = []
    in_fence = False
    in_fm = False
    fm_done = False

    for i, raw in enumerate(lines, 1):
        s = raw.strip()

        # 文件开头的 YAML frontmatter
        if i == 1 and s == "---":
            in_fm = True
            out.append((i, KIND_FRONTMATTER, raw))
            continue
        if in_fm:
            out.append((i, KIND_FRONTMATTER, raw))
            if s in ("---", "..."):
                in_fm = False
                fm_done = True
            continue
        if not fm_done and i == 1 and s != "":
            pass

        if FENCE_RE.match(raw):
            in_fence = not in_fence
            out.append((i, KIND_FENCE, raw))
            continue
        if in_fence:
            out.append((i, KIND_FENCE, raw))
            continue

        if s == "":
            out.append((i, KIND_BLANK, raw))
        elif s.startswith(">"):
            out.append((i, KIND_QUOTE, raw))
        elif HEADING_RE.match(raw) or BOLD_HEADING_RE.match(raw):
            out.append((i, KIND_HEADING, raw))
        elif TABLE_RE.match(raw):
            out.append((i, KIND_TABLE, raw))
        elif LIST_RE.match(raw):
            out.append((i, KIND_LIST, raw))
        elif IMAGE_RE.match(raw):
            out.append((i, KIND_IMAGE, raw))
        else:
            out.append((i, KIND_BODY, raw))
    return out


def code_spans(line):
    """行内代码的字符区间，命中落进来就作废。"""
    return [(m.start(), m.end()) for m in INLINE_CODE_RE.finditer(line)]


def line_starts(text):
    """每一行在全文里的起始偏移。line_starts[i] 即第 i+1 行的起点。"""
    out = [0]
    for line in text.split("\n"):
        out.append(out[-1] + len(line) + 1)
    return out


def sentence_spans(text):
    """把全文切成句子区间 [(start, end)]，句末标点含在内。

    这是门禁判定「越界改动」的粒度单位：一处改动只要落在某个句子里，
    而那个句子里有规则命中，就算有据可查。按行判太粗——同一行里的
    另一句话被顺手润色，也能蒙混过关。
    """
    spans = []
    start = 0
    for i, ch in enumerate(text):
        if ch in "。！？；\n":
            if i + 1 > start:
                spans.append((start, i + 1))
            start = i + 1
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def build_paragraphs(rows):
    """连续 body 行构成一段。返回 [(first_lineno, last_lineno, text)]。"""
    paras = []
    buf = []
    start = None
    for lineno, kind, raw in rows:
        if kind == KIND_BODY:
            if not buf:
                start = lineno
            buf.append(raw)
        else:
            if buf:
                paras.append((start, start + len(buf) - 1, "\n".join(buf)))
                buf = []
    if buf:
        paras.append((start, start + len(buf) - 1, "\n".join(buf)))
    return paras


def first_sentence(s):
    """第一句：切到第一个句末标点为止。"""
    m = re.search(r"[。！？]", s)
    return s[: m.end()] if m else s


def is_dialogue(para_text):
    """整段是引语的段落：跳过。"""
    t = para_text.strip()
    if len(t) < 4:
        return False
    head, tail = t[0], t[-1]
    return (head, tail) in {("「", "」"), ("“", "”"), ("『", "』")}


def is_mostly_chinese(s):
    zh = len(re.findall(r"[\u4e00-\u9fff]", s))
    en = len(re.findall(r"[A-Za-z]", s))
    return zh >= en


# ------------------------------------------------------------------ 规则求值

def _sig(sent):
    """句法指纹：逗号数 + 长度档。"""
    return (sent.count("，"), len(sent) // 8)


def _split_sentences(para):
    return [s.strip() for s in re.split(r"[。！？]", para) if len(s.strip()) >= 4]


def evaluate(text, rule_list=None, apply_min_hits=True):
    """按规则表扫描稿件。返回命中列表。

    apply_min_hits=False 用于规则表自检：跳过「全篇命中数」这类条件，
    单独验一条样本有没有被算子接住。
    """
    rule_list = rule_list or R.all_rules()
    rows = classify(text)
    paras = build_paragraphs(rows)
    starts = line_starts(text)
    hits = []

    def add(rule, lineno, snippet, offset=0, span_len=0):
        abs_start = starts[lineno - 1] + offset if lineno - 1 < len(starts) else 0
        hits.append({
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "priority": rule.get("priority", "P2"),
            "evidence": rule.get("evidence", "measured"),
            "fixable": bool(rule.get("fix")),
            "line": lineno,
            "offset": offset,
            "span_left": abs_start,
            "span_right": abs_start + (span_len or len(snippet)),
            "snippet": snippet,
            "note": "可机械替换（fix.py）" if rule.get("fix") else "需人工改",
        })

    def match_any(rule, s):
        for pat in rule.get("triggers", []):
            m = re.search(pat, s)
            if m:
                return m
        return None

    def vetoed(rule, s):
        v = rule.get("veto")
        return bool(v and re.search(v, s))

    for rule in rule_list:
        scope = rule.get("scope", "inline")
        got = []

        if scope == "inline":
            for lineno, kind, raw in rows:
                # 标题行也算正文：编号由 R05 处理，措辞照样归其他规则管。
                # 表格、引用、列表、代码不进扫描。
                if kind not in (KIND_BODY, KIND_HEADING):
                    continue
                if vetoed(rule, raw):
                    continue
                spans = code_spans(raw)
                found = []
                for pat in rule.get("triggers", []):
                    for m in re.finditer(pat, raw):
                        # 落在行内代码里的命中不算
                        if any(m.start() < e and m.end() > s for s, e in spans):
                            continue
                        if any(m.start() < x[1] and m.end() > x[0] for x in found):
                            continue
                        found.append((m.start(), m.end()))
                    if len(found) >= 4:
                        break
                for st, en in found[:4]:
                    got.append((lineno, raw[max(0, st - 12): en + 12], st, en - st))

        elif scope == "paragraph":
            for first, _last, para in paras:
                if not is_mostly_chinese(para) or is_dialogue(para):
                    continue
                s = first_sentence(para)
                if vetoed(rule, s):
                    continue
                m = match_any(rule, s)
                if m:
                    got.append((first, s.strip()[:60], m.start(), m.end() - m.start()))

        elif scope == "heading":
            for lineno, kind, raw in rows:
                if kind != KIND_HEADING:
                    continue
                m = match_any(rule, raw)
                if m:
                    got.append((lineno, raw.strip()[:60], m.start(), m.end() - m.start()))

        elif scope == "before-list":
            body = [(n, k, r) for n, k, r in rows]
            for idx, (lineno, kind, raw) in enumerate(body):
                if kind != KIND_BODY:
                    continue
                m = match_any(rule, raw)
                if not m:
                    continue
                nxt = None
                for j in range(idx + 1, len(body)):
                    if body[j][1] == KIND_BLANK:
                        continue
                    nxt = body[j]
                    break
                if nxt and nxt[1] == KIND_LIST:
                    got.append((lineno, raw.strip()[:60], m.start(), m.end() - m.start()))

        elif scope == "sentence-signature":
            for first, last, para in paras:
                if not is_mostly_chinese(para) or is_dialogue(para):
                    continue
                sents = _split_sentences(para)
                for i in range(len(sents) - 1):
                    a, b = sents[i], sents[i + 1]
                    if len(a) < 10 or len(b) < 10:
                        continue
                    if _sig(a) == _sig(b) and a.count("，") >= 1:
                        # 作用域是整段：打散句法可能动到段内任何一句
                        got.append((first, (a + "。" + b)[:60], 0,
                                    starts[last] - starts[first] if last < len(starts) else 0))
                        break

        min_hits = rule.get("min_hits", 0)
        if apply_min_hits and min_hits and len(got) < min_hits:
            got = []   # 未达全篇阈值：整条不报
        for item in got:
            add(rule, item[0], item[1], item[2], item[3] if len(item) > 3 else 0)

    hits.sort(key=lambda h: ({"P0": 0, "P1": 1, "P2": 2}.get(h["priority"], 9), h["line"]))
    return hits


# ------------------------------------------------------------------ 豁免区地图

def triage(text):
    rows = classify(text)
    zones = {}
    for lineno, kind, raw in rows:
        if kind in (KIND_BODY, KIND_BLANK):
            continue
        zones.setdefault(kind, []).append(lineno)
    return zones


ZONE_LABEL = {
    KIND_FENCE: "围栏代码块",
    KIND_QUOTE: "引用块",
    KIND_TABLE: "表格行",
    KIND_LIST: "列表行",
    KIND_HEADING: R.HEADING_ZONE_NOTE,
    KIND_FRONTMATTER: "YAML frontmatter",
    KIND_IMAGE: "图片／链接行",
}


def ranges(nums):
    out, start, prev = [], None, None
    for n in nums:
        if start is None:
            start = prev = n
        elif n == prev + 1:
            prev = n
        else:
            out.append((start, prev))
            start = prev = n
    if start is not None:
        out.append((start, prev))
    return out


def fmt_ranges(nums):
    return ", ".join(f"{a}" if a == b else f"{a}-{b}" for a, b in ranges(nums))


# ------------------------------------------------------------------ 报告

def stats(text):
    rows = classify(text)
    body = sum(1 for _, k, _ in rows if k == KIND_BODY)
    zh = len(re.findall(r"[\u4e00-\u9fff]", text))
    return {"lines": len(rows), "body_lines": body, "chars": zh,
            "paragraphs": len(build_paragraphs(rows))}


def print_triage(text):
    z = triage(text)
    st = stats(text)
    print(f"稿件规模：{st['lines']} 行，正文 {st['body_lines']} 行，{st['chars']} 汉字，"
          f"{st['paragraphs']} 段\n")
    print("豁免区地图（这些位置不进入扫描）")
    print("-" * 72)
    if not z:
        print("  （无）")
    for kind, nums in z.items():
        label = ZONE_LABEL.get(kind, kind)
        print(f"  {label:<28} {len(nums):>4} 行   {fmt_ranges(sorted(nums))}")
    print()
    print("豁免不是遗漏：代码、引用、表格、列表本身就是结构，改了会散架。")
    print("只有引出列表的那一句话（R03）会看列表前面的正文。")
    print("标题行**不豁免**——编号归 R05，措辞归其他规则；受保护的是标题的层级与顺序，")
    print("那条约束在 guard.py 的结构守恒里。")


def print_hits(text, hits, show_all=True):
    st = stats(text)
    by_p = {"P0": 0, "P1": 0, "P2": 0}
    for h in hits:
        by_p[h["priority"]] = by_p.get(h["priority"], 0) + 1
    n_fix = sum(1 for h in hits if h["fixable"])

    print(f"稿件规模：{st['body_lines']} 行正文，{st['chars']} 汉字，{st['paragraphs']} 段")
    print(f"命中 {len(hits)} 处：P0 {by_p.get('P0', 0)} / P1 {by_p.get('P1', 0)} / "
          f"P2 {by_p.get('P2', 0)}；其中 {n_fix} 处可机械替换\n")

    if not hits:
        print("没有命中任何规则。")
        return

    print(f"{'优先级':<6}{'规则':<5}{'行':>5}  {'证据':<9}{'动作':<20}命中片段")
    print("-" * 100)
    for h in hits:
        snip = h["snippet"].replace("\n", "⏎")
        print(f"{h['priority']:<6}{h['rule_id']:<5}{h['line']:>5}  "
              f"{R.EVIDENCE_LABEL.get(h['evidence'], h['evidence'])[:8]:<9}"
              f"{h['note']:<20}{snip}")

    print()
    print("命中不等于必改：先看 references/rules.md 里该条的「不改的情况」，")
    print("再用 --audit 抽样看上下文，确认是这条规则要治的病，再动手。")


def cmd_audit(text, n, seed=None):
    hits = evaluate(text)
    if not hits:
        print("没有命中，无需抽样。")
        return 0
    rnd = random.Random(seed)
    sample = rnd.sample(hits, min(n, len(hits)))
    lines = text.split("\n")
    print(f"抽样检视 {len(sample)} / {len(hits)} 条命中")
    print("看什么：命中片段是不是这条规则真要治的病。算子的覆盖范围总会比规则名宽一些，")
    print("      只看频率数字发现不了这件事——先看命中，再采信算子。\n")
    for h in sorted(sample, key=lambda x: x["line"]):
        ln = h["line"]
        print(f"── {h['rule_id']} {h['rule_name']} · 行 {ln} · {h['priority']}")
        for j in range(max(1, ln - 1), min(len(lines), ln + 1) + 1):
            mark = ">>" if j == ln else "  "
            print(f"   {mark} {j:>4} | {lines[j - 1]}")
        print(f"   命中：{h['snippet']}")
        print()
    return 0


# ------------------------------------------------------------------ 文档生成

def _md_rules():
    L = []
    L.append("<!-- 本文件由 scripts/rules.py 生成，不要手改。改规则请改 rules.py，"
             "然后跑 python3 scripts/scan.py --render -->")
    L.append("")
    L.append("# 规则全表")
    L.append("")
    L.append(f"规则表版本 {R.VERSION} · 适用范围：{R.SCOPE} · 共 {len(R.RULES)} 条")
    L.append("")
    L.append("优先级：**P0 必改** —— 改一条赚一条；**P1 应改** —— 不改就还是模板；"
             "**P2 视情况** —— 证据偏弱，看整篇密度决定。")
    L.append("")
    L.append("证据等级：强（约 3 倍以上）／中（约 2–3 倍）／弱（约 1.25–2 倍）／"
             "反向（人类侧更高，只能禁止反向改）／不稳定（组间或跨模型差异过大）／"
             "本版新增（无对照数据，可选）。量级口径见 baseline.md。")
    L.append("")
    L.append("| 规则 | 名称 | 优先级 | 证据 | 评估范围 | 可机械替换 |")
    L.append("|---|---|---|---|---|---|")
    for r in R.RULES:
        L.append(f"| {r['id']} | {r['name']} | {r['priority']} | "
                 f"{R.EVIDENCE_LABEL.get(r['evidence'], r['evidence'])} | "
                 f"{r.get('scope', 'inline')} | {'是' if r.get('fix') else '否'} |")
    L.append("")
    L.append("---")
    L.append("")

    for r in R.RULES:
        L.append(f"## {r['id']} {r['name']}")
        L.append("")
        L.append(f"**优先级** {r['priority']} · **证据** {R.EVIDENCE_LABEL.get(r['evidence'], r['evidence'])}"
                 f" · **评估范围** {r.get('scope', 'inline')}"
                 f" · **机械可替换** {'是' if r.get('fix') else '否'}")
        L.append("")
        L.append(f"**它坏在哪。** {r['why']}")
        L.append("")
        L.append("**触发标记。**")
        L.append("")
        if r.get("triggers"):
            for t in r["triggers"]:
                L.append(f"- `{t}`")
        elif r.get("scope") == "sentence-signature":
            L.append("- 段内相邻两句：逗号数相同、长度同档、每句不少于 10 字，"
                     "且句中逗号不少于 1 个")
        else:
            L.append("- （无正则触发，见评估范围）")
        if r.get("veto"):
            L.append("")
            L.append(f"**否决标记**（命中即取消本次命中）：`{r['veto']}`")
        if r.get("min_hits"):
            L.append("")
            L.append(f"**全篇阈值**：同一条命中数达到 {r['min_hits']} 才报。")
        L.append("")
        L.append(f"**改法。** {r['how']}")
        L.append("")
        if r.get("fix"):
            L.append("**机械替换（fix.py 可直接执行）。**")
            L.append("")
            for pat, rep in r["fix"]:
                L.append(f"- `{pat}` → `{rep}`")
            L.append("")
        elif r["scope"] != "sentence-signature":
            L.append("**机械替换。** 无。这条必须人工改——脚本只做不需要读懂句意就能改对的事。")
            L.append("")
        if r.get("fix_note"):
            L.append(f"> {r['fix_note']}")
            L.append("")
        L.append("**不改的情况。**")
        L.append("")
        for k in r["keep"]:
            L.append(f"- {k}")
        L.append("")
        L.append("**正反例。**")
        L.append("")
        for ex in r["examples"]:
            L.append(f"> ❌ {ex['bad']}")
            L.append(">")
            L.append(f"> ✅ {ex['good']}")
            L.append("")
        if r.get("guards"):
            L.append("**必须不被命中的反例**（selftest 拿它当测试用例）。")
            L.append("")
            for g in r["guards"]:
                L.append(f"- {g}")
            L.append("")
        L.append("---")
        L.append("")
    return "\n".join(L)


def _md_not_rules():
    L = []
    L.append("<!-- 本文件由 scripts/rules.py 生成，不要手改。 -->")
    L.append("")
    L.append("# 不可改清单")
    L.append("")
    L.append("这张表和规则表一样是硬约束。列在这里的特征**看着像 AI 腔，实测站不住**，"
             "不能据此改文字。它们在公共讨论里流通得很广，所以每隔一段时间就会有人"
             "「顺手」按它们改一遍——那正是这篇文章要被退回的原因。")
    L.append("")
    L.append("区分原则：**规则的依据是触发标记可定位，不是频率高低。**")
    L.append("")
    L.append("| 特征 | 证据 | 为什么不改 |")
    L.append("|---|---|---|")
    for n in R.NOT_RULES:
        L.append(f"| {n['name']} | {R.EVIDENCE_LABEL.get(n['evidence'], n['evidence'])} | {n['why']} |")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 还有一层：不因为「读着不像人写的」就改")
    L.append("")
    L.append("主观上觉得某句生硬、不像中文，不构成改动理由。只有能在规则表里指出"
             "触发标记的，才允许动。指不出对应规则号的改动一律撤销。")
    L.append("")
    L.append("## 豁免区")
    L.append("")
    L.append("| 区块 | 说明 |")
    L.append("|---|---|")
    for _k, label, why in R.EXEMPT_ZONES:
        L.append(f"| {label} | {why} |")
    L.append("")
    return "\n".join(L)


def cmd_render():
    here = os.path.dirname(os.path.abspath(__file__))
    ref = os.path.join(os.path.dirname(here), "references")
    os.makedirs(ref, exist_ok=True)
    p1 = os.path.join(ref, "rules.md")
    p2 = os.path.join(ref, "not-rules.md")
    with io.open(p1, "w", encoding="utf-8") as f:
        f.write(_md_rules())
    with io.open(p2, "w", encoding="utf-8") as f:
        f.write(_md_not_rules())
    print(f"已生成 {p1}")
    print(f"已生成 {p2}")
    print(f"规则 {len(R.RULES)} 条，不可改清单 {len(R.NOT_RULES)} 条。")
    return 0


# ------------------------------------------------------------------ CLI

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="晓得·凡人腔调 —— 命中定位（只读）", add_help=True)
    ap.add_argument("path", nargs="?", help="稿件路径（.md 或纯文本）")
    ap.add_argument("--triage", action="store_true", help="只输出豁免区地图")
    ap.add_argument("--audit", type=int, metavar="N", help="随机抽 N 条命中连上下文打印")
    ap.add_argument("--seed", type=int, default=None, help="抽样随机种子（便于复现）")
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    ap.add_argument("--render", action="store_true", help="由 rules.py 重生成 references/ 文档")
    ap.add_argument("--rules", help="只跑指定规则，逗号分隔，如 R01,R02")
    args = ap.parse_args(argv)

    if args.render:
        return cmd_render()

    if not args.path:
        ap.print_help()
        return 2

    if not os.path.exists(args.path):
        print(f"找不到稿件：{args.path}")
        return 2

    with io.open(args.path, encoding="utf-8") as f:
        text = f.read()

    if args.triage:
        print_triage(text)
        return 0

    if args.audit is not None:
        return cmd_audit(text, args.audit, args.seed)

    rule_list = R.all_rules()
    if args.rules:
        want = {x.strip().upper() for x in args.rules.split(",")}
        rule_list = [r for r in rule_list if r["id"] in want]
        if not rule_list:
            print(f"没有匹配的规则号：{args.rules}")
            return 2

    hits = evaluate(text, rule_list)
    if args.json:
        print(json.dumps({
            "file": os.path.abspath(args.path),
            "stats": stats(text),
            "triage": {k: len(v) for k, v in triage(text).items()},
            "hits": hits,
        }, ensure_ascii=False, indent=2))
        return 0

    print_hits(text, hits)
    return 0


if __name__ == "__main__":
    sys.exit(main())
