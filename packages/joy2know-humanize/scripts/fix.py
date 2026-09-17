#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""晓得·凡人腔调 —— 机械替换（唯一会写盘的脚本）。

    python3 fix.py 原稿.md --out 改后.md           干跑，只打印会改什么
    python3 fix.py 原稿.md --out 改后.md --write   真的写出改后稿

只处理规则表里 `fix` 非空、且**定义域是纯模式的**那几条：翻案腔、序数词小标题、
起手式、「当……时」、复述句、时代背景起手。
它们不需要读懂句意就能改对，所以交给脚本：零 token、零漂移、可回滚。

其余规则（段首零回指要看上下文、破折号要看是揭晓还是插入、拟人喻体要换说法、
相邻句同构要打散句法）一律留给人。脚本替不了那些判断，硬做只会把文章改坏。

三条安全约定
--------------------------------------------------------------
1  默认只干跑，不写盘。必须给 --write 才落文件，且**永不覆盖输入文件**。
2  只改命中行，一次只动解决问题所必需的部分；同一行多条命中按规则表顺序叠加。
3  写完必须跑 guard.py。脚本不会替你确认改动有没有越界。

退出码：0 成功 / 2 用法或读文件出错。
"""

import argparse
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rules as R      # noqa: E402
import scan            # noqa: E402


def apply_fixes(text, only=None):
    """返回 (新文本, 改动清单)。改动清单：[{line, rule_id, rule_name, before, after}]"""
    rule_list = R.all_rules()
    if only:
        want = {x.strip().upper() for x in only}
        rule_list = [r for r in rule_list if r["id"] in want]

    hits = scan.evaluate(text, rule_list)
    by_line = {}
    for h in hits:
        if h["fixable"]:
            by_line.setdefault(h["line"], [])
            if h["rule_id"] not in by_line[h["line"]]:
                by_line[h["line"]].append(h["rule_id"])

    lines = text.split("\n")
    changes = []
    order = {r["id"]: i for i, r in enumerate(rule_list)}

    for lineno, rids in sorted(by_line.items()):
        before = lines[lineno - 1]
        cur = before
        for rid in sorted(rids, key=lambda x: order.get(x, 99)):
            rule = R.by_id(rid)
            for pat, rep in rule.get("fix", []):
                cur = re.sub(pat, rep, cur)
        if cur != before:
            lines[lineno - 1] = cur
            changes.append({"line": lineno, "rule_id": ",".join(rids),
                            "before": before, "after": cur})
    return "\n".join(lines), changes


def main(argv=None):
    ap = argparse.ArgumentParser(description="晓得·凡人腔调 —— 机械替换")
    ap.add_argument("path", help="原稿路径")
    ap.add_argument("--out", help="改后稿路径（--write 时必填）")
    ap.add_argument("--write", action="store_true", help="真的写盘（默认只干跑）")
    ap.add_argument("--rules", help="只跑指定规则，逗号分隔，如 R01,R05")
    args = ap.parse_args(argv)

    if not os.path.exists(args.path):
        print(f"找不到原稿：{args.path}")
        return 2
    if args.write and not args.out:
        print("--write 必须配 --out：本脚本永不原地覆盖原稿。")
        return 2
    if args.write and os.path.abspath(args.out) == os.path.abspath(args.path):
        print("--out 不能与原稿同路径：本脚本永不原地覆盖原稿。")
        return 2

    text = io.open(args.path, encoding="utf-8").read()
    new, changes = apply_fixes(text, args.rules)

    fixable_ids = [r["id"] for r in R.RULES if r.get("fix")]
    print(f"机械替换 · 本版可机械处理的规则：{'、'.join(fixable_ids)}")
    print(f"其余规则需要读懂句意，脚本不动，见 references/rules.md 的「改法」一栏。\n")

    if not changes:
        print("没有可机械替换的命中。")
        if args.write:
            io.open(args.out, "w", encoding="utf-8").write(text)
            print(f"原稿原样写出：{args.out}")
        return 0

    print(f"{'行':>5}  {'规则':<10}{'改前':<48}改后")
    print("-" * 110)
    for c in changes:
        print(f"{c['line']:>5}  {c['rule_id']:<10}{c['before'][:46]:<48}{c['after'][:46]}")

    print(f"\n共 {len(changes)} 行、{sum(1 for c in changes)} 处机械替换。")

    if not args.write:
        print("\n（干跑，未写盘。确认无误后加 --write --out <路径> 落文件。）")
        return 0

    io.open(args.out, "w", encoding="utf-8").write(new)
    print(f"\n已写出：{args.out}")
    print("\n下一步必须跑门禁：")
    print(f"    python3 scripts/guard.py --before {args.path} --after {args.out}")
    print("机械替换不会替你确认改动有没有越界——守恒与越界那两道检查只有门禁会做。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
