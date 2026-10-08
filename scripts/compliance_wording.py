#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合规用词门禁 —— 检查技能 / 专家 / 专家团的**对外文案**会不会让机器审核判成
「调用了 LLM 以外的AI 做内容生成」（进而要求补资质、加类目）。

背景（2026-10-08 客服问明，全仓通用）
------------------------------------
平台**机器审核**按「能力表象」判合规：名称 / 描述里出现「AI 生成 / 合成 / 制作 /
出片」一类词，就容易被判为涉及生成式 AI 服务 → 按「生成式 AI 需资质」要求补资质
或加类目。而本仓技能**只产出文本**（提示词 / 判据 / 清单 / 报告），**只用 LLM 与
本地工具**，不生成音图视频、不接任何生成式接口。**客服人工复审放行后，资质与类目
都不必动** —— 所以第一道防线就是**让文案一眼看出「只出文本」**。

⚠️ 这道门禁**只查对外文案**（名称 + 描述），不查正文 / references —— 正文要讲清
怎么用外部工具，属于必要信息；机器审核读的是卡片上那几个字段。

判据分级（与 docs/平台资产规范.md 第八节末小节一致）
--------------------------------------------------
**失败（XX）**  高危词直接命中「生成服务」语义，且**没有**否定式声明兜底 → 必改。
**提示（!!）**  高危词命中但同字段内**有**否定式声明（如「不生成任何音频」）→ 人工确认。
**通过（OK）**  无命中，或仅低危词。

反向对照（判据本身要能被验）
--------------------------
本脚本刻意支持 `--baseline-check`：它把每条规则**故意放宽**（去掉高危词表）后重跑，
若此时命中数不变，说明规则**根本没生效** —— 即判据是橡皮章。改判据后请跑一次。

用法
----
    python3 scripts/compliance_wording.py                    # 查全部包
    python3 scripts/compliance_wording.py packages/joy2know-cine-team
    python3 scripts/compliance_wording.py --baseline-check   # 反向验证判据有效性
"""

import json
import os
import re
import sys

# ── 判据的核心：动词 + 宾语 ─────────────────────────────────────────────
# ⚠️ **2026-10-08 修判据时的重大发现**：只看「有没有『生成』这个词」是错的。
# 首版判据在 28 个包里报出 18 处命中，逐条看下来**几乎全是误报** ——
#   「给**生成过**的图片建台账」  → 说的是**用户已有的素材**，不是我们产出
#   「按 token **生成**页面代码」 → 生成的是**代码**，不是媒体
#   「不适用于直接**生成** .pptx」→ 否定句
#   「参考反思式**生成**框架」→ 学术框架名
# **平台机器审核的判据也不是「有没有这个词」，而是「产物是不是媒体文件」。**
# 所以判据必须是**动词 → 宾语**的配对：高危动词**且**宾语是媒体 → 真风险。
RISK_VERBS_EN = [
    r"generat(e|es|ed|ing|ion)", r"synthesi[sz]e[sd]?", r"synthesi[sz]ing",
    r"render(s|ed|ing)?", r"compose[sd]?", r"produc(e|es|ed|ing|ion)",
    r"create[sd]?", r"export(s|ed|ing)?",
    r"convert(s|ed|ing)?",          # convert text into a video
    r"upscale[sd]?", r"inpaint(ing|ed)?",
    r"voice[- ]clon(e|ing|ed)", r"face[- ]swap",
]
RISK_VERBS_ZH = ["生成", "合成", "渲染", "出图", "生图", "出片", "成片",
                 "克隆", "换脸", "换声", "配音", "导出", "导出视频", "导出音频"]

# 媒体宾语 —— 与高危动词配对才判失败
MEDIA_OBJ = [
    r"videos?", r"clips?", r"animations?", r"films?", r"footage",
    r"audio", r"music", r"songs?", r"tracks?", r"sound", r"voice-?overs?",
    r"images?", r"pictures?", r"photos?", r"artwork", r"illustrations?",
    r"renders?", r"vocal", r"speech", r"avatars?", r"3d models?", r"assets?",
]
MEDIA_OBJ_ZH = ["视频", "影片", "片段", "动画", "音频", "音乐", "歌", "曲子", "声音",
                "配音", "人声", "图片", "图像", "画", "插画", "照片", "素材",
                "语音", "模型文件", "3d 模型"]

# 非媒体产物 —— 命中也不判失败（我们真正的产出都是这一类）
TEXTUAL_OBJ = [
    r"code", r"scripts?", r"markdown", r"\bmd\b", r"text", r"prompts?",
    r"lists?", r"tables?", r"reports?", r"specs?", r"json", r"yaml",
    r"\bcsv\b", r"html", r"diagrams?", r"charts?", r"slides?", r"docs?",
    r"documents?", r"files?\b", r"plan", r"outline", r"tokens?\b",
]
TEXTUAL_OBJ_ZH = ["代码", "脚本", "文本", "提示词", "清单", "表格", "报告", "文档",
                  "说明", "大纲", "计划", "规范", "看板", "页面", "笔记", "台账",
                  "地图", "卡", "锚点", "结构", "字段"]

# ── 低危词：单独出现不构成风险，只作提示 ───────────────────────────────
LOW_EN = [r"\bAI\b", r"\bmodel(s)?\b", r"\bprompt(s|ing)?\b", r"\bvideo\b",
          r"\baudio\b", r"\bimage[s]?\b", r"\bmusic\b", r"\bfilm\b",
          r"\bconvert(s|ed|ing)?\b", r"\bcreative\b", r"\bproduction\b"]
LOW_ZH = ["AI", "模型", "提示词", "视频", "音频", "图像", "画面", "音乐", "影片"]

# ── 否定式声明：出现即视为已自证「不生成」 ──────────────────────────────
DISCLAIMER = [
    r"不生成", r"不接入任何生成", r"不调用任何生成", r"不带账号", r"不接入任何",
    r"纯文本", r"只产出文本", r"仅产出文本", r"文本产出", r"写作工具",
    r"does not generate", r"never generates", r"no generation",
    r"text-only", r"prompt-only", r"does not call any",
    r"no third-party ai", r"not a generation service",
    r"pure text", r"writes? (only )?text", r"text output only",
]

# 否定语境：句子本身在否定这件事（「不适用于直接生成 X」「不是生成 X」）
NEGATION_CTX = [
    # 中文否定式：⚠️ 「一律不接 / 一概不… / 都不… / 不…了」这类**带副词**的写法最容易被漏掉
    # （2026-10-08 实测：`conversation-digest` 的「非 WorkBuddy 的对话一律不接」就属这类，
    #  词表里没有「不接」而只有「不适用/不包括」，导致假红灯。）
    r"不适用", r"不包括", r"不提供", r"不会", r"不做", r"不是", r"无需", r"不能",
    r"不接", r"不读", r"不产", r"不写", r"不支持", r"不含", r"不碰",
    r"一律不", r"一概不", r"都不", r"不予", r"不设", r"不跑",
    r"只(读|处理|支持|接|做|面向)", r"仅(读|处理|支持|接|做|面向)",
    r"not ", r"never ", r"no ", r"without ", r"does not ", r"cannot ", r"excludes ",
]
DISCLAIMER_WINDOW = 400  # 否定式声明的搜索窗口（字符）


def _hits(text, pats_en, pats_zh):
    """返回命中的词形列表（去重、保留原文大小写以便定位）。"""
    out = []
    for p in pats_en:
        for m in re.finditer(p, text, re.I):
            out.append(m.group(0))
    for w in pats_zh:
        if w in text:
            out.append(w)
    return sorted(set(out), key=str.lower)


def _has_disclaimer(text):
    return any(re.search(p, text, re.I) for p in DISCLAIMER)


def _in_negative_ctx(text, pos, window_before=90, window_after=40):
    """命中位置附近是否有否定语境词。

    ⚠️ 窗口是**非对称**的（前 90 / 后 40）—— 2026-10-08 实测出来的：
    否定词几乎总在句子**开头**、命中词在从句末尾（中文先否定后举例）。
    对称 60/60 会漏掉 `joy2know-conversation-digest` 的这句假红灯：
      「非 WorkBuddy 的对话**一律不接**：ChatGPT / Claude 等平台的对话**导出**…以及 PDF / Word / **图片**…」
    「一律不接」距「导出」88 字，对称窗口够不着 → 被误判成「我们导出图片」。
    """
    a, b = max(0, pos - window_before), min(len(text), pos + window_after)
    window = text[a:b]
    return any(re.search(p, window, re.I) for p in NEGATION_CTX)


def _flatten(v, prefix=""):
    """把 plugin.json 里 {zh, en} 形态的字段摊平成 [(路径, 文本)]。"""
    if isinstance(v, str):
        return [(prefix, v)] if v.strip() else []
    if isinstance(v, dict):
        out = []
        for k, sub in v.items():
            out += _flatten(sub, f"{prefix}.{k}" if prefix else k)
        return out
    return []


# 技能：frontmatter 字段 → 中文名
SKILL_FIELDS = ["display_name", "display_name_en", "description",
                "description_zh", "description_en"]
# 专家 / 团：plugin.json 字段（含嵌套 dict 形式）
EXPERT_FIELDS = ["profession", "displayName", "description", "displayDescription"]

DISCLAIMER_WINDOW = 400  # 否定式声明的搜索窗口（字符）


def _hits(text, pats_en, pats_zh):
    """返回命中的词形列表（去重、保留原文大小写以便定位）。"""
    out = []
    for p in pats_en:
        for m in re.finditer(p, text, re.I):
            out.append(m.group(0))
    for w in pats_zh:
        if w in text:
            out.append(w)
    return sorted(set(out), key=str.lower)


def _has_disclaimer(text):
    for p in DISCLAIMER:
        if re.search(p, text, re.I):
            return True
    return False


def _flatten(v, prefix=""):
    """把 plugin.json 里 {zh, en} 形态的字段摊平成 [(路径, 文本)]。"""
    if isinstance(v, str):
        return [(prefix, v)] if v.strip() else []
    if isinstance(v, dict):
        out = []
        for k, sub in v.items():
            out += _flatten(sub, f"{prefix}.{k}" if prefix else k)
        return out
    return []


def parse_frontmatter_fields(fm):
    """把 frontmatter 抽成 {字段: 完整值}。

    ⚠️ 必须处理 YAML 折行块（`>-` / `|` / `>-` 后跟缩进续行）。
    **曾经的真实缺陷**：用逐行正则匹配，在折行块上只抓到 `>-` 两个字符
    —— 全仓最长的那条 `description`（几百字）**根本没进检查，却报「通过」**。
    这是最典型的假绿灯：查了等于没查。现在按缩进续行整体收拢。
    """
    out = {}
    lines = fm.split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r"^([A-Za-z_][\w\-]*):\s*(.*)$", ln)
        if not m:
            i += 1
            continue
        key, first = m.group(1), m.group(2).strip()
        if first in (">-", ">", "|", "|-", "|+"):          # 折行 / 块标量
            i += 1
            buf = []
            while i < len(lines):
                nxt = lines[i]
                # 续行必须缩进；顶格或新字段出现即止
                if nxt.strip() and not nxt.startswith((" ", "\t")):
                    break
                if re.match(r"^[A-Za-z_][\w\-]*:", nxt):
                    break
                buf.append(nxt.strip())
                i += 1
            out[key] = " ".join(x for x in buf if x)
        else:
            out[key] = first.strip('"').strip("'").strip()
            i += 1
    return out


def collect_fields(base, only=None):
    """收集所有包的 (包名, 字段路径, 文本) 三元组。"""
    rows = []
    pkgs = sorted(os.listdir(base))
    for name in pkgs:
        root = os.path.join(base, name)
        if not os.path.isdir(root) or name.startswith("."):
            continue
        if only and name != only:
            continue
        # 技能
        sk = os.path.join(root, "SKILL.md")
        if os.path.exists(sk):
            txt = open(sk, encoding="utf-8").read()
            m = re.search(r"^---\n(.*?)\n---", txt, re.S)
            if m:
                fields = parse_frontmatter_fields(m.group(1))
                for f in SKILL_FIELDS:
                    if fields.get(f):
                        rows.append((name, f, fields[f]))
        # 专家 / 专家团
        pj = os.path.join(root, ".codebuddy-plugin", "plugin.json")
        if os.path.exists(pj):
            try:
                d = json.load(open(pj, encoding="utf-8"))
            except Exception as e:
                rows.append((name, "plugin.json", f"__PARSE_ERROR__ {e}"))
                continue
            for f in EXPERT_FIELDS:
                for path, val in _flatten(d.get(f), f):
                    rows.append((name, f"plugin.json:{path}", val))
    return rows


def _media_obj_hits(text, verb_pos):
    """高危动词的**紧邻宾语**位置是否有媒体词。

    判据只看动词后 60 字内 —— 远距离出现的媒体词多半是「触发词」段落里的枚举，
    不构成「我们产出媒体」的表述。
    """
    a, b = verb_pos, min(len(text), verb_pos + 60)
    seg = text[a:b]
    en = _hits(seg, MEDIA_OBJ, [])
    zh = _hits(seg, [], MEDIA_OBJ_ZH)
    return sorted(set(en + zh), key=str.lower)


def _verb_positions(text, verbs_en, verbs_zh):
    """返回 [(词形, 起始位置)]，中英文都收。"""
    out = []
    for p in verbs_en:
        for m in re.finditer(p, text, re.I):
            out.append((m.group(0), m.start()))
    for w in verbs_zh:
        for m in re.finditer(re.escape(w), text):
            out.append((w, m.start()))
    return sorted(out, key=lambda x: x[1])


def check(base, only=None, disable_risk=False):
    """跑一遍判据。返回 (fail, warn, ok_rows)。disable_risk=True 用于反向验证。"""
    rows = collect_fields(base, only)
    if not rows:
        print(f"⚠️ 没收集到任何对外文案（包目录：{base}）—— 判据没生效，不是「全部通过」")
        return ([("无", "未收集到字段")], [], [])

    fails, warns, oks = [], [], []
    for pkg, path, text in rows:
        if text.startswith("__PARSE_ERROR__"):
            fails.append((pkg, f"{path}: {text}"))
            continue
        verbs_en = [] if disable_risk else RISK_VERBS_EN
        verbs_zh = [] if disable_risk else RISK_VERBS_ZH
        pairs = _verb_positions(text, verbs_en, verbs_zh)
        if not pairs:
            lo = _hits(text, LOW_EN, LOW_ZH)
            oks.append((pkg, f"{path}: " + (f"仅低危词 {lo}" if lo else "无风险词")))
            continue

        real, negated, textual = [], [], []
        for verb, pos in pairs:
            objs = _media_obj_hits(text, pos)
            if not objs:
                continue                      # 动词的宾语不是媒体 → 不算
            if _in_negative_ctx(text, pos):
                negated.append((verb, objs))  # 「不适用于直接生成视频」
            else:
                real.append((verb, objs))

        if real:
            if _has_disclaimer(text):
                warns.append((pkg, f"{path}: {real} 但同字段有否定式声明「不生成…」→ 人工确认声明是否覆盖"))
            else:
                shows = [f"{v}→{o}" for v, o in real[:4]]
                fails.append((pkg, f"{path}: 高危动词+媒体宾语 {shows} 且无否定式声明 → 必改"))
        elif negated:
            shows = [f"{v}→{o}" for v, o in negated[:3]]
            oks.append((pkg, f"{path}: 否定语境中的媒体词 {shows}（已声明不做）"))
        else:
            textual = _hits(text, TEXTUAL_OBJ, TEXTUAL_OBJ_ZH)
            lo = _hits(text, LOW_EN, LOW_ZH)
            note = f"动词+非媒体产物 {textual[:4]}" if textual else (f"仅低危词 {lo}" if lo else "无风险词")
            oks.append((pkg, f"{path}: {note}"))
    return (fails, warns, oks)


# ── 反向验证样本（--selftest）─────────────────────────────────────────────
# 两组都用**同一份判据**跑，结果必须相反 —— 否则判据是橡皮章。
# 样本在临时目录现造，不落仓库（避免「样本自己也要过门禁」的循环）。
BAD_SKILL = """---
name: joy2know-selftest-bad
display_name: 晓得·自测违规
display_name_en: joy2know SelfTest Bad
description: >-
  输入一句话，直接生成成片的视频与配音素材，导出 MP4 与音频文件，
  还能把图片渲染成动态视频。触发词：生成视频、配音、成片导出。
description_zh: 输入一句话，直接生成视频与配音素材并导出文件。
description_en: >-
  Turn one sentence into a finished video with voiceover and export MP4 and audio files;
  also renders still images into motion clips.
category: 内容创作 > 视频
version: 1.0.0
author: Tairraos - 晓得乐
---

# selftest-bad（反向样本 · 应当报失败）
"""

GOOD_SKILL = """---
name: joy2know-selftest-good
display_name: 晓得·自测合规
display_name_en: joy2know SelfTest Good
description: >-
  把创意写成能直接粘贴的文本：逐镜提示词、角色锚点与配乐提示词包，
  外加一份拍摄排期表。**只产出文本，不生成任何图片或视频，不接入任何生成接口。**
  触发词：写提示词、分镜文本、配乐提示词、排期表。
description_zh: 把创意写成可直接粘贴的提示词文本与排期表；不生成任何图片或视频。
description_en: >-
  Writes one creative idea into paste-ready text: per-shot prompts, character anchors and a music
  prompt pack, plus a shooting schedule. Prompt text only: does not generate any image or video and
  calls no generation API.
category: 工具 > 办公
version: 1.0.0
author: Tairraos - 晓得乐
---

# selftest-good（对照样本 · 不应报失败）
"""


def _write_samples(root):
    """在临时目录里造两组样本，返回 (bad_packages_dir, good_packages_dir)。"""
    import tempfile
    bad = tempfile.mkdtemp(prefix="cw-selftest-bad-")
    good = tempfile.mkdtemp(prefix="cw-selftest-good-")
    for root_dir, fname, pkg in ((bad, BAD_SKILL, "joy2know-selftest-bad"),
                                  (good, GOOD_SKILL, "joy2know-selftest-good")):
        d = os.path.join(root_dir, "packages", pkg)
        os.makedirs(d)
        open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8").write(fname)
    return os.path.join(bad, "packages"), os.path.join(good, "packages")


def selftest():
    bad_dir, good_dir = _write_samples(None)
    b_fail, b_warn, _ = check(bad_dir)
    g_fail, _, _ = check(good_dir)

    print("\n═══ 合规用词门禁 · 反向验证（--selftest） ═══")
    print(f"  违规样本包：joy2know-selftest-bad  → 失败 {len(b_fail)} · 提示 {len(b_warn)}")
    for pkg, msg in b_fail:
        print(f"    [XX] {pkg} · {msg}")
    print(f"  合规样本包：joy2know-selftest-good → 失败 {len(g_fail)}")

    ok = True
    if not b_fail:
        print("  ❌ 违规样本没报失败 —— 判据失效（橡皮章），它的「通过」结果不可信")
        ok = False
    if g_fail:
        print("  ❌ 合规样本也报失败 —— 判据过宽（假红灯），先去规范文档对口径")
        ok = False
    if ok:
        print("  ✅ 两组结果相反，判据既不漏也不滥")
    import shutil
    shutil.rmtree(os.path.dirname(bad_dir), ignore_errors=True)
    shutil.rmtree(os.path.dirname(good_dir), ignore_errors=True)
    return 0 if ok else 3


def main():
    if "--selftest" in sys.argv:
        return selftest()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    baseline = "--baseline-check" in sys.argv
    # 默认扫 packages/；也接受直接传单个包目录（上溯一层）
    base_arg = args[0] if args else os.path.join(os.getcwd(), "packages")
    if not os.path.isdir(base_arg):
        # 传进来的可能是仓库根，补上 packages/
        cand = os.path.join(base_arg, "packages")
        if os.path.isdir(cand):
            base_arg = cand
        else:
            print(f"目录不存在: {base_arg}")
            return 2

    base = os.path.abspath(base_arg)
    # 传进来的若是仓库根（其下有 packages/），下潜一层
    if os.path.isdir(os.path.join(base, "packages")):
        base = os.path.join(base, "packages")
    only = None
    # 传单个包目录时上溯到 packages/ 那一层，否则一个包都认不出来
    if os.path.exists(os.path.join(base, "SKILL.md")) or \
       os.path.exists(os.path.join(base, ".codebuddy-plugin", "plugin.json")):
        only = os.path.basename(base)
        base = os.path.dirname(base)
    if not os.path.isdir(os.path.join(base, "packages")) and \
       not any(os.path.isdir(os.path.join(base, d)) and
               (os.path.exists(os.path.join(base, d, "SKILL.md")) or
                os.path.exists(os.path.join(base, d, ".codebuddy-plugin")))
               for d in (os.listdir(base) if os.path.isdir(base) else [])):
        print(f"⚠️ {base} 下没有任何包目录（既没有 <包名>/SKILL.md，也没有 .codebuddy-plugin/）")
        return 2

    fails, warns, oks = check(base, only, disable_risk=baseline)

    tag = "（反向验证：判据已关闭）" if baseline else ""
    print(f"\n═══ 合规用词门禁{tag} ═══")
    print(f"扫描根：{base}\n")

    for pkg, msg in fails:
        print(f"  [XX] {pkg} · {msg}")
    for pkg, msg in warns:
        print(f"  [!!] {pkg} · {msg}")
    for pkg, msg in oks:
        print(f"  [OK] {pkg} · {msg}")

    print(f"\n  通过 {len(oks)} · 提示 {len(warns)} · 失败 {len(fails)}")

    if baseline:
        # 反向验证：判据关闭后应当**命中数为 0**；若仍与正向一致 → 判据没生效
        total = len(fails) + len(warns)
        if total == 0:
            print("  ✅ 反向验证通过：关掉判据后零命中，说明正向结果确由判据产生")
            return 0
        print(f"  ❌ 反向验证失败：关掉判据后仍有 {total} 条命中 —— 判据没真正生效")
        return 3

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())