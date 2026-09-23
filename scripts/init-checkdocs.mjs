#!/usr/bin/env node
/**
 * 发布前检测报告 —— 骨架生成器
 * ---------------------------------------------------------------
 *   node scripts/init-checkdocs.mjs            为缺报告的包补骨架（不覆盖已有）
 *   node scripts/init-checkdocs.mjs --list     只列状态，不写文件
 *   node scripts/init-checkdocs.mjs <包名...>  只处理指定包（支持前缀匹配）
 *
 * 报告位置：packages/<包名>/<包名>.md
 *   - 与包目录同名（按约定）
 *   - **不进 zip**：构建工具在复制到暂存目录时排除它
 *   - **进 git**：要能看历史
 *
 * 本脚本**只生成骨架，不生成结论**。
 * 结论必须来自真实的四道门检测（见仓库根 AGENT.md 第 3 节），
 * 骨架里的状态一律是「⛔ 未检测」—— 编造检测结论比没有报告更糟。
 *
 * 零第三方依赖。
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PACKAGES = path.join(ROOT, 'packages');

const C = {
  dim: (s) => `\x1b[2m${s}\x1b[0m`,
  green: (s) => `\x1b[32m${s}\x1b[0m`,
  yellow: (s) => `\x1b[33m${s}\x1b[0m`,
  red: (s) => `\x1b[31m${s}\x1b[0m`,
  bold: (s) => `\x1b[1m${s}\x1b[0m`,
};

const exists = (p) => fs.existsSync(p);

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

function parseFrontmatter(md) {
  const m = /^---\r?\n([\s\S]*?)\r?\n---/.exec(md);
  if (!m) return {};
  const fields = {};
  let key = null;
  for (const line of m[1].split(/\r?\n/)) {
    const top = /^([A-Za-z_][\w-]*)\s*:\s*(.*)$/.exec(line);
    if (top) { key = top[1]; fields[key] = top[2].trim(); }
    else if (key && /^\s+\S/.test(line)) fields[key] += ' ' + line.trim();
  }
  return fields;
}

function walk(dir, base = dir) {
  const out = [];
  if (!exists(dir)) return out;
  for (const name of fs.readdirSync(dir).sort()) {
    if (name === '.DS_Store') continue;
    const full = path.join(dir, name);
    if (fs.statSync(full).isDirectory()) out.push(...walk(full, base));
    else out.push(path.relative(base, full).split(path.sep).join('/'));
  }
  return out;
}

function scanPackages() {
  const list = [];
  if (!exists(PACKAGES)) return list;
  for (const name of fs.readdirSync(PACKAGES).sort()) {
    if (name.startsWith('.')) continue;
    const dir = path.join(PACKAGES, name);
    if (!fs.statSync(dir).isDirectory()) continue;

    const skillMd = path.join(dir, 'SKILL.md');
    const pluginJson = path.join(dir, '.codebuddy-plugin/plugin.json');
    const isExpert = exists(pluginJson);
    const isSkill = exists(skillMd) && !isExpert;

    let version = '—';
    let label = '（无入口文件）';
    let subtype = null;
    let embed = [];
    if (isExpert) {
      try {
        const pj = readJson(pluginJson);
        version = String(pj.version || '—');
        subtype = pj.expertType === 'team' ? '专家团' : '专家';
        label = (pj.profession && (pj.profession.zh || pj.profession.en)) || pj.name || name;
      } catch { label = '（plugin.json 解析失败）'; }
    } else if (isSkill) {
      const fm = parseFrontmatter(fs.readFileSync(skillMd, 'utf8'));
      version = fm.version || '—';
      label = fm.display_name || '（无 display_name）';
    }
    const manifest = path.join(dir, 'skills.json');
    if (exists(manifest)) {
      try {
        const j = readJson(manifest);
        embed = (Array.isArray(j) ? j : j.skills || []).map(String);
      } catch { /* 交给构建工具报错 */ }
    }

    const type = isExpert ? subtype : (isSkill ? '技能' : '非法');
    list.push({ name, dir, type, isExpert, isSkill, version, label, embed,
      doc: path.join(dir, `${name}.md`), files: walk(dir) });
  }
  return list;
}

/** 从包内文件推出「待验证项」——只做机械枚举，不做任何结论 */
function pendingRows(pkg) {
  const rows = [];
  const scripts = pkg.files.filter((f) => /^scripts\/[^/]+\.(py|mjs|js|sh)$/.test(f));
  for (const s of scripts) {
    rows.push([`脚本 \`${s}\` 可运行且行为与 SKILL.md 描述一致`,
      `\`--help\` 至少一次 · 主流程真跑一次 · 边界样本一次`, '待测']);
  }
  const refs = pkg.files.filter((f) => /^references\/.+\.md$/.test(f));
  for (const r of refs) {
    rows.push([`参考文档 \`${r}\` 所述与实现一致（不能只是"写得好听"）`,
      '按文档描述的格式造样本，核对实现是否真按此处理', '待测']);
  }
  if (pkg.isSkill) {
    rows.push(['`SKILL.md` 声明的每条能力都有对应实现（门 2 完整性）',
      '逐条摘出承诺 → 与实现对照 → 标 有/无/部分', '待测']);
    rows.push(['`description` 里「不适用于」的场景确实不触发',
      '造该场景的输入，确认不会误触发', '待测']);
    rows.push(['SKILL.md frontmatter 9 个必填字段齐全且 YAML 合法',
      '`python3 scripts/selfcheck.py packages/' + pkg.name + '`', '待测']);
  } else {
    rows.push(['`plugin.json` 全字段齐全、三方成对、硬约束达标',
      '`python3 scripts/selfcheck.py packages/' + pkg.name + '`', '待测']);
    if ((pkg.type === '专家团')) {
      rows.push(['`settings.json` 与 `setting.json` 都在且内容一致、agent 指向主理人',
        '逐字比对两个文件与 `teamInfo.leadAgent`', '待测']);
      rows.push(['`agents[]` 文件名去 `.md` 与 `members[].id` 严格一一对应',
        '枚举比对（不是抽查）', '待测']);
    }
    if (pkg.embed.length) {
      rows.push([`内嵌技能（${pkg.embed.join('、')}）在包内可解析为技能`,
        '构建后检查 `skills/<名>/SKILL.md` 存在且与主源一致', '待测']);
    }
    rows.push(['卡面主标题取 `profession`、副标题取 `displayName`（别放反）',
      '按客户端实际渲染惯例核对取值', '待测']);
  }
  rows.push(['降级路径：声明「缺 X 就降级」的，把 X 藏起来仍不崩且提示正确',
    '临时改名/移走依赖后重跑', '待测']);
  rows.push(['反向验证：故意造「应该被抓」的错样本，确认真的被抓',
    '至少 1 组（例如去掉一个必填字段、篡改一处内容）', '待测']);
  return rows;
}

function skeleton(pkg) {
  const L = [];
  const fileList = pkg.files.map((f) => '  ' + f).join('\n');
  const pending = pendingRows(pkg);
  const rows = pending.map((r) => `| ${r[0]} | ${r[1]} | ${r[2]} | — |`).join('\n');

  L.push(`# 发布前检测报告 · ${pkg.label}（${pkg.name}）`);
  L.push('');
  L.push('> **本文件是开发期文档，不进 zip**（构建时自动排除）；但**要进 git**。');
  L.push('> 规范见仓库根 `AGENT.md` 第 3–4 节。**下次检测先读本文件**，只重测有变化的部分与「未覆盖项」。');
  L.push('');
  L.push(`- **包名**：${pkg.name}`);
  L.push(`- **类型**：${pkg.type}`);
  L.push(`- **对应版本**：${pkg.version}`);
  L.push('- **检测状态**：⛔ 未检测');
  L.push('- **最后检测**：—');
  L.push('- **检测方式**：—');
  L.push('');
  L.push('---');
  L.push('');
  L.push('## 一、包内文件（从磁盘枚举，不手写）');
  L.push('');
  L.push('```');
  L.push(fileList || '  （无）');
  L.push('```');
  L.push('');
  L.push('## 二、能力清单与验证结果');
  L.push('');
  L.push('> 「结果」栏取值：`✅ 通过` / `❌ 失败` / `⚠️ 部分` / `未覆盖`。');
  L.push('> **每格都要有证据**：真实命令 + 真实输出要点。只写「没报错」不算验证。');
  L.push('');
  L.push('| 能力 / 待验证项 | 验证方式（命令与样本） | 结果 | 证据要点 |');
  L.push('|---|---|---|---|');
  L.push(rows);
  L.push('');
  L.push('## 三、门 2 · 完整性对照（文档承诺 → 实现）');
  L.push('');
  L.push('> 把 `SKILL.md` / `plugin.json` / `agents/*.md` 里的能力承诺逐条摘出来对照。');
  L.push('> 重点抓「文档写了、实现没做」——这在 v1.1.0 的 `joy2know-asset-ledger` 上真实发生过。');
  L.push('');
  L.push('| 文档承诺（摘原文） | 实现位置 | 有 / 无 / 部分 | 备注 |');
  L.push('|---|---|---|---|');
  L.push('|  |  |  |  |');
  L.push('');
  L.push('## 四、门 3 · 合理性结论');
  L.push('');
  L.push('- **规则是否自洽**：（两条规则有没有互相打架）');
  L.push('- **推断是否标注为推断**：（靠启发式猜出的结论有没有标出来）');
  L.push('- **错误提示是否可指导下一步**：');
  L.push('- **边界是否优雅**（空数据 / 缺文件 / 旧格式 / 重复记录）：');
  L.push('- **零依赖是否守住**：');
  L.push('- **值来源是否可追溯**：');
  L.push('');
  L.push('## 五、门 4 · 测试真实性自评（防放水）');
  L.push('');
  L.push('> 逐条自查下面七种假测试形态，中一条即视为本门未通过。');
  L.push('');
  L.push('- [ ] 1. 只跑 happy path，没跑边界');
  L.push('- [ ] 2. 只看「没报错 / 退出码 0」，没核对输出内容');
  L.push('- [ ] 3. 把「文档写了」当成「已验证」');
  L.push('- [ ] 4. 自造理想样本（比真实产物干净）');
  L.push('- [ ] 5. 跳过失败项、不记录');
  L.push('- [ ] 6. 修完只测修好的那条，没跑回归');
  L.push('- [ ] 7. 造错样本只造了会被抓的那种（门禁变橡皮章）');
  L.push('');
  L.push('**反向验证记录**（做了什么、造了什么错样本、工具是否亮红灯）：');
  L.push('');
  L.push('**一句话回答**：本包的核心能力如果坏掉，是哪一步会亮红灯？');
  L.push('');
  L.push('## 六、未覆盖项 / 已知缺陷 / 待办');
  L.push('');
  L.push('> **这一栏不许空着。** 没有任何一次检测能覆盖 100%；空着 = 没认真写。');
  L.push('> 每次检测顺手消掉一条，让它越来越薄。');
  L.push('');
  L.push('**未覆盖项**（尚未验证的能力或场景）：');
  L.push('');
  L.push('- 本报告尚未做任何实测 —— **全部能力均为未覆盖**。按「二」的待验证项逐条走完四道门后回填。');
  L.push('');
  L.push('**已知缺陷**：');
  L.push('');
  L.push('- （无记录）');
  L.push('');
  L.push('**待办**：');
  L.push('');
  L.push('- 完成首次四道门检测，把头部「检测状态」改为实际结论，并把「对应版本」锁定为当时版本。');
  L.push('');
  L.push('## 七、检测履历');
  L.push('');
  L.push('| 日期 | 版本 | 状态 | 摘要（本轮测了什么、改了什么） |');
  L.push('|---|---|---|---|');
  L.push(`| — | ${pkg.version} | ⛔ 未检测 | 骨架生成，等待首次检测 |`);
  L.push('');
  return L.join('\n');
}

/** 读报告头部的检测状态（供 --list 汇总）*/
function docState(pkg) {
  if (!exists(pkg.doc)) return { has: false };
  const t = fs.readFileSync(pkg.doc, 'utf8');
  const st = /^-\s*\*\*检测状态\*\*[：:]\s*(.+)$/m.exec(t);
  const ver = /^-\s*\*\*对应版本\*\*[：:]\s*(\S+)/m.exec(t);
  return { has: true, status: st ? st[1].trim() : '（缺状态行）', version: ver ? ver[1] : '（缺版本行）' };
}

function main() {
  const argv = process.argv.slice(2);
  const listOnly = argv.includes('--list');
  const targets = argv.filter((a) => !a.startsWith('-'));

  let pkgs = scanPackages();
  if (pkgs.length === 0) {
    console.error(C.red('packages/ 下没有找到任何包。'));
    process.exit(1);
  }
  if (targets.length) {
    pkgs = pkgs.filter((p) => targets.some((t) => p.name === t || p.name.startsWith(t)));
    if (pkgs.length === 0) {
      console.error(C.red('没有匹配的包。'));
      process.exit(1);
    }
  }

  console.log('');
  console.log(C.bold('发布前检测报告 · 状态总览') + C.dim('   （packages/<包名>/<包名>.md）'));
  console.log('');
  const pad = (s, n) => s + ' '.repeat(Math.max(0, n - [...String(s)].reduce((a, c) => a + (c.charCodeAt(0) > 255 ? 2 : 1), 0)));
  console.log(C.dim('  ' + pad('包名', 30) + pad('类型', 8) + pad('版本', 9) + pad('报告', 8) + '检测状态'));
  console.log(C.dim('  ' + '─'.repeat(96)));

  let created = 0;
  let missing = 0;
  for (const p of pkgs) {
    const st = docState(p);
    let cell;
    if (!st.has) {
      missing++;
      cell = C.yellow('缺报告');
      if (!listOnly) {
        fs.writeFileSync(p.doc, skeleton(p), 'utf8');
        created++;
        cell = C.green('已生成骨架');
      }
    } else {
      cell = /未检测|未通过/.test(st.status) ? C.yellow(st.status) : C.green(st.status);
      if (st.version !== p.version) cell += C.yellow(`（报告版本 ${st.version} ≠ 包版本 ${p.version}）`);
    }
    console.log('  ' + pad(p.name, 30) + pad(p.type, 8) + pad(p.version, 9) + pad(st.has ? '✓' : '✗', 8) + cell);
  }
  console.log('');

  if (listOnly) {
    console.log(C.dim(`  共 ${pkgs.length} 个包，缺报告 ${missing} 个（加 --list 以外的参数即可生成骨架）。`));
  } else {
    console.log(created > 0
      ? C.green(`已为 ${created} 个包生成报告骨架`) + C.dim('（其余已有报告，未改动）')
      : C.dim('全部包都已有报告，未改动任何文件。'));
    console.log(C.dim('  骨架里的结论一律是「⛔ 未检测」—— 结论只能来自真实的四道门检测（见 AGENT.md）。'));
  }
  console.log('');
}

main();
