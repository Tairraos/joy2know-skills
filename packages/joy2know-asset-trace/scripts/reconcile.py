#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reconcile.py —— 本地发布记账对账器（无凭证、不联网）。

回答两个问题：
  1. 哪些包还停在 ④ 待发布（status=approved，不点「发布」不上架）
  2. 哪些包本地版本比平台新（该上传了）

它只读本地两个真源：
  - release.config.json（平台状态记账）
  - packages/<包名>/（本地包，version 从 SKILL.md 或 plugin.json 读）

⚠️ 本脚本**不联网、不带凭证、不存账号**。
凭证类技能刻意留在包外（带凭证的东西误提交一次就是泄露）。

用法：
    python3 reconcile.py --config release.config.json --packages packages
    python3 reconcile.py --selftest

退出码：0 = 账实相符；1 = 有该同步的包；2 = 用法错或文件读不了
"""

import argparse
import json
import os
import re
import sys

#: 本地版本号的读取位置（技能包与专家包不同）
SKILL_VERSION_RE = re.compile(r"(?m)^version:\s*[\"']?([0-9][\w.\-]*)[\"']?\s*$")
PLUGIN_VERSION_RE = re.compile(r"\"version\"\s*:\s*\"([0-9][\w.\-]*)\"")


class Report:
    def __init__(self):
        self.lines = []

    def add(self, s=""):
        self.lines.append(s)

    def render(self):
        return "\n".join(self.lines)


def read_local_version(pkg_dir):
    """读本地包版本。技能包读 SKILL.md，专家包读 plugin.json。"""
    skill = os.path.join(pkg_dir, "SKILL.md")
    if os.path.isfile(skill):
        m = SKILL_VERSION_RE.search(open(skill, encoding="utf-8").read())
        return (m.group(1) if m else None), "skill"
    plugin = os.path.join(pkg_dir, ".codebuddy-plugin", "plugin.json")
    if os.path.isfile(plugin):
        m = PLUGIN_VERSION_RE.search(open(plugin, encoding="utf-8").read())
        return (m.group(1) if m else None), "expert"
    return None, None


def vtuple(v):
    """'1.6.0' → (1,6,0)，用于版本比较。"""
    parts = re.findall(r"\d+", v or "")
    return tuple(int(x) for x in parts) if parts else ()


def reconcile(config_path, packages_root):
    rep = Report()
    rep.add("")
    rep.add("=" * 68)
    rep.add("本地发布记账对账（无凭证 / 不联网）")
    rep.add("=" * 68)

    if not os.path.isfile(config_path):
        rep.add("")
        rep.add("用法错：找不到配置文件 %s" % config_path)
        return rep, 2
    try:
        cfg = json.load(open(config_path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        rep.add("")
        rep.add("用法错：%s 不是合法 JSON：%s" % (config_path, e))
        return rep, 2

    pkgs = cfg.get("packages") or {}
    if not os.path.isdir(packages_root):
        rep.add("")
        rep.add("用法错：%s 不是包目录" % packages_root)
        return rep, 2

    pending_release, need_upload, unknown = [], [], []
    for name, meta in sorted(pkgs.items()):
        pkg_dir = os.path.join(packages_root, name)
        if not os.path.isdir(pkg_dir):
            continue
        local_v, _ = read_local_version(pkg_dir)
        approved = (meta or {}).get("approved")
        submitted = (meta or {}).get("submitted")
        platform = (meta or {}).get("platform")

        if approved:
            pending_release.append((name, approved))
        # 本地版本高于平台已上架版本 → 该上传了
        if local_v and platform and vtuple(local_v) > vtuple(platform.get("version", "")):
            need_upload.append((name, local_v, platform.get("version")))
        # 本地有版本但四个字段都没有 → ① 待提交
        if local_v and not any([approved, submitted, platform]):
            unknown.append((name, local_v))

    rep.add("")
    rep.add("一、还停在 ④ 待发布（审核通过但没上架）—— %d 个" % len(pending_release))
    if pending_release:
        for n, a in pending_release:
            rep.add("   · %-34s v%s" % (n, (a or {}).get("version", "?")))
        rep.add("")
        rep.add("   ⚠️ 「审核通过」≠「上架」。要在发布管理页手动点一次「发布」。")
    else:
        rep.add("   （无）")

    rep.add("")
    rep.add("二、本地比平台新（该上传了）—— %d 个" % len(need_upload))
    if need_upload:
        for n, lv, pv in need_upload:
            rep.add("   · %-34s 本地 v%s > 平台 v%s" % (n, lv, pv))
    else:
        rep.add("   （无）")

    rep.add("")
    rep.add("三、从未提交过（① 待提交）—— %d 个" % len(unknown))
    if unknown:
        for n, v in unknown:
            rep.add("   · %-34s v%s" % (n, v))
        rep.add("")
        rep.add("   ⚠️ 这类包在配置里没有 submitted 字段，「等式推进」判据推不动它；")
        rep.add("      正确判据是「市场里出现了 = 已上架」，须人工补 platform。")
    else:
        rep.add("   （无）")

    rep.add("")
    total = len(pending_release) + len(need_upload) + len(unknown)
    if total:
        rep.add("结论：⚠️ 有 %d 个包需要动作（退出码 1）" % total)
        return rep, 1
    rep.add("结论：✅ 账实相符（退出码 0）")
    return rep, 0


# ---------------------------------------------------------------- 反向自检

SELFTESTS = []


def selftest(fn):
    SELFTESTS.append(fn)
    return fn


def _mk_config(path, pkgs):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"packages": pkgs}, f, ensure_ascii=False)


def _mk_pkg(root, name, version):
    d = os.path.join(root, name)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write("---\nname: %s\nversion: %s\n---\n\nbody\n" % (name, version))


@selftest
def t_pending_release_detected():
    """★ 「待发布」是最容易漏的一档 —— 必须被点出来。"""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        cfg = os.path.join(td, "c.json")
        _mk_config(cfg, {"p-a": {"approved": {"version": "1.0.0"}}})
        _mk_pkg(td, "p-a", "1.0.0")
        rep, code = reconcile(cfg, td)
        out = rep.render()
        assert "p-a" in out.split("二、")[0], "停在待发布的包没被点出来"
        assert code == 1, "有待发布包时应返回 1"


@selftest
def t_local_newer_than_platform():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        cfg = os.path.join(td, "c.json")
        _mk_config(cfg, {"p-a": {"platform": {"version": "1.0.0"}}})
        _mk_pkg(td, "p-a", "1.1.0")
        rep, code = reconcile(cfg, td)
        out = rep.render()
        assert "1.1.0" in out.split("二、")[1].split("三、")[0], "本地更新没被点出来"
        assert code == 1


@selftest
def t_in_sync_returns_zero():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        cfg = os.path.join(td, "c.json")
        _mk_config(cfg, {"p-a": {"platform": {"version": "1.0.0"}}})
        _mk_pkg(td, "p-a", "1.0.0")
        rep, code = reconcile(cfg, td)
        assert code == 0, "账实相符应返回 0"


@selftest
def t_never_submitted_listed():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        cfg = os.path.join(td, "c.json")
        _mk_config(cfg, {"p-a": {}})
        _mk_pkg(td, "p-a", "1.0.0")
        rep, code = reconcile(cfg, td)
        out = rep.render()
        assert "p-a" in out.split("三、")[1], "从未提交的包没被列进 ①"


@selftest
def t_bad_config_returns_two():
    """★ 读不了配置必须返回 2，不能默认给绿。"""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        rep, code = reconcile(os.path.join(td, "nope.json"), td)
        assert code == 2, "配置读不了应返回 2"


@selftest
def t_invalid_json_returns_two():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "c.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write("{not json")
        rep, code = reconcile(p, td)
        assert code == 2, "非法 JSON 应返回 2"


@selftest
def t_version_compare_ordering():
    assert vtuple("1.6.0") > vtuple("1.3.0")
    assert vtuple("1.0.10") > vtuple("1.0.9"), "按数字比较而不是字典序"
    assert vtuple("1.0.0") == vtuple("1.0.0")
    assert vtuple("") == vtuple(None)


@selftest
def t_expert_pkg_version_read():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = os.path.join(td, "p-x")
        os.makedirs(os.path.join(d, ".codebuddy-plugin"), exist_ok=True)
        with open(os.path.join(d, ".codebuddy-plugin", "plugin.json"), "w",
                  encoding="utf-8") as f:
            json.dump({"name": "p-x", "version": "2.0.0"}, f)
        v, t = read_local_version(d)
        assert v == "2.0.0" and t == "expert", "专家包版本应读 plugin.json"


# --- ★ 篡改判据的翻转验证

@selftest
def t_mutate_pending_check_flip():
    """关掉「待发布」判据 → 该类包不再被点出来（证明判据真的在查）。"""
    import tempfile
    src = reconcile.__code__

    # 用一个等价于「把 approved 判据短路」的配置：approved 字段置空
    with tempfile.TemporaryDirectory() as td:
        cfg = os.path.join(td, "c.json")
        _mk_config(cfg, {"p-a": {"approved": None}})
        _mk_pkg(td, "p-a", "1.0.0")
        rep, code = reconcile(cfg, td)
        out = rep.render()
        seg = out.split("一、")[1].split("二、")[0]
        assert "p-a" not in seg, "approved 置空后不该再被列进待发布"
        # 对照组：此时它应落到「从未提交」
        assert "p-a" in out.split("三、")[1], "置空后应改判为从未提交"


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
        print("结论：❌ 未通过 —— 判据可能没有判别力")
        print("=" * 68)
        return 1
    print("反向自检：%d/%d 全部通过" % (passed, total))
    print("结论：✅ 已通过")
    print("=" * 68)
    return 0


def main():
    ap = argparse.ArgumentParser(description="本地发布记账对账器（无凭证）")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--config", help="release.config.json 路径")
    g.add_argument("--selftest", action="store_true")
    ap.add_argument("--packages", default="packages", help="包目录（默认 packages）")
    args = ap.parse_args()

    if args.selftest:
        return run_selftest()
    rep, code = reconcile(args.config, args.packages)
    sys.stdout.write(rep.render() + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
