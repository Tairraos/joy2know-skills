#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_refs.py —— 内嵌引用审计（零依赖，Python 标准库）

用法：
    python3 scripts/audit_refs.py            # 全仓审计，有问题退出码 1
    python3 scripts/audit_refs.py --selftest  # 内置正反样本

为什么需要它（2026-10-18 实证）：
`joy2know-lyricist` 1.0.0 被平台驳回，驳回原文：
    「资产包缺少必需资源2 项：技能「joy2know-mureka-musician」；
      技能「joy2know-musician」（agents/joy2know-lyricist.md 引用）」
    「评级结论：内置文件缺失」

**平台会扫agent 正文里出现的技能包名，把它们当成「引用」，并要求必须内嵌。**
这不是我们自己的判据，是平台的硬性校验 —— 人眼扫不出来（本轮 18 个专家/团全查，
只有两个音乐大师交叉提及却都过审了），所以必须机器查。

两条审计规则：
  R1「引用未内嵌」：agent 正文提到的每个真实技能包名，都必须出现在 skills.json 里
  R2「平台交叉」：三个音乐大师（suno / mureka / tianyin）互相不得提及、不得内嵌对方家族的技能
     —— 用户只会用其中一个平台，交叉会让用户困惑，也会引发R1

排除项（重要，否则全是误报）：
  - 成员名（agents/*.md 的文件名）不是技能包名 —— 专家团成员常与技能同名或近似
  - 包自身名不算引用
  - skill包（只有 SKILL.md、没有 .codebuddy-plugin/）不参与 —— 平台对技能正文
    与 agent 正文的扫描口径不同（2026-10-18实证：lyric-design 技能正文点名过
    musician / mureka-musician，技能本身过审了，而 lyricist 专家被驳）
"""

import json
import os
import re
import sys
import glob

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_RE = re.compile(r'joy2know-[a-z0-9-]+')

# 平台家族：大师 -> 自己家族关键词（技能名里含这些词的就是自家人）
FAMILY = {
    "joy2know-suno-maestro": "suno",
    "joy2know-mureka-maestro": "mureka",
    "joy2know-tianyin-maestro": "tianyin",
}


def scan(root=REPO):
    """返回 findings 列表 [{level, id, pkg, msg, hint}]"""
    F = []

    def add(fid, level, pkg, msg, hint=None):
        item = {"id": fid, "level": level, "pkg": pkg, "msg": msg}
        if hint:
            item["hint"] = hint
        F.append(item)

    # 真实技能包（有 SKILL.md 的）
    real_skills = {os.path.basename(d) for d in glob.glob(os.path.join(root, "packages", "*"))
                   if os.path.isfile(os.path.join(d, "SKILL.md"))}
    # 成员名（agents/*.md 的文件名）—— 不是技能包名，必须排除
    member_names = {os.path.splitext(os.path.basename(a))[0]
                    for a in glob.glob(os.path.join(root, "packages", "*", "agents", "*.md"))}

    for d in sorted(glob.glob(os.path.join(root, "packages", "*"))):
        name = os.path.basename(d)
        pj = os.path.join(d, ".codebuddy-plugin", "plugin.json")
        if not os.path.isfile(pj):
            continue                      # 技能包不参与（见文件头说明）
        try:
            cfg = json.load(open(pj, encoding="utf-8"))
        except Exception as e:            # noqa: BLE001
            add("R0", "FAIL", name, f"plugin.json 读不了：{e}")
            continue

        sj = os.path.join(d, "skills.json")
        if os.path.isfile(sj):
            embedded = set(json.load(open(sj, encoding="utf-8")).get("skills") or [])
        else:
            embedded = {s.split("/")[-1] for s in (cfg.get("skills") or [])}

        mentioned = set()
        for a in glob.glob(os.path.join(d, "agents", "*.md")):
            mentioned |= set(SKILL_RE.findall(open(a, encoding="utf-8").read()))
        mentioned.discard(name)
        # 只保留真实技能包名，排除成员名
        refs = sorted(x for x in mentioned if x in real_skills and x not in member_names)

        # ---- R1 引用未内嵌 ----
        missing = [x for x in refs if x not in embedded]
        if missing:
            add("R1", "FAIL", name,
                f"agent 正文引用了未内嵌的技能：{', '.join(missing)}",
                "⭐ 平台会判「资产包缺少必需资源」直接驳回（2026-10-18 lyricist 实证）。"
                "两条出路：① 把这些技能加进 skills.json 内嵌；"
                "② 若本包不该依赖它们（自成一体），改 agent 措辞去掉点名")

        # ---- R2 平台交叉 ----
        mine = FAMILY.get(name)
        if mine:
            # 自家豁免：本线的技能（joy2know-<mine>-*）不算交叉，只有别家平台的才算
            def fam_of(skill):
                for fam, key in FAMILY.items():
                    if re.search(rf"joy2know-{key}", skill):
                        return key
                return None
            foreign = sorted({r for r in refs if fam_of(r) and fam_of(r) != mine})
            if foreign:
                add("R2", "FAIL", name,
                    f"{mine} 线提到了别家平台的技能：{', '.join(foreign)}",
                    "⭐ 用户只会用其中一个平台：suno 不依赖 mureka，mureka 不依赖 suno，天音同理。"
                    "正文只提自己的技能包名，不许并列写「A / B」")

    return F


def report(findings, title="内嵌引用审计"):
    fails = [f for f in findings if f["level"] == "FAIL"]
    if not findings:
        print(f"[OK] {title} —— 全部通过（无引用缺失、无平台交叉）")
    for f in findings:
        print(f"[{f['level']}] {f['id']} {f['pkg']}: {f['msg']}")
        if f.get("hint"):
            print(f"       ↳ {f['hint']}")
    print(f"—— {len(fails)} FAIL ——")
    return 1 if fails else 0


# ---------------------------------------------------------------------------
# 自检：造一个「引用未内嵌」和一个「平台交叉」的临时仓，确认都能被抓到
# ---------------------------------------------------------------------------

def selftest():
    import shutil
    import tempfile
    cases = []

    def build_repo(files):
        d = tempfile.mkdtemp(prefix="audit-refs-")
        for rel, content in files.items():
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
        return d

    def good_files():
        return {
            # 两个真实技能包
            "packages/joy2know-alpha/SKILL.md": "---\nname: joy2know-alpha\n---\n",
            "packages/joy2know-beta/SKILL.md": "---\nname: joy2know-beta\n---\n",
            # 一个专家：引用了 alpha 且已内嵌 alpha
            "packages/joy2know-demo/.codebuddy-plugin/plugin.json":
                '{"name":"joy2know-demo","skills":["./skills/joy2know-alpha"]}',
            "packages/joy2know-demo/skills.json": '{"skills":["joy2know-alpha"]}',
            "packages/joy2know-demo/agents/joy2know-demo.md":
                "---\nname: joy2know-demo\n---\n走 `joy2know-alpha` 那条路径。\n",
        }

    def baseline():
        r = scan(good_files.__wrapped__() if False else _TEMP[0])
        if r:
            return f"规范仓不该有问题，实得 {[(f['id'], f['pkg'], f['msg']) for f in r]}"
        return None
    cases.append(("基线 · 引用已内嵌 → 通过", baseline))

    def missing_ref():
        files = good_files()
        # 改成引用 beta 但没内嵌
        files["packages/joy2know-demo/agents/joy2know-demo.md"] = \
            "---\nname: joy2know-demo\n---\n走 `joy2know-alpha` 与 `joy2know-beta`。\n"
        d = build_repo(files)
        r = scan(d)
        if not any(f["id"] == "R1" for f in r):
            return f"引用未内嵌应报 R1，实得 {[(f['id'], f['msg']) for f in r]}"
        shutil.rmtree(d, ignore_errors=True)
        return None
    cases.append(("① 引用未内嵌 → R1 FAIL（平台驳回的成因）", missing_ref))

    def member_false_positive():
        """成员名不是技能包名 —— 专家团成员常与技能近似，不能误报"""
        files = good_files()
        files["packages/joy2know-team/.codebuddy-plugin/plugin.json"] = \
            '{"name":"joy2know-team","skills":[]}'
        files["packages/joy2know-team/skills.json"] = '{"skills":[]}'
        files["packages/joy2know-team/agents/joy2know-team-lead.md"] = \
            "---\nname: joy2know-team\n---\n主理 `joy2know-team-lead` 负责统筹。\n"
        d = build_repo(files)
        r = scan(d)
        if any(f["id"] == "R1" for f in r):
            return f"成员名被误判成技能引用：{[(f['pkg'], f['msg']) for f in r]}"
        shutil.rmtree(d, ignore_errors=True)
        return None
    cases.append(("② 成员名不是技能包名 → 不误报", member_false_positive))

    def cross_family():
        """suno 大师正文提到 mureka-musician → R2"""
        files = good_files()
        # ⭐ 被引用的技能必须是「真实存在的包」（有 SKILL.md），否则会被 refs 的
        #   「只保留真实技能包名」过滤掉 —— 造不出交叉，判据就永远验不到
        files["packages/joy2know-suno-musician/SKILL.md"] = "---\nname: joy2know-suno-musician\n---\n"
        files["packages/joy2know-mureka-musician/SKILL.md"] = "---\nname: joy2know-mureka-musician\n---\n"
        files["packages/joy2know-suno-maestro/.codebuddy-plugin/plugin.json"] = \
            '{"name":"joy2know-suno-maestro","skills":["./skills/joy2know-suno-musician"]}'
        files["packages/joy2know-suno-maestro/skills.json"] = '{"skills":["joy2know-suno-musician"]}'
        # ⭐ 必须造真正的交叉：suno 大师正文里提 **mureka**-musician（别家），不是自家
        files["packages/joy2know-suno-maestro/agents/joy2know-suno-maestro.md"] = \
            "---\nname: joy2know-suno-maestro\n---\n" \
            "单曲走 `joy2know-suno-musician`，另一条参考 `joy2know-mureka-musician`。\n"
        d = build_repo(files)
        r = scan(d)
        if not any(f["id"] == "R2" for f in r):
            return f"平台交叉应报 R2，实得 {[(f['id'], f['msg']) for f in r]}"
        shutil.rmtree(d, ignore_errors=True)
        return None
    cases.append(("③ 平台交叉（suno 提 mureka）→ R2 FAIL", cross_family))

    def own_family_ok():
        """自家技能不算交叉 —— suno 大师提 suno-musician 是天经地义，判成交叉就全是误报"""
        files = good_files()
        files["packages/joy2know-suno-musician/SKILL.md"] = "---\nname: joy2know-suno-musician\n---\n"
        files["packages/joy2know-mureka-musician/SKILL.md"] = "---\nname: joy2know-mureka-musician\n---\n"
        files["packages/joy2know-suno-maestro/.codebuddy-plugin/plugin.json"] = \
            '{"name":"joy2know-suno-maestro","skills":["./skills/joy2know-suno-musician"]}'
        files["packages/joy2know-suno-maestro/skills.json"] = '{"skills":["joy2know-suno-musician"]}'
        files["packages/joy2know-suno-maestro/agents/joy2know-suno-maestro.md"] = \
            "---\nname: joy2know-suno-maestro\n---\n单曲走 `joy2know-suno-musician`。\n"
        d = build_repo(files)
        r = scan(d)
        if any(f["id"] == "R2" for f in r):
            return f"自家技能被误判成交叉：{[(f['pkg'], f['msg']) for f in r]}"
        shutil.rmtree(d, ignore_errors=True)
        return None
    cases.append(("④ 自家技能 → 不算交叉（防误报）", own_family_ok))

    # 跑
    _TEMP = [build_repo(good_files())]
    bad = 0
    for name, fn in cases:
        try:
            err = fn()
        except Exception as e:  # noqa: BLE001
            err = f"抛异常：{e}"
        finally:
            pass
        if err:
            bad += 1
            print(f"[FAIL] 自检项「{name}」：{err}")
    shutil.rmtree(_TEMP[0], ignore_errors=True)
    print(f"自检 {len(cases)} 项{'全部通过' if bad == 0 else f'中有 {bad} 项未通过'}")
    return 0 if bad == 0 else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 2
    return report(scan())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
