#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
晓得·设计解剖 —— 网页样式候选值提取脚本

用途：给一个网页 URL，抓取它的 HTML 与 CSS，把「颜色 / 字号 / 间距 / 圆角 / 阴影」
的候选值按出现频次统计出来，供 AI 判断哪些是真正的设计令牌。

设计原则：
1. 零第三方依赖，只用 Python 标准库，任何环境都能跑。
2. 只做「统计」，不做「判断」。选哪个当主色由 AI 结合页面结构决定，
   脚本不猜。它输出频次，不输出结论。
3. 抓不到就老实报错退出，绝不返回编造的默认值。

用法：
    python3 fetch-page-css.py <url> [--limit 25] [--css-only] [--timeout 20]

输出：
    一段纯文本候选清单，直接喂给 AI 读取。
"""

import argparse
import re
import ssl
import sys
import urllib.parse
import urllib.request
from collections import Counter

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# 允许自签名证书：企业内网站点常见，用户本机抓取场景优先保证能拿到内容
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def fetch(url, timeout):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,text/css,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
        raw = r.read()
        ctype = r.headers.get("Content-Type", "")
    enc = "utf-8"
    m = re.search(r'charset=([\w\-]+)', ctype, re.I)
    if m:
        enc = m.group(1)
    try:
        return raw.decode(enc, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


HEX_RE = re.compile(r'#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')
RGB_RE = re.compile(r'\brgba?\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*(?:,\s*[\d.]+\s*)?\)')
FONT_SIZE_RE = re.compile(r'font-size\s*:\s*([\d.]+)\s*(px|rem|em|pt)', re.I)
FONT_FAMILY_RE = re.compile(r'font-family\s*:\s*([^;{}]+)', re.I)
RADIUS_RE = re.compile(r'border-radius\s*:\s*([^;{}]+)', re.I)
SHADOW_RE = re.compile(r'box-shadow\s*:\s*([^;{}]+)', re.I)
SPACING_RE = re.compile(
    r'\b(?:padding|margin|gap|row-gap|column-gap|padding-top|padding-bottom|'
    r'margin-top|margin-bottom|padding-left|padding-right)\s*:\s*([^;{}]+)', re.I)
CSS_VAR_RE = re.compile(r'(--[\w\-]+)\s*:\s*([^;{}]+)')


def collect_css_links(html, base):
    links = []
    for m in re.finditer(r'<link[^>]+rel=["\']?stylesheet["\'][^>]*>', html, re.I):
        tag = m.group(0)
        hm = re.search(r'href=["\']([^"\']+)["\']', tag)
        if hm:
            links.append(urllib.parse.urljoin(base, hm.group(1)))
    return links


def inline_css(html):
    return "\n".join(m.group(1) for m in re.finditer(r'<style[^>]*>(.*?)</style>', html, re.S | re.I))


def parse_spacing(raw):
    """把 '8px 16px' / '0 auto' 这类复合值拆成单个带单位数字"""
    out = []
    for tok in re.split(r'[\s]+', raw.strip()):
        m = re.match(r'^([\d.]+)(px|rem|em)$', tok)
        if m:
            v, u = float(m.group(1)), m.group(2)
            if u == "rem":
                v *= 16
            out.append(int(v) if v == int(v) else v)
    return out


def report(css_text, limit, css_only):
    colors = Counter()
    for m in HEX_RE.finditer(css_text):
        colors[m.group(0).lower()] += 1
    for m in RGB_RE.finditer(css_text):
        colors[re.sub(r'\s+', '', m.group(0))] += 1

    sizes = Counter()
    for m in FONT_SIZE_RE.finditer(css_text):
        v, u = m.group(1), m.group(2).lower()
        val = float(v) * 16 if u == "rem" else float(v)
        sizes[f"{int(val) if val == int(val) else val}px"] += 1

    spacing = Counter()
    for m in SPACING_RE.finditer(css_text):
        for v in parse_spacing(m.group(1)):
            if v > 0:
                spacing[f"{v}px"] += 1

    radius = Counter(re.sub(r'\s+', ' ', m.group(1).strip()) for m in RADIUS_RE.finditer(css_text))
    shadow = Counter(re.sub(r'\s+', ' ', m.group(1).strip())[:70] for m in SHADOW_RE.finditer(css_text))
    families = Counter(re.sub(r'\s+', ' ', m.group(1).strip())[:80] for m in FONT_FAMILY_RE.finditer(css_text))
    cssvars = Counter()
    for m in CSS_VAR_RE.finditer(css_text):
        cssvars[f"{m.group(1)}: {m.group(2).strip()[:60]}"] += 1

    lines = []
    def sec(title, counter, note=""):
        lines.append(f"\n### {title}{note}")
        if not counter:
            lines.append("  （未提取到）")
            return
        for k, c in counter.most_common(limit):
            lines.append(f"  {c:>5}x  {k}")

    sec("CSS 变量（最优先看这里，原站若已令牌化可直接沿用）", cssvars)
    sec("颜色候选", colors)
    sec("字号候选（rem 已按 16px 折算）", sizes)
    sec("间距候选（padding/margin/gap）", spacing)
    sec("圆角候选", radius)
    sec("阴影候选", shadow)
    sec("字体族候选", families)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="提取网页样式候选值")
    ap.add_argument("url", help="网页 URL")
    ap.add_argument("--limit", type=int, default=25, help="每类最多输出多少条（默认 25）")
    ap.add_argument("--css-only", action="store_true", help="只抓 CSS，不抓 HTML")
    ap.add_argument("--timeout", type=int, default=20, help="单次请求超时秒数（默认 20）")
    args = ap.parse_args()

    try:
        html = fetch(args.url, args.timeout)
    except Exception as e:
        print(f"[抓取失败] {args.url}\n原因：{type(e).__name__}: {e}\n"
              f"处理：确认 URL 可访问，或改用截图作为参考物；不要凭印象编造配色。", file=sys.stderr)
        sys.exit(2)

    css = inline_css(html)
    links = collect_css_links(html, args.url)
    ok, failed = 0, []
    for lk in links[:12]:                      # 最多取 12 个外链，避免拖太久
        try:
            css += "\n" + fetch(lk, args.timeout)
            ok += 1
        except Exception as e:
            failed.append(f"{lk} ({type(e).__name__})")

    print(f"来源：{args.url}")
    print(f"内联样式：{'有' if inline_css(html) else '无'}    外链 CSS：发现 {len(links)} 个，成功 {ok} 个")
    if failed:
        print(f"抓取失败的外链：{'; '.join(failed)}")
    if len(css) < 200:
        print("\n[警告] 拿到的样式内容极少，该页面很可能是纯前端渲染（SPA）。"
              "\n建议：改用页面截图作为参考物；不要根据这段内容生成配色。")
    print(report(css, args.limit, args.css_only))


if __name__ == "__main__":
    main()
