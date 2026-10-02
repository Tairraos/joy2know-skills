#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""晓得·选题炼法 —— 打分器自检（只读，不改任何稿件或数据）

    python3 scripts/selftest.py           全量自检
    python3 scripts/selftest.py -v        连每条通过项一起打印

它检查的是**判据本身**，不是你的选题：
  1. 每一档阈值的两侧边界 —— 34 分必须是「合格」、35 分必须是「重点做」
  2. 每条阻断规则的**正例必中、反例不中**（含红线、基因、总分三处门）
  3. ⑥⑧ 告警的正反例 —— 包括「只有 ①–⑤ 高、⑥⑧ 低」这一条流量选题告警
  4. 文档锚点：`references/examples.md` 里三条范例的总分与判定，**必须与脚本算出来的一致**
  5. 输入校验：分数越界、个数不对、非整数，都要报错而不是静默通过

第 4 条是这个自检里最容易被忽略、也最值钱的一条：范例写在文档里、分数算在脚本里，
两者一旦漂移，读文档的人会照着一个错的数去打分卡。所以把它变成可执行的门槛。
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import score as S      # noqa: E402

N = S.N_DIMS


def dims_for(total):
    """构造一个总分恰好等于 total 的 8 维分数向量（每维 1–5）。"""
    d = [1] * N
    left = total - N
    i = 0
    while left > 0:
        add = min(4, left)
        d[i % N] += add
        left -= add
        i += 1
    return d


def has(text, key):
    return key in text


def run(verbose=False):
    oks, fails, notes = [], [], []

    print("选题炼法 v%s · 维度 %d 维 · 满分 %d · 阈值 %s"
          % ("1.0.0", N, N * 5,
             "/".join("%d→%s" % (f, lab) for f, lab, _ in S.STRATA)))
    print("⑥⑧ 下标 %s · 告警门槛 < %d · 基因下限 %d\n"
          % (S.PROMO_IDX, S.PROMO_MIN, S.GENES_MIN))

    # ---- 1) 阈值边界两侧 ----
    BOUNDARY = [(40, "重点做"), (39, "重点做"), (35, "重点做"), (34, "合格"),
                (30, "合格"), (29, "边缘"), (24, "边缘"), (23, "淘汰"), (8, "淘汰")]
    for total, want in BOUNDARY:
        got = S.evaluate(dims_for(total))["stratum"]
        if got == want:
            oks.append("边界 %d 分 → %s ✓" % (total, got))
        else:
            fails.append("边界 %d 分 判成 %s，应为 %s" % (total, got, want))

    # ---- 2) 阻断项：正例必中 / 反例不中 ----
    def block(dims, redlines=0, genes=None):
        return S.evaluate(list(dims), redlines, genes)

    POS = [
        ("红线命中 1 条（其余满分）", dict(dims=[5] * N, redlines=1), "红线命中"),
        ("基因命中 0 条", dict(dims=[5] * N, genes=0), "命中 0 条"),
        ("基因命中 1 条（要求 ≥2）", dict(dims=[5] * N, genes=1), "仅命中 1 条"),
        ("总分低于 30", dict(dims=dims_for(29)), "总分 29 < 30"),
    ]
    for label, kw, key in POS:
        r = block(**kw)
        if any(has(b, key) for b in r["blocking"]) and r["verdict"] == "不可做":
            oks.append("阻断正例命中：%s ✓" % label)
        else:
            fails.append("阻断正例**未被拦下**：%s → blocking=%s" % (label, r["blocking"]))

    NEG = [
        ("红线 0 条", dict(dims=[5] * N, redlines=0), "红线命中"),
        ("基因 2 条（刚好达标）", dict(dims=[5] * N, genes=2), "基因"),
        ("基因 3 条", dict(dims=[5] * N, genes=3), "基因"),
        ("基因未提供（不判）", dict(dims=[5] * N, genes=None), "基因"),
        ("总分刚好 30", dict(dims=dims_for(30)), "总分 30"),
    ]
    for label, kw, key in NEG:
        r = block(**kw)
        if not any(has(b, key) for b in r["blocking"]):
            oks.append("阻断反例未命中：%s ✓" % label)
        else:
            fails.append("阻断反例**被误拦**：%s → %s" % (label, r["blocking"]))

    # ---- 3) ⑥⑧ 告警：正例必中 / 反例不中 ----
    r = S.evaluate([5, 5, 4, 5, 5, 2, 4, 1], genes=4)
    if any(has(w, "流量选题告警") for w in r["warns"]):
        oks.append("流量选题告警正例命中 ✓")
    else:
        fails.append("流量选题告警**未触发**（①–⑤ 全高、⑥⑧ 双低）→ %s" % r["warns"])
    n_promo = sum(1 for w in r["warns"] if w.startswith(S.DIM_NAMES[5][:1])
                  or w.startswith(S.DIM_NAMES[7][:1]))
    if n_promo == 2:
        oks.append("⑥⑧ 单维告警各命中 1 条 ✓")
    else:
        fails.append("⑥⑧ 单维告警应有 2 条，实际 %d 条 → %s" % (n_promo, r["warns"]))

    NEG_WARN = [
        ("①–⑤ 高，⑥⑧ 也都高（35 分范例）",
         [5, 4, 5, 5, 2, 5, 4, 5], "流量选题告警"),
        ("①–⑤ 本身就不高，⑥⑧ 再低也不算「会爆但留不下」",
         [3, 2, 2, 3, 2, 1, 3, 1], "流量选题告警"),
        ("⑥⑧ 都在门槛上（3 分）", [5, 5, 5, 5, 5, 3, 4, 3], "流量选题告警"),
    ]
    for label, dims, key in NEG_WARN:
        r = S.evaluate(list(dims))
        if not any(has(w, key) for w in r["warns"]):
            oks.append("告警反例未命中：%s ✓" % label)
        else:
            fails.append("告警反例**被误报**：%s → %s" % (label, r["warns"]))

    # ---- 4) 区分度告警 ----
    r = S.evaluate([4] * N)
    if any(has(w, "区分度") for w in r["warns"]):
        oks.append("区分度告警正例命中（八维全 4）✓")
    else:
        fails.append("八维全 4 应触发区分度告警")
    r = S.evaluate([5, 3, 5, 3, 5, 3, 5, 3])
    if not any(has(w, "区分度") for w in r["warns"]):
        oks.append("区分度告警反例未命中（极差 2）✓")
    else:
        fails.append("极差 2 不应触发区分度告警 → %s" % r["warns"])

    # ---- 5) 文档锚点：examples.md 里三条范例的分数必须与脚本一致 ----
    DOC_CASES = [
        ("例一 35 分 → 重点做", [5, 4, 5, 5, 2, 5, 4, 5], 3, 35, "重点做", 0),
        # 例二故意**不**给流量告警：①–⑤ 本身就没人看，不构成「会爆但留不下」
        ("例二 18 分 → 淘汰（无流量告警）", [1, 1, 2, 1, 3, 1, 5, 4], None, 18, "淘汰", 0),
        ("例三 31 分 → 合格 + 流量告警", [5, 5, 4, 5, 5, 2, 4, 1], 4, 31, "合格", 1),
    ]
    for label, dims, genes, want_total, want_stratum, want_promo in DOC_CASES:
        r = S.evaluate(list(dims), 0, genes)
        got_promo = 1 if any(has(w, "流量选题告警") for w in r["warns"]) else 0
        if r["total"] != want_total:
            fails.append("文档锚点 «%s»：文档写 %d 分，脚本算 %d 分" % (label, want_total, r["total"]))
        elif r["stratum"] != want_stratum:
            fails.append("文档锚点 «%s»：文档写「%s」，脚本判「%s」"
                         % (label, want_stratum, r["stratum"]))
        elif got_promo != want_promo:
            fails.append("文档锚点 «%s»：文档写流量告警=%d，脚本 %d"
                         % (label, want_promo, got_promo))
        else:
            oks.append("文档锚点一致：%s ✓" % label)

    # ---- 6) 输入校验：以下都**必须报错** ----
    BAD = [
        ("只给 7 个维度分", lambda: S.evaluate([5] * (N - 1))),
        ("某一维给 0 分", lambda: S.evaluate([5] * (N - 1) + [0])),
        ("某一维给 6 分", lambda: S.evaluate([5] * (N - 1) + [6])),
        ("某一维给小数 3.5", lambda: S.evaluate([5] * (N - 1) + [3.5])),
    ]
    for label, fn in BAD:
        try:
            fn()
            fails.append("输入校验**没有拦下**：%s" % label)
        except ValueError:
            oks.append("输入校验拦下：%s ✓" % label)

    # ---- 输出 ----
    if verbose:
        for o in oks:
            print("  [OK] %s" % o)
        print()

    print("用例：阈值边界 %d 条 / 阻断正例 %d 条 / 阻断反例 %d 条 / 告警反例 %d 条 / 输入校验 %d 条"
          % (len(BOUNDARY), len(POS), len(NEG), len(NEG_WARN), len(BAD)))
    print("通过 %d 项，失败 %d 项" % (len(oks), len(fails)))
    if notes:
        for n in notes:
            print("  [!!] %s" % n)
    if fails:
        print()
        for f in fails:
            print("  [XX] %s" % f)
        print("\n判据自检未通过：%d 项需要修。" % len(fails))
        return 1
    print("\n=== 判据自检通过：边界两侧正确、阻断与告警正反例全部符合、文档锚点一致 ===")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    return run(a.verbose)


if __name__ == "__main__":
    sys.exit(main())
