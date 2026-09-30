#!/usr/bin/env node
/**
 * 晓得·别解 —— 卡片骨架渲染器 + 合规检查器（零第三方依赖）
 *
 *   node scripts/card.mjs render --word 甲方 --pinyin "jiǎ fāng" \
 *       --en "Client / Party A" --trad-same \
 *       --def "甲方，是一个动词。" --def "用一笔预算，买断另一个人对美的定义权。" \
 *       --diagram diagram.svg --caption "自环：每改一版，需求就多一条" \
 *       --out card.svg
 *
 *   node scripts/card.mjs check --in card.svg
 *   node scripts/card.mjs palettes
 *   node scripts/card.mjs selftest
 *
 * 设计要点：
 * 1) 两套画布（poster / inline）**共用一张 y 轴节奏表**（下方 TABLE_Y）。
 *    手工维护两套坐标必然漂移，所以只留一份 y 表，宽度差异由 CANVAS 描述。
 * 2) 配色默认按词条哈希取（同一个词永远同一个色），另支持指定与真随机。
 * 3) 图解片段以**图解区中心为原点**书写，脚本负责平移 —— 片段因此与画布宽无关。
 * 4) 一切降级都要出声：不认识的颜色名 / 图解文件不存在 / 繁體值缺失，一律非 0 退出并给出口。
 */

import fs from 'node:fs';
import path from 'node:path';

const MIN_FONT = 11;
const MAX_COLORS = 4;

/** y 轴节奏表 —— 两套画布通用，唯一真源 */
const TABLE_Y = {
  title: 62,
  divider: 80,
  pinyin: 116,
  word: 154,
  langs: 180,
  def: [222, 248, 274],
  dTop: 300,
  dBottom: 470,
  caption: 496,
  footer: 548,
  cardBottom: 584,
};

/** 画布差异只在这三项：宽度、左右留白、词字号 */
const CANVAS = {
  poster: { w: 400, h: 600, cardX: 16, cardW: 368, cardY: 16, word: 32, divHalf: 60 },
  inline: { w: 680, h: 604, cardX: 40, cardW: 600, cardY: 20, word: 34, divHalf: 90 },
};

const PALETTES = {
  sakura: { bg: '#FBE6EA', ink: '#3A2A2E', soft: '#8C7A7F', accent: '#A64B63' },
  mint: { bg: '#E4F1E6', ink: '#2A3B2E', soft: '#7C8C80', accent: '#2F6B4F' },
  cream: { bg: '#FBF2DC', ink: '#3A3325', soft: '#8C8371', accent: '#A97C2F' },
  lilac: { bg: '#EEE7F6', ink: '#302A3A', soft: '#7F7A8C', accent: '#6A5AA6' },
  sky: { bg: '#E2EFF8', ink: '#26333C', soft: '#76868F', accent: '#2E6C93' },
  peach: { bg: '#FDECDF', ink: '#3A2E26', soft: '#8C7C71', accent: '#B36A3C' },
  matcha: { bg: '#EAF1DC', ink: '#2F3A26', soft: '#808C71', accent: '#5C7A31' },
  cocoa: { bg: '#F2E7DF', ink: '#352C27', soft: '#8A7F77', accent: '#8C5A3C' },
};
const PALETTE_NAMES = Object.keys(PALETTES);

const KAI = "'Kaiti SC','STKaiti',KaiTi,serif";
const TITLE_TEXT = '晓得·别解';
const DEFAULT_FOOTER = '一目晓得';

/**
 * 默认禁用字样 —— 只收「带冒号的署名标记」这类不可能出现在正文里的形态。
 * 裸词（如「来源」「作者」）会误伤正常释义（「来源不明的优越感」），所以不进默认表。
 * 具体第三方作品名 / 作者名请在出卡时用 --forbid 显式传进来。
 */
const FORBID_DEFAULT = ['©', '提示词框架', '作者：', '来源：'];

const out = (s) => process.stdout.write(s + '\n');
const err = (s) => process.stderr.write(s + '\n');

function bail(msg, hint) {
  err('[XX] ' + msg);
  if (hint) err('     出口：' + hint);
  process.exit(1);
}

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** FNV-1a，用来让「同一个词 = 同一个色」 */
function hashWord(s) {
  let h = 2166136261 >>> 0;
  for (const ch of s) {
    h ^= ch.codePointAt(0);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h;
}

function parseArgs(argv) {
  const o = { _: [], def: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      if (['trad-same', 'no-footer', 'help'].includes(key)) {
        o[key] = true;
      } else {
        const v = argv[++i];
        if (v === undefined) bail(`--${key} 缺少取值`);
        if (key === 'def') o.def.push(v);
        else o[key] = v;
      }
    } else o._.push(a);
  }
  return o;
}

function resolvePalette(o, word) {
  const want = (o.palette || 'auto').trim();
  if (want === 'auto') {
    const key = PALETTE_NAMES[hashWord(word) % PALETTE_NAMES.length];
    return { key, why: `auto（按词条哈希）` };
  }
  if (want === 'random') {
    const key = PALETTE_NAMES[Math.floor(Math.random() * PALETTE_NAMES.length)];
    return { key, why: 'random（真随机）' };
  }
  if (!PALETTES[want]) {
    bail(`不认识的颜色名：${want}`, `可用：${PALETTE_NAMES.join(' / ')} / auto / random`);
  }
  return { key: want, why: '指定' };
}

function resolveTrad(o, word) {
  if (o['trad-kind']) {
    const k = String(o['trad-kind']).toLowerCase();
    if (k === 'alpha') return '字母詞，繁簡同形';
    if (k === 'digit') return '數字詞，繁簡同形';
    bail(`--trad-kind 只支持 alpha / digit，收到：${o['trad-kind']}`);
  }
  if (o['trad-same']) return `${word}（同形）`;
  if (o.trad) {
    // 繁体字形必然含汉字。传进来的值没有汉字 = 一定是用错了（如把 --trad-same 写成 --trad same）
    // —— 静默把 "same" 印进卡片比报错危险得多，所以这里直接驳回。
    if (!/[\u3400-\u9fff]/.test(o.trad)) {
      bail(
        `--trad 的取值不含汉字：${o.trad}`,
        '同形请用 --trad-same；字母词 / 数字词请用 --trad-kind alpha|digit；只有异形才用 --trad <字形>'
      );
    }
    return o.trad;
  }
  bail(
    '缺少繁體值 —— 语言行必有这一项',
    '三选一：--trad 週報（异形） / --trad-same（同形） / --trad-kind alpha|digit（字母词或数字词）'
  );
}

function buildSvg(o) {
  const word = o.word;
  if (!word) bail('缺少 --word（词条）', '至少要给一个词：--word 甲方');
  if (!o.def.length) bail('缺少 --def（释义，至少一行）', '--def "一句话"');

  const canvasKey = o.canvas || 'poster';
  const C = CANVAS[canvasKey];
  if (!C) bail(`不认识的画布：${canvasKey}`, '可用：poster（400×600 竖版）/ inline（680 宽）');

  const pal = resolvePalette(o, word);
  const P = PALETTES[pal.key];
  const trad = resolveTrad(o, word);

  let diagram = '';
  if (o.diagram) {
    if (!fs.existsSync(o.diagram)) {
      bail(`图解文件不存在：${o.diagram}`, '确认路径；确实不画图就不要传 --diagram');
    }
    diagram = fs
      .readFileSync(o.diagram, 'utf8')
      .replace(/\{\{bg\}\}/g, P.bg)
      .replace(/\{\{ink\}\}/g, P.ink)
      .replace(/\{\{soft\}\}/g, P.soft)
      .replace(/\{\{accent\}\}/g, P.accent);
    const left = [...diagram.matchAll(/\{\{(\w+)\}\}/g)].map((m) => m[1]);
    if (left.length) {
      err(`[!!] 图解里还有未替换的占位符：${[...new Set(left)].join(', ')}（仅支持 bg/ink/soft/accent）`);
    }
  }

  const cx = C.w / 2;
  const dCy = (TABLE_Y.dTop + TABLE_Y.dBottom) / 2;
  const defLine = (y, t) =>
    t ? `<text x="${cx}" y="${y}" font-size="15" fill="${P.ink}" text-anchor="middle" font-family="${KAI}">${esc(t)}</text>` : '';

  const langParts = [];
  if (o.en) langParts.push(`English: ${o.en}`);
  langParts.push(`繁體：${trad}`);

  const footer = o['no-footer'] ? null : o.footer || DEFAULT_FOOTER;

  const body = [
    `<rect x="${C.cardX}" y="${C.cardY}" width="${C.cardW}" height="${TABLE_Y.cardBottom - C.cardY}" rx="16" fill="${P.bg}"/>`,
    `<text x="${cx}" y="${TABLE_Y.title}" font-size="17" fill="${P.ink}" text-anchor="middle" font-family="${KAI}" letter-spacing="4">${TITLE_TEXT}</text>`,
    `<line x1="${cx - C.divHalf}" y1="${TABLE_Y.divider}" x2="${cx + C.divHalf}" y2="${TABLE_Y.divider}" stroke="${P.soft}" stroke-width="0.5"/>`,
    o.pinyin
      ? `<text x="${cx}" y="${TABLE_Y.pinyin}" font-size="13" fill="${P.soft}" text-anchor="middle">${esc(o.pinyin)}</text>`
      : '',
    `<text x="${cx}" y="${TABLE_Y.word}" font-size="${C.word}" fill="${P.ink}" text-anchor="middle" font-family="${KAI}">${esc(word)}</text>`,
    `<text x="${cx}" y="${TABLE_Y.langs}" font-size="12" fill="${P.soft}" text-anchor="middle">${esc(langParts.join('  |  '))}</text>`,
    ...TABLE_Y.def.map((y, i) => defLine(y, o.def[i])),
    diagram ? `<g transform="translate(${cx} ${dCy})">${diagram}</g>` : '',
    o.caption
      ? `<text x="${cx}" y="${TABLE_Y.caption}" font-size="11" fill="${P.soft}" text-anchor="middle">${esc(o.caption)}</text>`
      : '',
    footer
      ? `<text x="${cx}" y="${TABLE_Y.footer}" font-size="11" fill="${P.soft}" text-anchor="middle">${esc(footer)}</text>`
      : '',
  ]
    .filter(Boolean)
    .join('\n');

  const svg =
    `<svg width="100%" viewBox="0 0 ${C.w} ${C.h}" role="img" xmlns="http://www.w3.org/2000/svg">\n` +
    `<title>别解：${esc(word)}</title>\n` +
    `<desc>别解卡片。词条${esc(word)}${o.pinyin ? `，拼音 ${esc(o.pinyin)}` : ''}；词条下方为英文与繁體；再下方是别解释义与语义图解。</desc>\n` +
    body +
    `\n</svg>\n`;

  return { svg, canvasKey, palette: pal, trad };
}

/* ------------------------------ check ------------------------------ */

function checkSvg(svg, opts = {}) {
  const issues = [];
  const notes = [];
  const forbid = (opts.forbid || []).filter(Boolean);

  const viewBox = /viewBox="0 0 (\d+) (\d+)"/.exec(svg);
  if (!viewBox) issues.push('缺少 viewBox');
  else if (![400, 680].includes(Number(viewBox[1]))) {
    issues.push(`画布宽 ${viewBox[1]} 不在允许值 {400, 680}`);
  }
  if (!/width="100%"/.test(svg)) issues.push('根元素缺 width="100%"');

  const shapes = [...svg.matchAll(/<(rect|circle|ellipse|polygon|polyline|path|line|text|tspan)\b([^>]*)>/g)];
  if (!shapes.length) issues.push('一个图形元素都没找到');
  let noPaint = 0;
  for (const m of shapes) {
    const attrs = m[2];
    if (!/\bfill\s*=/.test(attrs) && !/\bstroke\s*=/.test(attrs)) {
      noPaint++;
      issues.push(`<${m[1]}> 未显式写 fill / stroke（会退化成黑色）`);
    }
  }
  for (const m of shapes) {
    if (!['polyline', 'path'].includes(m[1])) continue;
    if (!/\bfill\s*=/.test(m[2])) issues.push(`<${m[1]}> 缺显式 fill（连线应写 fill="none"）`);
  }

  const sizes = [...svg.matchAll(/font-size="([\d.]+)"/g)].map((m) => Number(m[1]));
  const small = sizes.filter((n) => n < MIN_FONT);
  if (small.length) issues.push(`有 ${small.length} 处字号小于 ${MIN_FONT}px：${[...new Set(small)].join(', ')}`);

  const colors = new Set();
  for (const m of svg.matchAll(/(?:fill|stroke)="([^"]+)"/g)) {
    const v = m[1].trim().toLowerCase();
    if (['none', 'transparent', 'currentcolor'].includes(v)) continue;
    colors.add(v);
  }
  if (colors.size > MAX_COLORS) {
    issues.push(`颜色数 ${colors.size} 超过上限 ${MAX_COLORS}：${[...colors].join(', ')}`);
  }

  const emoji = /[\u{1F000}-\u{1FAFF}\u{2190}-\u{21FF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}\uFE0F]/u.exec(svg);
  if (emoji) issues.push(`出现 emoji / 符号字符：${emoji[0]}（图标请用几何图形）`);

  if (/<!--/.test(svg)) issues.push('含 HTML 注释（渲染时会闪，且占体积）');
  if (/<script\b/i.test(svg)) issues.push('含 <script>');
  if (/\son[a-z]+\s*=/i.test(svg)) issues.push('含 on* 事件属性');

  const stripped = svg
    .replace(/xmlns(:xlink)?="http:\/\/www\.w3\.org\/[^"]*"/g, '')
    .replace(/http:\/\/www\.w3\.org\/[^"'\s]*/g, '');
  if (/http/i.test(stripped)) issues.push('含外部链接（http）');
  if (/url\(/.test(stripped)) issues.push('含 url( 外部引用');
  if (/xlink:href|<image\b/i.test(svg)) issues.push('含 <image> 或 xlink:href 外部资源');

  if (!/<title>/.test(svg)) issues.push('缺 <title>（无障碍）');
  if (!/<desc>/.test(svg)) issues.push('缺 <desc>（无障碍）');

  if (!svg.includes(TITLE_TEXT)) issues.push(`刊头不是「${TITLE_TEXT}」`);
  if (!svg.includes('繁體：')) issues.push('语言行缺「繁體：」');

  const texts = [...svg.matchAll(/<text\b[^>]*>([\s\S]*?)<\/text>/g)].map((m) => m[1]);
  const joined = texts.join('\n');
  for (const w of [...FORBID_DEFAULT, ...forbid]) {
    if (w && joined.includes(w)) issues.push(`卡片内出现不该有的署名/来源字样：${w}`);
  }
  const footerTexts = texts.filter((t) => t && !t.includes(TITLE_TEXT));
  if (footerTexts.length === 0) notes.push('卡片没有页脚文字（非失败）');

  return { issues, notes, colors: colors.size, minFont: Math.min(...sizes), shapes: shapes.length };
}

/* ------------------------------ selftest ------------------------------ */

/* 固定的真实词样本：用于「配色按词稳定」与「配色不塌缩」两项。
   取自中文互联网真实热词 / 职场词 / 缩写词，**不要改成几个随手编的词** ——
   样本太小时「某套色没被抽到」只是小样本噪声，判据会得出错误结论。 */
const SAMPLE_WORDS = [
  '甲方', '乙方', '内卷', '躺平', '摸鱼', '加班', '复盘', '对齐', '赋能', '抓手',
  '闭环', '落地', '痛点', '场景', '生态', '打法', '心智', '赛道', '风口', '韭菜',
  '打工人', '社畜', '中年危机', '信息茧房', '内耗', '焦虑', '情绪价值', '钝感力', '边界感', '松弛感',
  '仪式感', '获得感', '使命感', '责任心', '执行力', '周报', '月报', '述职', '绩效', '晋升',
  '跳槽', '裸辞', '副业', '自媒体', '直播', '带货', '私域', '流量', '留存', '转化',
  '复购', '拉新', '日活', '客单价', 'KPI', '996', '摸鱼学', '甲方爸爸', '颗粒度', '复盘会',
];

function selftest() {
  const base = buildSvg({ word: '甲方', pinyin: 'jiǎ fāng', en: 'Client / Party A', 'trad-same': true, def: ['一句话'], canvas: 'poster' }).svg;
  const cases = [
    ['阳性对照 · 正常卡', base, false, '完全合规的卡应通过'],
    ['画布宽写错', base.replace('viewBox="0 0 400', 'viewBox="0 0 402'), true, '宽度不在 {400,680}'],
    ['抽掉一个 fill', base.replace(/\sfill="[^"]+"/, ''), true, '元素丢 fill'],
    ['字号压到 9px', base.replace('font-size="11"', 'font-size="9"'), true, '低于 11px'],
    ['塞进两种新颜色', base.replace('<rect', '<rect fill="#123456" stroke="#654321"'), true, '颜色超 4（基线卡无图解，卡面只有 3 色，故须加两种）'],
    ['加一个 emoji', base.replace('一目晓得', '一目晓得\u{1F319}'), true, 'emoji'],
    ['加 HTML 注释', base.replace('<title>', '<!-- c --><title>'), true, '注释'],
    ['加 script', base.replace('<title>', '<script>x</script><title>'), true, 'script'],
    ['加外部链接', base.replace('<title>', '<image href="https://x/y.png"/><title>'), true, '外链'],
    ['抽掉 desc', base.replace(/<desc>[\s\S]*?<\/desc>/, ''), true, '无障碍'],
    ['改掉刊头', base.replace(TITLE_TEXT, '汉语新解'), true, '刊头不对'],
    ['去掉繁體行', base.replace('繁體：', '繁體'), true, '语言行'],
    ['页脚塞入署名标记', base.replace(DEFAULT_FOOTER, '作者：某某'), true, '署名标记'],
    ['--forbid 追加禁用词', base.replace(DEFAULT_FOOTER, '某某作品'), true, '自定义禁用词', { forbid: ['某某作品'] }],
    ['阴性对照 · inline 画布', buildSvg({ word: 'KPI', 'trad-kind': 'alpha', def: ['一句话'], canvas: 'inline' }).svg, false, 'inline 画布同样应通过'],
  ];
  let pass = 0;
  let total = 0;
  for (const [name, svg, wantFail, why, opts] of cases) {
    const r = checkSvg(svg, opts || {});
    const failed = r.issues.length > 0;
    const result = wantFail ? '期望被驳回' : '期望通过';
    const actual = failed ? '实际被驳回' : '实际通过';
    const good = failed === wantFail;
    total++;
    if (good) pass++;
    out(`  ${good ? '[OK]' : '[XX]'} ${name.padEnd(22, ' ')} ${actual}（${result}）${good ? '' : '  <- ' + why}`);
  }

  /* 配色两项走真实选色路径 resolvePalette。**不许用 hashWord 直算来测**：
     直算等于断言「一个纯函数是否等于它自己」，恒真、永不失败，
     而且选色逻辑整个坏掉（例如永远返回第一套色）它照样报绿 —— 那是假测试。 */
  const stableOk = (f) => {
    const a = f(SAMPLE_WORDS);
    const b = f(SAMPLE_WORDS);
    return a.every((k, i) => k === b[i]);
  };
  const spreadOk = (keys) => {
    const c = new Map(PALETTE_NAMES.map((n) => [n, 0]));
    for (const k of keys) c.set(k, (c.get(k) || 0) + 1);
    const allReachable = PALETTE_NAMES.every((n) => (c.get(n) || 0) > 0);
    const maxShare = Math.max(...c.values()) / keys.length;
    return allReachable && maxShare <= 0.4;
  };
  const pickAuto = (ws) => ws.map((w) => resolvePalette({}, w).key);
  let drift = 0;
  const extra = [
    ['配色按词稳定（走真实选色路径）', stableOk(pickAuto), true,
      `${SAMPLE_WORDS.length} 个词各取两次逐一比对（此判据对 --palette random 那种漂移取色必须判不稳）`],
    ['配色不塌缩 · 无死分支', spreadOk(pickAuto(SAMPLE_WORDS)), true,
      `8 套色全可达，且单一色占比 ≤ 40%（实测 ${SAMPLE_WORDS.length} 个词的分布需落在此区间）`],
    ['反向对照 · 漂移取色应判不稳', stableOk(() => SAMPLE_WORDS.map(() => PALETTE_NAMES[(drift++) % PALETTE_NAMES.length])), false,
      '每次调用都换色 → 稳定性判据必须判它不稳，否则该判据没有判别力'],
    ['反向对照 · 塌缩取色应判分散失败', spreadOk(SAMPLE_WORDS.map(() => PALETTE_NAMES[0])), false,
      '全部落同一套色 → 分散度判据必须判它失败'],
    ['反向对照 · 缺一套色应判分散失败', spreadOk(PALETTE_NAMES.slice(1).flatMap((n) => [n, n, n])), false,
      '漏掉一套色（死分支）→ 分散度判据必须判它失败'],
  ];
  for (const [name, got, want, why] of extra) {
    const good = got === want;
    total++;
    if (good) pass++;
    out(`  ${good ? '[OK]' : '[XX]'} ${name.padEnd(26, ' ')} 实际${got ? '通过' : '失败'}（期望${want ? '通过' : '失败'}）${good ? '' : '  <- ' + why}`);
  }
  out(`\n自检 ${pass}/${total} 项`);
  return pass === total ? 0 : 1;
}

/* ------------------------------ main ------------------------------ */

const argv = process.argv.slice(2);
const cmd = argv[0];
const o = parseArgs(argv.slice(1));

if (!cmd || cmd === 'help' || o.help) {
  out('用法:');
  out('  node scripts/card.mjs render --word <词> [--pinyin <拼音>] [--en <英文>] \\');
  out('      (--trad <繁體> | --trad-same | --trad-kind alpha|digit) \\');
  out('      --def <释义行> [--def <第二行>] [--def <第三行>] \\');
  out('      [--diagram <片段.svg>] [--caption <图说>] \\');
  out('      [--canvas poster|inline] [--palette auto|random|<色名>] \\');
  out('      [--footer <文字> | --no-footer] [--out <文件>]');
  out('  node scripts/card.mjs check --in <card.svg> [--forbid <词>]');
  out('  node scripts/card.mjs palettes');
  out('  node scripts/card.mjs selftest');
  process.exit(cmd ? 0 : 1);
}

if (cmd === 'palettes') {
  out('可用配色（键 / 底 / 墨 / 弱化 / 强调）：');
  for (const k of PALETTE_NAMES) {
    const p = PALETTES[k];
    out(`  ${k.padEnd(8, ' ')} ${p.bg}  ${p.ink}  ${p.soft}  ${p.accent}`);
  }
  process.exit(0);
}

if (cmd === 'selftest') {
  out('检查器自检（正向 + 反向，逐条篡改检查目标）：');
  process.exit(selftest());
}

if (cmd === 'render') {
  const r = buildSvg(o);
  if (o.out) {
    fs.writeFileSync(path.resolve(o.out), r.svg);
    out(`已写出 ${o.out}（画布 ${r.canvasKey}，配色 ${r.palette.key} · ${r.palette.why}）`);
    out(`下一步必跑：node scripts/card.mjs check --in ${o.out}`);
  } else {
    process.stdout.write(r.svg);
  }
  process.exit(0);
}

if (cmd === 'check') {
  if (!o.in) bail('缺少 --in <card.svg>', 'node scripts/card.mjs check --in card.svg');
  if (!fs.existsSync(o.in)) bail(`文件不存在：${o.in}`, '确认路径；render 时用 --out 指定输出文件');
  const svg = fs.readFileSync(o.in, 'utf8');
  const forbid = (o.forbid || '').split(',').map((s) => s.trim()).filter(Boolean);
  const r = checkSvg(svg, { forbid });
  out(`检查 ${o.in}：元素 ${r.shapes} · 颜色 ${r.colors} · 最小字号 ${r.minFont}px`);
  for (const nt of r.notes) out('  [!!] ' + nt);
  if (r.issues.length) {
    out(`\n不合规 ${r.issues.length} 项：`);
    for (const i of r.issues) out('  [XX] ' + i);
    out('\n出口：按 references/card-spec.md §五 逐条修；图解只写 {{bg}}/{{ink}}/{{soft}}/{{accent}} 四个占位符。');
    process.exit(1);
  }
  out('=== 合规检查通过 ===');
  process.exit(0);
}

bail(`不认识的命令：${cmd}`, '可用命令：render / check / palettes / selftest');
