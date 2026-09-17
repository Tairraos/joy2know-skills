#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ledger.py —— 晓得·素材台账 配套脚本（纯标准库，零第三方依赖，无需 Pillow）

功能：
  1. 扫描目录，识别图片/视频文件
  2. 读取同名 .txt（提示词正文）与 .json（结构化元数据）作为同源信息
  3. 用标准库解析 PNG/JPEG 头部得到分辨率（不引入 Pillow）
  4. 落盘为 JSONL 或 CSV 索引
  5. 支持按创作意图检索：角色/场景/用途/标签/模型/是否废片/是否可商用/最小分辨率/版本
  6. 增量扫描：以 路径+大小+修改时间 判定已入库项，跳过不重复

用法：
  python scripts/ledger.py scan ./outputs --index ledger.jsonl [--recursive] [--format jsonl|csv]
  python scripts/ledger.py query --index ledger.jsonl --role lina --commercial true --min-res 1024 --scrap false
  python scripts/ledger.py query --index ledger.jsonl --tag poster
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".avi"}


def parse_image_dimensions(path):
    """用标准库解析 PNG/JPEG 头部得到 (宽, 高)；不支持或解析失败返回 None。"""
    try:
        with open(path, "rb") as f:
            head = f.read(64)
        if len(head) < 24:
            return None
        # PNG: 8 字节签名 + IHDR(4长度+4类型) 后 宽高各 4 字节大端
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            w = int.from_bytes(head[16:20], "big")
            h = int.from_bytes(head[20:24], "big")
            return (w, h) if w and h else None
        # JPEG: 以 FFD8 开头，扫描 SOF 标记
        if head[:2] == b"\xff\xd8":
            with open(path, "rb") as f:
                data = f.read()
            i = 2
            while i < len(data) - 9:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                # SOF0..SOF15 中除 C4/C8/CC 为有效尺寸标记
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    h = int.from_bytes(data[i + 5:i + 7], "big")
                    w = int.from_bytes(data[i + 7:i + 9], "big")
                    return (w, h) if w and h else None
                # 跳到下一个标记
                if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                    i += 2
                else:
                    seg_len = int.from_bytes(data[i + 2:i + 4], "big")
                    i += 2 + seg_len if seg_len > 0 else 2
            return None
        return None
    except Exception:
        return None


def probe_video(path):
    """可选探测：优先用系统 ffprobe 取视频宽高与时长。ffprobe 不存在或调用失败则静默返回 None。
    不引入任何第三方库；ffprobe 是外部命令行工具，缺失即降级。"""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        cmd = [
            ffprobe, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "default=noprint_wrappers=1",
            path,
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if out.returncode != 0:
            return None
        info = {}
        for line in out.stdout.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                info[k.strip()] = v.strip()
        w, h = info.get("width"), info.get("height")
        res = None
        if w and h:
            try:
                res = "%dx%d" % (int(w), int(h))
            except ValueError:
                res = None
        dur = info.get("duration") or None
        return {"resolution": res, "duration": dur}
    except Exception:
        return None


def read_sibling_metadata(path):
    """读取同名 .txt（提示词）与 .json（结构化字段），合并为 dict。"""
    meta = {}
    base = os.path.splitext(path)[0]
    txt_path = base + ".txt"
    json_path = base + ".json"
    if os.path.isfile(txt_path):
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                meta["prompt"] = f.read().strip()
        except Exception:
            meta["prompt"] = None
    if os.path.isfile(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                meta.update(data)
        except Exception:
            meta["_json_error"] = "parse_failed"
    return meta


def make_record(path, root, allow_probe=True):
    st = os.stat(path)
    ext = os.path.splitext(path)[1].lower()
    ftype = "video" if ext in VIDEO_EXTS else "image"
    rec = {
        "file_path": os.path.relpath(path, root),
        "type": ftype,
        "role": None,
        "scene": None,
        "purpose": None,
        "prompt": None,
        "model": None,
        "params": None,
        "tags": [],
        "is_scrap": False,
        "version": None,
        "commercial": None,
        "resolution": None,
        "created_at": None,
        "duration": None,
        "_size": st.st_size,
        "_mtime": int(st.st_mtime),
    }
    meta = read_sibling_metadata(path)
    for k in ("role", "scene", "purpose", "prompt", "model", "params",
              "tags", "is_scrap", "version", "commercial", "created_at"):
        if k in meta and meta[k] not in (None, ""):
            rec[k] = meta[k]
    if ftype == "image":
        dims = parse_image_dimensions(path)
        if dims:
            rec["resolution"] = "%dx%d" % dims
    elif ftype == "video" and allow_probe:
        pv = probe_video(path)
        if pv:
            if pv.get("resolution"):
                rec["resolution"] = pv["resolution"]
            rec["duration"] = pv.get("duration")
    return rec


def iter_media_files(directory, recursive):
    for entry in os.scandir(directory):
        if entry.is_dir():
            if recursive:
                yield from iter_media_files(entry.path, recursive)
            continue
        ext = os.path.splitext(entry.name)[1].lower()
        if ext in IMAGE_EXTS or ext in VIDEO_EXTS:
            yield entry.path


def load_index(index_path):
    records = []
    if not os.path.isfile(index_path):
        return records
    if index_path.endswith(".csv"):
        with open(index_path, "r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                records.append(row)
    else:
        with open(index_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def save_index(records, index_path, fmt):
    if fmt == "csv":
        fields = ["file_path", "type", "role", "scene", "purpose", "prompt",
                  "model", "params", "tags", "is_scrap", "version",
                  "commercial", "resolution", "duration", "created_at"]
        with open(index_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for r in records:
                row = dict(r)
                if isinstance(row.get("tags"), list):
                    row["tags"] = ",".join(map(str, row["tags"]))
                w.writerow(row)
    else:
        with open(index_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


def cmd_scan(args):
    records = load_index(args.index)
    seen = {(r.get("file_path"), int(r.get("_size", -1)), int(r.get("_mtime", -1)))
            for r in records}
    root = args.directory
    added = 0
    for p in iter_media_files(root, args.recursive):
        rel = os.path.relpath(p, root)
        st = os.stat(p)
        key = (rel, st.st_size, int(st.st_mtime))
        if key in seen:
            continue
        records.append(make_record(p, root, allow_probe=not args.no_ffprobe))
        seen.add(key)
        added += 1
    save_index(records, args.index, args.format)
    print("扫描完成：新增 %d 条，台账共 %d 条 → %s" % (added, len(records), args.index))


def _as_bool(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    return str(v).strip().lower() in ("true", "1", "yes", "是")


def cmd_query(args):
    records = load_index(args.index)
    if not records:
        print("台账为空或不存在：%s" % args.index)
        return
    role = args.role
    scene = args.scene
    purpose = args.purpose
    model = args.model
    tag = args.tag
    version = args.version
    scrap = _as_bool(args.scrap) if args.scrap is not None else None
    commercial = _as_bool(args.commercial) if args.commercial is not None else None
    min_res = int(args.min_res) if args.min_res else 0

    hits = []
    for r in records:
        if role and (r.get("role") or "") != role:
            continue
        if scene and (r.get("scene") or "") != scene:
            continue
        if purpose and (r.get("purpose") or "") != purpose:
            continue
        if model and (r.get("model") or "") != model:
            continue
        if version and str(r.get("version") or "") != str(version):
            continue
        if scrap is not None and _as_bool(r.get("is_scrap")) != scrap:
            continue
        if commercial is not None and _as_bool(r.get("commercial")) != commercial:
            continue
        if tag:
            tags = r.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            if tag not in tags:
                continue
        if min_res:
            res = r.get("resolution") or ""
            try:
                w, h = (int(x) for x in res.lower().split("x"))
                if w < min_res or h < min_res:
                    continue
            except Exception:
                continue
        hits.append(r)

    print("命中 %d / %d 条：" % (len(hits), len(records)))
    for r in hits:
        res = r.get("resolution") or "未提供"
        scrap_mark = " [废片]" if _as_bool(r.get("is_scrap")) else ""
        print("  %s | %s | %s | res=%s%s" % (
            r.get("file_path"), r.get("role") or "未提供",
            r.get("purpose") or "未提供", res, scrap_mark))


def main():
    parser = argparse.ArgumentParser(description="素材台账：扫描 + 检索（纯标准库）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="扫描目录建立/增量更新台账")
    p_scan.add_argument("directory", help="要扫描的目录")
    p_scan.add_argument("--index", default="ledger.jsonl", help="索引文件路径")
    p_scan.add_argument("--recursive", action="store_true", help="递归子目录")
    p_scan.add_argument("--no-ffprobe", action="store_true", help="跳过 ffprobe 探测视频分辨率/时长")
    p_scan.add_argument("--format", default="jsonl", choices=["jsonl", "csv"])
    p_scan.set_defaults(func=cmd_scan)

    p_q = sub.add_parser("query", help="按创作意图检索")
    p_q.add_argument("--index", default="ledger.jsonl", help="索引文件路径")
    p_q.add_argument("--role", help="按角色过滤")
    p_q.add_argument("--scene", help="按场景过滤")
    p_q.add_argument("--purpose", help="按用途过滤")
    p_q.add_argument("--model", help="按生成模型过滤")
    p_q.add_argument("--tag", help="按标签过滤（命中即匹配）")
    p_q.add_argument("--version", help="按版本号过滤")
    p_q.add_argument("--scrap", help="是否废片：true/false")
    p_q.add_argument("--commercial", help="是否可商用：true/false")
    p_q.add_argument("--min-res", help="最小分辨率（宽高均 >= 此值）")
    p_q.set_defaults(func=cmd_query)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
