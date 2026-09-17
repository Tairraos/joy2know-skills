#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""log_cluster.py —— 晓得·日志侦探 的日志聚类脚本（零第三方依赖，纯标准库）。

功能：
  1. 流式逐行读取日志（支持 .gz），不把整个文件读进内存。
  2. 用正则把变化变量抽象为 <UUID>/<IP>/<EMAIL>/<PATH>/<HEX>/<TS>/<NUM> 占位符，
     按「模板」聚类，而不是按字符串相似度（否则每行都算不同）。
  3. 输出每类：出现次数、首次/末次时间、时间分布（分钟或小时桶）、示例原文 3 条、
     首次出现的前后各 N 行上下文。
  4. 处理 JSON 日志与多行堆栈：不以时间戳/已知行首模式开头的行视为续行，归并到上一条日志。

设计原则：大文件必须流式；聚类按模板而非字面，才能把「同一类报错」聚到一起。
"""

import argparse
import gzip
import json
import re
import sys
from collections import Counter, defaultdict

# ---------- 行首识别：用于判断「这是一条新日志」还是「上一行的续行」 ----------
MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
# 行首时间戳（ISO / 带括号 / syslog 风格）
TS_HEAD_RE = re.compile(
    r"^\s*("
    r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?"  # ISO
    r"|\[[^\]]*\d{2}:\d{2}:\d{2}[^\]]*\]"                                          # [..time..]
    r"|" + MONTHS + r"\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}"                              # syslog
    r")"
)
# 已知日志级别打头（无时间戳也认作新记录）
LEVEL_HEAD_RE = re.compile(r"^\s*(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|TRACE|NOTICE)\b")
JSON_HEAD_RE = re.compile(r"^\s*[{\[]")  # 可能是 JSON 行

# ---------- 从行首抽取时间（用于排序/分桶） ----------
ISO_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?)")
SYSLOG_RE = re.compile(MONTHS + r"\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}")

# JSON 日志常见字段
TS_KEYS = ("timestamp", "time", "ts", "@timestamp", "date", "datetime", "logged_at")
MSG_KEYS = ("message", "msg", "log", "text", "event", "error", "description")

# ---------- 变量抽象：把变化的量替换成占位符，顺序很重要 ----------
UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                     r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b")
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PATH_RE = re.compile(r"(?:/[\w./-]+|[A-Za-z]:\\[\w\\./-]+)")
HEX_RE = re.compile(r"\b0x[0-9a-fA-F]+\b")
TS_BODY_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\b")
NUM_RE = re.compile(r"\b\d+\b")
# 长十六进制 / 哈希串（>=10 位）视为标识符
HASH_RE = re.compile(r"\b[0-9a-fA-F]{10,}\b")
# 键值对里的值（token=... / request_id=... 等）抽象为 <ID>
TOKEN_VAL_RE = re.compile(
    r"(\b(?:token|api[_-]?key|secret|key|id|request[_-]?id|trace[_-]?id|"
    r"session[_-]?id|nonce|cursor)=)[^\s,&]+", re.IGNORECASE)
# 激进模式专用：长度 >= 8 且同时含字母与数字的独立 token -> <ID>
# 用 8 而非更短，是为了避免把 v2 / 1e3 / 版本号这类正常文案误并。
AGGR_ID_RE = re.compile(
    r"\b(?=[A-Za-z0-9_-]{8,}\b)(?=[A-Za-z0-9_-]*[A-Za-z])"
    r"(?=[A-Za-z0-9_-]*[0-9])[A-Za-z0-9_-]+\b")


def abstract_template(text, aggressive=False):
    """把一行文本抽象成模板：变量 -> 占位符。aggressive=True 时启用更激进的 ID 抽象。"""
    t = UUID_RE.sub("<UUID>", text)
    t = IP_RE.sub("<IP>", t)
    t = EMAIL_RE.sub("<EMAIL>", t)
    t = PATH_RE.sub("<PATH>", t)
    t = HEX_RE.sub("<HEX>", t)
    t = HASH_RE.sub("<ID>", t)
    t = TOKEN_VAL_RE.sub(r"\1<ID>", t)
    if aggressive:
        t = AGGR_ID_RE.sub("<ID>", t)
    t = TS_BODY_RE.sub("<TS>", t)
    t = NUM_RE.sub("<NUM>", t)
    # 压缩多余空白，便于同模板归并
    t = re.sub(r"\s+", " ", t).strip()
    return t


def extract_time(line):
    """从行首抽取 datetime 字符串（ISO 优先，其次 syslog）。失败返回 None。"""
    m = ISO_RE.search(line)
    if m:
        return m.group(1).replace(" ", "T").split(".")[0].replace("Z", "")
    m = SYSLOG_RE.search(line)
    if m:
        return m.group(0)
    return None


def parse_json_line(line):
    """若是 JSON 日志，返回 (timestamp_str, message_str) 或 (None, None)。"""
    s = line.strip()
    if not (s.startswith("{")):
        return None, None
    try:
        obj = json.loads(s)
    except ValueError:
        return None, None
    if not isinstance(obj, dict):
        return None, None
    ts = None
    for k in TS_KEYS:
        if k in obj and obj[k]:
            ts = str(obj[k])
            break
    msg = None
    for k in MSG_KEYS:
        if k in obj and obj[k]:
            msg = str(obj[k])
            break
    if msg is None:
        # 没有 message 字段，退化为整行抽象
        msg = s
    return ts, msg


def open_stream(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return open(path, "r", encoding="utf-8", errors="ignore")


def is_new_record(line):
    if TS_HEAD_RE.match(line) or LEVEL_HEAD_RE.match(line):
        return True
    if JSON_HEAD_RE.match(line):
        # 必须真能解析成 JSON 才算新记录，否则当作续行
        s = line.strip()
        try:
            json.loads(s)
            return True
        except ValueError:
            return False
    return False


def bucket_key(ts_str, bucket):
    if not ts_str:
        return None
    if bucket == "hour":
        return ts_str[:13] if len(ts_str) >= 13 else ts_str
    return ts_str[:16] if len(ts_str) >= 16 else ts_str  # 分钟


def parse_filter(dt_str):
    if not dt_str:
        return None
    # 接受 YYYY-MM-DD 或 YYYY-MM-DDTHH:MM:SS
    return dt_str.replace("T", " ")


def in_range(ts_str, since, until):
    if not ts_str:
        return True  # 无法判定时间的记录默认保留
    if since and ts_str < since:
        return False
    if until and ts_str > until:
        return False
    return True


def stream_clusters(path, top, context, bucket, since, until, aggressive=False):
    """第一遍流式：聚类，并记录每类首现的原始行号。aggressive 控制是否启用激进 ID 抽象。"""
    clusters = defaultdict(lambda: {
        "count": 0, "first": None, "last": None,
        "buckets": Counter(), "examples": [], "first_line": None,
    })
    line_no = 0
    record_open = False  # 当前是否处于一条记录中
    cur_raw_parts = []
    cur_time = None
    cur_template = None
    cur_start_line = None  # 当前记录起始行号（用于上下文定位）

    def flush():
        nonlocal cur_raw_parts, cur_time, cur_template, record_open, cur_start_line
        if not cur_raw_parts:
            record_open = False
            return
        raw = "".join(cur_raw_parts).rstrip("\n")
        tmpl = abstract_template(raw, aggressive)
        c = clusters[tmpl]
        if c["first"] is None:
            c["first"] = cur_time
            c["first_line"] = cur_start_line  # 记录首行，上下文以此为中心
            if len(c["examples"]) < 3:
                c["examples"].append(raw[:300])
        c["count"] += 1
        if cur_time:
            if c["last"] is None or cur_time > c["last"]:
                c["last"] = cur_time
            bk = bucket_key(cur_time, bucket)
            if bk:
                c["buckets"][bk] += 1
        elif c["last"] is None:
            c["last"] = None
        cur_raw_parts = []
        cur_time = None
        cur_template = None
        cur_start_line = None
        record_open = False

    with open_stream(path) as fh:
        for line in fh:
            line_no += 1
            if is_new_record(line):
                flush()  # 上一记录收口
                ts = extract_time(line)
                jts, jmsg = parse_json_line(line)
                if jts:
                    ts = jts
                # 用「抽象后的 message」作为本记录的文本基础
                text = jmsg if jmsg is not None else line
                cur_raw_parts = [text]
                cur_time = ts
                cur_template = None
                cur_start_line = line_no
                record_open = True
            else:
                # 续行（多行堆栈 / 换行消息）：归并到当前记录
                if record_open:
                    cur_raw_parts.append(line)
                else:
                    # 文件开头的孤立续行，当作一条新记录兜底
                    cur_raw_parts = [line]
                    cur_time = extract_time(line)
                    cur_start_line = line_no
                    record_open = True
        flush()

    # 时间过滤（按首现时间）
    if since or until:
        clusters = {k: v for k, v in clusters.items()
                    if in_range(v["first"], since, until) or v["first"] is None}
    return clusters


def collect_context(path, need_lines, context):
    """第二遍流式：只为 top 模板的首现行号收集前后上下文（内存安全）。"""
    ctx_map = {}
    lo = {ln - context for ln in need_lines if ln is not None}
    hi = {ln + context for ln in need_lines if ln is not None}
    min_ln = min(lo) if lo else 1
    max_ln = max(hi) if hi else 1
    line_no = 0
    buf = {}  # 行号 -> 行内容（仅保留窗口附近）
    with open_stream(path) as fh:
        for line in fh:
            line_no += 1
            if line_no < min_ln - 1:
                continue
            if line_no > max_ln + 1:
                break
            buf[line_no] = line.rstrip("\n")
    for ln in need_lines:
        if ln is None:
            continue
        before = [buf.get(i, "") for i in range(max(1, ln - context), ln)]
        after = [buf.get(i, "") for i in range(ln + 1, ln + context + 1)]
        ctx_map[ln] = (before, after)
    return ctx_map


def main(argv=None):
    p = argparse.ArgumentParser(
        description="日志流式聚类：按模板聚合错误模式，输出次数/时间线/上下文")
    p.add_argument("path", help="日志文件路径（支持 .gz）")
    p.add_argument("--top", type=int, default=20, help="输出前 N 类（默认 20）")
    p.add_argument("--context", type=int, default=3,
                   help="首次出现的前后各 N 行上下文（默认 3）")
    p.add_argument("--bucket", choices=["minute", "hour"], default="minute",
                   help="时间分布桶粒度（默认 minute）")
    p.add_argument("--since", default=None, help="仅统计该时间之后的记录 YYYY-MM-DD[THH:MM:SS]")
    p.add_argument("--until", default=None, help="仅统计该时间之前的记录")
    p.add_argument("--no-context", action="store_true", help="跳过上下文收集（更快）")
    p.add_argument("--aggressive", action="store_true",
                   help="激进 ID 抽象：把长度>=8 且同时含字母与数字的独立 token（如 "
                        "abc12345xyz）也归一为 <ID>。仅当同一类错误因每个 ID 不同而被拆成"
                        "几百类时才开；日常排查不要开，因为它可能误并正常文案（如含数字的单词）。")
    args = p.parse_args(argv)

    if not os_path_isfile(args.path):
        print("错误：文件不存在 -> %s" % args.path, file=sys.stderr)
        return 2

    since, until = parse_filter(args.since), parse_filter(args.until)
    clusters = stream_clusters(args.path, args.top, args.context,
                               args.bucket, since, until, args.aggressive)
    if not clusters:
        print("未发现任何日志记录。", file=sys.stderr)
        return 1

    ranked = sorted(clusters.items(), key=lambda kv: kv[1]["count"], reverse=True)
    top_items = ranked[:args.top]
    need_lines = [v["first_line"] for _, v in top_items]
    ctx_map = {} if args.no_context else collect_context(args.path, need_lines, args.context)

    mode = "激进（--aggressive：额外归一化 长度>=8 且含字母+数字的独立 token）" \
        if args.aggressive else "保守（默认：仅 UUID/IP/email/path/hex/长哈希/key=value 归一）"
    print("=" * 72)
    print("日志聚类报告：%s" % args.path)
    print("聚类模式：%s" % mode)
    print("共识别 %d 类模板，以下为出现次数最多的前 %d 类。"
          % (len(clusters), len(top_items)))
    print("=" * 72)

    for idx, (tmpl, c) in enumerate(top_items, 1):
        print("\n#%d  出现 %d 次" % (idx, c["count"]))
        print("  模板：%s" % tmpl)
        print("  首次：%s    末次：%s"
              % (c["first"] or "未解析到时间", c["last"] or "未解析到时间"))
        if c["buckets"]:
            top_bk = c["buckets"].most_common(5)
            dist = "，".join("%s×%d" % (b, n) for b, n in top_bk)
            print("  时间分布（%s 桶，Top5）：%s" % (args.bucket, dist))
        print("  示例原文（最多 3 条）：")
        for ex in c["examples"]:
            print("    | %s" % ex)
        ln = c["first_line"]
        if ln is not None and ln in ctx_map:
            before, after = ctx_map[ln]
            if before:
                print("  首次出现【前 %d 行】上下文：" % args.context)
                for b in before:
                    print("    > %s" % b)
            if after:
                print("  首次出现【后 %d 行】上下文：" % args.context)
                for a in after:
                    print("    < %s" % a)

    print("\n提示：本脚本只给「模板聚类 + 次数 + 时间线 + 上下文」，"
          "不替你下根因结论。根因请结合上下文人工判断。")
    return 0


def os_path_isfile(p):
    import os
    return os.path.isfile(p)


if __name__ == "__main__":
    sys.exit(main())
