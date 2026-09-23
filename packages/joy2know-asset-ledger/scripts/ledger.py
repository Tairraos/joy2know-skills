#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ledger.py —— 晓得·素材台账 配套脚本 v1.2.0

纯标准库，零第三方依赖，不需要 Pillow。视频分辨率/时长走可选的系统 ffprobe，缺了就降级。

子命令
  scan     扫描目录建立 / 增量更新台账（默认自动尝试从图内元数据挖提示词与参数）
  query    按创作意图检索，另支持提示词全文检索与批次过滤
  set      人工补字段 / 标废片 / 改可商用 —— 补上「文档里有、脚本没有」的写入入口
  stats    台账体检：总量、废片率、字段完整度、分布、隐私提醒
  render   渲染单文件浅色 HTML 看板（缩略图网格 + 前端筛选 + 统计条）

三条设计底线
  1) 检索维度只围绕创作意图；文件名与时间只用于「推断批次」，不作检索滤镜。
  2) 值只来自同源文件 / 图内元数据 / 用户给定，三者在 meta_source 里分开记，不猜。
  3) 废片显式标注入库，检索默认排除，需要时用 --scrap true 找回。

用法
  python scripts/ledger.py scan ./outputs --index ledger.jsonl [--recursive]
  python scripts/ledger.py query --index ledger.jsonl --role lina --commercial true --min-res 1024
  python scripts/ledger.py query --index ledger.jsonl --grep-prompt "rain, umbrella"
  python scripts/ledger.py set --index ledger.jsonl --path out/lina_03.png --purpose poster --scrap true
  python scripts/ledger.py stats --index ledger.jsonl
  python scripts/ledger.py render --index ledger.jsonl --out ledger.html
"""

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import zlib

TOOL_VERSION = "1.2.0"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".avi"}

# 台账字段（顺序即 JSONL / CSV 的写出顺序）
CREATIVE_FIELDS = ["role", "scene", "purpose", "prompt", "model",
                   "params", "tags", "is_scrap", "version", "commercial"]
TECH_FIELDS = ["file_path", "type", "resolution", "duration", "created_at"]
DERIVED_FIELDS = ["batch_family", "batch_id", "batch_basis", "shot_id",
                  "meta_source", "meta_tool", "raw_meta", "flags"]
CSV_COLUMNS = ["file_path", "type", "role", "scene", "purpose", "prompt",
               "model", "params", "tags", "is_scrap", "version", "commercial",
               "resolution", "duration", "created_at",
               "batch_family", "batch_id", "batch_basis", "shot_id",
               "meta_source", "meta_tool"]
# CSV 也要带上增量判定键，否则二次扫描会重复入库
CSV_KEY_COLUMNS = ["_size", "_mtime"]

DEFAULT_BATCH_WINDOW = 600  # 秒；同一命名族内，间隔不超过这个值视为同一批

# 本机绝对路径的样子（用于隐私提醒：内嵌元数据里常混进作者家目录）
LOCAL_PATH_RE = re.compile(r"(/Users/|/home/|[A-Za-z]:\\\\)")


# ============================================================ 图片 / 视频解析

def parse_image_dimensions(path, head_limit=2 * 1024 * 1024):
    """用标准库解析 PNG / JPEG 头部得到 (宽, 高)；不支持或解析失败返回 None。"""
    try:
        with open(path, "rb") as f:
            head = f.read(64)
        if len(head) < 24:
            return None
        # PNG: 8 字节签名 + IHDR(4 长度 + 4 类型) 后宽高各 4 字节大端
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            w = int.from_bytes(head[16:20], "big")
            h = int.from_bytes(head[20:24], "big")
            return (w, h) if w and h else None
        # JPEG: 以 FFD8 开头，扫描 SOF 标记。SOF 一般就在文件头部，
        # 这里只读前 2MB —— 避免为一张大图把整个文件吞进内存。
        if head[:2] == b"\xff\xd8":
            with open(path, "rb") as f:
                data = f.read(head_limit)
            i = 2
            while i < len(data) - 9:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                # SOF0..SOF15 中除 C4 / C8 / CC 为有效尺寸标记
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    h = int.from_bytes(data[i + 5:i + 7], "big")
                    w = int.from_bytes(data[i + 7:i + 9], "big")
                    return (w, h) if w and h else None
                if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                    i += 2
                else:
                    seg_len = int.from_bytes(data[i + 2:i + 4], "big")
                    i += 2 + seg_len if seg_len > 0 else 2
            return None
        return None
    except Exception:
        return None


def read_png_text_chunks(path):
    """读取 PNG 的全部文本块，返回 {keyword: text}。

    三种块都要认 —— 这是本技能最容易踩空的地方：
      tEXt  未压缩，Latin-1；A1111 的 parameters 就走这里
      zTXt  zlib 压缩，关键字明文；ComfyUI 的大 JSON 经常落在这
      iTXt  UTF-8，压缩标志可选；XMP 与部分工具走这里
    只认 tEXt 的解析器，会在一大半 ComfyUI 图上读不出任何东西。
    """
    out = {}
    try:
        with open(path, "rb") as f:
            if f.read(8) != b"\x89PNG\r\n\x1a\n":
                return None
            while True:
                hdr = f.read(8)
                if len(hdr) < 8:
                    break
                length = int.from_bytes(hdr[:4], "big")
                ctype = hdr[4:8]
                if length > 64 * 1024 * 1024:  # 异常长度，防止读到天边
                    break
                data = f.read(length)
                f.read(4)  # CRC 不校验，损坏的块最多是读不出来，不该中断整批

                if ctype == b"tEXt":
                    k, _, v = data.partition(b"\x00")
                    out[_dec(k, "latin-1")] = _dec(v, "latin-1")
                elif ctype == b"zTXt":
                    k, _, rest = data.partition(b"\x00")
                    body = b""
                    if len(rest) > 1:
                        try:
                            body = zlib.decompress(rest[1:])
                        except Exception:
                            body = b""
                    out[_dec(k, "latin-1")] = _dec(body, "latin-1")
                elif ctype == b"iTXt":
                    k, _, rest = data.partition(b"\x00")
                    if len(rest) >= 2:
                        comp_flag, _method = rest[0], rest[1]
                        body = rest[2:]
                        # 跳过 language tag 与 translated keyword 两段
                        i = body.find(b"\x00")
                        if i >= 0:
                            j = body.find(b"\x00", i + 1)
                            if j >= 0:
                                body = body[j + 1:]
                        if comp_flag == 1:
                            try:
                                body = zlib.decompress(body)
                            except Exception:
                                body = b""
                        out[_dec(k, "latin-1")] = _dec(body, "utf-8")
                if ctype == b"IEND":
                    break
    except Exception:
        return out or None
    return out


def _dec(b, enc):
    try:
        return b.decode(enc)
    except Exception:
        return b.decode(enc, "replace")


def _split_top_level(text, sep=","):
    """按 sep 切分，但不切进引号里 —— Lora hashes: "a: 1, b: 2" 会骗过朴素切分。"""
    parts, buf, quote = [], [], None
    for ch in text:
        if quote:
            if ch == quote:
                quote = None
            buf.append(ch)
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch == sep:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return parts


def parse_a1111_parameters(text):
    """解析 Automatic1111 / Forge 的 parameters 纯文本块。

    结构：正向提示词（可多行）→ 一行 `Negative prompt: ...` → 一行 `Steps: ..., Sampler: ...`。
    注意提示词自己就含逗号，所以参数行必须靠 `Steps:` 锚点定位，不能从前往后切。
    """
    res = {"tool": "a1111"}
    pos, neg, param_line = [], [], None
    mode = "pos"
    for line in text.split("\n"):
        if line.startswith("Negative prompt:"):
            mode = "neg"
            neg.append(line[len("Negative prompt:"):].strip())
            continue
        if re.match(r"^\s*Steps:\s*\d", line):
            mode = "params"
            param_line = line
            continue
        if mode == "pos":
            pos.append(line)
        elif mode == "neg":
            neg.append(line)
    if pos:
        res["prompt"] = "\n".join(pos).strip()
    if neg:
        res["negative_prompt"] = "\n".join(neg).strip()

    kv = {}
    if param_line:
        for part in _split_top_level(param_line):
            if ":" in part:
                k, _, v = part.partition(":")
                kv[k.strip()] = v.strip()
    params = {}
    for src, dst in (("Steps", "steps"), ("Sampler", "sampler"), ("CFG scale", "cfg"),
                     ("Seed", "seed"), ("Size", "size"), ("Model", "model"),
                     ("Model hash", "model_hash"), ("Denoising strength", "denoise"),
                     ("Clip skip", "clip_skip"), ("Schedule type", "scheduler"),
                     ("VAE", "vae"), ("Lora hashes", "lora_hashes")):
        if src in kv:
            params[dst] = kv[src]
    if params:
        res["params"] = params
    if kv.get("Model"):
        res["model"] = kv["Model"]
    if kv.get("Size") and re.match(r"^\d+x\d+$", kv["Size"]):
        res["resolution"] = kv["Size"]
    return res


def parse_comfy_prompt(json_text):
    """解析 ComfyUI 的 prompt 块（API 执行图 JSON）。

    正向 / 负向提示词不靠节点标题猜，而是顺着 KSampler 的 positive / negative
    输入连线找到真正的 CLIPTextEncode —— 标题写在 _meta.title 里，随时会被改。
    连线拿不到时才退回标题启发式，并在 basis 里注明。
    """
    try:
        graph = json.loads(json_text)
    except Exception:
        return None
    if not isinstance(graph, dict) or not graph:
        return None
    res = {"tool": "comfyui"}
    params, positive, negative, basis = {}, None, None, "link"

    sampler_types = {"KSampler", "KSamplerAdvanced", "SamplerCustom", "KSamplerSelect"}
    sampler = None
    for _, node in _iter_nodes(graph):
        if node.get("class_type") in sampler_types:
            sampler = node
            break

    if sampler:
        ins = sampler.get("inputs", {}) or {}
        for k, dst in (("seed", "seed"), ("noise_seed", "seed"), ("steps", "steps"),
                       ("cfg", "cfg"), ("sampler_name", "sampler"),
                       ("scheduler", "scheduler"), ("denoise", "denoise")):
            if k in ins and not isinstance(ins[k], list):
                params[dst] = ins[k]
        positive = _node_text(graph, ins.get("positive"))
        negative = _node_text(graph, ins.get("negative"))

    if positive is None and negative is None:
        basis = "title"
        for _, node in _iter_nodes(graph):
            if "CLIPTextEncode" not in str(node.get("class_type", "")):
                continue
            t = (node.get("inputs") or {}).get("text")
            if not isinstance(t, str):
                continue
            title = ((node.get("_meta") or {}).get("title") or "").lower()
            if "neg" in title:
                negative = negative or t
            else:
                positive = positive or t

    if positive is not None:
        res["prompt"] = positive
    if negative is not None:
        res["negative_prompt"] = negative
    if params:
        res["params"] = params
    for _, node in _iter_nodes(graph):
        ct = node.get("class_type", "")
        if ct in ("CheckpointLoaderSimple", "CheckpointLoader", "UNETLoader"):
            name = (node.get("inputs") or {}).get("ckpt_name") or (node.get("inputs") or {}).get("unet_name")
            if isinstance(name, str) and name:
                res["model"] = name
                break
    res["basis"] = basis
    return res if len(res) > 2 else None


def _iter_nodes(graph):
    for nid, node in graph.items():
        if nid.startswith("_"):
            continue
        if isinstance(node, dict) and "class_type" in node:
            yield nid, node


def _node_text(graph, ref):
    """顺着连线取回上游节点的 text 输入；ref 形如 ["6", 0]。"""
    if not isinstance(ref, list) or not ref:
        return None
    node = graph.get(str(ref[0]))
    if not isinstance(node, dict):
        return None
    t = (node.get("inputs") or {}).get("text")
    if isinstance(t, str):
        return t
    for key in ("text_g", "text_l"):
        if isinstance((node.get("inputs") or {}).get(key), str):
            return node["inputs"][key]
    return None


def parse_jsonish(text, tool):
    """InvokeAI / Fooocus / NovelAI 之类把参数写成 JSON 的，做浅提取，认不出就交回原文。"""
    try:
        data = json.loads(text)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    res = {"tool": tool}

    def dig(*keys):
        for k in keys:
            if k in data and isinstance(data[k], (str, int, float)) and data[k] != "":
                return data[k]
        return None

    p = dig("prompt", "positive_prompt", "positive")
    if p:
        res["prompt"] = str(p)
    n = dig("negative_prompt", "negative")
    if n:
        res["negative_prompt"] = str(n)
    m = dig("model", "model_name", "ckpt_name", "base_model")
    if m:
        res["model"] = str(m)
    seed = dig("seed")
    if seed is not None:
        res["params"] = {"seed": seed}
    return res if len(res) > 1 else None


def extract_embedded_metadata(path):
    """从图内元数据挖创作信息。返回 (结果 dict | None, 全部文本块 dict | None)。

    支持：ComfyUI（prompt / workflow，含 zTXt 压缩）、Automatic1111 / Forge（parameters）、
    InvokeAI（invokeai_metadata / sd-metadata）、Fooocus / NovelAI（Comment）。
    明确不支持：JPEG / WebP 里的 EXIF UserComment（A1111 存 JPEG 时会走那里）——
    这条限制写在 references 里，遇到时 raw_meta 会把原文带出来供人工查看。
    """
    ext = os.path.splitext(path)[1].lower()
    if ext != ".png":
        return None, None
    chunks = read_png_text_chunks(path)
    if not chunks:
        return None, None

    # ComfyUI：prompt 是执行图，优先用它；workflow 只是画布图，兜底
    for key in ("prompt", "workflow"):
        if key in chunks and chunks[key].strip().startswith("{"):
            got = parse_comfy_prompt(chunks[key])
            if got:
                return got, chunks
    if "parameters" in chunks:
        return parse_a1111_parameters(chunks["parameters"]), chunks
    for key, tool in (("invokeai_metadata", "invokeai"), ("sd-metadata", "invokeai"),
                      ("Comment", "fooocus/novelai"), ("Description", "generic")):
        if key in chunks:
            got = parse_jsonish(chunks[key], tool)
            if got:
                return got, chunks
    return None, chunks


def probe_video(path):
    """可选探测：优先用系统 ffprobe 取视频宽高与时长。ffprobe 不存在或调用失败则静默返回 None。"""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        cmd = [ffprobe, "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height,duration",
               "-of", "default=noprint_wrappers=1", path]
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
        return {"resolution": res, "duration": info.get("duration") or None}
    except Exception:
        return None


# ============================================================ 单条记录

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


def _to_str(v):
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    if v is None:
        return None
    return str(v)


def make_record(path, root, allow_probe=True, embed=True, keep_raw_meta=False):
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
        "batch_family": None,
        "batch_id": None,
        "batch_basis": None,
        "shot_id": None,
        "meta_source": "none",
        "meta_tool": None,
        "raw_meta": None,
        "flags": [],
        "_size": st.st_size,
        "_mtime": int(st.st_mtime),
    }

    # 1) 同源文件（作者自己落的旁挂元数据，最可信）
    sidecar = read_sibling_metadata(path)
    for k in CREATIVE_FIELDS:
        if k in sidecar and sidecar[k] not in (None, ""):
            rec[k] = sidecar[k]
    rec["created_at"] = sidecar.get("created_at") or None
    if any(sidecar.get(k) not in (None, "") for k in ("role", "prompt", "model")):
        rec["meta_source"] = "sidecar"

    # 2) 图内元数据（没有同源文件时的主来源）
    if embed and ftype == "image":
        got, chunks = extract_embedded_metadata(path)
        if got:
            if rec["meta_source"] == "none":
                rec["meta_source"] = "embedded"
                rec["meta_tool"] = got.get("tool")
            else:
                rec["meta_tool"] = rec["meta_tool"] or got.get("tool")
            for k in ("prompt", "model", "params", "resolution"):
                if rec.get(k) in (None, "", []) and got.get(k) not in (None, "", []):
                    rec[k] = got[k]
            neg = got.get("negative_prompt")
            if neg:
                rec["params"] = rec["params"] if isinstance(rec["params"], dict) else {}
                rec["params"].setdefault("negative_prompt", neg)
            if got.get("basis"):
                rec["flags"].append("comfy-basis:" + got["basis"])
        if chunks:
            # 认不出的块也留个底：截断保存，供人工查看，不参与检索
            names = sorted(chunks.keys())
            rec["flags"].append("png-chunks:" + ",".join(names))
            if LOCAL_PATH_RE.search(json.dumps(chunks, ensure_ascii=False)):
                rec["flags"].append("meta-has-local-path")
            if keep_raw_meta:
                blob = json.dumps(chunks, ensure_ascii=False)
                rec["raw_meta"] = blob[:4000]

    # 3) 分辨率：图片以头部解析为准，绝不靠文件名猜
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

    if not rec["created_at"]:
        import datetime
        rec["created_at"] = datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
        rec["flags"].append("created_at-from-mtime")
    return rec


def iter_media_files(directory, recursive):
    try:
        entries = list(os.scandir(directory))
    except OSError:
        return
    for entry in entries:
        if entry.name.startswith("."):
            continue
        if entry.is_dir(follow_symlinks=False):
            if recursive:
                for p in iter_media_files(entry.path, recursive):
                    yield p
            continue
        ext = os.path.splitext(entry.name)[1].lower()
        if ext in IMAGE_EXTS or ext in VIDEO_EXTS:
            yield entry.path


# ============================================================ 索引读写

def load_index(index_path):
    """读台账。返回 (records, meta)。兼容没有 _meta 行的旧台账。"""
    records, meta = [], {}
    if not os.path.isfile(index_path):
        return records, meta
    if index_path.endswith(".csv"):
        with open(index_path, "r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("file_path") == "__meta__":
                    try:
                        meta = json.loads(row.get("prompt") or "{}")
                    except Exception:
                        meta = {}
                    continue
                rec = dict(row)
                for k in CSV_KEY_COLUMNS:
                    if k in rec and rec[k] not in (None, ""):
                        try:
                            rec[k] = int(float(rec[k]))
                        except ValueError:
                            rec.pop(k, None)
                for k in ("is_scrap", "commercial"):
                    if rec.get(k) not in (None, ""):
                        rec[k] = str(rec[k]).strip().lower() in ("true", "1", "yes", "是")
                if rec.get("tags"):
                    rec["tags"] = [t.strip() for t in str(rec["tags"]).split(",") if t.strip()]
                else:
                    rec["tags"] = []
                records.append(rec)
    else:
        with open(index_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue  # 单行损坏不该让整个台账读不出来
                if isinstance(obj, dict) and obj.get("_meta"):
                    meta = obj
                else:
                    records.append(obj)
    return records, meta


def save_index(records, index_path, fmt, meta=None):
    meta = dict(meta or {})
    meta["tool_version"] = TOOL_VERSION
    if fmt == "csv":
        fields = CSV_COLUMNS + CSV_KEY_COLUMNS
        with open(index_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            # meta 也落一行，否则 render 找不到 root，增量也读不回键
            meta_row = {k: "" for k in fields}
            meta_row["file_path"] = "__meta__"
            meta_row["prompt"] = json.dumps(meta, ensure_ascii=False)
            w.writerow(meta_row)
            for r in records:
                row = dict(r)
                if isinstance(row.get("tags"), list):
                    row["tags"] = ",".join(map(str, row["tags"]))
                if isinstance(row.get("params"), dict):
                    row["params"] = json.dumps(row["params"], ensure_ascii=False)
                w.writerow(row)
    else:
        with open(index_path, "w", encoding="utf-8") as f:
            m = {"_meta": True}
            m.update(meta)
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _dedupe(records, verbose=True):
    """同一 file_path 只留最后一条。csv 时代留下的重复台账，靠这一步收敛。"""
    seen, out, dropped = set(), [], 0
    for r in reversed(records):
        p = r.get("file_path")
        if p in seen:
            dropped += 1
            continue
        seen.add(p)
        out.append(r)
    out.reverse()
    if dropped and verbose:
        print("提示：台账里有 %d 条重复记录（同一文件多条），已按最后一次扫描的结果收敛。" % dropped)
    return out


# ============================================================ 批次推断

_STEM_RULES = [
    (re.compile(r"[\s_-]*\(\d{1,3}\)$"), "copy-paren"),
    (re.compile(r"[\s_-]*(?:copy|副本)$", re.I), "copy-word"),
    (re.compile(r"[\s_-]+v(?:er)?\.?\d{1,3}$", re.I), "version-v"),
    (re.compile(r"[\s_-]+\d{1,4}$"), "trailing-number"),
]


def norm_stem(stem):
    """把文件名主干规范化成「命名族」。返回 (族名, 命中的规则)。

    例：lina_03 → lina（trailing-number）；poster (1) → poster（copy-paren）。
    绝不改内容，只去尾部版本/副本标记 —— 规则名会记进 batch_basis，误判可见可查。
    """
    s = stem
    for rx, name in _STEM_RULES:
        new = rx.sub("", s)
        if new != s and new.strip():
            return new.strip(" _-"), name
    return s, None


def assign_batches(records, window=DEFAULT_BATCH_WINDOW):
    """按「文件名族 + 时间邻近」推断批次，写回 batch_family / batch_id / batch_basis。

    这是推断，不是事实 —— 一律以 [推断] 呈现。文件属性在这里只当线索，
    不作为检索维度（见 SKILL.md 规则 1）。
    """
    fams = {}
    for r in records:
        p = r.get("file_path") or ""
        stem = os.path.splitext(os.path.basename(p))[0]
        fam, rule = norm_stem(stem)
        r["batch_family"] = fam if rule else None
        r["batch_id"] = None
        r["batch_basis"] = None
        r.setdefault("flags", [])
        if rule:
            r["flags"] = [f for f in r["flags"] if not f.startswith("stem-rule:")]
            r["flags"].append("stem-rule:" + rule)
        fams.setdefault(fam, []).append(r)

    groups = 0
    for fam, items in fams.items():
        if len(items) < 2:
            continue
        items.sort(key=lambda r: (r.get("_mtime") or 0, r.get("file_path") or ""))
        bucket, last = [], None
        buckets = []
        for r in items:
            t = r.get("_mtime") or 0
            if last is None or (t - last) <= window:
                bucket.append(r)
            else:
                buckets.append(bucket)
                bucket = [r]
            last = t
        if bucket:
            buckets.append(bucket)
        for i, b in enumerate(buckets, 1):
            if len(b) < 2:
                continue
            groups += 1
            for r in b:
                r["batch_id"] = "%s#%d" % (fam, i)
                r["batch_basis"] = "filename+time"
        # 同族但时间相差太远 → 仍标出族关系，只是不成批
        for r in items:
            if not r.get("batch_id"):
                r["batch_basis"] = "filename-only"
    return groups


# ============================================================ 与角色档案 / 分镜工联动

def _addflag(rec, flag):
    """幂等写标记：同前缀的旧值先清掉，重复 scan 不会越堆越多。"""
    rec.setdefault("flags", [])
    pre = flag.split(":")[0]
    rec["flags"] = [f for f in rec["flags"] if f != flag and not f.startswith(pre + ":")]
    rec["flags"].append(flag)


def _extract_anchors(text):
    """取角色卡的 locked_anchors 列表项。YAML（`locked_anchors:`）与 Markdown
    （`## 连续性锁`）两种等价格式都认，遇下一个非列表行即认为块结束。

    **只用正则取这一个块**，不假装能解析任意 YAML —— 角色卡的实际字段就这几个。
    """
    out = []
    capturing = False
    for raw in text.split("\n"):
        ln = raw.rstrip()
        if re.search(r"连续性锁", ln) or re.match(r"^\s*locked_anchors\s*:", ln):
            inline = re.search(r"\[(.+?)\]", ln)
            if inline:  # 行内数组写法 locked_anchors: [a, b]
                return [x.strip().strip("'\"") for x in inline.group(1).split(",") if x.strip()]
            capturing = True
            continue
        if not capturing or not ln.strip():
            continue
        m = re.match(r"^\s*[-*]\s+(.+)$", ln)
        if m:
            v = re.sub(r"（[^）]*）\s*$", "", m.group(1).strip()).strip().strip("'\"")
            if v:
                out.append(v)
            continue
        break  # 不是列表项也不是空行 → 块结束
    return out


def load_character_cards(directory):
    """读「晓得·角色档案」产出的角色卡目录，返回 {角色名: [锚点短语]}。

    角色卡落在 `characters/char_<name>.yaml` 或 `.md`。这里只取 `name` 与
    `locked_anchors` 两个字段，**不引入 YAML 依赖**。
    """
    cards = {}
    if not directory:
        return cards
    if not os.path.isdir(directory):
        print("提示：--characters 指定的目录不存在：%s" % directory)
        return cards
    for fn in sorted(os.listdir(directory)):
        if not fn.startswith("char_") or not fn.endswith((".yaml", ".yml", ".md")):
            continue
        try:
            with open(os.path.join(directory, fn), "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            continue
        names = [m.group(1).strip().strip("'\"")
                 for m in re.finditer(r"^\s*name:\s*([^\s#]+)", text, re.M)]
        if not names:
            m = re.search(r"[-*]\s*代号[：:]\s*(\S+)", text)
            if m:
                names = [m.group(1).strip()]
        if not names:
            # 兜底取文件名里的 name —— 这是角色卡的命名约定，不是「凭文件名猜角色」
            names = [os.path.splitext(fn)[0][len("char_"):]]
        anchors = _extract_anchors(text)
        for n in names:
            if n:
                cards.setdefault(n, anchors)
    return cards


def _parse_prompts_md(text):
    """解析「晓得·分镜工」的 shots/prompts.md：按 `## shot_001` 分段取条目。"""
    out, cur = {}, None
    for ln in text.split("\n"):
        m = re.match(r"^##\s+(shot_\d+)\s*$", ln)
        if m:
            cur = m.group(1)
            out[cur] = {}
            continue
        if not cur:
            continue
        m2 = re.match(r"^[-*]\s*([^：:]+)[：:]\s*(.+)$", ln)
        if not m2:
            continue
        k, v = m2.group(1).strip(), m2.group(2).strip()
        if "提示词" in k:
            out[cur]["prompt"] = v
        elif "景别" in k or "运镜" in k:
            out[cur]["shot_language"] = v
        elif "锚点" in k:
            out[cur]["anchors_text"] = v
    return out


def load_storyboard(target):
    """读「晓得·分镜工」的产出目录（或其 manifest.json），返回 {shot_001: {...}}。

    清单 `manifest.json` 给的是实测值（起止、时长、首帧路径）；`prompts.md`
    给的是该镜的提示词。两者合并后，首帧图能自动带上它对应的分镜提示词。
    """
    shots = {}
    if not target:
        return shots
    manifest_path = os.path.join(target, "manifest.json") if os.path.isdir(target) else target
    if not os.path.isfile(manifest_path):
        print("提示：--storyboard 没找到 manifest.json：%s" % manifest_path)
        return shots
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        print("提示：分镜清单解析失败：%s" % manifest_path)
        return shots
    for s in (data.get("shots") or []) if isinstance(data, dict) else []:
        tag = s.get("tag")
        if tag:
            shots[tag] = {"duration": s.get("duration"), "start": s.get("start"),
                          "end": s.get("end"), "prompt": None}
    prompts_md = os.path.join(os.path.dirname(manifest_path), "prompts.md")
    if os.path.isfile(prompts_md):
        try:
            with open(prompts_md, "r", encoding="utf-8") as f:
                parsed = _parse_prompts_md(f.read())
        except Exception:
            parsed = {}
        for tag, body in parsed.items():
            shots.setdefault(tag, {"duration": None})
            shots[tag]["prompt"] = body.get("prompt")
            if body.get("shot_language"):
                shots[tag]["shot_language"] = body["shot_language"]
    return shots


def apply_links(records, cards, shots):
    """把角色卡与分镜清单的信息接进台账。返回一份联动报告。

    两条边界（都与规则 1、规则 2 一致）：
      · 角色名**只做校验**（在不在卡里），绝不因为文件名含某角色就自动填 `role`；
      · 锚点短语逐条比对提示词，命中情况记进 flags，作为「生成时有没有照角色卡来」的证据。
    """
    report = {"unknown_role": [], "anchor_miss": [], "anchor_partial": [],
              "no_prompt": [], "storyboard_hit": 0, "storyboard_unknown": []}
    for r in records:
        role = r.get("role")
        if role and cards:
            anchors = cards.get(role)
            if anchors is None:
                _addflag(r, "unknown-role")
                report["unknown_role"].append((r.get("file_path"), role))
            elif anchors:
                prompt = r.get("prompt") or ""
                if not prompt:
                    report["no_prompt"].append(r.get("file_path"))
                else:
                    hit = sum(1 for a in anchors if a.lower() in prompt.lower())
                    if hit == 0:
                        _addflag(r, "anchor-miss:%s(0/%d)" % (role, len(anchors)))
                        report["anchor_miss"].append(r.get("file_path"))
                    elif hit < len(anchors):
                        _addflag(r, "anchor-partial:%s(%d/%d)" % (role, hit, len(anchors)))
                        report["anchor_partial"].append(r.get("file_path"))

        base = os.path.basename(r.get("file_path") or "")
        m = re.search(r"(shot_\d{3})", base)
        if m and shots is not None and shots:
            tag = m.group(1)
            info = shots.get(tag)
            if not info:
                report["storyboard_unknown"].append(tag)
                continue
            r["shot_id"] = tag
            report["storyboard_hit"] += 1
            if not r.get("duration") and info.get("duration") is not None:
                r["duration"] = str(info["duration"])
                _addflag(r, "duration-from-storyboard")
            if not r.get("prompt") and info.get("prompt"):
                r["prompt"] = info["prompt"]
                if r.get("meta_source") == "none":
                    r["meta_source"] = "sidecar"
                r["meta_tool"] = r.get("meta_tool") or "storyboard"
                _addflag(r, "prompt-from-storyboard")
    return report


def _print_link_report(report, cards, shots):
    if not cards and not shots:
        return
    print("  联动：", end="")
    bits = []
    if cards:
        bits.append("角色卡 %d 张" % len(cards))
    if shots:
        bits.append("分镜 %d 镜，台账命中 %d" % (len(shots), report["storyboard_hit"]))
    print(" · ".join(bits))
    if report["unknown_role"]:
        names = sorted({n for _, n in report["unknown_role"]})
        print("    ⚠ %d 条素材的角色不在角色卡里（可能是改名/拼错）：%s"
              % (len(report["unknown_role"]), ", ".join(names[:6])))
    if report["anchor_miss"]:
        print("    ⚠ %d 条素材的提示词一条锚点短语都没命中 —— 生成时可能没用角色卡" % len(report["anchor_miss"]))
        for p in report["anchor_miss"][:5]:
            print("      %s" % p)
    if report["anchor_partial"]:
        print("    · %d 条只命中了部分锚点（改了造型或提示词被压缩）" % len(report["anchor_partial"]))
    if report["storyboard_unknown"]:
        tags = sorted(set(report["storyboard_unknown"]))
        print("    ⚠ 有 shot 文件名对不上分镜清单：%s" % ", ".join(tags[:6]))


# ============================================================ 检索条件

def _as_bool(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    return str(v).strip().lower() in ("true", "1", "yes", "是")


def _tags_of(r):
    tags = r.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    return tags


def _res_of(r):
    res = r.get("resolution") or ""
    try:
        w, h = (int(x) for x in str(res).lower().split("x"))
        return w, h
    except Exception:
        return None


def filter_records(records, args):
    """统一过滤。返回 (命中列表, 因缺字段被跳过的条数)。"""
    role = args.role
    scene = args.scene
    purpose = args.purpose
    model = args.model
    tag = args.tag
    version = args.version
    batch = getattr(args, "batch", None)
    shot = getattr(args, "shot", None)
    grep = getattr(args, "grep_prompt", None)
    scrap = _as_bool(args.scrap) if args.scrap is not None else None
    all_scrap = getattr(args, "all", False)
    commercial = _as_bool(args.commercial) if args.commercial is not None else None
    min_res = int(args.min_res) if args.min_res else 0
    min_long = int(args.min_long_side) if getattr(args, "min_long_side", None) else 0

    hits, skipped_missing = [], 0
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
        if batch and (r.get("batch_id") or "") != batch and (r.get("batch_family") or "") != batch:
            continue
        if shot and (r.get("shot_id") or "") != shot:
            continue
        if grep:
            hay = (r.get("prompt") or "")
            if isinstance(r.get("params"), dict):
                hay += " " + json.dumps(r["params"], ensure_ascii=False)
            if grep.lower() not in hay.lower():
                continue
        if commercial is not None and _as_bool(r.get("commercial")) != commercial:
            continue
        if scrap is not None:
            if _as_bool(r.get("is_scrap")) != scrap:
                continue
        elif not all_scrap:
            if _as_bool(r.get("is_scrap")):  # 默认排除废片
                continue
        if min_res or min_long:
            dims = _res_of(r)
            if not dims:
                skipped_missing += 1
                continue
            w, h = dims
            if min_res and (w < min_res or h < min_res):
                continue
            if min_long and max(w, h) < min_long:
                continue
        hits.append(r)
    return hits, skipped_missing


# ============================================================ 子命令

def cmd_scan(args):
    records, meta = load_index(args.index)
    records = _dedupe(records)
    prev = meta.get("root")
    root_abs = os.path.abspath(args.directory)
    if prev and prev != root_abs and records:
        print("提示：本台账原本记录的是 %s，本次扫描 %s。"
              "相对路径以各自的扫描目录为基准，混用前请确认。" % (prev, root_abs))

    seen = {(r.get("file_path"), r.get("_size", -1), r.get("_mtime", -1)) for r in records}
    known_paths = {r.get("file_path") for r in records}
    added = 0
    for p in iter_media_files(root_abs, args.recursive):
        rel = os.path.relpath(p, root_abs)
        st = os.stat(p)
        key = (rel, st.st_size, int(st.st_mtime))
        if key in seen:
            continue
        rec = make_record(p, root_abs, allow_probe=not args.no_ffprobe,
                          embed=not args.no_embed, keep_raw_meta=args.keep_raw_meta)
        if rel in known_paths:
            rec["flags"].append("suspect-rename")
        records.append(rec)
        seen.add(key)
        known_paths.add(rel)
        added += 1

    groups = 0
    if not args.no_batch:
        groups = assign_batches(records, args.batch_window)

    cards = load_character_cards(getattr(args, "characters", None))
    shots = load_storyboard(getattr(args, "storyboard", None))
    link = apply_links(records, cards, shots)

    meta["root"] = root_abs
    meta["updated_at"] = _now()
    if cards:
        meta["characters_dir"] = os.path.abspath(args.characters)
    if shots:
        meta["storyboard"] = os.path.abspath(args.storyboard)
    save_index(records, args.index, args.format, meta)

    emb = sum(1 for r in records if r.get("meta_source") == "embedded")
    print("扫描完成：新增 %d 条，台账共 %d 条 → %s" % (added, len(records), args.index))
    print("  创作字段来源：图内元数据 %d · 同源文件 %d · 未提供 %d"
          % (emb,
             sum(1 for r in records if r.get("meta_source") == "sidecar"),
             sum(1 for r in records if r.get("meta_source") == "none")))
    if not args.no_batch:
        batched = sum(1 for r in records if r.get("batch_id"))
        print("  批次 [推断]：%d 组，覆盖 %d 条（同族判定窗口 %d 秒）"
              % (groups, batched, args.batch_window))
    _print_link_report(link, cards, shots)
    leak = sum(1 for r in records if "meta-has-local-path" in (r.get("flags") or []))
    if leak:
        print("  ⚠ %d 条素材的内嵌元数据含本机绝对路径（可能带用户名）—— "
              "对外分享前先看 stats 的隐私提醒。" % leak)


def cmd_query(args):
    records, _ = load_index(args.index)
    records = _dedupe(records)
    if not records:
        print("台账为空或不存在：%s" % args.index)
        return
    hits, skipped = filter_records(records, args)
    print("命中 %d / %d 条：" % (len(hits), len(records)))
    for r in hits:
        res = r.get("resolution") or "未提供"
        marks = []
        if _as_bool(r.get("is_scrap")):
            marks.append("废片")
        if _as_bool(r.get("commercial")):
            marks.append("可商用")
        if r.get("batch_id"):
            marks.append(r["batch_id"] + " [推断]")
        print("  %s | %s | %s | res=%s%s" % (
            r.get("file_path"), r.get("role") or "未提供",
            r.get("purpose") or "未提供", res,
            (" [" + " · ".join(marks) + "]") if marks else ""))
    if skipped:
        print("  另有 %d 条因分辨率未提供被跳过（视频缺 ffprobe 时会出现）。" % skipped)
    if not hits and args.scrap is None and not args.all:
        scrap_n = sum(1 for r in records if _as_bool(r.get("is_scrap")))
        if scrap_n:
            print("  提示：台账里有 %d 条废片，检索默认不显示；要一并看用 --all，只看废片用 --scrap true。"
                  % scrap_n)


SETTABLE = ["role", "scene", "purpose", "prompt", "model", "version",
            "commercial", "is_scrap"]


def cmd_set(args):
    records, meta = load_index(args.index)
    if not records:
        print("台账为空或不存在：%s" % args.index)
        return
    hit, err = _locate(records, args.path)
    if err:
        print("未改动：" + err)
        return

    changed = []
    for f in SETTABLE:
        v = getattr(args, f.replace("-", "_"), None)
        if v is None:
            continue
        if f in ("commercial", "is_scrap"):
            v = _as_bool(v)
        hit[f] = v
        changed.append("%s=%s" % (f, v))
    if args.tag:
        tags = _tags_of(hit)
        for t in args.tag:
            if t not in tags:
                tags.append(t)
                changed.append("+tag:%s" % t)
        hit["tags"] = tags
    if args.clear_tags:
        hit["tags"] = []
        changed.append("清空 tags")
    for f in args.unset or []:
        if f in hit:
            hit[f] = None
            changed.append("清空 %s" % f)

    if not changed:
        print("没有给出要改的字段。可改：%s（另有 --tag / --clear-tags / --unset）"
              % " ".join("--" + f for f in SETTABLE))
        return

    # 人工给的值优先级最高。但 meta_source 描述的是「提示词这类核心字段从哪来」，
    # 只在真的改了 prompt 时才改写 —— 否则补一个 role 就会把
    # 「提示词其实来自图内元数据」这个事实抹掉，stats 的来源分布随之失真。
    if args.prompt is not None:
        hit["meta_source"] = "user"
    hit.setdefault("flags", [])
    if "user-edited" not in hit["flags"]:
        hit["flags"].append("user-edited")
    meta["updated_at"] = _now()
    save_index(records, args.index, args.format, meta)
    print("已更新 %s" % hit.get("file_path"))
    for c in changed:
        print("  " + c)


def _locate(records, path):
    exact = [r for r in records if r.get("file_path") == path]
    if len(exact) == 1:
        return exact[0], None
    by_name = [r for r in records if os.path.basename(r.get("file_path") or "") == path]
    if len(by_name) == 1:
        return by_name[0], None
    sub = [r for r in records if path in (r.get("file_path") or "")]
    if len(sub) == 1:
        return sub[0], None
    if len(sub) > 1:
        return None, "「%s」匹配到 %d 条，不唯一：%s" % (
            path, len(sub), ", ".join((r.get("file_path") or "")[:40] for r in sub[:5]))
    return None, "台账里没有匹配「%s」的记录" % path


def cmd_stats(args):
    records, meta = load_index(args.index)
    records = _dedupe(records)
    if not records:
        print("台账为空或不存在：%s" % args.index)
        return
    total = len(records)
    imgs = sum(1 for r in records if r.get("type") == "image")
    vids = total - imgs
    scrap = [r for r in records if _as_bool(r.get("is_scrap"))]
    comm_yes = sum(1 for r in records if _as_bool(r.get("commercial")) is True)
    comm_no = sum(1 for r in records if _as_bool(r.get("commercial")) is False)

    print("台账：%s" % args.index)
    print("  记录总数     %d" % total)
    print("  图片 / 视频  %d / %d" % (imgs, vids))
    if meta.get("root"):
        print("  扫描根目录   %s" % meta["root"])
    if meta.get("updated_at"):
        print("  最近更新     %s" % meta["updated_at"])

    print("\n素材状态")
    print("  废片         %d（%.1f%%）" % (len(scrap), len(scrap) * 100.0 / total))
    print("  可商用       %d 是 · %d 否 · %d 未提供" % (comm_yes, comm_no, total - comm_yes - comm_no))
    no_res = sum(1 for r in records if not r.get("resolution"))
    if no_res:
        print("  分辨率缺失   %d（视频未装 ffprobe 时会这样）" % no_res)

    print("\n创作字段来源")
    for key, label in (("embedded", "图内元数据"), ("sidecar", "同源文件"),
                       ("user", "人工补录"), ("none", "未提供")):
        n = sum(1 for r in records if r.get("meta_source") == key)
        if n:
            print("  %-10s %d（%.0f%%）" % (label, n, n * 100.0 / total))
    tools = {}
    for r in records:
        if r.get("meta_tool"):
            tools[r["meta_tool"]] = tools.get(r["meta_tool"], 0) + 1
    if tools:
        print("  认出的工具 " + " · ".join("%s %d" % (k, v) for k, v in sorted(tools.items())))
    edited = sum(1 for r in records if "user-edited" in (r.get("flags") or []))
    if edited:
        print("  人工补录过   %d 条（补 role / 用途 / 废片标记等；"
              "上面的提示词来源判定不受影响）" % edited)

    print("\n字段完整度（条越长缺得越多；缺 = 未提供，不代表素材有问题）")
    for f in CREATIVE_FIELDS:
        miss = sum(1 for r in records
                   if r.get(f) in (None, "", []) or (f == "tags" and not _tags_of(r)))
        bar = "▒" * int(round(miss * 20.0 / total)) if total else ""
        print("  %-10s 缺 %-4d %s" % (f, miss, bar))

    print("\n分布（各取前 8）")
    for f, label in (("role", "按角色"), ("model", "按模型"),
                     ("purpose", "按用途"), ("batch_family", "按命名族")):
        cnt = {}
        for r in records:
            k = r.get(f) or "未提供"
            cnt[k] = cnt.get(k, 0) + 1
        top = sorted(cnt.items(), key=lambda x: -x[1])[:8]
        print("  %-8s %s" % (label, " · ".join("%s %d" % (k, v) for k, v in top)))

    batched = [r for r in records if r.get("batch_id")]
    fams = {r["batch_id"] for r in batched}
    print("\n批次 [推断]")
    print("  疑似批次     %d 组，覆盖 %d 条" % (len(fams), len(batched)))
    if args.show_batches and fams:
        for b in sorted(fams):
            items = [r for r in batched if r["batch_id"] == b]
            print("  %-16s %d 条 → %s" % (b, len(items),
                                          ", ".join((r.get("file_path") or "")[:32] for r in items[:4])))

    leaks = [r for r in records if "meta-has-local-path" in (r.get("flags") or [])]
    if leaks:
        print("\n隐私提醒")
        print("  %d 条素材的内嵌元数据含本机绝对路径（可能带用户名 / 目录结构）。" % len(leaks))
        for r in leaks[:5]:
            print("    %s" % r.get("file_path"))
        if len(leaks) > 5:
            print("    …… 另有 %d 条" % (len(leaks) - 5))
        print("  对外分享这些图前，建议先用专门工具剥掉 PNG 文本块。")

    if args.show_fields:
        print("\n全部字段名：")
        print("  创作 " + " ".join(CREATIVE_FIELDS))
        print("  技术 " + " ".join(TECH_FIELDS + ["shot_id"]))
        print("  派生 " + " ".join(DERIVED_FIELDS))

    def flagged(pre):
        return [r for r in records
                if any(f == pre or f.startswith(pre + ":")
                       for f in (r.get("flags") or []))]

    unknown, miss, partial = flagged("unknown-role"), flagged("anchor-miss"), flagged("anchor-partial")
    shot = [r for r in records if r.get("shot_id")]
    if unknown or miss or partial or shot or meta.get("characters_dir"):
        print("\n联动（由 scan --characters / --storyboard 写入）")
        if meta.get("characters_dir"):
            print("  角色卡目录   %s" % meta["characters_dir"])
        if unknown:
            names = sorted({r.get("role") for r in unknown})
            print("  角色不在卡里 %d 条 → %s" % (len(unknown), ", ".join(str(n) for n in names[:6])))
        if miss:
            print("  锚点全未命中 %d 条（提示词里没有角色卡的锚点短语）" % len(miss))
            for r in miss[:5]:
                print("    %s" % r.get("file_path"))
        if partial:
            print("  锚点部分命中 %d 条（改了造型，或提示词被压缩）" % len(partial))
        if shot:
            ids = sorted({r.get("shot_id") for r in shot})
            print("  已接分镜     %d 条素材，覆盖 %d 个镜头" % (len(shot), len(ids)))
        if meta.get("storyboard") and not shot:
            print("  分镜清单里没有与台账文件名匹配的 shot_*")


def _now():
    import datetime
    return datetime.datetime.now().isoformat(timespec="seconds")


# ============================================================ HTML 看板

_HTML_CSS = """
:root{
  --s:#2f7d5d; --e:#b3352f; --c:#4a5a6a; --a:#a8761c;
  --bg:#f7f6f3; --card:#ffffff; --line:#e3e1dc; --ink:#22201d; --dim:#6b6862;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.6 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}
.wrap{max-width:1240px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:17px;font-weight:500;margin:0 0 4px}
.sub{color:var(--dim);font-size:12px;margin-bottom:20px}
.bar{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:18px}
.kv{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:10px 14px;min-width:104px}
.kv b{display:block;font-size:18px;font-weight:500;line-height:1.3}
.kv span{font-size:12px;color:var(--dim)}
.kv.warn b{color:var(--a)}
.kv.bad b{color:var(--e)}
.filters{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:14px;margin-bottom:18px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
select,input[type=search]{font:inherit;padding:6px 10px;border:1px solid var(--line);
  border-radius:8px;background:#fff;color:var(--ink);min-width:132px}
input[type=search]{flex:1;min-width:200px}
.chip{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;
  border:1px solid var(--line);background:#fff;cursor:pointer;font-size:12px;user-select:none}
.chip.on{background:#eef4f0;border-color:#9dc4b3;color:var(--s)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(212px,1fr));gap:14px}
.sk{background:var(--card);border:1px solid var(--line);border-radius:12px;
  overflow:hidden;display:flex;flex-direction:column}
.sk.scrap{border-color:#e5bdb9;background:#fdf8f7}
.th{aspect-ratio:4/3;background:#f0eeea;display:flex;align-items:center;justify-content:center;
  color:var(--dim);font-size:12px;overflow:hidden}
.th img{width:100%;height:100%;object-fit:cover;display:block}
.body{padding:10px 12px 12px;display:flex;flex-direction:column;gap:6px;flex:1}
.name{font-size:12px;color:var(--dim);word-break:break-all}
.rowtag{display:flex;flex-wrap:wrap;gap:4px}
.t{font-size:11px;padding:2px 7px;border-radius:6px;background:#f1efeb;color:var(--c)}
.t.s{background:#eaf3ee;color:var(--s)}
.t.e{background:#fbeceb;color:var(--e)}
.t.a{background:#faf1e0;color:var(--a)}
.prompt{margin-top:auto;font-size:11px;color:var(--dim);max-height:52px;overflow:hidden;
  border-top:1px dashed var(--line);padding-top:6px}
.empty{color:var(--dim);padding:40px 0;text-align:center}
.callout{border-left:3px solid var(--a);background:#fdfaf2;padding:10px 14px;
  border-radius:0 8px 8px 0;font-size:12px;color:var(--dim);margin-top:22px}
"""

_HTML_JS = """
var DATA=[], filtered=[];
function el(id){return document.getElementById(id)}
function uniq(k){var s={};DATA.forEach(function(r){var v=r[k];if(v){s[v]=1}});
  return Object.keys(s).sort()}
function fill(){
  [['fRole','role'],['fModel','model'],['fPurpose','purpose'],['fBatch','batch_family']]
  .forEach(function(p){
    var sel=el(p[0]);uniq(p[1]).forEach(function(v){
      var o=document.createElement('option');o.value=v;o.textContent=v;sel.appendChild(o)})});
}
function match(r){
  if(el('fRole').value && (r.role||'')!==el('fRole').value) return false;
  if(el('fModel').value && (r.model||'')!==el('fModel').value) return false;
  if(el('fPurpose').value && (r.purpose||'')!==el('fPurpose').value) return false;
  if(el('fBatch').value && (r.batch_family||'')!==el('fBatch').value) return false;
  if(el('onlyCommercial').classList.contains('on') && r.commercial!==true) return false;
  if(el('onlyBatch').classList.contains('on') && !r.batch_id) return false;
  if(!el('showScrap').classList.contains('on') && r.is_scrap) return false;
  if(el('onlyScrap').classList.contains('on') && !r.is_scrap) return false;
  var q=el('q').value.trim().toLowerCase();
  if(q){
    var hay=((r.file_path||'')+' '+(r.prompt||'')+' '+(r.role||'')+' '+(r.purpose||'')).toLowerCase();
    if(hay.indexOf(q)<0) return false;
  }
  return true;
}
function badge(r){
  var b=[];
  if(r.is_scrap) b.push('<span class="t e">废片</span>');
  if(r.commercial===true) b.push('<span class="t s">可商用</span>');
  if(r.commercial===false) b.push('<span class="t a">限自用</span>');
  if(r.role) b.push('<span class="t">'+r.role+'</span>');
  if(r.purpose) b.push('<span class="t">'+r.purpose+'</span>');
  if(r.batch_id) b.push('<span class="t a">'+r.batch_id+' 推断</span>');
  if(r.resolution) b.push('<span class="t">'+r.resolution+'</span>');
  (r.tags||[]).slice(0,3).forEach(function(t){b.push('<span class="t">'+t+'</span>')});
  return b.join('');
}
function draw(){
  filtered=DATA.filter(match);
  el('count').textContent=filtered.length+' / '+DATA.length+' 条';
  var g=el('grid');g.innerHTML='';
  if(!filtered.length){g.innerHTML='<div class="empty">没有命中的素材。检索默认不显示废片，需要时打开「含废片」。</div>';return}
  filtered.forEach(function(r){
    var d=document.createElement('div');
    d.className='sk'+(r.is_scrap?' scrap':'');
    var th=r.type==='video'
      ? '<div class="th">VIDEO</div>'
      : '<div class="th"><img loading="lazy" src="'+r._src+'" onerror="this.parentNode.textContent=\\'图不可读\\'"></div>';
    d.innerHTML=th+'<div class="body">'+badge(r)+
      '<div class="name">'+r.file_path+'</div>'+
      (r.prompt?'<div class="prompt">'+r.prompt.replace(/</g,'&lt;')+'</div>':'')+
      '</div>';
    g.appendChild(d);
  });
}
function toggle(id){el(id).classList.toggle('on');draw()}
function reset(){
  ['fRole','fModel','fPurpose','fBatch'].forEach(function(i){el(i).value=''});
  el('q').value='';
  ['onlyCommercial','onlyBatch','showScrap','onlyScrap'].forEach(function(i){el(i).classList.remove('on')});
  draw();
}
function boot(){
  ['fRole','fModel','fPurpose','fBatch'].forEach(function(i){
    el(i).addEventListener('change',draw)});
  el('q').addEventListener('input',draw);
  ['onlyCommercial','onlyBatch','showScrap','onlyScrap'].forEach(function(i){
    el(i).addEventListener('click',function(){toggle(i)})});
  el('reset').addEventListener('click',reset);
  fill();draw();
}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot);
else boot();
"""


def cmd_render(args):
    records, meta = load_index(args.index)
    records = _dedupe(records)
    if not records:
        print("台账为空或不存在：%s" % args.index)
        return
    root = args.root or meta.get("root")
    out_html = os.path.abspath(args.out)
    out_dir = os.path.dirname(out_html)

    payload = []
    missing = 0
    for r in records:
        item = {k: r.get(k) for k in
                ("file_path", "type", "role", "scene", "purpose", "prompt", "model",
                 "is_scrap", "commercial", "resolution", "duration", "batch_id",
                 "batch_family", "meta_source")}
        item["tags"] = _tags_of(r)
        item["is_scrap"] = bool(_as_bool(r.get("is_scrap")))
        item["commercial"] = _as_bool(r.get("commercial"))
        src = ""
        if root:
            abspath = os.path.join(root, r.get("file_path") or "")
            src = os.path.relpath(abspath, out_dir)
        item["_src"] = src
        if root and not os.path.isfile(os.path.join(root, r.get("file_path") or "")):
            missing += 1
        payload.append(item)

    total = len(records)
    scrap = sum(1 for r in records if _as_bool(r.get("is_scrap")))
    comm = sum(1 for r in records if _as_bool(r.get("commercial")) is True)
    no_role = sum(1 for r in records if not r.get("role"))
    batched = sum(1 for r in records if r.get("batch_id"))
    emb = sum(1 for r in records if r.get("meta_source") == "embedded")

    html = []
    html.append("<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\">")
    html.append("<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">")
    html.append("<title>素材台账 · 晓得</title>")
    html.append("<style>" + _HTML_CSS + "</style>\n</head>\n<body>\n<div class=\"wrap\">")
    html.append("<h1>素材台账</h1>")
    html.append("<div class=\"sub\">%s 条素材 · 扫描目录 %s · 更新于 %s</div>"
                % (total, (root or "未记录"), meta.get("updated_at") or "—"))
    html.append("<div class=\"bar\">")
    html.append("<div class=\"kv\"><b>%d</b><span>素材总数</span></div>" % total)
    html.append("<div class=\"kv bad\"><b>%d</b><span>废片</span></div>" % scrap)
    html.append("<div class=\"kv\"><b>%d</b><span>可商用</span></div>" % comm)
    html.append("<div class=\"kv\"><b>%d</b><span>来自图内元数据</span></div>" % emb)
    html.append("<div class=\"kv warn\"><b>%d</b><span>缺角色</span></div>" % no_role)
    html.append("<div class=\"kv\"><b>%d</b><span>已归入批次</span></div>" % batched)
    html.append("</div>")

    html.append("<div class=\"filters\">")
    html.append("<select id=\"fRole\"><option value=\"\">全部角色</option></select>")
    html.append("<select id=\"fModel\"><option value=\"\">全部模型</option></select>")
    html.append("<select id=\"fPurpose\"><option value=\"\">全部用途</option></select>")
    html.append("<select id=\"fBatch\"><option value=\"\">全部命名族</option></select>")
    html.append("<span class=\"chip\" id=\"onlyCommercial\">仅可商用</span>")
    html.append("<span class=\"chip\" id=\"onlyBatch\">仅成批素材</span>")
    html.append("<span class=\"chip\" id=\"showScrap\">含废片</span>")
    html.append("<span class=\"chip\" id=\"onlyScrap\">只看废片</span>")
    html.append("<input type=\"search\" id=\"q\" placeholder=\"搜文件名 / 提示词 / 角色 / 用途……\">")
    html.append("<span class=\"chip\" id=\"reset\">重置</span>")
    html.append("<span class=\"sub\" id=\"count\" style=\"margin:0\"></span>")
    html.append("</div>")

    html.append("<div class=\"grid\" id=\"grid\"></div>")
    html.append("<div class=\"callout\">批次是用「文件名族 + 生成时间邻近」推断出来的，"
                "一律标注「推断」，不等于事实。检索默认不显示废片 —— 点「含废片」可一并查看。</div>")
    html.append("</div>")
    html.append("<script>var DATA=" + json.dumps(payload, ensure_ascii=False) + ";</script>")
    html.append("<script>" + _HTML_JS + "</script>")
    html.append("</body>\n</html>\n")

    with open(out_html, "w", encoding="utf-8") as f:
        f.write("\n".join(html))
    print("看板已写入 %s（%d 条素材）" % (out_html, total))
    if not root:
        print("  提示：台账里没记扫描根目录，缩略图无法定位，看板只显示字段。"
              "改用 --root <扫描目录> 指定。")
    elif missing:
        print("  提示：%d 条素材在磁盘上找不到（已移动或删除），看板上显示为「图不可读」。" % missing)


# ============================================================ CLI

def main():
    parser = argparse.ArgumentParser(description="素材台账 v%s：扫描 / 检索 / 补录 / 体检 / 看板（纯标准库）" % TOOL_VERSION)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="扫描目录建立 / 增量更新台账")
    p_scan.add_argument("directory", help="要扫描的目录")
    p_scan.add_argument("--index", default="ledger.jsonl", help="索引文件路径")
    p_scan.add_argument("--recursive", action="store_true", help="递归子目录")
    p_scan.add_argument("--no-ffprobe", action="store_true", help="跳过 ffprobe 探测视频分辨率 / 时长")
    p_scan.add_argument("--no-embed", action="store_true", help="不从图内元数据挖提示词与参数")
    p_scan.add_argument("--no-batch", action="store_true", help="不做批次推断")
    p_scan.add_argument("--characters", metavar="DIR",
                        help="角色卡目录（晓得·角色档案的产出 char_*.yaml）：校验 role 是否已知，并比对锚点短语是否进了提示词")
    p_scan.add_argument("--storyboard", metavar="PATH",
                        help="分镜产出目录或其 manifest.json（晓得·分镜工）：shot_* 素材自动带上对应镜头的提示词与时长")
    p_scan.add_argument("--batch-window", type=int, default=DEFAULT_BATCH_WINDOW,
                        help="同族判定窗口（秒），默认 %d" % DEFAULT_BATCH_WINDOW)
    p_scan.add_argument("--keep-raw-meta", action="store_true",
                        help="把认不出的文本块原文也存进台账（截断 4000 字符）")
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
    p_q.add_argument("--batch", help="按批次或命名族过滤（[推断]）")
    p_q.add_argument("--shot", help="按分镜镜头号过滤（如 shot_001）")
    p_q.add_argument("--grep-prompt", help="在提示词全文里搜关键词")
    p_q.add_argument("--scrap", help="是否废片：true / false")
    p_q.add_argument("--all", action="store_true", help="不按废片过滤（默认排除废片）")
    p_q.add_argument("--commercial", help="是否可商用：true / false")
    p_q.add_argument("--min-res", help="最小分辨率，宽高均 >= 此值")
    p_q.add_argument("--min-long-side", help="最小长边，取宽高中的大者比较")
    p_q.set_defaults(func=cmd_query)

    p_s = sub.add_parser("set", help="人工补字段 / 标废片 / 改可商用")
    p_s.add_argument("--index", default="ledger.jsonl")
    p_s.add_argument("--path", required=True, help="文件路径（精确、文件名或唯一子串）")
    p_s.add_argument("--role")
    p_s.add_argument("--scene")
    p_s.add_argument("--purpose")
    p_s.add_argument("--prompt")
    p_s.add_argument("--model")
    p_s.add_argument("--version")
    p_s.add_argument("--commercial", help="true / false")
    p_s.add_argument("--is-scrap", dest="is_scrap", help="true / false")
    p_s.add_argument("--tag", action="append", help="追加标签，可多次")
    p_s.add_argument("--clear-tags", action="store_true", help="清空全部标签")
    p_s.add_argument("--unset", action="append", help="清空某字段，可多次")
    p_s.add_argument("--format", default="jsonl", choices=["jsonl", "csv"])
    p_s.set_defaults(func=cmd_set)

    p_st = sub.add_parser("stats", help="台账体检")
    p_st.add_argument("--index", default="ledger.jsonl")
    p_st.add_argument("--show-batches", action="store_true", help="逐组列出推断批次")
    p_st.add_argument("--show-fields", action="store_true", help="列出全部字段名")
    p_st.set_defaults(func=cmd_stats)

    p_r = sub.add_parser("render", help="渲染单文件 HTML 看板")
    p_r.add_argument("--index", default="ledger.jsonl")
    p_r.add_argument("--out", default="ledger.html", help="输出的 HTML 路径")
    p_r.add_argument("--root", help="素材根目录（台账里没记录时用它定位缩略图）")
    p_r.set_defaults(func=cmd_render)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
