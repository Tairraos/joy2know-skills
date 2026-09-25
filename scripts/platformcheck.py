#!/usr/bin/env python3
"""平台上传预检 —— 复刻开放平台前端的上传校验规则，在本地先跑一遍。

## 为什么会有这个脚本（2026-09-25 实证）

`joy2know-code-scholar-v1.2.0.zip` 上传被平台以
`解析失败：未找到 SKILL.md，请确保该路径文件存在` 驳回。
追到平台前端产物后确认：**平台按「类型」挑校验器，而报错文案由参数拼出**。

来源（`open.workbuddy.cn` 页面 chunk `1523-997c981aceee83dd.js`，2026-09-25 抓取）：

    tR 技能     = [ fileSize(3MB),   extension([".zip"]), mime(), fileExists(["SKILL.md"]) ]
    tB 专家     = [ fileSize(20MB),  extension([".zip"]), mime(), fileExists([".codebuddy-plugin/plugin.json"]) ]
    tZ 连接器   = [ fileSize(20MB),  extension([".zip"]), mime(), fileExists(["connector-meta.json"]),
                    fileExistsAny([["mcp.json", "cli.json"]]) ]
    tO Buddy应用= [ fileSize(3MB),   extension([".zip"]), mime() ]
    tW = { Skill: tR, Expert: tB, Connector: tZ, BuddyApp: tO }
    class tK { execute({file, capabilityType, assetId}) { let n = tW[capabilityType]; ... } }

以及路径匹配函数（**逐字移植，含它的怪癖**）：

    function tA(e, t) {                     // e = 包内文件路径列表, t = 要求存在的条目
      let a;
      if (e.includes(t)) return true;       // ① 列表里直接有这一条
      for (let t of e) {
        let e = t.indexOf("/");
        if (-1 === e) return false;         // ② 顶层有裸文件 → 直接失败
        let r = t.slice(0, e);              // ③ 取第一段目录名
        if (void 0 === a) { a = r; continue; }
        if (a !== r) return false;          // ④ 顶层目录不唯一 → 失败
      }
      return !!a && e.includes(a + "/" + t) // ⑤ 否则要求「<唯一顶层目录>/<条目>」
    }

配套细节（同样照抄）：
- 只统计**文件**（`if (r.dir) continue`），目录条目不计；
- 忽略 `__MACOSX/`、`__DS_Store`、`._*`；
- 路径先 `\\`→`/`、去开头 `./`、去开头 `/`。

## 由此得出的关键结论

**技能包与专家包的「根级必需文件」不同，二者不可能互相顶替：**
- 技能包必须是 `<包名>/SKILL.md`；
- 专家包必须是 `<包名>/.codebuddy-plugin/plugin.json`，它的 SKILL.md 内嵌在
  `<包名>/skills/<技能名>/SKILL.md`——**按技能口径去查，永远查不到根级 SKILL.md**。

所以「未找到 SKILL.md」这条报错，**只会出现在用技能入口/类型去传一个专家包的时候**。
包本身没坏，是**类型选错了**（或点错了入口）。

## 用法

    python3 scripts/platformcheck.py                     # 检查 dist/ 下全部产物
    python3 scripts/platformcheck.py --zip <某个.zip>    # 检查单个
    python3 scripts/platformcheck.py --selftest          # 阳性对照 + 篡改验证（证明本脚本不是橡皮章）
    python3 scripts/platformcheck.py --json              # 机器可读

退出码：0 = 全部按「应有的类型」通过；1 = 有产物在应有类型下失败；2 = 用法/文件错误

## 口径声明（不许编）

- `missing_entry` 的文案**由实证确定**：用户在平台看到的原文是
  「未找到 SKILL.md，请确保该路径文件存在」，与 `params.entry = "SKILL.md"` 完全吻合。
- 其余报错码的**文案**未在平台前端产物里找到（走的是服务端/运行时 i18n），
  本脚本只标注**码**，文案一律标「未实证」。
- mime 检查（`application/zip`）本脚本按扩展名等价处理，不读取系统 MIME。
"""

import argparse
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def default_artifact_dir() -> Path:
    """默认产物目录（本脚本要能同时用在两种地方）。

    ① 本仓库：脚本在 `scripts/`，产物在 `../dist`；
    ② 把脚本放进技能包后，在任何业务项目里直接跑 —— 此时产物在该项目的 `./dist`。
    两者都不存在时返回 ①，由调用处报「没找到 zip」并提示用 `--dir` / `--zip`。
    """
    for cand in (SCRIPT_DIR.parent / "dist", Path.cwd() / "dist"):
        if cand.is_dir():
            return cand
    return SCRIPT_DIR.parent / "dist"


DIST = default_artifact_dir()

MB = 1048576

# ── 平台的四个校验器（逐字对应 tR / tB / tZ / tO）──────────────────────────
VALIDATORS = {
    "Skill":     {"max_bytes": 3 * MB,  "require": ["SKILL.md"],                        "require_any": None},
    "Expert":    {"max_bytes": 20 * MB, "require": [".codebuddy-plugin/plugin.json"],   "require_any": None},
    "Connector": {"max_bytes": 20 * MB, "require": ["connector-meta.json"],             "require_any": [["mcp.json", "cli.json"]]},
    "BuddyApp":  {"max_bytes": 3 * MB,  "require": [],                                 "require_any": None},
}

CODE_LABEL = {
    "invalid_file_type": "扩展名不是 .zip（invalid_file_type）",
    "invalid_mime_type": "MIME 不是 application/zip（invalid_mime_type，仅扩展名可判，本地不校验）",
    "invalid_archive": "压缩包读不出条目（invalid_archive）",
    "missing_entry": "缺少必需条目（missing_entry）",
    "missing_any_entry": "缺少必需条目之一（missing_any_entry）",
    "file_too_large": "超出体积上限（file_too_large）",
}


# ── ① 条目抽取：对应 tL.resolveEntryPaths / normalizeEntryPath / isIgnorable ──
def normalize(p: str) -> str:
    p = p.replace("\\", "/")
    if p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def ignorable(p: str) -> bool:
    if not p or p == "__MACOSX" or p.startswith("__MACOSX/"):
        return True
    tail = p.rsplit("/", 1)[-1]
    return tail == ".DS_Store" or tail.startswith("._")


def entry_paths(zpath: Path):
    """返回 (files, err)。files 为文件条目（目录不计），按平台口径规范化与过滤。"""
    try:
        with zipfile.ZipFile(zpath) as zf:
            out = []
            for info in zf.infolist():
                if info.is_dir():
                    continue
                n = normalize(info.filename)
                if n and not ignorable(n):
                    out.append(n)
            return out, None
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"


# ── ② 路径匹配：tA 的逐字移植 ───────────────────────────────────────────────
def path_matches(entries, required):
    top = None
    if required in entries:
        return True
    for e in entries:
        i = e.find("/")
        if i == -1:
            return False
        seg = e[:i]
        if top is None:
            top = seg
            continue
        if top != seg:
            return False
    return bool(top) and f"{top}/{required}" in entries


# ── ③ 单个校验器 ───────────────────────────────────────────────────────────
def run_validator(zpath: Path, vtype: str, entries, entries_err):
    spec = VALIDATORS[vtype]
    size = zpath.stat().st_size
    issues = []

    if size > spec["max_bytes"]:
        issues.append({"code": "file_too_large", "params": {"maxMb": round(spec["max_bytes"] / MB)}})
    if not zpath.name.lower().endswith(".zip"):
        issues.append({"code": "invalid_file_type", "params": {}})
    if entries_err or not entries:
        issues.append({"code": "invalid_archive", "params": {"detail": entries_err or "0 个文件条目"}})
        return issues
    for req in spec["require"]:
        if not path_matches(entries, req):
            issues.append({"code": "missing_entry", "params": {"entry": req}})
    if spec["require_any"]:
        for group in spec["require_any"]:
            if not any(path_matches(entries, r) for r in group):
                issues.append({"code": "missing_any_entry", "params": {"entry": " / ".join(group)}})
    return issues


def expected_type(entries) -> str:
    """按包内实际内容判断这是技能包还是专家包（与仓库口径一致）。"""
    top = None
    for e in entries:
        seg = e.split("/", 1)
        if len(seg) > 1:
            top = seg[0]
            break
    if top is None:
        return "?"
    if f"{top}/SKILL.md" in entries:
        return "Skill"
    if f"{top}/.codebuddy-plugin/plugin.json" in entries:
        return "Expert"
    return "?"


def check_zip(zpath: Path):
    entries, err = entry_paths(zpath)
    exp = expected_type(entries)
    report = {"zip": zpath.name, "expected": exp, "size_kb": round(zpath.stat().st_size / 1024, 1),
              "results": {}}
    for vt in VALIDATORS:
        issues = run_validator(zpath, vt, entries, err)
        report["results"][vt] = {"pass": not issues, "issues": issues}
    return report


def render(report):
    lines = [f"{report['zip']}  （{report['size_kb']} KB）"]
    exp = report["expected"]
    for vt, r in report["results"].items():
        mark = "✅ 通过" if r["pass"] else "❌ 失败"
        star = " ← 本包应有的类型" if vt == exp else ""
        lines.append(f"    {vt:<10} {mark}{star}")
        for it in r["issues"]:
            msg = f"        · {CODE_LABEL.get(it['code'], it['code'])}"
            if it["params"]:
                msg += f"  params={it['params']}"
            lines.append(msg)
            if it["code"] in ("missing_entry", "missing_any_entry"):
                lines.append(f"          平台会渲染成：「未找到 {it['params']['entry']}，"
                             f"请确保该路径文件存在」" if it["params"].get("entry") == "SKILL.md"
                             else f"          （该码的文案未实证，仅 {it['code']}）")
    # 结论：本包用「应有的类型」能否过
    ok = report["results"].get(exp, {}).get("pass", False)
    lines.append(f"    → 按 {exp} 类型上传：{'通过' if ok else '会被驳回'}")
    # 互相顶替的提示
    wrong = [vt for vt, r in report["results"].items() if not r["pass"] and vt != exp]
    if exp in ("Skill", "Expert") and [vt for vt in wrong if vt in ("Skill", "Expert")]:
        other = "Expert" if exp == "Skill" else "Skill"
        lines.append(f"    ⚠️ 这个包**不能**用 {other} 类型上传 —— 两者根级必需文件不同，换了必挂。")
    return "\n".join(lines)


# ── ④ 自检：阳性对照 + 篡改验证 ─────────────────────────────────────────────
def build_fixture(root: Path, kind: str, nested_extra: bool = False, drop_required: bool = False):
    """造一个最小可用的技能包 / 专家包 zip，返回路径。

    drop_required：抽掉根级必需文件，但保留其它文件 —— 这样条目列表非空，
                   触发的是 missing_entry（正是 code-scholar 遇到的那条），
                   而不是 invalid_archive（空包）。两者是不同判据，不能混。
    nested_extra ：整体多套一层同名目录，用来复现「多套一层」这类真实事故。
    """
    name = "fixture-skill" if kind == "Skill" else "fixture-expert"
    # 每个变体用独立目录 —— 复用同名目录会让上一轮建的文件残留，
    # 造出「以为抽掉了、其实还在」的假样本（本轮就踩过一次）。
    variant = f"{name}{'-nested' if nested_extra else ''}{'-noreq' if drop_required else ''}"
    d = root / variant
    d.mkdir(parents=True, exist_ok=True)
    if kind == "Skill":
        if not drop_required:
            (d / "SKILL.md").write_text("---\nname: fixture-skill\n---\n", encoding="utf-8")
        (d / "notes.md").write_text("占位，保证条目列表非空\n", encoding="utf-8")
    else:
        (d / ".codebuddy-plugin").mkdir(parents=True, exist_ok=True)
        (d / "agents").mkdir(parents=True, exist_ok=True)
        if not drop_required:
            (d / ".codebuddy-plugin" / "plugin.json").write_text('{"name":"fixture-expert"}', encoding="utf-8")
        (d / "agents" / "fixture-expert.md").write_text("---\nname: fixture-expert\n---\n", encoding="utf-8")
        (d / "skills" / "inner").mkdir(parents=True, exist_ok=True)
        (d / "skills" / "inner" / "SKILL.md").write_text("---\nname: inner\n---\n", encoding="utf-8")

    if nested_extra:
        wrap = root / f"_wrap_{variant}"
        shutil.rmtree(wrap, ignore_errors=True)
        for f in sorted(d.rglob("*")):
            if f.is_file():
                dest = wrap / name / variant / f.relative_to(d)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
        src = wrap
    else:
        src = d

    base = root / f"{variant}.zip"
    base.unlink(missing_ok=True)
    with zipfile.ZipFile(base, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(src.rglob("*")):
            if f.is_file():
                zf.write(f, str(f.relative_to(src)))

    # 回读确认：样本真的长成我以为的样子（不确认就可能拿错样本去验证脚本）
    entries, _ = entry_paths(base)
    if kind == "Skill":
        present = any(e.endswith("SKILL.md") for e in entries)
        want = not drop_required
    else:
        present = any(e.endswith(".codebuddy-plugin/plugin.json") for e in entries)
        want = not drop_required
    if present != want:
        raise AssertionError(f"样本自检失败：{base.name} 期望必需文件{'在' if want else '不在'}，实际{'在' if present else '不在'}"
                             f"（条目={entries}）")
    return base


def selftest():
    print("═══ 自检 1：阳性对照（合规包必须全绿，否则判据本身有问题）═══")
    tmp = Path(tempfile.mkdtemp(prefix="pc-selftest-"))
    ok = True
    try:
        for kind in ("Skill", "Expert"):
            z = build_fixture(tmp, kind)
            r = check_zip(z)
            good = r["results"][kind]["pass"]
            print(f"  {kind:<7} 合规样本 → 按 {kind} 上传 {'✅ 通过' if good else '❌ 误判为失败'}")
            ok &= good

        print("\n═══ 自检 2：专家包用「技能」类型 → 必须复现出那条报错 ═══")
        z = build_fixture(tmp, "Expert")
        r = check_zip(z)
        iss = r["results"]["Skill"]["issues"]
        repro = any(i["code"] == "missing_entry" and i["params"].get("entry") == "SKILL.md" for i in iss)
        print(f"  专家包 → 按 Skill 上传：{'✅ 复现「未找到 SKILL.md」' if repro else '❌ 未复现'}")
        ok &= repro
        z2 = build_fixture(tmp, "Skill")
        r2 = check_zip(z2)
        iss2 = r2["results"]["Expert"]["issues"]
        repro2 = any(i["code"] == "missing_entry" and ".codebuddy-plugin/plugin.json" in str(i["params"]) for i in iss2)
        print(f"  技能包 → 按 Expert 上传：{'✅ 复现「未找到 .codebuddy-plugin/plugin.json」' if repro2 else '❌ 未复现'}")
        ok &= repro2

        print("\n═══ 自检 3：篡改验证（把合规包改坏，检查器必须变红）═══")
        flips = [
            ("技能包抽掉 SKILL.md", build_fixture(tmp, "Skill", drop_required=True), "Skill", True),
            ("专家包抽掉 plugin.json", build_fixture(tmp, "Expert", drop_required=True), "Expert", True),
            ("专家包多套一层目录", build_fixture(tmp, "Expert", nested_extra=True), "Expert", True),
        ]
        for label, z, vt, should_fail in flips:
            r = check_zip(z)
            failed = not r["results"][vt]["pass"]
            mark = "✅ 变红" if failed == should_fail else "❌ 没反应"
            print(f"  {label:<22} → 按 {vt} 上传 {mark}")
            if failed:
                for i in r["results"][vt]["issues"][:1]:
                    print(f"        · {CODE_LABEL.get(i['code'], i['code'])}  params={i['params']}")
            ok &= (failed == should_fail)

        print("\n═══ 自检 4：阴性对照（合规包不该被误伤）═══")
        for kind in ("Skill", "Expert"):
            z = build_fixture(tmp, kind)
            r = check_zip(z)
            noise = r["results"][kind]["issues"]
            print(f"  {kind:<7} 合规样本 → 应有类型上 {'✅ 0 条告警' if not noise else '❌ ' + str(noise)}")
            ok &= not noise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{'✅ 自检全部通过' if ok else '❌ 自检存在失败项 —— 先怀疑判据，再怀疑结论'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="复刻平台上传校验，本地预检 dist/ 产物")
    ap.add_argument("--zip", help="只检查这一个 zip")
    ap.add_argument("--dir", default=str(DIST),
                    help=f"产物目录（默认 {DIST}；它不是本仓库时用这个参数指过去）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--selftest", action="store_true", help="跑阳性对照与篡改验证")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if args.zip:
        targets = [Path(args.zip)]
    else:
        targets = sorted(Path(args.dir).glob("*.zip"))
    if not targets:
        print(f"没找到任何 zip —— 找过：{args.dir}", file=sys.stderr)
        print("  （默认依次找「脚本上一级/dist」与「当前目录/dist」两处）", file=sys.stderr)
        print("  产物目录不在默认位置时，指一下：--dir <产物目录>；或单个包：--zip <包.zip>", file=sys.stderr)
        print("  只想确认这个检查器本身有效：--selftest", file=sys.stderr)
        return 2

    reports = [check_zip(t) for t in targets if t.exists()]
    bad = [r["zip"] for r in reports if not r["results"].get(r["expected"], {}).get("pass", False)]
    if args.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    else:
        print(f"平台上传预检：{len(reports)} 个产物（规则复刻自 open.workbuddy.cn 前端，2026-09-25 抓取）\n")
        for r in reports:
            print(render(r))
            print()
        if bad:
            print(f"❌ {len(bad)} 个产物在其应有类型下会被驳回：{'、'.join(bad)}")
        else:
            print(f"✅ {len(reports)} 个产物都能通过各自的校验器。")
            print("   ⚠️ 但「能过」不等于「类型选对」—— 上传时务必按包的真实类型选：")
            print("      技能包 → 技能入口；专家/专家团 → 专家入口。选错必报「未找到 SKILL.md」。")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
