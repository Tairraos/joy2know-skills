#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crop-avatar.py —— 把「3/4 比例 + 上下留白」的生成图裁成干净的 512×512 头像。

**为什么需要它**：WorkBuddy 生成的图**右下角带水印**。
所以先生成 3/4 竖版图、提示词要求「上下留白、中间矩形区域画头像」，
水印就会落在下方空白区 —— 居中裁出中间方形时它一起被切掉。

用法：
    python3 crop-avatar.py <输入图> <输出.png> [--side-ratio 1.0] [--no-resize]

    --side-ratio  方形边长占图宽的比例（默认 1.0 = 整宽）。缩小可再避开边缘。
    --no-resize   不缩到 512（只裁切，用于先看效果）

退出码：0 成功 / 1 处理失败 / 2 用法错

依赖：优先 Pillow；没有则退化用 macOS 自带 `sips`；两者都没有则报错并给安装提示。
"""

import argparse
import os
import shutil
import subprocess
import sys

TARGET = 512
MAX_BYTES = 500 * 1024          # 平台口径：头像 ≤500KB


def have_pil():
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def crop_with_pil(src, dst, side_ratio, resize):
    from PIL import Image
    im = Image.open(src).convert("RGBA") if src.lower().endswith(".png") else Image.open(src).convert("RGB")
    w, h = im.size
    side = int(min(w, h) * side_ratio)
    left = (w - side) // 2
    top = (h - side) // 2                      # ★ 居中：上下留白各占一半，水印在下留白里被切掉
    im2 = im.crop((left, top, left + side, top + side))
    if resize:
        im2 = im2.resize((TARGET, TARGET), Image.LANCZOS)
    im2.save(dst)
    return im2.size


def crop_with_sips(src, dst, side, resize):
    """退化路径：macOS 自带 sips。居中裁切 → 缩放。"""
    tmp = dst + ".crop.png"
    subprocess.run(["sips", "--cropToHeightWidth", str(side), str(side), src, "--out", tmp],
                   check=True, capture_output=True)
    if resize:
        subprocess.run(["sips", "--resampleHeightWidth", str(TARGET), str(TARGET), tmp, "--out", dst],
                       check=True, capture_output=True)
        os.remove(tmp)
    else:
        os.replace(tmp, dst)
    return size_of(dst)


def size_of(p):
    from struct import unpack
    with open(p, "rb") as f:
        head = f.read(33)
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return unpack(">II", head[16:24])
    return (0, 0)   # 非 PNG 不解析（sips 路径下默认输出 png）


def do_crop(src, dst, side_ratio, resize):
    if not os.path.isfile(src):
        print("用法错：找不到输入图 %s" % src, file=sys.stderr)
        return 2
    if have_pil():
        try:
            wh = crop_with_pil(src, dst, side_ratio, resize)
            return 0, wh
        except Exception as e:                       # noqa: BLE001
            print("Pillow 处理失败（%s），尝试 sips…" % e)
    if shutil.which("sips"):
        # sips 只支持整数边长，先按宽度算
        try:
            from struct import unpack
            with open(src, "rb") as f:
                head = f.read(33)
            w, h = unpack(">II", head[16:24]) if head[:8] == b"\x89PNG\r\n\x1a\n" else (0, 0)
            if not w:
                print("sips 路径只支持 PNG 输入，请先转成 PNG。", file=sys.stderr)
                return 1
            side = int(min(w, h) * side_ratio)
            wh = crop_with_sips(src, dst, side, resize)
            return 0, wh
        except Exception as e:                       # noqa: BLE001
            print("sips 处理失败：%s" % e, file=sys.stderr)
            return 1
    print("没有可用的图像处理工具。二选一：\n"
          "  ① 装 Pillow：pip install Pillow\n"
          "  ② 在 macOS 上用系统自带的 sips（需先把输入转成 PNG）", file=sys.stderr)
    return 1


def report(dst):
    ok = True
    wh = size_of(dst)
    size = os.path.getsize(dst)
    print("\n输出 %s" % dst)
    print("  尺寸 %d×%d" % wh)
    if wh != (TARGET, TARGET):
        print("  ⚠️ 尺寸不是 %d×%d —— 检查是否漏了缩放" % (TARGET, TARGET)); ok = False
    print("  体积 %.1f KB（上限 500KB）" % (size / 1024))
    if size > MAX_BYTES:
        print("  ⚠️ 超过 500KB，平台会拒"); ok = False
    print("\n请**眼看一遍**：头像若被切到下巴或额头，说明生成时上下留白不够 ——\n"
          "  回去重新生成，不要硬裁（可加 --side-ratio 0.9 再试，但根因是提示词）。")
    return ok


# ─────────────────────────── 反向自检 ───────────────────────────

def selftest():
    import tempfile
    if not have_pil():
        print("跳过自检：本机没有 Pillow（自检需要它来造样本）")
        return 0
    from PIL import Image
    passed = failed = 0
    with tempfile.TemporaryDirectory() as td:
        # 造一张 768×1024（3:4）的图：中间方形是红色头像区，上下留白是白色，右下角画一个"水印"黑块
        im = Image.new("RGB", (768, 1024), (255, 255, 255))
        for y in range(128, 896):
            for x in range(0, 768):
                im.putpixel((x, y), (200, 30, 30))
        # 右下角水印（故意画在下方留白里）
        for y in range(950, 1010):
            for x in range(600, 760):
                im.putpixel((x, y), (0, 0, 0))
        src = os.path.join(td, "src.png")
        im.save(src)

        dst = os.path.join(td, "out.png")
        code, wh = do_crop(src, dst, 1.0, True)
        # ① 尺寸是 512×512
        if code == 0 and wh == (TARGET, TARGET):
            passed += 1; print("  [PASS] 裁切并缩放到 512×512")
        else:
            failed += 1; print("  [FAIL] 尺寸不对：%r code=%r" % (wh, code))
        # ② 水印被切掉了（输出图里不应出现近黑色像素）
        out = Image.open(dst).convert("RGB")
        dark = 0
        for y in range(0, TARGET, 8):
            for x in range(0, TARGET, 8):
                r, g, b = out.getpixel((x, y))
                if r < 60 and g < 60 and b < 60:
                    dark += 1
        if dark == 0:
            passed += 1; print("  [PASS] 右下角水印已被裁掉（输出无深色块）")
        else:
            failed += 1; print("  [FAIL] 输出里仍有深色像素 %d 个 —— 水印没切干净" % dark)
        # ③ 中间区域确实是头像（红色占多数）
        red = 0
        for y in range(60, TARGET - 60, 16):
            for x in range(60, TARGET - 60, 16):
                r, g, b = out.getpixel((x, y))
                if r > 150 and g < 80:
                    red += 1
        if red > 0:
            passed += 1; print("  [PASS] 中间头像区被保留（红 %d）" % red)
        else:
            failed += 1; print("  [FAIL] 中间头像区没保留")

        # ④ 反向对照：不裁切（--no-resize 且整图）时，水印**应当**仍在
        dst2 = os.path.join(td, "whole.png")
        im.resize((512, 512), Image.LANCZOS).save(dst2)
        o2 = Image.open(dst2).convert("RGB")
        dark2 = any(o2.getpixel((x, y))[0] < 60 and o2.getpixel((x, y))[1] < 60
                    for y in range(0, 512, 6) for x in range(0, 512, 6))
        if dark2:
            passed += 1; print("  [PASS] 对照：不清洗时水印确实存在（证明上面的检查有判别力）")
        else:
            failed += 1; print("  [FAIL] 对照样本里都没水印 —— 上面的检查可能是橡皮章")

    print("\n反向自检：%d/%d 通过" % (passed, passed + failed))
    return 0 if not failed else 1


def main():
    ap = argparse.ArgumentParser(description="把 3/4 生成图裁成 512×512 头像")
    ap.add_argument("src", nargs="?", help="输入图")
    ap.add_argument("dst", nargs="?", help="输出 png")
    ap.add_argument("--side-ratio", type=float, default=1.0, help="方形边长占图宽比例（默认 1.0）")
    ap.add_argument("--no-resize", action="store_true", help="只裁切不缩到 512")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.src or not a.dst:
        ap.print_help(); return 2
    if not (0.2 <= a.side_ratio <= 1.0):
        print("用法错：--side-ratio 要在 0.2~1.0", file=sys.stderr); return 2
    r = do_crop(a.src, a.dst, a.side_ratio, not a.no_resize)
    if isinstance(r, tuple) and r[0] == 0:
        return 0 if report(a.dst) else 0
    return r if isinstance(r, int) else 1


if __name__ == "__main__":
    sys.exit(main())
