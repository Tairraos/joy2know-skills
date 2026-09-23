#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""repo_scan.py —— 晓得·代码考古 的仓库扫描脚本（零第三方依赖，纯标准库）。

功能：
  1. 递归扫描一个代码仓库，按启发式规则给文件打分，输出「最重要的 N 个文件」。
  2. 解析主流依赖清单文件，输出技术栈与依赖概览。
  3. 输出可控深度的目录职责树（每目录标注文件数与其下得分最高的文件）。
  4. 自动跳过噪音目录（node_modules / dist / .git / vendor ...），绝不打印仓库全文。

设计原则：不读完所有文件。先看结构、再按分数挑出最值得读的少数文件。
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

# ---------- 噪音过滤 ----------
NOISE_DIRS = {
    ".git", "node_modules", "dist", "build", "target", "out", "vendor",
    "__pycache__", ".venv", "venv", "env", ".idea", ".vscode", ".next",
    ".nuxt", "coverage", ".turbo", ".svelte-kit", "bin", "obj",
}
NOISE_FILE_RE = re.compile(
    r"(\.(lock|min\.(js|css)|map)$)"  # 锁文件 / 压缩产物 / sourcemap
    r"|^(package-lock\.json|yarn\.lock|poetry\.lock|go\.sum|"
    r"pnpm-lock\.yaml|composer\.lock|Gemfile\.lock)$",
    re.IGNORECASE,
)
# 超大且通常是固件/数据的文件，默认不计入打分（只看大小，不读内容）
HUGE_BYTES = 2 * 1024 * 1024

# ---------- 入口信号：文件名命中即视为潜在入口 ----------
ENTRY_NAMES = {
    "main", "index", "app", "server", "application", "manage", "wsgi", "asgi",
    "run", "start", "bootstrap", "launch", "cli", "cmd", "program", "service",
    "__main__", "settings", "config", "routes", "router", "urls",
}
# 目录层级浅（根目录）的入口权重更高
ENTRY_NAME_IN_DIR = {"cmd", "bin", "internal", "pkg", "src", "app", "lib", "core"}

# 关键字命中（路径或文件名）：路由 / 控制器 / 模型 / 服务 等核心关注点
KEYWORD_RE = re.compile(
    r"(route|router|controller|model|schema|service|handler|middleware|"
    r"api|view|dao|repository|config|middleware|endpoint|resolver)",
    re.IGNORECASE,
)

# 引用语句特征，用于统计「被引用次数」
IMPORT_PATTERNS = [
    re.compile(r"^\s*import\s+([a-zA-Z0-9_\.]+)"),            # python / go
    re.compile(r"^\s*from\s+([a-zA-Z0-9_\.]+)\s+import"),     # python
    re.compile(r"require\(['\"]([a-zA-Z0-9_\-/]+)['\"]\)"),   # js/node
    re.compile(r"import\s+['\"]([a-zA-Z0-9_\-/]+)['\"]"),     # js esm
    re.compile(r"#include\s+[<\"]?([a-zA-Z0-9_\-/]+\.[a-zA-Z]+)"),  # c/c++
    re.compile(r'using\s+([a-zA-Z0-9_\.]+)\s*;'),            # c# / java-ish
]
# 文本类源码扩展名（只在这些文件里统计引用，避免读二进制）
CODE_EXT = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".c", ".cc",
    ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".rs", ".swift", ".kt",
    ".scala", ".sh", ".sql", ".vue",
}

DEP_FILES = {
    "package.json": "node",
    "requirements.txt": "python",
    "pyproject.toml": "python",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "pom.xml": "java-maven",
    "build.gradle": "java-gradle",
    "Gemfile": "ruby",
    "composer.json": "php",
}


def is_noise_dir(name):
    return name in NOISE_DIRS


def is_noise_file(path):
    base = os.path.basename(path)
    if NOISE_FILE_RE.search(base):
        return True
    low = base.lower()
    if low.endswith(".min.js") or low.endswith(".min.css"):
        return True
    return False


def walk_repo(root):
    """返回 (files, dirs_tree)。files: 相对路径列表（已排除噪音）。"""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # 原地剪枝噪音目录，避免递归进去
        dirnames[:] = [d for d in dirnames if not is_noise_dir(d)]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            if is_noise_file(rel):
                continue
            files.append(rel)
    files.sort()
    return files


def count_references(root, files):
    """粗略统计每个模块 basename 被引用次数（近似，用于打分，不追求精确）。"""
    ref_counter = Counter()
    for rel in files:
        ext = os.path.splitext(rel)[1].lower()
        if ext not in CODE_EXT:
            continue
        full = os.path.join(root, rel)
        try:
            if os.path.getsize(full) > HUGE_BYTES:
                continue
            with open(full, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if len(line) > 400:
                        continue
                    for pat in IMPORT_PATTERNS:
                        m = pat.search(line)
                        if m:
                            mod = m.group(1)
                            # 取最后一段作为 basename，例如 a.b.foo -> foo
                            ref_counter[mod.split(".")[-1].split("/")[-1]] += 1
                            break
        except OSError:
            continue
    return ref_counter


def score_files(root, files, ref_counter, max_depth):
    scored = []
    for rel in files:
        full = os.path.join(root, rel)
        try:
            size = os.path.getsize(full)
        except OSError:
            continue
        ext = os.path.splitext(rel)[1].lower()
        depth = rel.count(os.sep) + 1
        base = os.path.basename(rel)
        stem = os.path.splitext(base)[0]
        base_lower = base.lower()
        reasons = []

        score = 0

        # 1) 入口信号
        if stem.lower() in ENTRY_NAMES:
            bonus = 30 if depth <= 2 else 18
            score += bonus
            reasons.append("入口文件名 +%d" % bonus)
        # 处于入口型目录
        top_dir = rel.split(os.sep)[0].lower() if depth >= 2 else ""
        if top_dir in ENTRY_NAME_IN_DIR:
            score += 6
            reasons.append("位于核心目录 +6")

        # 2) 被引用次数（近似）
        ref = ref_counter.get(stem, 0)
        if ref > 0:
            rbonus = min(ref * 3, 45)
            score += rbonus
            reasons.append("被引用约 %d 次 +%d" % (ref, rbonus))

        # 3) 层级浅优先
        if depth <= 2:
            score += (12 - depth * 4)
            reasons.append("层级浅")
        elif depth <= max_depth:
            score += max(0, 8 - depth)
        else:
            score -= 4  # 太深且非入口，略降权

        # 4) 文件规模适中
        if size < 200:
            score -= 6
            reasons.append("过小(可能被忽略)")
        elif 200 <= size <= 60 * 1024:
            score += 10
            reasons.append("规模适中 +10")
        elif size <= 300 * 1024:
            score += 3
        else:
            score -= 8
            reasons.append("超大文件降权")

        # 5) 核心关键字
        if KEYWORD_RE.search(rel):
            score += 12
            reasons.append("核心关键字命中 +12")

        # 锁文件 / 构建产物再保险（理论上已过滤，这里兜底）
        if ext in {".lock", ".map"} or base_lower.endswith(".lock"):
            score = -999

        scored.append((score, rel, reasons, size))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


try:  # Python 3.11+ 标准库；拿不到就退回正则（见 _pyproject_deps）
    import tomllib
except ImportError:  # pragma: no cover
    tomllib = None


def _split_req(spec):
    """把 'fastapi>=0.110' / 'pkg[extra]; python_version>="3.9"' 切成包名。"""
    return re.split(r"[<>=!~\[; ]", str(spec).strip(), maxsplit=1)[0]


def _pyproject_deps(text):
    """从 pyproject.toml 取依赖名。

    优先用标准库 tomllib 按 TOML **结构**取值 —— 这样 `[project]` 下的
    `name` / `version` / `dependencies` 这些**表键不会被当成依赖**（原实现用
    `^\\s*key\\s*=` 正则抓，会把它们一起抓出来）。
    覆盖：PEP 621 `[project].dependencies` 与 `optional-dependencies`、
    PEP 735 `[dependency-groups]`、Poetry `[tool.poetry*.dependencies]`。
    """
    names = []
    if tomllib is not None:
        try:
            data = tomllib.loads(text)
        except Exception:
            data = None
        if isinstance(data, dict):
            proj = data.get("project") or {}
            for dep in proj.get("dependencies") or []:
                nm = _split_req(dep)
                if nm:
                    names.append(nm)
            for group in (proj.get("optional-dependencies") or {}).values():
                for dep in group or []:
                    nm = _split_req(dep)
                    if nm:
                        names.append(nm)
            for group in (data.get("dependency-groups") or {}).values():
                for dep in group or []:
                    if not isinstance(dep, str):
                        continue
                    nm = _split_req(dep)
                    if nm:
                        names.append(nm)
            poetry = (data.get("tool") or {}).get("poetry") or {}
            for key in ("dependencies", "dev-dependencies"):
                for nm in (poetry.get(key) or {}):
                    if nm.lower() != "python":
                        names.append(nm)
            for grp in (poetry.get("group") or {}).values():
                for nm in ((grp or {}).get("dependencies") or {}):
                    if nm.lower() != "python":
                        names.append(nm)
            if names:
                return names
    # 退回：只从 dependencies 数组里取字符串字面量，不再按 `key =` 抓表键
    for block in re.finditer(r"(?ms)^\s*dependencies\s*=\s*\[(.*?)\]", text):
        for lit in re.findall(r"""["']([^"']+)["']""", block.group(1)):
            nm = _split_req(lit)
            if nm:
                names.append(nm)
    for head in re.finditer(
            r"(?m)^\s*\[tool\.poetry[^\]]*dependencies[^\]]*\]\s*$", text):
        seg = text[head.end():]
        nxt = re.search(r"(?m)^\s*\[", seg)
        seg = seg[: nxt.start()] if nxt else seg
        for mm in re.finditer(r"(?m)^\s*([a-zA-Z0-9_.\-]+)\s*=", seg):
            if mm.group(1).lower() != "python":
                names.append(mm.group(1))
    return names


def parse_dependencies(root):
    """解析受支持的依赖清单，返回 {ecosystem: [name, ...]}。"""
    deps = {}  # eco -> set(names)；多文件同生态必须**合并**，不能覆盖
    for fname, eco in DEP_FILES.items():
        full = os.path.join(root, fname)
        if not os.path.isfile(full):
            continue
        try:
            with open(full, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except OSError:
            continue
        names = []
        if fname == "package.json":
            try:
                data = json.loads(text)
                for sec in ("dependencies", "devDependencies", "peerDependencies"):
                    if isinstance(data.get(sec), dict):
                        names += list(data[sec].keys())
            except ValueError:
                pass
        elif fname == "requirements.txt":
            for line in text.splitlines():
                line = line.split("#")[0].strip()
                if not line or line.startswith("-"):
                    continue
                names.append(re.split(r"[=<>!~ ]", line, maxsplit=1)[0])
        elif fname == "pyproject.toml":
            names += _pyproject_deps(text)
        elif fname == "Gemfile":
            # `gem "rails", "~> 7.0"` / `gem 'pg'`。原实现让 Gemfile 落进最后的 else
            # 分支（按空格取首词），于是输出 `gem` / `source` 这类关键字而非真实依赖。
            for line in text.splitlines():
                line = line.split("#")[0].strip()
                gm = re.match(r"""gem\s+["']([^"']+)["']""", line)
                if gm:
                    names.append(gm.group(1))
        elif fname == "go.mod":
            for m in re.finditer(r"^\s*([a-zA-Z0-9_./\-]+)\s+v[\d]", text, re.M):
                names.append(m.group(1))
        elif fname == "Cargo.toml":
            in_deps = False
            for line in text.splitlines():
                if re.match(r"^\s*\[dependencies", line):
                    in_deps = True
                    continue
                if re.match(r"^\s*\[", line):
                    in_deps = False
                if in_deps:
                    mm = re.match(r"^\s*([a-zA-Z0-9_\-]+)\s*=", line)
                    if mm:
                        names.append(mm.group(1))
        elif fname == "pom.xml":
            for m in re.finditer(r"<artifactId>([^<]+)</artifactId>", text):
                names.append(m.group(1))
        elif fname == "composer.json":
            try:
                data = json.loads(text)
                for sec in ("require", "require-dev"):
                    if isinstance(data.get(sec), dict):
                        names += list(data[sec].keys())
            except ValueError:
                pass
        else:
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    names.append(line.split()[0])
        if names:
            # 合并而非覆盖：requirements.txt 与 pyproject.toml 同属 python 生态，
            # 原实现 `deps[eco] = ...` 会让后解析的那个把前一个的依赖**静默丢掉**。
            deps.setdefault(eco, set()).update(names)
    return {eco: sorted(v) for eco, v in deps.items()}


def build_tree(files, max_depth):
    """返回每目录的文件数（只统计真正的目录前缀，不含文件自身）。"""
    dir_count = Counter()
    for rel in files:
        parts = rel.split(os.sep)
        # i 取到 len(parts)-1，即只累加目录前缀，最后一个元素是文件本身，跳过
        for i in range(1, len(parts)):
            d = os.sep.join(parts[:i])
            dir_count[d] += 1
    return dir_count


def print_report(root, files, scored, deps, max_files, max_depth, dir_count):
    total_bytes = 0
    try:
        for rel in files:
            total_bytes += os.path.getsize(os.path.join(root, rel))
    except OSError:
        pass

    print("=" * 64)
    print("仓库扫描报告：%s" % os.path.abspath(root))
    print("=" * 64)
    print("文件总数（已排除噪音）：%d    估算体积：%.2f MB" % (
        len(files), total_bytes / (1024 * 1024)))
    langs = sorted({os.path.splitext(f)[1].lower() for f in files if os.path.splitext(f)[1]})
    print("涉及扩展名：%s" % (", ".join(langs) if langs else "无"))

    print("\n--- 最重要的 %d 个文件（按启发式打分）---" % max_files)
    for i, (sc, rel, reasons, size) in enumerate(scored[:max_files], 1):
        print("%2d. [%s] %s" % (i, fmt_size(size), rel))
        print("     得分 %d · %s" % (sc, "；".join(reasons) if reasons else "通用源码"))

    print("\n--- 依赖清单（技术栈概览）---")
    if deps:
        for eco, names in deps.items():
            print("[%s] 共 %d 项：" % (eco, len(names)))
            # 每行最多列 6 个，避免刷屏
            for j in range(0, len(names), 6):
                print("    " + ", ".join(names[j:j + 6]))
    else:
        print("未识别到受支持的依赖清单文件（package.json / requirements.txt / "
              "pyproject.toml / go.mod / Cargo.toml / pom.xml / composer.json 等）。")

    print("\n--- 目录职责树（深度 <= %d，标注文件数与代表文件）---" % max_depth)
    # 仅展示深度 <= max_depth 的目录，按路径排序
    shown = [d for d in dir_count if d.count(os.sep) + 1 <= max_depth]
    for d in sorted(shown):
        indent = "  " * (d.count(os.sep))
        print("%s%s/  (%d 文件)" % (indent, os.path.basename(d) or d, dir_count[d]))
    if not shown:
        print("（仓库为空或文件均位于超过最大深度的层级）")

    print("\n提示：本脚本只输出「最重要的文件清单 + 依赖 + 目录树」，"
          "不会打印任何文件正文。下一步请按需读取清单里的文件。")


def fmt_size(n):
    if n < 1024:
        return "%dB" % n
    if n < 1024 * 1024:
        return "%.1fK" % (n / 1024)
    return "%.1fM" % (n / 1024 / 1024)


def main(argv=None):
    p = argparse.ArgumentParser(
        description="仓库启发式扫描：找出最重要的 N 个文件 + 依赖清单 + 目录树")
    p.add_argument("path", nargs="?", default=".", help="仓库根目录（默认当前目录）")
    p.add_argument("--max-files", type=int, default=20,
                   help="输出最重要的文件数量（默认 20）")
    p.add_argument("--max-depth", type=int, default=3,
                   help="目录树展示的最大深度（默认 3）")
    p.add_argument("--no-ref", action="store_true",
                   help="跳过引用统计（超大仓库可加速）")
    args = p.parse_args(argv)

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print("错误：目录不存在 -> %s" % root, file=sys.stderr)
        return 2

    files = walk_repo(root)
    if not files:
        print("仓库为空或所有文件都被噪音规则跳过。", file=sys.stderr)
        return 1

    ref_counter = Counter() if args.no_ref else count_references(root, files)
    scored = score_files(root, files, ref_counter, args.max_depth)
    deps = parse_dependencies(root)
    dir_count = build_tree(files, args.max_depth)
    print_report(root, files, scored, deps, args.max_files, args.max_depth, dir_count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
