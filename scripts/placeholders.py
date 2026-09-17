#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""晓得 / joy2know · 头像占位图生成器

用法
------------------------------------------------------------------
    python3 scripts/placeholders.py --check     只报状态：缺哪些、哪些还是占位图
    python3 scripts/placeholders.py             补齐缺失的（绝不覆盖已有文件）
    python3 scripts/placeholders.py --redo      重画台账里的占位图（真图不动）
    python3 scripts/placeholders.py --force     连真图一起覆盖（危险，慎用）
    python3 scripts/placeholders.py --plain     画纯图形占位（不印名字）

默认只补「缺失」的文件，一张已有文件都不动 —— 你换好的真图不会被脚本碰。
每次生成会把 sha1 记进 avatars/.placeholders.json，所以 --check 能准确说出
「还剩几张是占位图」，替换是覆盖同名文件，不靠文件名猜。

三类图标（与 scripts/build.mjs 的约定严格一致）
------------------------------------------------------------------
    avatars/<技能名>.png              技能图标（后台发布技能时要用，不进 zip）
    avatars/<包名>.png                专家 / 专家团自身图标（必填，缺了上传失败）
    avatars/<包名>/<文件名>.png        专家团成员图标（文件名取自 plugin.json 的 members[].avatar）

占位图规格：512×512 PNG，浅灰相框 + 太阳 + 山形，底部印「谁 · 待替换」。
有 Pillow 就印名字，没装则自动回退成纯图形版 —— 功能不依赖第三方库。

设计意图：占位图不是给用户看的，是给**做图的人**看的。
文件名只说得出 polish-lead.png，图上的「闻山 · 主理人·总编审」才说得清该画谁。
"""
import argparse
import hashlib
import json
import os
import re
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKGS = os.path.join(ROOT, 'packages')
AVATARS = os.path.join(ROOT, 'avatars')
# 记下「哪些是我画的占位图」。.-- 开头，build.mjs 的成员计数会跳过它。
MANIFEST = os.path.join(AVATARS, '.placeholders.json')

EXT = ['.png', '.jpg', '.jpeg', '.webp']
SIZE = 512
# 台账没记到的图，退回按体积判断：占位图是几 KB 的纯图形，真图都在 200KB 以上。
PLACEHOLDER_MAX_BYTES = 40 * 1024

try:
    from PIL import Image, ImageDraw, ImageFont
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

# ---- 配色（浅灰一套，一眼认得出是「暂无图片」）----
C_BG = (232, 232, 232)
C_FRAME = (176, 176, 176)
C_PANEL = (250, 250, 250)
C_GLYPH = (168, 168, 168)
C_TITLE = (108, 108, 108)
C_SUB = (152, 152, 152)

FONT_CANDIDATES = [
    '/System/Library/Fonts/PingFang.ttc',
    '/System/Library/Fonts/Hiragino Sans GB.ttc',
    '/System/Library/Fonts/STHeiti Medium.ttc',
    '/Library/Fonts/Arial Unicode.ttf',
    '/System/Library/Fonts/Supplemental/Songti.ttc',
]


# ============================================================
#  需求扫描：仓库里到底需要哪些图
# ============================================================
def frontmatter(path):
    """只取 frontmatter 里的单行标量，够读 display_name 用。"""
    try:
        text = open(path, encoding='utf-8').read()
    except OSError:
        return {}
    m = re.match(r'^---\r?\n(.*?)\r?\n---', text, re.S)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).split('\n'):
        mm = re.match(r'^([A-Za-z_][\w-]*):[ \t]*(.*)$', line)
        if mm:
            fm[mm.group(1)] = mm.group(2).strip().strip('"\'')
    return fm


def scan():
    """返回 [(类别, 目标路径, 主标题, 副标题), ...]，覆盖仓库全部三类图标。"""
    items = []
    if not os.path.isdir(PKGS):
        return items
    for name in sorted(os.listdir(PKGS)):
        pkg = os.path.join(PKGS, name)
        if not os.path.isdir(pkg):
            continue
        pj = os.path.join(pkg, '.codebuddy-plugin', 'plugin.json')

        if os.path.exists(pj):
            with open(pj, encoding='utf-8') as f:
                conf = json.load(f)
            is_team = conf.get('expertType') == 'team'
            label = '专家团自身' if is_team else '专家自身'
            prof = (conf.get('profession') or {}).get('zh') or name
            items.append(('own', os.path.join(AVATARS, name + '.png'),
                          prof, '%s · 待替换' % label))
            for m in (conf.get('members') or []):
                fn = os.path.basename(m.get('avatar') or '')
                if not fn:
                    continue
                mname = (m.get('name') or {}).get('zh') or m.get('id', '')
                mprof = (m.get('profession') or {}).get('zh') or ''
                sub = '%s · 待替换' % mprof if mprof else '团队成员 · 待替换'
                items.append(('member', os.path.join(AVATARS, name, fn), mname, sub))
        elif os.path.exists(os.path.join(pkg, 'SKILL.md')):
            fm = frontmatter(os.path.join(pkg, 'SKILL.md'))
            title = fm.get('display_name') or name
            items.append(('skill', os.path.join(AVATARS, name + '.png'),
                          title, '技能图标 · 待替换'))
    return items


def existing(base_no_ext):
    """按任意图片后缀找已存在的文件 —— 和 build.mjs 的查找口径一致。"""
    for e in EXT:
        if os.path.exists(base_no_ext + e):
            return base_no_ext + e
    return None


def file_sha1(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 16), b''):
            h.update(block)
    return h.hexdigest()


def load_manifest():
    """占位图台账：{相对路径: 生成时的 sha1}。

    记哈希是为了能准确回答「这张换了没有」—— 替换是覆盖同名文件，
    光看文件在不在没用，得看内容还是不是脚本画的那一张。
    """
    try:
        with open(MANIFEST, encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    return {}


def save_manifest(entries):
    merged = load_manifest()
    merged.update(entries)
    os.makedirs(AVATARS, exist_ok=True)
    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(dict(sorted(merged.items())), f, ensure_ascii=False, indent=2)
        f.write('\n')
    return merged


def manifest_report(items):
    """返回 (还是占位图, 已换成真图)。

    台账里的按 sha1 比 —— 替换是覆盖同名文件，光看文件在不在没用。
    **台账没记到的**（早期手工放进去的、或换了后缀的）以前会被直接跳过，
    导致「缺 + 占位 + 真图」三个数字加起来不等于总数，看着像少算。
    退回按体积判即可：占位图是几 KB 的纯图形，真图都在 200KB 以上，40KB 分界很宽。
    """
    marks = load_manifest()
    still, replaced = [], []
    for it in items:
        rel = os.path.relpath(it[1], ROOT)
        found = existing(os.path.splitext(it[1])[0])
        if not found:
            continue          # 文件都没有，归「缺图」管，不在这里报
        if rel in marks:
            if file_sha1(found) == marks[rel]:
                still.append(it)
            else:
                replaced.append(it)
        elif os.path.getsize(found) <= PLACEHOLDER_MAX_BYTES:
            still.append(it)  # 没入台账，但明显还是占位图
        else:
            replaced.append(it)
    return still, replaced


# ============================================================
#  画图 · 有 Pillow（能印名字）
# ============================================================
def load_font(size, bold=False):
    for path in FONT_CANDIDATES:
        if not os.path.exists(path):
            continue
        for idx in ((1, 0) if bold else (0, 1)):
            try:
                return ImageFont.truetype(path, size, index=idx)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size)
    except Exception:
        return ImageFont.load_default()


def fit_font(draw, text, start, limit, bold):
    """标题过长时自动缩字号，避免贴边。"""
    size = start
    while size > 14:
        f = load_font(size, bold)
        try:
            if draw.textlength(text, font=f) <= limit:
                return f
        except Exception:
            return f
        size -= 2
    return load_font(size, bold)


def draw_pillow(path, title, subtitle):
    img = Image.new('RGB', (SIZE, SIZE), C_BG)
    d = ImageDraw.Draw(img)

    cx, cy = SIZE // 2, 210
    d.rounded_rectangle([cx - 166, cy - 124, cx + 166, cy + 124], radius=24, fill=C_FRAME)
    d.rounded_rectangle([cx - 156, cy - 114, cx + 156, cy + 114], radius=19, fill=C_PANEL)

    sx, sy, sr = cx - 52, cy - 44, 24
    d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=C_GLYPH)

    base = cy + 90
    d.polygon([(cx - 112, base), (cx - 26, base - 112), (cx + 60, base)], fill=C_GLYPH)
    d.polygon([(cx + 2, base), (cx + 72, base - 86), (cx + 142, base)], fill=C_GLYPH)

    f1 = fit_font(d, title, 26, 452, True)
    f2 = fit_font(d, subtitle, 19, 452, False)
    d.text((cx, 390), title, font=f1, fill=C_TITLE, anchor='mm')
    d.text((cx, 432), subtitle, font=f2, fill=C_SUB, anchor='mm')

    img.save(path, 'PNG', optimize=True)
    return os.path.getsize(path)


# ============================================================
#  画图 · 没 Pillow（纯标准库，只画图形）
# ============================================================
FRAME_OUT = dict(cx=256, cy=256, hw=178, hh=140, r=26)
FRAME_IN = dict(cx=256, cy=256, hw=168, hh=130, r=20)
SUN = dict(cx=196, cy=206, r=26)
M1 = [(150, 356), (248, 216), (346, 356)]
M2 = [(268, 356), (352, 246), (436, 356)]


def _rounded(x, y, cx, cy, hw, hh, r):
    dx = max(abs(x - cx) - (hw - r), 0.0)
    dy = max(abs(y - cy) - (hh - r), 0.0)
    return min(max(0.5 - ((dx * dx + dy * dy) ** 0.5 - r), 0.0), 1.0)


def _circle(x, y, cx, cy, r):
    return min(max(0.5 - (((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 - r), 0.0), 1.0)


def _in_tri(x, y, pts):
    acc = 0
    for i in range(3):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % 3]
        cross = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
        acc += 1 if cross > 0 else (-1 if cross < 0 else 0)
    return 1.0 if abs(acc) == 3 else 0.0


def _blend(base, top, a):
    return tuple(base[i] * (1 - a) + top[i] * a for i in range(3))


def _chunk(tag, data):
    return (struct.pack('>I', len(data)) + tag + data
            + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF))


def draw_plain(path):
    raw = bytearray()
    for y in range(SIZE):
        raw.append(0)
        yc = y + 0.5
        for x in range(SIZE):
            xc = x + 0.5
            px = list(C_BG)
            for fn, kw, color in ((_rounded, FRAME_OUT, C_FRAME), (_rounded, FRAME_IN, C_PANEL)):
                a = fn(xc, yc, **kw)
                if a:
                    px = list(_blend(px, color, a))
            a = _circle(xc, yc, **SUN)
            if a:
                px = list(_blend(px, C_GLYPH, a))
            for tri in (M1, M2):
                if _in_tri(xc, yc, tri):
                    px = list(_blend(px, C_GLYPH, 1.0))
            raw += bytes(int(c + 0.5) for c in px)

    out = bytearray(b'\x89PNG\r\n\x1a\n')
    out += _chunk(b'IHDR', struct.pack('>IIBBBBB', SIZE, SIZE, 8, 2, 0, 0, 0))
    out += _chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    out += _chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(bytes(out))
    return len(out)


# ============================================================
def main():
    ap = argparse.ArgumentParser(description='补齐晓得系列的占位图标')
    ap.add_argument('--check', action='store_true', help='只报状态，不写文件')
    ap.add_argument('--redo', action='store_true', help='重画台账里的占位图（不动真图）')
    ap.add_argument('--force', action='store_true', help='连真图一起覆盖（危险）')
    ap.add_argument('--plain', action='store_true', help='不印名字，画纯图形占位')
    args = ap.parse_args()

    items = scan()
    if not items:
        print('没有扫到任何包，检查 packages/ 目录')
        return 1

    marks = load_manifest()
    todo = []
    for it in items:
        rel = os.path.relpath(it[1], ROOT)
        found = existing(os.path.splitext(it[1])[0])
        if args.force or not found or (args.redo and rel in marks):
            todo.append(it)

    still, replaced = manifest_report(items)
    missing = [it for it in items if not existing(os.path.splitext(it[1])[0])]

    if args.check:
        print('仓库共需 %d 张图标：缺 %d · 仍是占位图 %d · 已换成真图 %d'
              % (len(items), len(missing), len(still), len(replaced)))
        if missing:
            print('')
            print('【缺图 —— 不补上传会失败】')
            for kind, target, title, subtitle in missing:
                print('  ✗ %-47s %s' % (os.path.relpath(target, ROOT), title))
        if still:
            print('')
            print('【仍是占位图 —— 等着你替换】')
            for kind, target, title, subtitle in still:
                print('  □ %-47s %-14s %s'
                      % (os.path.relpath(target, ROOT), title, subtitle.split(' · ')[0]))
        return 0

    if not todo:
        print('无需补图：%d 张图标齐了（其中 %d 张仍是占位图）' % (len(items), len(still)))
        return 0

    use_pil = HAVE_PIL and not args.plain
    mode = '印名字' if use_pil else ('纯图形（--plain）' if args.plain else '纯图形（未装 Pillow，字印不了）')
    print('补 %d 张占位图 · %s · 512×512' % (len(todo), mode))
    print('')

    entries = {}
    total = 0
    for kind, target, title, subtitle in todo:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        size = draw_pillow(target, title, subtitle) if use_pil else draw_plain(target)
        total += size
        entries[os.path.relpath(target, ROOT)] = file_sha1(target)
        print('  + %-48s %-7.1f KB  %s'
              % (os.path.relpath(target, ROOT), size / 1024, title))

    save_manifest(entries)
    print('')
    print('合计 %d 张 / %.1f KB。已存在的文件一张没动。' % (len(todo), total / 1024))
    if use_pil:
        print('有真图了直接覆盖同名文件即可，不用改任何配置；换完跑一次 pnpm build。')
        print('想知道还剩哪些没换：python3 scripts/placeholders.py --check')
    return 0


if __name__ == '__main__':
    sys.exit(main())
