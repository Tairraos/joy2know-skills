#!/usr/bin/env node
/**
 * 晓得 / joy2know 资产包打包工具
 * ---------------------------------------------------------------
 *   pnpm build                      打包 packages/ 下全部包 → dist/
 *   pnpm build joy2know-mr          只打包指定包（可给多个，支持前缀匹配）
 *   pnpm list                       列出全部包及其状态
 *   pnpm build --no-check           跳过深度自检（selfcheck.py）
 *   pnpm build --strict             深度自检发现问题即中止（默认仅告警）
 *   pnpm build --no-skill-icons     不把技能图标写进内嵌技能目录
 *
 * 两条核心约定
 * ---------------------------------------------------------------
 * 1) 内嵌技能不存副本。
 *    专家/专家团包根放 skills.json 声明依赖，构建时才从 packages/<技能名>/
 *    复制真实技能进来 —— 同一份方法论只有一份源文件。
 *      { "skills": ["joy2know-clarify"] }
 *    同时按 skills.json 重写包内 plugin.json 的 skills 数组，杜绝两处漂移。
 *
 * 2) 图标只在仓库根 avatars/，包里不放。
 *      avatars/<包名>.png              专家/专家团自身的图标
 *                                      → 写到该包 plugin.json 里 avatar 字段指定的路径
 *      avatars/<包名>/<文件名>.png      专家团成员图标
 *                                      → 按文件名逐个写入包的 avatars/
 *      avatars/<技能名>.png            技能图标（唯一真源）
 *                                      → 独立技能包不注入（官方技能包无图标槽位，
 *                                        该图用于后台发布技能时上传）
 *                                      → 被内嵌进专家包时，复制为
 *                                        skills/<技能名>/icon.png
 *
 * 依赖：系统 zip / unzip（macOS、Linux 自带）。不引入任何 npm 依赖。
 */

import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { execFileSync, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PACKAGES = path.join(ROOT, 'packages');
const AVATARS = path.join(ROOT, 'avatars');
const DIST = path.join(ROOT, 'dist');

const EMBED_MANIFEST = 'skills.json';
const SKILL_ICON_NAME = 'icon.png';

const AVATAR_EXT = ['.png', '.jpg', '.jpeg', '.webp'];
const IMG_MAX_BYTES = 500 * 1024;
const IMG_SIZE = 512;
const ZIP_LIMIT = { skill: 3 * 1024 * 1024, expert: 20 * 1024 * 1024 };

// 深度自检脚本位置（可用环境变量 SELFCHECK 覆盖）
const SELFCHECK_CANDIDATES = [
  process.env.SELFCHECK,
  path.join(os.homedir(), '.workbuddy/skills/WorkBuddy资产包生产/scripts/selfcheck.py'),
].filter(Boolean);

const PY_CANDIDATES = [
  path.join(os.homedir(), '.workbuddy/binaries/python/envs/default/bin/python'),
  path.join(os.homedir(), '.workbuddy/binaries/python/versions/3.13.12/bin/python3'),
  'python3',
];

const C = {
  dim: (s) => `\x1b[2m${s}\x1b[0m`,
  red: (s) => `\x1b[31m${s}\x1b[0m`,
  green: (s) => `\x1b[32m${s}\x1b[0m`,
  yellow: (s) => `\x1b[33m${s}\x1b[0m`,
  cyan: (s) => `\x1b[36m${s}\x1b[0m`,
  bold: (s) => `\x1b[1m${s}\x1b[0m`,
};

// ---------------------------------------------------------------- 工具函数

const exists = (p) => fs.existsSync(p);
const norm = (rel) => rel.split(path.sep).join('/');

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

/** 读取 frontmatter 顶层键值（仅够用：键名 + 值文本，支持 >- 折叠） */
function parseFrontmatter(md) {
  const m = /^---\r?\n([\s\S]*?)\r?\n---/.exec(md);
  if (!m) return null;
  const body = m[1];
  const fields = {};
  let key = null;
  for (const line of body.split(/\r?\n/)) {
    const top = /^([A-Za-z_][\w-]*)\s*:\s*(.*)$/.exec(line);
    if (top) {
      key = top[1];
      fields[key] = top[2].trim();
    } else if (key && /^\s+\S/.test(line)) {
      fields[key] += ' ' + line.trim();
    }
  }
  for (const k of Object.keys(fields)) {
    fields[k] = fields[k].replace(/^[>|][-+]?\s*/, '').replace(/\s+/g, ' ').trim();
  }
  return { fields, raw: body };
}

/** 极简图片规格读取：PNG / JPEG，无依赖 */
function imageInfo(buf) {
  const PNG_SIG = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  if (buf.length > 24 && buf.subarray(0, 8).equals(PNG_SIG)) {
    return { format: 'PNG', width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
  }
  if (buf[0] === 0xff && buf[1] === 0xd8) {
    let i = 2;
    while (i < buf.length - 9) {
      if (buf[i] !== 0xff) { i++; continue; }
      const marker = buf[i + 1];
      if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker)) {
        return {
          format: 'JPEG',
          height: buf.readUInt16BE(i + 5),
          width: buf.readUInt16BE(i + 7),
        };
      }
      const len = buf.readUInt16BE(i + 2);
      if (!Number.isFinite(len) || len < 2) break;
      i += 2 + len;
    }
  }
  return null;
}

function walkFiles(dir, base = dir) {
  const out = [];
  if (!exists(dir)) return out;
  for (const name of fs.readdirSync(dir)) {
    if (name === '.DS_Store') continue;
    const full = path.join(dir, name);
    if (fs.statSync(full).isDirectory()) out.push(...walkFiles(full, base));
    else out.push(path.relative(base, full));
  }
  return out;
}

/** 在 avatars/ 里按「名字 + 任一图片后缀」找单文件图标 */
function findIcon(name) {
  return AVATAR_EXT.map((e) => path.join(AVATARS, name + e)).find(exists) || null;
}

/** 校验一张图标的规格，返回 { problems, warnings } */
function checkIcon(file, label) {
  const problems = [];
  const warnings = [];
  const buf = fs.readFileSync(file);
  const rel = norm(path.relative(ROOT, file));
  const info = imageInfo(buf);
  if (!info) {
    problems.push(`${rel}（${label}）不是可识别的 PNG / JPEG`);
    return { problems, warnings };
  }
  if (buf.length > IMG_MAX_BYTES) {
    problems.push(`${rel}（${label}）体积 ${(buf.length / 1024).toFixed(0)}KB，超过 500KB`);
  }
  if (info.width !== IMG_SIZE || info.height !== IMG_SIZE) {
    warnings.push(`${rel}（${label}）尺寸 ${info.width}×${info.height}，官方要求 512×512`);
  }
  if (info.format !== 'PNG') {
    warnings.push(`${rel}（${label}）是 ${info.format}，官方推荐 PNG`);
  }
  return { problems, warnings };
}

// ---------------------------------------------------------------- 包扫描

function scanPackages() {
  if (!exists(PACKAGES)) return [];
  const list = [];
  for (const name of fs.readdirSync(PACKAGES).sort()) {
    if (name.startsWith('.')) continue;
    const dir = path.join(PACKAGES, name);
    if (!fs.statSync(dir).isDirectory()) continue;

    const skillMd = path.join(dir, 'SKILL.md');
    const pluginJson = path.join(dir, '.codebuddy-plugin/plugin.json');
    const isExpert = exists(pluginJson);
    const isSkill = exists(skillMd);

    let type = null;
    if (isExpert) type = 'expert';
    else if (isSkill) type = 'skill';

    let expertSubtype = null;
    if (isExpert) {
      try { expertSubtype = readJson(pluginJson).expertType === 'team' ? 'team' : 'expert'; }
      catch { expertSubtype = 'expert'; }
    }

    // 内嵌技能声明
    let embed = [];
    let embedError = null;
    const manifestPath = path.join(dir, EMBED_MANIFEST);
    if (exists(manifestPath)) {
      try {
        const j = readJson(manifestPath);
        embed = (Array.isArray(j) ? j : j.skills || []).map(String);
      } catch (e) {
        embedError = `${EMBED_MANIFEST} 解析失败：${e.message}`;
      }
    }

    list.push({ name, dir, type, isExpert, isSkill, expertSubtype, skillMd, pluginJson, embed, embedError });
  }
  return list;
}

function displayNameOf(pkg) {
  if (pkg.isExpert) {
    try {
      const pj = readJson(pkg.pluginJson);
      const dn = pj.displayName;
      return (dn && (dn.zh || dn.en)) || pj.name || pkg.name;
    } catch { return '（plugin.json 解析失败）'; }
  }
  if (pkg.isSkill) {
    const fm = parseFrontmatter(fs.readFileSync(pkg.skillMd, 'utf8'));
    return fm?.fields.display_name || '（无 display_name）';
  }
  return '（无入口文件）';
}

// ---------------------------------------------------------------- 内嵌技能

/**
 * 把 skills.json 声明的外部技能复制进暂存目录，并同步 plugin.json 的 skills 数组。
 * 这是「同一份方法论只有一份源文件」的落点。
 */
function embedSkills(pkg, stageDir, opts) {
  const problems = [];
  const warnings = [];
  const injectedIcons = [];
  const manifestInStage = path.join(stageDir, EMBED_MANIFEST);

  // 描述文件不进包
  const dropManifest = () => { if (exists(manifestInStage)) fs.rmSync(manifestInStage, { force: true }); };

  if (pkg.embedError) {
    problems.push(pkg.embedError);
    dropManifest();
    return { problems, warnings, injectedIcons, count: 0 };
  }

  if (pkg.embed.length === 0) {
    // 没声明却留着副本 → 说明有人手抄了一份，明说
    const stray = path.join(stageDir, 'skills');
    if (exists(stray) && fs.readdirSync(stray).length > 0) {
      warnings.push(
        `包内有 skills/ 目录但 ${EMBED_MANIFEST} 是空的 —— ` +
        `请把技能名写进 ${EMBED_MANIFEST}，别在包里放副本`
      );
    }
    dropManifest();
    return { problems, warnings, injectedIcons, count: 0 };
  }

  if (!pkg.isExpert) {
    problems.push(`只有专家 / 专家团包才能内嵌技能，当前包是技能包`);
    dropManifest();
    return { problems, warnings, injectedIcons, count: 0 };
  }

  // 源包里若残留副本，直接弃用（以 skills.json 声明的真实技能为准）
  const stray = path.join(stageDir, 'skills');
  if (exists(stray)) {
    fs.rmSync(stray, { recursive: true, force: true });
    warnings.push(`源包里残留 skills/ 副本，已弃用并按 ${EMBED_MANIFEST} 重建`);
  }

  const declared = [];
  for (const sname of pkg.embed) {
    const src = path.join(PACKAGES, sname);
    if (!exists(src)) {
      problems.push(`${EMBED_MANIFEST} 引用的技能 “${sname}” 在 packages/ 下不存在`);
      continue;
    }
    if (!exists(path.join(src, 'SKILL.md'))) {
      problems.push(`packages/${sname} 不是技能包（缺 SKILL.md）`);
      continue;
    }
    const dst = path.join(stageDir, 'skills', sname);
    fs.cpSync(src, dst, { recursive: true });
    // 技能自己的描述文件 / 系统文件不该跟着走
    for (const junk of [EMBED_MANIFEST, '.DS_Store']) {
      const f = path.join(dst, junk);
      if (exists(f)) fs.rmSync(f, { force: true });
    }
    declared.push(`./skills/${sname}`);

    // 技能图标：唯一真源 avatars/<技能名>.png
    const icon = findIcon(sname);
    if (icon) {
      const chk = checkIcon(icon, `内嵌技能 ${sname} 的图标`);
      problems.push(...chk.problems);
      warnings.push(...chk.warnings);
      if (opts.skillIcons) {
        fs.copyFileSync(icon, path.join(dst, SKILL_ICON_NAME));
        injectedIcons.push(sname);
      }
    } else {
      warnings.push(`内嵌技能 ${sname} 缺图标：avatars/${sname}.png`);
    }
  }

  // plugin.json 的 skills 数组由 skills.json 唯一决定，避免两处漂移
  if (declared.length > 0) {
    const pjPath = path.join(stageDir, '.codebuddy-plugin/plugin.json');
    const pj = readJson(pjPath);
    const before = JSON.stringify(Array.isArray(pj.skills) ? pj.skills : []);
    if (before !== JSON.stringify(declared)) {
      pj.skills = declared;
      fs.writeFileSync(pjPath, JSON.stringify(pj, null, 2) + '\n');
      if (before !== '[]') {
        warnings.push(`plugin.json 的 skills 与 ${EMBED_MANIFEST} 不一致，已按后者同步为 ${JSON.stringify(declared)}`);
      }
    }
  }

  dropManifest();
  return { problems, warnings, injectedIcons, count: declared.length };
}

// ---------------------------------------------------------------- 图标注入

/**
 * 从根 avatars/ 解析该包的自身图标与成员图标。
 *   avatars/<包名>.png          → plugin.json 的 avatar 字段位置
 *   avatars/<包名>/<文件名>.png  → 包的 avatars/<文件名>
 * 返回 { dest: [{from,to,label}], problems, warnings, ownIcon }
 */
function resolveAvatars(pkg, stageDir) {
  const dest = [];
  const problems = [];
  const warnings = [];
  let ownIcon = null;

  // 1) 自身图标 → plugin.json 的 avatar 字段
  if (pkg.isExpert) {
    let pj;
    try {
      pj = readJson(path.join(stageDir, '.codebuddy-plugin/plugin.json'));
    } catch (e) {
      problems.push(`plugin.json 解析失败：${e.message}`);
      return { dest, problems, warnings, ownIcon };
    }
    const avatarField = pj.avatar;
    if (!avatarField) {
      problems.push('plugin.json 缺 avatar 字段');
    } else {
      const hit = findIcon(pkg.name);
      if (hit) {
        ownIcon = hit;
        dest.push({ from: hit, to: path.join(stageDir, avatarField), label: `${pkg.name} 自身图标` });
      } else if (!exists(path.join(stageDir, avatarField))) {
        warnings.push(
          `未找到自身图标 avatars/${pkg.name}.png —— 该包将不含 ${avatarField}（上传会失败）`
        );
      }
    }
  }

  // 2) 成员图标 → 包的 avatars/<文件名>
  const dirSrc = path.join(AVATARS, pkg.name);
  if (exists(dirSrc) && fs.statSync(dirSrc).isDirectory()) {
    for (const f of fs.readdirSync(dirSrc).sort()) {
      if (f.startsWith('.')) continue;
      const from = path.join(dirSrc, f);
      if (!fs.statSync(from).isFile()) continue;
      dest.push({ from, to: path.join(stageDir, 'avatars', f), label: `成员图标 ${f}` });
    }
  }

  // 3) 规格校验
  for (const item of dest) {
    const chk = checkIcon(item.from, item.label);
    problems.push(...chk.problems);
    warnings.push(...chk.warnings);
  }

  return { dest, problems, warnings, ownIcon };
}

// ---------------------------------------------------------------- 打包

function zipCommand() {
  const probe = spawnSync('zip', ['-v'], { stdio: 'ignore' });
  if (probe.error) {
    console.error(C.red('找不到 zip 命令。macOS / Linux 一般自带；Windows 请用 WSL 或 Git Bash。'));
    process.exit(2);
  }
}

function makeZip(stageParent, name, zipPath) {
  if (exists(zipPath)) fs.rmSync(zipPath);
  execFileSync(
    'zip',
    ['-rq', zipPath, name, '-x', '*.DS_Store', '-x', '__MACOSX/*'],
    { cwd: stageParent }
  );
}

function firstZipEntry(zipPath) {
  try {
    const out = execFileSync('unzip', ['-Z1', zipPath], { encoding: 'utf8' });
    return out.split('\n')[0];
  } catch {
    return null;
  }
}

function runSelfcheck(dir) {
  const script = SELFCHECK_CANDIDATES.find(exists);
  if (!script) return { skipped: true, reason: '未找到 selfcheck.py（可用 SELFCHECK=<路径> 指定）' };
  const py = PY_CANDIDATES.find((p) => p === 'python3' || exists(p));
  if (!py) return { skipped: true, reason: '未找到 python 解释器' };
  const r = spawnSync(py, [script, dir], { encoding: 'utf8' });
  if (r.error) return { skipped: true, reason: `自检执行失败：${r.error.message}` };
  return { skipped: false, code: r.status, output: (r.stdout || '') + (r.stderr || '') };
}

function buildOne(pkg, opts) {
  const problems = [];
  const warnings = [];

  if (!pkg.type) {
    problems.push('既没有 SKILL.md，也没有 .codebuddy-plugin/plugin.json —— 不是合法资产包');
    return { problems, warnings };
  }
  if (pkg.isExpert && pkg.isSkill) {
    problems.push('同时存在 SKILL.md 与 .codebuddy-plugin/plugin.json —— 类型有歧义');
    return { problems, warnings };
  }

  const stage = fs.mkdtempSync(path.join(os.tmpdir(), 'joy2know-build-'));
  const stageDir = path.join(stage, pkg.name);
  const zipPath = path.join(stage, `${pkg.name}.zip`);

  try {
    fs.cpSync(pkg.dir, stageDir, { recursive: true });

    // 1) 内嵌技能：从唯一真源复制
    const emb = embedSkills(pkg, stageDir, opts);
    problems.push(...emb.problems);
    warnings.push(...emb.warnings);

    // 2) 图标注入
    const av = resolveAvatars(pkg, stageDir);
    problems.push(...av.problems);
    warnings.push(...av.warnings);
    for (const item of av.dest) {
      fs.mkdirSync(path.dirname(item.to), { recursive: true });
      fs.copyFileSync(item.from, item.to);
    }

    // 3) 独立技能包：图标不进包，但缺了要提醒（后台发布时要用）
    let skillIcon = null;
    if (pkg.isSkill) {
      skillIcon = findIcon(pkg.name);
      if (!skillIcon) warnings.push(`缺技能图标 avatars/${pkg.name}.png（后台发布技能时要用）`);
    }

    fs.mkdirSync(DIST, { recursive: true });
    makeZip(stage, pkg.name, zipPath);

    const first = firstZipEntry(zipPath);
    if (first !== `${pkg.name}/`) {
      problems.push(`zip 第一层是 ${JSON.stringify(first)}，应为 ${pkg.name}/`);
    }

    const size = fs.statSync(zipPath).size;
    const limit = pkg.isExpert ? ZIP_LIMIT.expert : ZIP_LIMIT.skill;
    if (size > limit) {
      problems.push(`zip ${(size / 1024 / 1024).toFixed(2)}MB，超过上限 ${limit / 1024 / 1024}MB`);
    }

    const leaked = walkFiles(stageDir).filter((f) => /\.(pem|key|p12|env)$/i.test(f));
    if (leaked.length) problems.push(`包内出现疑似凭证文件：${leaked.join(', ')}`);

    let check = null;
    if (!opts.noCheck && problems.length === 0) {
      check = runSelfcheck(stage);
      if (!check.skipped && check.code !== 0 && opts.strict) {
        problems.push(`深度自检未通过（--strict）`);
      }
    }

    if (problems.length > 0 && !opts.force) {
      return { problems, warnings, check, size, published: false, embed: emb, ownIcon: av.ownIcon, skillIcon };
    }

    const finalZip = path.join(DIST, `${pkg.name}.zip`);
    fs.copyFileSync(zipPath, finalZip);

    return {
      problems, warnings, check, size, published: true, zip: finalZip,
      embed: emb, ownIcon: av.ownIcon, skillIcon,
    };
  } finally {
    fs.rmSync(stage, { recursive: true, force: true });
  }
}

// ---------------------------------------------------------------- CLI

function usage() {
  console.log(`
${C.bold('晓得 / joy2know 打包工具')}

  ${C.cyan('pnpm build')}                打包 packages/ 下全部包 → dist/
  ${C.cyan('pnpm build <名字...>')}      只打包指定包（支持前缀匹配）
  ${C.cyan('pnpm list')}                 列出全部包

  选项
    --no-check         跳过深度自检（selfcheck.py）
    --strict           深度自检发现问题即中止
    --force            即使有错误也写出 zip
    --no-skill-icons   不把技能图标写进内嵌技能目录
    --list             等价于 pnpm list
    --help             显示本帮助

  ${C.bold('内嵌技能')}  写在包根 ${EMBED_MANIFEST} 里，构建时从 packages/<技能名>/ 复制
  ${C.bold('图标')}      avatars/<包名>.png（自身）· avatars/<包名>/<文件名>.png（团队成员）
              avatars/<技能名>.png（技能图标，唯一真源）
`);
}

/** 按「终端可见宽度」补空格：CJK 记 2 列，ANSI 颜色码不计宽 */
const stripAnsi = (s) => String(s).replace(/\x1b\[[0-9;]*m/g, '');
const pad = (s, n) =>
  s + ' '.repeat(Math.max(0, n - [...stripAnsi(s)].reduce((a, c) => a + (c.charCodeAt(0) > 255 ? 2 : 1), 0)));

function cmdList(pkgs) {
  const ownIconState = (p) => {
    const single = findIcon(p.name);
    const folder = path.join(AVATARS, p.name);
    const hasDir = exists(folder) && fs.statSync(folder).isDirectory();
    // 成员数量是「附加信息」，不能替代自身图标的状态：
    // 只有成员目录、没有 avatars/<包名>.png 时，自身图标仍然是缺的（上传会失败）。
    const members = p.isExpert && hasDir
      ? C.dim(` +${fs.readdirSync(folder).filter((f) => !f.startsWith('.')).length} 成员`)
      : '';
    if (!single) return C.yellow('缺') + members;
    return C.green('✓') + members;
  };

  console.log('');
  console.log(C.bold(`packages/ 共 ${pkgs.length} 个包`) + C.dim('   （dist/ 为 zip 产物目录）'));
  console.log('');
  console.log(C.dim('  ' + pad('包名', 30) + pad('类型', 8) + pad('展示名', 18) + pad('自身图标', 12) + '内嵌技能'));
  console.log(C.dim('  ' + '─'.repeat(100)));

  let embedTotal = 0;
  let missingSkillIcons = 0;
  for (const p of pkgs) {
    const type = p.isExpert ? (p.expertSubtype === 'team' ? '专家团' : '专家') : (p.isSkill ? '技能' : C.red('非法'));
    let embedCell = C.dim('—');
    if (p.embedError) {
      embedCell = C.red('描述文件有误');
    } else if (p.embed.length > 0) {
      embedTotal += p.embed.length;
      const parts = p.embed.map((s) => {
        const hasSrc = exists(path.join(PACKAGES, s)) && exists(path.join(PACKAGES, s, 'SKILL.md'));
        const hasIcon = !!findIcon(s);
        if (!hasIcon) missingSkillIcons++;
        const mark = hasSrc ? (hasIcon ? C.green('✓') : C.yellow('◐')) : C.red('✗');
        return mark + C.dim(s.replace(/^joy2know-/, ''));
      });
      embedCell = `${p.embed.length} 个 ` + parts.join(' ');
    }
    console.log('  ' + pad(p.name, 30) + pad(type, 8) + pad(displayNameOf(p), 18) + pad(ownIconState(p), 12) + embedCell);
  }
  console.log('');
  console.log(C.dim(`  内嵌技能引用 ${embedTotal} 处（去重后 ${new Set(pkgs.flatMap((p) => p.embed)).size} 个技能），副本数为 0 —— 构建时才从 packages/ 复制`));
  if (missingSkillIcons > 0) {
    console.log(C.yellow(`  ◐ = 技能图标缺失（共 ${missingSkillIcons} 处）→ 补 avatars/<技能名>.png`));
  }
  console.log(C.dim('  自身图标：专家 / 专家团必填；技能图标用于后台发布，不进包'));
  console.log('');
}

function main() {
  const argv = process.argv.slice(2);
  const opts = {
    noCheck: argv.includes('--no-check'),
    strict: argv.includes('--strict'),
    force: argv.includes('--force'),
    skillIcons: !argv.includes('--no-skill-icons'),
  };

  if (argv.includes('--help') || argv.includes('-h')) return usage();

  const pkgs = scanPackages();
  if (pkgs.length === 0) {
    console.error(C.red('packages/ 下没有找到任何资产包。'));
    process.exit(1);
  }

  if (argv.includes('--list')) return cmdList(pkgs);

  const targets = argv.filter((a) => !a.startsWith('-'));
  let selected = pkgs;
  if (targets.length > 0) {
    selected = [];
    for (const t of targets) {
      const hits = pkgs.filter((p) => p.name === t || p.name.startsWith(t));
      if (hits.length === 0) {
        console.error(C.red(`找不到匹配 “${t}” 的包。用 pnpm list 查看全部。`));
        process.exit(1);
      }
      for (const h of hits) if (!selected.includes(h)) selected.push(h);
    }
  }

  zipCommand();
  console.log('');
  console.log(C.bold(`开始打包 ${selected.length} 个包 → dist/`));

  const results = [];
  let failed = 0;

  for (const pkg of selected) {
    process.stdout.write(`  ${C.dim('·')} ${pkg.name} … `);
    let r;
    try {
      r = buildOne(pkg, opts);
    } catch (e) {
      r = { problems: [`打包异常：${e.message}`], warnings: [], published: false, embed: { count: 0, injectedIcons: [] } };
    }
    results.push({ pkg, r });

    const embNote = r.embed && r.embed.count > 0 ? C.dim(` 内嵌 ${r.embed.count}`) : '';
    if (r.problems.length > 0 && !r.published) {
      failed++;
      console.log(C.red('失败'));
      for (const p of r.problems) console.log('      ' + C.red('✗ ') + p);
    } else if (r.warnings.length > 0 || (r.check && !r.check.skipped && r.check.code !== 0)) {
      console.log(C.yellow('通过（有告警）') + embNote);
      for (const w of r.warnings) console.log('      ' + C.yellow('! ') + w);
      if (r.check && !r.check.skipped && r.check.code !== 0) {
        console.log('      ' + C.yellow('! ') + '深度自检有输出，见下方汇总');
      }
    } else {
      console.log(C.green('通过') + embNote);
    }
  }

  // ---- 汇总表 ----
  console.log('');
  console.log(C.bold('打包结果'));
  console.log(C.dim('  ' + pad('包名', 30) + pad('类型', 8) + pad('内嵌技能', 10) + pad('zip', 12) + '状态'));
  console.log(C.dim('  ' + '─'.repeat(78)));
  for (const { pkg, r } of results) {
    const type = pkg.isExpert ? (pkg.expertSubtype === 'team' ? '专家团' : '专家') : '技能';
    const size = r.size ? (r.size / 1024).toFixed(1) + ' KB' : '—';
    const state = r.published ? C.green('✓ 已写入 dist/') : C.red('✗ 未写出');
    const emb = r.embed && r.embed.count > 0 ? `${r.embed.count} 个` : '—';
    console.log('  ' + pad(pkg.name, 30) + pad(type, 8) + pad(emb, 10) + pad(size, 12) + state);
  }
  console.log('');

  // ---- 内嵌技能注入明细 ----
  const withEmbed = results.filter((x) => x.r.embed && x.r.embed.count > 0);
  if (withEmbed.length > 0) {
    console.log(C.bold('内嵌技能（构建时从 packages/ 复制，仓库内无副本）'));
    for (const { pkg, r } of withEmbed) {
      const icons = (r.embed && r.embed.injectedIcons) || [];
      console.log('  ' + C.cyan(pkg.name) + C.dim(` ← ${pkg.embed.join(', ')}`));
      if (icons.length) {
        console.log('      ' + C.dim(`技能图标已注入：${icons.map((s) => `skills/${s}/${SKILL_ICON_NAME}`).join(', ')}`));
      }
    }
    console.log('');
  }

  // ---- 技能图标提示 ----
  const skillPkgs = results.filter((x) => x.pkg.isSkill);
  if (skillPkgs.length > 0) {
    const withIcon = skillPkgs.filter((x) => x.r.skillIcon).length;
    console.log(C.bold('技能图标') + C.dim(`  ${withIcon}/${skillPkgs.length} 个技能包已有 avatars/<技能名>.png`));
    const missing = skillPkgs.filter((x) => !x.r.skillIcon).map((x) => x.pkg.name);
    if (missing.length) console.log('  ' + C.yellow('缺：') + missing.join(', '));
    console.log(C.dim('  技能图标不进 zip —— 官方技能包没有图标槽位，该图用于后台发布技能时上传。'));
    console.log('');
  }

  // ---- 深度自检原文 ----
  const withCheck = results.filter((x) => x.r.check && !x.r.check.skipped && x.r.check.code !== 0);
  if (withCheck.length > 0) {
    for (const { pkg, r } of withCheck) {
      console.log(C.bold(`深度自检输出 · ${pkg.name}`));
      console.log(C.dim('  ' + r.check.output.trim().split('\n').join('\n  ')));
      console.log('');
    }
  }
  const skipped = results.find((x) => x.r.check && x.r.check.skipped);
  if (skipped) console.log(C.dim(`  （深度自检已跳过：${skipped.r.check.reason}）`));

  if (failed > 0) {
    console.error(C.red(`\n${failed} 个包打包失败。`));
    process.exit(1);
  }
  console.log(C.green(`全部完成：${results.length} 个包已写入 dist/`));
}

main();
