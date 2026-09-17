#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图标规格体检 · 把 avatars/ 下不合规的图缩到 512×512 / 500KB 以内

用法
------------------------------------------------------------------
    python3 scripts/shrink-icons.py            体检 + 出预览副本到 avatars/.shrunk/
    python3 scripts/shrink-icons.py --apply    替换原图（原图先备份进 avatars/.originals/）

为什么需要它：平台要求图标 512×512、单张 ≤500KB。尺寸超了体积必然超
（2048×2048 的插画轻易上 3MB），而**缩到 512 就够了，不用降画质** ——
实测 2048×2048/3.8MB 的图缩完 334KB，仍是全彩 PNG。

默认只体检、只写副本，不动你的原图。要真替换得显式加 --apply。
"""
import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AVATARS = os.path.join(ROOT, 'avatars')
PREVIEW = os.path.join(AVATARS, '.shrunk')
BACKUP = os.path.join(AVATARS, '.originals')

SIDE = 512
MAX_BYTES = 500 * 1024
EXT = ('.png', '.jpg', '.jpeg', '.webp')

try:
    from PIL import Image
except ImportError:
    print('缺 Pillow。装一个：')
    print('  ~/.workbuddy/binaries/python/envs/default/bin/pip install -i '
          'https://pypi.tuna.tsinghua.edu.cn/simple Pillow')
    sys.exit(1)


def collect():
    out = []
    for base, dirs, files in os.walk(AVATARS):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            if f.startswith('.') or not f.lower().endswith(EXT):
                continue
            out.append(os.path.join(base, f))
    return sorted(out)


def shrink(src, dst):
    """缩到 512×512 并压到 500KB 以内。返回 (宽, 高, 字节数, 做法)。"""
    im = Image.open(src)
    note = []

    if im.size != (SIDE, SIDE):
        keep_alpha = im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info)
        im = im.convert('RGBA' if keep_alpha else 'RGB')
        im = im.resize((SIDE, SIDE), Image.LANCZOS)
        note.append('%d×%d→512' % Image.open(src).size)

    ext = os.path.splitext(dst)[1].lower()
    if ext in ('.jpg', '.jpeg'):
        im.convert('RGB').save(dst, 'JPEG', quality=90, optimize=True, progressive=True)
    else:
        im.save(dst, 'PNG', optimize=True, compress_level=9)
        if os.path.getsize(dst) > MAX_BYTES:
            im.convert('P', palette=Image.ADAPTIVE, colors=256).save(
                dst, 'PNG', optimize=True)
            note.append('降为 256 色')

    return im.size[0], im.size[1], os.path.getsize(dst), '，'.join(note) or '仅压缩'


def main():
    ap = argparse.ArgumentParser(description='图标规格体检')
    ap.add_argument('--apply', action='store_true', help='替换原图（先备份到 avatars/.originals/）')
    args = ap.parse_args()

    files = collect()
    bad = []
    for p in files:
        try:
            im = Image.open(p)
        except Exception:
            print('  ! 读不了：%s' % os.path.relpath(p, ROOT))
            continue
        size = os.path.getsize(p)
        if im.size != (SIDE, SIDE) or size > MAX_BYTES:
            bad.append((p, im.size, size))

    print('avatars/ 下共 %d 张图，其中 %d 张不合规（需 512×512、≤500KB）' % (len(files), len(bad)))
    if not bad:
        print('全部合规。')
        return 0

    print('')
    print('  %-46s %-12s %9s  →  %9s  %s' % ('文件', '当前尺寸', '当前体积', '处理后', '做法'))
    print('  ' + '─' * 96)

    todo = []
    for p, size_wh, nbytes in bad:
        rel = os.path.relpath(p, ROOT)
        dst = p if args.apply else os.path.join(PREVIEW, os.path.basename(p))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if args.apply:
            os.makedirs(BACKUP, exist_ok=True)
            bak = os.path.join(BACKUP, os.path.basename(p))
            if not os.path.exists(bak):
                shutil.copy2(p, bak)
        w, h, new_bytes, note = shrink(p, dst)
        todo.append((rel, w, h, new_bytes, note))
        print('  %-46s %-12s %7.1fKB  →  %7.1fKB  %s'
              % (rel, '%d×%d' % size_wh, nbytes / 1024, new_bytes / 1024, note))

    print('')
    if args.apply:
        print('已替换 %d 张，原图备份在 avatars/.originals/（备份目录被构建忽略，不会进包）。' % len(todo))
        print('接着跑一次 pnpm build 复验。')
    else:
        print('预览副本已写到 avatars/.shrunk/ —— 原图一张没动。')
        print('确认效果没问题，加 --apply 替换：')
        print('  python3 scripts/shrink-icons.py --apply')
    return 0


if __name__ == '__main__':
    sys.exit(main())
