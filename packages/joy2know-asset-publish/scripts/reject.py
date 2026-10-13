#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reject.py —— 上传驳回处置判据器。

只回答一件事：**这个驳回要不要抬版本号。**

判据（2026-09-28 三次实证后订正）：
  这个资产有没有被平台**审核过**（2026-10-13 订正：旧口径写的是「有没有走到过『提交成功』」，
  但**自己撤回、还没被审过的，是不需要抬版本的**）。
    解析失败（描述超限 / 入口选错 / 结构不符） → 平台没占用版本号 → 修完**同名重传**
    被平台审核过（驳回 / 通过）              → 版本号已被记录    → **必须抬，内嵌它的包一起抬**
    （⚠️ 自己撤回、从未被审过 → **不用抬**；删掉草稿还能用原版本号重发）

用法：
    python3 reject.py --text "解析失败：描述字段超限"
    python3 reject.py --text "所选类目与应用类目不符" --skill joy2know-musician
    python3 reject.py --selftest

退出码：
    0  可自行处置（同名重传或按顺序走客服）
    1  **必须抬版本号**
    2  用法错 / 认不出是哪类驳回

设计原则：
  1. 判不出来时必须返回 2，**不能默认放行** —— 「不知道」比报错危险。
  2. 每条判据在 --selftest 里都有反向对照（含篡改判据表本身的翻转验证）。
  3. 不给绿就悄悄给红：必须把「为什么这么判」写进输出。
"""

import argparse
import re
import sys

# ---------------------------------------------------------------- 判据表

#: 「解析失败」类 —— 平台没占用版本号，修完可同名重传。
#: 长相：带「解析失败」前缀，多为字段/结构/入口问题。
#: ⚠️ 必须**中英双语**。早期只列中文，而平台侧可能返回英文原文
#: （实测样本 "Parse Failure: description_en too long" 判不出 → 返回 2 不放行）。
PARSE_FAILURE_HINTS = [
    "解析失败", "格式不符", "结构不符", "未找到", "不存在或无法读取",
    "描述字段超限", "字段缺失", "必填", "frontmatter",
    "parse failure", "parse error", "invalid", "malformed", "missing",
    "not found", "does not exist", "cannot be read", "exceeds", "too long",
    "required field", "json", "yaml",
]

#: 「被平台审核过（驳回）」类 —— 版本号已被占用，必须抬版本。
#: ⚠️ 注意区分：**自己撤回**（未被审）的不在此列，不需要抬版本。
#: 长相：不解析文件，而是说「类目/内容不符」这类审核结论。
SUBMITTED_BUT_REJECTED_HINTS = [
    "类目不符", "所选类目", "应用类目", "至少应包含", "深度合成", "ai创作", "ai 创作",
    "审核未通过", "不符合平台", "内容不符合", "涉及", "违规",
    "category mismatch", "category does not", "at least", "deep synthesis",
    "review failed", "not approved", "violat", "prohibited",
]

#: 平台侧的明确报错文案：同名重传已被占用的版本号。
VERSION_OCCUPIED_HINTS = [
    "必须大于当前最新版本", "版本号已被占用", "版本已存在",
]


class Report:
    def __init__(self):
        self.lines = []
        self.verdict = None          # "reupload" | "bump" | None
        self.need_bump = False
        self.reasons = []

    def add(self, s=""):
        self.lines.append(s)

    def render(self):
        return "\n".join(self.lines)


def classify(text):
    """返回 (verdict, reasons)。verdict ∈ {reupload, bump, None}。"""
    low = text.lower()
    reasons = []

    # ① 最高优先：平台自己说版本号被占用了 —— 这已经是「必须抬」的铁证
    for h in VERSION_OCCUPIED_HINTS:
        if h in text or h.lower() in low:
            reasons.append("命中平台报错 %r → 该版本号已被平台记录" % h)
            return "bump", reasons

    # ② 解析失败类 → 同名重传
    for h in PARSE_FAILURE_HINTS:
        if h.lower() in low:
            reasons.append("命中解析失败信号 %r → 平台未占用版本号" % h)
            return "reupload", reasons

    # ③ 审核驳回类 → 必须抬版本
    for h in SUBMITTED_BUT_REJECTED_HINTS:
        if h in text or h.lower() in low:
            reasons.append("命中审核驳回信号 %r → 提交已成功、版本号被占用" % h)
            return "bump", reasons

    return None, reasons


def advise(verdict, reasons, skill_name):
    r = Report()
    r.add("")
    r.add("=" * 68)
    r.add("驳回处置判据")
    r.add("=" * 68)
    if verdict is None:
        r.add("")
        r.add("**判不出是哪类驳回。** 已按规则返回 2（不放行）。")
        r.add("")
        r.add("下一步（人工判，别猜）：")
        r.add("  1. 回发布管理页看这条驳回的**完整原文**，贴进来再跑一次；")
        r.add("  2. 判据：带「解析失败」前缀的多为**同名重传**；")
        r.add("     说「所选类目与应用类目不符」的多为**必须抬版本**；")
        r.add("  3. ⚠️ 拿不准就当「必须抬」处理 —— 抬错的代价是白传一次，")
        r.add("     不抬的代价是**解析失败卡死**，且下一次还得抬。")
        return r, 2

    r.add("")
    for x in reasons:
        r.add("  · %s" % x)
    r.add("")

    if verdict == "reupload":
        r.add("结论：**可同名重传**（退出码 0）")
        r.add("")
        r.add("理由：平台没有占用这个版本号，修完用同一个版本重传即可。")
        r.add("")
        r.add("动作：")
        r.add("  1. 修字段/结构/入口问题；")
        r.add("  2. 重跑 platformcheck --zip（单值参数，一次一个）；")
        r.add("  3. 同名重传。")
        return r, 0

    r.add("结论：**必须抬版本号**（退出码 1）")
    r.add("")
    r.add("理由：这次提交已经「成功」过，版本号被平台记录。")
    r.add("      同名重传必报「包内版本号「X」必须大于当前最新版本「X」。")
    r.add("")
    r.add("动作：")
    r.add("  1. 抬版本号（实质内容改动 → patch；新增能力/规则/角色 → minor；")
    r.add("     字段或包结构改动 → major）；")
    r.add("  2. 五处同步：SKILL.md 的 version / plugin.json / 包内 README「## 版本」行 /")
    r.add("     检测报告头四行 / 正文引用；")
    r.add("  3. 若走的是类目驳回，按处置顺序**先找客服**，别急着改包；")
    if skill_name:
        r.add("")
        r.add("⚠️ **必须连带查「谁内嵌了它」**（R8 铁律）：")
        r.add("  grep -rl \"%s\" packages/*/skills.json "
              "packages/*/.codebuddy-plugin/plugin.json" % skill_name)
        r.add("  构建对内嵌技能列只实时读取、**不拦版本不匹配** →")
        r.add("  会出现「清单嵌新版、旧 zip 里是旧版」且 0 告警。")
        r.add("  内嵌方也要抬版本并重建。")
    else:
        r.add("")
        r.add("⚠️ **必须连带查「谁内嵌了它」**（R8 铁律）：")
        r.add("  grep -rl \"<技能名>\" packages/*/skills.json "
              "packages/*/.codebuddy-plugin/plugin.json")
        r.add("  有内嵌方 → 一起抬版本并重建（否则 0 告警地嵌着旧版）。")
    return r, 1


# ---------------------------------------------------------------- 反向自检

SELFTESTS = []


def selftest(fn):
    SELFTESTS.append(fn)
    return fn


@selftest
def t_parse_failure_is_reupload():
    for t in ["解析失败：描述字段超限",
              "解析失败：description_en 超过 1000 字符",
              "结构不符：zip 第一层必须是包目录",
              "未找到 SKILL.md，请确保该路径文件存在"]:
        v, _ = classify(t)
        assert v == "reupload", "%r 应判为可同名重传，实得 %r" % (t, v)


@selftest
def t_submitted_rejection_needs_bump():
    for t in ["所选类目与应用类目不符",
              "您的应用至少应包含『深度合成 > AI创作』类目",
              "审核未通过：内容不符合平台规范"]:
        v, _ = classify(t)
        assert v == "bump", "%r 应判为必须抬版本，实得 %r" % (t, v)


@selftest
def t_version_occupied_is_bump():
    """★ 平台自己说版本号被占用了 —— 这是最硬的铁证，优先级最高。"""
    for t in ["解析失败：包内版本号「1.6.0」必须大于当前最新版本「1.6.0」"]:
        v, _ = classify(t)
        assert v == "bump", "%r 应判为必须抬版本，实得 %r" % (t, v)


@selftest
def t_occupied_beats_parse_failure():
    """★ 同一句话里同时有「解析失败」和「版本号必须大于」——
    判据必须取「版本被占用」这条，否则会给出「可同名重传」的错误建议。"""
    v, _ = classify("解析失败：包内版本号「1.6.0」必须大于当前最新版本「1.6.0」")
    assert v == "bump", "同时含两类信号时没有取优先级更高的那条"


@selftest
def t_english_text_is_classified():
    """★ 平台可能返回英文原文 —— 判据表必须中英双语，否则英文驳回判不出。

    早期只列中文，实测英文样本 verdict=None → 返回 2 不放行。
    """
    for t in ["Parse Failure: description_en too long",
              "Invalid package structure",
              "Required field display_name is missing"]:
        v, _ = classify(t)
        assert v == "reupload", "英文解析失败 %r 判不出，实得 %r" % (t, v)
    v, _ = classify("Category mismatch: deep synthesis required")
    assert v == "bump", "英文审核驳回判不出，实得 %r" % v


@selftest
def t_unknown_returns_none():
    v, _ = classify("服务器开小差了，请稍后再试")
    assert v is None, "认不出时应返回 None（调用方会返回 2），而不是猜一个"


@selftest
def t_empty_is_none():
    v, _ = classify("")
    assert v is None, "空输入应判不出"


@selftest
def t_case_insensitive():
    v, _ = classify("Parse Failure: description_en too long")
    assert v == "reupload", "英文大小写不应影响判定"


@selftest
def t_skill_name_emits_grep():
    """给了技能名，必须给出 R8 的 grep 命令 —— 否则使用者会漏掉内嵌方。"""
    r, code = advise("bump", ["测试"], "joy2know-musician")
    out = r.render()
    assert "grep -rl" in out and "joy2know-musician" in out, "必须给出内嵌联动的 grep 命令"


@selftest
def t_exit_codes():
    """退出码语义：0 自行处置 / 1 必须抬 / 2 判不出。"""
    r1, c1 = advise("reupload", [], None)
    r2, c2 = advise("bump", [], None)
    r3, c3 = advise(None, [], None)
    assert (c1, c2, c3) == (0, 1, 2), "退出码语义错：%r" % ((c1, c2, c3),)


# --- ★ 篡改判据表本身的翻转验证

@selftest
def t_mutate_occupied_list_flip():
    global VERSION_OCCUPIED_HINTS
    saved = VERSION_OCCUPIED_HINTS
    try:
        VERSION_OCCUPIED_HINTS = []
        v, _ = classify("解析失败：包内版本号「1.6.0」必须大于当前最新版本「1.6.0」")
        # 关掉最高优先级判据后，这句会掉到「解析失败」分支
        assert v == "reupload", "关掉版本占用判据后应回落到解析失败分支"
    finally:
        VERSION_OCCUPIED_HINTS = saved


@selftest
def t_mutate_parse_list_flip():
    global PARSE_FAILURE_HINTS
    saved = PARSE_FAILURE_HINTS
    try:
        PARSE_FAILURE_HINTS = []
        v, _ = classify("解析失败：描述字段超限")
        assert v is None, "关掉解析失败判据后应判不出"
    finally:
        PARSE_FAILURE_HINTS = saved


@selftest
def t_mutate_rejected_list_flip():
    global SUBMITTED_BUT_REJECTED_HINTS
    saved = SUBMITTED_BUT_REJECTED_HINTS
    try:
        SUBMITTED_BUT_REJECTED_HINTS = []
        v, _ = classify("所选类目与应用类目不符")
        assert v is None, "关掉审核驳回判据后应判不出"
    finally:
        SUBMITTED_BUT_REJECTED_HINTS = saved


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
    print("反向自检：%d/%d 全部通过（含 3 项篡改判据的翻转验证）" % (passed, total))
    print("结论：✅ 已通过")
    print("=" * 68)
    return 0


def main():
    ap = argparse.ArgumentParser(description="上传驳回处置判据器")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--text", help="驳回原文或平台状态")
    g.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return run_selftest()

    text = args.text.strip()
    if not text:
        print("用法错：--text 不能为空（空输入判不出，返回 2）", file=sys.stderr)
        return 2
    verdict, reasons = classify(text)
    rep, code = advise(verdict, reasons, None)
    sys.stdout.write(rep.render() + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
