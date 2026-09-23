#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkBuddy 资产包四道自检

用法:
    python3 selfcheck.py <交付目录>
        <交付目录> 下应包含  {skill-name}/  和/或  {expert-name}/
    或:
    python3 selfcheck.py <单个包目录>
        （如 packages/joy2know-mr，内部会自动提到父目录处理）
    或:
    python3 selfcheck.py <交付目录> <skill-name> <expert-name>

零第三方依赖（PyYAML 不可用时自动降级为字段级正则校验）。

**一个包都没识别到时会明确报错**，不会输出「全部自检通过」——
「什么都没查」报绿是比报错更危险的事（老版对单个包目录跑就会出现这种情况）。

--------------------------------------------------------------------
来源与权威性（2026-09-23 搬入本仓库）
--------------------------------------------------------------------
本文件原为个人技能 `WorkBuddy资产包生产` 的 scripts/selfcheck.py，
2026-09-23 复制进本仓库，目的是让**本仓库不再依赖任何本机技能目录** ——
任何 harness 克隆下来就能跑 `pnpm build` 完成字段级自检。

**本仓库这一份是权威版本。** 改了校验规则先改这里；个人技能里那份是通用版本，
两边若都动过，以本仓库为准，并把规则回灌过去（规则只允许有一份真源）。

与本仓库构建流程的两点适配：
1. `pnpm build` 把包复制到**暂存目录**后才调本脚本（源包里没有内嵌技能，直接对源
   目录跑会误报「skills 路径不存在」）。暂存父目录里同时有 `<包名>/` 与 `<包名>.zip`，
   所以 zip 的第一层与体积检查仍然生效；单独跑而没先打包时，缺 zip 记提示而非失败。
2. 包内「发布前检测报告」（packages/<包名>/<包名>.md）是开发期文档、不进包，
   构建时不复制进暂存目录，因此不会被本脚本看到。
"""

import json
import os
import re
import struct
import subprocess
import sys

# 专家/专家团 categoryId 合法取值 —— 官方文档「行业分类」一节（/docs/expert）。
# 全平台共用这一份清单：专家团页面没有自己的分类表，也必须从这里选。
# 注意：不存在 "00-ExpertTeam" 之类的「专家团专属分类」（曾据此误填，上传时报
# 「categoryId 不在合法分类列表中」）。15 类之外一律判错。
VALID_CATEGORY_IDS = {
    "01-ProductDesign",      # 产品设计
    "02-Engineering",        # 技术工程
    "03-GameSpatial",        # 游戏空间
    "04-DataAI",             # 数据智能
    "05-MarketingGrowth",    # 营销增长
    "06-ContentCreative",    # 内容创作
    "07-SalesCommerce",      # 销售商务
    "08-FinanceInvestment",  # 金融投资
    "09-OperationsHR",       # 运营人力
    "10-ProjectQuality",     # 项目质量
    "11-SecurityCompliance", # 法务安全
    "12-IndustryConsultant", # 行业顾问
    "13-TencentZone",        # 腾讯专家
    "14-WorldWise",          # 全球发展
    "15-Education",          # 教育
}

issues, oks, notes = [], [], []


def ok(m):
    oks.append(m)


def bad(m):
    issues.append(m)


def parse_frontmatter(path):
    try:
        t = open(path, encoding="utf-8").read()
    except OSError:
        return None, ""
    m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    return (m.group(1) if m else None), t


def autodetect(base):
    """从目录里猜出 skill 名与 expert 名。"""
    skill = expert = None
    for d in sorted(os.listdir(base)):
        p = os.path.join(base, d)
        if not os.path.isdir(p) or d.startswith("."):
            continue
        if os.path.exists(os.path.join(p, "SKILL.md")):
            skill = d
        if os.path.exists(os.path.join(p, ".codebuddy-plugin", "plugin.json")):
            expert = d
    return skill, expert


def check_skill(base, name):
    sk = os.path.join(base, name, "SKILL.md")
    if not os.path.exists(sk):
        bad(f"[skill] 找不到 {name}/SKILL.md")
        return
    fm, txt = parse_frontmatter(sk)
    if fm is None:
        bad(f"[skill] {name}/SKILL.md 缺 YAML frontmatter")
        return

    required = ["name", "display_name", "display_name_en", "description",
                "description_zh", "description_en", "category", "version", "author"]
    missing = [f for f in required if not re.search(rf"^{f}\s*:", fm, re.M)]
    if missing:
        bad(f"[skill] frontmatter 缺字段: {', '.join(missing)}")
    else:
        ok(f"[skill] {len(required)} 个必填 frontmatter 字段齐全")

    d = {}
    try:
        import yaml
        d = yaml.safe_load(fm) or {}
        ok("[skill] frontmatter YAML 解析通过")
    except ImportError:
        notes.append("[skill] PyYAML 不可用，已降级为字段级校验；装 pyyaml 后可做完整 YAML 解析复检")
    except Exception as e:
        bad(f"[skill] frontmatter YAML 解析失败: {e}")

    if d.get("name") and d["name"] != name:
        bad(f"[skill] name 字段 {d['name']!r} 与目录名 {name!r} 不一致")

    # 冒号后空一格
    for ln in fm.split("\n"):
        if re.match(r"^\s*[\w\-]+\s*:[^\s>|]", ln) and not ln.rstrip().endswith(":"):
            bad(f"[skill] 疑似冒号后未空格: {ln!r}")

    # @references 引用落地
    refs = set(re.findall(r"@references/([\w\-.]+)", txt))
    for r in refs:
        p = os.path.join(base, name, "references", r)
        if os.path.exists(p):
            ok(f"[skill] 引用有效: @references/{r}")
        else:
            bad(f"[skill] 引用失效: @references/{r}")
    if not refs:
        ok("[skill] 无 @references 引用（未使用 references/）")

    # 子目录白名单（官方结构仅允许 references/ scripts/ templates/）
    allowed = {"references", "scripts", "templates"}
    skills_dir = os.path.join(base, name)
    for d in sorted(os.listdir(skills_dir)):
        p = os.path.join(skills_dir, d)
        if os.path.isdir(p) and not d.startswith(".") and d not in allowed:
            bad(f"[skill] 非白名单子目录: {d}/（官方仅允许 references/ scripts/ templates/）")
    stray = [f for f in sorted(os.listdir(skills_dir))
             if not os.path.isdir(os.path.join(skills_dir, f))
             and f != "SKILL.md" and not f.startswith(".")]
    if stray:
        ok(f"[skill] 根目录含非必需文件（不影响解析）: {', '.join(stray)}")

    # category 取值提示（官方示例值为 writing）
    m = re.search(r"^category:\s*(\S+)", fm, re.M)
    if m:
        ok(f"[skill] category = {m.group(1)}")

    # author 署名非空
    m = re.search(r"^author:\s*(.+)$", fm, re.M)
    if m and m.group(1).strip():
        ok(f"[skill] author 署名: {m.group(1).strip()!r}")
    else:
        bad("[skill] author 为空（官方必填：合作方名称）")


def check_expert(base, name, skill_names):
    root = os.path.join(base, name)
    pj_path = os.path.join(root, ".codebuddy-plugin", "plugin.json")
    if not os.path.exists(pj_path):
        bad(f"[expert] 找不到 {name}/.codebuddy-plugin/plugin.json")
        return
    try:
        pj = json.load(open(pj_path, encoding="utf-8"))
        ok("[expert] plugin.json JSON 解析通过")
    except Exception as e:
        bad(f"[expert] plugin.json 解析失败: {e}")
        return

    for k in ["name", "version", "description", "author", "agents", "skills",
              "expertType", "agentName", "displayName", "profession",
              "displayDescription", "avatar", "categoryId", "plugin",
              "tags", "quickPrompts"]:
        if k not in pj:
            bad(f"[expert] plugin.json 缺字段: {k}")
    ok("[expert] plugin.json 字段遍历完成")

    # ---- 官方硬约束（open.workbuddy.cn/docs/expert）----
    # 1) displayDescription.zh 中文字数须 40-50
    dd = pj.get("displayDescription")
    if isinstance(dd, dict) and isinstance(dd.get("zh"), str):
        n = len(re.findall(r"[\u4e00-\u9fff]", dd["zh"]))
        if 40 <= n <= 50:
            ok(f"[expert] displayDescription.zh 汉字 {n} 字（官方要求 40-50）")
        else:
            bad(f"[expert] displayDescription.zh 汉字 {n} 字，超出官方要求 40-50")

    # 2) defaultInitPrompt 必须与 quickPrompts[0] 完全一致
    dips, qps = pj.get("defaultInitPrompt"), pj.get("quickPrompts")
    if isinstance(dips, dict) and isinstance(qps, list) and qps:
        if dips == qps[0]:
            ok("[expert] defaultInitPrompt == quickPrompts[0]（官方硬约束）")
        else:
            bad(f"[expert] defaultInitPrompt={dips} 与 quickPrompts[0]={qps[0]} 不一致，官方要求二者相同")

    # 3) tags / quickPrompts 固定 3 个
    for k in ("tags", "quickPrompts"):
        v = pj.get(k)
        if isinstance(v, list):
            if len(v) == 3:
                ok(f"[expert] {k} 数量=3（官方固定 3）")
            else:
                bad(f"[expert] {k} 数量={len(v)}（官方固定 3）")

    # 4) avatar 必须在 avatars/ 下（官方结构）
    av_field = pj.get("avatar", "")
    if av_field and not str(av_field).startswith("avatars/"):
        bad(f"[expert] avatar 应为 avatars/ 下相对路径，当前 {av_field!r}")

    # 5) author 署名非空
    au = pj.get("author")
    if isinstance(au, dict):
        if au.get("name"):
            ok(f"[expert] author.name 署名: {au.get('name')!r}")
        else:
            bad("[expert] author.name 为空")
    elif au is None:
        bad("[expert] author 为空（官方必填）")

    for pair in ["displayName", "profession", "displayDescription"]:
        v = pj.get(pair)
        if not (isinstance(v, dict) and {"en", "zh"} <= set(v)):
            bad(f"[expert] {pair} 未中英成对")

    if pj.get("name") != name:
        bad(f"[expert] plugin.name {pj.get('name')!r} 与目录名 {name!r} 不一致")
    if pj.get("plugin") != name:
        bad(f"[expert] plugin 字段与 name 不一致")

    # categoryId 必须在官方 15 类行业分类白名单内（专家与专家团同一份清单）。
    # 平台侧报错原文：「categoryId "XX" 不在合法分类列表中」。
    cid = pj.get("categoryId")
    if cid in VALID_CATEGORY_IDS:
        ok(f"[expert] categoryId 合法: {cid}")
    elif cid is None:
        bad("[expert] categoryId 缺失（官方必填，取官方 15 类行业分类之一）")
    else:
        bad(f"[expert] categoryId 不在合法分类列表中: {cid!r}（合法取值见官方文档「行业分类」，共 15 类）")

    # 6) 专家团根目录：settings.json 与 setting.json 两个名字都要有，内容一致
    #    平台校验器实查 settings.json（缺了直接「解析失败」，2026-09-17 实测），
    #    而官方可下载模板 trading-team.zip 里用的是 setting.json —— 官方自己不一致。
    if pj.get("expertType") == "team":
        lead = (pj.get("teamInfo") or {}).get("leadAgent") or pj.get("agentName")
        seen = {}
        for fn in ("settings.json", "setting.json"):
            fp = os.path.join(root, fn)
            if not os.path.exists(fp):
                bad(f"[expert] 专家团缺 {fn}（平台查 settings.json，官方模板用 setting.json，两个都要放）")
                continue
            try:
                c = json.load(open(fp, encoding="utf-8"))
            except Exception as e:
                bad(f"[expert] {fn} 不是合法 JSON: {e}")
                continue
            seen[fn] = c
            if c.get("agent") == lead:
                ok(f"[expert] {fn} 主理人声明正确: agent={lead}")
            else:
                bad(f"[expert] {fn} 的 agent={c.get('agent')!r} 与主理人 {lead!r} 不一致")
        if len(seen) == 2:
            if json.dumps(seen["settings.json"], sort_keys=True) != json.dumps(seen["setting.json"], sort_keys=True):
                bad("[expert] settings.json 与 setting.json 内容不一致（应完全相同）")
            else:
                ok("[expert] settings.json 与 setting.json 内容一致")

    # 源目录 与 构建暂存目录 的差别：源包里 `skills/` 与专家头像都是**构建时才注入**的。
    # 判据：包根还有 skills.json（构建时会删掉它）。对源目录跑自检时，这两样缺失属正常，
    # 记提示而不是失败 —— 本项目不接受「需要人习惯性划掉的假红灯」。
    src_tree = os.path.exists(os.path.join(root, "skills.json"))

    for a in pj.get("agents", []):
        p = os.path.join(root, a)
        (ok if os.path.exists(p) else bad)(f"[expert] agents 路径 {'存在' if os.path.exists(p) else '缺失'}: {a}")
    for s in pj.get("skills", []):
        p = os.path.join(root, s, "SKILL.md")
        if os.path.exists(p):
            ok(f"[expert] skills 路径 存在: {s}")
        elif src_tree:
            notes.append(f"[expert] 内嵌技能 {s} 尚未生成（源目录里本就不该有，"
                         f"构建时才从 packages/ 复制；请以构建暂存目录的自检结果为准）")
        else:
            bad(f"[expert] skills 路径 缺失: {s}")

    av = os.path.join(root, pj.get("avatar", ""))
    if os.path.exists(av):
        b = open(av, "rb").read()
        if b[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", b[16:24])
            if (w, h) == (512, 512) and len(b) <= 500 * 1024:
                ok(f"[expert] 头像合法 PNG 512x512, {len(b)/1024:.1f}KB")
            else:
                bad(f"[expert] 头像规格不合规: {w}x{h}, {len(b)/1024:.1f}KB（应 512x512 / ≤500KB）")
        else:
            bad("[expert] 头像不是 PNG（未做尺寸校验）")
    else:
        # 源目录里没有包内头像，真源在仓库根 avatars/<包名>.png（构建时注入）
        src_icon = os.path.join(os.path.dirname(base), "avatars", name + ".png")
        if src_tree and os.path.exists(src_icon):
            notes.append(f"[expert] 头像由构建时从 avatars/{name}.png 注入（源目录里没有是正常的），"
                         f"规格已由构建工具校验")
        else:
            bad(f"[expert] avatar 缺失: {pj.get('avatar')}")

    # agent frontmatter 与 agentName 一致
    # 专家团：只有主理人的 name 等于 agentName，其余成员各自的 name 应等于 members[].id
    #（实测 agents[] 的文件名去 .md 后与 members[].id 严格一一对应）。
    member_ids = {m.get("id") for m in (pj.get("members") or [])}
    agent_name = pj.get("agentName")
    for a in pj.get("agents", []):
        p = os.path.join(root, a)
        afm, _ = parse_frontmatter(p)
        if afm:
            m = re.search(r"^name:\s*(\S+)", afm, re.M)
            n = m.group(1).strip() if m else None
            if n == agent_name:
                ok(f"[expert] agent name == agentName: {n}")
            elif n in member_ids:
                ok(f"[expert] agent name={n} 是团队成员（命中 members[].id）")
            else:
                bad(f"[expert] agent name={n!r} 既非 agentName={agent_name!r}，也不在 members[].id 中")
            for ln in afm.split("\n"):
                if re.match(r"^\s*[\w\-]+\s*:[^\s>|]", ln) and not ln.rstrip().endswith(":"):
                    bad(f"[expert] 疑似冒号后未空格: {ln!r}")

    # 主源与内嵌副本一致性
    for s in pj.get("skills", []):
        folder = os.path.basename(s.rstrip("/"))
        src = os.path.join(base, folder)
        dst = os.path.join(root, s)
        if os.path.isdir(src) and os.path.isdir(dst):
            # 排除两样「设计如此、不是漂移」的东西：
            #   icon.png      —— 独立技能包不带图标（官方技能包无图标槽位），
            #                    内嵌进专家包时才由构建复制出 skills/<技能名>/icon.png。
            #   <技能名>.md   —— 发布前检测报告，是**开发期文档**，构建时不复制进包。
            # 这两样之外，任何内容差异照抓（已用篡改主源的样本做反向验证）。
            r = subprocess.run(
                ["diff", "-r", "-x", "icon.png", "-x", folder + ".md", src, dst],
                capture_output=True)
            (ok if r.returncode == 0 else bad)(
                f"[expert] 主源 {folder}/ 与内嵌副本{'一致' if r.returncode == 0 else '不一致（已漂移）'}")


def check_packages(base, skill, expert):
    """体积上限按包类型判定：技能包 3MB / 专家包 20MB。

    注意：`pnpm build` 在**暂存目录**上跑本脚本。那一层里同时有 `<包名>/` 与
    `<包名>.zip`（构建工具先把 zip 写在暂存父目录再校验），所以这里通常能拿到 zip；
    若有人单独跑本脚本而没先打包，则记 **提示**而不是失败 —— 免得稳定多一条假红灯。
    """
    for n, lim in ((skill, 3 * 1024 * 1024), (expert, 20 * 1024 * 1024)):
        if not n:
            continue
        z = os.path.join(base, n + ".zip")
        if not os.path.exists(z):
            notes.append(f"[zip] 未找到 {n}.zip（跳过 zip 检查；构建流程里由 build.mjs 单独校验第一层与体积）")
            continue
        s = os.path.getsize(z)
        (ok if s <= lim else bad)(
            f"[zip] {n}.zip {s/1024:.1f}KB（上限 {lim//1024//1024}MB）"
            if s <= lim else f"[zip] {n}.zip {s/1024:.1f}KB 超出上限 {lim//1024//1024}MB")
        r = subprocess.run(["unzip", "-l", z], capture_output=True, text=True)
        if re.search(rf"^\s*0\s+\S+\s+\S+\s+{re.escape(n)}/$", r.stdout, re.M):
            ok(f"[zip] {n}.zip 第一层为包目录")
        else:
            bad(f"[zip] {n}.zip 第一层疑似不是 {n}/（检查是否多套了一层）")
        junk = re.findall(r"^\s*\d+\s+\S+\s+\S+\s+(\S*(?:\.DS_Store|__MACOSX|\.pyc)\S*)$",
                          r.stdout, re.M)
        if junk:
            bad(f"[zip] {n}.zip 含临时文件: {junk[:5]}（重新打包时排除）")


def check_secrets(base):
    pat = re.compile(r"(sk-[A-Za-z0-9]{16,}|AKID[A-Za-z0-9]{10,}|"
                     r"api[_-]?key\s*[:=]\s*['\"][^'\"]{12,})", re.I)
    hits = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.endswith((".md", ".json", ".py", ".js", ".sh", ".txt")):
                p = os.path.join(root, f)
                try:
                    if pat.search(open(p, encoding="utf-8", errors="ignore").read()):
                        hits.append(p)
                except OSError:
                    pass
    (ok if not hits else bad)(
        "[sec] 包内未发现硬编码凭证" if not hits else f"[sec] 疑似凭证: {hits}")


def main():
    base_arg = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.isdir(base_arg):
        print(f"目录不存在: {base_arg}")
        return 2
    base = os.path.abspath(base_arg)

    # 允许直接把**单个包目录**传进来（`selfcheck.py packages/joy2know-mr`）：
    # 提到它的父目录，后续一律按「父目录下有 <包名>/」处理，源目录比对也就找得到主源。
    # 不这么做的话，对包目录跑 autodetect 会一个包都认不出来，然后静默输出
    # 「全部自检通过」—— 一项没查却报绿，比报错危险得多。
    self_name = None
    if os.path.exists(os.path.join(base, "SKILL.md")):
        self_name = os.path.basename(base)
        base = os.path.dirname(base)
    elif os.path.exists(os.path.join(base, ".codebuddy-plugin", "plugin.json")):
        self_name = os.path.basename(base)
        base = os.path.dirname(base)

    if len(sys.argv) > 3:
        skill, expert = sys.argv[2], sys.argv[3]
    elif self_name:
        if os.path.exists(os.path.join(base, self_name, "SKILL.md")):
            skill, expert = self_name, None
        else:
            skill, expert = None, self_name
    else:
        skill, expert = autodetect(base)

    print(f"自检目录: {base}")
    print(f"识别到  技能包={skill or '(无)'}  专家包={expert or '(无)'}\n")

    # 一个包都没识别出来 = 什么都没检查，这不是通过
    if not skill and not expert:
        bad("没有识别到任何包 —— **什么都没有检查**（这不是通过）。"
            "请把参数指向含 <包名>/ 的父目录，或直接指向单个包目录。")

    if skill:
        check_skill(base, skill)
    if expert:
        check_expert(base, expert, [skill] if skill else [])
    check_packages(base, skill, expert)
    check_secrets(base)

    print(f"通过 {len(oks)} 项")
    for o in oks:
        print("  [OK] " + o)
    if notes:
        print(f"\n提示 {len(notes)} 条（非失败）：")
        for nt in notes:
            print("  [!!] " + nt)
    if issues:
        print(f"\n问题 {len(issues)} 项：")
        for i in issues:
            print("  [XX] " + i)
        return 1
    print("\n=== 全部自检通过 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
