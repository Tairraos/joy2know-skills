#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
series_audit.py —— 跨包「系列一致性」审计（selfcheck.py 的补充）

selfcheck.py 查的是**单个包**的字段/结构合规；
本脚本查的是**跨包**的系列级一致性缺陷 —— 同一套骨架在多个包里批量复现的那几类。

对应 `docs/平台资产规范.md` 第十二节的硬规则：
  A. §七「按需知识」是否点名了 references 的「必做类」章节 ......... R4
  B. 脚本里「用户可见」的开关是否写进了 SKILL.md .................. R2
  C. 静默失败点初筛（check=False 不查 / except:pass / 裸 except） ... R1

⚠️ 本脚本报出的**只是「候选」，不是判决**。
   概要章（「一、是什么」）、纯参考章、通用调试开关（--verbose/--json）都会误报，
   必须逐条人工定性后再动手。误报率高的判据宁可少报 —— 详见 R6 的说明。

用法：
    python3 scripts/series_audit.py .              # 人读报告
    python3 scripts/series_audit.py . --json       # 机器可读
    python3 scripts/series_audit.py . -v           # 带上下文
退出码：恒为 0（这是审计，不是门禁）；有无候选请读输出。
"""
import os
import re
import sys
import glob
import json

# —— R4：references 里哪些章节算「必做类」，必须被 §七 点名 ——
MUST_SECTION = re.compile(
    r"自检|必跑|必做|硬约束|翻车|纠正|注意|坑|清单|禁止|红线|不可|必须"
)

# —— R2：哪些参数属于「通用/开发用」，不算「实现有文档无」——
GENERIC_FLAGS = {
    "--help", "-h", "--version", "--verbose", "-v", "--debug", "--quiet", "-q",
    "--json", "--output", "-o", "--out", "--in", "--input", "-i",
    "--dry-run", "--force", "-f", "--yes", "-y", "--seed", "--rules",
    "--root", "--no-embed", "--no-batch",
}


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return ""


def package_names(root):
    return sorted(os.path.basename(d.rstrip("/")) for d in glob.glob(os.path.join(root, "packages", "*/")))


def load_doc_text(pkg_dir):
    """技能取 SKILL.md；专家/专家团取 agents/*.md 全文（那里才是给模型读的）。"""
    skill = os.path.join(pkg_dir, "SKILL.md")
    if os.path.exists(skill):
        return read(skill), True
    agents = sorted(glob.glob(os.path.join(pkg_dir, "agents", "*.md")))
    return "\n".join(read(a) for a in agents), False


def check_route(pkg_dir, skill_text):
    """A. §七「按需知识」对 references「必做类」章节的点名覆盖。"""
    m = re.search(r"^##\s*([一二三四五六七八九十]+)[、.]\s*按需知识\s*$", skill_text, re.M)
    if not m:
        return []
    end = re.search(
        r"^##\s*[一二三四五六七八九十]+[、.]\s*完成判据", skill_text[m.end():], re.M
    )
    body = skill_text[m.end(): m.end() + (end.start() if end else len(skill_text))]
    out = []
    for ref in sorted(set(re.findall(r"@references/([A-Za-z0-9._\-]+\.md)", body))):
        ref_path = os.path.join(pkg_dir, "references", ref)
        if not os.path.exists(ref_path):
            continue
        sections = re.findall(r"^##\s+(.+)$", read(ref_path), re.M)
        # 同一 references 文件可能在 §七 被**多行**分别提及（如「必做类章节 → §三§四」
        # 与「参考类章节 → §一§二」各一行）。必须把**所有**提及行都算作点名依据，
        # 否则只要最后一行的内容不含某章节名，就会误报「漏章」。
        route_lines = [ln for ln in body.split("\n") if "@references/" + ref in ln]
        line = "\n".join(route_lines)
        missing = []
        for sec in sections:
            if not MUST_SECTION.search(sec):
                continue
            core = re.sub(r"^[一二三四五六七八九十\d]+[、.]\s*", "", sec)
            core = re.sub(r"[（(].*?[)）]", "", core).strip()
            frags = [core[i:i + 3] for i in range(max(0, len(core) - 2))]
            if frags and not any(fr in line for fr in frags):
                missing.append(sec)
        if missing:
            out.append({"ref": ref, "missing": missing, "route_line": line.strip()})
    return out


def check_params(pkg_dir, skill_text):
    """B. 脚本里「用户可见」的开关是否写进文档。"""
    out = []
    paths = sorted(glob.glob(os.path.join(pkg_dir, "scripts", "*.py"))) + \
        sorted(glob.glob(os.path.join(pkg_dir, "scripts", "*.mjs"))) + \
        sorted(glob.glob(os.path.join(pkg_dir, "scripts", "*.js")))
    for path in paths:
        src = read(path)
        flags = set(re.findall(r'add_argument\(\s*["\'](--[a-zA-Z0-9\-]+)["\']', src))
        if not flags:
            flags = set(re.findall(r'["\'](--[a-zA-Z0-9\-]+)["\']', src))
        undoc = sorted(f for f in flags if f not in skill_text and f not in GENERIC_FLAGS)
        if undoc:
            out.append({
                "script": os.path.basename(path),
                "declared": sorted(flags),
                "undocumented": undoc,
            })
    return out


def check_silent(pkg_dir):
    """C. 静默失败点初筛（R1 的机器可查部分）。"""
    out = []
    paths = [p for p in glob.glob(os.path.join(pkg_dir, "scripts", "*"))
             if os.path.isfile(p) and os.path.splitext(p)[1] in (".py", ".mjs", ".js")]
    for path in sorted(paths):
        for i, ln in enumerate(read(path).split("\n"), 1):
            stripped = ln.strip()
            if re.search(r"check\s*=\s*False", stripped) \
               or re.search(r"except[^:]*:\s*pass\b", stripped) \
               or re.match(r"^except\s*:\s*$", stripped) \
               or re.match(r"^except\s+\w+\s*:\s*$", stripped):
                out.append({
                    "script": os.path.basename(path),
                    "line": i,
                    "code": stripped[:110],
                })
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    root = args[0] if args else "."
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    as_json = "--json" in sys.argv

    report = {"route": [], "params": [], "silent": [], "scanned": {}}
    n_route = n_params = 0

    for pkg in package_names(root):
        pkg_dir = os.path.join(root, "packages", pkg)
        doc_text, is_skill = load_doc_text(pkg_dir)
        if not doc_text:
            continue

        if is_skill:
            hits = check_route(pkg_dir, doc_text)
            if hits:
                n_route += 1
                report["route"].append({"package": pkg, "hits": hits})

        hits = check_params(pkg_dir, doc_text)
        if hits:
            n_params += 1
            report["params"].append({"package": pkg, "hits": hits})

        hits = check_silent(pkg_dir)
        if hits:
            report["silent"].append({"package": pkg, "hits": hits})

    report["scanned"] = {
        "route_packages": n_route,
        "param_packages": n_params,
        "silent_packages": len(report["silent"]),
    }

    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    line = "=" * 78
    print(line)
    print("跨包「系列一致性」审计  —— 报告为「候选」，定性需人工复核")
    print(line)

    print("\n【A】§七 未点名 references 的「必做类」章节（R4）")
    if not report["route"]:
        print("   ✅ 无候选")
    for item in report["route"]:
        print(f"   ⚠️  {item['package']}")
        for hit in item["hits"]:
            print(f"       references/{hit['ref']}")
            for sec in hit["missing"]:
                print(f"         漏：{sec}")
            if verbose:
                print(f"         §七 原文：{hit['route_line'][:110]}")
    print(f"   → 涉及 {len(report['route'])} 个包")

    print("\n【B】脚本开关未写进文档（R2）")
    if not report["params"]:
        print("   ✅ 无候选")
    for item in report["params"]:
        print(f"   ⚠️  {item['package']}")
        for hit in item["hits"]:
            und = ", ".join(hit["undocumented"])
            print(f"       {hit['script']}  未文档化 {len(hit['undocumented'])}/{len(hit['declared'])}：{und}")
    print(f"   → 涉及 {len(report['params'])} 个包")

    print("\n【C】静默失败点初筛（R1）")
    if not report["silent"]:
        print("   ✅ 无候选")
    for item in report["silent"]:
        print(f"   ⚠️  {item['package']}（{len(item['hits'])} 处）")
        if verbose:
            for hit in item["hits"]:
                print(f"       {hit['script']}:{hit['line']}  {hit['code']}")
    print(f"   → 涉及 {len(report['silent'])} 个包")

    print("\n" + line)
    print("提醒：以上均为「候选」。概要章、纯参考章、通用开关会误报。")
    print("逐条定性后再动手；定性结论写进该包检测报告第六节。")
    print(line)


if __name__ == "__main__":
    main()
