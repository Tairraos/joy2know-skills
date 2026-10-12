#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fieldcheck.py —— WorkBuddy 资产包字段与结构离线校验器。

不联网、不带凭证、零第三方依赖。同时支持技能包（SKILL.md）与专家/专家团包
（.codebuddy-plugin/plugin.json），按目录或 zip 自动识别。

用法：
    python3 fieldcheck.py --dir  path/to/包目录
    python3 fieldcheck.py --zip  path/to/产物.zip
    python3 fieldcheck.py --selftest

退出码：
    0  全过（或只有告警）
    1  有硬缺陷
    2  用法错 / 认不出包类型

设计原则（改这个脚本前先读完）：
  1. 「什么都没查出来」必须报错并返回非 0 —— 认不出包比报错危险得多。
  2. 每条判据都在 --selftest 里有反向对照：篡改判据本身，目标文案必须跟着翻转。
     没有反向对照的判据，等于不知道它有没有判别力。
  3. 不在测试里重算被测逻辑 —— 必须走真实解析路径，否则被测对象整个坏掉也照样报绿。
"""

import argparse
import io
import json
import os
import re
import sys
import zipfile

# ---------------------------------------------------------------- 判据表

#: 技能 SKILL.md 的 9 个必填 frontmatter（★ = 官方字段表未列但示例里有，缺了报解析失败）
REQUIRED_FRONTMATTER = [
    "name", "display_name", "display_name_en",
    "description", "description_zh", "description_en",
    "category", "version", "author",
]

#: 这三个字段官方字段表里没列，但示例代码块里有 —— 缺失直接解析失败
UNDOCUMENTED_BUT_REQUIRED = {"display_name", "display_name_en", "category"}

#: description_en 的平台硬上限（字符）。实测超限 → 解析失败。
DESCRIPTION_EN_LIMIT = 1000

#: categoryId 官方 15 类全清单。专家与专家团共用同一份。
VALID_CATEGORY_IDS = {
    "01-ProductDesign", "02-Engineering", "03-GameSpatial", "04-DataAI",
    "05-MarketingGrowth", "06-ContentCreative", "07-SalesCommerce", "08-FinanceInvestment",
    "09-OperationsHR", "10-ProjectQuality", "11-SecurityCompliance", "12-IndustryConsultant",
    "13-TencentZone", "14-WorldWise", "15-Education",
}

#: 包根一级子目录白名单 —— 平台只认这三个
ALLOWED_SUBDIRS = {"references", "scripts", "templates"}

#: 体积上限（字节）
SIZE_LIMIT_SKILL = 3 * 1024 * 1024
SIZE_LIMIT_EXPERT = 20 * 1024 * 1024

#: displayDescription.zh 的汉字数区间（官方口径）
DD_ZH_MIN, DD_ZH_MAX = 40, 50


class Report:
    """收集结果。bad 是硬缺陷（退出码 1），warn 是不阻断的告警。"""

    def __init__(self):
        self.bad = []
        self.warn = []
        self.checked = 0

    def bad_add(self, where, msg):
        self.bad.append((where, msg))

    def warn_add(self, where, msg):
        self.warn.append((where, msg))

    def ok(self, n=1):
        self.checked += n

    def render(self, title):
        lines = ["", "=" * 68, title, "=" * 68]
        if self.bad:
            lines.append("")
            lines.append("硬缺陷 %d 项：" % len(self.bad))
            for where, msg in self.bad:
                lines.append("  [FAIL] %s：%s" % (where, msg))
        if self.warn:
            lines.append("")
            lines.append("告警 %d 项：" % len(self.warn))
            for where, msg in self.warn:
                lines.append("  [WARN] %s：%s" % (where, msg))
        lines.append("")
        if self.bad:
            lines.append("结论：❌ 未通过（%d 项未通过）" % len(self.bad))
        elif self.warn:
            lines.append("结论：⚠️ 有条件通过（0 项未通过，%d 项告警）" % len(self.warn))
        else:
            lines.append("结论：✅ 已通过")
        lines.append("共执行 %d 条判据。" % self.checked)
        lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------- 读取层

def read_pkg_dir(pkg_dir):
    """把包目录读成 {相对路径: bytes}。"""
    files = {}
    for base, dirs, names in os.walk(pkg_dir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for n in names:
            if n == ".DS_Store":
                continue
            full = os.path.join(base, n)
            rel = os.path.relpath(full, pkg_dir)
            try:
                with open(full, "rb") as f:
                    files[rel] = f.read()
            except OSError:
                pass
    return files


def read_pkg_zip(zip_path):
    """把 zip 读成 {相对路径: bytes}。

    返回 (files, top_dirs, root_files)：
      top_dirs   —— 第一层的**目录**条目名（zip 里会显式存目录项）
      root_files —— 第一层直接躺着的**文件**名
    ⚠️ 两者必须分开：zip 会把 `pkg/references` 这种目录条目也存进去，
      早前没分开时，一个完全正确的 zip 会被判成「第一层有 3 个并列条目」（已踩）。
    """
    files = {}
    top_dirs, root_files = [], []
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            name = info.filename.replace("\\", "/")
            if name.startswith("__MACOSX/") or name.endswith(".DS_Store"):
                continue
            if info.is_dir():
                d = name.rstrip("/")
                if d and "/" not in d and d not in top_dirs:
                    top_dirs.append(d)
                continue
            if name.endswith("/"):
                continue
            files[name] = z.read(name)
            head = name.split("/", 1)[0]
            if "/" in name:
                if head not in top_dirs:
                    top_dirs.append(head)
            elif name not in root_files:
                root_files.append(name)
    return files, top_dirs, root_files


# ---------------------------------------------------------------- 解析层

def parse_frontmatter(text):
    """解析 YAML frontmatter。

    只用正则逐行取标量 —— 这是有意的选择：它跟真 YAML 解析器行为一致的地方够用，
    在「没装 PyYAML 时静默降级成正则」这个坑上不栽跟头（本脚本零依赖，直接用正则）。
    返回 (dict, 顺序列表, 解析成功与否)。
    """
    if not text.startswith("---"):
        return {}, [], False
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, [], False
    data = {}
    order = []
    cur_key = None
    cur_val = []
    for raw in lines[1:end]:
        # 顶层键：行首非空白的 key: value
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", raw)
        if m and not raw.startswith((" ", "\t")):
            if cur_key:
                data[cur_key] = "\n".join(cur_val).strip()
            cur_key = m.group(1)
            order.append(cur_key)
            cur_val = [m.group(2)]
        elif cur_key is not None:
            cur_val.append(raw.strip())
    if cur_key:
        data[cur_key] = "\n".join(cur_val).strip()
    return data, order, True


def count_han(s):
    """汉字个数（不含标点/空白/拉丁）。"""
    return len(re.findall(r"[\u4e00-\u9fff]", s or ""))


def package_type_of(files):
    """识别包类型。返回 'skill' / 'expert' / None。

    注意：这里刻意**不要求路径层级正确** —— 扁平结构（根级直接是 SKILL.md）
    也是合法输入，只是「结构错了」这一条要由 zip 判据单独报出来。
    否则会出现「认不出包类型」的误导性报错，把真问题掩盖掉。
    """
    for k in files:
        if k.replace("\\", "/").split("/")[-1] == "SKILL.md":
            return "skill"
    for k in files:
        if k.replace("\\", "/").endswith(".codebuddy-plugin/plugin.json"):
            return "expert"
    return None


def detect_root_prefix(files, top_names=None):
    """判断是否存在包目录前缀，返回前缀字符串（空串 = 无前缀）。

    要同时正确处理两种形态：
      A. 源码目录读出来的文件 —— 键就是包内相对路径（`.codebuddy-plugin/plugin.json`、`agents/x.md`）
      B. zip 里剥出来的文件     —— 键带包目录名（`my-pkg/.codebuddy-plugin/plugin.json`）
    ⚠️ 判据必须是「**键的第一段**是不是包内已知目录」，不能用 endswith ——
      形态 B 下 `my-pkg/.codebuddy-plugin/plugin.json` 也 endswith，
      会被误判成无前缀，于是整棵树被当成「白名单外子目录 my-pkg」（已踩）。
    """
    keys = [k.replace("\\", "/") for k in files]
    # 形态 A：出现「裸」的第一段（不是包目录名）
    for p in keys:
        head = p.split("/", 1)[0]
        if head in (".codebuddy-plugin", "agents", "references", "scripts",
                    "templates", "avatars", "assets") or p == "SKILL.md":
            return ""
    # 形态 B：所有键共用同一个顶层目录名
    tops = {p.split("/", 1)[0] for p in keys if "/" in p}
    if len(tops) == 1:
        only = next(iter(tops))
        if all(p == only or p.startswith(only + "/") for p in keys):
            return only + "/"
    return ""


def strip_prefix(files, prefix):
    if not prefix:
        return files
    return {k[len(prefix):]: v for k, v in files.items() if k.startswith(prefix)}


# ---------------------------------------------------------------- 判据

def check_zip_root(rep, top_dirs, source_label, root_files=None):
    """zip 第一层必须是包目录，不能直接是文件、也不能有多个并列目录。"""
    rep.ok()
    root_files = root_files or []
    if root_files:
        rep.bad_add(source_label, "zip 第一层直接是文件（%s）—— 打包时必须先 cd 进包目录，"
                                  "第一层只该有一个包目录" % ", ".join(sorted(root_files)[:4]))
        return
    if len(top_dirs) > 1:
        rep.bad_add(source_label, "zip 第一层有 %d 个并列目录（%s）—— 打包时必须先 cd 进包目录，"
                                  "第一层只该有一个包目录" % (len(top_dirs), ", ".join(sorted(top_dirs)[:4])))


def check_size(rep, files, ptype, source_label):
    rep.ok()
    total = sum(len(v) for v in files.values())
    limit = SIZE_LIMIT_SKILL if ptype == "skill" else SIZE_LIMIT_EXPERT
    label = "3MB（技能）" if ptype == "skill" else "20MB（专家/专家团）"
    if total > limit:
        rep.bad_add(source_label, "体积 %.1f KB 超过上限 %s" % (total / 1024.0, label))
    elif total > limit * 0.8:
        rep.warn_add(source_label, "体积 %.1f KB 已超上限八成（%s）—— 二进制资源不该进包" % (total / 1024.0, label))


def check_allowed_subdirs(rep, files, ptype, source_label):
    """包根一级子目录白名单。

    ⚠️ 技能包与专家包的口径**不同** —— 别把它们合并成一份清单：
      技能包：只认 references/ scripts/ templates/ 三个
      专家包：agents/ avatars/ .codebuddy-plugin/ 是平台要求的，
              且实测**允许 assets/**（有在架包这么用），比技能包宽松
    """
    rep.ok()
    if ptype == "skill":
        allowed = set(ALLOWED_SUBDIRS)
    else:
        allowed = set(ALLOWED_SUBDIRS) | {"agents", "avatars", "assets", ".codebuddy-plugin"}
    bad = set()
    for k in files:
        parts = k.replace("\\", "/").split("/")
        if len(parts) >= 2:
            d = parts[0]
            if d in ("", ".") or d.startswith("."):
                continue  # 根级文件
            if d not in allowed:
                bad.add(d)
    if bad:
        scope = "references/ scripts/ templates/" if ptype == "skill" \
            else "references/ scripts/ templates/ agents/ avatars/ assets/ .codebuddy-plugin/"
        rep.bad_add(source_label, "包根出现了白名单外的一级子目录：%s（本类包只认 %s）"
                     % (", ".join(sorted(bad)), scope))


def check_skill(rep, files, source_label):
    """技能包判据。"""
    skill_key = None
    for k in files:
        if k.replace("\\", "/").endswith("SKILL.md"):
            skill_key = k
            break
    if not skill_key:
        rep.bad_add(source_label, "找不到 SKILL.md（技能包必须根级有）")
        return

    try:
        text = files[skill_key].decode("utf-8")
    except UnicodeDecodeError:
        rep.bad_add(skill_key, "不是 UTF-8 编码")
        return

    fm, order, ok = parse_frontmatter(text)
    rep.ok()
    if not ok:
        rep.bad_add(skill_key, "frontmatter 解析失败：文件必须以 --- 开头且有闭合的 ---")
        return

    # 判据 1：9 个必填，一个都不能少
    for field in REQUIRED_FRONTMATTER:
        rep.ok()
        val = fm.get(field, "")
        if not val.strip():
            tag = "（★ 官方字段表未列，缺失直接解析失败）" if field in UNDOCUMENTED_BUT_REQUIRED else ""
            rep.bad_add(skill_key, "缺必填字段 %s%s" % (field, tag))

    # 判据 2：description_en 长度上限
    den = fm.get("description_en", "")
    if den:
        rep.ok()
        if len(den) > DESCRIPTION_EN_LIMIT:
            rep.bad_add(skill_key, "description_en %d 字符，超过平台上限 %d —— 会被解析失败"
                        % (len(den), DESCRIPTION_EN_LIMIT))
        elif len(den) > DESCRIPTION_EN_LIMIT * 0.9:
            rep.warn_add(skill_key, "description_en %d 字符，接近上限 %d"
                         % (len(den), DESCRIPTION_EN_LIMIT))

    # 判据 3：name 与目录名一致（仅目录模式有意义）
    nm = fm.get("name", "")
    if nm:
        rep.ok()
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", nm):
            rep.bad_add(skill_key, "name %r 不合规 —— 仅小写字母、数字、连字符，且不得有连续或首尾连字符" % nm)

    # 判据 4：description 不该空，且描述要含触发词这一层信息
    d = fm.get("description", "")
    if d:
        rep.ok()
        if len(d) > 900:
            rep.warn_add(skill_key, "description %d 字符，明显超出本系列经验区间（240–390 字）—— "
                                    "超标会稀释触发权重" % len(d))


def check_expert(rep, files, source_label, injected_ok=False):
    """专家 / 专家团包判据。

    injected_ok=True 表示这是**源目录**（构建前）：`skills/` 与 `avatars/`
    由构建阶段注入，源目录里本来就不存在 —— 此时不报「文件找不到」，
    只在报告里点名说这两类引用**要等构建后才有**。
    """
    pkey = None
    for k in files:
        if k.replace("\\", "/").endswith(".codebuddy-plugin/plugin.json"):
            pkey = k
            break
    if not pkey:
        rep.bad_add(source_label, "找不到 .codebuddy-plugin/plugin.json（专家包入口）")
        return

    try:
        cfg = json.loads(files[pkey].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        rep.bad_add(pkey, "不是合法 JSON：%s" % e)
        return
    rep.ok()

    # 判据 1：categoryId 必须在官方 15 类内
    rep.ok()
    cid = cfg.get("categoryId", "")
    if cid not in VALID_CATEGORY_IDS:
        rep.bad_add(pkey, "categoryId %r 不在官方 15 类清单内 —— 平台会直接打回。"
                          "注意不存在「专家团专属分类」" % cid)

    # 判据 2：name / plugin 一致，且与目录名一致
    rep.ok()
    nm, pg = cfg.get("name", ""), cfg.get("plugin", "")
    if nm and pg and nm != pg:
        rep.bad_add(pkey, "plugin %r 与 name %r 不一致" % (pg, nm))

    # 判据 3：defaultInitPrompt 必须逐字等于 quickPrompts[0]
    rep.ok()
    qs = cfg.get("quickPrompts") or []
    dip = cfg.get("defaultInitPrompt") or {}
    if qs and isinstance(dip, dict):
        q0 = qs[0]
        for lang in ("zh", "en"):
            a, b = dip.get(lang, ""), (q0 or {}).get(lang, "")
            if a != b:
                rep.bad_add(pkey, "defaultInitPrompt.%s 与 quickPrompts[0].%s 不逐字一致" % (lang, lang))
                break

    # 判据 4：tags / quickPrompts 各固定 3 个
    for field in ("tags", "quickPrompts"):
        rep.ok()
        v = cfg.get(field) or []
        if len(v) != 3:
            rep.bad_add(pkey, "%s 有 %d 个，平台要求固定 3 个" % (field, len(v)))

    # 判据 5：中英成对
    for field in ("displayName", "profession", "displayDescription"):
        rep.ok()
        v = cfg.get(field) or {}
        if not isinstance(v, dict) or not v.get("zh", "").strip() or not v.get("en", "").strip():
            rep.bad_add(pkey, "%s 必须中英成对（zh 与 en 都非空）" % field)

    # 判据 6：displayDescription.zh 40–50 汉字
    rep.ok()
    ddzh = ((cfg.get("displayDescription") or {}).get("zh") or "")
    if ddzh:
        n = count_han(ddzh)
        if n < DD_ZH_MIN or n > DD_ZH_MAX:
            rep.bad_add(pkey, "displayDescription.zh 有 %d 汉字，官方口径要求 %d–%d"
                        % (n, DD_ZH_MIN, DD_ZH_MAX))

    # 判据 7：description（英文）长度上限 —— 专家包会继承内嵌技能的违规
    rep.ok()
    d = cfg.get("description", "")
    if isinstance(d, str) and len(d) > DESCRIPTION_EN_LIMIT:
        rep.bad_add(pkey, "description %d 字符，超过平台上限 %d" % (len(d), DESCRIPTION_EN_LIMIT))

    # 判据 8：avatar 必须是 avatars/ 下的 PNG 相对路径，且文件存在
    rep.ok()
    av = cfg.get("avatar", "")
    if not av:
        rep.bad_add(pkey, "avatar 字段为空")
    elif not av.startswith("avatars/") or not av.endswith(".png"):
        rep.bad_add(pkey, "avatar %r 必须是 avatars/ 下的 .png 相对路径" % av)
    elif av not in files and not any(k.endswith(av) for k in files):
        # 源目录里头像由构建注入 —— 此时是预期状态，不是缺陷
        if injected_ok:
            rep.warn_add(pkey, "avatar %s 尚未出现在源目录（构建时注入）—— "
                               "请确认它在「资产图标」真源目录下存在且为 512×512 PNG" % av)
        else:
            rep.bad_add(pkey, "avatar 指向的文件 %s 在包里不存在" % av)

    # 判据 9：agents[] / skills[] 引用的文件必须存在
    for group in ("agents", "skills"):
        for ref in cfg.get(group) or []:
            # ⚠️ 必须用 removeprefix("./") 而不是 lstrip("./") ——
            # lstrip 会剥掉任意组合的 '.' 与 '/'，像 ".codebuddy-plugin/x" 会被误伤。
            rp = ref.removeprefix("./").replace("\\", "/")
            # ⚠️ plugin.json 的 agents[] 写的是 './agents/x.md'（带后缀），
            # skills[] 写的是 './skills/x'（不带）—— 不能无条件补 .md，
            # 否则会拼出 'x.md.md' 这种永远匹配不上的路径。
            if not rp.endswith(".md"):
                # skills 引用的是目录，去掉尾斜杠后按目录前缀匹配
                rp_clean = rp.rstrip("/")
                hit = any(k.replace("\\", "/").startswith(rp_clean + "/") or
                          k.replace("\\", "/").find(rp_clean) >= 0 for k in files)
            else:
                hit = any(k.replace("\\", "/").find(rp) >= 0 for k in files)
            rep.ok()
            if not hit:
                # skills/ 在源包里是 skills.json 声明的，文件由构建复制进来
                if injected_ok and group == "skills":
                    rep.warn_add(pkey, "skills 引用的 %s 尚未出现在源目录（构建时从技能真源复制）"
                                 % ref)
                else:
                    rep.bad_add(pkey, "%s 引用的 %s 在包里找不到" % (group, ref))

    # 判据 10：expertType=team 时，团专属结构
    if cfg.get("expertType") == "team":
        rep.ok()
        for f in ("settings.json", "setting.json"):
            if not any(k.endswith(f) for k in files):
                rep.bad_add(pkey, "专家团包缺少 %s（官方模板与平台校验器各用一个，两个都放最稳）" % f)
        members = cfg.get("members") or []
        m_ids = {m.get("id") for m in members}
        for m in members:
            rep.ok()
            if set(m.keys()) - {"id", "name", "profession", "avatar", "role"}:
                rep.bad_add(pkey, "members[] 元素 %r 字段超过五个（id/name/profession/avatar/role）" % m.get("id"))
        # agents 文件名去 .md 须与 members[].id 一一对应
        rep.ok()
        a_names = {os.path.basename(a).rsplit(".md", 1)[0] for a in (cfg.get("agents") or [])}
        if m_ids != a_names:
            rep.bad_add(pkey, "agents[] 与 members[].id 不一一对应（仅在包内 %s vs %s）"
                        % (sorted(a_names), sorted(x for x in m_ids if x)))


# ---------------------------------------------------------------- 主流程

def check_package(files, source_label, top_dirs=None, root_files=None, dir_name=None, injected_ok=False):
    rep = Report()
    ptype = package_type_of(files)
    if ptype is None:
        # 判据：认不出包类型必须报错，绝不给绿
        rep.bad_add(source_label, "认不出包类型 —— 既没有根级 SKILL.md，也没有 .codebuddy-plugin/plugin.json。"
                                   "请确认这个路径下确实是资产包")
        return rep, None

    if top_dirs is not None or root_files is not None:
        check_zip_root(rep, top_dirs or [], source_label, root_files or [])

    prefix = detect_root_prefix(files)
    inner = strip_prefix(files, prefix)

    check_allowed_subdirs(rep, inner, ptype, source_label)
    check_size(rep, inner, ptype, source_label)
    if ptype == "skill":
        check_skill(rep, inner, source_label)
    else:
        check_expert(rep, inner, source_label, injected_ok=injected_ok)
    return rep, ptype


def run_dir(path):
    if not os.path.isdir(path):
        print("用法错：%s 不是目录" % path, file=sys.stderr)
        return 2
    files = read_pkg_dir(path)
    if not files:
        print("用法错：目录 %s 下没有可读文件" % path, file=sys.stderr)
        return 2
    rep, ptype = check_package(files, os.path.basename(path.rstrip("/")),
                           dir_name=os.path.basename(path.rstrip("/")), injected_ok=True)
    # 目录模式：name 必须与目录名一致
    if ptype and os.path.isfile(os.path.join(path, "SKILL.md")):
        fm, _, _ = parse_frontmatter(open(os.path.join(path, "SKILL.md"), encoding="utf-8").read())
        d = os.path.basename(path.rstrip("/"))
        if fm.get("name") and fm["name"] != d:
            rep.ok()
            rep.bad_add("SKILL.md", "name %r 与目录名 %r 不一致" % (fm["name"], d))
    sys.stdout.write(rep.render("fieldcheck · 目录模式 · %s（识别为%s）"
                                % (path, "技能" if ptype == "skill" else "专家/专家团")))
    return 1 if rep.bad else 0


def run_zip(path):
    if not os.path.isfile(path):
        print("用法错：%s 不是文件" % path, file=sys.stderr)
        return 2
    files, top_dirs, root_files = read_pkg_zip(path)
    if not files:
        print("用法错：zip %s 里没有可读文件" % path, file=sys.stderr)
        return 2
    rep, ptype = check_package(files, os.path.basename(path), top_dirs, root_files)
    sys.stdout.write(rep.render("fieldcheck · zip 模式 · %s（识别为%s）"
                                % (path, "技能" if ptype == "skill" else "专家/专家团")))
    return 1 if rep.bad else 0


# ---------------------------------------------------------------- 反向自检

def _mk_skill(name="demo-skill", fm_over=None, body="body\n"):
    fm = {
        "name": name, "display_name": "演示技能", "display_name_en": "Demo Skill",
        "description": "触发词：演示。", "description_zh": "演示。", "description_en": "Demo.",
        "category": "capability", "version": "1.0.0", "author": "署名",
    }
    if fm_over:
        for k, v in fm_over.items():
            if v is None:
                fm.pop(k, None)
            else:
                fm[k] = v
    lines = ["---"]
    for k in REQUIRED_FRONTMATTER:
        if k in fm:
            lines.append("%s: %s" % (k, fm[k]))
    lines += ["---", "", body]
    return {"demo-skill/SKILL.md": "\n".join(lines).encode("utf-8")}


def _mk_expert(name="demo-expert", cfg_over=None, avatar=True):
    cfg = {
        "name": name, "version": "1.0.0", "description": "Demo expert.",
        "author": {"name": "署名"},
        "agents": ["./agents/demo-expert.md"],
        "skills": [],
        "expertType": "agent", "agentName": "demo-expert",
        "displayName": {"en": "joy2know", "zh": "署名"},
        "profession": {"en": "joy2know Demo", "zh": "晓得·演示"},
        "displayDescription": {"en": "An English one.", "zh": "这" * 44 + "。"},
        "avatar": "avatars/expert.png",
        "categoryId": "02-Engineering",
        "defaultInitPrompt": {"zh": "开始", "en": "Start"},
        "plugin": name,
        "tags": [{"en": "A", "zh": "甲"}, {"en": "B", "zh": "乙"}, {"en": "C", "zh": "丙"}],
        "quickPrompts": [{"en": "Start", "zh": "开始"}, {"en": "B", "zh": "乙"}, {"en": "C", "zh": "丙"}],
    }
    if cfg_over:
        for k, v in cfg_over.items():
            if v is None:
                cfg.pop(k, None)
            else:
                cfg[k] = v
    files = {
        "demo-expert/.codebuddy-plugin/plugin.json":
            json.dumps(cfg, ensure_ascii=False, indent=2).encode("utf-8"),
        "demo-expert/agents/demo-expert.md": b"---\nname: demo-expert\n---\n\nbody\n",
    }
    if avatar:
        files["demo-expert/avatars/expert.png"] = b"\x89PNG\r\n\x1a\n" + b"\0" * 16
    return files


def _bad_texts(rep):
    return [m for _, m in rep.bad]


SELFTESTS = []


def selftest(fn):
    SELFTESTS.append(fn)
    return fn


# --- 判据自检：每条都造一个「只错一处」的样本，断言它被抓到

def _pkg(files, **kw):
    """走 check_package 的真实路径。

    ⚠️ 别在这里自己拼判据调用 —— 那会造出「测试和被测代码走两条路」的假测试
    （已踩：早期样本带包名前缀，而判据假设前缀已剥，两边对不上，
      测出来的是样本的错，不是判据的错）。本函数只负责造样本。
    """
    rep, _ = check_package(files, "t", **kw)
    return rep

@selftest
def t_missing_required_field():
    files = _mk_skill(fm_over={"display_name": None})
    rep, _ = check_package(files, "t", None)
    assert any("display_name" in m for m in _bad_texts(rep)), "缺 display_name 未被抓"


@selftest
def t_undocumented_field_called_out():
    """★ 官方字段表未列的三个字段，缺失要单独点名 —— 这是本技能存在的第一理由。"""
    for f in ("display_name_en", "category"):
        files = _mk_skill(fm_over={f: None})
        rep, _ = check_package(files, "t", None)
        msgs = _bad_texts(rep)
        assert any(f in m and "解析失败" in m for m in msgs), \
            "缺 %s 时应点名并说明会解析失败，实得 %r" % (f, msgs)


@selftest
def t_description_en_limit():
    files = _mk_skill(fm_over={"description_en": "x" * (DESCRIPTION_EN_LIMIT + 1)})
    rep, _ = check_package(files, "t", None)
    assert any("description_en" in m and "上限" in m for m in _bad_texts(rep)), \
        "description_en 超限未被抓"


@selftest
def t_description_en_boundary_ok():
    """边界对照：刚好等于上限不该红。"""
    files = _mk_skill(fm_over={"description_en": "x" * DESCRIPTION_EN_LIMIT})
    rep, _ = check_package(files, "t", None)
    assert not any("description_en" in m for m in _bad_texts(rep)), "等于上限被误判为超限"


@selftest
def t_bad_name_format():
    files = _mk_skill(fm_over={"name": "Demo_Skill"})
    rep, _ = check_package(files, "t", None)
    assert any("name" in m and "不合规" in m for m in _bad_texts(rep)), "非法 name 未被抓"


@selftest
def t_no_frontmatter():
    files = {"demo-skill/SKILL.md": b"no frontmatter here\n"}
    rep, _ = check_package(files, "t", None)
    assert any("frontmatter" in m for m in _bad_texts(rep)), "无 frontmatter 未被抓"


@selftest
def t_unknown_package_type_not_green():
    """★ 认不出包必须报错，不能给绿。"""
    files = {"random/notes.txt": b"hello"}
    rep, ptype = check_package(files, "t", None)
    assert ptype is None and rep.bad, "认不出包时给了绿灯"


@selftest
def t_forbidden_subdir():
    files = _mk_skill()
    files["demo-skill/assets/big.png"] = b"\x89PNG"
    rep, _ = check_package(files, "t", None)
    assert any("assets" in m for m in _bad_texts(rep)), "技能包的白名单外子目录未被抓"


@selftest
def t_expert_allows_assets_dir():
    """★ 专家包允许 assets/，技能包不允许 —— 这两条口径不同，合并成一份清单就会误伤。

    教训：基线全绿不能证明判据对，也可能只是**没有样本触到它**。
    """
    files = _mk_expert()
    files["demo-expert/assets/big.bin"] = b"\0" * 64
    rep, _ = check_package(files, "t", None)
    assert not any("assets" in m for m in _bad_texts(rep)), \
        "专家包用了 assets/ 却被判违规 —— 判据把技能包口径错套到专家包上"


@selftest
def t_expert_still_rejects_junk_dir():
    """对照组：专家包的白名单外目录仍然要红，别为了放行 assets/ 把闸门整个拆了。"""
    files = _mk_expert()
    files["demo-expert/junk/big.bin"] = b"\0" * 64
    rep, _ = check_package(files, "t", None)
    assert any("junk" in m for m in _bad_texts(rep)), "专家包的白名单外子目录未被抓"


@selftest
def t_agents_ref_no_double_md():
    """★ plugin.json 的 agents[] 本来就带 .md —— 校验器若再补一次会拼出 x.md.md 永远匹配不上，
    于是在真实包上误报「agents 引用的文件找不到」。"""
    files = _mk_expert()
    assert "demo-expert/agents/demo-expert.md" in files, "样本构造有误"
    rep, _ = check_package(files, "t", None)
    assert not any("agents" in m for m in _bad_texts(rep)), \
        "agents 引用的真实存在的文件被判为缺失"


@selftest
def t_allowed_subdir_ok():
    files = _mk_skill()
    files["demo-skill/scripts/a.py"] = b"x=1"
    files["demo-skill/references/b.md"] = b"x"
    files["demo-skill/templates/c.txt"] = b"x"
    rep, _ = check_package(files, "t", None)
    assert not any("一级子目录" in m for m in _bad_texts(rep)), "白名单内子目录被误报"


@selftest
def t_bad_category_id():
    """★ 不存在的「专家团专属分类」是这个坑的代表值。"""
    files = _mk_expert(cfg_over={"categoryId": "00-ExpertTeam"})
    rep, _ = check_package(files, "t", None)
    assert any("categoryId" in m for m in _bad_texts(rep)), "非法 categoryId 未被抓"


@selftest
def t_all_15_category_ids_pass():
    for cid in sorted(VALID_CATEGORY_IDS):
        files = _mk_expert(cfg_over={"categoryId": cid})
        rep, _ = check_package(files, "t", None)
        assert not any("categoryId" in m for m in _bad_texts(rep)), "合法类目 %s 被误报" % cid


@selftest
def t_default_init_prompt_mismatch():
    files = _mk_expert(cfg_over={"defaultInitPrompt": {"zh": "别处", "en": "Start"}})
    rep, _ = check_package(files, "t", None)
    assert any("defaultInitPrompt" in m for m in _bad_texts(rep)), "defaultInitPrompt 不一致未被抓"


@selftest
def t_tags_count():
    files = _mk_expert(cfg_over={"tags": [{"en": "A", "zh": "甲"}]})
    rep, _ = check_package(files, "t", None)
    assert any("tags" in m for m in _bad_texts(rep)), "tags 数量不对未被抓"


@selftest
def t_bilingual_pairing():
    files = _mk_expert(cfg_over={"profession": {"en": "joy2know Demo"}})
    rep, _ = check_package(files, "t", None)
    assert any("profession" in m and "中英成对" in m for m in _bad_texts(rep)), "中英不成对未被抓"


@selftest
def t_display_description_length():
    files = _mk_expert(cfg_over={"displayDescription": {"en": "Short.", "zh": "太短了。"}})
    rep, _ = check_package(files, "t", None)
    assert any("displayDescription" in m for m in _bad_texts(rep)), "displayDescription 字数不对未被抓"


@selftest
def t_avatar_missing_file():
    files = _mk_expert(avatar=False)
    rep, _ = check_package(files, "t", None)
    assert any("avatar" in m for m in _bad_texts(rep)), "avatar 文件缺失未被抓"


@selftest
def t_avatar_bad_path():
    files = _mk_expert(cfg_over={"avatar": "icon.png"})
    rep, _ = check_package(files, "t", None)
    assert any("avatar" in m for m in _bad_texts(rep)), "avatar 路径非法未被抓"


@selftest
def t_plugin_name_mismatch():
    files = _mk_expert(cfg_over={"plugin": "other"})
    rep, _ = check_package(files, "t", None)
    assert any("plugin" in m for m in _bad_texts(rep)), "plugin 与 name 不一致未被抓"


@selftest
def t_team_missing_settings():
    cfg = _mk_expert()
    cfg["demo-expert/.codebuddy-plugin/plugin.json"] = json.dumps(
        {"name": "demo-expert", "plugin": "demo-expert", "version": "1.0.0",
         "expertType": "team", "agentName": "demo-lead",
         "agents": ["./agents/demo-lead.md"], "members": [],
         "displayName": {"en": "j", "zh": "签"}, "profession": {"en": "j", "zh": "签"},
         "displayDescription": {"en": "x", "zh": "这" * 44 + "。"},
         "categoryId": "02-Engineering", "avatar": "avatars/expert.png",
         "defaultInitPrompt": {"zh": "开始", "en": "Start"},
         "tags": [{"en": "A", "zh": "甲"}] * 3,
         "quickPrompts": [{"en": "Start", "zh": "开始"}, {"en": "B", "zh": "乙"}, {"en": "C", "zh": "丙"}],
         "description": "x"}, ensure_ascii=False).encode("utf-8")
    rep, _ = check_package(cfg, "t", None)
    assert any("settings.json" in m for m in _bad_texts(rep)), "专家团缺 settings.json 未被抓"


@selftest
def t_zip_flat_layout():
    """★ zip 第一层不能直接是 SKILL.md。"""
    files = _mk_skill()
    flat = {k.split("/", 1)[1]: v for k, v in files.items()}
    rep, _ = check_package(flat, "t", top_dirs=[], root_files=["SKILL.md"])
    assert any("第一层" in m for m in _bad_texts(rep)), "扁平 zip 未被抓"


@selftest
def t_zip_nested_ok():
    files = _mk_skill()
    rep, _ = check_package(files, "t", top_dirs=["demo-skill"], root_files=[])
    assert not any("第一层" in m for m in _bad_texts(rep)), "正确的 zip 结构被误报"


@selftest
def t_size_limit():
    files = _mk_skill()
    files["demo-skill/templates/big.bin"] = b"\0" * (SIZE_LIMIT_SKILL + 1)
    rep, _ = check_package(files, "t", None)
    assert any("体积" in m for m in _bad_texts(rep)), "体积超限未被抓"


# --- ★★ 关键：篡改判据本身，断言目标文案必须跟着翻转
# 这是「判据自检不是橡皮章」的唯一证据。没这一组，
# 上面的用例只能证明「坏包被报出来」，不能证明「好包会被放过」。

@selftest
def t_mutate_category_list_flip():
    """把 15 类清单改窄 → 原本合法的类目必须开始报错（判据确实在起作用）。"""
    global VALID_CATEGORY_IDS
    saved = VALID_CATEGORY_IDS
    try:
        VALID_CATEGORY_IDS = {"02-Engineering"}
        files = _mk_expert(cfg_over={"categoryId": "06-ContentCreative"})
        rep, _ = check_package(files, "t", None)
        assert any("categoryId" in m for m in _bad_texts(rep)), \
            "篡改类目清单后判据没有跟着变 —— 说明它本来就没在查"
    finally:
        VALID_CATEGORY_IDS = saved


@selftest
def t_mutate_description_limit_flip():
    """把上限从 1000 放宽到 2000 → 超 1000 的样本必须不再报错。"""
    global DESCRIPTION_EN_LIMIT
    saved = DESCRIPTION_EN_LIMIT
    try:
        DESCRIPTION_EN_LIMIT = 2000
        files = _mk_skill(fm_over={"description_en": "x" * 1500})
        rep, _ = check_package(files, "t", None)
        assert not any("description_en" in m for m in _bad_texts(rep)), \
            "放宽上限后仍然报错 —— 判据与文案不是同一件事"
    finally:
        DESCRIPTION_EN_LIMIT = saved


@selftest
def t_mutate_required_list_flip():
    """从必填清单里拿掉 version → 缺 version 的包必须不再报错。"""
    global REQUIRED_FRONTMATTER
    saved = REQUIRED_FRONTMATTER
    try:
        REQUIRED_FRONTMATTER = [f for f in saved if f != "version"]
        files = _mk_skill(fm_over={"version": None})
        rep, _ = check_package(files, "t", None)
        assert not any("version" in m for m in _bad_texts(rep)), \
            "拿掉必填项后仍然报错 —— 判据没在查这一条"
    finally:
        REQUIRED_FRONTMATTER = saved


def run_selftest():
    passed, failed = 0, []
    for fn in SELFTESTS:
        name = fn.__name__
        try:
            fn()
            passed += 1
            print("  [PASS] %s" % name)
        except AssertionError as e:
            failed.append((name, str(e)))
            print("  [FAIL] %s —— %s" % (name, e))
        except Exception as e:  # noqa: BLE001
            failed.append((name, "%s: %s" % (type(e).__name__, e)))
            print("  [ERROR] %s —— %s: %s" % (name, type(e).__name__, e))
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


def main():
    ap = argparse.ArgumentParser(add_help=True, description="WorkBuddy 资产包字段离线校验器")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dir", help="包目录路径")
    g.add_argument("--zip", dest="zip_path", help="zip 产物路径（单值，一次一个）")
    g.add_argument("--selftest", action="store_true", help="反向自检这个校验器本身")
    args = ap.parse_args()

    if args.selftest:
        return run_selftest()
    if args.dir:
        return run_dir(args.dir)
    return run_zip(args.zip_path)


if __name__ == "__main__":
    sys.exit(main())
