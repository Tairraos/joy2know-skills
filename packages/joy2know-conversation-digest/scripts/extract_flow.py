#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
晓得·对话归纳 —— WorkBuddy 会话流水提取器

只读本机 WorkBuddy 的会话记录，还原成「提示词 → 回答 → 产物文件」三段式流水。
不写入 ~/.workbuddy 下的任何文件；不连接网络。

用法
----
    # 1) 列出本机所有空间及其中的对话（先跑这个）
    python3 extract_flow.py --list

    # 2) 按空间路径提取（推荐；会自动映射到对应 project 目录）
    python3 extract_flow.py --workspace "/Users/you/Desktop/myproj" --out /tmp/flow

    # 3) 直接按 project 目录提取
    python3 extract_flow.py --project ~/.workbuddy/projects/Users-you-Desktop-myproj

    # 4) 只提取其中几个对话 / 取消回答截断
    python3 extract_flow.py --workspace "..." --sessions a1b2c3,d4e5f6
    python3 extract_flow.py --workspace "..." --preview 0

产出（写到 --out 目录，默认 /tmp/flow）
--------------------------------------
    manifest.json  结构化总数据（空间 / 对话 / 时间 / 计数 / 产物清单）
    users.md       每个对话的全部提问（已剥 <user_query> 壳、已去重）
    answers.md     每个对话的回答 block（默认截断 600 字预览）
    products.txt   每个对话的写文件清单（保序 + 次数 + 操作类型）
"""

import argparse
import collections
import datetime
import glob
import json
import os
import re
import sys

PROJECTS_DIR = os.path.expanduser("~/.workbuddy/projects")
WORKSPACE_NAMES = os.path.expanduser("~/.workbuddy/workspace-display-names.json")

WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "CreateFile")
AUX_PROMPTS = ("请继续执行任务", "继续执行任务", "继续", "continue")


# ---------------------------------------------------------------- 基础解析

def strip_user_context(text):
    """剥掉 system-reminder 等上下文注入，只留 <user_query> 里的真实提问。"""
    m = re.search(r"<user_query>(.*?)</user_query>", text, re.S)
    if m:
        return m.group(1).strip()
    # 没有 user_query 标签时，退化为删掉已知的注入块
    t = re.sub(r"<system-reminder.*?</system-reminder>", "", text, flags=re.S)
    t = re.sub(r"<ide_opened_file.*?</ide_opened_file>", "", t, flags=re.S)
    t = re.sub(r"<identity_context.*?</identity_context>", "", t, flags=re.S)
    t = re.sub(r"<memory.*?</memory>", "", t, flags=re.S)
    return t.strip()


def norm_prompt(text):
    """归一化用于去重：抹掉空白差异。"""
    return re.sub(r"\s+", " ", text).strip()


def is_aux_prompt(text):
    return norm_prompt(text) in AUX_PROMPTS


def iter_records(path):
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def load_workspace_names():
    if not os.path.exists(WORKSPACE_NAMES):
        return {}
    try:
        return json.load(open(WORKSPACE_NAMES, encoding="utf-8")).get("workspaces", {}) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def project_dirs_for_workspace(ws_path):
    """空间路径 → project 目录。前缀相同的目录都算（同一空间可能分散在多处）。"""
    ws_path = os.path.abspath(os.path.expanduser(ws_path)).rstrip("/")
    dashes = ws_path.replace("/", "-").lstrip("-")
    if not os.path.isdir(PROJECTS_DIR):
        return []
    hits = []
    for d in sorted(os.listdir(PROJECTS_DIR)):
        full = os.path.join(PROJECTS_DIR, d)
        if not os.path.isdir(full):
            continue
        if d == dashes or d.startswith(dashes + "-"):
            hits.append(full)
    return hits


def extract(path, preview=600):
    users, answers, products = [], [], []
    for d in iter_records(path):
        ty = d.get("type")

        if ty == "message":
            role = d.get("role")
            if role == "user":
                raw = "".join(
                    c.get("text", "")
                    for c in (d.get("content") or [])
                    if isinstance(c, dict) and c.get("type") == "input_text"
                )
                q = strip_user_context(raw)
                if q:
                    users.append((d.get("timestamp", 0), q))
            elif role == "assistant":
                txt = "".join(
                    c.get("text", "")
                    for c in (d.get("content") or [])
                    if isinstance(c, dict) and c.get("type") in ("output_text", "text")
                )
                if txt.strip():
                    answers.append((d.get("timestamp", 0), txt.strip()))

        # ★ 工具调用是 function_call，不是 tool_call
        elif ty == "function_call":
            if d.get("name") in WRITE_TOOLS:
                try:
                    args = json.loads(d.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                p = args.get("file_path") or args.get("path") or ""
                if p:
                    products.append((d.get("timestamp", 0), d.get("name"), p))

    # 提问去重（同一 prompt 会因上下文重注入出现多次）
    seen, dedup = set(), []
    for ts, q in users:
        k = norm_prompt(q)
        if k in seen:
            continue
        seen.add(k)
        dedup.append((ts, q))

    effective = [(ts, q) for ts, q in dedup if not is_aux_prompt(q)]

    # 产物保序去重
    prod_order, prod_count, prod_ops = collections.OrderedDict(), collections.Counter(), {}
    for _, name, p in products:
        prod_order.setdefault(p, None)
        prod_count[p] += 1
        prod_ops.setdefault(p, set()).add(name)

    return {
        "users": dedup,
        "effective": effective,
        "answers": answers,
        "products": [
            {"path": p, "calls": prod_count[p], "ops": sorted(prod_ops[p])}
            for p in prod_order
        ],
        "raw_user_count": len(users),
        "dedup_user_count": len(dedup),
        "effective_user_count": len(effective),
        "answer_blocks": len(answers),
        "write_calls": len(products),
    }


def fmt_time(ms):
    if not ms:
        return "?"
    return datetime.datetime.fromtimestamp(ms / 1000).strftime("%m-%d %H:%M:%S")


def fmt_full(ms):
    if not ms:
        return "?"
    return datetime.datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


def scan_range(path):
    ts = [d["timestamp"] for d in iter_records(path) if d.get("timestamp")]
    if not ts:
        return 0, 0
    return min(ts), max(ts)


def session_cwd(path):
    for d in iter_records(path):
        if d.get("cwd"):
            return d["cwd"]
    return None


# ---------------------------------------------------------------- --list

def cmd_list():
    if not os.path.isdir(PROJECTS_DIR):
        sys.exit("找不到 %s —— 本机似乎没有 WorkBuddy 会话记录。" % PROJECTS_DIR)

    names = load_workspace_names()
    by_cwd = collections.defaultdict(list)

    for d in sorted(os.listdir(PROJECTS_DIR)):
        full = os.path.join(PROJECTS_DIR, d)
        if not os.path.isdir(full):
            continue
        for f in sorted(glob.glob(os.path.join(full, "*.jsonl"))):
            if not os.path.isfile(f):
                continue
            sid = os.path.basename(f).split(".")[0]
            cwd = session_cwd(f) or "（记录中无 cwd 字段）"
            lo, hi = scan_range(f)
            r = extract(f, preview=0)
            by_cwd[cwd].append({
                "id": sid,
                "project_dir": full,
                "start": fmt_full(lo),
                "end": fmt_full(hi),
                "prompts": r["effective_user_count"],
                "products": len(r["products"]),
                "size_kb": round(os.path.getsize(f) / 1024),
            })

    if not by_cwd:
        sys.exit("在 %s 下没找到任何 .jsonl 会话记录。" % PROJECTS_DIR)

    print("本机 WorkBuddy 空间共 %d 个，对话 %d 个\n" % (
        len(by_cwd), sum(len(v) for v in by_cwd.values())))

    for cwd, items in sorted(by_cwd.items(), key=lambda kv: -max(i["size_kb"] for i in kv[1])):
        disp = names.get(cwd, {}).get("displayName") or "（无显示名）"
        print("=" * 78)
        print("空间：%s" % disp)
        print("路径：%s" % cwd)
        print("-" * 78)
        for it in sorted(items, key=lambda x: x["start"]):
            print("  %s  %s → %s  提问%3d  产物%3d  %6dKB" % (
                it["id"][:8], it["start"][5:16], it["end"][5:16],
                it["prompts"], it["products"], it["size_kb"]))
        print()


# ---------------------------------------------------------------- 主流程

def resolve_project(args):
    if args.project:
        p = os.path.expanduser(args.project)
        if not os.path.isdir(p):
            sys.exit("目录不存在：%s" % p)
        return [p]

    if args.workspace:
        hits = project_dirs_for_workspace(args.workspace)
        if not hits:
            sys.exit(
                "找不到与空间对应的会话目录：%s\n"
                "先跑 `--list` 看看本机到底有哪些空间。" % args.workspace
            )
        if len(hits) > 1:
            print("注意：该空间对应 %d 个会话目录，将合并处理：" % len(hits))
            for h in hits:
                print("   ", h)
        return hits

    sys.exit("请给 --workspace <空间路径> 或 --project <目录>，或用 --list 先看有哪些空间。")


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--list", action="store_true", help="列出本机所有空间与其中的对话")
    ap.add_argument("--workspace", default="", help="空间绝对路径（推荐）")
    ap.add_argument("--project", default="", help="~/.workbuddy/projects/<...> 目录")
    ap.add_argument("--out", default="/tmp/flow", help="输出目录（默认 /tmp/flow）")
    ap.add_argument("--sessions", default="", help="逗号分隔的 sessionUuid 前缀；留空=全部")
    ap.add_argument("--preview", type=int, default=600,
                    help="回答预览截断长度；0 = 不截断（默认 600）")
    args = ap.parse_args()

    if args.list:
        cmd_list()
        return

    proj_dirs = resolve_project(args)

    files = []
    for p in proj_dirs:
        files.extend(sorted(f for f in glob.glob(os.path.join(p, "*.jsonl")) if os.path.isfile(f)))
    if args.sessions:
        wants = [s.strip() for s in args.sessions.split(",") if s.strip()]
        files = [f for f in files if any(os.path.basename(f).startswith(w) for w in wants)]
    if not files:
        sys.exit("未找到 .jsonl 文件（空间指到了但目录里没有会话记录）。")

    # 按首条时间戳升序
    files.sort(key=lambda f: scan_range(f)[0])

    os.makedirs(args.out, exist_ok=True)
    users_out, ans_out, prod_out = [], [], []

    # 空间显示名
    names = load_workspace_names()
    cwd = session_cwd(files[0]) or ""
    disp = names.get(cwd, {}).get("displayName") if cwd else None
    if disp:
        print("空间显示名：%s  (%s)" % (disp, cwd))

    manifest = {
        "workspace_path": cwd,
        "workspace_display_name": disp,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "project_dirs": proj_dirs,
        "session_count": len(files),
        "sessions": [],
    }
    totals = collections.Counter()

    for i, fp in enumerate(files, 1):
        sid = os.path.basename(fp).split(".")[0]
        r = extract(fp, args.preview)
        lo, hi = scan_range(fp)
        head = (
            "\n\n" + "=" * 78
            + "\n对话 %d · %s\n时间 %s → %s\n"
              "提问 %d 条（原始 %d，去重 %d）｜回答 block %d｜写文件调用 %d\n"
            % (i, sid, fmt_full(lo), fmt_full(hi),
               r["effective_user_count"], r["raw_user_count"], r["dedup_user_count"],
               r["answer_blocks"], r["write_calls"])
            + "=" * 78 + "\n"
        )
        users_out.append(head)
        ans_out.append(head)
        prod_out.append(head)

        for ts, q in r["users"]:
            users_out.append("\n--- [%s] ---\n%s\n" % (fmt_time(ts), q))

        for ts, t in r["answers"]:
            if args.preview and len(t) > args.preview:
                body = t[:args.preview] + " …"
            else:
                body = t
            ans_out.append("\n--- [%s] len=%d ---\n%s\n" % (fmt_time(ts), len(t), body))

        for p in r["products"]:
            prod_out.append("  [%3dx %-9s] %s\n" % (p["calls"], "+".join(p["ops"]), p["path"]))
        if not r["products"]:
            prod_out.append("  （本对话无写文件记录）\n")

        manifest["sessions"].append({
            "index": i,
            "id": sid,
            "file": fp,
            "start": fmt_full(lo),
            "end": fmt_full(hi),
            "raw_user_count": r["raw_user_count"],
            "dedup_user_count": r["dedup_user_count"],
            "effective_user_count": r["effective_user_count"],
            "answer_blocks": r["answer_blocks"],
            "write_calls": r["write_calls"],
            "products": r["products"],
        })
        totals["raw_user_count"] += r["raw_user_count"]
        totals["dedup_user_count"] += r["dedup_user_count"]
        totals["effective_user_count"] += r["effective_user_count"]
        totals["products"] += len(r["products"])

    manifest["totals"] = dict(totals)

    for name, buf in (("users.md", users_out), ("answers.md", ans_out), ("products.txt", prod_out)):
        with open(os.path.join(args.out, name), "w", encoding="utf-8") as fh:
            fh.write("".join(buf))
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    print("对话 %d 个｜实质提问 %d 条｜唯一产物 %d 个"
          % (len(files), totals["effective_user_count"], totals["products"]))
    print("已输出到：%s" % args.out)


if __name__ == "__main__":
    main()
