#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gatecheck.py —— 发布前检测报告的**门禁校验器**。

它不测你的包，它测**你的检测报告**。

四道门（功能测试 / 完整性对照 / 合理性 / 测试真实性）靠自觉会放水，
所以把「放水的信号灯」做成可执行判据：

  - 「未覆盖项」一栏是空的        → 没认真写
  - 头部四行缺一行或格式不对       → 构建门禁判不出
  - 检测状态写了四选一以外的值      → 等同于「未检测」
  - 证据只有命令没有输出要点
  - 结论写了「应该没问题」这类模糊话
  - 自称「✅ 已通过」却没有反向验证记录

用法：
    python3 gatecheck.py --report packages/<包名>/<包名>.md
    python3 gatecheck.py --dir packages/<包名>
    python3 gatecheck.py --selftest

退出码：0 全过 / 1 有硬缺陷 / 2 用法错

设计原则（与 fieldcheck.py 同源）：
  1. 每条判据在 --selftest 里都有反向对照。没有反向对照的判据，
     不能证明它有判别力 —— 只能证明它在数字符。
  2. 「什么都没查出来」报错并返回非 0，绝不给绿。
"""

import argparse
import os
import re
import sys

# ---------------------------------------------------------------- 判据表

#: 报告头部必须有的四行（构建脚本靠它判门禁，格式不能改）
REQUIRED_HEADER_ROWS = ["对应版本", "检测状态", "最后检测", "检测方式"]

#: 检测状态只允许四选一。写「基本通过」「大概没问题」等同「未检测」。
VALID_STATUS = {"✅ 已通过", "⚠️ 有条件通过", "⛔ 未检测", "❌ 未通过"}

#: 状态 → 能否打包（构建按此判）
STATUS_BLOCKS_BUILD = {"⛔ 未检测", "❌ 未通过"}

#: 放水话术。出现即红灯 —— 「大概没问题」不是结论。
VAGUE_WORDS = [
    "应该没问题", "大概没问题", "基本通过", "问题不大", "应该是对的",
    "应该可以", "大概可用", "看着没问题", "估计没问题",
]

#: 证据必须有输出要点，光有命令不算数
#: 输出实据：代码块里出现结果行、退出码、计数，或正文出现「返回 N」「命中 N」这类实数断言。
#: ⚠️ 不能只匹配「输出」「要点」这类**元叙述词** —— 「只贴命令不贴输出要点」这句话本身
#: 就含「输出要点」，会把没贴证据的报告判成有证据。
EVIDENCE_HINT = re.compile(
    r"(退出码|exit=\s*\d|\d+\s*项?(?:未通过|通过|失败|命中|告警)|返回\s*\d|命中\s*\d|"
    r"共执行\s*\d|\d+/\d+)"
)

#: 表格式证据：第二节常把「命令 / 样本 / 结果 / 日期」排成表，**不贴代码块**。
#: 这同样是结构化证据（实测有已过审报告只给表格就被判红）。命中表头即可认。
EVIDENCE_TABLE_HINT = re.compile(r"\|[^\n]*?(命令|验证方式)[^\n]*\|[^\n]*?(样本)[^\n]*\|[^\n]*(结果)")

#: 反向验证的关键词 —— 没有它就声称「全过」是放水
REVERSE_HINT = re.compile(r"(反向验证|反向对照|篡改|故意造|坏样本|错样本|--selftest|判别力)")

#: 反向验证只在**正文**里找（跳过头部）—— 头部「检测方式」字段天然含这些词，
#: 不排除的话每份报告都会自动通过这条判据，判据形同虚设。
_HEADER_LINE = re.compile(r"(?m)^\s*[-*>]\s*\*\*(?:对应版本|检测状态|最后检测|检测方式)\*\*.*$")

#: 「未覆盖项」小节的标题写法（容错：全/半角括号、带序号等）
#: ⚠️ 必须吃掉**整行**。早期写 [^\n]*? 非贪婪，match.end() 落在标题行中间，
#: 剩下的「/ 已知缺陷 / 待办」被当成正文 → 空第六节判不出来（已踩）。
UNCOVERED_HEAD = re.compile(r"(?m)^#{2,4}[^\n]*(?:未覆盖项|已知缺陷|待办)[^\n]*$")

#: 正文七节必须有的标题 —— 只匹配**关键词**，不匹配全句。
#: ⚠️ 早期版本要求精确匹配「三、门 2 完整性对照」，而全仓真实写法是
#: 「三、门 2 · 完整性对照（文档承诺 → 实现）」—— 29 份已过审报告**全被误判为缺小节**。
#: 教训：判据匹配的是**语义位置**，不是排版变体。收紧判据前先拿真实样本跑一遍基线。
#: (匹配正则, 节名, 真实标题写法) —— 正则只管匹配，标题只管造样本，
#: **两者必须分开** —— 混成一份会出现「拿正则当标题写进样本」的假测试。
REQUIRED_SECTIONS = [
    (r"一[、.．]\s*包内文件", "包内文件", "一、包内文件（从磁盘枚举，不手写）"),
    (r"二[、.．]\s*能力清单", "能力清单", "二、能力清单与验证结果"),
    (r"三[、.．].{0,12}完整性对照", "完整性对照", "三、门 2 · 完整性对照（文档承诺 → 实现）"),
    (r"四[、.．].{0,12}合理性", "合理性", "四、门 3 · 合理性结论"),
    (r"五[、.．].{0,12}测试真实性", "测试真实性", "五、门 4 · 测试真实性自评（防放水）"),
    (r"六[、.．]\s*未覆盖项", "未覆盖项", "六、未覆盖项 / 已知缺陷 / 待办"),
    (r"七[、.．]\s*检测履历", "检测履历", "七、检测履历"),
]


#: 节号 → 真实标题（供样本构造与 detail 字典查表用）
_S_TITLE = {i + 1: t for i, (_p, _n, t) in enumerate(REQUIRED_SECTIONS)}


class Report:
    def __init__(self):
        self.bad = []
        self.warn = []
        self.checked = 0

    def bad_add(self, where, msg):
        self.bad.append((where, msg))

    def warn_add(self, where, msg):
        self.warn.append((where, msg))

    def ok(self):
        self.checked += 1

    def render(self, title):
        out = ["", "=" * 68, title, "=" * 68]
        if self.bad:
            out.append("")
            out.append("硬缺陷 %d 项：" % len(self.bad))
            for w, m in self.bad:
                out.append("  [FAIL] %s：%s" % (w, m))
        if self.warn:
            out.append("")
            out.append("告警 %d 项：" % len(self.warn))
            for w, m in self.warn:
                out.append("  [WARN] %s：%s" % (w, m))
        out.append("")
        if self.bad:
            out.append("结论：❌ 未通过（%d 项未通过）" % len(self.bad))
        elif self.warn:
            out.append("结论：⚠️ 有条件通过（0 项未通过，%d 项告警）" % len(self.warn))
        else:
            out.append("结论：✅ 已通过")
        out.append("共执行 %d 条判据。" % self.checked)
        out.append("")
        return "\n".join(out)


def _bad_texts(rep):
    return [m for _, m in rep.bad]


# ---------------------------------------------------------------- 主判据

def check_report(rep, text, label):
    # 判据 1：头部四行齐全且格式正确（列表格式 `- **X**：`，不是引用块 `>`）
    # ⚠️ 扫**全文**而不是前 N 字符 —— 真实报告的头部四行可能被一段说明隔开
    # （实测有包四行分散在第 32~43 行），只看开头会造出假红灯。
    head = text
    for row in REQUIRED_HEADER_ROWS:
        rep.ok()
        # 构建脚本靠 `- **对应版本**：` 这种列表格式识别；写成 `> **对应版本**：` 判不出
        if re.search(r"^\s*>\s*\*\*%s\*\*" % re.escape(row), head, re.M):
            rep.bad_add(label, "头部「%s」写成了引用块 `>` —— 必须用列表格式 `- **%s**：`" % (row, row))
        elif not re.search(r"^\s*[-*]\s*\*\*%s\*\*\s*[:：]" % re.escape(row), head, re.M):
            rep.bad_add(label, "头部缺「%s」行，或格式不是 `- **%s**：`" % (row, row))

    # 判据 2：检测状态必须四选一
    rep.ok()
    m = re.search(r"^\s*[-*]\s*\*\*检测状态\*\*\s*[:：]\s*(.+?)\s*$", head, re.M)
    status = None
    if m:
        status = m.group(1).strip()
        # 允许后缀说明，但主状态词必须在集合里
        if not any(v in status for v in VALID_STATUS):
            rep.bad_add(label, "检测状态 %r 不在四选一内（%s）—— 写「基本通过」等同「未检测」"
                         % (status, " / ".join(sorted(VALID_STATUS))))
        elif any(v in status for v in STATUS_BLOCKS_BUILD):
            rep.ok()
            rep.warn_add(label, "检测状态是「%s」—— 构建门禁会告警，--strict 直接失败" % status)

    # 判据 3：七节齐全
    for pat, name, _title in REQUIRED_SECTIONS:
        rep.ok()
        if not re.search(r"^#{2,4}\s*%s" % pat, text, re.M):
            rep.bad_add(label, "缺小节「第 %s 节」（%s）" % (name, name))

    # 判据 4 ★ 放水信号灯：未覆盖项不许空
    rep.ok()
    m = UNCOVERED_HEAD.search(text)
    if not m:
        rep.bad_add(label, "找不到「未覆盖项 / 已知缺陷 / 待办」小节 —— "
                           "没有任何一次检测能覆盖 100%，缺这一节等于没写")
    else:
        tail = text[m.end():]
        # 到下一个二级标题为止
        nxt = re.search(r"^##\s", tail, re.M)
        sec = tail[:nxt.start()] if nxt else tail
        body = re.sub(r"`[^`]*`|\*\*[^*]*\*\*", "", sec).strip()
        body = re.sub(r"^[\s\-*>|]+", "", body, flags=re.M).strip()
        # 允许「无」「暂无」这类明确声明，但必须显式；纯空白 = 放水
        if not body:
            rep.bad_add(label, "「未覆盖项」一栏是空的 —— 空 = 没认真写，不是「都测过了」")
        elif re.match(r"^(无|暂无|没有|待补)$", body.splitlines()[0].strip()):
            rep.ok()
            rep.warn_add(label, "「未覆盖项」写的是「%s」—— 确认真的没有未覆盖项，"
                                "任何一次检测都该有边界没跑到的地方" % body.splitlines()[0].strip())

    # 判据 5 ★ 放水信号灯：模糊话术
    # ⚠️ 必须排除**元叙述行** —— 报告里常写「结论里没有『应该没问题』」
    # 「无『应该没问题』式结论」来声明自己没放水，这些行含关键词但恰恰是合规的（已踩）。
    # 判法：该行含否定/引用标记（没有 / 无 / 不 / 未 / 「」/『』/ 禁止 / 不许）即跳过。
    rep.ok()
    meta = re.compile("(没有|无|不|未|禁|非|引用|「|『|`)")
    hit = []
    for line in text.splitlines():
        if meta.search(line):
            continue
        for w in VAGUE_WORDS:
            if w in line:
                hit.append(w)
    if hit:
        rep.bad_add(label, "出现放水话术：%s —— 结论要么给判据，要么写「未覆盖」"
                     % "、".join(sorted(set(hit))))

    # 判据 6：声称全过就必须有反向验证记录
    rep.ok()
    if status and "✅" in status:
        body_only = _HEADER_LINE.sub("", text)
        if not REVERSE_HINT.search(body_only):
            rep.bad_add(label, "状态写「✅ 已通过」但全文没有反向验证记录 —— "
                               "没做反向验证就没法证明门禁不是橡皮章")

    # 判据 7：证据要有输出要点，不能只有命令
    # ⚠️ 必须**按小节**判，不能全文搜 —— 别的章节（第五节的反向验证）里出现
    # 「exit=1」会把「第二节只贴了命令」这个事实盖掉（已踩）。
    rep.ok()
    has_code = ("```" in text) or re.search(r"^\s*\$\s+\S", text, re.M)
    if has_code:
        m2 = re.search(r"^#{2,4}\s*二、能力清单与验证结果", text, re.M)
        if not m2:
            rep.warn_add(label, "找不到「二、能力清单与验证结果」小节 —— 无法核对证据是否带输出")
        else:
            tail = text[m2.end():]
            nxt2 = re.search(r"^##\s", tail, re.M)
            sec2 = tail[:nxt2.start()] if nxt2 else tail
            has_evidence = (EVIDENCE_HINT.search(sec2)
                            or EVIDENCE_TABLE_HINT.search(sec2))
            if ("```" in sec2 or re.search(r"^\s*\$\s+\S", sec2, re.M)
                or EVIDENCE_TABLE_HINT.search(sec2)) and not has_evidence:
                rep.bad_add(label, "第二节有命令样本但没有任何输出实据 —— "
                                   "只贴命令不贴输出，等于没有证据")

    # 判据 8：四道门都要在正文里被点名
    for gate in ("门 1", "门 2", "门 3", "门 4"):
        rep.ok()
        if gate not in text:
            rep.warn_add(label, "正文没提到「%s」—— 四道门都要有结论，不能跳门" % gate)

    # 判据 9：履历不能只有一行且是今天 —— 说明报告在复用中没更新
    rep.ok()
    m = re.search(r"^#{2,4}\s*[^\n]*检测履历", text, re.M)
    if m:
        tail = text[m.end():]
        nxt = re.search(r"^##\s", tail, re.M)
        sec = tail[:nxt.start()] if nxt else tail
        rows = [l for l in sec.splitlines() if l.strip().startswith("|") and "---" not in l]
        if len(rows) < 2:
            rep.warn_add(label, "检测履历只有 %d 行 —— 每次检测都该追加一行，否则报告在复用中会悄悄过期" % len(rows))

    return rep


# ---------------------------------------------------------------- 反向自检

SELFTESTS = []


def selftest(fn):
    SELFTESTS.append(fn)
    return fn


def _mk_report(status="✅ 已通过", uncovered="- 字段口径的时效性未验证",
               extra="", sections=True, header_style="list", reverse=True, evidence=True):
    head = ""
    for row in REQUIRED_HEADER_ROWS:
        val = status if row == "检测状态" else ("1.0.0" if row == "对应版本"
                                                 else "2026-10-12" if row == "最后检测"
                                                 else "功能测试 + 反向验证")
        if header_style == "quote":
            head += "> **%s**：%s\n" % (row, val)
        else:
            head += "- **%s**：%s\n" % (row, val)
    # 合格样本必须名副其实：第五节要有反向验证记录，第二节要有输出实据。
    # 否则「合格样本」是靠元叙述词混过去的假样本 —— 这正是本技能要抓的东西。
    detail = {
        _S_TITLE[1]: (
            "\n| 能力 | 命令 | 结果 |\n|---|---|---|\n"
            "| 自检 | `python3 scripts/x.py --selftest` | 14/15 通过 |\n"
        ) if evidence else "内容\n",
        _S_TITLE[4]: (
            "\n做了反向验证：故意造坏样本，确认门禁变红（exit=1）。\n"
        ) if reverse else "内容\n",
    }
    secs = ""
    if sections:
        secs = "\n".join("## %s\n\n%s\n" % (t, detail.get(t, "内容\n"))
                         for _p, _n, t in REQUIRED_SECTIONS)
    body = "\n%s\n%s\n%s\n" % (head, secs, extra)
    h6 = "## " + _S_TITLE[6]
    return body.replace(h6 + "\n\n内容\n", h6 + "\n\n%s\n" % uncovered) \
               .replace(h6 + "\n\n内容", h6 + "\n\n%s" % uncovered)


@selftest
def t_good_report_passes():
    rep = check_report(Report(), _mk_report(), "t")
    assert not rep.bad, "合格报告被误报：%r" % _bad_texts(rep)


@selftest
def t_empty_uncovered_is_red():
    """★ 最典型的放水：「未覆盖项」空着。"""
    rep = check_report(Report(), _mk_report(uncovered=""), "t")
    assert any("未覆盖项" in m and "空" in m for m in _bad_texts(rep)), \
        "空的未覆盖项未被抓到"


@selftest
def t_vague_wording_is_red():
    rep = check_report(Report(), _mk_report(extra="结论：应该没问题，大概能过。"), "t")
    assert any("放水话术" in m for m in _bad_texts(rep)), "模糊结论未被抓到"


@selftest
def t_pass_without_reverse_is_red():
    """★ 声称全过但没做反向验证 —— 负样本必须真的「没有」那段内容。"""
    rep = check_report(Report(), _mk_report(status="✅ 已通过", reverse=False,
                                            evidence=False, extra="跑完了，没报错。"), "t")
    assert any("反向验证" in m for m in _bad_texts(rep)), \
        "无反向验证却判全过，未被抓到"


@selftest
def t_pass_with_reverse_ok():
    rep = check_report(Report(), _mk_report(
        extra="门禁自检跑过，篡改阈值后判据跟着翻转。"), "t")
    assert not any("反向验证" in m for m in _bad_texts(rep)), "有反向验证记录却被误报"


@selftest
def t_quote_style_header_is_red():
    """★ 头部写成引用块 → 构建脚本判不出，会静默失效。"""
    rep = check_report(Report(), _mk_report(header_style="quote"), "t")
    assert any("引用块" in m for m in _bad_texts(rep)), "引用块头部未被抓到"


@selftest
def t_missing_header_row_is_red():
    body = _mk_report().replace("- **检测方式**：功能测试 + 反向验证\n", "")
    rep = check_report(Report(), body, "t")
    assert any("检测方式" in m for m in _bad_texts(rep)), "缺头部行未被抓到"


@selftest
def t_invalid_status_is_red():
    rep = check_report(Report(), _mk_report(status="基本通过"), "t")
    assert any("四选一" in m for m in _bad_texts(rep)), "非法状态未被抓到"


@selftest
def t_all_four_statuses_accepted():
    for st in sorted(VALID_STATUS):
        rep = check_report(Report(), _mk_report(status=st), "t")
        assert not any("四选一" in m for m in _bad_texts(rep)), "合法状态 %s 被误报" % st


@selftest
def t_missing_section_is_red():
    h5 = "## " + _S_TITLE[5]
    body = _mk_report().replace(h5, "## 五、别的小节")
    rep = check_report(Report(), body, "t")
    assert any("测试真实性" in m for m in _bad_texts(rep)), "缺小节未被抓到"


@selftest
def t_command_without_output_is_red():
    """★ 只贴命令不贴输出。"""
    # ⚠️ 别用 replace 去改第二节的正文 —— detail 字典一改这里就匹配不上，
    # 负样本会「造不出缺失」，测出来的是假测试（已踩）。
    # 做法：正向插入一段只有命令、没有输出实据的内容。
    body = _mk_report(evidence=False).replace(
        "## 二、能力清单与验证结果\n\n",
        "## 二、能力清单与验证结果\n\n```\n$ python3 x.py --dir 包\n```\n", 1)
    rep = check_report(Report(), body, "t")
    assert any("输出实据" in m for m in _bad_texts(rep)), "只贴命令未被抓到"


@selftest
def t_meta_mention_of_vague_word_is_not_red():
    """★ 报告里声明「结论里没有『应该没问题』」是**合规**的，不该被放水话术判据打中。

    这类误伤过一轮：两份已过审报告因为引用了禁令本身被判红。
    """
    body = _mk_report(extra="结论里没有「应该没问题」式表述。")
    rep = check_report(Report(), body, "t")
    assert not any("放水话术" in m for m in _bad_texts(rep)), \
        "引用禁令本身被判成放水 —— 判据没排除元叙述"


@selftest
def t_table_evidence_is_enough():
    """★ 第二节把「命令/样本/结果/日期」排成表、不贴代码块，也是结构化证据。

    实测有一份已过审报告只因用表格就被判红 —— 判据不能只认代码块形态。
    """
    body = _mk_report(evidence=False).replace(
        "## " + _S_TITLE[2] + "\n\n内容\n",
        "## " + _S_TITLE[2] + "\n\n"
        "| 能力 | 验证方式（命令） | 样本 | 结果 |\n|---|---|---|---|\n"
        "| 字段齐全 | `fieldcheck.py --dir 包` | 实包 | ✅ 通过 |\n", 1)
    rep = check_report(Report(), body, "t")
    assert not any("输出实据" in m for m in _bad_texts(rep)), "表格式证据被判成没贴证据"


@selftest
def t_header_scanned_beyond_lead():
    """★ 头部四行可能被一段说明隔开到第 30+ 行 —— 只扫开头会造出假红灯。"""
    body = _mk_report().replace(
        "- **检测状态**：", "\n\n".join(["（说明段落 %d）" % i for i in range(40)]) + "\n\n- **检测状态**：", 1)
    rep = check_report(Report(), body, "t")
    assert not any("头部" in m for m in _bad_texts(rep)), "头部隔开就被判缺失"


@selftest
def t_unknown_package_not_green():
    rep = check_report(Report(), "", "t")
    assert rep.bad, "空报告给了绿灯"


# --- ★ 篡改判据本身的翻转验证

@selftest
def t_mutate_status_set_flip():
    global VALID_STATUS
    saved = VALID_STATUS
    try:
        VALID_STATUS = {"✅ 已通过"}
        rep = check_report(Report(), _mk_report(status="⚠️ 有条件通过"), "t")
        assert any("四选一" in m for m in _bad_texts(rep)), \
            "收窄状态集合后判据没跟着变 —— 它本来就没在查"
    finally:
        VALID_STATUS = saved


@selftest
def t_mutate_uncovered_check_flip():
    global UNCOVERED_HEAD
    saved = UNCOVERED_HEAD
    try:
        UNCOVERED_HEAD = re.compile(r"^#{2,4}\\s*[^\\n]*?(永远不会匹配到的标题)")
        rep = check_report(Report(), _mk_report(), "t")
        assert any("未覆盖项" in m for m in _bad_texts(rep)), \
            "关掉未覆盖项判据后，合格报告应该变红 —— 说明它本来就没在查"
    finally:
        UNCOVERED_HEAD = saved


@selftest
def t_mutate_vague_list_flip():
    global VAGUE_WORDS
    saved = VAGUE_WORDS
    try:
        VAGUE_WORDS = ["绝不会出现的短语"]
        rep = check_report(Report(), _mk_report(extra="结论：应该没问题。"), "t")
        assert not any("放水话术" in m for m in _bad_texts(rep)), \
            "清空放水话术后仍然报错 —— 判据与文案不是同一件事"
    finally:
        VAGUE_WORDS = saved


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
        print("结论：❌ 未通过 —— 校验器本身可能没有判别力")
        print("=" * 68)
        return 1
    print("反向自检：%d/%d 全部通过（含 3 项篡改判据的翻转验证）" % (passed, total))
    print("结论：✅ 已通过")
    print("=" * 68)
    return 0


def run_report(path):
    if not os.path.isfile(path):
        print("用法错：%s 不是文件" % path, file=sys.stderr)
        return 2
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if not text.strip():
        print("用法错：报告是空的 —— 空白报告给了绿灯，比报错危险得多", file=sys.stderr)
        return 2
    rep = check_report(Report(), text, os.path.basename(path))
    sys.stdout.write(rep.render("gatecheck · %s" % path))
    return 1 if rep.bad else 0


def run_dir(pkg_dir):
    if not os.path.isdir(pkg_dir):
        print("用法错：%s 不是目录" % pkg_dir, file=sys.stderr)
        return 2
    name = os.path.basename(pkg_dir.rstrip("/"))
    rp = os.path.join(pkg_dir, name + ".md")
    if not os.path.isfile(rp):
        print("用法错：找不到检测报告 %s（应与包目录同名）" % rp, file=sys.stderr)
        return 2
    return run_report(rp)


def main():
    ap = argparse.ArgumentParser(description="检测报告门禁校验器")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--report", help="检测报告 .md 路径")
    g.add_argument("--dir", help="包目录（自动找 <包名>/<包名>.md）")
    g.add_argument("--selftest", action="store_true", help="反向自检")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    if args.report:
        return run_report(args.report)
    return run_dir(args.dir)


if __name__ == "__main__":
    sys.exit(main())
