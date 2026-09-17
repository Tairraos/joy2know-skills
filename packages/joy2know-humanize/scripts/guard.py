#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""晓得·凡人腔调 —— 改写门禁（只读，只比较，不改稿）。

    python3 guard.py --before 原稿.md --after 改后.md
    python3 guard.py --before 原稿.md --after 改后.md --json

它把「改写有没有越界」从模型的自我声明，变成可执行的判据。
退出码：0 通过 / 1 有硬违规（不许交稿） / 2 用法或读文件出错。

四道检查
--------------------------------------------------------------
1 硬守恒   数字、引语、书名号、链接、英文串        → 增删即违规
2 强度守恒 「可能／通常／据说」这类限定词计数      → 计数不等即违规
3 结构守恒 标题层级序列、段落数、代码块、表格、    → 任何变化即违规
           引用、列表项数
4 越界改动 有变化的行，必须落在某条规则的命中行上  → 不在即违规

为什么需要第 4 条
--------------------------------------------------------------
「每一处改动都要能指出对应哪条规则」是这类改写最核心的约束，也是最难自查的一条：
同一段文字既是被改的对象，又是自查的依据，写着写着就顺手润色掉了。
这里用 diff 把每一处变化的位置钉出来，再拿规则命中位置去对——对不上的就是越界，
不管它读起来多顺。

第 1、2 条是它的补充：越界改动有时表现为「词换了但句法没动」，
位置对得上却把限定词吃掉了。所以守恒检查按元素而不是按位置做。
"""

import argparse
import collections
import difflib
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rules as R      # noqa: E402
import scan            # noqa: E402

PUNCT_ONLY = set("。！？；，、：:,.!?;…—－-— \t\n\u3000\"'“”‘’「」『』（）()《》〈〉[]【】")

Ok, Bad, Info = "ok", "bad", "info"


def count_units(texts, pats):
    c = collections.Counter()
    for t in texts:
        for p in pats:
            for m in re.finditer(p, t):
                c[m.group(0)] += 1
    return c


def diff_counter(before, after, label, pats_or_words, is_words=False):
    if is_words:
        b = collections.Counter()
        a = collections.Counter()
        for w in pats_or_words:
            b[w] = before.count(w)
            a[w] = after.count(w)
    else:
        b = count_units([before], pats_or_words)
        a = count_units([after], pats_or_words)
    lost = b - a
    gained = a - b
    return {"label": label, "before": sum(b.values()), "after": sum(a.values()),
            "lost": sorted(lost.elements()), "gained": sorted(gained.elements()),
            "status": Ok if not lost and not gained else Bad}


def heading_skeleton(text):
    rows = scan.classify(text)
    seq = []
    for _ln, kind, raw in rows:
        if kind == scan.KIND_HEADING:
            m = re.match(r"^(#{1,6})\s", raw)
            seq.append(len(m.group(1)) if m else -1)   # -1 = 加粗小标题
    return seq


def structure_report(before, after):
    b_rows = scan.classify(before)
    a_rows = scan.classify(after)

    def n(rows, kind):
        return sum(1 for _, k, _ in rows if k == kind)

    items = [
        ("标题层级序列", heading_skeleton(before), heading_skeleton(after)),
        ("代码块行数", n(b_rows, scan.KIND_FENCE), n(a_rows, scan.KIND_FENCE)),
        ("表格行数", n(b_rows, scan.KIND_TABLE), n(a_rows, scan.KIND_TABLE)),
        ("引用行数", n(b_rows, scan.KIND_QUOTE), n(a_rows, scan.KIND_QUOTE)),
        ("列表行数", n(b_rows, scan.KIND_LIST), n(a_rows, scan.KIND_LIST)),
        ("正文行数", n(b_rows, scan.KIND_BODY), n(a_rows, scan.KIND_BODY)),
        ("段落数", len(scan.build_paragraphs(b_rows)), len(scan.build_paragraphs(a_rows))),
    ]
    out = []
    for label, b, a in items:
        same = b == a
        out.append({"label": label, "before": b, "after": a,
                    "status": Ok if same else Bad,
                    "detail": "" if same else f"{b} → {a}"})
    return out


def out_of_scope(before, after, hits):
    """字符级越界检测：每处改动都必须落在一个「有命中的句子」里。

    粒度是句子而不是行——同一行里常常有两三句话，按行判的话，
    顺手把没命中的那句润色一遍也能过。改成按句判之后，
    改写一句话可以（那句话里有规则命中），润色另一句话不行。

    返回 (违规清单, 改动处数, 有据可查的改动处数)
    """
    sents = scan.sentence_spans(before)
    allowed = [False] * len(sents)
    for h in hits:
        l, r = h.get("span_left", 0), h.get("span_right", 0)
        for i, (s, e) in enumerate(sents):
            if l < e and r > s:
                allowed[i] = True

    def allowed_region(i1, i2):
        """[i1, i2) 是否算「有据可查」。

        两条通过路径：
          1. 整段落在某个有命中的句子里；
          2. 与某个有命中的句子有交集，且落在它外面的部分只是标点或空白。
        第 2 条是为了放过「。这意味着 → ，」这类跨句界的合并——句号归属上一句，
        但这次改动的实质内容全在那个有命中的句子里。
        """
        if i2 <= i1:
            i2 = i1 + 1
        for i, (s, e) in enumerate(sents):
            if not allowed[i]:
                continue
            lo, hi = max(i1, s), min(i2, e)
            if lo >= hi:
                continue
            rest = before[i1:lo] + before[hi:i2]
            if all(ch in PUNCT_ONLY for ch in rest):
                return True
        return False

    sm = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    illegal, n_changed, n_ok = [], 0, 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        frag_b, frag_a = before[i1:i2], after[j1:j2]
        # 纯空白的变化（段落合并／空行）另算：它改的是结构，交给结构守恒去报
        if frag_b.strip() == "" and frag_a.strip() == "":
            continue
        n_changed += 1
        if allowed_region(i1, i2 if i2 > i1 else i1 + 1):
            n_ok += 1
            continue
        line = before.count("\n", 0, i1) + 1
        illegal.append({"line": line, "before": frag_b, "after": frag_a, "kind": tag})
    return illegal, n_changed, n_ok


def residual(after, before_ids):
    hits = scan.evaluate(after)
    by_rule = collections.Counter(h["rule_id"] for h in hits)
    return hits, by_rule


def main(argv=None):
    ap = argparse.ArgumentParser(description="晓得·凡人腔调 —— 改写门禁（只读）")
    ap.add_argument("--before", required=True, help="原稿")
    ap.add_argument("--after", required=True, help="改后稿")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--allow-residual", action="store_true",
                    help="允许改后仍有命中（只标注不判违规）")
    args = ap.parse_args(argv)

    for p in (args.before, args.after):
        if not os.path.exists(p):
            print(f"找不到文件：{p}")
            return 2

    before = io.open(args.before, encoding="utf-8").read()
    after = io.open(args.after, encoding="utf-8").read()

    before_hits = scan.evaluate(before)
    hit_lines = {h["line"] for h in before_hits}

    # ---- 1 硬守恒 ----
    hard = [
        diff_counter(before, after, "数字（含百分比、中文数字）", [R.NUM_RE]),
        diff_counter(before, after, "引语／书名号／链接／英文串", R.QUOTE_RES),
    ]

    # ---- 2 强度守恒 ----
    hedges = diff_counter(before, after, "限定词与强度词", R.HEDGES, is_words=True)

    # ---- 3 结构守恒 ----
    struct = structure_report(before, after)

    # ---- 4 越界改动 ----
    illegal, n_changed, n_ok = out_of_scope(before, after, before_hits)

    # ---- 5 残留命中 ----
    r_hits, by_rule = residual(after, None)

    bad = []
    bad += [h for h in hard if h["status"] == Bad]
    if hedges["status"] == Bad:
        bad.append(hedges)
    bad += [s for s in struct if s["status"] == Bad]
    if illegal:
        bad.append({"label": "越界改动", "status": Bad})

    if args.json:
        print(json.dumps({
            "before": os.path.abspath(args.before),
            "after": os.path.abspath(args.after),
            "hard": hard, "hedges": hedges, "structure": struct,
            "out_of_scope": illegal, "changed_lines": n_changed,
            "hit_lines": sorted(hit_lines),
            "residual": by_rule,
            "verdict": "fail" if bad else "pass",
        }, ensure_ascii=False, indent=2))
        return 1 if bad else 0

    W = 76
    print(f"门禁检查")
    print(f"  原稿  {args.before}")
    print(f"  改后  {args.after}")
    print(f"  原稿命中 {len(before_hits)} 处，涉及 {len(hit_lines)} 行")
    print("=" * W)

    print("\n[1] 硬守恒 —— 数字、引语、书名号、链接、英文串，一个都不能增删")
    for h in hard:
        flag = "✓" if h["status"] == Ok else "✗"
        print(f"  {flag} {h['label']:<24} 原 {h['before']:>3}  改 {h['after']:>3}")
        if h["lost"]:
            print(f"        丢失：{'、'.join(h['lost'][:8])}")
        if h["gained"]:
            print(f"        新增：{'、'.join(h['gained'][:8])}")

    print("\n[2] 强度守恒 —— 把「可能提升」写成「提升」是篡改判断强度，不是去腔调")
    flag = "✓" if hedges["status"] == Ok else "✗"
    print(f"  {flag} {hedges['label']:<24} 原 {hedges['before']:>3}  改 {hedges['after']:>3}")
    if hedges["lost"]:
        print(f"        丢失：{'、'.join(hedges['lost'][:8])}")
    if hedges["gained"]:
        print(f"        新增：{'、'.join(hedges['gained'][:8])}")

    print("\n[3] 结构守恒 —— 标题层级、段落、代码块、表格、引用、列表，位置和数量都不动")
    for s in struct:
        flag = "✓" if s["status"] == Ok else "✗"
        detail = f"  {s['detail']}" if s["detail"] else ""
        print(f"  {flag} {s['label']:<24}{detail}")

    print(f"\n[4] 越界改动 —— 每处改动都必须落在有规则命中的句子里"
          f"（改动 {n_changed} 处，其中 {n_ok} 处有据可查）")
    if not illegal:
        print(f"  ✓ 没有越界改动")
    else:
        for it in illegal[:12]:
            print(f"  ✗ 行 {it['line']} 的改动指不出对应规则（{it['kind']}）")
            if it["before"]:
                print(f"        原：{it['before'][:70]}")
            print(f"        改：{it['after'][:70]}")
        if len(illegal) > 12:
            print(f"        …另有 {len(illegal) - 12} 处")

    print(f"\n[5] 残留命中 —— 改完还剩多少（不判违规，交人决定）")
    if not r_hits:
        print("  ✓ 已归零")
    else:
        for rid, c in sorted(by_rule.items()):
            rule = R.by_id(rid)
            print(f"  · {rid} {rule['name']}（{rule['priority']}·"
                  f"{R.EVIDENCE_LABEL.get(rule['evidence'], rule['evidence'])}）{c} 处")

    print("\n" + "=" * W)
    if bad:
        print("结论：✗ 未通过门禁。")
        print()
        print("修法：越界改动一律撤销，恢复原文；硬守恒丢失的元素补回；")
        print("      结构变化说明改了框架，回滚后重来。改完再跑一次 guard.py。")
        return 1
    print("结论：✓ 通过门禁。")
    if r_hits and not args.allow_residual:
        print(f"      仍有 {len(r_hits)} 处命中（见第 5 节）。若这些属于「不改的情况」，"
              f"在交付说明里写清理由；否则继续改。")
    print("      可以交付。记住把变更清单和本次门禁结论一并给出。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
