#!/usr/bin/env node
/**
 * 晓得 / joy2know 资产包打包工具
 * ---------------------------------------------------------------
 *   pnpm build                      打包 packages/ 下全部包 → dist/
 *   pnpm build joy2know-mr          只打包指定包（可给多个，支持前缀匹配）
 *   pnpm list                       列出全部包及其状态
 *   pnpm build --no-check           跳过深度自检（selfcheck.py）
 *   pnpm build --strict             深度自检 / 检测文档有问题即中止（默认仅告警）
 *   pnpm build --no-skill-icons     不把技能图标写进内嵌技能目录
 *   pnpm build --keep-old-zips      保留 dist/ 里同包的旧版本 zip（默认清理）
 *   pnpm build --no-manifest        不重写仓库根的 发布清单.md
 *
 * 四条核心约定
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
 * 3) 产物文件名带版本号：dist/<包名>-v<版本>.zip。
 *    上传平台用哪一个一目了然；同包的旧版本 zip 在下次构建时自动清理
 *    （zip 第一层仍必须是包目录名 —— 文件名不参与平台解析）。
 *
 * 4) 开发期文档不进包，发布清单自动生成。
 *    packages/<包名>/<包名>.md 是「发布前检测报告」（规范见 AGENT.md），
 *    构建时排除，不进 zip。仓库根 发布清单.md 的前四节由本脚本依据
 *    packages/ 实际版本 + release.config.json 重写，人工只改
 *    「发布时要注意」与「发布历史」两节。
 *    清单在**仓库根**而非 dist/ —— dist/ 是 gitignore 的产物目录，
 *    而清单里记着发布历史，属于要进 git 的资产。
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

// 发布参考信息（建议发布类目 / 平台侧最后版本）—— 唯一真源
const RELEASE_CONFIG = path.join(ROOT, 'release.config.json');
// 发布清单：前四节自动重写，AUTO:END 之后的人工段落原样保留。
// **放在仓库根**（不在 dist/）：dist/ 是 gitignore 的产物目录，清单里记着发布历史，
// 属于版本化资产，删一次 dist 不该把历史一起丢掉。
const MANIFEST = path.join(ROOT, '发布清单.md');
// 老位置遗留的清单（曾经放在 dist/），构建时顺手清掉，避免两处并存误导人
const LEGACY_MANIFEST_RE = /^发布清单(?:-\d+(?:\.\d+)*)?\.md$/;
const AUTO_BEGIN = '<!-- AUTO:BEGIN -->';
const AUTO_END = '<!-- AUTO:END -->';
// 发布前检测报告（开发期文档，不进包）；规范见 AGENT.md
const checkDocOf = (pkg) => path.join(pkg.dir, `${pkg.name}.md`);

const AVATAR_EXT = ['.png', '.jpg', '.jpeg', '.webp'];
const IMG_MAX_BYTES = 500 * 1024;
const IMG_SIZE = 512;
const ZIP_LIMIT = { skill: 3 * 1024 * 1024, expert: 20 * 1024 * 1024 };

// 深度自检脚本位置。
// 优先用**仓库自带**那一份（scripts/selfcheck.py）：本仓库不依赖任何本机技能目录，
// 换一台机器克隆下来就能跑完整自检。本机技能目录里的那份只作兜底。
// 需要临时换用别的副本时用环境变量 SELFCHECK=<路径>。
const SELFCHECK_CANDIDATES = [
  process.env.SELFCHECK,
  path.join(ROOT, 'scripts/selfcheck.py'),
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

/** 类型标签：技能 / 专家 / 专家团 */
function typeLabelOf(pkg) {
  if (pkg.isExpert) return pkg.expertSubtype === 'team' ? '专家团' : '专家';
  return pkg.isSkill ? '技能' : '非法';
}

/** 该包要上传的版本号：技能取 SKILL.md 的 version，专家/团取 plugin.json 的 version */
function versionOf(pkg) {
  if (pkg.isExpert) {
    try { return String(readJson(pkg.pluginJson).version || '—'); } catch { return '—'; }
  }
  if (pkg.isSkill) {
    const fm = parseFrontmatter(fs.readFileSync(pkg.skillMd, 'utf8'));
    return fm?.fields.version || '—';
  }
  return '—';
}

/** 发布用 zip 的文件名（带版本号）*/
const zipNameOf = (pkg) => `${pkg.name}-v${versionOf(pkg)}.zip`;

/** 技能包需要额外展示的 frontmatter 字段 */
function skillMetaOf(pkg) {
  try {
    const f = parseFrontmatter(fs.readFileSync(pkg.skillMd, 'utf8'))?.fields || {};
    return { zh: f.display_name || '—', en: f.display_name_en || '—' };
  } catch { return { zh: '—', en: '—' }; }
}

/** 专家/专家团：profession 与 categoryId 都写在包内 plugin.json */
function expertMetaOf(pkg) {
  try {
    const pj = readJson(pkg.pluginJson);
    const pf = pj.profession || {};
    return { zh: pf.zh || '—', en: pf.en || '—', categoryId: pj.categoryId || '—' };
  } catch { return { zh: '—', en: '—', categoryId: '—' }; }
}

/** 读 release.config.json（缺失 / 损坏都不致命，只告警）*/
function loadReleaseConfig() {
  if (!exists(RELEASE_CONFIG)) return { packages: {}, error: `${path.basename(RELEASE_CONFIG)} 不存在` };
  try {
    const j = readJson(RELEASE_CONFIG);
    return { packages: j.packages || {}, error: null };
  } catch (e) {
    return { packages: {}, error: `${path.basename(RELEASE_CONFIG)} 解析失败：${e.message}` };
  }
}

/** dist 里已构建产物的体积（KB 字符串）；未构建返回 null */
function builtSizeOf(zipName) {
  const p = path.join(DIST, zipName);
  if (!exists(p)) return null;
  return (fs.statSync(p).size / 1024).toFixed(1) + ' KB';
}

/**
 * 读包内「发布前检测报告」的状态。
 * 约定（见 AGENT.md）：报告里有一行 `- **对应版本**：x.y.z` 与一行 `- **检测状态**：…`。
 */
function checkDocState(pkg) {
  const p = checkDocOf(pkg);
  if (!exists(p)) return { exists: false };
  const text = fs.readFileSync(p, 'utf8');
  const ver = /^-\s*\*\*对应版本\*\*[：:]\s*(\S+)/m.exec(text);
  const st = /^-\s*\*\*检测状态\*\*[：:]\s*(.+)$/m.exec(text);
  const newest = newestSourceMtime(pkg);
  return {
    exists: true,
    path: p,
    version: ver ? ver[1] : null,
    status: st ? st[1].trim() : null,
    stale: newest > fs.statSync(p).mtimeMs,
  };
}

/** 包内源码文件的最新修改时间（排除检测报告自身）*/
function newestSourceMtime(pkg) {
  const docName = `${pkg.name}.md`;
  let newest = 0;
  for (const rel of walkFiles(pkg.dir)) {
    const base = path.basename(rel);
    if (base === docName || base === '.DS_Store') continue;
    try { newest = Math.max(newest, fs.statSync(path.join(pkg.dir, rel)).mtimeMs); } catch { /* ignore */ }
  }
  return newest;
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
    // 技能自己的描述文件、发布前检测报告、系统文件不该跟着走
    //（检测报告是开发期文档，与包根那一份同理：不进 zip）
    for (const junk of [EMBED_MANIFEST, `${sname}.md`, '.DS_Store']) {
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
  // __pycache__ / *.pyc 是跑过 Python 脚本就会冒出来的运行时产物，
  // 一旦进包会被深度自检判为「含临时文件」，故在打包层统一排除。
  execFileSync(
    'zip',
    ['-rq', zipPath, name,
      '-x', '*.DS_Store', '-x', '__MACOSX/*',
      '-x', '*/__pycache__/*', '-x', '*.pyc', '-x', '*.pyo'],
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

/**
 * 清理 dist/ 里同包的旧产物，只留本次写出的那一个。
 * 精确匹配「<包名>.zip」与「<包名>-v<数字>.zip」，绝不碰其它包的文件；
 * 只动 dist/（构建产物目录），不动源目录。--keep-old-zips 可关闭。
 */
function pruneOldZips(pkg, keepName, opts) {
  const removed = [];
  if (opts.keepOldZips || !exists(DIST)) return removed;
  const esc = pkg.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const re = new RegExp(`^${esc}(?:-v\\d+(?:\\.\\d+)*)?\\.zip$`);
  for (const f of fs.readdirSync(DIST)) {
    if (f === keepName || !re.test(f)) continue;
    fs.rmSync(path.join(DIST, f), { force: true });
    removed.push(f);
  }
  return removed;
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
  const zipName = zipNameOf(pkg);
  const docName = `${pkg.name}.md`;

  // 发布前检测报告是开发期文档，连同系统垃圾一起挡在暂存目录之外。
  // 注意：**只能排除包根的那一个** —— 专家包的 agent 文件可能与包同名
  //（如 agents/joy2know-code-scholar.md），按文件名匹配会误删它。
  const stageFilter = (src) => {
    const rel = path.relative(pkg.dir, src);
    if (!rel) return true;
    const relPosix = rel.split(path.sep).join('/');
    if (path.basename(src) === '.DS_Store') return false;
    return relPosix !== docName;
  };

  try {
    fs.cpSync(pkg.dir, stageDir, { recursive: true, filter: stageFilter });

    // 0) 发布前检测门 —— 见 AGENT.md。默认只告警；--strict 时算失败。
    const doc = checkDocState(pkg);
    if (!doc.exists) {
      warnings.push(`缺发布前检测报告 packages/${pkg.name}/${docName}（规范见 AGENT.md）`);
    } else {
      if (doc.status && /未检测|未通过|待检测/.test(doc.status)) {
        warnings.push(`发布前检测报告未通过：${doc.status}（packages/${pkg.name}/${docName}）`);
      }
      if (doc.version && doc.version !== versionOf(pkg)) {
        warnings.push(
          `发布前检测报告对应版本 ${doc.version} ≠ 包版本 ${versionOf(pkg)} —— 改过内容就要重测并同步文档`
        );
      }
      if (!doc.version || !doc.status) {
        warnings.push(`发布前检测报告缺「对应版本」或「检测状态」行（packages/${pkg.name}/${docName}）`);
      }
      if (doc.stale) {
        warnings.push(`包内文件比发布前检测报告新 —— 报告可能已过期（packages/${pkg.name}/${docName}）`);
      }
    }
    if (opts.strict && warnings.some((w) => w.includes('发布前检测报告'))) {
      problems.push('发布前检测未通过（--strict）');
      return { problems, warnings, check: null, published: false, zipName };
    }

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
      return { problems, warnings, check, size, published: false, embed: emb, ownIcon: av.ownIcon, skillIcon, zipName };
    }

    // 产物文件名带版本号：dist/<包名>-v<版本>.zip
    const finalZip = path.join(DIST, zipName);
    fs.copyFileSync(zipPath, finalZip);
    const pruned = pruneOldZips(pkg, zipName, opts);

    return {
      problems, warnings, check, size, published: true, zip: finalZip, zipName, pruned,
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
    --strict           深度自检 / 发布前检测报告有问题即中止
    --force            即使有错误也写出 zip
    --no-skill-icons   不把技能图标写进内嵌技能目录
    --keep-old-zips    保留 dist/ 里同包的旧版本 zip（默认清理）
    --no-manifest      不重写仓库根的 发布清单.md
    --list             等价于 pnpm list
    --help             显示本帮助

  ${C.bold('产物')}      dist/<包名>-v<版本>.zip（带版本号，同包只留最新一版）
  ${C.bold('发布清单')}  发布清单.md（仓库根）：前四节自动生成，末两节人工维护
  ${C.bold('检测报告')}  packages/<包名>/<包名>.md：发布前检测，开发期文档，不进 zip（规范见 AGENT.md）
  ${C.bold('内嵌技能')}  写在包根 ${EMBED_MANIFEST} 里，构建时从 packages/<技能名>/ 复制
  ${C.bold('图标')}      avatars/<包名>.png（自身）· avatars/<包名>/<文件名>.png（团队成员）
              avatars/<技能名>.png（技能图标，唯一真源）
`);
}

/** 按「终端可见宽度」补空格：CJK 记 2 列，ANSI 颜色码不计宽 */
const stripAnsi = (s) => String(s).replace(/\x1b\[[0-9;]*m/g, '');
const pad = (s, n) =>
  s + ' '.repeat(Math.max(0, n - [...stripAnsi(s)].reduce((a, c) => a + (c.charCodeAt(0) > 255 ? 2 : 1), 0)));

// ---------------------------------------------------------------- 发布清单

const two = (n) => String(n).padStart(2, '0');
function fmtStamp(d) {
  return `${d.getFullYear()}-${two(d.getMonth() + 1)}-${two(d.getDate())} ${two(d.getHours())}:${two(d.getMinutes())}`;
}

/** 状态：本地版本 vs 平台侧最后版本 */
function publishStatusOf(pkg, entry) {
  const local = versionOf(pkg);
  const pv = entry?.platform?.version || null;
  if (!pv) return '待上传';
  return pv === local ? '已提交' : '**已提交** ·【本地升级】';
}

/** 一行的体积 / zip 单元格 */
function zipCellOf(pkg) {
  const name = zipNameOf(pkg);
  const size = builtSizeOf(name);
  return { name, size, cell: size ? `\`${name}\`` : `\`${name}\` ⚠未构建`, sizeCell: size || '—' };
}

function renderSkillSection(skills, cfg) {
  const L = [];
  L.push(`## 一、技能（Skill）· ${skills.length} 个`);
  L.push('');
  L.push('> 技能包 **zip 内不含图标** —— 发布时需另外上传 `avatars/<包名>.png`（512×512 PNG，≤500KB）。');
  L.push('');
  L.push('| # | 中文名（display_name） | 英文名（display_name_en） | 本地版本 | 发布 zip（带版本号） | 体积 | 建议发布类目 | 平台侧最后版本 | 状态 |');
  L.push('|---|---|---|---|---|---|---|---|---|');
  skills.forEach((p, i) => {
    const meta = skillMetaOf(p);
    const e = cfg.packages[p.name] || {};
    const cat = e.suggestedCategory
      ? (e.categoryConfirmed ? `${e.suggestedCategory} ★已实证` : e.suggestedCategory)
      : '—';
    const z = zipCellOf(p);
    const pv = e.platform?.version || '—';
    L.push(`| ${i + 1} | ${meta.zh} | ${meta.en} | ${versionOf(p)} | ${z.cell} | ${z.sizeCell} | ${cat} | ${pv} | ${publishStatusOf(p, e)} |`);
  });
  L.push('');
  const notes = [];
  for (const p of skills) {
    const e = cfg.packages[p.name] || {};
    if (e.categoryNote) notes.push(`- \`${p.name}\`：${e.categoryNote}`);
    if (e.platform?.note) notes.push(`- \`${p.name}\`（平台侧）：${e.platform.note}`);
  }
  if (notes.length) {
    L.push('**逐包备注**');
    L.push('');
    L.push(notes.join('\n'));
    L.push('');
  }
  return L;
}

function renderExpertSection(pkgs, cfg, team) {
  const count = pkgs.length;
  const L = [];
  L.push(team
    ? `## 三、专家团（Expert Team）· ${count} 个`
    : `## 二、单专家（Expert）· ${count} 个`);
  L.push('');
  L.push(team
    ? '> 图标（团自身 + 全部成员）已在包内，无需另传。`categoryId` 随包提交 —— 发布页一般无需再选类目。'
    : '> 图标（自身）已在包内，无需另传。`categoryId` 随包提交 —— 发布页一般无需再选类目。');
  L.push('');
  L.push('| # | 中文名（profession.zh） | 英文名（profession.en） | categoryId | 本地版本 | 发布 zip（带版本号） | 体积 | 内嵌技能（版本） | 平台侧最后版本 | 状态 |');
  L.push('|---|---|---|---|---|---|---|---|---|---|');
  pkgs.forEach((p, i) => {
    const meta = expertMetaOf(p);
    const e = cfg.packages[p.name] || {};
    const embed = (p.embed || [])
      .map((s) => {
        const sp = pkgsAll.find((x) => x.name === s);
        return `\`${s}\`${sp ? ' ' + versionOf(sp) : ''}`;
      })
      .join('、') || '—';
    const z = zipCellOf(p);
    const pv = e.platform?.version || '—';
    L.push(`| ${i + 1} | ${meta.zh} | ${meta.en} | \`${meta.categoryId}\` | ${versionOf(p)} | ${z.cell} | ${z.sizeCell} | ${embed} | ${pv} | ${publishStatusOf(p, e)} |`);
  });
  L.push('');
  const notes = [];
  for (const p of pkgs) {
    const e = cfg.packages[p.name] || {};
    if (e.platform?.note) notes.push(`- \`${p.name}\`（平台侧）：${e.platform.note}`);
  }
  if (notes.length) {
    L.push('**逐包备注**');
    L.push('');
    L.push(notes.join('\n'));
    L.push('');
  }
  return L;
}

// 全量包引用（构建清单时填，供内嵌技能显示版本）
let pkgsAll = [];

function renderManifest(pkgs, cfg, stamp) {
  const skills = pkgs.filter((p) => p.isSkill && !p.isExpert);
  const experts = pkgs.filter((p) => p.isExpert && p.expertSubtype !== 'team');
  const teams = pkgs.filter((p) => p.isExpert && p.expertSubtype === 'team');

  const byVer = {};
  for (const p of pkgs) byVer[versionOf(p)] = (byVer[versionOf(p)] || 0) + 1;
  const verLine = Object.entries(byVer)
    .sort((a, b) => b[0].localeCompare(a[0], undefined, { numeric: true }))
    .map(([v, c]) => `${v} ×${c}`)
    .join('、');

  const L = [];
  L.push('# 发布清单 · 晓得 / joy2know');
  L.push('');
  L.push('> **前四节由 `pnpm build` 自动重写** —— 数据取自 packages/ 的实际版本与 `release.config.json`。');
  L.push('> **请勿手工编辑这些表格**：改了下一次构建就会覆盖。要改「建议发布类目 / 平台侧版本」，改 `release.config.json`。');
  L.push('> 人工维护的两节在文末 ——「五、发布时要注意」与「六、发布历史」，构建不会改动。');
  L.push('');
  L.push(`**生成时间**：${stamp}  ·  **包总数**：${pkgs.length}（技能 ${skills.length} · 专家 ${experts.length} · 专家团 ${teams.length}）`);
  L.push('');
  L.push(`**本地版本**：${verLine}`);
  L.push('');
  L.push('**状态口径**：`待上传` = 平台侧从未上线；`已提交` = 平台侧最后一个版本与本地一致；`已提交 ·【本地升级】` = 平台侧还是旧版，本地已抬高版本、**需要重传**（走「更新」而非「新建」）。');
  L.push('');
  L.push('---');
  L.push('');
  L.push(...renderSkillSection(skills, cfg));
  L.push('---');
  L.push('');
  L.push(...renderExpertSection(experts, cfg, false));
  L.push('---');
  L.push('');
  L.push(...renderExpertSection(teams, cfg, true));
  L.push('---');
  L.push('');
  L.push('## 四、产物规则（发布前对照）');
  L.push('');
  L.push('- **产物文件名**：`dist/<包名>-v<版本>.zip`（带版本号，便于区分是哪一版）。');
  L.push('- **同包只留最新一版**：每次构建后自动清理该包的旧版本 zip 与旧的无版本号 zip；`--keep-old-zips` 可保留。');
  L.push('- **zip 第一层必须是包目录名**（`<包名>/…`）—— 平台靠它解析，**外层文件名不参与解析**，改名不影响上传。');
  L.push('- **体积上限**：技能 3 MB · 专家 / 专家团 20 MB · 单张图标 500 KB @ 512×512。');
  L.push('- **技能包不含图标**：技能图标在后台发布时单独上传，不占 zip 配额。');
  L.push('- **`★已实证` 的含义**：该建议类目来自平台的判定 / 驳回原文；其余建议类目只是**方向参考**，发布时以下拉框里最接近的一项为准，**首选看平台给出的判定提示**。');
  L.push('');
  return L.join('\n');
}

const DEFAULT_MANUAL_TAIL = `\n---

## 五、发布时要注意

> 本节由人工维护，构建不会改动。

（待补充）

---

## 六、发布历史

> 本节由人工维护，构建不会改动。**每次发布 / 重传都要在这里追加一行**：日期 · 包名 · 版本 · 上传的文件名 · 结果。
> 文件名按当时的实际产物记录（早期无版本号的产物照原样写，别追改历史）。

| 发布日期 | 包名 | 类型 | 版本 | 上传文件 | 结果 |
|---|---|---|---|---|---|
`;

/** 重写仓库根 发布清单.md：AUTO 区自动生成，AUTO:END 之后的人工段落原样保留 */
function writeManifest(pkgs, cfg) {
  let tail = DEFAULT_MANUAL_TAIL;
  if (exists(MANIFEST)) {
    const old = fs.readFileSync(MANIFEST, 'utf8');
    const i = old.indexOf(AUTO_END);
    if (i >= 0) {
      const rest = old.slice(i + AUTO_END.length);
      if (rest.trim()) tail = rest.replace(/^\s*\n/, '\n');
    }
  }
  pkgsAll = pkgs;
  const stamp = fmtStamp(new Date());
  const out = `${AUTO_BEGIN}\n${renderManifest(pkgs, cfg, stamp)}\n${AUTO_END}\n${tail}`;
  fs.writeFileSync(MANIFEST, out);
  return MANIFEST;
}

/**
 * 清理 dist/ 里遗留的旧位置发布清单（曾放在 dist/ 下）。
 * 清单已迁到仓库根：两处并存必然会让人看错一份，构建时顺手清掉。
 * 只匹配 `发布清单.md` / `发布清单-<版本>.md`，不碰 dist/ 里任何 zip。
 */
function pruneLegacyManifests() {
  const removed = [];
  if (!exists(DIST)) return removed;
  for (const f of fs.readdirSync(DIST)) {
    if (!LEGACY_MANIFEST_RE.test(f)) continue;
    fs.rmSync(path.join(DIST, f), { force: true });
    removed.push(f);
  }
  return removed;
}

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
  console.log(C.dim('  ' + pad('包名', 30) + pad('类型', 8) + pad('版本', 9) + pad('展示名', 18) + pad('自身图标', 12) + '内嵌技能'));
  console.log(C.dim('  ' + '─'.repeat(108)));

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
    console.log('  ' + pad(p.name, 30) + pad(type, 8) + pad(versionOf(p), 9) + pad(displayNameOf(p), 18) + pad(ownIconState(p), 12) + embedCell);
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
    keepOldZips: argv.includes('--keep-old-zips'),
    noManifest: argv.includes('--no-manifest'),
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
  console.log(C.dim('  ' + pad('包名', 30) + pad('版本', 9) + pad('类型', 8) + pad('体积', 11) + pad('产物文件', 38) + '状态'));
  console.log(C.dim('  ' + '─'.repeat(112)));
  for (const { pkg, r } of results) {
    const type = typeLabelOf(pkg);
    const size = r.size ? (r.size / 1024).toFixed(1) + ' KB' : '—';
    const state = r.published ? C.green('✓ 已写入 dist/') : C.red('✗ 未写出');
    const emb = r.embed && r.embed.count > 0 ? C.dim(` 内嵌 ${r.embed.count}`) : '';
    console.log('  ' + pad(pkg.name, 30) + pad(versionOf(pkg), 9) + pad(type, 8) + pad(size, 11)
      + pad(r.published ? r.zipName : '—', 38) + state + emb);
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

  // ---- 旧产物清理明细 ----
  const prunedAll = results.flatMap((x) => (x.r.pruned || []).map((f) => ({ pkg: x.pkg.name, f })));
  if (prunedAll.length) {
    console.log('');
    console.log(C.bold('已清理同包旧产物') + C.dim('（每次构建只留该包最新一版；--keep-old-zips 可保留）'));
    for (const x of prunedAll) console.log('  ' + C.dim(`${x.pkg} → 删除 dist/${x.f}`));
  }

  // ---- 发布清单 ----
  if (!opts.noManifest) {
    const cfg = loadReleaseConfig();
    if (cfg.error) console.log('\n' + C.yellow('! ') + cfg.error + C.dim('（发布清单里的类目/平台版本会缺项）'));
    if (!exists(MANIFEST)) {
      console.log('\n' + C.yellow('! ') + `仓库根没有 发布清单.md，本次按默认模板新建` +
        C.dim('（发布历史需要另补）'));
    }
    writeManifest(pkgs, cfg);
    const stale = pruneLegacyManifests();
    console.log('');
    console.log(C.bold('发布清单') + C.dim(`  ${norm(path.relative(ROOT, MANIFEST))} 已按实际版本重写（人工段落保留）`));
    for (const f of stale) console.log('  ' + C.dim(`已清理旧位置 dist/${f}（清单已迁到仓库根，两处并存会看错）`));
  }
}

main();
