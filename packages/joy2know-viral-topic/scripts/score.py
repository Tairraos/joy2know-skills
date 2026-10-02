#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""晓得·选题炼法 —— 选题打分器

用法
------------------------------------------------------------------
    python3 scripts/score.py --dims 5,4,4,5,3,5,4,4
    python3 scripts/score.py --dims 5,4,3,5,2,5,4,4 --redlines 0 --genes 3
    python3 scripts/score.py --file 候选.json            # 批量
    python3 scripts/score.py --file 候选.json --json     # 机器可读

为什么要有脚本
------------------------------------------------------------------
打分卡只要靠口算，就会漂：同一个分数，心情好时给 4、心情差时给 3；
更常见的是「先定这条要做，再倒着凑分数」。把阈值与告警写进脚本之后，
**判定不随心情变** —— 觉得判定不对，改的是各维输入分（并说明理由），不是总分。

阈值与告警规则都硬编码在本文件顶部。改阈值 = 改判据，属于改技能，
请连 `selftest.py` 的边界用例一起改（它会守住每一条边界）。

退出码
------------------------------------------------------------------
    0  判定为可做（总分 ≥ 30 且无阻断）
    1  判定为不可做（总分 < 30，或红线命中 / 基因命中不足）
    2  用法或输入有错
"""

import argparse
import json
import sys

DIM_NAMES = ["①情绪强度", "②传播动机", "③角度独家性", "④人群匹配",
             "⑤时效性", "⑥卖点承载", "⑦形态可行性", "⑧转化承接"]
N_DIMS = len(DIM_NAMES)

# ★ ⑥ 与 ⑧ 的下标 —— 推广选题与流量选题的分界线
PROMO_IDX = (5, 7)

# ★ 阈值表：从高到低，取第一个 total >= 下限的档
STRATA = [
    (35, "重点做", "配最好的人力与预算"),
    (30, "合格", "建议做 2 个变体 A/B"),
    (24, "边缘", "说清缺哪条，补得上就做"),
    (0, "淘汰", "不要因为「想凑够 10 条」而留下"),
]

PROMO_PREF = 4      # ①–⑤ 全部 ≥ 此值，且 ⑥⑧ 有短板 → 流量选题告警
PROMO_MIN = 3       # ⑥ 或 ⑧ 低于此值 → 单维告警
GENES_MIN = 2       # 基因最少命中数（低于此值算阻断）
VARIANCE_MIN = 2    # 八维极差小于此值 → 打分可能没有区分度


def stratum(total):
    for floor, label, advice in STRATA:
        if total >= floor:
            return label, advice
    return STRATA[-1][1], STRATA[-1][2]


def evaluate(dims, redlines=0, genes=None, name=None):
    """核心判定。返回 dict，供文本与 JSON 两种输出共用。

    blocking —— 阻断项（有则判定为不可做，退出码 1）
    warns    —— 提示项（不改变判定，但必须报出声）
    """
    if len(dims) != N_DIMS:
        raise ValueError("需要 %d 个维度分，收到 %d 个" % (N_DIMS, len(dims)))
    for i, d in enumerate(dims, 1):
        if not isinstance(d, int) or not 1 <= d <= 5:
            raise ValueError("第 %d 维分数必须是 1–5 的整数，收到 %r" % (i, d))

    total = sum(dims)
    label, advice = stratum(total)
    blocking, warns = [], []

    # —— 阻断项：与分数无关的门 ——
    if redlines >= 1:
        blocking.append("红线命中 %d 条 → 淘汰该方向（与分数无关）" % redlines)
    if genes is not None:
        if genes <= 0:
            blocking.append("传播基因命中 0 条 → 砍掉，不论它多热点")
        elif genes < GENES_MIN:
            blocking.append("传播基因仅命中 %d 条（要求 ≥ %d 条）" % (genes, GENES_MIN))
    if total < 30 and not blocking:
        blocking.append("总分 %d < 30，判定为「%s」" % (total, label))

    # —— ⑥⑧ 两维：推广选题的命门 ——
    for idx, why in ((5, "这条内容与产品的关系立不住"), (7, "看完没有出口")):
        if dims[idx] < PROMO_MIN:
            warns.append("%s %d 分（< %d）：%s" % (DIM_NAMES[idx], dims[idx], PROMO_MIN, why))

    lead_high = all(d >= PROMO_PREF for d in dims[:5])
    promo_weak = any(dims[i] < PROMO_MIN for i in PROMO_IDX)
    if lead_high and promo_weak:
        warns.append(
            "⚠️ 流量选题告警：①–⑤ 均 ≥%d，而 %s 低于 %d —— "
            "它会爆，但人留不下来。要么补 ⑧（给一个与内容同构的动作），"
            "要么补 ⑥（让卖点变成内容本身）"
            % (PROMO_PREF,
               "、".join(DIM_NAMES[i] for i in PROMO_IDX if dims[i] < PROMO_MIN),
               PROMO_MIN))

    # —— 打分区分度 ——
    if max(dims) - min(dims) < VARIANCE_MIN:
        warns.append("八维极差仅 %d，分数分布过于集中 —— 打分可能没有区分度，回炉重打"
                     % (max(dims) - min(dims)))

    return {
        "name": name,
        "dims": list(dims),
        "total": total,
        "max": N_DIMS * 5,
        "stratum": label,
        "advice": advice,
        "redlines": redlines,
        "genes": genes,
        "blocking": blocking,
        "warns": warns,
        "verdict": "可做" if not blocking else "不可做",
    }


def render(res):
    L = []
    head = res["name"] + " —— " if res["name"] else ""
    L.append("%s总分 %d/%d  →  %s（%s）"
             % (head, res["total"], res["max"], res["stratum"], res["advice"]))
    L.append("  " + "  ".join("%s %d" % (n, d) for n, d in zip(DIM_NAMES, res["dims"])))
    if res["redlines"]:
        L.append("  红线命中：%d 条" % res["redlines"])
    if res["genes"] is not None:
        tag = ("重点投入级" if res["genes"] >= 3
               else "达标" if res["genes"] >= GENES_MIN
               else "不足")
        L.append("  基因命中：%d 条（%s）" % (res["genes"], tag))
    for b in res["blocking"]:
        L.append("  ⛔ " + b)
    for w in res["warns"]:
        L.append("  " + ("" if w.startswith("⚠️") else "⚠️ ") + w)
    L.append("  → 判定：%s" % res["verdict"])
    return "\n".join(L)


def parse_dims(s):
    try:
        return [int(x) for x in s.replace("，", ",").split(",") if x.strip() != ""]
    except ValueError:
        raise ValueError("--dims 只接受逗号分隔的整数，收到 %r" % s)


def load_file(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("picks") if isinstance(data, dict) else data
    if not isinstance(items, list) or not items:
        raise ValueError("文件里没有 picks 数组，或数组为空")
    out = []
    for i, it in enumerate(items, 1):
        if not isinstance(it, dict) or "dims" not in it:
            raise ValueError("第 %d 条缺少 dims 字段" % i)
        out.append(evaluate(it["dims"],
                            int(it.get("redlines", 0)),
                            it.get("genes"),
                            it.get("name") or "第 %d 条" % i))
    return out


def main():
    ap = argparse.ArgumentParser(description="选题 8 维打分器（阈值与告警硬编码在脚本内）")
    ap.add_argument("--dims", help="8 个维度分，逗号分隔，如 5,4,4,5,3,5,4,4")
    ap.add_argument("--file", help="批量输入 JSON：{\"picks\":[{\"name\":..,\"dims\":[..]}]}")
    ap.add_argument("--redlines", type=int, default=0, help="12 条心法里红线命中数（默认 0）")
    ap.add_argument("--genes", type=int, default=None, help="四大传播基因命中数（不填则不判）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    a = ap.parse_args()

    if not a.dims and not a.file:
        ap.print_help()
        return 2
    try:
        results = (load_file(a.file) if a.file
                   else [evaluate(parse_dims(a.dims), a.redlines, a.genes)])
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print("输入有误：%s" % e, file=sys.stderr)
        return 2

    if a.json:
        print(json.dumps(results if len(results) > 1 else results[0],
                         ensure_ascii=False, indent=2))
    else:
        for i, r in enumerate(results):
            if i:
                print()
            print(render(r))

    return 0 if all(r["verdict"] == "可做" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
