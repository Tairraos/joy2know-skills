#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""晓得·凡人腔调 —— 规则表自检（只读，不碰稿件）。

    python3 selftest.py           全量自检
    python3 selftest.py -v        连每条通过项一起打印

它检查的是**规则表自己**，不是你的稿子：
  1. 字段齐不齐、取值合不合法
  2. 每条触发标记能不能编译
  3. 每条的正例**必须被命中**
  4. 每条的反例**必须不被命中**

第 3、4 条是关键。公开的同类规则集里，算子与规则名之间的覆盖范围总会错开一点，
而频率数字本身不提示这件事——写规则的人看的是名字，跑算子的是正则，两者对不上
要到改完稿才发现。这里把「正例必中、反例不中」变成可执行的门槛：规则写错，
selftest 立刻红，改稿前就拦下。
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rules as R      # noqa: E402
import scan            # noqa: E402

PRIORITIES = {"P0", "P1", "P2"}
EVIDENCES = {"strong", "medium", "weak", "reversed", "disputed", "inferred", "measured"}
SCOPES = {"inline", "paragraph", "heading", "before-list", "sentence-signature"}
REQUIRED = ["id", "name", "priority", "evidence", "scope", "why", "how",
            "keep", "examples", "guards"]

LIST_SUFFIX = "\n- 甲\n- 乙\n"


def prep(rule, s):
    """给作用域补上必需的上下文，让单行样本能走到判定那一步。"""
    if rule.get("scope") == "before-list":
        return s + LIST_SUFFIX
    return s


def run(verbose=False):
    oks, fails, notes = [], [], []

    print(f"规则表版本 {R.VERSION} · 适用范围 {R.SCOPE} · 规则 {len(R.RULES)} 条 · "
          f"不可改清单 {len(R.NOT_RULES)} 条\n")

    # ---- 结构检查 ----
    seen = set()
    for r in R.RULES:
        rid = r.get("id", "?")
        if rid in seen:
            fails.append(f"{rid} 规则号重复")
        seen.add(rid)
        for f in REQUIRED:
            if f not in r:
                fails.append(f"{rid} 缺字段 {f}")
        if r.get("priority") not in PRIORITIES:
            fails.append(f"{rid} priority 取值非法：{r.get('priority')}")
        if r.get("evidence") not in EVIDENCES:
            fails.append(f"{rid} evidence 取值非法：{r.get('evidence')}")
        if r.get("scope") not in SCOPES:
            fails.append(f"{rid} scope 取值非法：{r.get('scope')}")
        if not r.get("keep"):
            fails.append(f"{rid} 没有写「不改的情况」——规则四件套缺一件")
        if not r.get("examples"):
            fails.append(f"{rid} 没有正反例")
        if not r.get("guards"):
            fails.append(f"{rid} 没有反例（无法验证算子没写宽）")
        if not r.get("triggers") and r.get("scope") != "sentence-signature":
            fails.append(f"{rid} 既没有 triggers，scope 也不是 sentence-signature")

    # ---- 正则编译 ----
    for r in R.RULES:
        for pat in r.get("triggers", []):
            try:
                re.compile(pat)
            except re.error as e:
                fails.append(f"{r['id']} 触发标记无法编译：{pat} → {e}")
        if r.get("veto"):
            try:
                re.compile(r["veto"])
            except re.error as e:
                fails.append(f"{r['id']} 否决标记无法编译：{e}")
        for pat, rep in r.get("fix", []):
            try:
                re.compile(pat)
            except re.error as e:
                fails.append(f"{r['id']} 机械替换无法编译：{pat} → {e}")
            if not isinstance(rep, str):
                fails.append(f"{r['id']} 机械替换的目标不是字符串：{rep!r}")

    # ---- 正例必中 ----
    for r in R.RULES:
        for i, ex in enumerate(r.get("examples", []), 1):
            doc = prep(r, ex["bad"])
            hits = scan.evaluate(doc, [r], apply_min_hits=False)
            if hits:
                oks.append(f"{r['id']} 正例 {i} 命中 ✓")
            else:
                fails.append(f"{r['id']} 正例 {i} **没有被命中**：{ex['bad'][:40]}")

    # ---- 反例必不中 ----
    for r in R.RULES:
        for i, g in enumerate(r.get("guards", []), 1):
            doc = prep(r, g)
            hits = scan.evaluate(doc, [r], apply_min_hits=False)
            if not hits:
                oks.append(f"{r['id']} 反例 {i} 未命中 ✓")
            else:
                fails.append(f"{r['id']} 反例 {i} **被误命中**：{g[:40]}")

    # ---- 结构一致性 ----
    for r in R.RULES:
        for pat, _rep in r.get("fix", []):
            if r.get("scope") == "sentence-signature":
                fails.append(f"{r['id']} 句法指纹规则不应带机械替换")

    # ---- 不可改清单 ----
    for n in R.NOT_RULES:
        if n.get("evidence") not in EVIDENCES:
            fails.append(f"不可改清单「{n['name']}」evidence 取值非法：{n.get('evidence')}")
        if not n.get("why"):
            fails.append(f"不可改清单「{n['name']}」没有写原因")
    oks.append(f"不可改清单 {len(R.NOT_RULES)} 条字段齐全 ✓")

    # ---- 输出 ----
    if verbose:
        for o in oks:
            print(f"  [OK] {o}")
        print()

    n_pos = sum(len(r.get("examples", [])) for r in R.RULES)
    n_neg = sum(len(r.get("guards", [])) for r in R.RULES)
    print(f"用例：正例 {n_pos} 条 / 反例 {n_neg} 条")
    print(f"通过 {len(oks)} 项，失败 {len(fails)} 项")
    if notes:
        for n in notes:
            print(f"  [!!] {n}")
    if fails:
        print()
        for f in fails:
            print(f"  [XX] {f}")
        print(f"\n规则表未通过：{len(fails)} 项需要修。")
        return 1
    print("\n=== 规则表自检通过：正例全中、反例全不中 ===")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    return run(a.verbose)


if __name__ == "__main__":
    sys.exit(main())
