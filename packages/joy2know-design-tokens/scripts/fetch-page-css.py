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

--css-only：只输出「CSS 变量（令牌）」一段，跳过颜色/字号/间距等候选段。
（原 docstring 与 argparse 都声明了这个旗标，但 report() 里从未使用它 —— 传不传输出逐字节相同。
  2026-09-23 改为真正生效，并把描述改成与行为一致。）

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


META_CHARSET_RE = re.compile(rb'<meta[^>]+charset\s*=\s*["\']?([\w\-]+)', re.I)
CSS_CHARSET_RE = re.compile(rb'@charset\s+["\']([\w\-]+)["\']', re.I)


def sniff_charset(raw, ctype):
    """按优先级嗅探字符编码，返回 (编码名 或 None, 来源说明)。

    顺序：HTTP Content-Type 的 charset → HTML `<meta charset>` → CSS `@charset`。
    只在开头几 KB 内找，避免大文件全量扫描。
    """
    m = re.search(r'charset=([\w\-]+)', ctype, re.I)
    if m:
        return m.group(1), "Content-Type"
    head = raw[:4096]
    m = META_CHARSET_RE.search(head)
    if m:
        return m.group(1).decode("ascii", "ignore"), "<meta charset>"
    m = CSS_CHARSET_RE.search(raw[:512])
    if m:
        return m.group(1).decode("ascii", "ignore"), "@charset"
    return None, None


def fetch(url, timeout):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,text/css,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
        raw = r.read()
        ctype = r.headers.get("Content-Type", "")

    enc, src = sniff_charset(raw, ctype)
    if enc:
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError) as e:
            # 声明了编码却解不开：留痕后再容错，绝不静默产出被吃掉的中文
            print(f"[编码警告] {url}\n"
                  f"  声明的编码 {enc}（来自 {src}）解码失败：{type(e).__name__}: {e}\n"
                  f"  已退回 UTF-8 容错解码 —— **非 ASCII 内容可能丢失**，请核对提取结果或改用截图作参考物。",
                  file=sys.stderr)
    else:
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            print(f"[编码警告] {url}\n"
                  f"  未识别到字符编码（Content-Type 无 charset，页面也无 <meta charset> / @charset）。\n"
                  f"  已按 UTF-8 容错解码 —— **非 ASCII 内容可能丢失**（GBK/GB18030 等页面尤其明显）；\n"
                  f"  若样式候选值异常偏少，请改用截图作参考物。",
                  file=sys.stderr)
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


def report(css_text, limit, css_only=False):
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
    if css_only:
        # `--css-only`：只给令牌段。原实现忽略该形参，导致旗标是空操作（2026-09-23 修复）。
        lines.append("\n（--css-only：只列令牌定义，颜色/字号/间距/圆角/阴影/字体族候选已跳过。"
                     "去掉该旗标可看全部候选。）")
        return "\n".join(lines)
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
    ap.add_argument("--css-only", action="store_true",
                    help="只输出「CSS 变量（令牌）」一段，跳过其余候选段")
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
