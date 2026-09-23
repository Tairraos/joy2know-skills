#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
晓得先生 · 头像生成器（零依赖，纯标准库）

设计：深蓝底 + 白色圆角面板 + 三条左对齐横条
含义：第一条粗横条 = 结论先行；下方两条递细横条 = 分层展开。
颜色与形状可用下方常量调整，改完直接重跑即可。
"""

import zlib
import struct
import sys

# ---------- 可调参数 ----------
W = H = 512
BG = (30, 64, 175)        # #1E40AF 深蓝
FG = (255, 255, 255)      # 白

PANEL = dict(cx=256, cy=256, hw=148, hh=148, r=68)
LEFT = 156                # 三条横条的左边缘（左对齐）
BARS = [
    dict(cy=196, hw=100, hh=18, r=18),   # 结论条：最粗
    dict(cy=268, hw=100, hh=11, r=11),
    dict(cy=316, hw=66,  hh=11, r=11),   # 最窄，形成视觉节奏
]
# ------------------------------


def coverage(x, y, cx, cy, hw, hh, r):
    """圆角矩形的抗锯齿覆盖率，返回 0.0~1.0。"""
    dx = abs(x - cx) - (hw - r)
    dy = abs(y - cy) - (hh - r)
    if dx < 0:
        dx = 0.0
    if dy < 0:
        dy = 0.0
    d = (dx * dx + dy * dy) ** 0.5 - r
    c = 0.5 - d
    if c < 0.0:
        return 0.0
    if c > 1.0:
        return 1.0
    return c


def build_pixels():
    panel = (PANEL["cx"], PANEL["cy"], PANEL["hw"], PANEL["hh"], PANEL["r"])
    bars = []
    for b in BARS:
        cx = LEFT + b["hw"]
        bars.append((cx, b["cy"], b["hw"], b["hh"], b["r"]))

    raw = bytearray()
    for y in range(H):
        raw.append(0)  # PNG filter type 0 (None)
        yc = y + 0.5
        for x in range(W):
            xc = x + 0.5
            r0, g0, b0 = BG
            a = coverage(xc, yc, *panel)
            if a > 0.0:
                r0 = r0 * (1 - a) + FG[0] * a
                g0 = g0 * (1 - a) + FG[1] * a
                b0 = b0 * (1 - a) + FG[2] * a
            for (cx, cy, hw, hh, rr) in bars:
                ab = coverage(xc, yc, cx, cy, hw, hh, rr)
                if ab > 0.0:
                    r0 = r0 * (1 - ab) + BG[0] * ab
                    g0 = g0 * (1 - ab) + BG[1] * ab
                    b0 = b0 * (1 - ab) + BG[2] * ab
            raw.append(int(r0 + 0.5))
            raw.append(int(g0 + 0.5))
            raw.append(int(b0 + 0.5))
    return bytes(raw)


def png_chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def write_png(path, raw):
    out = bytearray(b"\x89PNG\r\n\x1a\n")
    out += png_chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    out += png_chunk(b"IDAT", zlib.compress(raw, 9))
    out += png_chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(bytes(out))
    return len(out)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "expert.png"
    size = write_png(target, build_pixels())
    print(f"已生成 {target}  尺寸 {W}x{H}  体积 {size/1024:.1f} KB")
