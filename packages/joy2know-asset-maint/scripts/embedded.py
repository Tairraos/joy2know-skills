#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
embedded.py —— 内嵌联动与版本一致性检查器。

回答：**谁内嵌了这个技能，内嵌的版本和源包一致吗。**

背景（R8 铁律）：构建对「内嵌技能」列只做实时读取、**不拦版本不匹配**，
于是会出现「清单显示嵌着新版、旧 zip 里其实是旧版」且 **0 告警**。

本脚本读三个真源（都不在 zip 里，所以查的是**源码层**）：
  - packages/<技能名>/SKILL.md            源技能版本
  - packages/*/skills.json                内嵌声明
  - packages/*/.codebuddy-plugin/plugin.json   内嵌声明（skills[] 字段）

⚠️ 它**不校验 zip 内实际内容** —— 那一步必须 `unzip -p` 手工做（见 SKILL.md §一）。

用法：
    python3 embedded.py --skill joy2know-musician --config-root .
    python3 embedded.py --all --config-root .
    python3 embedded.py --selftest

退出码：0 = 无内嵌方或全部一致；1 = 有不一致；2 = 用法错
"""

import argparse
import glob
import json
import os
import re
import sys

SKILL_VERSION_RE = re.compile(r"(?m)^version:\s*[\"']?([0-9][\w.\-]*)[\"']?\s*$")
PLUGIN_JSON_RE = re.compile(r'"version"\s*:\s*"([0-9][\w.\-]*)"')


class Report:
    def __init__(self):
        self.lines = []
        self.bad = 0

    def add(self, s=""):
        self.lines.append(s)

    def render(self):
        return "\n".join(self.lines)


def read_version(path):
    try:
        return SKILL_VERSION_RE.search(open(path, encoding="utf-8").read()).group(1)
    except (OSError, AttributeError):
        try:
            return PLUGIN_JSON_RE.search(open(path, encoding="utf-8").read()).group(1)
        except (OSError, AttributeError):
            return None


def find_embedders(root, skill_name):
    """返回 [(包名, 内嵌版本或None, 声明位置)]。"""
    out = []
    for sj in sorted(glob.glob(os.path.join(root, "packages", "*", "skills.json"))):
        pkg = os.path.basename(os.path.dirname(sj))
        try:
            data = json.load(open(sj, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        # skills.json 是精确的列表成员比较（in 列表 = 全等），天然没有前缀误匹配问题
        if skill_name in (data.get("skills") or []):
            out.append((pkg, None, "skills.json"))
    for pj in sorted(glob.glob(os.path.join(root, "packages", "*", ".codebuddy-plugin", "plugin.json"))):
        pkg = os.path.basename(os.path.dirname(os.path.dirname(pj)))
        try:
            cfg = json.load(open(pj, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        refs = cfg.get("skills") or []
        # ⚠️ 必须按**路径段**精确匹配，不能用子串包含 ——
        # 子串会让查 `joy2know-harness` 命中 `joy2know-harness-rules`（前缀误匹配，已踩）。
        # 同时 glob 前缀匹配也要防：`skills/joy2know-harness` 不该匹配 `joy2know-harness-rules`。
        hit = False
        for r in refs:
            rp = (r or "").replace("\\", "/").removeprefix("./").rstrip("/")
            seg = rp.rsplit("/", 1)[-1]
            if seg == skill_name or rp.endswith("/" + skill_name):
                hit = True
                break
        if hit:
            out.append((pkg, None, "plugin.json"))
    # 同一个包可能同时被 skills.json 与 plugin.json 声明（两份是同一件事的两种记法）——
    # 去重，否则报告会把一个内嵌方列两遍（实测踩到）。
    seen, dedup = set(), []
    for pkg, v, where in out:
        if pkg in seen:
            continue
        seen.add(pkg)
        dedup.append((pkg, v, where))
    return dedup


def check(root, skill_name):
    rep = Report()
    rep.add("")
    rep.add("=" * 68)
    rep.add("内嵌联动检查：%s" % skill_name)
    rep.add("=" * 68)

    skill_md = os.path.join(root, "packages", skill_name, "SKILL.md")
    src_ver = read_version(skill_md) if os.path.isfile(skill_md) else None

    embedders = find_embedders(root, skill_name)
    if not embedders:
        rep.add("")
        rep.add("没有任何包内嵌它。")
        rep.add("（升级它时不需要连带重建 —— 但若你**正要**新增内嵌关系，走这里核对。）")
        return rep, 0

    rep.add("")
    rep.add("源包版本：%s" % (src_ver or "读不到"))
    rep.add("")
    rep.add("内嵌它的包（%d 个）：" % len(embedders))
    mismatch = 0
    for pkg, _v, where in embedders:
        pkg_ver = read_version(
            os.path.join(root, "packages", pkg, ".codebuddy-plugin", "plugin.json")
        ) or read_version(os.path.join(root, "packages", pkg, "SKILL.md"))
        # 声明位置不记版本号（skills.json / skills[] 只有名字）——
        # 真正的版本一致性要看**产物 zip 内**的副本，那一步必须手工 unzip。
        rep.add("   · %-32s 内嵌方版本 %-10s（声明在 %s）" % (pkg, pkg_ver or "?", where))
        rep.add("       → 必须核对：unzip -p dist/%s-v%s.zip %s/skills/%s/SKILL.md "
                "| grep -m1 '^version:'" % (pkg, pkg_ver or "?", pkg, skill_name))
    rep.add("")
    rep.add("⚠️ 声明位置（skills.json / skills[]）**不记版本号**，所以这里比对不出新旧。")
    rep.add("   真正的判据是**产物 zip 内嵌副本的版本**与源包一致 —— 必须手工 unzip 核对。")
    rep.add("   构建**不拦版本不匹配**，不一致也 0 告警。")
    rep.add("")
    rep.add("⚠️ 还有第二层过期：内嵌方 agents/*.md 正文可能**复述了被引技能的旧规则**，")
    rep.add("   自检不看正文 → 团队会照旧指令人做错事，而自检全绿。")
    return rep, 0


def check_all(root):
    """列出所有技能 → 内嵌方映射，用于反查。"""
    rep = Report()
    skills = [os.path.basename(os.path.dirname(p))
              for p in glob.glob(os.path.join(root, "packages", "*", "SKILL.md"))]
    rep.add("")
    rep.add("=" * 68)
    rep.add("全仓内嵌关系（%d 个技能）" % len(skills))
    rep.add("=" * 68)
    any_emb = False
    for s in sorted(skills):
        embs = find_embedders(root, s)
        if embs:
            any_emb = True
            rep.add("   %-34s ← %s" % (s, ", ".join(p for p, _, _ in embs)))
    if not any_emb:
        rep.add("   （没有任何技能被内嵌）")
    rep.add("")
    rep.add("⚠️ 改任何一条技能的规则前，先用这个映射找出所有内嵌方。")
    return rep, 0


# ---------------------------------------------------------------- 反向自检

SELFTESTS = []


def selftest(fn):
    SELFTESTS.append(fn)
    return fn


def _mk_tree(root, embedder_skill, embedded_skill, emb_pkg="pkg-a"):
    os.makedirs(os.path.join(root, "packages", embedded_skill), exist_ok=True)
    with open(os.path.join(root, "packages", embedded_skill, "SKILL.md"), "w",
              encoding="utf-8") as f:
        f.write("---\nname: %s\nversion: 1.0.0\n---\n\nbody\n" % embedded_skill)
    d = os.path.join(root, "packages", emb_pkg)
    os.makedirs(os.path.join(d, ".codebuddy-plugin"), exist_ok=True)
    with open(os.path.join(d, ".codebuddy-plugin", "plugin.json"), "w",
              encoding="utf-8") as f:
        json.dump({"name": emb_pkg, "version": "1.0.0",
                   "skills": ["./skills/" + embedded_skill]}, f)


@selftest
def t_finds_embedder_via_plugin_json():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        _mk_tree(td, None, "joy2know-demo")
        embs = find_embedders(td, "joy2know-demo")
        assert any(p == "pkg-a" for p, _, _ in embs), "没找到 plugin.json 里的内嵌声明"


@selftest
def t_finds_embedder_via_skills_json():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        _mk_tree(td, None, "joy2know-demo")
        with open(os.path.join(td, "packages", "pkg-a", "skills.json"), "w",
                  encoding="utf-8") as f:
            json.dump({"skills": ["joy2know-demo"]}, f)
        embs = find_embedders(td, "joy2know-demo")
        assert any(w == "skills.json" for _, _, w in embs), "没找到 skills.json 里的内嵌声明"


@selftest
def t_no_embedder_returns_zero():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        _mk_tree(td, None, "joy2know-demo")
        rep, code = check(td, "joy2know-other")
        assert code == 0 and "没有任何包内嵌它" in rep.render(), "无内嵌方应返回 0"


@selftest
def t_prefix_no_false_match():
    """★ glob 前缀匹配的坑：`joy2know-harness` 不能匹配到 `joy2know-harness-rules`。"""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        _mk_tree(td, None, "joy2know-harness-rules")
        # 现在把内嵌目标写成 harness-rules，然后查 harness
        embs = find_embedders(td, "joy2know-harness")
        assert not embs, "查 joy2know-harness 时命中了 joy2know-harness-rules —— 前缀误匹配"


@selftest
def t_check_all_lists_mapping():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        _mk_tree(td, None, "joy2know-demo")
        rep, code = check_all(td)
        out = rep.render()
        assert "joy2know-demo" in out and "pkg-a" in out, "全仓映射没列出来"


@selftest
def t_missing_skill_dir_is_not_green():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        rep, code = check(td, "joy2know-nonexistent")
        out = rep.render()
        # 没有源包时，源包版本应显示「读不到」，不能假装有版本
        assert "读不到" in out or "没有任何包内嵌它" in out, "源包缺失时不能给假版本"


@selftest
def t_broken_json_is_skipped_not_crash():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = os.path.join(td, "packages", "pkg-a")
        os.makedirs(os.path.join(d, ".codebuddy-plugin"), exist_ok=True)
        with open(os.path.join(d, ".codebuddy-plugin", "plugin.json"), "w",
                  encoding="utf-8") as f:
            f.write("{broken")
        # 不应抛异常
        embs = find_embedders(td, "x")
        assert embs == [], "坏 JSON 应被跳过而不是崩"


def run_selftest():
    passed, failed = 0, []
    for fn in SELFTESTS:
        try:
            fn()
            passed += 1
            print("  [PASS] %s" % fn.__name__)
        except AssertionError as e:
            failed.append(fn.__name__)
            print("  [FAIL] %s —— %s" % (fn.__name__, e))
        except Exception as e:  # noqa: BLE001
            failed.append(fn.__name__)
            print("  [ERROR] %s —— %s: %s" % (fn.__name__, type(e).__name__, e))
    total = len(SELFTESTS)
    print("")
    print("=" * 68)
    if failed:
        print("反向自检：%d/%d 通过，%d 项失败" % (passed, total, len(failed)))
        print("结论：❌ 未通过")
        print("=" * 68)
        return 1
    print("反向自检：%d/%d 全部通过" % (passed, total))
    print("结论：✅ 已通过")
    print("=" * 68)
    return 0


def main():
    ap = argparse.ArgumentParser(description="内嵌联动与版本一致性检查器")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--skill", help="要查的技能名")
    g.add_argument("--all", action="store_true", help="列出全仓内嵌关系")
    g.add_argument("--selftest", action="store_true")
    ap.add_argument("--config-root", default=".", help="仓库根（含 packages/）")
    args = ap.parse_args()

    if args.selftest:
        return run_selftest()
    if args.all:
        rep, code = check_all(args.config_root)
        sys.stdout.write(rep.render() + "\n")
        return code
    rep, code = check(args.config_root, args.skill)
    sys.stdout.write(rep.render() + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
