#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
split_shots.py —— 晓得·分镜工 配套脚本（零第三方依赖，只调用 ffmpeg / ffprobe）

功能：
  1. 检测镜头切换点（scene change），阈值可调（默认 0.3）
  2. 按切换点把视频切成若干镜头片段 shot_NNN.mp4
  3. 每个镜头抽取首帧 shot_NNN_firstframe.png
  4. 输出清单 shots/manifest.json（起止时间、时长、首帧/片段路径）

用法：
  python scripts/split_shots.py <视频路径> --output-dir shots --scene-thresh 0.3
  python scripts/split_shots.py input.mp4 --output-dir shots --no-clips   # 只抽首帧不出片段

依赖：ffmpeg + ffprobe 必须在 PATH。缺失时给出清晰报错与安装提示，直接退出。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys


def die(msg):
    print("错误：" + msg, file=sys.stderr)
    sys.exit(1)


def ensure_ffmpeg():
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            die(
                "未找到 %s。请先安装 ffmpeg：\n"
                "  macOS:    brew install ffmpeg\n"
                "  Ubuntu:   sudo apt install ffmpeg\n"
                "  Windows:  scoop install ffmpeg   (或从 https://ffmpeg.org 下载并加入 PATH)\n"
                "安装后重新运行本脚本。" % tool
            )


def get_duration(video):
    """用 ffprobe 取视频总时长（秒，浮点）。"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video,
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()
        return float(out)
    except (subprocess.CalledProcessError, ValueError):
        return None


def detect_cuts(video, thresh):
    """跑一遍 select 过滤器，解析 showinfo 里的 pts_time，返回切换点时间列表（秒）。"""
    cmd = [
        "ffmpeg", "-i", video,
        "-filter:v", "select='gt(scene,%s)',showinfo" % thresh,
        "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    cuts = []
    for line in proc.stderr.splitlines():
        if "pts_time:" in line:
            # 形如：... pts_time:2.340000 ...
            try:
                token = line.split("pts_time:")[1].split()[0]
                cuts.append(float(token))
            except (IndexError, ValueError):
                continue
    return cuts


def build_segments(cuts, duration):
    """把切换点拼成 [start, end] 片段列表。

    返回 `(segs, basis, source)`：
      - `basis`：实际用于切分的总时长（ffprobe 取不到时按切换点推断）
      - `source`：`'ffprobe'`（实测）或 `'inferred'`（推断）—— R1 要求推断值必须
        可辨识，不得与实测值同形输出（原实现把推断值直接当实测值写进 manifest）。
    """
    if not duration or duration <= 0:
        basis, source = ((cuts[-1] + 5.0) if cuts else 10.0), "inferred"
    else:
        basis, source = duration, "ffprobe"
    bounds = [0.0] + cuts + [basis]
    # 去重并排序，防止浮点抖动导致反向区间
    cleaned = []
    for b in bounds:
        if not cleaned or b > cleaned[-1] + 1e-3:
            cleaned.append(b)
    if cleaned[0] != 0.0:
        cleaned.insert(0, 0.0)
    segs = []
    for i in range(len(cleaned) - 1):
        segs.append((cleaned[i], cleaned[i + 1]))
    return segs, basis, source


def extract_first_frame(video, start, out_path):
    """在 start 处抽一帧（首帧）。"""
    cmd = [
        "ffmpeg", "-ss", "%.4f" % start, "-i", video,
        "-frames:v", "1", "-q:v", "2", "-y", out_path,
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=False)


def extract_clip(video, start, end, out_path):
    """切出 [start, end) 片段，重新编码保证边界干净。

    返回 `(ok, err)`。原实现 `check=False` 且不看返回值，失败只落 `clip=null`
    而**没有任何提示**（R1 不允许静默失败）—— 用户可能在不知情下拿到空片段目录。
    """
    dur = max(end - start, 0.1)
    cmd = [
        "ffmpeg", "-ss", "%.4f" % start, "-i", video,
        "-t", "%.4f" % dur,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "aac", "-y", out_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()
        return False, ("ffmpeg exit %d%s" % (proc.returncode,
                                             ("：" + tail[-1][:160]) if tail else ""))
    if not (os.path.isfile(out_path) and os.path.getsize(out_path) > 0):
        return False, "ffmpeg 返回 0 但产物为空"
    return True, None


def main():
    parser = argparse.ArgumentParser(description="白模视频切镜 + 抽首帧")
    parser.add_argument("video", help="输入视频路径（白模/灰模 mp4）")
    parser.add_argument("--output-dir", default="shots", help="输出目录（默认 shots）")
    parser.add_argument("--scene-thresh", type=float, default=0.3,
                        help="镜头切换检测阈值，默认 0.3（越大越不敏感）")
    parser.add_argument("--no-clips", action="store_true", help="只抽首帧，不产出镜头片段")
    args = parser.parse_args()

    if not os.path.isfile(args.video):
        die("输入视频不存在：%s" % args.video)

    ensure_ffmpeg()

    out_dir = args.output_dir
    os.makedirs(out_dir, exist_ok=True)

    print("正在读取视频信息 ...")
    duration = get_duration(args.video)
    if duration is None:
        print("警告：无法用 ffprobe 取得时长，将按切换点推断。", file=sys.stderr)

    print("正在检测镜头切换点（阈值 %.2f）..." % args.scene_thresh)
    cuts = detect_cuts(args.video, args.scene_thresh)
    segments, basis, duration_source = build_segments(cuts, duration)

    manifest = {
        "source": os.path.abspath(args.video),
        "scene_thresh": args.scene_thresh,
        "duration": duration,                      # ffprobe 实测值；取不到为 null
        "duration_source": duration_source,        # 'ffprobe' | 'inferred'（R1）
        "duration_used": round(basis, 3),          # 实际用于切分的总时长
        "shot_count": len(segments),
        "shots": [],
    }

    for idx, (start, end) in enumerate(segments, start=1):
        tag = "shot_%03d" % idx
        firstframe = os.path.join(out_dir, tag + "_firstframe.png")
        clip = os.path.join(out_dir, tag + ".mp4")

        print("  处理 %s：%.2f - %.2f 秒" % (tag, start, end))
        extract_first_frame(args.video, start, firstframe)
        ok_frame = os.path.isfile(firstframe) and os.path.getsize(firstframe) > 0
        clip_path = None
        clip_error = None
        if not args.no_clips:
            ok_clip, clip_error = extract_clip(args.video, start, end, clip)
            if ok_clip:
                clip_path = clip

        manifest["shots"].append({
            "index": idx,
            "tag": tag,
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(end - start, 3),
            "duration_source": duration_source,
            "firstframe": firstframe if ok_frame else None,
            "clip": clip_path,
            "clip_error": clip_error,
        })

    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("完成：共 %d 个镜头。清单：%s" % (len(segments), manifest_path))
    misses = [s["tag"] for s in manifest["shots"] if not s["firstframe"]]
    if misses:
        print("警告：以下镜头首帧抽取失败，请人工核对：%s" % ", ".join(misses), file=sys.stderr)
    if not args.no_clips:
        clip_misses = [s["tag"] for s in manifest["shots"] if not s["clip"]]
        if clip_misses:
            print("警告：以下镜头片段抽取失败，请人工核对：%s" % ", ".join(clip_misses),
                  file=sys.stderr)


if __name__ == "__main__":
    main()
